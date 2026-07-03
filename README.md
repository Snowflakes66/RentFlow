Project: RentFlow
Summary: A Django REST API enabling secure, transparent rent payments between landlords, agents, and tenants using Nomba's payment infrastructure.


Milestones completed:

Landlord registration with live Nomba virtual account creation (tested end-to-end against sandbox, real bank account numbers returned)
Tenant registration with JWT-based authentication
Payment initiation flow: creates a pending Payment record, calls Nomba's Checkout API with correct kobo conversion, returns a live checkout URL (tested end-to-end, 201 Created confirmed)
Webhook handler implemented with HMAC-SHA256 signature verification, idempotent event processing via requestId deduplication, and automatic payment status resolution (confirmed/underpaid/overpaid)
Core data models designed around the real payment lifecycle, including a dedicated WebhookEvent model for auditability

Known limitations (in progress):

Live webhook signature verification is implemented but not yet tested end-to-end The Nomba developer dashboard was inaccessible during this build phase (password reset emails not delivered), so the webhook secret and URL could not be configured
Subaccount creation via Nomba's API currently returns a sandbox-side 500 error; using a shared subaccount as a documented workaround, with per-landlord subaccounts planned once resolved
Split payments (landlord/platform percentage) not yet implemented, pending subaccount-per-landlord resolution

GitHub: github.com/Snowflakes66/RentFlow

