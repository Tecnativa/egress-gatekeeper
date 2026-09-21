#!/bin/sh
set -eu

nft -f /etc/nftables.conf

# Local DNS forwarder used by the allowlist sync (sync-allowlist.py points
# at 127.0.0.1). Containers keep using Docker's embedded DNS (127.0.0.11),
# which is left untouched so service names on local networks keep resolving.
servers=""
for ns in ${UPSTREAM_NAMESERVERS:-1.1.1.1}; do
    servers="$servers --server=$ns"
done
# shellcheck disable=SC2086
dnsmasq \
    --no-hosts \
    --no-resolv \
    --listen-address=127.0.0.1 \
    --bind-interfaces \
    $servers

exec python3 /usr/local/bin/sync-allowlist.py
