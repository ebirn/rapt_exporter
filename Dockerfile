FROM docker.io/library/python:3.13-slim

RUN pip install uv

WORKDIR /usr/src/app
COPY . /usr/src/app

RUN uv sync

ENV BLA=bla

ENTRYPOINT ["uv", "run", "rapt_exporter.py"]