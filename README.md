[![Last image-template](https://img.shields.io/badge/last%20template%20update-v1.1-informational)](https://github.com/Tecnativa/image-template/tree/v1.1)
[![GitHub Container Registry](https://img.shields.io/badge/GitHub%20Container%20Registry-latest-%2324292e)](https://github.com/orgs/Tecnativa/packages/container/package/egress-gatekeeper)

# Docker Egress Gatekeeper

Outbound network gatekeeper + filtered DNS for Docker application stacks.

This project lets application containers reach only a defined set of external hosts
while preserving internal Docker service resolution.

It is intended for stacks where:

-   the main application should not have unrestricted outbound internet access
-   only specific external domains or IPs should be reachable
-   internal Docker service names must continue to resolve normally
-   you don't want to modify the base image to manually handle ip rules

---

## State of the art

We have developed multiple solutions to solve this same problems, each with its own
upsides and downsides. This tries to be an improvement on the
[docker whitelist gateway](https://github.com/Tecnativa/docker-whitelist-gateway) that
removes its biggest downside: Main container retains full internet access if any command
is run using docker compose run.

Previously we used a socat based proxy service in
[docker whitelist](https://github.com/Tecnativa/docker-whitelist) that required a
container for every host that we wanted to allow access to.

## Gatekeeper architecture

A sidecar container and the main container share a single network namespace. Then the
sidecar can use a [nftables](https://netfilter.org/projects/nftables/) `output` chain to
setup netowrk rules for itself and the main container.

-   Only hosts listed in `ALLOWED_HOSTS` (resolved to IPs, refreshed every
    `REFRESH_INTERVAL` seconds) are reachable outside the stack.
-   Local Docker networks, loopback, and private IP ranges are always reachable.
-   Internal Docker service names keep resolving via Docker's embedded DNS.
-   Blocked outbound connections fail fast with `ECONNREFUSED` (curl exit code 7).

### DNS behavior

DNS resolution and outbound permission are **separate concerns** on purpose:

-   Application containers keep using Docker's embedded DNS (`127.0.0.11`), which is
    left untouched, so internal service names resolve normally and any public name
    _resolves_ — the gatekeeper simply refuses the connection afterwards.
-   The gatekeeper itself runs dnsmasq on `127.0.0.1` exclusively for
    `sync-allowlist.py` (via `NAMESERVERS`), forwarding to `UPSTREAM_NAMESERVERS`. This
    keeps the allowlist IPs consistent and independent of Docker's resolver state.

## Required capability

The gatekeeper container needs:

```yaml
cap_add:
    - NET_ADMIN #
```

---

## Environment variables

| Variable               | Default           | Description                                                    |
| ---------------------- | ----------------- | -------------------------------------------------------------- |
| `ALLOWED_HOSTS`        | _(required)_      | Space-separated hostnames or IPs allowed for outbound traffic. |
| `REFRESH_INTERVAL`     | `60`              | Seconds between allowlist DNS refreshes.                       |
| `UPSTREAM_NAMESERVERS` | `1.1.1.1 8.8.8.8` | Upstream resolvers used by the local dnsmasq forwarder.        |
| `ENABLE_IPV4`          | `1`               | Resolve and allow A records.                                   |
| `ENABLE_IPV6`          | `0`               | Also resolve and allow AAAA records.                           |
| `LOG_LEVEL`            | `INFO`            | Log level for `sync-allowlist.py`.                             |

## Recommended Compose layout

Take a look at the compose project used in tests:
[tests/compose.yaml](tests/compose.yaml)

Minimal example:

```yaml
services:
    gateway:
        image: ghcr.io/tecnativa/whitelist-gateway:latest
        cap_add:
            - NET_ADMIN
        environment:
            ALLOWED_HOSTS: api.github.com 1.1.1.1
        networks:
            public:

    main:
        image: myapp
        network_mode: service:gateway
        depends_on:
            gateway:
                condition: service_healthy

networks:
    public:
```

## Example behavior

With:

```yaml
ALLOWED_HOSTS: "api.partner.invalid files.vendor.invalid"
```

Expected behavior:

-   `getent hosts api.partner.invalid` → may resolve
-   `curl https://api.partner.invalid` → allowed
-   `getent hosts random-site.example.invalid` → may resolve
-   `curl https://random-site.example.invalid` → blocked by gateway
-   `getent hosts main-db` → resolves locally
-   `getent hosts smtprelay` → resolves locally

This is expected: **DNS resolution and outbound permission are intentionally separate
concerns**.

---

## Notes

-   Wildcard domains are not supported; every hostname in `ALLOWED_HOSTS` is resolved
    individually. On each refresh cycle the sets are flushed and re-populated from fresh
    DNS answers.
-   Because filtering happens per-IP, hosts behind CDNs with frequently rotating
    addresses are handled by the periodic refresh, but there is an inherent race between
    the IP a client resolves and the IPs currently in the set.

## Development

All the dependencies you need to develop this project (apart from Docker itself) are
managed with [uv](https://docs.astral.sh/uv/).

To set up your development environment, run:

```bash
pip install uv  # If you don't have uv installed
uv sync  # Install the python dependencies and setup the development environment
```

### Testing

To run the tests locally, add `--prebuild` to autobuild the image before testing:

```sh
uv run pytest --prebuild
```

By default, the image that the tests use (and optionally prebuild) is named
`egress-gatekeeper:testonly`. If you prefer, you can build it separately before testing,
and remove the `--prebuild` flag, to run the tests with that image you built:

```sh
docker image build -t test:egress-gatekeeper .
uv run pytest
```

If you want to use a different image, pass the `--image` command line argument with the
name you want:

```sh
# To build it automatically
uv run pytest --prebuild --image my_custom_image

# To prebuild it separately
docker image build -t my_custom_image .
uv run pytest --image my_custom_image
```
