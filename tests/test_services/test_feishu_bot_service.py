import pytest
import json
from unittest.mock import Mock, AsyncMock, patch
from fastapi import Request, HTTPException
from httpx import TimeoutException, RequestError, Response

from app.services.feishu_bot_service import (
    log_feishu_bot_request,
    convert_grafana_to_feishu,
    is_grafana_alert,
    process_webhook_request,
)
from app.models.feishu_bot_reqlog import FeishuBotReqLogCreate


@pytest.mark.unit
class TestFeishuBotService:
    """Test Feishu Bot service functionality"""

    @pytest.fixture
    def mock_request(self):
        """Create mock FastAPI request"""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/feishu-bot/webhook/proxy/test123"
        request.url.query = "source=alertmanager"
        request.headers = {
            "Content-Type": "application/json",
            "User-Agent": "AlertManager/0.25.0",
            "X-Forwarded-For": "192.168.1.100, 10.0.0.1",
        }
        request.client.host = "10.0.0.1"

        # Mock body method
        async def mock_body():
            return json.dumps({"status": "firing", "title": "Test Alert"}).encode()

        request.body = mock_body
        request._body = None

        return request

    @pytest.fixture
    def mock_session(self):
        """Create mock database session"""
        session = Mock()
        session.add = Mock()
        session.commit = Mock()
        return session

    @pytest.fixture
    def sample_log_entry(self):
        """Sample log entry for testing"""
        return FeishuBotReqLogCreate(
            webhook_id="test123",
            method="POST",
            path="/feishu-bot/webhook/proxy/test123",
            query="source=alertmanager",
            headers={"Content-Type": "application/json"},
            body={"status": "firing", "title": "Test Alert"},
            clientip="192.168.1.100",
            status=200,
            response_headers={"Content-Type": "application/json"},
            response_body={"code": 0, "msg": "success"},
        )

    def test_convert_grafana_to_feishu_bot_firing(self):
        """Test converting Grafana firing alert to Feishu format"""
        grafana_payload = {
            "status": "firing",
            "title": "[HIGH] CPU Usage Alert",
            "message": "CPU usage is above 80% on server-01",
        }

        result = convert_grafana_to_feishu(grafana_payload)

        assert result["msg_type"] == "interactive"
        assert result["card"]["schema"] == "2.0"
        assert result["card"]["header"]["template"] == "red"
        assert result["card"]["header"]["title"]["content"] == "[HIGH] CPU Usage Alert"
        assert result["card"]["header"]["title"]["tag"] == "plain_text"
        assert result["card"]["body"]["elements"][0]["tag"] == "markdown"
        assert (
            result["card"]["body"]["elements"][0]["content"]
            == "CPU usage is above 80% on server-01"
        )

    def test_convert_grafana_to_feishu_bot_resolved(self):
        """Test converting Grafana resolved alert to Feishu format"""
        grafana_payload = {
            "status": "resolved",
            "title": "CPU Usage Alert Resolved",
            "message": "CPU usage is back to normal",
        }

        result = convert_grafana_to_feishu(grafana_payload)

        assert result["card"]["header"]["template"] == "green"
        assert (
            result["card"]["header"]["title"]["content"] == "CPU Usage Alert Resolved"
        )

    def test_convert_grafana_to_feishu_bot_unknown(self):
        """Test converting Grafana unknown status to Feishu format"""
        grafana_payload = {
            "status": "pending",
            "title": "Unknown Alert Status",
            "message": "Alert status is unknown",
        }

        result = convert_grafana_to_feishu(grafana_payload)

        assert result["card"]["header"]["template"] == "blue"

    def test_convert_grafana_to_feishu_bot_minimal(self):
        """Test converting minimal Grafana payload"""
        grafana_payload = {}

        result = convert_grafana_to_feishu(grafana_payload)

        assert result["card"]["header"]["title"]["content"] == "Alert"
        assert result["card"]["body"]["elements"][0]["content"] == ""
        assert result["card"]["header"]["template"] == "blue"

    def test_is_grafana_alert_valid(self):
        """Test valid Grafana alert detection"""
        valid_payloads = [
            {"status": "firing", "title": "Test Alert", "message": "Test message"},
            {
                "status": "resolved",
                "title": "Another Alert",
                "message": "Another message",
                "extra_field": "extra_value",
            },
        ]

        for payload in valid_payloads:
            assert is_grafana_alert(payload) is True

    def test_is_grafana_alert_invalid(self):
        """Test invalid Grafana alert detection"""
        invalid_payloads = [
            {"status": "firing", "title": "Missing message"},
            {"title": "Test", "message": "Missing status"},
            {"status": "firing", "message": "Missing title"},
            {},
            None,
            "not a dict",
            ["not", "a", "dict"],
        ]

        for payload in invalid_payloads:
            assert is_grafana_alert(payload) is False

    @patch("config.config.settings.enable_console_logging", True)
    @patch("config.config.settings.enable_database_logging", True)
    def test_log_feishu_bot_request_success(self, mock_session, sample_log_entry):
        """Test successful logging to both console and database"""
        with patch("app.services.feishu_bot_service.logger") as mock_logger:
            log_feishu_bot_request(mock_session, sample_log_entry)

            # Check console logging
            mock_logger.info.assert_called_once()
            log_message = mock_logger.info.call_args[0][0]
            assert "Feishu Bot Webhook" in log_message
            assert "ID: test123" in log_message
            assert "Status: 200" in log_message

            # Check database logging
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @patch("config.config.settings.enable_console_logging", True)
    @patch("config.config.settings.enable_database_logging", False)
    def test_log_feishu_bot_request_console_only(self, mock_session, sample_log_entry):
        """Test logging to console only"""
        with patch("app.services.feishu_bot_service.logger") as mock_logger:
            log_feishu_bot_request(mock_session, sample_log_entry)

            # Check console logging
            mock_logger.info.assert_called_once()

            # Check database logging is skipped
            mock_session.add.assert_not_called()
            mock_session.commit.assert_not_called()

    @patch("config.config.settings.enable_console_logging", False)
    @patch("config.config.settings.enable_database_logging", True)
    def test_log_feishu_bot_request_database_only(self, mock_session, sample_log_entry):
        """Test logging to database only"""
        with patch("app.services.feishu_bot_service.logger") as mock_logger:
            log_feishu_bot_request(mock_session, sample_log_entry)

            # Check console logging is skipped
            mock_logger.info.assert_not_called()
            mock_logger.error.assert_not_called()

            # Check database logging
            mock_session.add.assert_called_once()
            mock_session.commit.assert_called_once()

    @patch("config.config.settings.enable_console_logging", True)
    @patch("config.config.settings.enable_database_logging", True)
    def test_log_feishu_bot_request_with_error(self, mock_session):
        """Test logging with error message"""
        log_entry = FeishuBotReqLogCreate(
            webhook_id="error_test",
            method="POST",
            path="/feishu-bot/error",
            query="",
            headers={},
            body={},
            clientip="127.0.0.1",
            status=500,
            error_message="Connection timeout",
        )

        with patch("app.services.feishu_bot_service.logger") as mock_logger:
            log_feishu_bot_request(mock_session, log_entry)

            # Check error logging
            mock_logger.error.assert_called_once()
            log_message = mock_logger.error.call_args[0][0]
            assert "Error: Connection timeout" in log_message

    @patch("config.config.settings.enable_console_logging", True)
    @patch("config.config.settings.enable_database_logging", True)
    def test_log_feishu_bot_request_database_error(
        self, mock_session, sample_log_entry
    ):
        """Test handling database logging error"""
        mock_session.commit.side_effect = Exception("Database connection error")

        with patch("app.services.feishu_bot_service.logger") as mock_logger:
            log_feishu_bot_request(mock_session, sample_log_entry)

            # Check that database error is logged
            assert mock_logger.error.call_count == 1
            error_message = mock_logger.error.call_args_list[0][0][0]
            assert "Failed to save log to database" in error_message

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    @patch(
        "config.config.settings.feishu_webhook_base_url",
        "https://open.feishu.cn/open-apis/bot/v2/hook/",
    )
    async def test_process_webhook_request_success(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_request, mock_session
    ):
        """Test successful webhook processing"""
        # Mock httpx client response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {"Content-Type": "application/json"}
        mock_response.json.return_value = {"code": 0, "msg": "success"}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            result = await process_webhook_request(
                "test123", mock_request, mock_session
            )

            # Verify security checks were called
            mock_verify_ip.assert_called_once()
            mock_verify_feishu.assert_called_once()

            # Verify HTTP request was made
            mock_client.post.assert_called_once()
            call_args = mock_client.post.call_args
            assert (
                "https://open.feishu.cn/open-apis/bot/v2/hook/test123"
                in call_args[1]["url"]
                or call_args[0][0]
                == "https://open.feishu.cn/open-apis/bot/v2/hook/test123"
            )

            # Verify logging was called
            mock_log.assert_called_once()

            # Check response
            assert result.status_code == 200

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    async def test_process_webhook_request_grafana_conversion(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_session
    ):
        """Test webhook processing with Grafana alert conversion"""
        # Create request with Grafana alert
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/feishu-bot/webhook/proxy/test123"
        request.url.query = ""
        request.headers = {"Content-Type": "application/json"}
        request.client.host = "127.0.0.1"

        grafana_body = {"status": "firing", "title": "CPU Alert", "message": "High CPU"}

        async def mock_body():
            return json.dumps(grafana_body).encode()

        request.body = mock_body
        request._body = None

        # Mock httpx response
        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {"success": True}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await process_webhook_request("test123", request, mock_session)

            # Verify the payload was converted to Feishu format
            call_args = mock_client.post.call_args
            sent_payload = call_args[1]["json"]
            assert sent_payload["msg_type"] == "interactive"
            assert sent_payload["card"]["header"]["title"]["content"] == "CPU Alert"

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    async def test_process_webhook_request_timeout(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_request, mock_session
    ):
        """Test webhook processing with timeout error"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(
                side_effect=TimeoutException("Request timed out")
            )
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await process_webhook_request("test123", mock_request, mock_session)

            assert exc_info.value.status_code == 504
            assert "timed out" in str(exc_info.value.detail)

            # Verify error was logged
            mock_log.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    async def test_process_webhook_request_connection_error(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_request, mock_session
    ):
        """Test webhook processing with connection error"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=RequestError("Connection failed"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await process_webhook_request("test123", mock_request, mock_session)

            assert exc_info.value.status_code == 502
            assert "Failed to connect" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    async def test_process_webhook_request_general_error(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_request, mock_session
    ):
        """Test webhook processing with general error"""
        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_client_class.return_value.__aenter__.return_value = mock_client

            with pytest.raises(HTTPException) as exc_info:
                await process_webhook_request("test123", mock_request, mock_session)

            assert exc_info.value.status_code == 500
            assert "Internal server error" in str(exc_info.value.detail)

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    async def test_process_webhook_request_x_real_ip(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_session
    ):
        """Test client IP extraction from X-Real-IP header"""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/feishu-bot/test"
        request.url.query = ""
        request.headers = {"X-Real-IP": "203.0.113.100"}
        request.client.host = "10.0.0.1"

        async def mock_body():
            return b'{"test": "data"}'

        request.body = mock_body
        request._body = None

        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await process_webhook_request("test123", request, mock_session)

            # Verify the correct IP was logged
            log_call_args = mock_log.call_args[0][1]  # Second argument is the log entry
            assert log_call_args.clientip == "203.0.113.100"

    @pytest.mark.asyncio
    @patch("app.services.feishu_bot_service.verify_webhook_ip_whitelist")
    @patch("app.services.feishu_bot_service.verify_feishu_bot_webhook")
    @patch("app.services.feishu_bot_service.log_feishu_bot_request")
    async def test_process_webhook_request_invalid_json(
        self, mock_log, mock_verify_feishu, mock_verify_ip, mock_session
    ):
        """Test webhook processing with invalid JSON body"""
        request = Mock(spec=Request)
        request.method = "POST"
        request.url.path = "/feishu-bot/test"
        request.url.query = ""
        request.headers = {}
        request.client.host = "127.0.0.1"

        async def mock_body():
            return b"invalid json content"

        request.body = mock_body
        request._body = None

        mock_response = Mock(spec=Response)
        mock_response.status_code = 200
        mock_response.headers = {}
        mock_response.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_client = AsyncMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_class.return_value.__aenter__.return_value = mock_client

            await process_webhook_request("test123", request, mock_session)

            # Verify the invalid JSON was handled gracefully
            log_call_args = mock_log.call_args[0][1]
            assert "raw" in log_call_args.body
            assert log_call_args.body["raw"] == "invalid json content"
