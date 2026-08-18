# 📊 API Usage, Billing & Prediction Analytics Dashboard

A centralized Django web platform designed to monitor external prediction API consumption, calculate dynamic tier-based pricing ("Pockets"), manage client billing/invoicing, and visualize real-time scoring metrics.

---

## 🌟 Key Features

- **📈 Real-Time Analytics Dashboard**:
  - Request tracking across customizable periods (today, yesterday, 7-day, 30-day, and month-to-date).
  - Visual charts for 24-hour hourly activity, 30-day request history, and 7-day approval rates.
  - Branch-level prediction breakdown and scoring distributions.
- **💼 Tiered Pocket (Plan) Billing**:
  - Exact financial calculations using Python `Decimal` to avoid floating-point inaccuracies.
  - Automatic quota tracking, limit warnings, and over-limit surcharge calculation.
- **📑 Invoice Generation & Management**:
  - Month-to-Date (MTD) unbilled balance tracking.
  - Automatic generation and persistence of monthly invoices (HTML & JSON outputs).
- **📜 Upstream Prediction Logs & Audit History**:
  - Query upstream prediction logs filtered by date ranges with pagination.
  - Export audit logs to **CSV** and **JSON** format.
- **🏢 Multi-Tenant Upstream API Integration**:
  - Dynamic API proxying: API URL and basic auth credentials configured per `Company`.
- **🌐 Localization**:
  - Cookie-based multi-language interface switching (`ru`, `en`, `uz`).

---

## 🏗️ Architecture & Core Entities

```
User ──► Profile ──► Company ──┬──► Pocket (Subscription Tier)
                               ├──► Invoices
                               └──► Upstream API (Dynamic URL + Auth)
```

- **`Pocket`**: Base quota (`requests_count`), base cost (`price`), and overage fee (`price_per_request_over_limit`).
- **`Company`**: Holds upstream API credentials and links to a subscription `Pocket`.
- **`Invoice`**: Records monthly consumption, total requests, and total billing amounts.

---

## 🚀 Quick Start with Docker

### 1. Prerequisites
- [Docker](https://docs.docker.com/get-docker/)
- [Docker Compose](https://docs.docker.com/compose/install/)

### 2. Build and Start the Containers
```bash
docker compose up --build -d
```

### 3. Database Setup & Initial Migration
Run migrations and create an administrator account:

```bash
docker compose exec web python manage.py makemigrations core
docker compose exec web python manage.py migrate
docker compose exec web python manage.py createsuperuser
```

The application will be accessible at `http://localhost:8000`.

---

## ⚙️ Initial Configuration

1. **Log in to Django Admin** (`http://localhost:8000/admin/`).
2. **Create a Pocket**: Define base cost, request limits, and over-limit fees.
3. **Create a Company**:
   - Assign the `Pocket`.
   - Set the external prediction `API URL`, `API Username`, and `API Password`.
4. **Link User Profile**: Assign the user's `Profile` to the created `Company`.

---

## 🛣️ Route & Endpoint Overview

| Route | Method | Description |
| :--- | :--- | :--- |
| `/login/` | `GET`, `POST` | Custom authentication with profile validation |
| `/` | `GET` | Main Dashboard (hourly activity, metrics, 30-day charts) |
| `/history/` | `GET` | Paginated prediction log viewer with date-range filters |
| `/history/export/csv/` | `GET` | Export all prediction logs for a date range to CSV |
| `/history/export/json/` | `GET` | Export all prediction logs for a date range to JSON |
| `/pricing/` | `GET` | View available subscription plans and current usage |
| `/invoices/` | `GET` | Company billing history and current unbilled MTD balance |
| `/invoices/generate/` | `GET` | Calculate & generate monthly invoice (`?format=json` supported) |

---

## 🔌 Upstream API Protocol

The application expects the upstream company API to accept standard query parameters and return a paginated JSON response:

**Request Parameters:**
- `start_date` (`DD.MM.YYYY`)
- `end_date` (`DD.MM.YYYY`)
- `page` (`int`)
- `items_per_page` (`int`)

**Expected JSON Response:**
```json
{
  "code": 200,
  "data": [
    {
      "hash_uid": "abc-123",
      "prediction_date": "15.08.2026 14:32:00",
      "pinfl": "12345678901234",
      "branch": "Branch_A",
      "prediction": "Approved",
      "good_prob": 88.5,
      "bad_prob": 11.5
    }
  ],
  "meta": {
    "currentPage": 1,
    "itemsPerPage": 100,
    "totalItems": 1,
    "lastPage": 1
  }
}
```

---

## 🛠️ Tech Stack

- **Backend**: Python 3, Django
- **HTTP Client**: `requests`
- **Data Serialization**: Built-in `csv`, `json`
- **Containerization**: Docker & Docker Compose
