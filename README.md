
- register pill att https://app.rapt.io
- create API key

# env vars to configure
```
RAPT_USERNAME: your rapt registration email
RAPT_API_KEY: the generated API key

RAPT_LOOP_SLEEP_TIME: how often to scrape - generally depending on your settings, on how of data is updated

RAPT_PUSH_GATEWAY_URL: your prometheus push gateway
```

# TODO
options to make metrics export configurable:
- server
- .prom file
- push gateway (with custom url)
- victoriametrics use timestamp: &timestamp=1599894041764 (https://github.com/VictoriaMetrics/VictoriaMetrics/issues/750)
- 'lastActivityTime': '2024-11-06T22:50:39.1277864+00:00' -> datetime.fromisoformat('2024-11-06T22:50:39.1277864+00:00')