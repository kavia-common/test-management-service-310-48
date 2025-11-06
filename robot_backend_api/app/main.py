import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.graph import router as graph_router
from .routers.subscribers import router as subs_router
from .routers.bng import router as bng_router
from .routers.load import router as load_router

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="Robot Backend API - BNG Efficiency",
    description="APIs to simulate BNG load, manage subscriber sessions, update Ditto twins, and interact with Graph.",
    version="1.0.0",
    openapi_tags=[
        {"name": "Graph APIs", "description": "Endpoints interacting with Graph (Neo4j) or in-memory topology."},
        {"name": "Subscribers", "description": "Attach/Detach subscriber workflows."},
        {"name": "BNG", "description": "BNG KPI updates, alerts and recommendations."},
        {"name": "Load Balancing", "description": "Rebalancing subscribers across BNGs."},
    ],
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# PUBLIC_INTERFACE
@app.get("/", summary="Health Check", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {"message": "Healthy"}


# Register routers
app.include_router(graph_router)
app.include_router(subs_router)
app.include_router(bng_router)
app.include_router(load_router)
