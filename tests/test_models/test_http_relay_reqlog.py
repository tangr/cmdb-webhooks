import pytest
import time
from sqlmodel import Session, select
from app.models.http_relay_reqlog import (
    HttpRelayReqLog,
    HttpRelayReqLogCreate,
    HttpRelayReqLogUpdate,
    HttpRelayReqLogRead,
    PaginationUrls,
    PaginationInfo,
    HttpRelayReqLogListResponse,
)


@pytest.mark.unit
class TestHttpRelayReqLogModel:
    """Test HTTP Relay request log model functionality"""

    def test_create_http_relay_reqlog(self, test_session: Session):
        """Test creating a new HTTP Relay request log"""
        log_data = HttpRelayReqLogCreate(
            host="http://test.example.com",
            method="POST",
            path="/api/test",
            query="param=value",
            headers={"Content-Type": "application/json", "User-Agent": "test-client"},
            body={"test": "data", "key": "value"},
            author="test_user",
            clientip="192.168.1.100",
            status=200,
            output="Success response",
        )

        db_log = HttpRelayReqLog.model_validate(log_data)
        test_session.add(db_log)
        test_session.commit()
        test_session.refresh(db_log)

        assert db_log.id is not None
        assert db_log.host == "http://test.example.com"
        assert db_log.method == "POST"
        assert db_log.path == "/api/test"
        assert db_log.query == "param=value"
        assert db_log.headers["Content-Type"] == "application/json"
        assert db_log.body["test"] == "data"
        assert db_log.author == "test_user"
        assert db_log.clientip == "192.168.1.100"
        assert db_log.status == 200
        assert db_log.output == "Success response"
        assert db_log.created_at > 0
        assert db_log.updated_at > 0

    def test_http_relay_reqlog_timestamps(self, test_session: Session):
        """Test that timestamps are automatically set"""
        before_creation = int(time.time())

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

        after_creation = int(time.time())

        assert before_creation <= log.created_at <= after_creation
        assert before_creation <= log.updated_at <= after_creation
        assert log.created_at == log.updated_at

    def test_http_relay_reqlog_json_fields(self, test_session: Session):
        """Test JSON fields can handle complex data"""
        complex_headers = {
            "Content-Type": "application/json",
            "Authorization": "Bearer token123",
            "X-Custom-Header": "custom-value",
            "User-Agent": "Mozilla/5.0 (compatible; test-client)",
        }

        complex_body = {
            "user": {"id": 123, "name": "Test User"},
            "data": [1, 2, 3, {"nested": True}],
            "metadata": {"version": "1.0", "timestamp": "2024-01-01T00:00:00Z"},
        }

        log = HttpRelayReqLog(
            host="http://test.com",
            method="POST",
            path="/api/complex",
            query="complex=true",
            headers=complex_headers,
            body=complex_body,
            author="test_user",
            clientip="10.0.0.1",
            status=201,
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.headers == complex_headers
        assert log.body == complex_body
        assert log.body["user"]["name"] == "Test User"
        assert log.body["data"][3]["nested"] is True

    def test_http_relay_reqlog_update(self, test_session: Session):
        """Test updating HTTP Relay request log"""
        log = HttpRelayReqLog(
            host="http://original.com",
            method="GET",
            path="/original",
            query="",
            headers={},
            body={},
            author="original_user",
            clientip="127.0.0.1",
            status=200,
            output="Original output",
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        original_created_at = log.created_at

        # Sleep for a moment to ensure timestamp difference
        time.sleep(1)

        # Update the log
        update_data = HttpRelayReqLogUpdate(
            status=404, output="Updated output", author="updated_user"
        )

        log.status = update_data.status
        log.output = update_data.output
        log.author = update_data.author
        log.updated_at = int(time.time())

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        assert log.status == 404
        assert log.output == "Updated output"
        assert log.author == "updated_user"
        assert log.created_at == original_created_at
        assert log.updated_at > original_created_at

    def test_http_relay_reqlog_read_model(self, test_session: Session):
        """Test HttpRelayReqLogRead model"""
        log = HttpRelayReqLog(
            host="http://test.com",
            method="GET",
            path="/test",
            query="test=1",
            headers={"Accept": "application/json"},
            body={"request": "data"},
            author="test_user",
            clientip="192.168.1.1",
            status=200,
            output="Test response",
        )

        test_session.add(log)
        test_session.commit()
        test_session.refresh(log)

        read_log = HttpRelayReqLogRead.model_validate(log)

        assert read_log.id == log.id
        assert read_log.host == log.host
        assert read_log.method == log.method
        assert read_log.path == log.path
        assert read_log.query == log.query
        assert read_log.headers == log.headers
        assert read_log.body == log.body
        assert read_log.author == log.author
        assert read_log.clientip == log.clientip
        assert read_log.status == log.status
        assert read_log.output == log.output
        assert read_log.created_at == log.created_at
        assert read_log.updated_at == log.updated_at

    def test_pagination_models(self):
        """Test pagination models"""
        urls = PaginationUrls(
            current="http://test.com/logs?page=2",
            prev="http://test.com/logs?page=1",
            next="http://test.com/logs?page=3",
        )

        assert urls.current == "http://test.com/logs?page=2"
        assert urls.prev == "http://test.com/logs?page=1"
        assert urls.next == "http://test.com/logs?page=3"

        pagination = PaginationInfo(
            per_page=10, has_next=True, has_prev=True, urls=urls
        )

        assert pagination.per_page == 10
        assert pagination.has_next is True
        assert pagination.has_prev is True
        assert pagination.urls.current == urls.current

    def test_http_relay_reqlog_list_response(self, test_session: Session):
        """Test HttpRelayReqLogListResponse model"""
        logs = [
            HttpRelayReqLog(
                host="http://test1.com",
                method="GET",
                path="/test1",
                query="",
                headers={},
                body={},
                author="user1",
                clientip="127.0.0.1",
                status=200,
            ),
            HttpRelayReqLog(
                host="http://test2.com",
                method="POST",
                path="/test2",
                query="",
                headers={},
                body={},
                author="user2",
                clientip="127.0.0.1",
                status=201,
            ),
        ]

        for log in logs:
            test_session.add(log)
        test_session.commit()

        urls = PaginationUrls(current="http://test.com/logs?page=1")
        pagination = PaginationInfo(
            per_page=10, has_next=False, has_prev=False, urls=urls
        )

        response = HttpRelayReqLogListResponse(
            logs=logs, user="test_user", limit=10, pagination=pagination
        )

        assert len(response.logs) == 2
        assert response.user == "test_user"
        assert response.limit == 10
        assert response.pagination.per_page == 10

    def test_query_http_relay_reqlog(self, test_session: Session):
        """Test querying HTTP Relay request logs"""
        logs = [
            HttpRelayReqLog(
                host="http://server1.com",
                method="GET",
                path="/api/users",
                query="filter=active",
                headers={"Accept": "application/json"},
                body={},
                author="admin",
                clientip="10.0.0.1",
                status=200,
            ),
            HttpRelayReqLog(
                host="http://server2.com",
                method="POST",
                path="/api/users",
                query="",
                headers={"Content-Type": "application/json"},
                body={"name": "New User"},
                author="user1",
                clientip="10.0.0.2",
                status=201,
            ),
        ]

        for log in logs:
            test_session.add(log)
        test_session.commit()

        # Query by method
        get_logs = test_session.exec(
            select(HttpRelayReqLog).where(HttpRelayReqLog.method == "GET")
        ).all()
        assert len(get_logs) == 1
        assert get_logs[0].path == "/api/users"

        # Query by status
        success_logs = test_session.exec(
            select(HttpRelayReqLog).where(HttpRelayReqLog.status >= 200, HttpRelayReqLog.status < 300)
        ).all()
        assert len(success_logs) == 2

        # Query by author
        admin_logs = test_session.exec(
            select(HttpRelayReqLog).where(HttpRelayReqLog.author == "admin")
        ).all()
        assert len(admin_logs) == 1
        assert admin_logs[0].method == "GET"
