#!/usr/bin/env python3
"""Healthcheck for the nftables-based whitelist gateway (gatekeeper).

Verifies:
1. The sync-allowlist loop process is running.
2. The inet/gateway nftables table with the output chain exists.
3. The allowed4 set is populated (allowlist synced at least once).
"""

import logging
import os
import subprocess

logger = logging.getLogger("healthcheck")


def error(message, exception=None):
    logger.error(message)
    if exception is None:
        raise SystemExit(1)
    raise exception


def _run(cmd, check=True):
    return subprocess.run(
        cmd,
        check=check,
        capture_output=True,
        text=True,
    )


def process_healthcheck():
    """The sync-allowlist loop must be running."""
    try:
        out = _run(["ps", "-o", "args="], check=True).stdout
    except Exception as e:
        error("failed to list processes", e)
    if "sync-allowlist.py" not in out:
        error("sync-allowlist.py process is not running")


def nftables_healthcheck():
    """The gateway table, output chain and a populated allowed4 set must exist."""
    try:
        out = _run(["nft", "list", "table", "inet", "gateway"], check=True).stdout
    except Exception as e:
        error("missing nftables table inet gateway", e)

    if "chain output" not in out:
        error("missing output chain in table inet gateway")

    if "ip daddr @allowed4 accept" not in out:
        error("missing allowed4 accept rule in output chain")

    try:
        out = _run(
            ["nft", "list", "set", "inet", "gateway", "allowed4"], check=True
        ).stdout
    except Exception as e:
        error("missing nftables set allowed4", e)

    if "elements" not in out:
        error("allowed4 set is empty (allowlist not synced yet?)")


def main():
    logging.basicConfig(level=logging.INFO)

    if not os.environ.get("ALLOWED_HOSTS", "").strip():
        error("ALLOWED_HOSTS is empty; nothing to healthcheck")

    process_healthcheck()
    nftables_healthcheck()
    print("OK")


if __name__ == "__main__":
    main()
