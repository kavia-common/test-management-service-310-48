import datetime
import logging
from typing import Optional

from fastapi import APIRouter, HTTPException

from ..clients.ditto_client import get_ditto_client
from ..clients.graph_client import get_graph_client
from ..models.schemas import AttachRequest, DetachRequest, AttachDetachResponse
from ..services.ip_allocator import allocate_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/subscribers", tags=["Subscribers"])


def _get_cidr_from_subnet_arg(subnet: str, explicit_cidr: Optional[str]) -> str:
    # If subnet looks like CIDR, return as is. Else use explicit_cidr or fallback to 100.64.1.0/24
    if "/" in subnet and any(c.isdigit() for c in subnet):
        return subnet
    if explicit_cidr:
        return explicit_cidr
    # Simple default for local simulations
    return "100.64.1.0/24"


# PUBLIC_INTERFACE
@router.post(
    "/attach",
    response_model=AttachDetachResponse,
    summary="Attach subscriber to BNG",
    description="Simulates subscriber attach: allocate IP, set session active in Ditto, increment BNG active_sessions, and update Graph relation.",
)
def attach(req: AttachRequest) -> AttachDetachResponse:
    """Attach subscriber to BNG and update Ditto/Graph states."""
    ditto = get_ditto_client()
    graph = get_graph_client()
    try:
        cidr = _get_cidr_from_subnet_arg(req.subnet, req.cidr)
        ip = allocate_ip(cidr, req.subscriber, req.requested_ip)
        ts = datetime.datetime.utcnow().isoformat() + "Z"

        # Subscriber session active
        ditto.set_subscriber_session(req.subscriber, status="active", ip_address=ip, last_allocated_at=ts)

        # BNG KPIs: increment active_sessions
        kpis = ditto.get_bng_kpis(req.bng)
        active = int(kpis.get("active_sessions", 0)) + 1
        ditto.update_bng_kpis(req.bng, active_sessions=active)

        # Graph relationship
        graph.reassign_subscriber(req.subscriber, from_bng="", to_bng=req.bng)  # from_bng unknown; add to target

        return AttachDetachResponse(
            subscriber=req.subscriber, bng=req.bng, ip_address=ip, session_status="active", bng_active_sessions=active
        )
    except Exception as e:
        logger.exception("Attach failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# PUBLIC_INTERFACE
@router.post(
    "/detach",
    response_model=AttachDetachResponse,
    summary="Detach subscriber from BNG",
    description="Simulates subscriber detach: set session inactive, decrement BNG active_sessions, and update Graph relation.",
)
def detach(req: DetachRequest) -> AttachDetachResponse:
    """Detach subscriber from BNG and update Ditto/Graph states."""
    ditto = get_ditto_client()
    graph = get_graph_client()
    try:
        # Subscriber session inactive
        ditto.set_subscriber_session(req.subscriber, status="inactive", ip_address="")

        # BNG KPIs: decrement active_sessions
        kpis = ditto.get_bng_kpis(req.bng)
        active = max(0, int(kpis.get("active_sessions", 0)) - 1)
        ditto.update_bng_kpis(req.bng, active_sessions=active)

        # Graph relation: remove from this BNG
        graph.reassign_subscriber(req.subscriber, from_bng=req.bng, to_bng="")  # remove mapping

        return AttachDetachResponse(
            subscriber=req.subscriber, bng=req.bng, ip_address=None, session_status="inactive", bng_active_sessions=active
        )
    except Exception as e:
        logger.exception("Detach failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
