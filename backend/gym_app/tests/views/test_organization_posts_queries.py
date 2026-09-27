"""Query contracts for private and member organization-post lists."""

import pytest
from django.contrib.auth import get_user_model
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework import status

from gym_app.models import Organization, OrganizationMembership, OrganizationPost

User = get_user_model()
MAX_CORPORATE_ORGANIZATION_POST_LIST_QUERIES = 3
MAX_MEMBER_ORGANIZATION_POST_LIST_QUERIES = 4


def _create_user(role, suffix):
    """Create an organization-post actor with a visible full name."""
    return User.objects.create_user(
        email=f"organization-posts-{role}-{suffix}@example.com",
        password=None,
        first_name="Post",
        last_name=suffix,
        role=role,
    )


def _create_organization(owner, suffix):
    """Create an organization whose valid post author is its corporate owner."""
    return Organization.objects.create(
        title=f"Post organization {suffix}",
        description="Organization post list budget fixture",
        corporate_client=owner,
    )


def _create_posts(organization, author, start, count, is_active=True):
    """Create post rows outside request capture without changing author validity."""
    return [
        OrganizationPost.objects.create(
            title=f"Post {index}",
            content=f"Post content {index}",
            organization=organization,
            author=author,
            is_active=is_active,
        )
        for index in range(start, start + count)
    ]


@pytest.mark.django_db
def test_corporate_organization_post_list_keeps_author_queries_constant(api_client):
    """Fails if private post serialization resumes one author query for every post."""
    owner = _create_user("corporate_client", "owner")
    organization = _create_organization(owner, "corporate")
    _create_posts(organization, owner, 0, 50)
    api_client.force_authenticate(user=owner)
    url = reverse("get-organization-posts", kwargs={"organization_id": organization.pk})

    with CaptureQueriesContext(connection) as one_post_queries:
        one_post_response = api_client.get(url, {"page_size": 1})
    with CaptureQueriesContext(connection) as fifty_post_queries:
        fifty_post_response = api_client.get(url, {"page_size": 50})

    owner_name = f"{owner.first_name} {owner.last_name}"
    assert (
        one_post_response.status_code,
        one_post_response.data["count"],
        len(one_post_response.data["results"]),
        one_post_response.data["results"][0]["author_name"],
    ) == (status.HTTP_200_OK, 50, 1, owner_name)
    assert (
        fifty_post_response.status_code,
        fifty_post_response.data["count"],
        len(fifty_post_response.data["results"]),
    ) == (status.HTTP_200_OK, 50, 50)
    assert {item["author_name"] for item in fifty_post_response.data["results"]} == {owner_name}
    assert len(one_post_queries) == len(fifty_post_queries)
    assert len(fifty_post_queries) <= MAX_CORPORATE_ORGANIZATION_POST_LIST_QUERIES


@pytest.mark.django_db
def test_corporate_organization_post_list_caps_requested_page_size(api_client):
    """Fails if a corporate post list permits a requested page larger than one hundred rows."""
    owner = _create_user("corporate_client", "page-cap")
    organization = _create_organization(owner, "page-cap")
    _create_posts(organization, owner, 0, 101)
    api_client.force_authenticate(user=owner)

    response = api_client.get(
        reverse("get-organization-posts", kwargs={"organization_id": organization.pk}),
        {"page_size": 999},
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["count"] == 101
    assert len(response.data["results"]) == 100


@pytest.mark.django_db
def test_member_organization_post_list_keeps_author_queries_constant(api_client):
    """Fails if member post serialization restores per-row author reads or exposes inactive posts."""
    owner = _create_user("corporate_client", "member-owner")
    member = _create_user("client", "active-member")
    organization = _create_organization(owner, "member")
    OrganizationMembership.objects.create(
        organization=organization,
        user=member,
        role="MEMBER",
        is_active=True,
    )
    _create_posts(organization, owner, 0, 50)
    inactive_post = _create_posts(organization, owner, 50, 1, is_active=False)[0]
    api_client.force_authenticate(user=member)
    url = reverse("get-organization-posts-public", kwargs={"organization_id": organization.pk})

    with CaptureQueriesContext(connection) as one_post_queries:
        one_post_response = api_client.get(url, {"page_size": 1})
    with CaptureQueriesContext(connection) as fifty_post_queries:
        fifty_post_response = api_client.get(url, {"page_size": 50})

    fifty_post_ids = {item["id"] for item in fifty_post_response.data["results"]}
    owner_name = f"{owner.first_name} {owner.last_name}"
    assert (
        one_post_response.status_code,
        one_post_response.data["count"],
        len(one_post_response.data["results"]),
        one_post_response.data["results"][0]["author_name"],
    ) == (status.HTTP_200_OK, 50, 1, owner_name)
    assert (
        fifty_post_response.status_code,
        fifty_post_response.data["count"],
        len(fifty_post_response.data["results"]),
    ) == (status.HTTP_200_OK, 50, 50)
    assert inactive_post.pk not in fifty_post_ids
    assert {
        tuple(sorted({item["is_active"] for item in fifty_post_response.data["results"]})),
        tuple(sorted({item["author_name"] for item in fifty_post_response.data["results"]})),
    } == {(True,), (owner_name,)}
    assert len(one_post_queries) == len(fifty_post_queries)
    assert len(fifty_post_queries) <= MAX_MEMBER_ORGANIZATION_POST_LIST_QUERIES
