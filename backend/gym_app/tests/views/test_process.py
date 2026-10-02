"""Tests for process module."""

import json
from datetime import timedelta
from unittest.mock import patch

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from django.utils import timezone
from freezegun import freeze_time
from rest_framework import status

from gym_app.models import (
    Case,
    CaseFile,
    Process,
    RecentProcess,
    Stage,
    StageAlert,
    User,
)

MAX_RECENT_PROCESS_LIST_QUERIES = 6
MAX_PROCESS_LIST_QUERIES = 6


def _create_recent_process_fixtures(user, start_index, count):
    """Create recent processes with distinct nested data for real serializer work."""
    recent_processes = []
    for index in range(start_index, start_index + count):
        client = User.objects.create_user(
            email=f"recent-client-{index}@example.com",
            password=None,
            role="Client",
        )
        lawyer = User.objects.create_user(
            email=f"recent-lawyer-{index}@example.com",
            password=None,
            role="Lawyer",
        )
        case = Case.objects.create(type=f"Recent case {index}")
        process = Process.objects.create(
            authority=f"Court {index}",
            plaintiff=f"Plaintiff {index}",
            defendant=f"Defendant {index}",
            ref=f"PERF-RECENT-{index}",
            lawyer=lawyer,
            case=case,
            subcase=f"Subcase {index}",
        )
        case_file = CaseFile.objects.create(
            file=SimpleUploadedFile(
                f"recent-{index}.txt",
                f"file-{index}".encode(),
                content_type="text/plain",
            )
        )
        first_stage = Stage.objects.create(status=f"First stage {index}")
        alerted_stage = Stage.objects.create(status=f"Alerted stage {index}")
        StageAlert.objects.create(stage=alerted_stage, description=f"Alert {index}")
        process.clients.add(client, user)
        process.case_files.add(case_file)
        process.stages.add(first_stage, alerted_stage)
        recent_process = RecentProcess.objects.create(user=user, process=process)
        RecentProcess.objects.filter(pk=recent_process.pk).update(
            last_viewed=timezone.now() + timezone.timedelta(minutes=index),
        )
        recent_processes.append(recent_process)
    return recent_processes


def _create_recent_history_entries(
    user,
    lawyer,
    case,
    prefix,
    count,
    start_time,
    grants_access,
):
    """Create recent entries with deterministic timestamps for access-list assertions."""
    entries = []
    for index in range(count):
        process = Process.objects.create(
            authority=f"{prefix} court {index}",
            plaintiff=f"{prefix} plaintiff {index}",
            defendant=f"{prefix} defendant {index}",
            ref=f"{prefix}-{index}",
            lawyer=lawyer,
            case=case,
            subcase=f"{prefix} subcase {index}",
        )
        if grants_access:
            process.clients.add(user)
        recent_process = RecentProcess.objects.create(user=user, process=process)
        RecentProcess.objects.filter(pk=recent_process.pk).update(
            last_viewed=start_time + timedelta(minutes=index),
        )
        entries.append(recent_process)
    return entries


def _create_assigned_shared_recent_entry(user, case, last_viewed):
    """Create one recent process where an external assignee is also a shared client."""
    shared_client_one = User.objects.create_user(
        email="shared-recent-one@example.com",
        password="testpassword",
        role="client",
    )
    shared_client_two = User.objects.create_user(
        email="shared-recent-two@example.com",
        password="testpassword",
        role="client",
    )
    shared_client_three = User.objects.create_user(
        email="shared-recent-three@example.com",
        password="testpassword",
        role="client",
    )
    process = Process.objects.create(
        authority="Assigned Shared Court",
        plaintiff="Assigned Shared Plaintiff",
        defendant="Assigned Shared Defendant",
        ref="ASSIGNED-SHARED-RECENT",
        lawyer=user,
        case=case,
        subcase="Assigned shared matter",
    )
    process.clients.add(user, shared_client_one, shared_client_two, shared_client_three)
    recent_process = RecentProcess.objects.create(user=user, process=process)
    RecentProcess.objects.filter(pk=recent_process.pk).update(last_viewed=last_viewed)
    return process


def _create_process_list_fixtures(lawyer, start_index, count):
    """Create processes with distinct cases for the list serializer budget."""
    expected_cases = {}
    for index in range(start_index, start_index + count):
        case = Case.objects.create(type=f"Budget case {index}")
        process = Process.objects.create(
            authority=f"Budget court {index}",
            plaintiff=f"Budget plaintiff {index}",
            defendant=f"Budget defendant {index}",
            ref=f"PROCESS-BUDGET-{index}",
            lawyer=lawyer,
            case=case,
            subcase=f"Budget subcase {index}",
        )
        expected_cases[process.ref] = (case.id, case.type)
    return expected_cases


@pytest.fixture
def client_user():
    """Client user."""
    return User.objects.create_user(
        email='client@example.com',
        password='testpassword',
        role='Client'
    )

@pytest.fixture
def lawyer_user():
    """Lawyer user."""
    return User.objects.create_user(
        email='lawyer@example.com',
        password='testpassword',
        role='Lawyer'
    )

@pytest.fixture
def admin_user():
    """Admin user."""
    return User.objects.create_user(
        email='admin@example.com',
        password='testpassword',
        role='Admin'
    )

@pytest.fixture
def case_type():
    """Case type."""
    return Case.objects.create(type='Criminal')

@pytest.fixture
def stage():
    """Stage."""
    return Stage.objects.create(status='In Progress')

@pytest.fixture
def process(client_user, lawyer_user, case_type, stage):
    """Process."""
    process = Process.objects.create(
        authority='Supreme Court',
        plaintiff='John Smith',
        defendant='Jane Doe',
        ref='CASE-123',
        lawyer=lawyer_user,
        case=case_type,
        subcase='Theft'
    )
    process.clients.add(client_user)
    process.stages.add(stage)
    return process

def _make_process_data(client_ids, lawyer_id, case_type_id, **overrides):
    base = {
        'authority': 'Court',
        'plaintiff': 'P',
        'defendant': 'D',
        'ref': 'CASE-001',
        'clientIds': client_ids,
        'lawyerId': lawyer_id,
        'caseTypeId': case_type_id,
        'subcase': 'Contract Dispute',
    }
    base.update(overrides)
    return base


@pytest.mark.django_db
class TestProcessViews:
    """Tests for Process Views."""
    
    def test_process_list_client(self, api_client, client_user, process):
        """Test that a client can only see their own processes."""
        # Authenticate as client
        api_client.force_authenticate(user=client_user)
        
        # Make the request
        url = reverse('process-list')
        response = api_client.get(url)
        
        # Assert the response
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['ref'] == 'CASE-123'
        assert response.data[0]['case'] == {
            'id': process.case.id,
            'type': process.case.type,
        }
        
        # Create another process with a different client
        other_client = User.objects.create_user(
            email='other.client@example.com',
            password='testpassword',
            role='Client'
        )
        other_process = Process.objects.create(
            authority='District Court',
            plaintiff='Other Person',
            defendant='Another Person',
            ref='CASE-456',
            lawyer=process.lawyer,
            case=process.case
        )
        other_process.clients.add(other_client)
        
        # Make the request again
        response = api_client.get(url)
        
        # Client should still only see their process
        assert len(response.data) == 1
        assert response.data[0]['ref'] == 'CASE-123'
    
    def test_process_list_lawyer_sees_all(self, api_client, lawyer_user, process):
        """Lawyers are gym staff and see every process (single-firm cooperative model,.

        consistent with dynamic_documents.permissions.apply_visibility_filter).
        """
        api_client.force_authenticate(user=lawyer_user)
        url = reverse('process-list')

        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['ref'] == 'CASE-123'

        other_lawyer = User.objects.create_user(
            email='other.lawyer@example.com',
            password='testpassword',
            role='Lawyer'
        )
        other_process = Process.objects.create(
            authority='District Court',
            plaintiff='Other Person',
            defendant='Another Person',
            ref='CASE-456',
            lawyer=other_lawyer,
            case=process.case
        )
        other_process.clients.set(process.clients.all())

        response = api_client.get(url)
        refs = {p['ref'] for p in response.data}
        assert refs == {'CASE-123', 'CASE-456'}
    
    def test_process_list_admin(self, api_client, admin_user, process):
        """Test that an admin can see all processes."""
        # Authenticate as admin
        api_client.force_authenticate(user=admin_user)
        
        # Make the request
        url = reverse('process-list')
        response = api_client.get(url)
        
        # Assert the response - admin sees the one process
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        
        # Create another process
        other_client = User.objects.create_user(
            email='other.client@example.com',
            password='testpassword',
            role='Client'
        )
        other_lawyer = User.objects.create_user(
            email='other.lawyer@example.com',
            password='testpassword',
            role='Lawyer'
        )
        other_process = Process.objects.create(
            authority='District Court',
            plaintiff='Other Person',
            defendant='Another Person',
            ref='CASE-456',
            lawyer=other_lawyer,
            case=process.case
        )
        other_process.clients.add(other_client)
        
        # Make the request again
        response = api_client.get(url)
        
        # Admin should see both processes
        assert len(response.data) == 2
        refs = [p['ref'] for p in response.data]
        assert 'CASE-123' in refs
        assert 'CASE-456' in refs
    
    def test_create_process_response(self, api_client, admin_user, client_user, lawyer_user, case_type):
        """Test creating a new process returns correct response."""
        api_client.force_authenticate(user=admin_user)
        
        main_data = _make_process_data(
            [client_user.id], lawyer_user.id, case_type.id,
            authority='Federal Court', plaintiff='Company Inc.',
            defendant='Other Company LLC', ref='CASE-789',
        )
        
        url = reverse('create-process')
        response = api_client.post(url, {'mainData': json.dumps(main_data)}, format='multipart')
        
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['authority'] == 'Federal Court'
        assert response.data['plaintiff'] == 'Company Inc.'
        assert response.data['ref'] == 'CASE-789'

    def test_create_process_db_state(self, api_client, admin_user, client_user, lawyer_user, case_type):
        """Test creating a new process creates correct database records."""
        api_client.force_authenticate(user=admin_user)
        
        main_data = _make_process_data(
            [client_user.id], lawyer_user.id, case_type.id,
            ref='CASE-DB', stages=[{'status': 'New'}, {'status': 'Analysis'}],
        )
        
        url = reverse('create-process')
        response = api_client.post(url, {'mainData': json.dumps(main_data)}, format='multipart')
        assert response.status_code == status.HTTP_201_CREATED
        
        created_process = Process.objects.get(ref='CASE-DB')
        assert created_process.clients.count() == 1
        assert created_process.lawyer.id == lawyer_user.id
        assert created_process.stages.count() == 2
    
    def test_create_process_invalid_client(self, api_client, admin_user, lawyer_user, case_type):
        """Test creating a process with an invalid client ID."""
        # Authenticate
        api_client.force_authenticate(user=admin_user)
        
        # Prepare the data with invalid client ID
        main_data = _make_process_data(
            [9999], lawyer_user.id, case_type.id,  # Invalid client ID
            authority='Federal Court', plaintiff='Company Inc.',
            defendant='Other Company LLC', ref='CASE-789',
        )
        
        # Make the request
        url = reverse('create-process')
        response = api_client.post(
            url, 
            {'mainData': json.dumps(main_data)}, 
            format='multipart'
        )
        
        # Assert the response
        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'Client or Lawyer not found' in response.data['detail']
        
        # Verify no process was created
        assert Process.objects.count() == 0
    
    def test_update_process_db_state(self, api_client, admin_user, process, case_type):
        """Test updating a process updates database correctly."""
        api_client.force_authenticate(user=admin_user)
        new_case_type = Case.objects.create(type='Civil')
        
        main_data = {
            'authority': 'Updated Court',
            'plaintiff': 'Updated Plaintiff',
            'defendant': 'Updated Defendant',
            'ref': 'UPDATED-REF',
            'caseTypeId': new_case_type.id,
        }
        
        url = reverse('update-process', kwargs={'pk': process.id})
        response = api_client.put(url, {'mainData': json.dumps(main_data)}, format='multipart')
        
        assert response.status_code == status.HTTP_200_OK
        updated_process = Process.objects.get(id=process.id)
        assert updated_process.authority == 'Updated Court'
        assert updated_process.plaintiff == 'Updated Plaintiff'
        assert updated_process.ref == 'UPDATED-REF'

    def test_update_process_case_files(self, api_client, admin_user, process):
        """Test updating a process replaces case files when caseFileIds are provided."""
        api_client.force_authenticate(user=admin_user)

        existing_file = CaseFile.objects.create(
            file=SimpleUploadedFile("existing.txt", b"existing", content_type="text/plain")
        )
        process.case_files.add(existing_file)

        new_file = CaseFile.objects.create(
            file=SimpleUploadedFile("new_file.txt", b"new", content_type="text/plain")
        )

        main_data = {
            'caseFileIds': [new_file.id],
        }

        url = reverse('update-process', kwargs={'pk': process.id})
        response = api_client.put(url, {'mainData': json.dumps(main_data)}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        process.refresh_from_db()
        case_file_ids = set(process.case_files.values_list('id', flat=True))
        assert case_file_ids == {new_file.id}

    def test_update_process_empty_case_file_ids_clears_all(self, api_client, admin_user, process):
        """Test that sending caseFileIds=[] removes all case files from the process."""
        api_client.force_authenticate(user=admin_user)

        file1 = CaseFile.objects.create(
            file=SimpleUploadedFile("f1.txt", b"a", content_type="text/plain")
        )
        file2 = CaseFile.objects.create(
            file=SimpleUploadedFile("f2.txt", b"b", content_type="text/plain")
        )
        process.case_files.set([file1, file2])
        assert process.case_files.count() == 2

        main_data = {'caseFileIds': []}

        url = reverse('update-process', kwargs={'pk': process.id})
        response = api_client.put(url, {'mainData': json.dumps(main_data)}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        process.refresh_from_db()
        assert process.case_files.count() == 0

    def test_update_process_omitted_case_file_ids_keeps_files(self, api_client, admin_user, process):
        """Test that omitting caseFileIds leaves existing case files unchanged."""
        api_client.force_authenticate(user=admin_user)

        file1 = CaseFile.objects.create(
            file=SimpleUploadedFile("keep.txt", b"keep", content_type="text/plain")
        )
        process.case_files.add(file1)
        assert process.case_files.count() == 1

        main_data = {'authority': 'New Authority'}

        url = reverse('update-process', kwargs={'pk': process.id})
        response = api_client.put(url, {'mainData': json.dumps(main_data)}, format='multipart')

        assert response.status_code == status.HTTP_200_OK
        process.refresh_from_db()
        assert process.case_files.count() == 1
        assert process.case_files.first().id == file1.id

    def test_update_process_response(self, api_client, admin_user, process, case_type):
        """Test updating a process returns correct response."""
        api_client.force_authenticate(user=admin_user)
        
        main_data = {
            'authority': 'Response Court',
            'plaintiff': 'Response Plaintiff',
            'defendant': 'Response Defendant',
            'ref': 'RESP-REF',
            'subcase': 'Response Subcase',
        }
        
        url = reverse('update-process', kwargs={'pk': process.id})
        response = api_client.put(url, {'mainData': json.dumps(main_data)}, format='multipart')
        
        assert response.status_code == status.HTTP_200_OK
        assert response.data['authority'] == 'Response Court'
        assert response.data['plaintiff'] == 'Response Plaintiff'
        assert response.data['ref'] == 'RESP-REF'
    
    def test_update_case_file(self, api_client, admin_user, process):
        """Test uploading a file to an existing process."""
        # Authenticate
        api_client.force_authenticate(user=admin_user)
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "new_document.txt", 
            b"New document content", 
            content_type="text/plain"
        )
        
        # Prepare the data
        data = {
            'processId': process.id,
            'file': test_file
        }
        
        # Make the request
        url = reverse('update-file')
        response = api_client.post(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['detail'] == 'File uploaded successfully.'
        assert 'fileId' in response.data
        
        # Verify the file was associated with the process
        process.refresh_from_db()
        assert process.case_files.count() == 1
        
        # Verify that the file name contains 'new_document' and ends with '.txt'
        # This is more flexible than checking for the exact filename with suffixes
        file_name = process.case_files.first().file.name
        assert 'new_document' in file_name
        assert file_name.endswith('.txt')
    
    def test_update_case_file_missing_process_id(self, api_client, admin_user):
        """Test uploading a file without specifying a process ID."""
        # Authenticate
        api_client.force_authenticate(user=admin_user)
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "document.txt", 
            b"Document content", 
            content_type="text/plain"
        )
        
        # Prepare the data without process ID
        data = {
            'file': test_file
        }
        
        # Make the request
        url = reverse('update-file')
        response = api_client.post(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Process ID is required' in response.data['detail']
        
        # Verify no files were created
        assert CaseFile.objects.count() == 0
    
    def test_update_case_file_missing_file(self, api_client, admin_user, process):
        """Test uploading without providing a file."""
        # Authenticate
        api_client.force_authenticate(user=admin_user)
        
        # Prepare the data without file
        data = {
            'processId': process.id
        }
        
        # Make the request
        url = reverse('update-file')
        response = api_client.post(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'File is required' in response.data['detail']
        
        # Verify no files were created
        assert CaseFile.objects.count() == 0
    
    def test_update_case_file_nonexistent_process(self, api_client, admin_user):
        """Test uploading a file to a non-existent process."""
        # Authenticate
        api_client.force_authenticate(user=admin_user)
        
        # Create a test file
        test_file = SimpleUploadedFile(
            "document.txt", 
            b"Document content", 
            content_type="text/plain"
        )
        
        # Prepare the data with non-existent process ID
        data = {
            'processId': 9999,  # Non-existent ID
            'file': test_file
        }
        
        # Make the request
        url = reverse('update-file')
        response = api_client.post(url, data, format='multipart')
        
        # Assert the response
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        
        # Verify no files were created
        assert CaseFile.objects.count() == 0
    
    def test_unauthenticated_access(self, api_client):
        """Test that unauthenticated users cannot access the process endpoints."""
        # Test process list
        list_url = reverse('process-list')
        list_response = api_client.get(list_url)
        assert list_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test create process
        create_url = reverse('create-process')
        create_response = api_client.post(create_url, {}, format='multipart')
        assert create_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test update process (using a fictitious ID)
        update_url = reverse('update-process', kwargs={'pk': 1})
        update_response = api_client.put(update_url, {}, format='multipart')
        assert update_response.status_code == status.HTTP_401_UNAUTHORIZED
        
        # Test update case file
        file_url = reverse('update-file')
        file_response = api_client.post(file_url, {}, format='multipart')
        assert file_response.status_code == status.HTTP_401_UNAUTHORIZED

    def test_get_recent_processes_returns_only_user_entries(self, api_client, client_user, process):
        """recent-processes debe devolver solo los procesos recientes del usuario autenticado."""
        # Crear entradas de procesos recientes para el usuario
        RecentProcess.objects.create(user=client_user, process=process)

        # Crear otra entrada para un usuario distinto
        other_user = User.objects.create_user(
            email='other.user@example.com',
            password='testpassword',
            role='Client'
        )
        other_process = Process.objects.create(
            authority='Other Court',
            plaintiff='Other',
            defendant='Other',
            ref='CASE-OTHER',
            lawyer=process.lawyer,
            case=process.case
        )
        RecentProcess.objects.create(user=other_user, process=other_process)

        api_client.force_authenticate(user=client_user)

        url = reverse('recent-processes')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 1
        assert response.data[0]['process']['id'] == process.id

    def test_get_recent_processes_limits_to_10_and_orders_by_last_viewed(self, api_client, client_user, case_type, lawyer_user):
        """recent-processes debe devolver máximo 10 elementos ordenados por last_viewed desc."""
        # Crear 12 procesos y entradas de RecentProcess con last_viewed creciente
        for i in range(12):
            p = Process.objects.create(
                authority='Court',
                plaintiff=f'P{i}',
                defendant=f'D{i}',
                ref=f'CASE-{i}',
                lawyer=lawyer_user,
                case=case_type
            )
            p.clients.add(client_user)
            rp = RecentProcess.objects.create(user=client_user, process=p)
            # Forzar un orden consistente incrementando last_viewed
            rp.last_viewed = rp.last_viewed.replace(microsecond=i)
            rp.save(update_fields=['last_viewed'])

        api_client.force_authenticate(user=client_user)
        url = reverse('recent-processes')
        response = api_client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) == 10

        # Comprobar que están ordenados por last_viewed descendente
        timestamps = [item['last_viewed'] for item in response.data]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_update_recent_process_creates_or_updates_entry(self, api_client, client_user, process):
        """update-recent-process debe crear o actualizar la entrada de RecentProcess."""
        api_client.force_authenticate(user=client_user)

        url = reverse('update-recent-process', kwargs={'process_id': process.id})

        # Primera llamada: debe crear la entrada
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_200_OK
        assert response.data['status'] == 'success'

        rp = RecentProcess.objects.get(user=client_user, process=process)
        first_last_viewed = rp.last_viewed

        # Segunda llamada: debe actualizar last_viewed
        response = api_client.post(url, {})
        assert response.status_code == status.HTTP_200_OK

        rp.refresh_from_db()
        assert rp.last_viewed >= first_last_viewed

    def test_update_recent_process_not_found(self, api_client, client_user):
        """update-recent-process debe responder 404 si el proceso no existe."""
        api_client.force_authenticate(user=client_user)

        url = reverse('update-recent-process', kwargs={'process_id': 9999})
        response = api_client.post(url, {})

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert response.data['error'] == 'Process not found'

    def test_update_recent_process_rejects_unrelated_client(
        self,
        api_client,
        client_user,
        process,
        lawyer_user,
        case_type,
    ):
        """Fails if an unrelated client can create a recent-process entry."""
        retained_recent = RecentProcess.objects.create(user=client_user, process=process)
        foreign_process = Process.objects.create(
            authority="Private Court",
            plaintiff="Private Plaintiff",
            defendant="Private Defendant",
            ref="PRIVATE-RECENT-001",
            lawyer=lawyer_user,
            case=case_type,
            subcase="Private matter",
        )
        api_client.force_authenticate(user=client_user)
        url = reverse("update-recent-process", kwargs={"process_id": foreign_process.id})

        response = api_client.post(url, {}, format="json")

        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "No tienes permiso para consultar este proceso."
        assert RecentProcess.objects.filter(user=client_user, process=foreign_process).exists() is False
        assert RecentProcess.objects.filter(pk=retained_recent.pk, process=process).exists() is True

    @freeze_time("2026-10-02 12:00:00")
    def test_update_recent_process_preserves_timestamp_after_client_access_is_revoked(
        self,
        api_client,
        client_user,
        process,
    ):
        """Fails if revoking process access still refreshes a recent timestamp."""
        recent_process = RecentProcess.objects.create(user=client_user, process=process)
        saved_last_viewed = timezone.now() - timedelta(days=1)
        RecentProcess.objects.filter(pk=recent_process.pk).update(last_viewed=saved_last_viewed)
        recent_process.refresh_from_db()
        saved_last_viewed = recent_process.last_viewed
        process.clients.remove(client_user)
        api_client.force_authenticate(user=client_user)
        url = reverse("update-recent-process", kwargs={"process_id": process.id})

        response = api_client.post(url, {}, format="json")

        recent_process.refresh_from_db()
        assert response.status_code == status.HTTP_403_FORBIDDEN
        assert response.data["detail"] == "No tienes permiso para consultar este proceso."
        assert RecentProcess.objects.filter(user=client_user, process=process).count() == 1
        assert recent_process.process_id == process.id
        assert recent_process.last_viewed == saved_last_viewed

    def test_recent_processes_excludes_process_after_client_access_is_revoked(
        self,
        api_client,
        client_user,
        process,
        lawyer_user,
        case_type,
    ):
        """Fails if a revoked client still receives a process from recent history."""
        retained_recent = RecentProcess.objects.create(user=client_user, process=process)
        revoked_process = Process.objects.create(
            authority="Revoked Court",
            plaintiff="Revoked Plaintiff",
            defendant="Revoked Defendant",
            ref="REVOKED-RECENT-001",
            lawyer=lawyer_user,
            case=case_type,
            subcase="Revoked matter",
        )
        revoked_process.clients.add(client_user)
        RecentProcess.objects.create(user=client_user, process=revoked_process)
        revoked_process.clients.remove(client_user)
        api_client.force_authenticate(user=client_user)

        response = api_client.get(reverse("recent-processes"))

        response_process_ids = [item["process"]["id"] for item in response.data]
        assert response.status_code == status.HTTP_200_OK
        assert retained_recent.process_id in response_process_ids
        assert revoked_process.id not in response_process_ids

    def test_recent_processes_include_assigned_basic_lawyer(
        self,
        api_client,
        case_type,
    ):
        """Fails if a non-internal assigned lawyer loses recent-process access."""
        assigned_lawyer = User.objects.create_user(
            email="assigned-basic-lawyer@example.com",
            password="testpassword",
            role="basic",
        )
        assigned_process = Process.objects.create(
            authority="Assigned Court",
            plaintiff="Assigned Plaintiff",
            defendant="Assigned Defendant",
            ref="ASSIGNED-RECENT-001",
            lawyer=assigned_lawyer,
            case=case_type,
            subcase="Assigned matter",
        )
        RecentProcess.objects.create(user=assigned_lawyer, process=assigned_process)
        api_client.force_authenticate(user=assigned_lawyer)

        response = api_client.get(reverse("recent-processes"))

        assert response.status_code == status.HTTP_200_OK
        assert assigned_process.id in [item["process"]["id"] for item in response.data]

    @pytest.mark.parametrize(
        "internal_attributes",
        [
            pytest.param({"role": "lawyer", "is_gym_lawyer": False, "is_staff": False, "is_superuser": False}, id="role-lawyer"),
            pytest.param({"role": "basic", "is_gym_lawyer": True, "is_staff": False, "is_superuser": False}, id="gym-lawyer"),
            pytest.param({"role": "basic", "is_gym_lawyer": False, "is_staff": True, "is_superuser": False}, id="staff"),
            pytest.param({"role": "basic", "is_gym_lawyer": False, "is_staff": False, "is_superuser": True}, id="superuser"),
        ],
    )
    def test_recent_processes_include_internal_access_variants(
        self,
        api_client,
        case_type,
        lawyer_user,
        internal_attributes,
    ):
        """Fails if an internal access variant loses recent-process visibility."""
        internal_user = User.objects.create_user(
            email=f"recent-internal-{internal_attributes['role']}-{internal_attributes['is_gym_lawyer']}-{internal_attributes['is_staff']}-{internal_attributes['is_superuser']}@example.com",
            password="testpassword",
            **internal_attributes,
        )
        internal_process = Process.objects.create(
            authority="Internal Court",
            plaintiff="Internal Plaintiff",
            defendant="Internal Defendant",
            ref="INTERNAL-RECENT-001",
            lawyer=lawyer_user,
            case=case_type,
            subcase="Internal matter",
        )
        RecentProcess.objects.create(user=internal_user, process=internal_process)
        api_client.force_authenticate(user=internal_user)

        response = api_client.get(reverse("recent-processes"))

        assert response.status_code == status.HTTP_200_OK
        assert internal_process.id in [item["process"]["id"] for item in response.data]


@pytest.mark.django_db
@freeze_time("2026-10-02 12:00:00")
def test_recent_processes_filters_access_before_the_ten_item_limit(
    api_client,
    client_user,
    lawyer_user,
    case_type,
):
    """Fails if newer inaccessible history displaces authorized recent processes."""
    visible_start = timezone.now() - timedelta(days=1)
    _create_recent_history_entries(
        client_user, lawyer_user, case_type, "INACCESSIBLE-RECENT", 11,
        visible_start + timedelta(days=1), False,
    )
    _create_recent_history_entries(
        client_user, lawyer_user, case_type, "AUTHORIZED-RECENT", 9,
        visible_start, True,
    )
    assigned_shared_process = _create_assigned_shared_recent_entry(
        client_user,
        case_type,
        visible_start + timedelta(minutes=9),
    )
    expected_process_ids = list(
        RecentProcess.objects.filter(
            user=client_user,
            process__clients=client_user,
        )
        .order_by("-last_viewed")
        .values_list("process_id", flat=True)
    )
    inaccessible_process_ids = set(
        RecentProcess.objects.filter(
            user=client_user,
            process__ref__startswith="INACCESSIBLE-RECENT",
        ).values_list("process_id", flat=True)
    )
    api_client.force_authenticate(user=client_user)

    response = api_client.get(reverse("recent-processes"))

    response_process_ids = [item["process"]["id"] for item in response.data]
    assert response.status_code == status.HTTP_200_OK
    assert response_process_ids == expected_process_ids
    assert len(response_process_ids) == 10
    assert len(response_process_ids) == len(set(response_process_ids))
    assert response_process_ids.count(assigned_shared_process.id) == 1
    assert set(response_process_ids).isdisjoint(inaccessible_process_ids)


# ======================================================================
# Tests merged from test_process_views.py (coverage + edge cases)
# ======================================================================

@pytest.fixture
def _pv_lawyer():
    return User.objects.create_user(
        email='law_pc@e.com', password='p', role='lawyer',
        first_name='L', last_name='P')


@pytest.fixture
def _pv_lawyer2():
    return User.objects.create_user(
        email='law2_pc@e.com', password='p', role='lawyer',
        first_name='L2', last_name='P')


@pytest.fixture
def _pv_client():
    return User.objects.create_user(
        email='cli_pc@e.com', password='p', role='client',
        first_name='C', last_name='P')


@pytest.fixture
def _pv_ctype():
    return Case.objects.create(type='CivPC')


@pytest.fixture
def _pv_proc(_pv_lawyer, _pv_client, _pv_ctype):
    p = Process.objects.create(
        authority='A', plaintiff='P', defendant='D', ref='PC1',
        lawyer=_pv_lawyer, case=_pv_ctype, subcase='S')
    p.clients.add(_pv_client)
    return p


@pytest.mark.django_db
class TestProcessRegressionScenarios:
    """Tests for Process Regression Scenarios."""

    def test_update_process_changes_lawyer(self, api_client, _pv_lawyer, _pv_lawyer2, _pv_proc):  # noqa: PT019
        """Line 215: updating lawyerId assigns new lawyer to process."""
        api_client.force_authenticate(user=_pv_lawyer)
        url = reverse('update-process', kwargs={'pk': _pv_proc.pk})
        data = {'mainData': json.dumps({'lawyerId': _pv_lawyer2.id})}
        r = api_client.put(url, data, format='multipart')
        assert r.status_code == status.HTTP_200_OK
        _pv_proc.refresh_from_db()
        assert _pv_proc.lawyer_id == _pv_lawyer2.id


# --- Edge-case fixtures ---

@pytest.fixture
def _edge_lawyer():
    return User.objects.create_user(
        email="lawyer-edge@example.com", password="testpassword",
        first_name="Lawyer", last_name="Edge", role="Lawyer",
    )


@pytest.fixture
def _edge_client():
    return User.objects.create_user(
        email="client-edge@example.com", password="testpassword",
        first_name="Client", last_name="Edge", role="Client",
    )


@pytest.fixture
def _edge_admin():
    return User.objects.create_user(
        email="admin-edge@example.com", password="testpassword",
        first_name="Admin", last_name="Edge", role="Admin",
    )


@pytest.fixture
def _edge_ctype():
    return Case.objects.create(type="Civil")


@pytest.fixture
def _edge_proc(_edge_lawyer, _edge_client, _edge_ctype):
    proc = Process.objects.create(
        authority="Juzgado 1", plaintiff="Plaintiff", defendant="Defendant",
        ref="REF-001", lawyer=_edge_lawyer, case=_edge_ctype, progress=50,
    )
    proc.clients.add(_edge_client)
    stage = Stage.objects.create(status="Initial stage")
    proc.stages.add(stage)
    return proc


# ---------------------------------------------------------------------------
# process_list – exception handler (lines 46-47)
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestProcessListEdges:
    """Tests for Process List Edges."""

    def test_process_list_exception_returns_500(self, api_client, _edge_client):  # noqa: PT019
        """Cover the except block in process_list."""
        api_client.force_authenticate(user=_edge_client)
        url = reverse("process-list")
        with patch(
            "gym_app.views.process.ProcessSerializer",
            side_effect=Exception("DB error"),
        ):
            response = api_client.get(url)
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "DB error" in response.data["detail"]

    def test_process_list_admin_returns_all(self, api_client, _edge_admin, _edge_proc):  # noqa: PT019
        """Cover the else branch (non-client, non-lawyer role) in process_list."""
        api_client.force_authenticate(user=_edge_admin)
        url = reverse("process-list")
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK


# ---------------------------------------------------------------------------
# create_process – edge cases
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestCreateProcessEdges:
    """Tests for Create Process Edges."""

    def _build_main_data(self, **overrides):
        defaults = {
            "clientIds": [], "lawyerId": None, "caseTypeId": None,
            "authority": "Auth", "plaintiff": "P", "defendant": "D",
            "ref": "R-1", "subcase": "Sub-civil", "stages": [],
        }
        defaults.update(overrides)
        return defaults

    def test_create_process_single_client_id_not_list(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover line 67: client_ids converted from scalar to list."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=_edge_client.id, lawyerId=_edge_lawyer.id, caseTypeId=_edge_ctype.id,
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_process_invalid_lawyer(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover lines 75-76: lawyer DoesNotExist."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=99999, caseTypeId=_edge_ctype.id,
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_process_invalid_case_type(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover lines 81-82: case type DoesNotExist."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=_edge_lawyer.id, caseTypeId=99999,
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_404_NOT_FOUND

    def test_create_process_non_numeric_progress(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover lines 88-89: progress that can't be cast to int."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=_edge_lawyer.id,
            caseTypeId=_edge_ctype.id, progress="not-a-number",
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        assert response.data["progress"] == 0

    def test_create_process_stage_without_status_skipped(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover line 115: stage with empty status is skipped."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=_edge_lawyer.id,
            caseTypeId=_edge_ctype.id, stages=[{"status": ""}, {"status": "Filed"}],
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        proc = Process.objects.get(pk=response.data["id"])
        assert proc.stages.count() == 1

    def test_create_process_stage_with_valid_date(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover lines 120-123: stage with valid ISO date."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        # alertIsActive=False — past stage date would otherwise be rejected.
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=_edge_lawyer.id,
            caseTypeId=_edge_ctype.id, stages=[{"status": "Filed", "date": "2025-06-15"}],
            alertIsActive=False,
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED
        proc = Process.objects.get(pk=response.data["id"])
        stage = proc.stages.first()
        assert str(stage.date) == "2025-06-15"

    def test_create_process_stage_with_invalid_date_falls_back(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover lines 124-125: invalid date falls back to today."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=_edge_lawyer.id,
            caseTypeId=_edge_ctype.id, stages=[{"status": "Filed", "date": "not-a-date"}],
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_201_CREATED

    def test_create_process_unexpected_exception(self, api_client, _edge_lawyer, _edge_client, _edge_ctype):  # noqa: PT019
        """Cover lines 142-144: unexpected exception returns 500."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[_edge_client.id], lawyerId=_edge_lawyer.id, caseTypeId=_edge_ctype.id,
        )
        with patch("gym_app.views.process.Process.objects.create", side_effect=Exception("unexpected")):
            response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

    def test_create_process_empty_client_ids(self, api_client, _edge_lawyer, _edge_ctype):  # noqa: PT019
        """Cover line 71: empty clientIds returns 404."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("create-process")
        main_data = self._build_main_data(
            clientIds=[], lawyerId=_edge_lawyer.id, caseTypeId=_edge_ctype.id,
        )
        response = api_client.post(url, {"mainData": json.dumps(main_data)}, format="multipart")
        assert response.status_code == status.HTTP_404_NOT_FOUND


# ---------------------------------------------------------------------------
# update_process – edge cases
# ---------------------------------------------------------------------------
@pytest.mark.django_db
class TestUpdateProcessEdges:
    """Tests for Update Process Edges."""

    def test_update_process_json_body_directly(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover line 161: request.data is dict without 'mainData' key."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        data = {"plaintiff": "New Plaintiff", "authorityEmail": "auth@example.com"}
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.plaintiff == "New Plaintiff"
        assert _edge_proc.authority_email == "auth@example.com"

    def test_update_process_invalid_json_maindata_fallback(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover lines 167-169: mainData is not valid JSON, fallback to request.data."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        response = api_client.put(url, {"mainData": "not-json{{"}, format="multipart")
        assert response.status_code == status.HTTP_200_OK

    def test_update_process_progress_non_numeric(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover lines 192-198: progress update with non-numeric value."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        data = {"progress": "abc"}
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.progress in (50, 0)

    def test_update_process_progress_clamped(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover line 197: progress clamped to 0-100."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        data = {"progress": 150}
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.progress == 100

    def test_update_process_client_ids_scalar(self, api_client, _edge_lawyer, _edge_proc, _edge_client):  # noqa: PT019
        """Cover lines 203-208: clientIds as scalar, not list."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        data = {"clientIds": _edge_client.id}
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK

    def test_update_process_invalid_lawyer_id(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover lines 213-217: lawyerId that doesn't exist (DoesNotExist caught)."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        data = {"lawyerId": 99999}
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.lawyer == _edge_lawyer

    def test_update_process_invalid_case_type_id(self, api_client, _edge_lawyer, _edge_proc, _edge_ctype):  # noqa: PT019
        """Cover lines 225-226: caseTypeId that doesn't exist."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        data = {"caseTypeId": 99999}
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.case == _edge_ctype

    def test_update_process_replaces_stages(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover lines 239-255: stage replacement with valid/invalid dates."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        # alertIsActive=False — past dates in fixtures would trip the guard.
        data = {
            "alertIsActive": False,
            "stages": [
                {"status": "New stage", "date": "2025-03-01"},
                {"status": ""},
                {"status": "Another stage", "date": "bad-date"},
                {"status": "No date stage"},
            ]
        }
        response = api_client.put(url, data, format="json")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.stages.count() == 3
        dates = list(_edge_proc.stages.values_list("date", flat=True))
        from datetime import date
        assert date(2025, 3, 1) in dates

    def test_update_process_with_maindata_multipart(self, api_client, _edge_lawyer, _edge_proc):  # noqa: PT019
        """Cover lines 163-166: mainData as valid JSON string in multipart."""
        api_client.force_authenticate(user=_edge_lawyer)
        url = reverse("update-process", kwargs={"pk": _edge_proc.pk})
        main_data = json.dumps({"defendant": "Updated Defendant"})
        response = api_client.put(url, {"mainData": main_data}, format="multipart")
        assert response.status_code == status.HTTP_200_OK
        _edge_proc.refresh_from_db()
        assert _edge_proc.defendant == "Updated Defendant"


# ======================================================================
# B3 regression — update_process sends a stakeholder email
# ======================================================================

@pytest.mark.django_db
class TestUpdateProcessEmailNotification:
    """Verify that editing a process triggers the stakeholder email helper.

    Before the fix, ``update_process`` only emitted in-app notifications.
    The fix added ``_send_process_update_email`` which mirrors
    ``_send_alert_email``. The view now calls the helper after the
    Notification rows are created so stakeholders receive an email too.
    """

    def test_update_process_calls_email_helper_once(self, api_client, admin_user, process):
        """Patch the email helper and assert it is invoked exactly once."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('update-process', kwargs={'pk': process.id})
        payload = {'authority': 'Email Court', 'plaintiff': 'P', 'defendant': 'D'}

        target = 'gym_app.views.process._send_process_update_email'
        with patch(target) as mock_send:
            response = api_client.put(
                url, {'mainData': json.dumps(payload)}, format='multipart'
            )

        assert response.status_code == status.HTTP_200_OK
        assert mock_send.call_count == 1, (
            'update_process should invoke _send_process_update_email exactly once'
        )

    def test_update_process_email_targets_stakeholder_addresses(
        self, api_client, admin_user, process, lawyer_user, client_user,
    ):
        """The email goes to the stakeholder list returned by the recipients helper."""
        api_client.force_authenticate(user=admin_user)
        url = reverse('update-process', kwargs={'pk': process.id})
        payload = {'authority': 'Email Court'}

        target = 'gym_app.views.process._send_process_update_email'
        with patch(target) as mock_send:
            api_client.put(url, {'mainData': json.dumps(payload)}, format='multipart')

        assert mock_send.call_count == 1
        _, kwargs = mock_send.call_args
        recipients = kwargs.get('recipients') or (mock_send.call_args[0][1] if len(mock_send.call_args[0]) > 1 else [])
        emails = {getattr(u, 'email', None) for u in recipients}
        # At minimum the lawyer and the client should be notified.
        assert lawyer_user.email in emails
        assert client_user.email in emails

    def test_update_process_email_includes_lawyer_when_lawyer_is_actor(
        self, api_client, process, lawyer_user, client_user,
    ):
        """R3 fix: when the assigned LAWYER triggers the update they must.

        still receive the notification email (and in-app notification).
        Previously the actor was excluded so the lawyer never saw their own
        edits in the notification center / inbox.
        """
        api_client.force_authenticate(user=lawyer_user)
        url = reverse('update-process', kwargs={'pk': process.id})
        payload = {'authority': 'Lawyer Triggered Update'}

        target = 'gym_app.views.process._send_process_update_email'
        with patch(target) as mock_send:
            api_client.put(url, {'mainData': json.dumps(payload)}, format='multipart')

        assert mock_send.call_count == 1
        _, kwargs = mock_send.call_args
        recipients = kwargs.get('recipients') or []
        emails = {getattr(u, 'email', None) for u in recipients}
        assert lawyer_user.email in emails, (
            'lawyer must receive the email even when they are the actor'
        )
        assert client_user.email in emails, 'clients must still be included'

    def test_update_process_email_failure_does_not_break_api(self, api_client, admin_user, process):
        """If the underlying email transport raises, the helper logs it and the API still returns 200.

        ``_send_process_update_email`` wraps ``send_template_email`` in a
        try/except so transport failures never surface as HTTP 500. This
        test patches the transport (not the helper) so the helper's own
        error-handling path is exercised.
        """
        api_client.force_authenticate(user=admin_user)
        url = reverse('update-process', kwargs={'pk': process.id})
        payload = {'authority': 'Email Court'}

        target = 'gym_app.views.process.send_template_email'
        with patch(target, side_effect=Exception('SMTP down')):
            response = api_client.put(
                url, {'mainData': json.dumps(payload)}, format='multipart'
            )

        assert response.status_code == status.HTTP_200_OK


@pytest.mark.django_db
class TestLawyerDeletionProtection:
    """A lawyer that owns processes cannot be deleted (PROTECT)."""

    def test_deleting_lawyer_with_process_raises_protected_error(self, process, lawyer_user):
        """Deleting lawyer with process raises protected error."""
        from django.db.models import ProtectedError

        with pytest.raises(ProtectedError):
            lawyer_user.delete()
        assert Process.objects.filter(id=process.id).exists()

    def test_deleting_lawyer_without_process_succeeds(self):
        """Deleting lawyer without process succeeds."""
        lawyer = User.objects.create_user(
            email="lonely-lawyer@test.com", password="x", role="Lawyer"
        )
        lawyer_id = lawyer.id
        lawyer.delete()
        assert not User.objects.filter(id=lawyer_id).exists()


@pytest.mark.django_db
def test_recent_processes_have_constant_query_budget(api_client, client_user):
    """Fails if recent process serialization returns to per-row relation queries."""
    _create_recent_process_fixtures(client_user, 0, 1)
    api_client.force_authenticate(user=client_user)
    url = reverse("recent-processes")

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url)
    _create_recent_process_fixtures(client_user, 1, 49)
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    assert single_row_response.status_code == status.HTTP_200_OK
    assert len(single_row_response.data) == 1
    assert fifty_row_response.status_code == status.HTTP_200_OK
    assert len(fifty_row_response.data) == 10
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_RECENT_PROCESS_LIST_QUERIES


@pytest.mark.django_db
def test_process_list_has_constant_case_query_budget(api_client, lawyer_user):
    """Fails if process list serializes each case without select_related loading."""
    single_case = _create_process_list_fixtures(lawyer_user, 0, 1)
    api_client.force_authenticate(user=lawyer_user)
    url = reverse('process-list')

    with CaptureQueriesContext(connection) as single_row_queries:
        single_row_response = api_client.get(url)
    fifty_cases = _create_process_list_fixtures(lawyer_user, 1, 49)
    with CaptureQueriesContext(connection) as fifty_row_queries:
        fifty_row_response = api_client.get(url)

    assert (
        single_row_response.status_code,
        len(single_row_response.data),
        fifty_row_response.status_code,
        len(fifty_row_response.data),
    ) == (status.HTTP_200_OK, 1, status.HTTP_200_OK, 50)
    assert {
        item['ref']: (item['case']['id'], item['case']['type'])
        for item in single_row_response.data
    } == single_case
    assert {
        item['ref']: (item['case']['id'], item['case']['type'])
        for item in fifty_row_response.data
    } == single_case | fifty_cases
    assert len(single_row_queries) == len(fifty_row_queries)
    assert len(fifty_row_queries) <= MAX_PROCESS_LIST_QUERIES


@pytest.mark.django_db
def test_recent_processes_keep_top_ten_recent_entries(api_client, client_user):
    """Fails if recent processes stop limiting the response to the newest ten entries."""
    _create_recent_process_fixtures(client_user, 0, 12)
    api_client.force_authenticate(user=client_user)

    response = api_client.get(reverse("recent-processes"))

    assert response.status_code == status.HTTP_200_OK
    assert len(response.data) == 10
    assert [item["process"]["ref"] for item in response.data] == [
        "PERF-RECENT-11",
        "PERF-RECENT-10",
        "PERF-RECENT-9",
        "PERF-RECENT-8",
        "PERF-RECENT-7",
        "PERF-RECENT-6",
        "PERF-RECENT-5",
        "PERF-RECENT-4",
        "PERF-RECENT-3",
        "PERF-RECENT-2",
    ]


@pytest.mark.django_db
def test_recent_processes_serialize_related_models(api_client, client_user):
    """Fails if recent process case, lawyer, client, or file payloads stop serializing."""
    _create_recent_process_fixtures(client_user, 0, 12)
    api_client.force_authenticate(user=client_user)

    response = api_client.get(reverse("recent-processes"))

    assert response.status_code == status.HTTP_200_OK
    expected_file_url = Process.objects.get(ref="PERF-RECENT-11").case_files.get().file.url
    nested_process = response.data[0]["process"]
    assert {
        "case": nested_process["case"]["type"],
        "lawyer": nested_process["lawyer"]["email"],
        "file": nested_process["case_files"][0]["file"],
    } == {
        "case": "Recent case 11",
        "lawyer": "recent-lawyer-11@example.com",
        "file": expected_file_url,
    }
    assert {client["email"] for client in nested_process["clients"]} == {
        "client@example.com",
        "recent-client-11@example.com",
    }


@pytest.mark.django_db
def test_recent_processes_preserve_stage_alert_payload(api_client, client_user):
    """Fails if recent process stages lose their order or optional alert payload."""
    _create_recent_process_fixtures(client_user, 0, 12)
    api_client.force_authenticate(user=client_user)

    response = api_client.get(reverse("recent-processes"))

    assert response.status_code == status.HTTP_200_OK
    nested_process = response.data[0]["process"]
    assert [stage["status"] for stage in nested_process["stages"]] == ["First stage 11", "Alerted stage 11"]
    assert nested_process["stages"][0]["alert"] is None
    assert nested_process["stages"][1]["alert"]["description"] == "Alert 11"
