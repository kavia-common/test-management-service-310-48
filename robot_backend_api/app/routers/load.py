import logging
from fastapi import APIRouter, HTTPException

from ..clients.graph_client import get_graph_client
from ..clients.ditto_client import get_ditto_client
from ..models.schemas import RebalanceRequest, RebalanceResponse
from ..services.ip_allocator import allocate_ip

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/load", tags=["Load Balancing"])


# PUBLIC_INTERFACE
@router.post(
    "/rebalance",
    response_model=RebalanceResponse,
    summary="Rebalance subscribers between BNGs",
    description="Moves N subscribers from from_bng to to_bng, allocating IPs on the destination subnet and updating Ditto KPIs.",
)
def rebalance(req: RebalanceRequest) -> RebalanceResponse:
    """Rebalance N subscribers from one BNG to another."""
    ditto = get_ditto_client()
    graph = get_graph_client()

    try:
        candidates = graph.subscribers_by_bng(req.from_bng)
        to_move = candidates[: req.count]
        moved = []

        # decrement source sessions
        from_k = ditto.get_bng_kpis(req.from_bng)
        from_active = max(0, int(from_k.get("active_sessions", 0)) - len(to_move))
        ditto.update_bng_kpis(req.from_bng, active_sessions=from_active)

        # increment destination sessions based on actual moved
        to_k = ditto.get_bng_kpis(req.to_bng)
        to_active = int(to_k.get("active_sessions", 0)) + len(to_move)
        ditto.update_bng_kpis(req.to_bng, active_sessions=to_active)

        cidr = req.cidr if req.cidr else (req.to_subnet if "/" in req.to_subnet else "100.64.1.0/24")

        for sub in to_move:
            # allocate new IP for destination
            ip = allocate_ip(cidr, sub)
            ditto.set_subscriber_session(sub, status="active", ip_address=ip)
            graph.reassign_subscriber(sub, from_bng=req.from_bng, to_bng=req.to_bng)
            moved.append(sub)

        # return updated sessions
        from_final = ditto.get_bng_kpis(req.from_bng).get("active_sessions", from_active)
        to_final = ditto.get_bng_kpis(req.to_bng).get("active_sessions", to_active)

        return RebalanceResponse(moved=moved, from_bng_sessions=int(from_final), to_bng_sessions=int(to_final))
    except Exception as e:
        logger.exception("Rebalance failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
