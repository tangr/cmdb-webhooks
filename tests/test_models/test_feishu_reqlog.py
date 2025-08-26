import pytest
import time
from sqlmodel import Session, select
from app.models.feishu_reqlog import (
    FeishuReqLog,
    FeishuReqLogCreate,
    FeishuReqLogUpdate,
    FeishuReqLogRead,
)


@pytest.mark.unit
class TestFeishuReqLogModel:
    """Test Feishu request log model functionality"""

    def test_create_feishu_reqlog(self, test_session: Session):
        """Test creating a new Feishu request log"""
        log_data = FeishuReqLogCreate(
            webhook_id="webhook_123",
            method="POST",
            path="/feishu/webhook/proxy/123",
            query="source=alertmanager",
            headers={"Content-Type": "application/json", "User-Agent": "alertmanager"},
            body={
                "status": "firing",
                "title": "Test Alert",
                "message": "CPU usage high",
            },
            clientip="192.168.1.100",
            status=200,
            response_headers={"Content-Type": "application/json"},
            response_body={"success": True, "message_id": "msg_12345"},
            error_message=None,
        )

        db_log = FeishuReqLog.model_validate(log_data)
        test_session.add(db_log)
        test_session.commit()
        test_session.refresh(db_log)

        assert db_log.id is not None
        assert db_log.webhook_id == "webhook_123"
        assert db_log.method == "POST"
        assert db_log.path == "/feishu/webhook/proxy/123"
        assert db_log.query == "source=alertmanager"
        assert db_log.headers["Content-Type"] == "application/json"
        assert db_log.body["status"] == "firing"
        assert db_log.clientip == "192.168.1.100"
        assert db_log.status == 200
        assert db_log.response_headers["Content-Type"] == "application/json"
        assert db_log.response_body["success"] is True
        assert db_log.error_message is None
        assert db_log.created_at > 0
        assert db_log.updated_at > 0

    def test_feishu_reqlog_timestamps(self, test_session: Session):
        """Test that timestamps are automatically set"""
        before_creation = int(time.time())

        log = FeishuReqLog(
            webhook_id="webhook_test",
            method="POST",
            path="/feishu/test",
            query="",
            headers={},
            body={},
            clientip="127.0.0.1",
            status=200,
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        after_creation = int(time.time())

        assert before_creation <= log.created_at <= after_creation
        assert before_creation <= log.updated_at <= after_creation
        assert log.created_at == log.updated_at

    def test_feishu_reqlog_with_error(self, test_session: Session):
        """Test Feishu request log with error"""
        log = FeishuReqLog(
            webhook_id="webhook_error",
            method="POST",
            path="/feishu/webhook/proxy/invalid",
            query="test=1",
            headers={"Content-Type": "application/json"},
            body={"invalid": "data"},
            clientip="10.0.0.1",
            status=500,
            response_headers=None,
            response_body=None,
            error_message="Connection timeout to Feishu API",
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.webhook_id == "webhook_error"
        assert log.status == 500
        assert log.response_headers is None
        assert log.response_body is None
        assert log.error_message == "Connection timeout to Feishu API"

    def test_feishu_reqlog_complex_data(self, test_session: Session):
        """Test Feishu request log with complex JSON data"""
        complex_body = {
            "msg_type": "interactive",
            "card": {
                "config": {"wide_screen_mode": True},
                "header": {
                    "title": {"tag": "plain_text", "content": "Alert Notification"}
                },
                "elements": [
                    {
                        "tag": "div",
                        "text": {
                            "tag": "lark_md",
                            "content": "**Status**: firing\n**Instance**: server-01",
                        },
                    },
                    {
                        "tag": "action",
                        "actions": [
                            {
                                "tag": "button",
                                "text": {
                                    "tag": "plain_text",
                                    "content": "View Details",
                                },
                            }
                        ],
                    },
                ],
            },
        }

        complex_response = {
            "code": 0,
            "msg": "success",
            "data": {
                "message_id": "om_12345678901234567890123456789012",
                "root_id": "",
                "parent_id": "",
                "msg_type": "interactive",
            },
        }

        log = FeishuReqLog(
            webhook_id="webhook_complex",
            method="POST",
            path="/feishu/webhook/alias/alerts",
            query="format=card",
            headers={
                "Content-Type": "application/json",
                "Authorization": "Bearer bot_token_123",
            },
            body=complex_body,
            clientip="172.16.0.10",
            status=200,
            response_headers={"Content-Type": "application/json; charset=utf-8"},
            response_body=complex_response,
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.body["card"]["header"]["title"]["content"] == "Alert Notification"
        assert (
            log.body["card"]["elements"][0]["text"]["content"]
            == "**Status**: firing\n**Instance**: server-01"
        )
        assert (
            log.response_body["data"]["message_id"]
            == "om_12345678901234567890123456789012"
        )
        assert log.response_body["code"] == 0

    def test_feishu_reqlog_update(self, test_session: Session):
        """Test updating Feishu request log"""
        log = FeishuReqLog(
            webhook_id="webhook_original",
            method="POST",
            path="/feishu/original",
            query="",
            headers={},
            body={},
            clientip="127.0.0.1",
            status=200,
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        original_created_at = log.created_at

        # Sleep for a moment to ensure timestamp difference
        time.sleep(1)

        # Update the log
        update_data = FeishuReqLogUpdate(
            status=400,
            error_message="Invalid webhook format",
            response_body={"error": "Bad Request"},
        )

        log.status = update_data.status
        log.error_message = update_data.error_message
        log.response_body = update_data.response_body
        log.updated_at = int(time.time())

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.status == 400
        assert log.error_message == "Invalid webhook format"
        assert log.response_body["error"] == "Bad Request"
        assert log.created_at == original_created_at
        assert log.updated_at > original_created_at

    def test_feishu_reqlog_read_model(self, test_session: Session):
        """Test FeishuReqLogRead model"""
        log = FeishuReqLog(
            webhook_id="webhook_read_test",
            method="POST",
            path="/feishu/webhook/proxy/read_test",
            query="format=json",
            headers={"Content-Type": "application/json"},
            body={"test": "read_data"},
            clientip="192.168.1.50",
            status=201,
            response_headers={"Location": "/messages/12345"},
            response_body={"id": "12345", "status": "sent"},
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        read_log = FeishuReqLogRead.model_validate(log)

        assert read_log.id == log.id
        assert read_log.webhook_id == log.webhook_id
        assert read_log.method == log.method
        assert read_log.path == log.path
        assert read_log.query == log.query
        assert read_log.headers == log.headers
        assert read_log.body == log.body
        assert read_log.clientip == log.clientip
        assert read_log.status == log.status
        assert read_log.response_headers == log.response_headers
        assert read_log.response_body == log.response_body
        assert read_log.error_message == log.error_message
        assert read_log.created_at == log.created_at
        assert read_log.updated_at == log.updated_at

    def test_query_feishu_reqlog(self, test_session: Session):
        """Test querying Feishu request logs"""
        logs = [
            FeishuReqLog(
                webhook_id="webhook_1",
                method="POST",
                path="/feishu/webhook/proxy/1",
                query="type=alert",
                headers={},
                body={"status": "firing"},
                clientip="10.0.0.1",
                status=200,
            ),
            FeishuReqLog(
                webhook_id="webhook_2",
                method="POST",
                path="/feishu/webhook/proxy/2",
                query="type=resolve",
                headers={},
                body={"status": "resolved"},
                clientip="10.0.0.2",
                status=200,
            ),
            FeishuReqLog(
                webhook_id="webhook_1",
                method="POST",
                path="/feishu/webhook/proxy/1",
                query="type=alert",
                headers={},
                body={"status": "firing"},
                clientip="10.0.0.1",
                status=500,
                error_message="API timeout",
            ),
        ]

        for log in logs:
            test_session.add(log)
        test_session.commit()

        # Query by webhook_id
        webhook1_logs = test_session.exec(
            select(FeishuReqLog).where(FeishuReqLog.webhook_id == "webhook_1")
        ).all()
        assert len(webhook1_logs) == 2

        # Query by status
        success_logs = test_session.exec(
            select(FeishuReqLog).where(FeishuReqLog.status == 200)
        ).all()
        assert len(success_logs) == 2

        # Query by error
        error_logs = test_session.exec(
            select(FeishuReqLog).where(FeishuReqLog.error_message.is_not(None))
        ).all()
        assert len(error_logs) == 1
        assert error_logs[0].error_message == "API timeout"

    def test_feishu_reqlog_optional_fields(self, test_session: Session):
        """Test Feishu request log with minimal required fields"""
        log = FeishuReqLog(
            webhook_id="minimal_webhook",
            method="POST",
            path="/feishu/minimal",
            query="",
            headers={},
            body={},
            clientip="127.0.0.1",
            status=200,
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.webhook_id == "minimal_webhook"
        assert log.response_headers is None
        assert log.response_body is None
        assert log.error_message is None
        assert log.created_at > 0
        assert log.updated_at > 0
