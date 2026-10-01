"""Regression tests for the bounded dynamic-document list page size."""

import pytest
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from rest_framework.test import APIClient

from gym_app.models import DynamicDocument, User

pytestmark = pytest.mark.django_db


@pytest.fixture
def lawyer():
    """Create the lawyer who can list every document in the test collection."""
    return User.objects.create_user(
        email="page-limit-lawyer@test.com",
        password="testpassword",
        first_name="Page",
        last_name="Limit",
        role="lawyer",
        is_gym_lawyer=True,
    )


@pytest.fixture
def document_collection(lawyer):
    """Create more documents than the maximum API page size."""
    documents = [
        DynamicDocument(
            title=f"Cap-{number:03d}",
            content="<p>content</p>",
            state="Draft",
            created_by=lawyer,
            managed_by=lawyer,
        )
        for number in range(1, 106)
    ]
    DynamicDocument.objects.bulk_create(documents)
    return documents


@pytest.mark.parametrize(
    ("limit", "expected_size"),
    [(None, 10), ("abc", 10), ("0", 10), ("-1", 10)],
)
def test_document_list_defaults_invalid_limits_to_ten(
    lawyer, document_collection, limit, expected_size
):
    """Fails if an invalid page limit no longer falls back to exactly ten documents."""
    client = APIClient()
    client.force_authenticate(user=lawyer)
    params = {} if limit is None else {"limit": limit}

    response = client.get(reverse("list_dynamic_documents"), params)

    assert response.status_code == 200
    assert len(response.data["items"]) == expected_size
    assert response.data["totalItems"] == 105
    assert response.data["totalPages"] == 11
    assert response.data["currentPage"] == 1


@pytest.mark.parametrize("limit", ["100", "101"])
def test_document_list_caps_oversized_pages_at_one_hundred(
    lawyer, document_collection, limit
):
    """Fails if an oversized request serializes or selects more than one hundred documents."""
    client = APIClient()
    client.force_authenticate(user=lawyer)

    with CaptureQueriesContext(connection) as queries:
        response = client.get(reverse("list_dynamic_documents"), {"limit": limit})

    page_queries = [
        query["sql"].upper()
        for query in queries.captured_queries
        if " LIMIT " in query["sql"].upper()
    ]
    assert response.status_code == 200
    assert len(response.data["items"]) == 100
    assert response.data["totalItems"] == 105
    assert response.data["totalPages"] == 2
    assert any("LIMIT 100" in query for query in page_queries)


def test_document_list_honors_descending_title_sort_after_search(
    lawyer, document_collection
):
    """Fails if a capped page loses descending title order after a document search."""
    client = APIClient()
    client.force_authenticate(user=lawyer)
    url = reverse("list_dynamic_documents")

    ordered = client.get(url, {"limit": "100", "search": "Cap", "sort_by": "name-desc"})

    assert ordered.status_code == 200
    assert [item["title"] for item in ordered.data["items"][:2]] == [
        "Cap-105",
        "Cap-104",
    ]
    assert ordered.data["items"][-1]["title"] == "Cap-006"
    assert ordered.data["totalItems"] == 105
    assert ordered.data["totalPages"] == 2


def test_document_list_returns_the_last_bounded_page_for_an_out_of_range_page(
    lawyer, document_collection
):
    """Fails if an out-of-range page no longer resolves to the final capped page."""
    client = APIClient()
    client.force_authenticate(user=lawyer)
    last_page = client.get(
        reverse("list_dynamic_documents"),
        {"limit": "999", "page": "999", "search": "Cap", "sort_by": "name-desc"},
    )

    assert last_page.status_code == 200
    assert [item["title"] for item in last_page.data["items"]] == [
        "Cap-005",
        "Cap-004",
        "Cap-003",
        "Cap-002",
        "Cap-001",
    ]
    assert last_page.data["currentPage"] == 2
