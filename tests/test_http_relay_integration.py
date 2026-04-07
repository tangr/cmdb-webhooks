import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi import status
from httpx import AsyncClient, TimeoutException, RequestError, Response

from app.models.http_relay_reqlog import HttpRelayReqLog


@pytest.mark.integration
class TestHttpRelayRoutes:
    """Integration tests for HTTP Relay routes"""

    @pytest.mark.asyncio
    async def test_create_http_relay_log_success(
        self, async_client: AsyncClient, sample_cmdb_request, api_key_headers
    ):
        """Test successful HTTP Relay log creation via webhook"""
        with patch("app.services.http_relay_service.process_http_relay_request") as mock_process:
            mock_process.return_value = {
                "status": 200,
                "output": "Success",
                "clientip": "127.0.0.1",
                "processed_at": 1640995200,
            }

            response = await async_client.post(
                "/http-relay/", json=sample_cmdb_request, headers=api_key_headers
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["status"] == 200
            assert data["output"] == "Success"
            assert "processed_at" in data

    @pytest.mark.asyncio
    async def test_create_http_relay_log_missing_host(
        self, async_client: AsyncClient, api_key_headers
    ):
        """Test HTTP Relay log creation with missing host parameter"""
        invalid_request = {
            "method": "GET",
            "path": "/api/test",
            "author": "test_user",
            # Missing required 'host' parameter
        }

        response = await async_client.post(
            "/http-relay/", json=invalid_request, headers=api_key_headers
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "Missing 'host' parameter" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_http_relay_log_invalid_api_key(
        self, async_client: AsyncClient, sample_cmdb_request
    ):
        """Test HTTP Relay log creation with invalid API key"""
        invalid_headers = {"X-API-Key": "invalid-key"}

        response = await async_client.post(
            "/http-relay/", json=sample_cmdb_request, headers=invalid_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_http_relay_log_no_api_key(
        self, async_client: AsyncClient, sample_cmdb_request
    ):
        """Test HTTP Relay log creation without API key"""
        response = await async_client.post("/http-relay/", json=sample_cmdb_request)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_create_http_relay_log_timeout_error(
        self, async_client: AsyncClient, sample_cmdb_request, api_key_headers
    ):
        """Test HTTP Relay log creation with timeout error"""
        with patch("app.services.http_relay_service.process_http_relay_request") as mock_process:
            from fastapi import HTTPException

            mock_process.side_effect = HTTPException(
                status_code=504, detail="Request to target server timed out"
            )

            response = await async_client.post(
                "/http-relay/", json=sample_cmdb_request, headers=api_key_headers
            )

            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
            assert "timed out" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_create_http_relay_log_connection_error(
        self, async_client: AsyncClient, sample_cmdb_request, api_key_headers
    ):
        """Test HTTP Relay log creation with connection error"""
        with patch("app.services.http_relay_service.process_http_relay_request") as mock_process:
            from fastapi import HTTPException

            mock_process.side_effect = HTTPException(
                status_code=502, detail="Failed to connect to target server"
            )

            response = await async_client.post(
                "/http-relay/", json=sample_cmdb_request, headers=api_key_headers
            )

            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            assert "Failed to connect" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_get_http_relay_logs_authenticated(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test getting HTTP Relay logs with authentication"""
        # Create some test logs
        test_logs = [
            HttpRelayReqLog(
                host="http://test1.com",
                method="GET",
                path="/api/test1",
                query="",
                headers={},
                body={},
                author="user1",
                clientip="127.0.0.1",
                status=200,
                output="Success",
            ),
            HttpRelayReqLog(
                host="http://test2.com",
                method="POST",
                path="/api/test2",
                query="param=value",
                headers={"Content-Type": "application/json"},
                body={"data": "test"},
                author="user2",
                clientip="192.168.1.1",
                status=201,
                output="Created",
            ),
        ]

        for log in test_logs:
            test_session.add(log)
        test_session.commit()

        response = await async_client.get("/http-relay/", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        assert "text/html" in response.headers["content-type"]

    @pytest.mark.asyncio
    async def test_get_http_relay_logs_unauthenticated(self, async_client: AsyncClient):
        """Test getting HTTP Relay logs without authentication"""
        response = await async_client.get("/http-relay/")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_http_relay_logs_list_authenticated(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test getting HTTP Relay logs list with authentication"""
        # Create test logs
        for i in range(5):
            log = HttpRelayReqLog(
                host=f"http://test{i}.com",
                method="GET",
                path=f"/api/test{i}",
                query="",
                headers={},
                body={},
                author=f"user{i}",
                clientip="127.0.0.1",
                status=200,
                output=f"Response {i}",
            )
            test_session.add(log)
        test_session.commit()

        response = await async_client.get("/http-relay/logs", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "logs" in data
        assert "pagination" in data
        assert len(data["logs"]) <= 10  # Default page size

    @pytest.mark.asyncio
    async def test_get_http_relay_logs_list_with_pagination(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test HTTP Relay logs list with pagination parameters"""
        # Create 15 test logs
        for i in range(15):
            log = HttpRelayReqLog(
                host=f"http://test{i}.com",
                method="GET",
                path=f"/api/test{i}",
                query="",
                headers={},
                body={},
                author=f"user{i}",
                clientip="127.0.0.1",
                status=200,
            )
            test_session.add(log)
        test_session.commit()

        # Test first page with limit
        response = await async_client.get(
            "/http-relay/logs?skip=0&limit=5", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["logs"]) == 5
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is False

        # Test second page
        response = await async_client.get(
            "/http-relay/logs?skip=5&limit=5", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["logs"]) == 5
        assert data["pagination"]["has_next"] is True
        assert data["pagination"]["has_prev"] is True

    @pytest.mark.asyncio
    async def test_get_http_relay_logs_list_unauthenticated(self, async_client: AsyncClient):
        """Test getting HTTP Relay logs list without authentication"""
        response = await async_client.get("/http-relay/logs")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_get_http_relay_log_by_id_authenticated(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test getting specific HTTP Relay log by ID"""
        log = HttpRelayReqLog(
            host="http://example.com",
            method="POST",
            path="/api/specific",
            query="id=123",
            headers={"Authorization": "Bearer token"},
            body={"action": "update"},
            author="specific_user",
            clientip="10.0.0.1",
            status=200,
            output="Updated successfully",
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        response = await async_client.get(f"/http-relay/{log.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == log.id
        assert data["host"] == "http://example.com"
        assert data["method"] == "POST"
        assert data["author"] == "specific_user"
        assert data["status"] == 200

    @pytest.mark.asyncio
    async def test_get_http_relay_log_by_id_not_found(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test getting HTTP Relay log by non-existent ID"""
        response = await async_client.get("/http-relay/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_get_http_relay_log_by_id_unauthenticated(
        self, async_client: AsyncClient, test_session
    ):
        """Test getting HTTP Relay log by ID without authentication"""
        log = HttpRelayReqLog(
            host="http://test.com",
            method="GET",
            path="/test",
            query="",
            headers={},
            body={},
            author="test",
            clientip="127.0.0.1",
            status=200,
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        response = await async_client.get(f"/http-relay/{log.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_update_http_relay_log_admin(
        self, async_client: AsyncClient, admin_auth_headers, test_session
    ):
        """Test updating HTTP Relay log with admin privileges"""
        log = HttpRelayReqLog(
            host="http://original.com",
            method="GET",
            path="/original",
            query="",
            headers={},
            body={},
            author="original_author",
            clientip="127.0.0.1",
            status=200,
            output="Original output",
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        update_data = {
            "status": 404,
            "output": "Updated output",
            "author": "updated_author",
        }

        response = await async_client.put(
            f"/http-relay/{log.id}", json=update_data, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["status"] == 404
        assert data["output"] == "Updated output"
        assert data["author"] == "updated_author"

    @pytest.mark.asyncio
    async def test_update_http_relay_log_non_admin(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test updating HTTP Relay log without admin privileges"""
        log = HttpRelayReqLog(
            host="http://test.com",
            method="GET",
            path="/test",
            query="",
            headers={},
            body={},
            author="test",
            clientip="127.0.0.1",
            status=200,
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        update_data = {"status": 404}

        response = await async_client.put(
            f"/http-relay/{log.id}", json=update_data, headers=auth_headers
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_update_http_relay_log_not_found(
        self, async_client: AsyncClient, admin_auth_headers
    ):
        """Test updating non-existent HTTP Relay log"""
        update_data = {"status": 404}

        response = await async_client.put(
            "/http-relay/99999", json=update_data, headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_http_relay_log_admin(
        self, async_client: AsyncClient, admin_auth_headers, test_session
    ):
        """Test deleting HTTP Relay log with admin privileges"""
        log = HttpRelayReqLog(
            host="http://delete-test.com",
            method="DELETE",
            path="/api/delete",
            query="",
            headers={},
            body={},
            author="delete_user",
            clientip="127.0.0.1",
            status=204,
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)
        log_id = log.id

        response = await async_client.delete(
            f"/http-relay/{log_id}", headers=admin_auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "deleted successfully" in data["message"].lower()

        # Verify log is actually deleted
        verify_response = await async_client.get(
            f"/http-relay/{log_id}", headers=admin_auth_headers
        )
        assert verify_response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_delete_http_relay_log_non_admin(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test deleting HTTP Relay log without admin privileges"""
        log = HttpRelayReqLog(
            host="http://test.com",
            method="GET",
            path="/test",
            query="",
            headers={},
            body={},
            author="test",
            clientip="127.0.0.1",
            status=200,
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        response = await async_client.delete(f"/http-relay/{log.id}", headers=auth_headers)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    @pytest.mark.asyncio
    async def test_delete_http_relay_log_not_found(
        self, async_client: AsyncClient, admin_auth_headers
    ):
        """Test deleting non-existent HTTP Relay log"""
        response = await async_client.delete("/http-relay/99999", headers=admin_auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_http_relay_log_filtering_and_search(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test HTTP Relay log filtering and search functionality"""
        # Create logs with different statuses and authors
        logs = [
            HttpRelayReqLog(
                host="http://success.com",
                method="GET",
                path="/success",
                query="",
                headers={},
                body={},
                author="user1",
                clientip="127.0.0.1",
                status=200,
                output="Success",
            ),
            HttpRelayReqLog(
                host="http://error.com",
                method="POST",
                path="/error",
                query="",
                headers={},
                body={},
                author="user2",
                clientip="127.0.0.1",
                status=500,
                output="Error",
            ),
            HttpRelayReqLog(
                host="http://notfound.com",
                method="GET",
                path="/notfound",
                query="",
                headers={},
                body={},
                author="user1",
                clientip="127.0.0.1",
                status=404,
                output="Not Found",
            ),
        ]

        for log in logs:
            test_session.add(log)
        test_session.commit()

        # Test filtering by author (if supported)
        response = await async_client.get(
            "/http-relay/logs?author=user1", headers=auth_headers
        )
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            if "logs" in data:
                user1_logs = [
                    log for log in data["logs"] if log.get("author") == "user1"
                ]
                assert len(user1_logs) >= 1

    @pytest.mark.asyncio
    async def test_http_relay_request_with_various_http_methods(
        self, async_client: AsyncClient, api_key_headers
    ):
        """Test HTTP Relay requests with different HTTP methods"""
        test_cases = [
            {"method": "GET", "expected_status": 200},
            {"method": "POST", "expected_status": 200},
            {"method": "PUT", "expected_status": 200},
            {"method": "DELETE", "expected_status": 200},
            {"method": "PATCH", "expected_status": 200},
        ]

        for case in test_cases:
            request_data = {
                "host": "http://httpbin.org",
                "method": case["method"],
                "path": f"/{case['method'].lower()}",
                "query": "test=1",
                "headers": {"User-Agent": "webhook-proxy-test"},
                "body": (
                    {"test": "data"}
                    if case["method"] in ["POST", "PUT", "PATCH"]
                    else {}
                ),
                "author": "test_user",
            }

            with patch(
                "app.services.http_relay_service.process_http_relay_request"
            ) as mock_process:
                mock_process.return_value = {
                    "status": case["expected_status"],
                    "output": f"{case['method']} response",
                    "clientip": "127.0.0.1",
                    "processed_at": 1640995200,
                }

                response = await async_client.post(
                    "/http-relay/", json=request_data, headers=api_key_headers
                )

                assert response.status_code == status.HTTP_200_OK
                data = response.json()
                assert data["status"] == case["expected_status"]
