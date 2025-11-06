import logging
from fastapi import APIRouter, HTTPException, Query

from ..clients.ditto_client import get_ditto_client, DittoError
from ..models.schemas import (
    BngKpiUpdateRequest,
    BngKpiResponse,
    BngAlertRequest,
    BngRecommendationRequest,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/bng", tags=["BNG"])


# PUBLIC_INTERFACE
@router.get(
    "/kpis",
    response_model=BngKpiResponse,
    summary="Get BNG KPIs",
    description="Returns CPU, memory percent and active session count for the BNG.",
)
def get_kpis(bng: str = Query(..., description="BNG thingId")) -> BngKpiResponse:
    """Return BNG KPIs from Ditto state feature."""
    try:
        k = get_ditto_client().get_bng_kpis(bng)
        return BngKpiResponse(bng=bng, cpu=int(k["cpu"]), mem_pct=int(k["mem_pct"]), active_sessions=int(k["active_sessions"]))
    except Exception as e:
        logger.exception("Get KPIs failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# PUBLIC_INTERFACE
@router.post(
    "/update-kpis",
    response_model=BngKpiResponse,
    summary="Update BNG KPIs",
    description="Updates BNG KPIs in Ditto 'state' feature.",
)
def update_kpis(req: BngKpiUpdateRequest) -> BngKpiResponse:
    """Update BNG KPIs."""
    try:
        updated = get_ditto_client().update_bng_kpis(req.bng, cpu=req.cpu, mem_pct=req.mem_pct, active_sessions=req.active_sessions)
        props = updated.get("properties", {})
        return BngKpiResponse(
            bng=req.bng,
            cpu=int(props.get("cpu", 0)),
            mem_pct=int(props.get("mem_pct", 0)),
            active_sessions=int(props.get("active_sessions", 0)),
        )
    except DittoError as e:
        logger.warning("Ditto not reachable: %s", e)
        raise HTTPException(status_code=502, detail="Ditto not reachable or failed")
    except Exception as e:
        logger.exception("Update KPIs failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# PUBLIC_INTERFACE
@router.post(
    "/alerts",
    summary="Append BNG alert",
    description="Appends an alert to the BNG 'alerts' feature in Ditto.",
)
def add_alert(req: BngAlertRequest):
    """Append an alert string to Ditto."""
    try:
        feature = get_ditto_client().append_alert(req.bng, req.alert)
        return {"status": "ok", "alerts": feature.get("properties", {}).get("alerts", [])}
    except DittoError as e:
        logger.warning("Ditto not reachable for alert: %s", e)
        raise HTTPException(status_code=502, detail="Ditto not reachable or failed")
    except Exception as e:
        logger.exception("Add alert failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


# PUBLIC_INTERFACE
@router.post(
    "/recommendations",
    summary="Append BNG recommendation",
    description="Appends a recommendation to the BNG 'alerts' feature in Ditto.",
)
def add_recommendation(req: BngRecommendationRequest):
    """Append a recommendation string to Ditto."""
    try:
        feature = get_ditto_client().append_recommendation(req.bng, req.recommendation)
        return {"status": "ok", "recommendations": feature.get("properties", {}).get("recommendations", [])}
    except DittoError as e:
        logger.warning("Ditto not reachable for recommendation: %s", e)
        raise HTTPException(status_code=502, detail="Ditto not reachable or failed")
    except Exception as e:
        logger.exception("Add recommendation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))
