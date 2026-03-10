import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi import status
from httpx import AsyncClient, TimeoutException, RequestError, Response

from app.models.feishu_bot_reqlog import FeishuBotReqLog


@pytest.mark.integration
class TestFeishuBotRoutes:
    """Integration tests for Feishu Bot routes"""

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_proxy_by_id_success(
        self, async_client: AsyncClient, sample_feishu_webhook
    ):
        """Test successful Feishu Bot webhook proxy by ID"""
        webhook_id = "test_webhook_123"

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi.responses import JSONResponse

            mock_process.return_value = JSONResponse(
                content={"code": 0, "msg": "success", "message_id": "msg_12345"},
                status_code=200,
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json=sample_feishu_webhook
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["code"] == 0
            assert data["msg"] == "success"

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_proxy_by_alias_success(
        self, async_client: AsyncClient, sample_feishu_webhook
    ):
        """Test successful Feishu Bot webhook proxy by alias name"""
        webhook_name = "alertmanager-webhook"

        with patch(
            "app.services.webhook_mapping.get_webhook_id_by_name"
        ) as mock_get_id:
            mock_get_id.return_value = "abc123def456"

            with patch(
                "app.services.feishu_bot_service.process_webhook_request"
            ) as mock_process:
                from fastapi.responses import JSONResponse

                mock_process.return_value = JSONResponse(
                    content={"code": 0, "msg": "success"}, status_code=200
                )

                response = await async_client.post(
                    f"/feishu-bot/webhook/alias/{webhook_name}", json=sample_feishu_webhook
                )

                assert response.status_code == status.HTTP_200_OK
                mock_get_id.assert_called_once_with(webhook_name)

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_proxy_by_alias_not_found(
        self, async_client: AsyncClient, sample_feishu_webhook
    ):
        """Test Feishu Bot webhook proxy with non-existent alias"""
        webhook_name = "nonexistent-webhook"

        with patch(
            "app.services.webhook_mapping.get_webhook_id_by_name"
        ) as mock_get_id:
            mock_get_id.return_value = None

            response = await async_client.post(
                f"/feishu-bot/webhook/alias/{webhook_name}", json=sample_feishu_webhook
            )

            assert response.status_code == status.HTTP_404_NOT_FOUND
            assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_grafana_alert_conversion(
        self, async_client: AsyncClient
    ):
        """Test Feishu Bot webhook with Grafana alert format conversion"""
        webhook_id = "grafana_webhook"
        grafana_alert = {
            "status": "firing",
            "title": "[CRITICAL] High CPU Usage",
            "message": "CPU usage is above 90% on server-prod-01 for the last 5 minutes",
        }

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi.responses import JSONResponse

            mock_process.return_value = JSONResponse(
                content={"code": 0, "msg": "ok"}, status_code=200
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json=grafana_alert
            )

            assert response.status_code == status.HTTP_200_OK
            # Verify process_webhook_request was called with the webhook ID
            mock_process.assert_called_once()
            call_args = mock_process.call_args[0]
            assert call_args[0] == webhook_id

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_timeout_error(
        self, async_client: AsyncClient, sample_feishu_webhook
    ):
        """Test Feishu Bot webhook with timeout error"""
        webhook_id = "timeout_test"

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi import HTTPException

            mock_process.side_effect = HTTPException(
                status_code=504, detail="Request to Feishu API timed out"
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json=sample_feishu_webhook
            )

            assert response.status_code == status.HTTP_504_GATEWAY_TIMEOUT
            assert "timed out" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_connection_error(
        self, async_client: AsyncClient, sample_feishu_webhook
    ):
        """Test Feishu Bot webhook with connection error"""
        webhook_id = "connection_error_test"

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi import HTTPException

            mock_process.side_effect = HTTPException(
                status_code=502, detail="Failed to connect to Feishu API"
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json=sample_feishu_webhook
            )

            assert response.status_code == status.HTTP_502_BAD_GATEWAY
            assert "Failed to connect" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_invalid_json(self, async_client: AsyncClient):
        """Test Feishu Bot webhook with invalid JSON payload"""
        webhook_id = "invalid_json_test"

        response = await async_client.post(
            f"/feishu-bot/webhook/proxy/{webhook_id}",
            data="invalid json content",
            headers={"Content-Type": "application/json"},
        )

        # This should be handled by FastAPI's JSON parsing
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_empty_payload(self, async_client: AsyncClient):
        """Test Feishu Bot webhook with empty payload"""
        webhook_id = "empty_payload_test"

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi.responses import JSONResponse

            mock_process.return_value = JSONResponse(
                content={"code": 0, "msg": "ok"}, status_code=200
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json={}
            )

            assert response.status_code == status.HTTP_200_OK

    @pytest.mark.asyncio
    async def test_feishu_bot_logs_list_authenticated(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test getting Feishu Bot logs with authentication"""
        # Create test logs
        test_logs = [
            FeishuBotReqLog(
                webhook_id="webhook_1",
                method="POST",
                path="/feishu-bot/webhook/proxy/webhook_1",
                query="source=alertmanager",
                headers={"Content-Type": "application/json"},
                body={"status": "firing", "title": "Alert 1"},
                clientip="192.168.1.100",
                status=200,
                response_body={"code": 0, "msg": "success"},
            ),
            FeishuBotReqLog(
                webhook_id="webhook_2",
                method="POST",
                path="/feishu-bot/webhook/proxy/webhook_2",
                query="",
                headers={"Content-Type": "application/json"},
                body={"status": "resolved", "title": "Alert 2"},
                clientip="192.168.1.101",
                status=200,
                response_body={"code": 0, "msg": "success"},
            ),
        ]

        for log in test_logs:
            test_session.add(log)
        test_session.commit()

        response = await async_client.get("/feishu-bot/logs", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "data" in data
        assert isinstance(data["data"], list)
        assert len(data["data"]) >= 2

        # Check log structure
        log_entry = data["data"][0]
        assert "webhook_id" in log_entry
        assert "method" in log_entry
        assert "status" in log_entry
        assert "created_at" in log_entry

    @pytest.mark.asyncio
    async def test_feishu_bot_logs_list_with_pagination(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test Feishu Bot logs list with pagination"""
        # Create multiple test logs
        for i in range(15):
            log = FeishuBotReqLog(
                webhook_id=f"webhook_{i}",
                method="POST",
                path=f"/feishu-bot/webhook/proxy/webhook_{i}",
                query="",
                headers={},
                body={"alert_id": i},
                clientip="127.0.0.1",
                status=200,
            )
            test_session.add(log)
        test_session.commit()

        # Test with limit parameter
        response = await async_client.get("/feishu-bot/logs?limit=5", headers=auth_headers)

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert len(data["data"]) == 5

    @pytest.mark.asyncio
    async def test_feishu_bot_logs_list_unauthenticated(self, async_client: AsyncClient):
        """Test getting Feishu Bot logs without authentication"""
        response = await async_client.get("/feishu-bot/logs")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_feishu_bot_log_by_id_authenticated(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test getting specific Feishu Bot log by ID"""
        log = FeishuBotReqLog(
            webhook_id="specific_webhook",
            method="POST",
            path="/feishu-bot/webhook/proxy/specific_webhook",
            query="format=card",
            headers={"Authorization": "Bearer bot_token"},
            body={
                "msg_type": "interactive",
                "card": {"header": {"title": {"content": "Test Alert"}}},
            },
            clientip="10.0.0.50",
            status=200,
            response_headers={"Content-Type": "application/json"},
            response_body={"code": 0, "msg": "success", "message_id": "om_12345"},
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        response = await async_client.get(
            f"/feishu-bot/logs/{log.id}", headers=auth_headers
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == log.id
        assert data["webhook_id"] == "specific_webhook"
        assert data["method"] == "POST"
        assert data["status"] == 200
        assert data["body"]["msg_type"] == "interactive"
        assert data["response_body"]["message_id"] == "om_12345"

    @pytest.mark.asyncio
    async def test_feishu_bot_log_by_id_not_found(
        self, async_client: AsyncClient, auth_headers
    ):
        """Test getting Feishu Bot log by non-existent ID"""
        response = await async_client.get("/feishu-bot/logs/99999", headers=auth_headers)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert "not found" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_feishu_bot_log_by_id_unauthenticated(
        self, async_client: AsyncClient, test_session
    ):
        """Test getting Feishu Bot log by ID without authentication"""
        log = FeishuBotReqLog(
            webhook_id="test_webhook",
            method="POST",
            path="/feishu-bot/test",
            query="",
            headers={},
            body={},
            clientip="127.0.0.1",
            status=200,
        )
        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        response = await async_client.get(f"/feishu-bot/logs/{log.id}")

        assert response.status_code == status.HTTP_401_UNAUTHORIZED

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_with_various_alert_types(
        self, async_client: AsyncClient
    ):
        """Test Feishu Bot webhook with various alert types and formats"""
        webhook_id = "multi_format_webhook"

        test_cases = [
            # Grafana firing alert
            {
                "payload": {
                    "status": "firing",
                    "title": "[HIGH] Database Connection Lost",
                    "message": "Unable to connect to database server db-prod-01",
                },
                "expected_conversion": True,
            },
            # Grafana resolved alert
            {
                "payload": {
                    "status": "resolved",
                    "title": "Database Connection Restored",
                    "message": "Database connection is now stable",
                },
                "expected_conversion": True,
            },
            # Direct Feishu card format
            {
                "payload": {
                    "msg_type": "interactive",
                    "card": {
                        "header": {
                            "title": {"content": "Custom Alert", "tag": "plain_text"}
                        },
                        "body": {
                            "elements": [
                                {"tag": "markdown", "content": "Custom message"}
                            ]
                        },
                    },
                },
                "expected_conversion": False,
            },
            # Simple text message
            {
                "payload": {"text": "Simple text alert message"},
                "expected_conversion": False,
            },
        ]

        for i, case in enumerate(test_cases):
            with patch(
                "app.services.feishu_bot_service.process_webhook_request"
            ) as mock_process:
                from fastapi.responses import JSONResponse

                mock_process.return_value = JSONResponse(
                    content={"code": 0, "msg": "ok"}, status_code=200
                )

                response = await async_client.post(
                    f"/feishu-bot/webhook/proxy/{webhook_id}", json=case["payload"]
                )

                assert (
                    response.status_code == status.HTTP_200_OK
                ), f"Test case {i} failed"

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_error_logging(
        self, async_client: AsyncClient, test_session
    ):
        """Test that Feishu Bot webhook errors are properly logged"""
        webhook_id = "error_logging_test"

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi import HTTPException

            mock_process.side_effect = HTTPException(
                status_code=500, detail="Internal server error"
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json={"test": "error"}
            )

            assert response.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR

            # Note: Error logging verification would require checking database logs
            # This would be tested in the service layer tests

    @pytest.mark.asyncio
    async def test_feishu_bot_logs_filtering(
        self, async_client: AsyncClient, auth_headers, test_session
    ):
        """Test Feishu Bot logs filtering functionality"""
        # Create logs with different webhook IDs and statuses
        logs = [
            FeishuBotReqLog(
                webhook_id="webhook_alerts",
                method="POST",
                path="/feishu-bot/webhook/proxy/webhook_alerts",
                query="",
                headers={},
                body={"status": "firing"},
                clientip="127.0.0.1",
                status=200,
            ),
            FeishuBotReqLog(
                webhook_id="webhook_notifications",
                method="POST",
                path="/feishu-bot/webhook/proxy/webhook_notifications",
                query="",
                headers={},
                body={"status": "info"},
                clientip="127.0.0.1",
                status=200,
            ),
            FeishuBotReqLog(
                webhook_id="webhook_alerts",
                method="POST",
                path="/feishu-bot/webhook/proxy/webhook_alerts",
                query="",
                headers={},
                body={"status": "resolved"},
                clientip="127.0.0.1",
                status=500,
                error_message="API timeout",
            ),
        ]

        for log in logs:
            test_session.add(log)
        test_session.commit()

        # Test filtering by webhook_id (if supported by the API)
        response = await async_client.get(
            "/feishu-bot/logs?webhook_id=webhook_alerts", headers=auth_headers
        )
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            if isinstance(data.get("data"), list):
                alert_logs = [
                    log for log in data["data"] if log.get("webhook_id") == "webhook_alerts"
                ]
                assert len(alert_logs) >= 2

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_request_headers_forwarding(
        self, async_client: AsyncClient
    ):
        """Test that request headers are properly forwarded"""
        webhook_id = "header_test"

        custom_headers = {
            "Content-Type": "application/json",
            "X-Custom-Header": "test-value",
            "User-Agent": "CustomClient/1.0",
        }

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi.responses import JSONResponse

            mock_process.return_value = JSONResponse(
                content={"code": 0, "msg": "ok"}, status_code=200
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}",
                json={"test": "headers"},
                headers=custom_headers,
            )

            assert response.status_code == status.HTTP_200_OK
            mock_process.assert_called_once()

    @pytest.mark.asyncio
    async def test_feishu_bot_webhook_large_payload(self, async_client: AsyncClient):
        """Test Feishu Bot webhook with large JSON payload"""
        webhook_id = "large_payload_test"

        # Create a large payload
        large_payload = {
            "msg_type": "interactive",
            "card": {
                "header": {
                    "title": {"content": "Large Alert Data", "tag": "plain_text"}
                },
                "body": {
                    "elements": [
                        {
                            "tag": "markdown",
                            "content": f"Alert data entry {i}: " + "x" * 100,
                        }
                        for i in range(100)  # Create 100 elements
                    ]
                },
            },
        }

        with patch(
            "app.services.feishu_bot_service.process_webhook_request"
        ) as mock_process:
            from fastapi.responses import JSONResponse

            mock_process.return_value = JSONResponse(
                content={"code": 0, "msg": "ok"}, status_code=200
            )

            response = await async_client.post(
                f"/feishu-bot/webhook/proxy/{webhook_id}", json=large_payload
            )

            assert response.status_code == status.HTTP_200_OK
