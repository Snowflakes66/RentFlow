# RentFlow

A Django REST API enabling secure, transparent rent payments between landlords, agents, and tenants using Nomba's payment infrastructure.

Built for the **Nomba x DevCareer Hackathon 2026**.

---

## What It Does

RentFlow solves a real problem in the Nigerian rental market: rent payments are often informal, untracked, and dispute-prone. RentFlow gives landlords a virtual account, lets tenants initiate payments through a secure checkout flow, and automatically reconciles payment status — including underpayments and overpayments — via webhook events.

---

## Nomba APIs Used

- **Virtual Accounts** — each landlord gets a dedicated NUBAN account on registration
- **Checkout API** — generates a secure hosted payment link for tenants
- **Webhooks** — server-to-server payment confirmation with HMAC-SHA256 signature verification
- **Transactions API** — on-demand payment verification via `orderReference`
- **Split Payments** — 98% routed to landlord's subaccount, 2% to platform subaccount on every transaction

---

## Endpoints

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| POST | `/api/landlords/register/` | None | Register landlord, create Nomba virtual account |
| POST | `/api/tenants/register/` | None | Register tenant |
| POST | `/api/token/` | None | Obtain JWT access + refresh tokens |
| POST | `/api/token/refresh/` | None | Refresh JWT |
| POST | `/api/payments/initiate/` | JWT | Initiate payment, return Nomba checkout URL |
| POST | `/api/payments/webhook/` | HMAC signature | Receive and verify Nomba payment events |
| GET | `/api/payments/callback/` | None | Post-checkout redirect handler |
| GET | `/api/payments/verify/<order_reference>/` | JWT | Verify payment against Nomba transactions API |

---

## Payment Flow

1. Landlord registers → Nomba virtual account created, real NUBAN returned
2. Tenant registers and authenticates via JWT
3. Tenant initiates payment → pending `Payment` record created → Nomba Checkout API called → `checkoutLink` returned
4. Tenant completes payment on hosted checkout page
5. Nomba sends webhook POST → HMAC-SHA256 signature verified → `requestId` deduplication check → payment status resolved (confirmed / underpaid / overpaid)
6. Payment can be independently verified via the verify endpoint at any time

---

## Split Payments

Every payment is split at the Nomba level using `splitRequest`:

```json
{
  "splitType": "PERCENTAGE",
  "splitList": [
    { "accountId": "<landlord_subaccount_id>", "value": "98.00" },
    { "accountId": "<platform_subaccount_id>", "value": "2.00" }
  ]
}
```

In production, landlord and platform subaccounts are separate. In sandbox, a shared subaccount ID is used as a documented workaround (subaccount creation via API returns a 500 in Nomba's sandbox environment).

---

## Data Models

- `Landlord` — linked to Django user, stores `nomba_account_id` and `nomba_subaccount_id`
- `Tenant` — linked to Django user, associated with a landlord
- `Payment` — tracks `order_reference`, `expected_amount`, `amount_received`, `status` (pending / confirmed / underpaid / overpaid), and `confirmed_at`
- `WebhookEvent` — full audit log of every incoming webhook, including raw payload and `requestId` for idempotency

---

## Tech Stack

- Python / Django / Django REST Framework
- PostgreSQL
- Simple JWT (djangorestframework-simplejwt)
- Nomba Sandbox API

---

## Setup

**1. Clone the repo**
```bash
git clone https://github.com/Snowflakes66/RentFlow.git
cd RentFlow/rental_platform
```

**2. Create and activate virtual environment**
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Mac/Linux
```

**3. Install dependencies**
```bash
pip install -r requirements.txt
```

**4. Configure environment variables**

Copy `.env.example` to `.env` and fill in your values:

```
DB_NAME=rentflow_db
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432
SECRET_KEY=your_django_secret_key

BASE_URL=https://your-ngrok-url.ngrok-free.dev

NOMBA_BASE_URL=https://sandbox.nomba.com/v1
NOMBA_ACCOUNT_ID=your_nomba_account_id
NOMBA_SUBACCOUNT_ID=your_nomba_subaccount_id
NOMBA_PLATFORM_SUBACCOUNT_ID=your_platform_subaccount_id
NOMBA_CLIENT_ID=your_client_id
NOMBA_CLIENT_SECRET=your_client_secret
NOMBA_WEBHOOK_SECRET=your_webhook_secret

NGROK_HOST=your-ngrok-url.ngrok-free.dev
```

**5. Run migrations and start server**
```bash
python manage.py migrate
python manage.py runserver
```

---

## Known Sandbox Limitations

**Webhook tested end-to-end with real Nomba events** — Signature verification passed, deduplication works, and payment status updated to confirmed automatically Webhook secret was shared by the Nomba team on Slack. URL was registered via the Google Form they provided.

**Subaccount creation via API** — `POST /accounts/sub-accounts` returns a 500 error in Nomba's sandbox. A shared subaccount ID is used for both landlord and platform splits as a deliberate workaround. The code is production-ready and would use separate subaccounts in a live environment.

---

## GitHub

[https://github.com/Snowflakes66/RentFlow]