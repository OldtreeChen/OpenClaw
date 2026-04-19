from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class SearchRequest(BaseModel):
    query: str = Field(..., description="Keyword for restaurant search")
    location: str = Field(..., description="City or area text, ex: Taipei")
    party_size: int = Field(..., ge=1, le=20)
    dining_time: Optional[str] = Field(default=None, description="ISO 8601 datetime string")
    cuisine_type: Optional[str] = None
    cuisine_tag: Optional[str] = None
    must_have_terms: list[str] = Field(default_factory=list)
    preferred_terms: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)
    budget_level: Optional[int] = Field(default=None, ge=1, le=4)
    limit: int = Field(default=5, ge=1, le=10)


class Restaurant(BaseModel):
    place_id: str
    name: str
    rating: Optional[float] = None
    user_rating_count: Optional[int] = None
    price_level: Optional[int] = None
    formatted_address: Optional[str] = None
    google_maps_uri: Optional[str] = None
    website_uri: Optional[str] = None
    phone_number: Optional[str] = None
    open_now: Optional[bool] = None
    reservable: Optional[bool] = None


class SearchResponse(BaseModel):
    restaurants: list[Restaurant]


class ReservationLinkRequest(BaseModel):
    place_id: str
    website_uri: Optional[str] = None
    google_maps_uri: Optional[str] = None


class ReservationLinkResponse(BaseModel):
    reservation_platform: str
    reservation_url: str
    note: Optional[str] = None


class AssistedReservationRequest(BaseModel):
    restaurant_name: str
    reservation_time: str = Field(..., description="ISO 8601 datetime string")
    party_size: int = Field(..., ge=1, le=20)
    contact_name: str
    contact_phone: str
    website_uri: Optional[str] = None
    google_maps_uri: Optional[str] = None
    note: Optional[str] = None


class AssistedReservationOption(BaseModel):
    platform: str
    url: str
    label: str


class AssistedReservationResponse(BaseModel):
    primary_option: AssistedReservationOption
    fallback_options: list[AssistedReservationOption]
    booking_summary_text: str
    steps: list[str]


class AvailabilityProbeItem(BaseModel):
    restaurant_name: str
    party_size: int = Field(..., ge=1, le=20)
    reservation_date: str = Field(..., description="YYYY-MM-DD")
    preferred_time: Optional[str] = Field(default=None, description="HH:MM")
    website_uri: Optional[str] = None
    google_maps_uri: Optional[str] = None


class AvailabilityProbeRequest(BaseModel):
    items: list[AvailabilityProbeItem] = Field(..., min_length=1, max_length=100)
    max_parallel: int = Field(default=3, ge=1, le=10)
    probe_timeout_sec: int = Field(default=12, ge=3, le=45)


class AvailabilityProbeResult(BaseModel):
    restaurant_name: str
    platform: str
    status: Literal["available", "unavailable", "unknown", "fallback", "error"]
    available_times: list[str]
    reason: Optional[str] = None
    primary_option: Optional[AssistedReservationOption] = None
    fallback_options: list[AssistedReservationOption] = Field(default_factory=list)


class AvailabilityProbeResponse(BaseModel):
    total: int
    available_count: int
    fallback_count: int
    unknown_count: int
    results: list[AvailabilityProbeResult]


class SearchAndProbeRequest(BaseModel):
    message: str
    location: str = "台北市"
    party_size: int = Field(default=2, ge=1, le=20)
    reservation_date: Optional[str] = Field(default=None, description="YYYY-MM-DD")
    preferred_time: Optional[str] = Field(default=None, description="HH:MM")
    cuisine_type: Optional[str] = None
    must_have_terms: list[str] = Field(default_factory=list)
    preferred_terms: list[str] = Field(default_factory=list)
    avoid_terms: list[str] = Field(default_factory=list)
    budget_level: Optional[int] = Field(default=None, ge=1, le=4)
    limit: int = Field(default=5, ge=1, le=10)
    max_parallel: int = Field(default=3, ge=1, le=10)
    probe_timeout_sec: int = Field(default=10, ge=3, le=45)


class SearchAndProbeItem(BaseModel):
    place_id: str
    name: str
    rating: Optional[float] = None
    address: Optional[str] = None
    website_uri: Optional[str] = None
    google_maps_uri: Optional[str] = None
    platform: str
    reservation_platform: Optional[str] = None
    reservation_url: Optional[str] = None
    availability_status: Literal["available", "unavailable", "unknown", "fallback", "error"]
    available_times: list[str]
    primary_option: Optional[AssistedReservationOption] = None
    fallback_options: list[AssistedReservationOption] = Field(default_factory=list)


class SearchAndProbeResponse(BaseModel):
    query: str
    location: str
    party_size: int
    reservation_date: str
    preferred_time: Optional[str] = None
    results: list[SearchAndProbeItem]


class LineWebhookRequest(BaseModel):
    user_id: str
    message: str
    location: str = "台北市"
    party_size: int = Field(default=2, ge=1, le=20)
    reservation_date: Optional[str] = None
    preferred_time: Optional[str] = None
    limit: int = Field(default=5, ge=1, le=10)


class LineAction(BaseModel):
    label: str
    url: str


class BookingIntent(BaseModel):
    restaurant_name: str
    provider: str
    url: str
    party_size: int = Field(..., ge=1, le=20)
    reservation_date: str = Field(..., description="YYYY-MM-DD")
    preferred_time: Optional[str] = Field(default=None, description="HH:MM")
    availability_status: Literal["available", "unavailable", "unknown", "fallback", "error"]
    available_times: list[str] = Field(default_factory=list)
    booking_summary_text: str


class LineWebhookResponse(BaseModel):
    reply_text: str
    actions: list[LineAction] = Field(default_factory=list)
    booking_intents: list[BookingIntent] = Field(default_factory=list)
    search_and_probe: Optional[SearchAndProbeResponse] = None


class BookingCreateRequest(BaseModel):
    provider: Literal["inline", "eztable"]
    restaurant_name: str
    reservation_time: str = Field(..., description="ISO 8601 datetime string")
    party_size: int = Field(..., ge=1, le=20)
    contact_name: str
    contact_phone: str
    note: Optional[str] = None
    dry_run: bool = True
    provider_payload: Optional[dict[str, Any]] = None


class BookingCreateResponse(BaseModel):
    provider: Literal["inline", "eztable"]
    reservation_id: str
    status: Literal["confirmed", "cancelled", "simulated", "pending"]
    message: str


class BookingCancelRequest(BaseModel):
    provider: Literal["inline", "eztable"]
    reservation_id: str
    dry_run: bool = True
    provider_payload: Optional[dict[str, Any]] = None


class BookingCancelResponse(BaseModel):
    provider: Literal["inline", "eztable"]
    reservation_id: str
    status: Literal["cancelled", "simulated", "not_found", "pending"]
    message: str
