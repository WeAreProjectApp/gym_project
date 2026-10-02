import hashlib
import hmac
import json
import requests
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from gym_app.models import Subscription, PaymentHistory
from gym_app.serializers.subscription import SubscriptionSerializer, PaymentHistorySerializer

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_wompi_config(request):
    """
    Get Wompi public configuration.
    
    Returns:
        Response: JSON with Wompi public key
    """
    return Response({
        'public_key': settings.WOMPI_PUBLIC_KEY,
        'environment': settings.WOMPI_ENVIRONMENT
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_signature(request):
    """
    Generate integrity signature for Wompi transactions.
    
    This endpoint generates a SHA256 signature using Wompi's integrity key
    to ensure transaction security.
    
    Formula: SHA256(reference + amount_in_cents + currency + integrity_secret)
    Example: SHA256("sub_cliente_17661571663232290000COPtest_integrity_xxxxx")
    
    Args:
        request (Request): HTTP request containing:
            - amount_in_cents (int): Transaction amount in cents (COP)
            - currency (str): Currency code (e.g., 'COP')
            - reference (str): Unique transaction reference
    
    Returns:
        Response: JSON with the generated signature
    """
    amount_in_cents = request.data.get('amount_in_cents')
    currency = request.data.get('currency', 'COP')
    reference = request.data.get('reference')
    
    if not amount_in_cents or not reference:
        return Response(
            {'error': 'amount_in_cents and reference are required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Generate signature: SHA256(reference + amount_in_cents + currency + integrity_key)
    # NO separators between values - concatenate directly
    concatenated_string = f"{reference}{amount_in_cents}{currency}{settings.WOMPI_INTEGRITY_KEY}"
    signature = hashlib.sha256(concatenated_string.encode()).hexdigest()
    
    logger.info("Wompi integrity signature generated")
    
    return Response({
        'signature': signature
    }, status=status.HTTP_200_OK)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_subscription(request):
    """
    Create a new subscription and process the first payment with Wompi.
    
    This endpoint creates a subscription record in the database and processes
    the initial payment using Wompi's API.
    
    Args:
        request (Request): HTTP request containing:
            - plan_type (str): Type of plan (basico, cliente, corporativo)
            - payment_source_id (str): Wompi payment source token
    
    Returns:
        Response: JSON with subscription details and payment status
    """
    user = request.user
    plan_type = request.data.get('plan_type')
    # New contract: frontend sends session_id and token for paid plans
    session_id = request.data.get('session_id')
    card_token = request.data.get('token')
    # Backwards compatibility: allow payment_source_id if already created in Wompi
    existing_payment_source_id = request.data.get('payment_source_id')

    if not plan_type:
        return Response(
            {'error': 'plan_type is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    if plan_type not in ['basico', 'cliente', 'corporativo']:
        return Response(
            {'error': 'Invalid plan_type. Must be: basico, cliente, or corporativo'},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Define plan amounts (in COP)
    plan_amounts = {
        'basico': Decimal('0.00'),
        'cliente': Decimal('50000.00'),
        'corporativo': Decimal('150000.00'),
    }

    amount = plan_amounts[plan_type]

    # Calculate next billing date (30 days from now)
    next_billing_date = datetime.now().date() + timedelta(days=30)

    wompi_payment_source_id = None

    # Only create a payment source with Wompi for paid plans
    if amount > 0:
        # Prefer session_id + token (new contract). Fallback to existing_payment_source_id if provided.
        if existing_payment_source_id:
            # Assume client already created a payment source in Wompi and sent its id
            wompi_payment_source_id = existing_payment_source_id
        else:
            if not session_id or not card_token:
                return Response(
                    {'error': 'session_id and token are required for paid plans'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Fetch acceptance tokens from Wompi merchant info
            acceptance_token = None
            personal_auth_token = None
            merchant_body = None

            try:
                merchant_resp = requests.get(
                    f"{settings.WOMPI_API_URL}/merchants/{settings.WOMPI_PUBLIC_KEY}",
                    timeout=10,
                )
                merchant_resp.raise_for_status()
                merchant_body = merchant_resp.json()

                presigned_acceptance = merchant_body.get('data', {}).get('presigned_acceptance', {})
                presigned_personal = merchant_body.get('data', {}).get('presigned_personal_data_auth', {})

                acceptance_token = presigned_acceptance.get('acceptance_token')
                personal_auth_token = presigned_personal.get('acceptance_token')

            except requests.RequestException as e:
                logger.error("Error fetching Wompi acceptance tokens: %s", str(e))
                return Response(
                    {'error': 'Error fetching acceptance tokens from Wompi', 'details': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            if not acceptance_token or not personal_auth_token:
                logger.error("Missing acceptance tokens in Wompi merchant response: %s", merchant_body)
                return Response(
                    {'error': 'Invalid acceptance tokens from Wompi', 'wompi_response': merchant_body},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            # Create payment source in Wompi using session_id, card token and acceptance tokens
            payment_source_payload = {
                "session_id": session_id,
                "type": "CARD",
                "token": card_token,
                "customer_email": user.email,
                "acceptance_token": acceptance_token,
                "accept_personal_auth": personal_auth_token,
                "customer_data": {
                    "full_name": f"{user.first_name} {user.last_name}".strip() or user.email,
                },
            }

            headers = {
                "Authorization": f"Bearer {settings.WOMPI_PRIVATE_KEY}",
                "Content-Type": "application/json",
            }

            try:
                logger.info("Creating Wompi payment source for user %s", user.id)
                ps_response = requests.post(
                    f"{settings.WOMPI_API_URL}/payment_sources",
                    json=payment_source_payload,
                    headers=headers,
                    timeout=10,
                )
                try:
                    ps_body = ps_response.json()
                except ValueError:
                    ps_body = ps_response.text

                if ps_response.status_code >= 400:
                    logger.error("Wompi payment source error (status %s): %s", ps_response.status_code, ps_body)
                    return Response(
                        {
                            'error': 'Error creating payment source with Wompi',
                            'wompi_status': ps_response.status_code,
                            'wompi_response': ps_body,
                        },
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

                wompi_payment_source_id = ps_body.get('data', {}).get('id') if isinstance(ps_body, dict) else None
                if not wompi_payment_source_id:
                    logger.error("Wompi payment source response missing id: %s", ps_body)
                    return Response(
                        {'error': 'Invalid response from Wompi while creating payment source', 'wompi_response': ps_body},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )

            except requests.RequestException as e:
                logger.error("Error creating Wompi payment source: %s", str(e))
                return Response(
                    {'error': 'Error creating payment source with Wompi', 'details': str(e)},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

    # Create subscription in database
    try:
        subscription = Subscription.objects.create(
            user=user,
            plan_type=plan_type,
            payment_source_id=wompi_payment_source_id,
            status='active',
            next_billing_date=next_billing_date,
            amount=amount,
        )

        # Update user role based on plan type
        role_mapping = {
            'basico': 'basic',
            'cliente': 'client',
            'corporativo': 'corporate_client',
        }
        user.role = role_mapping[plan_type]
        user.save()

        return Response({
            'subscription_id': subscription.id,
            'plan_type': subscription.plan_type,
            'status': subscription.status,
            'amount': str(subscription.amount),
            'next_billing_date': subscription.next_billing_date.isoformat(),
            'user_role': user.role,
            'message': 'Subscription created successfully',
        }, status=status.HTTP_201_CREATED)

    except Exception as e:
        logger.error("Error creating subscription: %s", str(e))
        return Response(
            {'error': 'Error creating subscription', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_current_subscription(request):
    """
    Get the current active subscription for the authenticated user.
    
    Returns:
        Response: JSON with current subscription details or null if no active subscription
    """
    try:
        subscription = Subscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not subscription:
            return Response({
                'subscription': None,
                'message': 'No active subscription found'
            }, status=status.HTTP_200_OK)
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': 'Error retrieving subscription', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def cancel_subscription(request):
    """
    Cancel the current active subscription for the authenticated user.
    
    Returns:
        Response: JSON with cancelled subscription details
    """
    try:
        # Look for an active subscription first
        active_subscription = Subscription.objects.filter(
            user=request.user,
            status='active',
        ).first()

        # If there is no active subscription, check if there is a cancelled one
        if not active_subscription:
            cancelled_subscription = Subscription.objects.filter(
                user=request.user,
                status='cancelled',
            ).first()

            if cancelled_subscription:
                return Response(
                    {'error': 'Subscription is already cancelled'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND,
            )

        subscription = active_subscription
        
        # Cancel the subscription
        subscription.status = 'cancelled'
        subscription.save()

        # Update user role to basic
        request.user.role = 'basic'
        request.user.save()
        
        logger.info(f"User {request.user.id} cancelled subscription {subscription.id}")
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': 'Error cancelling subscription', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_payment_method(request):
    """
    Update the payment method for the current active subscription.
    
    Args:
        request (Request): HTTP request containing:
            - payment_source_id (str): New Wompi payment source token
    
    Returns:
        Response: JSON with updated subscription details
    """
    payment_source_id = request.data.get('payment_source_id')
    
    if not payment_source_id:
        return Response(
            {'error': 'payment_source_id is required'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        subscription = Subscription.objects.filter(
            user=request.user,
            status='active'
        ).first()
        
        if not subscription:
            return Response(
                {'error': 'No active subscription found'},
                status=status.HTTP_404_NOT_FOUND
            )
        
        # Update payment source
        subscription.payment_source_id = payment_source_id
        subscription.save()
        
        logger.info(f"User {request.user.id} updated payment method for subscription {subscription.id}")
        
        serializer = SubscriptionSerializer(subscription)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': 'Error updating payment method', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_payment_history(request):
    """
    Get payment history for the authenticated user's subscriptions.
    
    Returns:
        Response: JSON array with payment history
    """
    try:
        # Get all subscriptions for the user
        subscriptions = Subscription.objects.filter(user=request.user)
        
        # Get all payments for these subscriptions
        payments = PaymentHistory.objects.filter(
            subscription__in=subscriptions
        ).order_by('-payment_date')
        
        serializer = PaymentHistorySerializer(payments, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
        
    except Exception as e:
        return Response(
            {'error': 'Error retrieving payment history', 'details': str(e)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@csrf_exempt
@api_view(['POST'])
@permission_classes([AllowAny])
def wompi_webhook(request):
    """
    Webhook endpoint to receive payment notifications from Wompi.
    
    This endpoint receives and processes payment status updates from Wompi.
    It validates the signature to ensure the request is authentic and updates
    the subscription status accordingly.
    
    Args:
        request (Request): HTTP request containing Wompi event data
    
    Returns:
        JsonResponse: Acknowledgment response
    """
    try:
        # Get the signature from headers
        signature_header = request.META.get('HTTP_X_WOMPI_SIGNATURE')
        
        if not signature_header:
            logger.warning("Webhook received without signature")
            return JsonResponse({'error': 'Missing signature'}, status=400)
        
        # Get raw body for signature validation
        raw_body = request.body.decode('utf-8')
        
        # Validate signature using events key
        expected_signature = hmac.new(
            settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256
        ).hexdigest()
        
        if not hmac.compare_digest(signature_header, expected_signature):
            logger.warning("Invalid webhook signature")
            return JsonResponse({'error': 'Invalid signature'}, status=401)
        
        # Parse the event data
        event_data = json.loads(raw_body)
        
        # Extract event information
        event_type = event_data.get('event')
        transaction_data = event_data.get('data', {}).get('transaction', {})
        
        if not transaction_data:
            logger.warning("Webhook received without transaction data")
            return JsonResponse({'error': 'Missing transaction data'}, status=400)
        
        # Get transaction details
        transaction_id = transaction_data.get('id')
        transaction_status = transaction_data.get('status')
        reference = transaction_data.get('reference', '')
        
        logger.info(f"Webhook received: {event_type} - Transaction {transaction_id} - Status: {transaction_status}")
        
        # Process only subscription-related transactions
        if reference.startswith('SUB-'):
            # Extract subscription ID from reference (format: SUB-{subscription_id}-{timestamp})
            try:
                subscription_id = int(reference.split('-')[1])
                subscription = Subscription.objects.get(id=subscription_id)
                
                # Update subscription based on transaction status
                if transaction_status == 'APPROVED':
                    # Payment successful
                    if subscription.status != 'active':
                        subscription.status = 'active'
                        subscription.save()
                        
                        # Update user role if needed
                        role_mapping = {
                            'basico': 'basic',
                            'cliente': 'client',
                            'corporativo': 'corporate_client',
                        }
                        expected_role = role_mapping.get(subscription.plan_type)
                        if subscription.user.role != expected_role:
                            subscription.user.role = expected_role
                            subscription.user.save()
                    
                    logger.info(f"Subscription {subscription_id} payment approved")
                    
                elif transaction_status == 'DECLINED':
                    # Payment failed
                    subscription.status = 'expired'
                    subscription.save()
                    
                    # Downgrade user to basic
                    subscription.user.role = 'basic'
                    subscription.user.save()
                    
                    logger.warning(f"Subscription {subscription_id} payment declined")
                    
                elif transaction_status == 'VOIDED':
                    # Payment voided/cancelled
                    logger.info(f"Subscription {subscription_id} payment voided")
                    
                elif transaction_status == 'ERROR':
                    # Payment error
                    logger.error(f"Subscription {subscription_id} payment error")
                
            except (IndexError, ValueError):
                logger.error(f"Invalid subscription reference format: {reference}")
            except Subscription.DoesNotExist:
                logger.error(f"Subscription not found for reference: {reference}")
        
        # Return success response
        return JsonResponse({'status': 'success', 'message': 'Webhook processed'}, status=200)
        
    except json.JSONDecodeError:
        logger.error("Invalid JSON in webhook payload")
        return JsonResponse({'error': 'Invalid JSON'}, status=400)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return JsonResponse({'error': 'Internal server error'}, status=500)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def cancel_subscription_view(request, subscription_id):
    """
    Cancel a user's subscription.
    
    Args:
        request (Request): HTTP request
        subscription_id (int): ID of the subscription to cancel
    
    Returns:
        Response: Cancellation confirmation
    """
    try:
        subscription = Subscription.objects.get(id=subscription_id, user=request.user)
        
        if subscription.status == 'cancelled':
            return Response(
                {'error': 'Subscription is already cancelled'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Cancel the subscription
        subscription.status = 'cancelled'
        subscription.save()
        
        # Update user role to basic
        request.user.role = 'basic'
        request.user.save()
        
        logger.info(f"User {request.user.id} cancelled subscription {subscription_id}")
        
        return Response({
            'message': 'Subscription cancelled successfully',
            'subscription_id': subscription.id,
            'status': subscription.status
        }, status=status.HTTP_200_OK)
        
    except Subscription.DoesNotExist:
        return Response(
            {'error': 'Subscription not found'},
            status=status.HTTP_404_NOT_FOUND
        )
