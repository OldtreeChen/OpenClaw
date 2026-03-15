import test from "node:test";
import assert from "node:assert/strict";
import {
  checkAvailability,
  createReservationRequest,
  searchRestaurants
} from "../src/tools/restaurantService.js";

test("searchRestaurants filters by city and date", () => {
  const result = searchRestaurants({
    city: "Taipei",
    date: "2026-03-14"
  });

  assert.ok(result.count > 0);
  assert.equal(result.results.every((item) => item.city === "Taipei"), true);
  assert.equal(
    result.results.every((item) => item.availableTimes.length > 0),
    true
  );
});

test("checkAvailability returns available slots for a known restaurant", () => {
  const result = checkAvailability({
    restaurantId: "taipei-umami-grill",
    date: "2026-03-14"
  });

  assert.equal(result.ok, true);
  assert.ok(Array.isArray(result.availableTimes));
  assert.ok(result.availableTimes.includes("18:00"));
});

test("createReservationRequest rejects unavailable times", () => {
  const result = createReservationRequest({
    restaurantId: "taipei-umami-grill",
    date: "2026-03-14",
    time: "22:30",
    partySize: 2,
    customerName: "Tester",
    phone: "0912345678"
  });

  assert.equal(result.ok, false);
  assert.equal(result.error, "Requested time is unavailable.");
});
