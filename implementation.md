# SMSOS v2 — Remaining Phases Implementation Plan

This document outlines the implementation plan for the remaining phases (Phases 3–8) of the SMSOS v2 project. Our immediate focus will be on **Phase 3: SMS Pipeline Implementation**.

## Open Questions

> [!IMPORTANT]
> **Gemini API Model**: Do you have a preference for which Gemini model to use for processing messages (e.g., `gemini-1.5-flash` for lower latency or `gemini-1.5-pro` for complex reasoning)? We will default to `gemini-1.5-flash` for optimal speed in a chat context.

> [!WARNING]
> **Twilio Phone Numbers**: The system currently defaults to the Twilio Sandbox number (`+14155238886`). For production, we will need to handle per-business Twilio numbers or a central verified WhatsApp sender. We will assume a single central number for now based on the previous scope.

## Phase Overview

### Phase 3: SMS Pipeline Implementation (Completed)
- [x] Integrated Twilio WhatsApp Webhook (`POST /api/v1/webhooks/twilio`).
- [x] Integrated Google GenAI (`google-genai` / Gemini) for multi-lingual intent parsing & response generation (English, Tamil, Tanglish).
- [x] Built core messaging pipeline, state machine, order & reservation automated creation logic.
- [x] Unit & Integration tests passing (100%).

### Phase 4: Dashboard Foundation (Completed)
- [x] Set up Vanilla JS SPA frontend structure in `apps/dashboard/`.
- [x] Built glassmorphism design system in `apps/dashboard/css/styles.css` with dark theme, smooth micro-animations, and Google Fonts (Inter, Outfit).
- [x] Implemented JWT authentication flow, state persistence, session expiry, and client routing.

### Phase 5: Dashboard Core Features (Completed)
- [x] Implemented Orders management view (`#orders`), status update actions (Ready/Completed/Cancelled), revenue stats, and manual order creation.
- [x] Implemented Catalog management view (`#catalog`), stock status badges, and item creation modal.
- [x] Implemented Customer directory view (`#customers`) and customer creation modal.
- [x] Implemented Reservations management view (`#reservations`) and reservation creation modal.

### Phase 6: Dashboard Analytics & Conversations (Completed)
- [x] Implemented Analytics dashboard view (`#analytics`) with total revenue, active orders, customer metrics, inventory health, and order fulfillment breakdown progress charts.
- [x] Implemented AI WhatsApp Conversations live chat drawer (`#conversations`) with interactive thread selection, message direction indicators (inbound/outbound bubbles), timestamps, and status checks.

### Phase 7: E2E Integration & Polish (Completed)
- [x] Full end-to-end integration and API verification.
- [x] UI/UX polish with glassmorphism panels, CSS gradients, dynamic animations, and responsive sidebars.
- [x] Automated test suite passing 100% across unit and integration tests.

### Phase 8: Deployment (Next)
- Containerization (Docker).
- Production deployment preparations.

---

## Proposed Changes for Phase 3

### Dependencies
#### [MODIFY] pyproject.toml
- Add `google-genai` (or `google-generativeai`) to support Gemini AI.
- Run `pip install google-generativeai` (and freeze to dependencies).

### Core AI & SMS Services
#### [NEW] apps/api/app/core/ai.py
- Implements `GeminiService` class.
- Handles initialization of the GenerativeModel.
- Provides methods for intent classification and generating AI replies.
- Enforces system prompts instructing the AI on the business catalog and policies, capable of handling English, Tamil, and Tanglish.

#### [NEW] apps/api/app/core/sms.py
- Implements `TwilioService` class.
- Handles sending outbound messages via the Twilio REST API.
- Handles validating inbound Twilio Webhook signatures.

### Webhook API Layer
#### [NEW] apps/api/app/api/v1/webhooks.py
- Exposes `POST /twilio` endpoint.
- Validates the Twilio signature.
- Parses the inbound `From`, `Body`, and `MessageSid`.
- Delegates to the `messaging.py` module via a background task (to respond to Twilio quickly and avoid timeouts).

#### [MODIFY] apps/api/app/api/v1/router.py
- Register the `webhooks.py` router.

### Messaging & Business Logic
#### [NEW] apps/api/app/modules/messaging.py
- **Inbound Processing**: Stores the raw message in `inbound_messages`.
- **State Management**: Retrieves or initializes `ConversationState`.
- **AI Orchestration**: Passes context to `GeminiService` to extract user intent.
- **Action Execution**:
  - If intent is "order", updates DB, creates an `Order`.
  - If intent is "catalog", fetches catalog items.
- **Response Generation**: Generates the final reply text via AI.
- **Outbound Processing**: Stores the reply in `outbound_messages` and dispatches it via `TwilioService`.

## Verification Plan

### Automated Tests
- `pytest apps/api/tests/integration/test_webhooks.py` to ensure Twilio payloads are processed properly.
- `pytest apps/api/tests/unit/test_ai.py` to mock Gemini and test intent parsing logic.

### Manual Verification
- Expose the local server using `ngrok` or similar.
- Configure the Twilio WhatsApp Sandbox webhook URL to point to the local server.
- Send test messages in English and Tanglish via WhatsApp to verify AI responses and DB state changes.

---

## [NEW] Live Order Status Context & Automatic Outbound Notifications Plan

### 1. Inbound Order Status Tracking (AI Context)
We will feed live order status into the Gemini prompt context so that when customers ask "Where is my order?" or check status, Gemini will know the exact status (e.g. pending, ready, completed, cancelled) and respond accurately.

#### [MODIFY] [messaging.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/modules/messaging.py)
- Query the database for the customer's last 3 orders (loading status, total amount, items, and creation date).
- Pass this order status list into `gemini_service.process_customer_message(...)`.

#### [MODIFY] [ai.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/core/ai.py)
- Accept the `order_context` parameter.
- Append a human-readable summary of the customer's recent orders directly into the Gemini prompt `system_instruction`.
- Direct the system prompt to use this context to answer status check queries (intent: `CHECK_STATUS`).

### 2. Outbound Status Notifications (Dashboard Trigger)
When the business owner updates an order status in the dashboard, the system will automatically send a push message (WhatsApp/SMS) notifying the customer.

#### [MODIFY] [orders.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/orders.py)
- In the `PUT /orders/{order_id}` handler:
  - If `req.status` is changed, retrieve the order and the customer's phone number.
  - Query the history (`inbound_messages` / `outbound_messages`) to detect if the customer's active channel is `whatsapp:` or `sms`.
  - Format a notification template based on the status (e.g., "Your order is ready", "Your order has been completed", etc.).
  - Send the notification message using `twilio_service.send_message`.
