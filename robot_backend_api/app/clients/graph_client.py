import logging
from typing import Dict, List, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger(__name__)


class GraphClientError(Exception):
    """Raised for Graph client errors."""


class GraphClient:
    """Client for Graph API with in-memory fallback."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.base_url = self.settings.GRAPH_API_BASE_URL.rstrip("/") if self.settings.GRAPH_API_BASE_URL else None
        self._headers = {}
        if self.settings.GRAPH_AUTH_BEARER:
            self._headers["Authorization"] = f"Bearer {self.settings.GRAPH_AUTH_BEARER}"
        self._client = httpx.Client(timeout=self.settings.HTTP_TIMEOUT_SECONDS) if self.base_url else None

        # In-memory representation: bng -> list of subscribers
        self._mem_edges: Dict[str, List[str]] = {
            "LEXI-NDT:BNG-Chennai-1": ["LEXI-NDT:Subscriber-SUB1", "LEXI-NDT:Subscriber-SUB2"],
            "LEXI-NDT:BNG-Bangalore-1": ["LEXI-NDT:Subscriber-SUB3", "LEXI-NDT:Subscriber-SUB4"],
        }

    # PUBLIC_INTERFACE
    def subscribers_by_bng(self, bng_id: str) -> List[str]:
        """Return list of subscriber thingIds served by a BNG. Uses Graph if available, otherwise fallback."""
        if self.base_url and self._client:
            try:
                # Placeholder: the actual path depends on Graph service API
                # We assume POST /graph/subscribers-by-bng with body {"bng":"<id>"}
                resp = self._client.post(
                    f"{self.base_url}/graph/subscribers-by-bng",
                    headers=self._headers,
                    json={"bng": bng_id},
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("subscribers", [])
            except Exception as e:
                logger.exception("Graph API subscribers_by_bng failed: %s", e)

        if get_settings().ENABLE_INMEMORY_GRAPH:
            return list(self._mem_edges.get(bng_id, []))
        return []

    # PUBLIC_INTERFACE
    def reassign_subscriber(self, subscriber_id: str, from_bng: str, to_bng: str) -> bool:
        """Update SERVES_SUBSCRIBER relationship in Graph. Fallback updates in-memory map."""
        if self.base_url and self._client:
            try:
                # Placeholder API call
                resp = self._client.post(
                    f"{self.base_url}/graph/reassign",
                    headers=self._headers,
                    json={"subscriber": subscriber_id, "from_bng": from_bng, "to_bng": to_bng},
                )
                resp.raise_for_status()
                return resp.json().get("success", True)
            except Exception as e:
                logger.exception("Graph API reassign_subscriber failed: %s", e)

        if get_settings().ENABLE_INMEMORY_GRAPH:
            src_list = self._mem_edges.get(from_bng, [])
            if subscriber_id in src_list:
                src_list.remove(subscriber_id)
            dst_list = self._mem_edges.setdefault(to_bng, [])
            if subscriber_id not in dst_list:
                dst_list.append(subscriber_id)
            return True
        return False


_graph_client_singleton: Optional[GraphClient] = None


# PUBLIC_INTERFACE
def get_graph_client() -> GraphClient:
    """Get singleton graph client."""
    global _graph_client_singleton
    if _graph_client_singleton is None:
        _graph_client_singleton = GraphClient()
    return _graph_client_singleton
