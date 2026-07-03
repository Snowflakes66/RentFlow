from django.shortcuts import render
import uuid
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, permissions
from django.contrib.auth.models import User
from .models import Landlord, Tenant, Payment, WebhookEvent
from .nomba_client import nomba_post
from django.conf import settings
import hmac
import hashlib
import base64
import json
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.utils import timezone


class LandlordRegistrationView(APIView):
    
    def post(self, request):
        data = request.data

        # Step 1: Extract the landlord's info from the request
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')

        # Validation to make sure required fields are present
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

        # Step 5: Creating a virtual account for this landlord
        virtual_account_response = nomba_post('/accounts/virtual', {
            'accountRef': f"va_{account_ref}",
            'accountName': name,
            'currency': 'NGN',
        })
        print("Virtual account response:", virtual_account_response)
        # To Check if virtual account creation was successful
        if virtual_account_response.get('code') != '00':
            # If Subaccount was created but virtual account failed it gets flag
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
    



class TenantRegistrationView(APIView):
    def post(self, request):
        data = request.data

        # Step 1: Extract the tenant's info from the request
        name = data.get('name')
        email = data.get('email')
        phone_number = data.get('phone_number')
        password = data.get('password')

        if not all([name, email, phone_number, password]):
            return Response(
                {'error': 'name, email, phone_number and password are required'},
                status=status.HTTP_400_BAD_REQUEST
            )


        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'A tenant with this email already exists'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 2: Create the Django User and Tenant record locally
        user = User.objects.create_user(
            username=email,  # using email as username
            email=email,
            password=password
        )

        tenant = Tenant.objects.create(
            user=user,
            name=name,
            email=email,
            phone_number=phone_number,
        )


        # Step 3: Return a success response with the tenant's details
        return Response({
            'message': 'Tenant registered successfully',
            'tenant_id': tenant.id,
            'name': tenant.name,
            'email': tenant.email,
        }, status=status.HTTP_201_CREATED)
    



class InitiatePaymentView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        tenant = request.user.tenant_profile
        landlord_id = request.data.get('landlord_id')
        amount_naira = request.data.get('amount')

        if not landlord_id or not amount_naira:
            return Response(
                {"error": "landlord_id and amount required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Step 1: Look up the landlord
        try:
            landlord = Landlord.objects.get(id=landlord_id)
        except Landlord.DoesNotExist:
            return Response(
                {"error": "Landlord not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Step 2: Generate order reference and convert amount to kobo
        order_reference = str(uuid.uuid4())
        amount_kobo = int(float(amount_naira) * 100)  # convert naira to kobo

        # Step 3: Create Payment record in database with status pending
        payment = Payment.objects.create(
            tenant=tenant,
            landlord=landlord,
            order_reference=order_reference,
            expected_amount=amount_kobo,
            status=Payment.Status.PENDING,
        )

        # Step 4: Call Nomba checkout API
        checkout_response = nomba_post('/checkout/order', {
            'order': {
                'orderReference': order_reference,
                'amount': amount_kobo,
                'currency': 'NGN',
                'customerEmail': tenant.email,
                'customerId': str(tenant.id),
                'accountId': landlord.nomba_subaccount_id,
                'callbackUrl': f"{settings.BASE_URL}/api/payments/callback/",
                'orderMetaData': {
                    'landlordId': str(landlord.id),
                    'tenantId': str(tenant.id),
                    'paymentId': str(payment.id),
                }
            }
        })

        # Check if checkout creation was successful
        if checkout_response.get('code') != '00':
            # Delete the payment record we just created since checkout failed
            payment.delete()
            return Response(
                {"error": "Failed to create checkout order", "details": checkout_response},
                status=status.HTTP_502_BAD_GATEWAY
            )

        # Step 5: Return the checkout URL to the tenant
        checkout_url = checkout_response['data']['checkoutLink']

        return Response({
            'message': 'Payment initiated successfully',
            'order_reference': order_reference,
            'amount_naira': amount_naira,
            'amount_kobo': amount_kobo,
            'checkout_url': checkout_url,
            'payment_id': payment.id,
        }, status=status.HTTP_201_CREATED)
    






@method_decorator(csrf_exempt, name='dispatch')
class WebhookView(APIView):
    authentication_classes = []  # No JWT auth for webhooks - Nomba signs them instead
    permission_classes = []

    def post(self, request):
        # Step 1: Get the signature and timestamp from Nomba's headers
        nomba_signature = request.headers.get('nomba-signature')
        nomba_timestamp = request.headers.get('nomba-timestamp')

        # Step 2: Get the raw request body
        payload = request.body.decode('utf-8')

        # Step 3: Verify the signature to confirm this is genuinely from Nomba
        if nomba_signature and settings.NOMBA_WEBHOOK_SECRET:
            is_valid = self.verify_signature(payload, nomba_signature, nomba_timestamp)
            if not is_valid:
                return Response({'error': 'Invalid signature'}, status=status.HTTP_400_BAD_REQUEST)

        # Step 4: Parse the payload
        try:
            data = json.loads(payload)
        except json.JSONDecodeError:
            return Response({'error': 'Invalid JSON'}, status=status.HTTP_400_BAD_REQUEST)

        event_type = data.get('event_type')
        request_id = data.get('requestId')

        # Step 5: Check for duplicate webhooks using requestId
        if WebhookEvent.objects.filter(request_id=request_id).exists():
            # Already processed this event - return 200 so Nomba stops retrying
            return Response({'message': 'Already processed'}, status=status.HTTP_200_OK)

        # Step 6: Save the webhook event to database
        WebhookEvent.objects.create(
            request_id=request_id,
            event_type=event_type,
            raw_payload=data,
            signature_valid=is_valid if (nomba_signature and settings.NOMBA_WEBHOOK_SECRET) else False,
        )

        # Step 7: Handle payment_success event
        if event_type == 'payment_success':
            self.handle_payment_success(data)

        # Step 8: Always return 200 quickly so Nomba doesn't retry
        return Response({'message': 'Webhook received'}, status=status.HTTP_200_OK)

    def verify_signature(self, payload, nomba_signature, nomba_timestamp):
        try:
            data = json.loads(payload)
            transaction = data.get('data', {}).get('transaction', {})
            merchant = data.get('data', {}).get('merchant', {})

            # Construct the exact string Nomba uses to generate the signature
            hashing_payload = ':'.join([
                data.get('event_type', ''),
                data.get('requestId', ''),
                merchant.get('userId', ''),
                merchant.get('walletId', ''),
                transaction.get('transactionId', ''),
                transaction.get('type', ''),
                transaction.get('time', ''),
                transaction.get('responseCode', '') or '',
                nomba_timestamp or '',
            ])

            # Compute HMAC-SHA256 and base64 encode it
            computed = hmac.new(
                settings.NOMBA_WEBHOOK_SECRET.encode(),
                hashing_payload.encode(),
                hashlib.sha256
            ).digest()

            computed_b64 = base64.b64encode(computed).decode()
            return computed_b64 == nomba_signature

        except Exception:
            return False

    def handle_payment_success(self, data):
        try:
            order = data.get('data', {}).get('order', {})
            transaction = data.get('data', {}).get('transaction', {})

            order_reference = order.get('orderReference')
            amount_received = int(float(transaction.get('transactionAmount', 0)) * 100)  # convert to kobo

            # Find the payment record in our database
            payment = Payment.objects.get(order_reference=order_reference)

            # Compare amounts and set status
            if amount_received < payment.expected_amount:
                payment.status = Payment.Status.UNDERPAID
            elif amount_received > payment.expected_amount:
                payment.status = Payment.Status.OVERPAID
            else:
                payment.status = Payment.Status.CONFIRMED

            payment.amount_received = amount_received
            payment.confirmed_at = timezone.now()
            payment.save()

        except Payment.DoesNotExist:
            pass  # Payment not found - log it but don't crash
        except Exception:
            pass  # Don't crash the webhook response
