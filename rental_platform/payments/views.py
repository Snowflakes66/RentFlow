from django.shortcuts import render

import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth.models import User
from .models import Landlord
from .nomba_client import nomba_post
from django.conf import settings


class LandlordRegistrationView(APIView):
    
    def post(self, request):
        data = request.data

        # Step 1: Extract the landlord's info from the request
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')

        # Basic validation — make sure required fields are present
        if not all([name, email, phone_number, password]):
            return Response(
                {'error': 'name, email, phone_number and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Check if a user with this email already exists
        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'A landlord with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 2: Create the Django User and Landlord record locally
        user = User.objects.create_user(
            username=email,  # using email as username
            email=email,
            password=password
        )

        landlord = Landlord.objects.create(
            user=user,
            name=name,
            email=email,
            phone_number=phone_number,
        )

        # Step 3: Create a subaccount on Nomba for this landlord
        # The accountRef is our own stable reference we generate
        account_ref = f"landlord_{landlord.id}_{uuid.uuid4().hex[:8]}"

        
        # Step 4: Save the subaccount ID back to the landlord record
        nomba_subaccount_id = settings.NOMBA_SUBACCOUNT_ID 
        landlord.nomba_subaccount_id = nomba_subaccount_id
        landlord.account_ref = account_ref
        landlord.save()

        # Step 5: Create a virtual account for this landlord
        virtual_account_response = nomba_post('/accounts/virtual', {
            'accountRef': f"va_{account_ref}",
            'accountName': name,
            'currency': 'NGN',
        })
        print("Virtual account response:", virtual_account_response)
        # Check if virtual account creation was successful
        if virtual_account_response.get('code') != '00':
            # Subaccount was created but virtual account failed — flag it
            return Response(
                {'error': 'Subaccount created but virtual account failed', 'details': virtual_account_response},
                status=status.HTTP_502_BAD_GATEWAY
            )
        
        # Step 6: Save the virtual account details back to the landlord record
        virtual_data = virtual_account_response['data']
        landlord.virtual_account_number = virtual_data.get('bankAccountNumber')
        landlord.account_name = virtual_data.get('bankAccountName')
        landlord.save()

        # Step 7: Return a success response with the landlord's details
        return Response({
            'message': 'Landlord registered successfully',
            'landlord_id': landlord.id,
            'name': landlord.name,
            'email': landlord.email,
            'virtual_account_number': landlord.virtual_account_number,
            'account_name': landlord.account_name,
        }, status=status.HTTP_201_CREATED)
    
