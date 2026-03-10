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
  "http://127.0.0.1:8000/feishu-bot/webhook/alias/tang-mytest-bot" \
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
  "event_name": "push",
  "before": "84ee80ae38d5813cc1c02a0d6436edc73971fabf",
  "after": "2325693d3c8c6f367b179f97d7d8e4ad821b54e1",
  "ref": "refs/heads/tangshoubinbranch",
  "checkout_sha": "2325693d3c8c6f367b179f97d7d8e4ad821b54e1",
  "message": null,
  "user_id": 20,
  "user_name": "ShouBin Tang",
  "user_username": "tangshoubin",
  "user_email": null,
  "user_avatar": null,
  "project_id": 74,
  "project": {
    "id": 74,
    "name": "contract",
    "description": null,
    "web_url": "https://git.yax.tech/exodus-server/contract",
    "avatar_url": null,
    "git_ssh_url": "git@git.yax.tech:exodus-server/contract.git",
    "git_http_url": "https://git.yax.tech/exodus-server/contract.git",
    "namespace": "exodus-server",
    "visibility_level": 0,
    "path_with_namespace": "exodus-server/contract",
    "default_branch": "master",
    "ci_config_path": null,
    "homepage": "https://git.yax.tech/exodus-server/contract",
    "url": "git@git.yax.tech:exodus-server/contract.git",
    "ssh_url": "git@git.yax.tech:exodus-server/contract.git",
    "http_url": "https://git.yax.tech/exodus-server/contract.git"
  },
  "commits": [
    {
      "id": "e05fc04a989adccfe27d373b980469a0b8841169",
      "message": "update a6\n",
      "title": "update a6",
      "timestamp": "2026-02-04T10:08:28+08:00",
      "url": "https://git.yax.tech/exodus-server/contract/-/commit/e05fc04a989adccfe27d373b980469a0b8841169",
      "author": {
        "name": "tangshoubin",
        "email": "[REDACTED]"
      },
      "added": [

      ],
      "modified": [
        "test1.txt"
      ],
      "removed": [

      ]
    },
    {
      "id": "2325693d3c8c6f367b179f97d7d8e4ad821b54e1",
      "message": "update a7\n",
      "title": "build:yes update a7",
      "timestamp": "2026-02-04T10:08:41+08:00",
      "url": "https://git.yax.tech/exodus-server/contract/-/commit/2325693d3c8c6f367b179f97d7d8e4ad821b54e1",
      "author": {
        "name": "tangshoubin",
        "email": "[REDACTED]"
      },
      "added": [

      ],
      "modified": [
        "test1.txt"
      ],
      "removed": [

      ]
    }
  ],
  "total_commits_count": 2,
  "push_options": {
  },
  "repository": {
    "name": "contract",
    "url": "git@git.yax.tech:exodus-server/contract.git",
    "description": null,
    "homepage": "https://git.yax.tech/exodus-server/contract",
    "git_http_url": "https://git.yax.tech/exodus-server/contract.git",
    "git_ssh_url": "git@git.yax.tech:exodus-server/contract.git",
    "visibility_level": 0
  }
}'

```
