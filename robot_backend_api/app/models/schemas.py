from typing import List, Optional
from pydantic import BaseModel, Field


class SubscribersByBngRequest(BaseModel):
    bng: str = Field(..., description="Thing ID of the BNG.")


class SubscribersByBngResponse(BaseModel):
    subscribers: List[str] = Field(..., description="List of subscriber thingIds served by the BNG.")


class AttachRequest(BaseModel):
    subscriber: str = Field(..., description="Subscriber thingId")
    bng: str = Field(..., description="BNG thingId")
    subnet: str = Field(..., description="Subnet twin id or CIDR string to allocate IP from")
    requested_ip: Optional[str] = Field(None, description="Optional requested IP")
    cidr: Optional[str] = Field(None, description="Optional explicit CIDR if subnet argument is a name or thingId")


class DetachRequest(BaseModel):
    subscriber: str = Field(..., description="Subscriber thingId")
    bng: str = Field(..., description="BNG thingId")


class AttachDetachResponse(BaseModel):
    subscriber: str
    bng: str
    ip_address: Optional[str] = None
    session_status: str
    bng_active_sessions: int


class BngKpiUpdateRequest(BaseModel):
    bng: str = Field(..., description="BNG thingId")
    cpu: Optional[int] = Field(None, description="CPU percent")
    mem_pct: Optional[int] = Field(None, description="Memory percent")
    active_sessions: Optional[int] = Field(None, description="Active session count override")


class BngKpiResponse(BaseModel):
    bng: str
    cpu: int
    mem_pct: int
    active_sessions: int


class BngAlertRequest(BaseModel):
    bng: str = Field(..., description="BNG thingId")
    alert: str = Field(..., description="Alert text")


class BngRecommendationRequest(BaseModel):
    bng: str = Field(..., description="BNG thingId")
    recommendation: str = Field(..., description="Recommendation text")


class RebalanceRequest(BaseModel):
    from_bng: str = Field(..., description="Source BNG")
    to_bng: str = Field(..., description="Destination BNG")
    count: int = Field(..., ge=1, description="Number of subscribers to move")
    to_subnet: str = Field(..., description="Subnet twin id or CIDR for destination allocation")
    cidr: Optional[str] = Field(None, description="Optional explicit CIDR if to_subnet is not CIDR")


class RebalanceResponse(BaseModel):
    moved: List[str] = Field(..., description="List of subscriber IDs moved")
    from_bng_sessions: int
    to_bng_sessions: int
