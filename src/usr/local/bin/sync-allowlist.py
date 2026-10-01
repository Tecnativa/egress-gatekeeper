#!/usr/bin/env python3
import ipaddress
import logging
import os
import subprocess
import time

from dns.resolver import (
    NXDOMAIN,
    LifetimeTimeout,
    NoAnswer,
    NoNameservers,
    Resolver,
)

logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(message)s",
)

logger = logging.getLogger("gateway")
INTERVAL = int(os.getenv("REFRESH_INTERVAL", "60"))
raw_hosts = [
    host
    for key, value in os.environ.items()
    if key.startswith("ALLOWED_HOSTS")
    for host in value.split()
]


def env_flag(key, default=False) -> bool:
    raw = os.getenv(key)
    return default if not raw else raw.lower() in {"true", "1", "yes", "on"}


def resolve_hosts(resolver, hosts, enable_ipv4, enable_ipv6):
    """Resolve `hosts` to address sets, logging and skipping the ones DNS cannot answer.

    Returns (ipv4, ipv6), but only `ipv4` is ever populated: AAAA answers land
    there too, so `ipv6` is always empty. A pre-existing defect, not fixed here.
    """
    ipv4, ipv6 = set(), set()
    for host in hosts:
        try:
            answer4 = resolver.resolve(host, "A") if enable_ipv4 else []
            answer6 = resolver.resolve(host, "AAAA") if enable_ipv6 else []
        except (NXDOMAIN, NoAnswer, LifetimeTimeout, NoNameservers) as e:
            logger.warning(f"Could not resolve {host}: {e}")
            continue
        for ip in answer4:
            ipv4.add(str(ip))
        for ip in answer6:
            ipv4.add(str(ip))  # Known pre-existing defect: AAAA into the IPv4 set
    return ipv4, ipv6


def main():
    logger.info(f"Allowing connection to {raw_hosts}")
    enable_ipv4 = env_flag("ENABLE_IPV4", True)
    enable_ipv6 = env_flag("ENABLE_IPV6", False)
    oneshot = env_flag("ONESHOT", False)

    resolver = Resolver()
    resolver.nameservers = ["127.0.0.11"]
    allowed_hosts = set()
    allowed_ipv4 = set()
    allowed_ipv6 = set()
    for host in raw_hosts:
        try:
            ip_addr = ipaddress.ip_address(host)
            if ip_addr.version == 4:
                allowed_ipv4.add(str(ip_addr))
            else:
                allowed_ipv6.add(str(ip_addr))
        except ValueError:
            allowed_hosts.add(host)

    while True:
        resolved4, resolved6 = resolve_hosts(
            resolver, allowed_hosts, enable_ipv4, enable_ipv6
        )
        ipv4 = set(allowed_ipv4) | resolved4
        ipv6 = set(allowed_ipv6) | resolved6
        subprocess.run(
            ["nft", "flush", "set", "inet", "gateway", "allowed4"],
            check=True,
        )

        for ip in sorted(ipv4):
            subprocess.run(
                ["nft", "add", "element", "inet", "gateway", "allowed4", "{", ip, "}"],
                check=True,
            )

        subprocess.run(
            ["nft", "flush", "set", "inet", "gateway", "allowed6"],
            check=True,
        )

        for ip in sorted(ipv6):
            subprocess.run(
                ["nft", "add", "element", "inet", "gateway", "allowed6", "{", ip, "}"],
                check=True,
            )
        if oneshot:
            raise SystemExit(0)
        time.sleep(INTERVAL)


if __name__ == "__main__":
    main()
