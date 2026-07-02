from django.urls import path
from .views import LandlordRegistrationView

urlpatterns = [
    path('landlords/register/', LandlordRegistrationView.as_view(), name='landlord-register'),
]