# RentFlow

A Django REST API enabling secure, transparent rent payments between landlords, agents, and tenants using Nomba's payment infrastructure.

## Features

- Landlord registration with automatic Nomba virtual account creation
- Tenant registration
- Rent payment initiation via Nomba Checkout API
- Webhook handler with HMAC-SHA256 signature verification
- Payment status tracking (pending, confirmed, underpaid, overpaid)
- Idempotent webhook processing via requestId deduplication

## Tech Stack

- Django 5.2 + Django REST Framework
- PostgreSQL
- Nomba API (sandbox)

## Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/landlords/register/ | Register a landlord and create Nomba virtual account |
| POST | /api/tenants/register/ | Register a tenant |
| POST | /api/payments/initiate/ | Initiate a rent payment (authenticated) |
| POST | /api/payments/webhook/ | Nomba webhook handler |
| POST | /api/token/ | Obtain JWT access token |

## Setup

```bash
git clone <repo-url>
cd RentFlow/rental_platform
pip install -r requirements.txt
cp .env.example .env  # fill in your credentials
python manage.py migrate
python manage.py runserver
```

## Environment Variables
NOMBA_BASE_URL=https://sandbox.nomba.com/v1
NOMBA_ACCOUNT_ID=your-parent-account-id
NOMBA_CLIENT_ID=your-test-client-id
NOMBA_CLIENT_SECRET=your-test-client-secret
NOMBA_SUBACCOUNT_ID=your-subaccount-id
NOMBA_WEBHOOK_SECRET=your-webhook-secret
BASE_URL=http://127.0.0.1:8000
DB_NAME=rentflow_db
DB_USER=postgres
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432



## Notes

Subaccount creation via API returns 500 in Nomba sandbox, using a shared sandbox subaccount as workaround. In production each landlord gets their own subaccount.
Webhook signature verification is implemented and ready, pending Nomba dashboard access to configure the webhook secret.
Amounts are stored and transmitted in kobo (1 NGN = 100 kobo).