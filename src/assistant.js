import OpenAI from "openai";
import {
  searchRestaurants,
  checkAvailability,
  createReservationRequest,
  listReservations
} from "./tools/restaurantService.js";

const sessions = new Map();

const systemPrompt = `
You are OpenClaw, a restaurant concierge for Traditional Chinese users.
Your job is to help users discover restaurants and prepare reservation requests.

Rules:
- Reply in Traditional Chinese unless the user clearly uses another language.
- Be concise and practical.
- If the user wants restaurant suggestions, call search_restaurants before recommending specific venues.
- If the user wants to reserve, first make sure you know restaurant, date, time, party size, customer name, and phone.
- Before submitting a reservation request, check availability when needed.
- Do not claim a booking is fully confirmed. If create_reservation_request succeeds, explain that the request is created and is waiting for final confirmation or manual platform integration.
- If user requirements are missing, ask for the missing fields clearly.
`.trim();

const tools = [
  {
    type: "function",
    name: "search_restaurants",
    description: "Search restaurants by city, area, cuisine, budget, date, party size, or keywords.",
    strict: true,
    parameters: {
      type: "object",
      properties: {
        city: { type: "string" },
        area: { type: "string" },
        cuisine: { type: "string" },
        date: { type: "string", description: "Date in YYYY-MM-DD." },
        partySize: { type: "number" },
        budget: {
          type: "string",
          description: "Expected values like $, $$, or $$$."
        },
        keywords: {
          type: "array",
          items: { type: "string" }
        }
      },
      additionalProperties: false
    }
  },
  {
    type: "function",
    name: "check_availability",
    description: "Check if a restaurant has available times for a date and optional time.",
    strict: true,
    parameters: {
      type: "object",
      properties: {
        restaurantId: { type: "string" },
        date: { type: "string", description: "Date in YYYY-MM-DD." },
        time: { type: "string", description: "Time in HH:MM." },
        partySize: { type: "number" }
      },
      required: ["restaurantId", "date"],
      additionalProperties: false
    }
  },
  {
    type: "function",
    name: "create_reservation_request",
    description: "Create a reservation request after required details are collected.",
    strict: true,
    parameters: {
      type: "object",
      properties: {
        restaurantId: { type: "string" },
        date: { type: "string", description: "Date in YYYY-MM-DD." },
        time: { type: "string", description: "Time in HH:MM." },
        partySize: { type: "number" },
        customerName: { type: "string" },
        phone: { type: "string" },
        notes: { type: "string" }
      },
      required: ["restaurantId", "date", "time", "partySize", "customerName", "phone"],
      additionalProperties: false
    }
  },
  {
    type: "function",
    name: "list_reservations",
    description: "List all reservation requests created in the current demo server.",
    strict: true,
    parameters: {
      type: "object",
      properties: {},
      additionalProperties: false
    }
  }
];

function runTool(name, args) {
  switch (name) {
    case "search_restaurants":
      return searchRestaurants(args);
    case "check_availability":
      return checkAvailability(args);
    case "create_reservation_request":
      return createReservationRequest(args);
    case "list_reservations":
      return listReservations();
    default:
      return { ok: false, error: `Unknown tool: ${name}` };
  }
}

function getTextFromResponse(response) {
  if (response.output_text) {
    return response.output_text;
  }

  const texts = [];
  for (const item of response.output || []) {
    if (item.type !== "message" || !Array.isArray(item.content)) {
      continue;
    }

    for (const content of item.content) {
      if (content.type === "output_text" && content.text) {
        texts.push(content.text);
      }
    }
  }

  return texts.join("\n").trim();
}

function getClient() {
  if (!process.env.OPENAI_API_KEY) {
    throw new Error("OPENAI_API_KEY is not set.");
  }

  return new OpenAI({
    apiKey: process.env.OPENAI_API_KEY
  });
}

export async function chatWithAssistant({ sessionId, message }) {
  const client = getClient();
  const session = sessions.get(sessionId) || {};

  let response = await client.responses.create({
    model: process.env.MODEL || "gpt-5",
    instructions: systemPrompt,
    previous_response_id: session.previousResponseId,
    input: [{ role: "user", content: [{ type: "input_text", text: message }] }],
    tools
  });

  while (true) {
    const functionCalls = (response.output || []).filter(
      (item) => item.type === "function_call"
    );

    if (functionCalls.length === 0) {
      break;
    }

    const toolOutputs = functionCalls.map((call) => {
      const args = JSON.parse(call.arguments || "{}");
      const result = runTool(call.name, args);

      return {
        type: "function_call_output",
        call_id: call.call_id,
        output: JSON.stringify(result)
      };
    });

    response = await client.responses.create({
      model: process.env.MODEL || "gpt-5",
      instructions: systemPrompt,
      previous_response_id: response.id,
      input: toolOutputs,
      tools
    });
  }

  sessions.set(sessionId, {
    previousResponseId: response.id
  });

  return {
    sessionId,
    responseId: response.id,
    text: getTextFromResponse(response)
  };
}
