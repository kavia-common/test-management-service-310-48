import logging
from fastapi import APIRouter, HTTPException
from ..models.schemas import SubscribersByBngRequest, SubscribersByBngResponse
from ..clients.graph_client import get_graph_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/graph", tags=["Graph APIs"])


# PUBLIC_INTERFACE
@router.post(
    "/subscribers-by-bng",
    response_model=SubscribersByBngResponse,
    summary="Get subscribers served by BNG",
    description="Returns list of subscriber thingIds for the specified BNG using Graph or fallback.",
)
def subscribers_by_bng(req: SubscribersByBngRequest) -> SubscribersByBngResponse:
    """Return subscribers list for a BNG."""
    try:
        subs = get_graph_client().subscribers_by_bng(req.bng)
        return SubscribersByBngResponse(subscribers=subs)
    except Exception as e:
        logger.exception("Failed to get subscribers by BNG: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
