from django.urls import path
from .views import LandlordRegistrationView, TenantRegistrationView, InitiatePaymentView


urlpatterns = [
    path('landlords/register/', LandlordRegistrationView.as_view(), name='landlord-register'),
    path('tenants/register/', TenantRegistrationView.as_view(), name='tenant-register'),
    path('payments/initiate/', InitiatePaymentView.as_view(), name='initiate-payment'),
]