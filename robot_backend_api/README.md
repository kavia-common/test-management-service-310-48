# Robot Backend API - BNG Efficiency

This backend extends the FastAPI service with endpoints to support BNG efficiency tests and load balancing workflows. It integrates with Eclipse Ditto (digital twins) and optionally a Graph API (Neo4j). When Graph or Ditto are not reachable, robust in-memory fallbacks are provided (configurable).

## Run

The FastAPI app entrypoint remains `robot_backend_api/src/api/main.py`, which re-exports the full-featured app from `robot_backend_api/app/main.py`.

- Install requirements (already specified in `requirements.txt`)
- Start with uvicorn:
  uvicorn robot_backend_api.src.api.main:app --host 0.0.0.0 --port 3001 --reload

OpenAPI docs: http://localhost:3001/docs

## Environment Configuration

Create a `.env` from `.env.example` and adjust:

- DITTO_BASE_URL: Base URL for Ditto REST v2 (e.g., http://localhost:8080/api/2)
- DITTO_AUTH: Optional "Basic <token>" Authorization header
- DITTO_USERNAME / DITTO_PASSWORD: Alternative to DITTO_AUTH
- GRAPH_API_BASE_URL: Optional base URL for Graph service. If omitted, in-memory topology is used.
- GRAPH_AUTH: Optional bearer token for Graph
- HTTP_TIMEOUT_SECONDS, HTTP_RETRIES: HTTP client tuning
- ENABLE_INMEMORY_GRAPH: true/false to enable fallback
- ENABLE_INMEMORY_DITTO: true/false to simulate Ditto locally

Never hardcode secrets; provide via environment variables.

## Endpoints

- POST /api/graph/subscribers-by-bng
  Body: {"bng":"<thingId>"}
  Resp: {"subscribers":[thingIds...]}

- POST /api/subscribers/attach
  Body: {"subscriber":"<thingId>", "bng":"<thingId>", "subnet":"<subnetIdOrCIDR>", "cidr":"optional"}
  Behavior: Allocates IP, sets subscriber session active in Ditto, increments BNG active_sessions, updates Graph mapping.
  Resp: {subscriber, bng, ip_address, session_status, bng_active_sessions}

- POST /api/subscribers/detach
  Body: {"subscriber":"<thingId>", "bng":"<thingId>"}
  Behavior: Sets session inactive, decrements BNG active_sessions, updates Graph.
  Resp: {subscriber, bng, session_status, bng_active_sessions}

- POST /api/bng/update-kpis
  Body: {"bng":"<thingId>", "cpu":int?, "mem_pct":int?, "active_sessions":int?}
  Behavior: Updates Ditto state feature.
  Resp: {bng, cpu, mem_pct, active_sessions}

- GET /api/bng/kpis?bng=<thingId>
  Returns {bng, cpu, mem_pct, active_sessions}

- POST /api/bng/alerts
  Body: {"bng":"<thingId>", "alert":"..."}
  Behavior: Ensures alerts feature exists and appends alert.

- POST /api/bng/recommendations
  Body: {"bng":"<thingId>", "recommendation":"..."}
  Behavior: Appends recommendation similarly.

- POST /api/load/rebalance
  Body: {"from_bng":"...", "to_bng":"...", "count":N, "to_subnet":"...", "cidr":"optional"}
  Behavior: Moves N subscribers: updates Ditto session/IP and Graph mapping, adjusts session counters.
  Resp: {moved:[], from_bng_sessions:int, to_bng_sessions:int}

## IP Allocation

The allocator uses a deterministic strategy:
- Hash subscriberId to a host index within the provided subnet CIDR.
- Supports optional requested_ip.

See: `app/services/ip_allocator.py`.

## Robot Framework Resource

A convenience resource is provided at `robot/resources/api_keywords.resource`, wrapping the endpoints with RequestsLibrary keywords.

Usage in your Robot test:
- Resource    robot/resources/api_keywords.resource
- Create API Session
- ${subs}=    Get Subscribers By BNG    LEXI-NDT:BNG-Chennai-1
- ${res}=     Attach Subscriber    LEXI-NDT:Subscriber-SUB4    LEXI-NDT:BNG-Chennai-1    100.64.1.0/24
- ${kpi}=     Get BNG KPIs    LEXI-NDT:BNG-Chennai-1
- ${reb}=     Rebalance Load    LEXI-NDT:BNG-Chennai-1    LEXI-NDT:BNG-Bangalore-1    1    100.65.1.0/24

## Notes

- For Ditto unavailability, endpoints return HTTP 502 for alert/recommendation operations.
- In-memory Graph fallback is seeded with the sample topology from the user's description.
- Extend GraphClient with real API paths if available later (see TODOs).
