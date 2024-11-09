FROM docker.io/library/python:3.13-slim

RUN pip install uv

WORKDIR /usr/src/app
COPY . /usr/src/app

RUN uv sync

ENV RAPT_USERNAME=username-missing
ENV RAPT_API_KEY=api-key-missing
ENV RAPT_PUSH_GATEWAY_URL=url-pushserver-missing
ENV RAPT_LOOP_SLEEP_TIME=300

ENTRYPOINT ["uv", "run", "rapt_exporter.py"]