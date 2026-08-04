FROM ghcr.io/astral-sh/uv:python3.12-alpine AS base

RUN apk add --no-cache \
        curl \
        dumb-init \
        dnsmasq \
        iproute2 \
        ipset \
        iptables \
        libcurl \
        nftables

FROM base AS builder
WORKDIR /opt
RUN apk add --no-cache \
        build-base \
        curl-dev

COPY pyproject.toml uv.lock ./
ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-python-downloads --no-dev


FROM base AS target

ENV NAMESERVERS="127.0.0.1" \
    UPSTREAM_NAMESERVERS="1.1.1.1 8.8.8.8" \
    PORT="*" \
    LISTEN_PORT="15000" \
    RESOLVE_INTERVAL="60" \
    PRE_RESOLVE="0" \
    MODE="tcp" \
    VERBOSE="0" \
    MAX_CONNECTIONS="100" \
    UDP_ANSWERS="1" \
    HTTP_HEALTHCHECK="0" \
    HTTP_HEALTHCHECK_URL="http://\$TARGET/" \
    SMTP_HEALTHCHECK="0" \
    SMTP_HEALTHCHECK_URL="smtp://\$TARGET/" \
    SMTP_HEALTHCHECK_COMMAND="HELP" \
    DNS_UPSTREAMS="1.1.1.1 8.8.8.8" \
    PATH="/opt/venv/bin:$PATH" \
    ENABLE_IPV4="1" \
    ENABLE_IPV6="0"

COPY --from=builder /opt/venv /opt/venv
COPY src/ /

RUN chmod +x /usr/local/bin/ -R

ENTRYPOINT ["dumb-init", "--", "/usr/local/bin/entrypoint.sh"]
HEALTHCHECK \
  --start-period=15s \
  --start-interval=1s \
  --interval=30s \
  --timeout=5s \
  --retries=3 \
  CMD ["healthcheck.py"]
