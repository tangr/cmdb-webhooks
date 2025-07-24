```
curl -X POST \
  -H "Content-Type: application/json" \
  "http://127.0.0.1:8000/jms_reqlog/" \
  -d '{
    "host": "127.0.0.1:8000",
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
    "status": 200,
    "output": "Success response"
  }'

```
