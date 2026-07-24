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

### Phase 6: Dashboard Analytics & Conversations (Next)
- Analytics dashboard implementation.
- Live view of ongoing AI conversations.

### Phase 7: E2E Integration & Polish
- Full system testing.
- UI/UX polish and micro-animations.

### Phase 8: Deployment
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
