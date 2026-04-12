from __future__ import annotations

from fastapi import BackgroundTasks, FastAPI, Header, HTTPException, Request

from app.assisted import prepare_assisted_reservation
from app.availability import probe_availability_batch
from app.booking import cancel_booking, create_booking
from app.line_integration import _extract_text_events, handle_line_webhook, verify_line_signature
from app.models import (
    AssistedReservationRequest,
    AssistedReservationResponse,
    AvailabilityProbeRequest,
    AvailabilityProbeResponse,
    BookingCancelRequest,
    BookingCancelResponse,
    BookingCreateRequest,
    BookingCreateResponse,
    LineWebhookRequest,
    LineWebhookResponse,
    ReservationLinkRequest,
    ReservationLinkResponse,
    SearchAndProbeRequest,
    SearchAndProbeResponse,
    SearchRequest,
    SearchResponse,
)
from app.orchestrator import run_line_query, run_search_and_probe
from app.reservation import get_reservation_link
from app.services import search_restaurants

app = FastAPI(title="Restaurant Agent MVP", version="0.5.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/search", response_model=SearchResponse)
async def search(payload: SearchRequest) -> SearchResponse:
    try:
        restaurants = await search_restaurants(payload)
    except ValueError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Google Places request failed: {exc}") from exc

    return SearchResponse(restaurants=restaurants)


@app.post("/agent/search-and-probe", response_model=SearchAndProbeResponse)
async def agent_search_and_probe(payload: SearchAndProbeRequest) -> SearchAndProbeResponse:
    try:
        return await run_search_and_probe(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/line/openclaw-query", response_model=LineWebhookResponse)
async def line_openclaw_query(payload: LineWebhookRequest) -> LineWebhookResponse:
    try:
        return await run_line_query(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/line/webhook")
async def line_webhook(
    background_tasks: BackgroundTasks,
    request: Request,
    x_line_signature: str | None = Header(default=None),
) -> dict[str, int | str]:
    body = await request.body()
    if not verify_line_signature(body, x_line_signature):
        raise HTTPException(status_code=401, detail="Invalid LINE signature.")

    payload = await request.json()
    queued = len(_extract_text_events(payload))
    background_tasks.add_task(handle_line_webhook, payload)
    return {"status": "ok", "handled": queued}


@app.post("/reserve-link", response_model=ReservationLinkResponse)
async def reserve_link(payload: ReservationLinkRequest) -> ReservationLinkResponse:
    platform, url, note = get_reservation_link(payload.website_uri, payload.google_maps_uri)
    if not url:
        raise HTTPException(status_code=404, detail="No reservation URL found.")
    return ReservationLinkResponse(reservation_platform=platform, reservation_url=url, note=note)


@app.post("/availability/probe-batch", response_model=AvailabilityProbeResponse)
async def availability_probe_batch(payload: AvailabilityProbeRequest) -> AvailabilityProbeResponse:
    try:
        return await probe_availability_batch(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/booking/assist", response_model=AssistedReservationResponse)
async def booking_assist(payload: AssistedReservationRequest) -> AssistedReservationResponse:
    try:
        return prepare_assisted_reservation(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/booking/create", response_model=BookingCreateResponse)
async def booking_create(payload: BookingCreateRequest) -> BookingCreateResponse:
    try:
        return create_booking(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/booking/cancel", response_model=BookingCancelResponse)
async def booking_cancel(payload: BookingCancelRequest) -> BookingCancelResponse:
    try:
        return cancel_booking(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
