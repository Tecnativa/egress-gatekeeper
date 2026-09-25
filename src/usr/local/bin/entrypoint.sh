#!/bin/sh
set -eu
nft -f /etc/nftables.conf
sync-allowlist.py
