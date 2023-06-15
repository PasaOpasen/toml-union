# syntax=docker/dockerfile:1


FROM python:3.8-slim as toml_union

ENV PYTHONUNBUFFERED=1
ENV LANG=C.UTF-8

RUN python -m pip install --upgrade pip && \    
    python -m pip cache purge && \
    rm -rf ~/.cache

RUN mkdir /toml_union

WORKDIR /toml_union

COPY ./requirements.txt /toml_union/

RUN python -m pip install -r requirements.txt && \
    python -m pip cache purge && \
    rm -rf ~/.cache

COPY ./toml_union.py /toml_union/

CMD [ "python", "toml_union.py", "-h" ]


