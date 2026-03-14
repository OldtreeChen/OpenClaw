import { restaurants } from "../data/restaurants.js";

const reservations = [];

function normalize(text) {
  return String(text || "").trim().toLowerCase();
}

export function searchRestaurants({
  city,
  area,
  cuisine,
  date,
  partySize,
  budget,
  keywords
}) {
  const requestedKeywords = Array.isArray(keywords)
    ? keywords.map(normalize).filter(Boolean)
    : [];

  const results = restaurants
    .filter((restaurant) => {
      if (city && normalize(restaurant.city) !== normalize(city)) {
        return false;
      }

      if (area && normalize(restaurant.area) !== normalize(area)) {
        return false;
      }

      if (cuisine && !normalize(restaurant.cuisine).includes(normalize(cuisine))) {
        return false;
      }

      if (budget && normalize(restaurant.priceLevel) !== normalize(budget)) {
        return false;
      }

      if (requestedKeywords.length > 0) {
        const haystack = [
          restaurant.name,
          restaurant.cuisine,
          restaurant.area,
          ...restaurant.tags
        ]
          .map(normalize)
          .join(" ");

        if (!requestedKeywords.every((keyword) => haystack.includes(keyword))) {
          return false;
        }
      }

      if (date) {
        const slots = restaurant.availability[date] || [];
        if (slots.length === 0) {
          return false;
        }
      }

      if (partySize && partySize > 8 && !restaurant.tags.includes("private-room")) {
        return false;
      }

      return true;
    })
    .sort((left, right) => right.rating - left.rating)
    .slice(0, 5)
    .map((restaurant) => ({
      id: restaurant.id,
      name: restaurant.name,
      city: restaurant.city,
      area: restaurant.area,
      cuisine: restaurant.cuisine,
      priceLevel: restaurant.priceLevel,
      rating: restaurant.rating,
      tags: restaurant.tags,
      address: restaurant.address,
      reservationChannels: restaurant.reservationChannels,
      reservationUrl: restaurant.reservationUrl,
      availableTimes: date ? restaurant.availability[date] || [] : []
    }));

  return {
    count: results.length,
    results
  };
}

export function checkAvailability({ restaurantId, date, time, partySize }) {
  const restaurant = restaurants.find((item) => item.id === restaurantId);
  if (!restaurant) {
    return { ok: false, error: "Restaurant not found." };
  }

  if (!date) {
    return { ok: false, error: "date is required." };
  }

  const slots = restaurant.availability[date] || [];
  const exactMatch = time ? slots.includes(time) : slots.length > 0;

  return {
    ok: exactMatch,
    restaurant: restaurant.name,
    date,
    requestedTime: time || null,
    partySize: partySize || null,
    availableTimes: slots
  };
}

export function createReservationRequest({
  restaurantId,
  date,
  time,
  partySize,
  customerName,
  phone,
  notes
}) {
  const restaurant = restaurants.find((item) => item.id === restaurantId);
  if (!restaurant) {
    return { ok: false, error: "Restaurant not found." };
  }

  if (!date || !time || !partySize || !customerName || !phone) {
    return {
      ok: false,
      error: "restaurantId, date, time, partySize, customerName, and phone are required."
    };
  }

  const slots = restaurant.availability[date] || [];
  if (!slots.includes(time)) {
    return {
      ok: false,
      error: "Requested time is unavailable.",
      availableTimes: slots
    };
  }

  const reservation = {
    id: `resv_${reservations.length + 1}`,
    restaurantId,
    restaurant: restaurant.name,
    date,
    time,
    partySize,
    customerName,
    phone,
    notes: notes || "",
    status: "pending_confirmation",
    channel: restaurant.reservationChannels[0]
  };

  reservations.push(reservation);

  return {
    ok: true,
    reservation
  };
}

export function listReservations() {
  return reservations;
}
