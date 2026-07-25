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

---

## [NEW] Item Deletion & Shop Table Capacity Management Plan

### 1. Unified Delete Capabilities
Add full deletion support across backend API endpoints and frontend dashboard views for all core entities.

#### Backend API (`apps/api/app/api/v1/`)
- **[MODIFY] [catalog.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/catalog.py)**: Add `@router.delete("/catalog/{item_id}")`
- **[MODIFY] [reservations.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/reservations.py)**: Add `@router.delete("/reservations/{reservation_id}")`
- **[MODIFY] [orders.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/orders.py)**: Add `@router.delete("/orders/{order_id}")`
- **[MODIFY] [customers.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/customers.py)**: Add `@router.delete("/customers/{customer_id}")`

#### Frontend Dashboard (`apps/dashboard/js/app.js`)
- Add Delete buttons (red trash icons) with confirm prompts to:
  - Catalog items view (`deleteCatalogItem`)
  - Reservations table (`deleteReservation`)
  - Orders table (`deleteOrder`)
  - Customers table (`deleteCustomer`)

### 2. Shop Table Capacity Management
Allow business owners to specify and manage total available tables in their shop, and enforce table limits during reservations.

#### Backend API & Business Settings
- **[NEW] `apps/api/app/api/v1/business.py`**: Add `GET /api/v1/business/settings` and `PUT /api/v1/business/settings` to read/update `table_count` in `BusinessSettings`.
- **[MODIFY] `messaging.py` & `ai.py`**: Feed `table_count` into Gemini context to enforce table availability during AI table reservations.

#### Dashboard UI
- **[MODIFY] `apps/dashboard/js/app.js`**:
  - Add a **Shop Table Settings** header card on the **Reservations** page.
  - Include an editable input for `Total Available Tables` and a `Save Capacity` button.

---

## [NEW] Conversational Reservation Details Collection Plan

### Goal
Prevent blank or incomplete database reservation records by making the AI ask for missing details (such as date/time, party size, and customer name) before confirming and saving the reservation.

### Proposed Changes

#### 1. Gemini Schema Update (`apps/api/app/core/ai.py`)
- Update `IntentResult` model to include:
  - `reservation_date: Optional[str] = Field(default=None, description="Date of reservation, e.g. YYYY-MM-DD or today/tomorrow")`
  - `reservation_time: Optional[str] = Field(default=None, description="Time of reservation, e.g. HH:MM or 4 PM")`
  - `customer_name: Optional[str] = Field(default=None, description="Name of the customer for the table reservation")`
  - `is_reservation_complete: bool = Field(default=False, description="True ONLY if the customer has fully specified the reservation date, time, party size, and customer name")`
- Update the system instructions in `ai.py` to tell the model:
  - To check if the customer has specified the reservation date, time, number of guests, and booking customer name.
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

---

## [NEW] Item Deletion & Shop Table Capacity Management Plan

### 1. Unified Delete Capabilities
Add full deletion support across backend API endpoints and frontend dashboard views for all core entities.

#### Backend API (`apps/api/app/api/v1/`)
- **[MODIFY] [catalog.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/catalog.py)**: Add `@router.delete("/catalog/{item_id}")`
- **[MODIFY] [reservations.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/reservations.py)**: Add `@router.delete("/reservations/{reservation_id}")`
- **[MODIFY] [orders.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/orders.py)**: Add `@router.delete("/orders/{order_id}")`
- **[MODIFY] [customers.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/customers.py)**: Add `@router.delete("/customers/{customer_id}")`

#### Frontend Dashboard (`apps/dashboard/js/app.js`)
- Add Delete buttons (red trash icons) with confirm prompts to:
  - Catalog items view (`deleteCatalogItem`)
  - Reservations table (`deleteReservation`)
  - Orders table (`deleteOrder`)
  - Customers table (`deleteCustomer`)

### 2. Shop Table Capacity Management
Allow business owners to specify and manage total available tables in their shop, and enforce table limits during reservations.

#### Backend API & Business Settings
- **[NEW] `apps/api/app/api/v1/business.py`**: Add `GET /api/v1/business/settings` and `PUT /api/v1/business/settings` to read/update `table_count` in `BusinessSettings`.
- **[MODIFY] `messaging.py` & `ai.py`**: Feed `table_count` into Gemini context to enforce table availability during AI table reservations.

#### Dashboard UI
- **[MODIFY] `apps/dashboard/js/app.js`**:
  - Add a **Shop Table Settings** header card on the **Reservations** page.
  - Include an editable input for `Total Available Tables` and a `Save Capacity` button.

---

## [NEW] Conversational Reservation Details Collection Plan

### Goal
Prevent blank or incomplete database reservation records by making the AI ask for missing details (such as date/time, party size, and customer name) before confirming and saving the reservation.

### Proposed Changes

#### 1. Gemini Schema Update (`apps/api/app/core/ai.py`)
- Update `IntentResult` model to include:
  - `reservation_date: Optional[str] = Field(default=None, description="Date of reservation, e.g. YYYY-MM-DD or today/tomorrow")`
  - `reservation_time: Optional[str] = Field(default=None, description="Time of reservation, e.g. HH:MM or 4 PM")`
  - `customer_name: Optional[str] = Field(default=None, description="Name of the customer for the table reservation")`
  - `is_reservation_complete: bool = Field(default=False, description="True ONLY if the customer has fully specified the reservation date, time, party size, and customer name")`
- Update the system instructions in `ai.py` to tell the model:
  - To check if the customer has specified the reservation date, time, number of guests, and booking customer name.
  - If any required detail is missing, set `is_reservation_complete = False` and use `reply_text` to politely ask for the missing details in their language.
  - Set `is_reservation_complete = True` only when all reservation details are fully provided and confirmed.

#### 2. Messaging Handler Update (`apps/api/app/modules/messaging.py`)
- Check `ai_result.is_reservation_complete` when intent is `RESERVATION`.
- Only write to the `reservations` table and set `conv_state.state = "RESERVATION_CONFIRMED"` if `is_reservation_complete` is `True`.
- Parse the extracted `reservation_date` and `reservation_time` into a proper timezone-aware `datetime` object.
- Populate `customer_name` using `customer_name` from AI entities (defaulting to the customer's database name if not extracted).
- If `is_reservation_complete` is `False`, do not save any reservation record to the database, allowing the user to reply to the bot's question and provide the missing details.

---

## [NEW] Owner Signup, Onboarding & Profile Management Plan

### Goal
Allow new business owners to register, complete onboarding business details (Business Name, Phone Number, Location), view their dashboard, and manage their profile details in a top-right profile section.

### Proposed Changes

#### 1. Backend Schema & API Updates (`apps/api/app/`)
- **[MODIFY] [business.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/db/models/business.py)**: Add `location: Mapped[str | None] = mapped_column(String(255), nullable=True)` to `Business` model to capture store location.
- **[MODIFY] [auth.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/auth.py)**:
  - Add `POST /auth/signup` endpoint: Creates a new placeholder `Business` record and a `User` owner record.
  - Add `POST /auth/onboarding` endpoint: Requires auth, accepts `business_name`, `phone_number`, and `location` to complete business profile.
  - Add `GET /auth/profile` and `PUT /auth/profile` endpoints: Fetch and update the owner's name, password, business name, phone, and location.

#### 2. Frontend Onboarding & Signup UI (`apps/dashboard/`)
- **[MODIFY] [index.html](file:///c:/Users/smart/Desktop/SMSOS/apps/dashboard/index.html)**:
  - Add a **Signup Card** in the Auth Screen.
  - Add an **Onboarding Card** shown to new signups before they access the main dashboard.
  - Add a Profile dropdown container (avatar icon + name) in the top-right header bar.
- **[MODIFY] [app.js](file:///c:/Users/smart/Desktop/SMSOS/apps/dashboard/js/app.js)**:
  - Handle routing and toggling between Login, Signup, and Onboarding states.
  - Add `GET/PUT /auth/profile` fetching/updating inside an "Edit Profile" modal.
  - Handle dropdown triggers (showing/hiding dropdown menu, signing out).

---

## [NEW] Conversational Thread Deletion & AI Context Reset Plan

### Goal
Provide a way to delete conversation threads in the dashboard "AI Conversations" view, which clears message history and resets the AI context (state) for a customer's WhatsApp number.

### Proposed Changes

#### 1. Backend Route Update (`apps/api/app/api/v1/conversations.py`)
- **[MODIFY] [conversations.py](file:///c:/Users/smart/Desktop/SMSOS/apps/api/app/api/v1/conversations.py)**:
  - Import `delete` from `sqlalchemy`.
  - Add `DELETE /api/v1/conversations/{phone_number}` endpoint.
  - Logic: Delete `InboundMessage`, `OutboundMessage`, and `ConversationState` records associated with the user's business and target phone number.

#### 2. Frontend UI Update (`apps/dashboard/js/app.js`)
- **[MODIFY] [app.js](file:///c:/Users/smart/Desktop/SMSOS/apps/dashboard/js/app.js)**:
  - Update `renderConversationsView` to include a "Delete Thread" button (with trash icon) in the selected chat header.
  - Add `deleteConversation(phone)` javascript function to trigger the delete API request, show toast, and reload the thread list.
