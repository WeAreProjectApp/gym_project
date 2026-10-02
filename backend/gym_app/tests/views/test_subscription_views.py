"""Tests for subscription_views module."""
import hashlib
import hmac
import json
import logging
import unittest.mock as mock
from datetime import date
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from requests.exceptions import RequestException
from rest_framework import status

from gym_app.models import PaymentHistory, Subscription

User = get_user_model()
FIXED_BILLING_DATE = date(2099, 1, 1)


@pytest.fixture
def subscription_user():
    """Subscription user."""
    return User.objects.create_user(
        email="subscriber@example.com",
        password="testpassword",
        first_name="Sub",
        last_name="User",
        role="basic",
    )


@pytest.fixture
def wompi_settings(settings):
    """Wompi settings."""
    settings.WOMPI_PUBLIC_KEY = "pub_test_123"
    settings.WOMPI_ENVIRONMENT = "test"
    settings.WOMPI_INTEGRITY_KEY = "integrity_test_key"
    settings.WOMPI_API_URL = "https://sandbox.wompi.co/v1"
    settings.WOMPI_PRIVATE_KEY = "priv_test_123"
    settings.WOMPI_EVENTS_KEY = "events_test_key"
    return settings


@pytest.mark.django_db
class TestWompiConfigAndSignature:
    """Tests for Wompi Config And Signature."""

    def test_get_wompi_config(self, api_client, wompi_settings):
        """Verify get wompi config."""
        url = reverse("subscription-wompi-config")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["public_key"] == wompi_settings.WOMPI_PUBLIC_KEY
        assert response.data["environment"] == wompi_settings.WOMPI_ENVIRONMENT

    def test_generate_signature_unauthenticated(self, api_client, wompi_settings):
        """Verify generate signature unauthenticated."""
        url = reverse("subscription-generate-signature")
        payload = {"amount_in_cents": 1000, "reference": "REF123"}

        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_generate_signature_missing_fields_authenticated(self, api_client, subscription_user, wompi_settings):
        """Verify generate signature missing fields authenticated."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-generate-signature")

        response = api_client.post(url, {"amount_in_cents": 1000}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "amount_in_cents and reference are required" in response.data["error"]

    def test_generate_signature_emits_safe_log_event(self, api_client, subscription_user, wompi_settings, caplog):
        """Fails if generating a signature logs payment signing material."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-generate-signature")

        wompi_settings.WOMPI_INTEGRITY_KEY = "distinct-integrity-key-9876543210"
        payload = {"amount_in_cents": 5000, "currency": "COP", "reference": "REF-UNIQUE-999"}
        expected_concatenated = f"{payload['reference']}{payload['amount_in_cents']}{payload['currency']}{wompi_settings.WOMPI_INTEGRITY_KEY}"
        expected_signature = hashlib.sha256(expected_concatenated.encode()).hexdigest()

        with caplog.at_level(logging.INFO, logger="gym_app.views.subscription"):
            response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        assert response.data["signature"] == expected_signature
        module_messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == "gym_app.views.subscription"
        ]
        assert module_messages == ["Wompi integrity signature generated"]
        assert wompi_settings.WOMPI_INTEGRITY_KEY not in caplog.text
        assert wompi_settings.WOMPI_INTEGRITY_KEY[:20] not in caplog.text
        assert expected_concatenated not in caplog.text
        assert expected_signature not in caplog.text


@pytest.mark.django_db
class TestCreateSubscription:
    """Tests for Create Subscription."""

    def test_create_subscription_unauthenticated(self, api_client):
        """Verify create subscription unauthenticated."""
        url = reverse("subscription-create")
        response = api_client.post(url, {"plan_type": "basico"}, format="json")
        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_create_subscription_missing_plan_type(self, api_client, subscription_user):
        """Verify create subscription missing plan type."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "plan_type is required"

    def test_create_subscription_invalid_plan_type(self, api_client, subscription_user):
        """Verify create subscription invalid plan type."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        response = api_client.post(url, {"plan_type": "invalid"}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Invalid plan_type. Must be: basico, cliente, or corporativo" in response.data["error"]

    def test_create_free_subscription_basico(self, api_client, subscription_user):
        """Verify create free subscription basico."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        response = api_client.post(url, {"plan_type": "basico"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        # Subscription created
        sub = Subscription.objects.get(user=subscription_user)
        assert sub.plan_type == "basico"
        assert sub.status == "active"
        assert sub.amount == Decimal("0.00")
        # User role updated accordingly
        subscription_user.refresh_from_db()
        assert subscription_user.role == "basic"

    @pytest.mark.contract
    def test_create_subscription_response_contract(self, api_client, subscription_user):
        """Verify create subscription response contract."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        response = api_client.post(url, {"plan_type": "basico"}, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        assert set(response.data.keys()) == {
            "subscription_id",
            "plan_type",
            "status",
            "amount",
            "next_billing_date",
            "user_role",
            "message",
        }

    def test_create_paid_subscription_with_existing_payment_source(self, api_client, subscription_user):
        """Verify create paid subscription with existing payment source."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        payload = {"plan_type": "cliente", "payment_source_id": "src_test_123"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        sub = Subscription.objects.get(user=subscription_user)
        assert sub.plan_type == "cliente"
        assert sub.payment_source_id == "src_test_123"
        subscription_user.refresh_from_db()
        assert subscription_user.role == "client"

    def test_create_paid_subscription_missing_session_and_token(self, api_client, subscription_user):
        """Verify create paid subscription missing session and token."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        payload = {"plan_type": "corporativo"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "session_id and token are required for paid plans"

    @mock.patch("gym_app.views.subscription.requests.post")
    @mock.patch("gym_app.views.subscription.requests.get")
    def test_create_paid_subscription_with_session_and_token_success(
        self,
        mock_get,
        mock_post,
        api_client,
        subscription_user,
        wompi_settings,
    ):
        """Verify create paid subscription with session and token success."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        # Mock merchant info with acceptance tokens
        merchant_resp = mock.Mock()
        merchant_resp.raise_for_status.return_value = None
        merchant_resp.json.return_value = {
            "data": {
                "presigned_acceptance": {"acceptance_token": "acc_token"},
                "presigned_personal_data_auth": {"acceptance_token": "personal_token"},
            }
        }
        mock_get.return_value = merchant_resp

        # Mock successful payment source creation
        ps_response = mock.Mock()
        ps_response.status_code = 200
        ps_response.json.return_value = {"data": {"id": "src_from_wompi"}}
        mock_post.return_value = ps_response

        payload = {"plan_type": "cliente", "session_id": "sess_1", "token": "card_tok"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_201_CREATED
        sub = Subscription.objects.get(user=subscription_user)
        assert sub.payment_source_id == "src_from_wompi"
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @mock.patch("gym_app.views.subscription.requests.get")
    def test_create_paid_subscription_error_fetching_tokens(self, mock_get, api_client, subscription_user, wompi_settings):
        """Verify create paid subscription error fetching tokens."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        # Simulate network error when fetching merchant info
        mock_get.side_effect = RequestException("boom")

        payload = {"plan_type": "cliente", "session_id": "sess_1", "token": "card_tok"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert "Error fetching acceptance tokens from Wompi" in response.data["error"]
        mock_get.assert_called_once()

    @pytest.mark.edge
    @mock.patch("gym_app.views.subscription.requests.post")
    @mock.patch("gym_app.views.subscription.requests.get")
    def test_create_paid_subscription_wompi_payment_source_error(
        self,
        mock_get,
        mock_post,
        api_client,
        subscription_user,
        wompi_settings,
    ):
        """Verify create paid subscription wompi payment source error."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        merchant_resp = mock.Mock()
        merchant_resp.raise_for_status.return_value = None
        merchant_resp.json.return_value = {
            "data": {
                "presigned_acceptance": {"acceptance_token": "acc_token"},
                "presigned_personal_data_auth": {"acceptance_token": "personal_token"},
            }
        }
        mock_get.return_value = merchant_resp

        ps_response = mock.Mock()
        ps_response.status_code = 400
        ps_response.json.return_value = {"error": "bad"}
        mock_post.return_value = ps_response

        payload = {"plan_type": "cliente", "session_id": "sess_1", "token": "card_tok"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.data["error"] == "Error creating payment source with Wompi"
        assert response.data["wompi_status"] == 400
        assert not Subscription.objects.filter(user=subscription_user).exists()
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    @pytest.mark.edge
    @mock.patch("gym_app.views.subscription.requests.post")
    @mock.patch("gym_app.views.subscription.requests.get")
    def test_create_paid_subscription_wompi_payment_source_missing_id(
        self,
        mock_get,
        mock_post,
        api_client,
        subscription_user,
        wompi_settings,
    ):
        """Verify create paid subscription wompi payment source missing id."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-create")

        merchant_resp = mock.Mock()
        merchant_resp.raise_for_status.return_value = None
        merchant_resp.json.return_value = {
            "data": {
                "presigned_acceptance": {"acceptance_token": "acc_token"},
                "presigned_personal_data_auth": {"acceptance_token": "personal_token"},
            }
        }
        mock_get.return_value = merchant_resp

        ps_response = mock.Mock()
        ps_response.status_code = 200
        ps_response.json.return_value = {"data": {}}
        mock_post.return_value = ps_response

        payload = {"plan_type": "cliente", "session_id": "sess_1", "token": "card_tok"}
        response = api_client.post(url, payload, format="json")

        assert response.status_code == status.HTTP_502_BAD_GATEWAY
        assert response.data["error"] == "Invalid response from Wompi while creating payment source"
        assert not Subscription.objects.filter(user=subscription_user).exists()
        mock_get.assert_called_once()
        mock_post.assert_called_once()


@pytest.mark.django_db
class TestSubscriptionManagement:
    """Tests for Subscription Management."""

    def test_get_current_subscription_no_active(self, api_client, subscription_user):
        """Verify get current subscription no active."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-current")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["subscription"] is None
        assert response.data["message"] == "No active subscription found"

    def test_get_current_subscription_with_active(self, api_client, subscription_user):
        """Verify get current subscription with active."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-current")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data["id"] == sub.id
        assert response.data["plan_type"] == sub.plan_type

    def test_cancel_subscription_no_active(self, api_client, subscription_user):
        """Verify cancel subscription no active."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-cancel")

        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "No active subscription found"

    def test_cancel_subscription_success(self, api_client, subscription_user):
        """Verify cancel subscription success."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-cancel")

        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        sub.refresh_from_db()
        assert sub.status == "cancelled"
        subscription_user.refresh_from_db()
        assert subscription_user.role == "basic"

    def test_cancel_subscription_already_cancelled(self, api_client, subscription_user):
        """Verify cancel subscription already cancelled."""
        _sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="cancelled",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-cancel")

        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Subscription is already cancelled"

    def test_update_payment_method_missing_payment_source_id(self, api_client, subscription_user):
        """Verify update payment method missing payment source id."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-update-payment-method")

        response = api_client.patch(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "payment_source_id is required"

    def test_update_payment_method_no_active_subscription(self, api_client, subscription_user):
        """Verify update payment method no active subscription."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-update-payment-method")

        response = api_client.patch(url, {"payment_source_id": "src_new"}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "No active subscription found"

    def test_update_payment_method_success(self, api_client, subscription_user):
        """Verify update payment method success."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
            payment_source_id="src_old",
        )
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-update-payment-method")

        response = api_client.patch(
            url, {"payment_source_id": "src_new"}, format="json"
        )

        assert response.status_code == status.HTTP_200_OK
        sub.refresh_from_db()
        assert sub.payment_source_id == "src_new"

    def test_get_payment_history_success(self, api_client, subscription_user):
        """Verify get payment history success."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        PaymentHistory.objects.create(
            subscription=sub,
            amount=Decimal("50000.00"),
            status="approved",
            reference="REF-1",
        )
        # Another user's payment should not appear
        other_user = User.objects.create_user(
            email="other@example.com",
            password="testpassword",
        )
        other_sub = Subscription.objects.create(
            user=other_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        PaymentHistory.objects.create(
            subscription=other_sub,
            amount=Decimal("50000.00"),
            status="approved",
            reference="REF-2",
        )

        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-payments")

        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]["reference"] == "REF-1"


@pytest.mark.django_db
class TestWompiWebhook:
    """Tests for Wompi Webhook."""

    def test_wompi_webhook_missing_signature(self, api_client, wompi_settings):
        """Verify wompi webhook missing signature."""
        url = reverse("subscription-webhook")
        payload = {"event": "transaction.updated", "data": {}}
        raw_body = json.dumps(payload)

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
        )

        assert response.status_code == 400
        assert response.json()["error"] == "Missing signature"

    def test_wompi_webhook_invalid_signature(self, api_client, wompi_settings):
        """Verify wompi webhook invalid signature."""
        url = reverse("subscription-webhook")
        payload = {"event": "transaction.updated", "data": {}}
        raw_body = json.dumps(payload)

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE="invalid_signature",
        )

        assert response.status_code == 401
        assert response.json()["error"] == "Invalid signature"

    def test_wompi_webhook_invalid_json(self, api_client, wompi_settings):
        """Verify wompi webhook invalid json."""
        url = reverse("subscription-webhook")
        raw_body = "{bad-json"
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 400
        assert response.json()["error"] == "Invalid JSON"

    def test_wompi_webhook_missing_transaction_data(self, api_client, wompi_settings):
        """Verify wompi webhook missing transaction data."""
        url = reverse("subscription-webhook")
        payload = {"event": "transaction.updated", "data": {}}
        raw_body = json.dumps(payload)
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 400
        assert response.json()["error"] == "Missing transaction data"

    def test_wompi_webhook_subscription_approved(self, api_client, subscription_user, wompi_settings):
        """Verify wompi webhook subscription approved."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="expired",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )

        url = reverse("subscription-webhook")
        reference = f"SUB-{sub.id}-20240101010101"
        payload = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "trx_1",
                    "status": "APPROVED",
                    "reference": reference,
                }
            },
        }
        raw_body = json.dumps(payload)
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 200
        body = response.json()
        assert body["status"] == "success"
        sub.refresh_from_db()
        assert sub.status == "active"
        subscription_user.refresh_from_db()
        assert subscription_user.role == "client"

    def test_wompi_webhook_subscription_declined(self, api_client, subscription_user, wompi_settings):
        """Verify wompi webhook subscription declined."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )

        url = reverse("subscription-webhook")
        reference = f"SUB-{sub.id}-20240101010101"
        payload = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "trx_2",
                    "status": "DECLINED",
                    "reference": reference,
                }
            },
        }
        raw_body = json.dumps(payload)
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 200
        sub.refresh_from_db()
        assert sub.status == "expired"
        subscription_user.refresh_from_db()
        assert subscription_user.role == "basic"

    @pytest.mark.parametrize("status_value", ["VOIDED", "ERROR"])
    def test_wompi_webhook_subscription_voided_or_error(self, api_client, subscription_user, wompi_settings, status_value):
        """Verify wompi webhook subscription voided or error."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )

        url = reverse("subscription-webhook")
        reference = f"SUB-{sub.id}-20240101010101"
        payload = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "trx_3",
                    "status": status_value,
                    "reference": reference,
                }
            },
        }
        raw_body = json.dumps(payload)
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 200
        sub.refresh_from_db()
        assert sub.status == "active"

    def test_wompi_webhook_invalid_reference_format(self, api_client, wompi_settings):
        """Verify wompi webhook invalid reference format."""
        url = reverse("subscription-webhook")
        payload = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "trx_4",
                    "status": "APPROVED",
                    "reference": "SUB-INVALID",
                }
            },
        }
        raw_body = json.dumps(payload)
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"

    def test_wompi_webhook_subscription_not_found(self, api_client, wompi_settings):
        """Verify wompi webhook subscription not found."""
        url = reverse("subscription-webhook")
        payload = {
            "event": "transaction.updated",
            "data": {
                "transaction": {
                    "id": "trx_5",
                    "status": "APPROVED",
                    "reference": "SUB-9999-20240101010101",
                }
            },
        }
        raw_body = json.dumps(payload)
        expected_signature = hmac.new(
            wompi_settings.WOMPI_EVENTS_KEY.encode(),
            raw_body.encode(),
            hashlib.sha256,
        ).hexdigest()

        response = api_client.post(
            url,
            data=raw_body,
            content_type="application/json",
            HTTP_X_WOMPI_SIGNATURE=expected_signature,
        )

        assert response.status_code == 200
        assert response.json()["status"] == "success"


@pytest.mark.django_db
class TestCancelSubscriptionById:
    """Tests for Cancel Subscription By Id."""

    def test_cancel_subscription_view_success(self, api_client, subscription_user):
        """Verify cancel subscription view success."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="active",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-cancel-by-id", kwargs={"subscription_id": sub.id})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_200_OK
        sub.refresh_from_db()
        assert sub.status == "cancelled"
        subscription_user.refresh_from_db()
        assert subscription_user.role == "basic"
        assert response.data["message"] == "Subscription cancelled successfully"

    def test_cancel_subscription_view_not_found(self, api_client, subscription_user):
        """Verify cancel subscription view not found."""
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-cancel-by-id", kwargs={"subscription_id": 9999})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data["error"] == "Subscription not found"

    def test_cancel_subscription_view_already_cancelled(self, api_client, subscription_user):
        """Verify cancel subscription view already cancelled."""
        sub = Subscription.objects.create(
            user=subscription_user,
            plan_type="cliente",
            status="cancelled",
            next_billing_date=FIXED_BILLING_DATE,
            amount=Decimal("50000.00"),
        )
        api_client.force_authenticate(user=subscription_user)
        url = reverse("subscription-cancel-by-id", kwargs={"subscription_id": sub.id})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.data["error"] == "Subscription is already cancelled"


# ======================================================================
# Tests merged from test_subscription_coverage.py
# ======================================================================

"""Tests for uncovered branches in subscription.py (91%→higher)."""
import hashlib  # noqa: F811
import hmac  # noqa: F811
import json  # noqa: F811
from datetime import timedelta
from decimal import Decimal  # noqa: F811
from unittest import mock

import pytest
from django.conf import settings
from django.urls import reverse  # noqa: F811
from rest_framework import status  # noqa: F811

from gym_app.models import Subscription, User  # noqa: F811


@pytest.fixture
def client_u():
    """Client u."""
    return User.objects.create_user(
        email='cli_sc@e.com', password='p', role='client',
        first_name='C', last_name='S')


@pytest.fixture
def active_sub(client_u):
    """Active sub."""
    return Subscription.objects.create(
        user=client_u, plan_type='cliente', status='active',
        amount=Decimal('50000.00'),
        next_billing_date=FIXED_BILLING_DATE + timedelta(days=30))


@pytest.mark.django_db
class TestSubscriptionRegressionScenarios:
    """Tests for Subscription Regression Scenarios."""

    # --- create_subscription: Wompi merchant fetch fails (lines 198-203) ---
    def test_create_sub_wompi_merchant_error(self, api_client, client_u):
        """Lines 198-203: requests.RequestException fetching merchant tokens."""
        api_client.force_authenticate(user=client_u)
        import requests as req_lib
        with mock.patch.object(
            req_lib, 'get', side_effect=req_lib.RequestException('timeout')
        ):
            r = api_client.post(
                reverse('subscription-create'),
                {'plan_type': 'cliente', 'session_id': 's1', 'token': 't1'},
                format='json')
        assert r.status_code == 502
        assert 'acceptance tokens' in r.data['error']

    # --- create_subscription: missing acceptance tokens (lines 205-210) ---
    def test_create_sub_missing_acceptance_tokens(self, api_client, client_u):
        """Lines 205-210: Wompi merchant returns empty tokens."""
        api_client.force_authenticate(user=client_u)
        from types import SimpleNamespace
        mock_resp = SimpleNamespace(
            status_code=200,
            json=lambda: {'data': {}},
            raise_for_status=lambda: None
        )
        with mock.patch('requests.get', return_value=mock_resp) as mock_get:
            r = api_client.post(
                reverse('subscription-create'),
                {'plan_type': 'cliente', 'session_id': 's1', 'token': 't1'},
                format='json')
        assert r.status_code == 502
        assert 'Invalid acceptance tokens' in r.data['error']
        mock_get.assert_called_once()

    # --- create_subscription: payment source API error (lines 240-252) ---
    def test_create_sub_payment_source_api_error(self, api_client, client_u):
        """Lines 240-252: Wompi payment source returns 4xx."""
        api_client.force_authenticate(user=client_u)
        from types import SimpleNamespace
        merchant_resp = SimpleNamespace(
            status_code=200,
            json=lambda: {
                'data': {
                    'presigned_acceptance': {'acceptance_token': 'tok_a'},
                    'presigned_personal_data_auth': {'acceptance_token': 'tok_p'},
                }
            },
            raise_for_status=lambda: None
        )

        ps_resp = SimpleNamespace(
            status_code=422,
            json=lambda: {'error': 'invalid card'}
        )

        with mock.patch('requests.get', return_value=merchant_resp) as mock_get, \
             mock.patch('requests.post', return_value=ps_resp) as mock_post:
            r = api_client.post(
                reverse('subscription-create'),
                {'plan_type': 'cliente', 'session_id': 's1', 'token': 't1'},
                format='json')
        assert r.status_code == 502
        assert 'Error creating payment source' in r.data['error']
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    # --- create_subscription: payment source request exception (lines 262-267) ---
    def test_create_sub_payment_source_exception(self, api_client, client_u):
        """Lines 262-267: requests.RequestException creating payment source."""
        api_client.force_authenticate(user=client_u)
        from types import SimpleNamespace

        import requests as req_lib
        merchant_resp = SimpleNamespace(
            status_code=200,
            json=lambda: {
                'data': {
                    'presigned_acceptance': {'acceptance_token': 'tok_a'},
                    'presigned_personal_data_auth': {'acceptance_token': 'tok_p'},
                }
            },
            raise_for_status=lambda: None
        )

        with mock.patch('requests.get', return_value=merchant_resp) as mock_get, \
             mock.patch('requests.post',
                        side_effect=req_lib.RequestException('conn err')) as mock_post:
            r = api_client.post(
                reverse('subscription-create'),
                {'plan_type': 'cliente', 'session_id': 's1', 'token': 't1'},
                format='json')
        assert r.status_code == 502
        assert 'Error creating payment source' in r.data['error']
        mock_get.assert_called_once()
        mock_post.assert_called_once()

    # --- wompi_webhook: invalid JSON (lines 581-583) ---
    def test_webhook_invalid_json(self, api_client):
        """Lines 581-583: invalid JSON in webhook payload."""
        raw = 'not json{{{'
        sig = hmac.new(
            settings.WOMPI_EVENTS_KEY.encode(),
            raw.encode(), hashlib.sha256).hexdigest()
        r = api_client.post(
            reverse('subscription-webhook'),
            raw, content_type='application/json',
            HTTP_X_WOMPI_SIGNATURE=sig)
        assert r.status_code == 400

    # --- wompi_webhook: DECLINED transaction (lines 554-563) ---
    def test_webhook_declined_transaction(self, api_client, active_sub):
        """Lines 554-563: DECLINED transaction downgrades user."""
        event = {
            'event': 'transaction.updated',
            'data': {'transaction': {
                'id': 'tx1',
                'status': 'DECLINED',
                'reference': f'SUB-{active_sub.id}-12345'
            }}
        }
        raw = json.dumps(event)
        sig = hmac.new(
            settings.WOMPI_EVENTS_KEY.encode(),
            raw.encode(), hashlib.sha256).hexdigest()
        r = api_client.post(
            reverse('subscription-webhook'),
            raw, content_type='application/json',
            HTTP_X_WOMPI_SIGNATURE=sig)
        assert r.status_code == 200
        active_sub.refresh_from_db()
        assert active_sub.status == 'expired'
        active_sub.user.refresh_from_db()
        assert active_sub.user.role == 'basic'

    # --- wompi_webhook: generic exception (lines 584-586) ---
    def test_webhook_generic_exception(self, api_client):
        """Lines 584-586: generic exception returns 500."""
        raw = json.dumps({'event': 'test'})
        sig = hmac.new(
            settings.WOMPI_EVENTS_KEY.encode(),
            raw.encode(), hashlib.sha256).hexdigest()
        with mock.patch('json.loads', side_effect=RuntimeError('boom')):
            r = api_client.post(
                reverse('subscription-webhook'),
                raw, content_type='application/json',
                HTTP_X_WOMPI_SIGNATURE=sig)
        assert r.status_code == 500
