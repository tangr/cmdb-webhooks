# README

```text
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-API-Key: QNbl7W9Ez7hVkR44ja93" \
  "http://127.0.0.1:8000/cmdb/" \
  -d '{
    "host": "http://127.0.0.1:8000",
    "method": "POST",
    "path": "/api/test",
    "query": "param1=value1&param2=value2",
    "headers": {
      "Content-Type": "application/json",
      "User-Agent": "curl/7.68.0"
    },
    "body": {
      "test_key": "test_value",
      "data": "sample data"
    },
    "author": "test_user",
    "clientip": "127.0.0.1",
    "status": 200,
    "output": "Success response"
  }'


curl -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/feishu/webhook/alias/tang-mytest-bot" \
  -d '{
    "status": "firing",
    "title": "[🔥:1] test-High CPU usage - Multi-region1 Multi-region alerts (server-08 us-west db-server-2 critical)",
    "message": "<hr>🔥\n**Value**: A=93, C=1, reducer=93\n**Labels**:\n- *alertname* = test-High CPU usage - Multi-region1\n- *grafana_folder* = Multi-region alerts\n- *instance* = server-08\n- *region* = us-west\n- *service* = db-server-2\n- *severity* = critical\n\n**Links**:  [🔗](https://grafana-test.exodushk.com/alerting/grafana/beuz77ezwfncwb/view?orgId=1)  [🔕](https://grafana-test.exodushk.com/alerting/silence/new?alertmanager=grafana&matcher=__alert_rule_uid__%3Dbeuz77ezwfncwb&matcher=instance%3Dserver-08&matcher=region%3Dus-west&matcher=service%3Ddb-server-2&matcher=severity%3Dcritical&orgId=1)\n"
  }'


# GitLab System Hook -> Jenkins Generic Webhook Trigger
curl -X POST \
  -H "Content-Type: application/json" \
  -H "X-Gitlab-Token: your-secret-token" \
  -H "X-Gitlab-Event: Push Hook" \
  "http://127.0.0.1:8000/gitlab/webhook" \
  -d '{
    "object_kind": "push",
    "ref": "refs/heads/main",
    "checkout_sha": "abc123def456",
    "user_id": 1,
    "user_name": "Test User",
    "user_username": "testuser",
    "user_email": "test@example.com",
    "project": {
      "id": 100,
      "name": "my-project",
      "path_with_namespace": "mygroup/my-project",
      "web_url": "https://gitlab.example.com/mygroup/my-project"
    },
    "commits": [
      {
        "id": "abc123",
        "message": "First commit message",
        "author": {"name": "Test User", "email": "test@example.com"}
      },
      {
        "id": "def456",
        "message": "Second commit message",
        "author": {"name": "Test User", "email": "test@example.com"}
      }
    ],
    "total_commits_count": 2
  }'

```
