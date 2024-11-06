
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
