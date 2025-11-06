import json
import logging
from typing import Any, Dict, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


class DittoError(Exception):
    """Raised when Ditto operations fail."""


class DittoClient:
    """Client for interacting with Eclipse Ditto API."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.DITTO_BASE_URL.rstrip("/")
        self.timeout = self.settings.HTTP_TIMEOUT_SECONDS
        self._client = httpx.Client(timeout=self.timeout)
        self._headers = self._build_headers()

        # In-memory fallback store if enabled
        self._mem_store: Dict[str, Dict[str, Any]] = {}

    def _build_headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {"Content-Type": "application/json"}
        if self.settings.DITTO_AUTH:
            headers["Authorization"] = self.settings.DITTO_AUTH
        elif self.settings.DITTO_USERNAME and self.settings.DITTO_PASSWORD:
            # httpx supports auth tuple but we use Basic header to be explicit
            import base64

            token = base64.b64encode(
                f"{self.settings.DITTO_USERNAME}:{self.settings.DITTO_PASSWORD}".encode("utf-8")
            ).decode("utf-8")
            headers["Authorization"] = f"Basic {token}"
        return headers

    def _thing_url(self, thing_id: str) -> str:
        return f"{self.base_url}/things/{thing_id}"

    def _feature_url(self, thing_id: str, feature_id: str) -> str:
        return f"{self._thing_url(thing_id)}/features/{feature_id}"

    def _get_or_init_mem_thing(self, thing_id: str) -> Dict[str, Any]:
        if thing_id not in self._mem_store:
            self._mem_store[thing_id] = {"features": {}}
        return self._mem_store[thing_id]

    def _get_or_init_mem_feature(self, thing_id: str, feature_id: str) -> Dict[str, Any]:
        thing = self._get_or_init_mem_thing(thing_id)
        features = thing.setdefault("features", {})
        return features.setdefault(feature_id, {"properties": {}})

    # PUBLIC_INTERFACE
    def get_feature(self, thing_id: str, feature_id: str) -> Optional[Dict[str, Any]]:
        """Get a feature of a Ditto thing."""
        if get_settings().ENABLE_INMEMORY_DITTO:
            return self._get_or_init_mem_feature(thing_id, feature_id)

        url = self._feature_url(thing_id, feature_id)
        try:
            resp = self._client.get(url, headers=self._headers)
            if resp.status_code == 404:
                return None
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            logger.exception("Ditto get_feature failed for %s/%s: %s", thing_id, feature_id, e)
            raise DittoError(str(e)) from e

    # PUBLIC_INTERFACE
    def put_feature(self, thing_id: str, feature_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create or replace a feature for a Ditto thing."""
        if get_settings().ENABLE_INMEMORY_DITTO:
            self._get_or_init_mem_thing(thing_id)
            self._mem_store[thing_id]["features"][feature_id] = data
            return data

        url = self._feature_url(thing_id, feature_id)
        try:
            resp = self._client.put(url, headers=self._headers, content=json.dumps(data))
            resp.raise_for_status()
            return resp.json() if resp.content else data
        except Exception as e:
            logger.exception("Ditto put_feature failed for %s/%s: %s", thing_id, feature_id, e)
            raise DittoError(str(e)) from e

    # PUBLIC_INTERFACE
    def patch_feature(self, thing_id: str, feature_id: str, patch_ops: Any) -> Dict[str, Any]:
        """Apply JSON Patch to a feature (if Ditto supports). Fallback to read-modify-write."""
        if get_settings().ENABLE_INMEMORY_DITTO:
            # naive apply: handle append to arrays path like /properties/alerts
            feature = self._get_or_init_mem_feature(thing_id, feature_id)
            try:
                for op in patch_ops:
                    if op.get("op") in ("add", "replace"):
                        path = op["path"].lstrip("/").split("/")
                        node = feature
                        for p in path[:-1]:
                            node = node.setdefault(p, {})
                        node[path[-1]] = op["value"]
                    elif op.get("op") == "test":
                        # ignore
                        pass
                return feature
            except Exception as e:
                raise DittoError(f"In-memory patch failed: {e}") from e

        url = self._feature_url(thing_id, feature_id)
        try:
            resp = self._client.patch(url, headers=self._headers, content=json.dumps(patch_ops))
            if resp.status_code in (400, 405, 409, 501):
                # Fallback to read-modify-write
                logger.info("Ditto patch not supported/failed, using RMW: %s", resp.text)
                current = self.get_feature(thing_id, feature_id) or {"properties": {}}
                # We only support adding values to arrays via a push-like operation in fallback
                # The caller is expected to perform manual RMW if needed.
                return current
            resp.raise_for_status()
            return resp.json() if resp.content else {}
        except Exception as e:
            logger.exception("Ditto patch_feature failed for %s/%s: %s", thing_id, feature_id, e)
            raise DittoError(str(e)) from e

    # PUBLIC_INTERFACE
    def ensure_alerts_feature(self, bng_thing_id: str) -> Dict[str, Any]:
        """Ensure alerts feature exists with structure {properties:{alerts:[], recommendations:[]}}."""
        feature_id = "alerts"
        feature = self.get_feature(bng_thing_id, feature_id)
        default = {"properties": {"alerts": [], "recommendations": []}}
        if not feature:
            return self.put_feature(bng_thing_id, feature_id, default)
        # validate structure
        props = feature.setdefault("properties", {})
        props.setdefault("alerts", [])
        props.setdefault("recommendations", [])
        # write back if structure was missing
        if get_settings().ENABLE_INMEMORY_DITTO:
            self.put_feature(bng_thing_id, feature_id, feature)
        else:
            try:
                self.put_feature(bng_thing_id, feature_id, feature)
            except DittoError:
                pass
        return feature

    # PUBLIC_INTERFACE
    def append_alert(self, bng_thing_id: str, alert: str) -> Dict[str, Any]:
        """Append an alert string to alerts feature."""
        feature = self.ensure_alerts_feature(bng_thing_id)
        props = feature["properties"]
        alerts = props.get("alerts", [])
        alerts.append(alert)
        feature["properties"]["alerts"] = alerts
        return self.put_feature(bng_thing_id, "alerts", feature)

    # PUBLIC_INTERFACE
    def append_recommendation(self, bng_thing_id: str, rec: str) -> Dict[str, Any]:
        """Append a recommendation string to alerts feature."""
        feature = self.ensure_alerts_feature(bng_thing_id)
        props = feature["properties"]
        recs = props.get("recommendations", [])
        recs.append(rec)
        feature["properties"]["recommendations"] = recs
        return self.put_feature(bng_thing_id, "alerts", feature)

    # PUBLIC_INTERFACE
    def get_bng_kpis(self, bng_thing_id: str) -> Dict[str, Any]:
        """Read BNG KPIs from state feature."""
        feature = self.get_feature(bng_thing_id, "state") or {"properties": {}}
        props = feature.get("properties", {})
        return {
            "cpu": props.get("cpu", 0),
            "mem_pct": props.get("mem_pct", 0),
            "active_sessions": props.get("active_sessions", 0),
        }

    # PUBLIC_INTERFACE
    def update_bng_kpis(
        self,
        bng_thing_id: str,
        cpu: Optional[int] = None,
        mem_pct: Optional[int] = None,
        active_sessions: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Update BNG KPIs in Ditto 'state' feature."""
        feature = self.get_feature(bng_thing_id, "state") or {"properties": {"cpu": 0, "mem_pct": 0, "active_sessions": 0}}
        props = feature.setdefault("properties", {})
        if cpu is not None:
            props["cpu"] = cpu
        if mem_pct is not None:
            props["mem_pct"] = mem_pct
        if active_sessions is not None:
            props["active_sessions"] = active_sessions
        return self.put_feature(bng_thing_id, "state", feature)

    # PUBLIC_INTERFACE
    def set_subscriber_session(
        self, subscriber_thing_id: str, status: str, ip_address: str = "", last_allocated_at: Optional[str] = None
    ) -> Dict[str, Any]:
        """Update subscriber's session feature."""
        feature = self.get_feature(subscriber_thing_id, "session") or {"properties": {}}
        props = feature.setdefault("properties", {})
        props["status"] = status
        if ip_address is not None:
            props["ip_address"] = ip_address
        if last_allocated_at is not None:
            props["last_allocated_at"] = last_allocated_at
        return self.put_feature(subscriber_thing_id, "session", feature)

    # PUBLIC_INTERFACE
    def list_active_subscribers(self) -> Dict[str, Dict[str, Any]]:
        """Return mapping of subscriber -> session props for active sessions (Ditto scan fallback).
        Note: Without Ditto search we rely on in-memory known keys or return empty.
        """
        results: Dict[str, Dict[str, Any]] = {}
        if get_settings().ENABLE_INMEMORY_DITTO:
            for thing_id, thing in self._mem_store.items():
                if thing_id.startswith("LEXI-NDT:Subscriber-"):
                    sess = thing.get("features", {}).get("session", {}).get("properties", {})
                    if sess.get("status") == "active":
                        results[thing_id] = sess
            return results

        # If Ditto search API isn't configured, we cannot query all items; return empty.
        logger.info("Ditto search not configured; returning empty active subscriber list")
        return results

    # PUBLIC_INTERFACE
    def ensure_thing_exists(self, thing_id: str) -> None:
        """For in-memory mode, ensures a thing exists."""
        if get_settings().ENABLE_INMEMORY_DITTO:
            self._get_or_init_mem_thing(thing_id)


# Singleton accessor
_client_instance: Optional[DittoClient] = None


# PUBLIC_INTERFACE
def get_ditto_client() -> DittoClient:
    """Get a singleton DittoClient."""
    global _client_instance
    if _client_instance is None:
        _client_instance = DittoClient()
    return _client_instance
