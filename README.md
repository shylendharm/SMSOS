# SMSOS — Smart Messaging Operating System

> **An Autonomous, Multi-Model AI-Powered WhatsApp & SMS Commerce Engine for Restaurants and Retail Businesses.**

[![Python 3.12](https://img.shields.io/badge/Python-3.12-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-4169E1?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Groq LLaMA 3.3](https://img.shields.io/badge/AI-Groq%20LLaMA%203.3%2070B-f05032?style=flat&logo=meta&logoColor=white)](https://groq.com/)
[![Google Gemini](https://img.shields.io/badge/AI-Google%20Gemini%202.0-8E44AD?style=flat&logo=google-gemini&logoColor=white)](https://ai.google.dev/)
[![Twilio](https://img.shields.io/badge/Messaging-Twilio%20WhatsApp%2FSMS-F22F46?style=flat&logo=twilio&logoColor=white)](https://www.twilio.com/)
[![Pytest Passed](https://img.shields.io/badge/Tests-29%2F29%20Passed-brightgreen?style=flat&logo=pytest&logoColor=white)](https://docs.pytest.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## 📌 Executive Summary

**SMSOS** bridges the gap between conversational messaging and merchant management. Instead of requiring customers to download third-party food delivery apps or navigate complex web forms, SMSOS transforms WhatsApp and SMS into a **fully autonomous ordering terminal**.

Customers can place orders, check menu items, request repeat orders, track delivery ETAs, and reserve dining tables using natural, conversational language. Behind the scenes, SMSOS orchestrates multi-provider AI models (Groq LLaMA 3.3 70B, Google Gemini 2.0 Flash), automated matrix distance routing, PostgreSQL transactional storage, and live merchant dashboards.

---

## 🚀 Key Features & Highlights

### 🧠 1. Multi-Tier Resilient AI Engine
- **Ultra-Fast Primary AI (Groq LLaMA 3.3 70B)**: Sub-second (<0.4s) natural language understanding and structured JSON entity extraction.
- **Fail-Safe Provider Chain**:
  $$\text{Groq AI (Primary)} \longrightarrow \text{Gemini 2.0 Flash} \longrightarrow \text{OpenRouter Free Models} \longrightarrow \text{Offline Regex Fallback}$$
- **Zero-Downtime Offline Fallback**: If all cloud AI APIs hit rate limits or network issues, a built-in offline NLP regex parser extracts quantities, item names, and delivery locations locally.

### 🛍️ 2. Conversational Commerce & Quick Re-Order
- **Intent Recognition**: Automatically classifies messages into `PLACE_ORDER`, `INQUIRY`, `RESERVATION`, `CHECK_STATUS`, or `OTHER`.
- **Entity Extraction**: Captures food item names, quantities, special requests, and detailed delivery addresses (*"send 2 dosa and 1 coffee to Venpa Block"*).
- **One-Tap Re-Ordering**: Recognizes phrases like *"repeat last order"* or *"same order again"*, retrieves historical customer data, and drafts the order instantly.
- **Order State Machine**: Manages multi-turn conversation states (`ORDER_PENDING` → `ORDER_LOCATION_PENDING` → `ORDER_CONFIRMED`).

### 📍 3. Smart Distance & Delivery ETA Routing
- **OpenRouteService (ORS) Matrix Routing**: Calculates actual driving distance (km) and road duration (mins) between the shop and customer.
- **Landmark Geocoding (Nominatim)**: Resolves hostel blocks, college campuses, and landmark addresses via OpenStreetMap with Plus Code stripping.
- **Dynamic ETA Formula**:
  $$\text{Delivery ETA} = \text{Default Prep Time} + \text{Item Volume Factor} + \text{Road Distance (km)} \times \text{Speed Factor} + \text{Traffic Buffer}$$

### 🍽️ 4. Dynamic Table Reservation Engine
- **Slot Management**: Automated 90-minute dining table reservation slots.
- **Capacity Balancing**: Computes live table availability based on business capacity rules.
- **Structured Scheduling**: Converts relative date/time expressions (*"tomorrow at 7pm"*) into standardized ISO dates (`YYYY-MM-DD`) and 24-hour time slots (`19:00`).

### 📑 5. Programmatic PDF Receipt Generation
- Automated invoice generation using **ReportLab** stored in `/static/receipts/`.
- Includes itemized price breakdowns, tax calculations, estimated delivery times, shop branding, and QR codes.

### 📊 6. Merchant Management Dashboard
- Real-time Single Page Application (SPA) built with Vanilla HTML5, CSS3, and JavaScript.
- Displays live order queues, status transition triggers (*Pending → Preparing → Out for Delivery → Delivered*), table reservations, inventory stock control, and sales analytics.

---

## 🏗️ Architecture & System Flow

```mermaid
flowchart TD
    subgraph Client Layer
        A[Customer on WhatsApp / SMS]
    end

    subgraph Messaging Gateway
        B[Twilio Messaging API]
    end

    subgraph Backend Infrastructure [FastAPI Async Core]
        C[POST /api/v1/webhooks/twilio]
        D[Messaging Orchestrator]
        
        subgraph AI Provider Chain
            E[1. Groq LLaMA 3.3 70B]
            F[2. Google Gemini 2.0 Flash]
            G[3. OpenRouter Free Models]
            H[4. Offline Regex Parser]
        end
        
        I[Geo & Routing Engine\nORS + Nominatim Geocoding]
        J[ReportLab PDF Engine]
    end

    subgraph Database Layer
        K[(PostgreSQL Database\nSQLAlchemy 2.0 Async)]
    end

    subgraph Merchant Interface
        L[Single Page Dashboard\nHTML5 / Vanilla CSS / JS]
    end

    A <-->|WhatsApp / SMS| B
    B <-->|HTTP POST Webhook| C
    C --> D
    D <--> E
    E -- On Rate Limit --> F
    F -- On Fail --> G
    G -- On Fail --> H
    D <--> I
    D --> J
    D <--> K
    L <-->|REST API v1| K
```

---

## 🛠️ Technology Stack

| Component | Technology | Description |
|---|---|---|
| **Language** | Python 3.12.1 | Modern async Python codebase. |
| **Backend Framework** | FastAPI (v0.100+) | High-performance asynchronous REST API framework. |
| **Database** | PostgreSQL + asyncpg | Relational database with full async I/O. |
| **ORM & Migrations** | SQLAlchemy 2.0 + Alembic | Type-safe asynchronous ORM models and migrations. |
| **AI / LLM Engine** | Groq LLaMA 3.3 70B, Google Gemini 2.0, OpenRouter | Multi-model pipeline for structured JSON generation. |
| **Messaging Gateway** | Twilio Python SDK | Webhook handling and WhatsApp/SMS delivery. |
| **Geo & Routing** | OpenRouteService (ORS) + Nominatim | Road distance matrix calculation & reverse geocoding. |
| **Document Generation** | ReportLab | Automated PDF receipt and invoice generation. |
| **Merchant Frontend** | Vanilla HTML5 / CSS3 / JavaScript | Responsive single-page dashboard with zero dependencies. |
| **Testing** | Pytest + AnyIO | Asynchronous test suite with 100% pass rate. |
| **Logging & Security** | Structlog + PyJWT + bcrypt + Firebase Admin | Structured JSON logging, JWT auth, Google Sign-In. |

---

## 🗄️ Database Architecture

The system features **14 relational database models**:

| Table Name | Description |
|---|---|
| `users` | Merchant accounts, hashed passwords, roles (`owner`, `staff`), Firebase UIDs. |
| `businesses` | Shop profile, physical address, lat/lon, table capacity, prep times. |
| `catalog_items` | Menu items, categories, pricing, stock availability flags. |
| `customers` | Customer phone numbers, names, total order counts, lifetime spend. |
| `orders` | Order headers, statuses (`pending`, `confirmed`, `preparing`, `delivered`, `cancelled`), delivery locations, ETAs. |
| `order_items` | Line items, quantities, historical unit prices. |
| `reservations` | Table bookings, party sizes, reservation dates, 90-minute slot times. |
| `conversation_states` | Active customer conversation states for multi-turn dialogs. |
| `inbound_messages` | Full audit log of incoming WhatsApp/SMS webhook payloads. |
| `outbound_messages` | Full audit log of outgoing Twilio responses and SIDs. |
| `webhook_events` | Webhook delivery telemetry and retry logs. |
| `intent_predictions` | AI prediction records, confidence scores, detected languages. |
| `inventory_items` | Stock quantities, unit measures, low-stock reorder thresholds. |
| `inventory_logs` | Audit trail of manual and automated stock adjustments. |

---

## 📡 REST API Structure (`/api/v1`)

```
/api/v1
 ├── /auth            # POST /login, POST /register, GET /profile, POST /google
 ├── /business        # GET /me, PUT /me, PUT /capacity
 ├── /catalog         # GET /items, POST /items, PUT /items/{id}, DELETE /items/{id}
 ├── /orders          # GET /, GET /{id}, PUT /{id}/status, GET /{id}/pdf
 ├── /reservations    # GET /, POST /, PUT /{id}/status
 ├── /conversations   # GET /{phone}/history, GET /states
 ├── /inventory       # GET /items, POST /items, PUT /items/{id}/stock, GET /logs
 ├── /analytics       # GET /dashboard, GET /revenue, GET /top-items
 └── /webhooks/twilio # POST / (Twilio Inbound Listener)
```

---

## 💻 Local Setup & Installation

### 1. Prerequisites
- **Python 3.12+**
- **PostgreSQL 15+**
- **Twilio Account** (with WhatsApp Sandbox configured)
- **Groq API Key** (from [console.groq.com](https://console.groq.com/keys))

### 2. Clone Repository & Setup Environment
```bash
git clone https://github.com/shylendharm/SMSOS.git
cd SMSOS

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
cd apps/api
pip install -r pyproject.toml
```

### 3. Environment Configuration
Create a `.env` file in the project root:
```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/smsos_dev

JWT_SECRET=your_jwt_secret_key_at_least_32_bytes
JWT_ALGORITHM=HS256
JWT_EXPIRATION_MINUTES=30

TWILIO_ACCOUNT_SID=your_twilio_account_sid
TWILIO_AUTH_TOKEN=your_twilio_auth_token
TWILIO_PHONE_NUMBER=+14155238886

GROQ_API_KEY=gsk_your_groq_api_key
GEMINI_API_KEY=your_gemini_api_key
OPENROUTER_API_KEY=your_openrouter_api_key
ORS_API_KEY=your_openrouteservice_api_key

API_BASE_URL=http://localhost:8005
FRONTEND_BASE_URL=http://localhost:5173
```

### 4. Database Setup & Migrations
```bash
# Run database migrations
alembic upgrade head
```

### 5. Launch Backend Server
```bash
python app/main.py
```
The server starts dynamically on the port specified in `API_BASE_URL` in your `.env` (e.g., `8005`). If no port is specified, it defaults to `8000`. 
API documentation is available at `http://localhost:<PORT>/docs` (e.g., `http://localhost:8005/docs`).

### 6. Webhook Setup (Localtunnel / Ngrok)
Expose the configured port (e.g., 8005) to receive live WhatsApp messages:
```bash
npx ngrok http 8005
```
Copy the generated HTTPS URL and paste it into your Twilio Sandbox settings:
```
https://your-ngrok-domain.ngrok-free.app/api/v1/webhooks/twilio (HTTP POST)
```

---

## 🧪 Testing

Run the full automated Pytest suite (29 integration and unit tests):

```bash
cd apps/api
python -m pytest -v
```

### Test Output Summary:
```
============================= test session starts =============================
tests/integration/test_auth_api.py::test_auth_flow PASSED                [  3%]
tests/integration/test_auth_api.py::test_register_flow PASSED            [  6%]
tests/integration/test_auth_api.py::test_google_auth_flow PASSED         [ 10%]
tests/integration/test_core_apis.py::test_all_core_apis_integration PASSED [ 13%]
tests/integration/test_webhooks.py::test_twilio_webhook_endpoint PASSED  [ 17%]
tests/integration/test_webhooks.py::test_auto_substitution_message PASSED [ 20%]
tests/unit/test_ai.py::test_fallback_response PASSED                     [ 24%]
tests/unit/test_geo.py::test_haversine_distance PASSED                   [ 27%]
tests/unit/test_geo.py::test_geocode_address_fallback_nominatim PASSED   [ 31%]
tests/unit/test_geo.py::test_calculate_delivery_eta_pipeline PASSED      [ 34%]
tests/unit/test_geo.py::test_calculate_delivery_eta_empty_address PASSED [ 37%]
tests/unit/test_models.py::test_all_14_models_creation PASSED            [ 41%]
tests/unit/test_order_delivery.py::test_intent_result_delivery_fields PASSED [ 44%]
tests/unit/test_pdf.py::test_generate_order_receipt_pdf PASSED           [ 48%]
tests/unit/test_reorder.py::test_intent_result_reorder_field PASSED      [ 51%]
tests/unit/test_reorder.py::test_reorder_keyword_matching PASSED         [ 55%]
tests/unit/test_session.py::test_db_session_lifecycle PASSED             [ 58%]
tests/unit/test_session.py::test_db_session_rollback_on_error PASSED     [ 62%]
tests/unit/test_status_notifications.py::test_order_preparing_message PASSED [ 65%]
tests/unit/test_status_notifications.py::test_order_out_for_delivery_message PASSED [ 68%]
tests/unit/test_status_notifications.py::test_order_delivered_message PASSED [ 72%]
tests/unit/test_status_notifications.py::test_order_cancelled_message PASSED [ 75%]
tests/unit/test_status_notifications.py::test_order_unknown_status_message PASSED [ 79%]
tests/unit/test_status_notifications.py::test_reservation_confirmed_message PASSED [ 82%]
tests/unit/test_status_notifications.py::test_reservation_confirmed_single_guest PASSED [ 86%]
tests/unit/test_status_notifications.py::test_reservation_seated_message PASSED [ 89%]
tests/unit/test_status_notifications.py::test_reservation_cancelled_message PASSED [ 93%]
tests/unit/test_status_notifications.py::test_reservation_completed_message PASSED [ 96%]
tests/unit/test_status_notifications.py::test_reservation_no_show_message PASSED [100%]

======================== 29 passed in 46.23s (0:00:46) ========================
```

---

## 👨‍💻 Developer & Author

Developed by **Shylendhar M**  
- **GitHub**: [@shylendharm](https://github.com/shylendharm)  
- **Project Repository**: [github.com/shylendharm/SMSOS](https://github.com/shylendharm/SMSOS)

---

## 📄 License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.
