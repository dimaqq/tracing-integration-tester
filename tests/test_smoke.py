
"""root@hexanator-0:/# curl http://localhost:80/v1/rate-limit.check --header 'Content-Type: application/json'   --data '{
    "requests": [
        {
            "name": "requests_per_sec",
            "unique_key": "account:12345",
            "hits": "1",
            "limit": "10",
            "duration": "1000"
        }
    ]
}'
{"responses":[{"limit":"10", "remaining":"9", "reset_time":"1720592294506"}]}
"""
