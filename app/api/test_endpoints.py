import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import json

from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Create authentication headers."""
    # For testing purposes, we mock the token validation
    with patch('app.core.security.jwt.decode') as mock_decode:
        mock_decode.return_value = {"sub": "test-user"}
        response = TestClient(app).post(
            "/api/v1/auth/token",
            data={"username": "admin", "password": "password"}
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}


def test_root_endpoint(client):
    """Test the root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Welcome" in response.json()["message"]


def test_health_endpoint(client):
    """Test the health endpoint."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_auth_endpoint(client):
    """Test the authentication endpoint."""
    # Test successful authentication
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "password"}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "token_type" in response.json()
    assert response.json()["token_type"] == "bearer"
    
    # Test failed authentication
    response = client.post(
        "/api/v1/auth/token",
        data={"username": "admin", "password": "wrong-password"}
    )
    assert response.status_code == 401


def test_unauthorized_access(client):
    """Test unauthorized access to protected endpoints."""
    response = client.get("/api/v1/status/test-job")
    assert response.status_code == 401
    
    response = client.post("/api/v1/execute", json={})
    assert response.status_code == 401


def test_execute_batch(client, auth_headers):
    """Test the execute batch endpoint."""
    # Mock the task_queue.enqueue_job method
    with patch('app.core.queue_instance.task_queue.enqueue_job') as mock_enqueue:
        mock_enqueue.return_value = None
        
        # Send a valid request
        request_data = {
            "batch_id": "test-batch",
            "tests": [
                {
                    "test_id": "test-1",
                    "turns": [
                        {
                            "turn_id": "turn-1",
                            "order": 1,
                            "user_input": "Hello",
                            "validations": [
                                {
                                    "validation_id": "validation-1",
                                    "validation_type": "contains",
                                    "validation_parameters": {
                                        "text": "world",
                                        "case_sensitive": True
                                    }
                                }
                            ]
                        }
                    ],
                    "credentials": {
                        "sf_org_domain": "https://example.org",
                        "sf_client_id": "client-id",
                        "sf_client_secret": "client-secret",
                        "sf_agent_id": "agent-id"
                    }
                }
            ]
        }
        
        response = client.post(
            "/api/v1/execute",
            json=request_data,
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "job_id" in response.json()
        assert response.json()["status"] == "queued"
        
        # Verify that enqueue_job was called
        mock_enqueue.assert_called_once()


def test_get_batch_status(client, auth_headers):
    """Test the get batch status endpoint."""
    # Mock the execution service
    with patch('app.services.execution.ExecutionService.get_batch_status') as mock_get_status:
        # Set up the mock to return a status object
        mock_get_status.return_value = {
            "job_id": "test-job",
            "batch_id": "test-batch",
            "status": "running",
            "started_at": "2023-01-01T00:00:00",
            "progress": 50,
            "total_tests": 10,
            "completed_tests": 5,
            "failed_tests": 0,
            "current_test_id": "test-6",
            "current_turn": 2
        }
        
        # Send a request
        response = client.get(
            "/api/v1/status/test-job",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["job_id"] == "test-job"
        assert response.json()["status"] == "running"
        assert response.json()["progress"] == 50
        
        # Test with a non-existent job
        mock_get_status.return_value = None
        
        response = client.get(
            "/api/v1/status/non-existent-job",
            headers=auth_headers
        )
        
        assert response.status_code == 404


def test_get_batch_results(client, auth_headers):
    """Test the get batch results endpoint."""
    # Mock the execution service
    with patch('app.services.execution.ExecutionService.get_batch_results') as mock_get_results:
        # Set up the mock to return a results object
        mock_get_results.return_value = {
            "job_id": "test-job",
            "batch_id": "test-batch",
            "status": "completed",
            "started_at": "2023-01-01T00:00:00",
            "completed_at": "2023-01-01T00:05:00",
            "total_tests": 2,
            "completed_tests": 2,
            "failed_tests": 0,
            "total_validations": 10,
            "passed_validations": 8,
            "failed_validations": 2,
            "pass_rate": 80.0,
            "avg_response_time": 500.0,
            "test_results": [
                {
                    "test_id": "test-1",
                    "status": "completed",
                    "started_at": "2023-01-01T00:00:00",
                    "completed_at": "2023-01-01T00:02:30",
                    "total_validations": 5,
                    "passed_validations": 4,
                    "failed_validations": 1,
                    "pass_rate": 80.0,
                    "avg_response_time": 450.0,
                    "turn_results": []
                },
                {
                    "test_id": "test-2",
                    "status": "completed",
                    "started_at": "2023-01-01T00:02:30",
                    "completed_at": "2023-01-01T00:05:00",
                    "total_validations": 5,
                    "passed_validations": 4,
                    "failed_validations": 1,
                    "pass_rate": 80.0,
                    "avg_response_time": 550.0,
                    "turn_results": []
                }
            ]
        }
        
        # Send a request
        response = client.get(
            "/api/v1/results/test-job",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["job_id"] == "test-job"
        assert response.json()["status"] == "completed"
        assert response.json()["pass_rate"] == 80.0
        assert len(response.json()["test_results"]) == 2
        
        # Test with include_scraped_content
        response = client.get(
            "/api/v1/results/test-job?include_scraped_content=true",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        
        # Test with a non-existent job
        mock_get_results.return_value = None
        
        response = client.get(
            "/api/v1/results/non-existent-job",
            headers=auth_headers
        )
        
        assert response.status_code == 404


def test_queue_status(client, auth_headers):
    """Test the queue status endpoint."""
    # Mock the task queue
    with patch('app.core.queue_instance.task_queue.get_status') as mock_get_status:
        # Set up the mock to return a status object
        mock_get_status.return_value = {
            "running": True,
            "workers": 3,
            "queue_size": 5,
            "active_jobs": 2,
            "active_job_ids": ["job-1", "job-2"]
        }
        
        # Send a request
        response = client.get(
            "/api/v1/queue/status",
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert response.json()["running"] is True
        assert response.json()["workers"] == 3
        assert response.json()["queue_size"] == 5
        assert response.json()["active_jobs"] == 2
        assert "job-1" in response.json()["active_job_ids"]


def test_admin_server_status(client, auth_headers):
    """Test the admin server status endpoint."""
    # Mock the is_admin dependency
    with patch('app.core.security.is_admin', return_value=True):
        # Mock the database connection check
        with patch('sqlalchemy.orm.session.Session.execute'):
            # Send a request
            response = client.get(
                "/api/v1/admin/status",
                headers=auth_headers
            )
            
            assert response.status_code == 200
            assert "version" in response.json()
            assert "database_connected" in response.json()
            assert "queue_status" in response.json()
            assert "memory_usage_mb" in response.json()


def test_admin_update_setting(client, auth_headers):
    """Test the admin update setting endpoint."""
    # Mock the is_admin dependency
    with patch('app.core.security.is_admin', return_value=True):
        # Send a request
        response = client.post(
            "/api/v1/admin/settings",
            json={"name": "LOG_LEVEL", "value": "DEBUG"},
            headers=auth_headers
        )
        
        assert response.status_code == 200
        assert "message" in response.json()
        
        # Test with an invalid setting
        response = client.post(
            "/api/v1/admin/settings",
            json={"name": "INVALID_SETTING", "value": "value"},
            headers=auth_headers
        )
        
        assert response.status_code == 400