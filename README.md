```
curl -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/jms_reqlog/" \
  -d '{
    "jmshost": "127.0.0.1:8000",
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

```
