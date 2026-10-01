"""Query-budget and concurrency regressions for role visibility grants."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from django.db import close_old_connections, connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from gym_app.models import User
from gym_app.models.dynamic_document import (
    DocumentVisibilityPermission,
    DynamicDocument,
)
from gym_app.views.dynamic_documents.permission_views import (
    MAX_ROLE_VISIBILITY_QUERIES,
    _grant_role_visibility,
)

pytestmark = pytest.mark.django_db


def _lawyer():
    return User.objects.create_user(
        email="visibility-owner@test.com",
        password="testpassword",
        first_name="Visibility",
        last_name="Owner",
        role="lawyer",
        is_gym_lawyer=True,
    )


def _document(owner, public=False):
    return DynamicDocument.objects.create(
        title="Role visibility document",
        content="<p>content</p>",
        state="Draft",
        created_by=owner,
        is_public=public,
    )


def _role_users(count):
    roles = ("client", "corporate_client", "basic")
    return [
        User.objects.create_user(
            email=f"role-visibility-{count}-{number}@test.com",
            password="testpassword",
            first_name="Role",
            last_name=f"User {number}",
            role=roles[number % len(roles)],
        )
        for number in range(count)
    ]


def _grant_and_count_queries(owner, count, existing_permission=False):
    document = _document(owner, public=True)
    users = _role_users(count)
    if existing_permission:
        DocumentVisibilityPermission.objects.create(
            document=document,
            user=users[0],
            granted_by=owner,
        )
    client = APIClient()
    client.force_authenticate(user=owner)
    url = reverse("grant-visibility-permissions-by-role", kwargs={"pk": document.pk})
    with CaptureQueriesContext(connection) as queries:
        response = client.post(
            url,
            {"roles": ["client", "corporate_client", "basic", "lawyer"]},
            format="json",
        )
    return document, users, response, len(queries)


def test_role_visibility_grant_keeps_query_count_constant_from_one_to_fifty_users():
    """Fails if role grants return to one permission query per user."""
    owner = _lawyer()
    baseline_document, baseline_users, _, one_user_queries = _grant_and_count_queries(
        owner, 1
    )
    baseline_document.delete()
    User.objects.filter(pk__in=[user.pk for user in baseline_users]).delete()

    _, _, response, fifty_user_queries = _grant_and_count_queries(owner, 50)

    assert response.status_code == 200
    assert one_user_queries == fifty_user_queries
    assert fifty_user_queries <= MAX_ROLE_VISIBILITY_QUERIES == 8


def test_role_visibility_grant_reports_existing_permissions_as_skipped_users():
    """Fails if an existing permission is reported as newly granted by a role request."""
    owner = _lawyer()
    document, users, response, _ = _grant_and_count_queries(
        owner, 50, existing_permission=True
    )
    payload = response.data
    expected_ids = {user.pk for user in users}
    granted_ids = {entry["user_id"] for entry in payload["granted_permissions"]}
    skipped_ids = {entry["user_id"] for entry in payload["skipped_users"]}

    assert response.status_code == 200
    assert payload["roles_processed"] == ["client", "corporate_client", "basic"]
    assert granted_ids | skipped_ids == expected_ids
    assert granted_ids.isdisjoint(skipped_ids)
    assert skipped_ids == {users[0].pk}
    assert len(granted_ids) == 49
    assert (
        payload["warning"]
        == "Note: Document is public, so all users already have access regardless of explicit permissions."
    )


def test_role_visibility_grant_is_idempotent_after_creating_missing_permissions():
    """Fails if a repeated role grant creates another visibility row for the same user."""
    owner = _lawyer()
    document, users, _, _ = _grant_and_count_queries(
        owner, 50, existing_permission=True
    )
    expected_ids = {user.pk for user in users}
    client = APIClient()
    client.force_authenticate(user=owner)
    repeat = client.post(
        reverse("grant-visibility-permissions-by-role", kwargs={"pk": document.pk}),
        {"roles": ["client", "corporate_client", "basic", "lawyer"]},
        format="json",
    )

    assert repeat.status_code == 200
    assert repeat.data["granted_permissions"] == []
    assert {entry["user_id"] for entry in repeat.data["skipped_users"]} == expected_ids
    assert DocumentVisibilityPermission.objects.filter(document=document).count() == 50


@pytest.mark.django_db(transaction=True)
@pytest.mark.skipif(
    not connection.features.has_select_for_update,
    reason="Real row-lock concurrency requires SELECT FOR UPDATE support",
)
def test_role_visibility_race_keeps_one_permission_per_user():
    """Fails if concurrent role grants leave duplicate visibility permissions for one user."""
    owner = _lawyer()
    document = _document(owner)
    recipient = _role_users(1)[0]
    workers_ready = Barrier(2)

    def grant_from_separate_connection():
        close_old_connections()
        try:
            users = User.objects.filter(pk=recipient.pk)
            workers_ready.wait()
            result = _grant_role_visibility(
                document, users, owner
            )
            return result[0][1]
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as executor:
        created_flags = list(
            executor.map(lambda _: grant_from_separate_connection(), range(2))
        )

    assert sorted(created_flags) == [False, True]
    assert (
        DocumentVisibilityPermission.objects.filter(
            document=document, user=recipient
        ).count()
        == 1
    )
