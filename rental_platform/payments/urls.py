from django.urls import path
from .views import LandlordRegistrationView, TenantRegistrationView, InitiatePaymentView, WebhookView,PaymentCallbackView, VerifyPaymentView


urlpatterns = [
    path('landlords/register/', LandlordRegistrationView.as_view(), name='landlord-register'),
    path('tenants/register/', TenantRegistrationView.as_view(), name='tenant-register'),
    path('payments/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
    path('payments/webhook/', WebhookView.as_view(), name='webhook'),
    path('payments/callback/', PaymentCallbackView.as_view(), name='payment-callback'),
    path('payments/verify/<str:order_reference>/', VerifyPaymentView.as_view(), name='verify-payment'),
]