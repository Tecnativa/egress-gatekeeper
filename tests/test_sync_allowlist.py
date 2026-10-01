"""Unit tests for the allowlist resolution loop.

The integration tests already cover a name that does not exist, via the
`madeupdomain.invalid` entry in tests/conftest.py. These cover a name that
exists but cannot be answered right now.
"""

import importlib.util
from pathlib import Path

import pytest
from dns.resolver import LifetimeTimeout, NoNameservers, NXDOMAIN

SCRIPT = Path(__file__).parents[1] / "src/usr/local/bin/sync-allowlist.py"


def load_script():
    spec = importlib.util.spec_from_file_location("sync_allowlist", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


sync_allowlist = load_script()


class FakeResolver:
    """Returns canned answers, or raises a canned exception, per host."""

    def __init__(self, answers):
        self.answers = answers

    def resolve(self, host, rdtype):
        outcome = self.answers[host]
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def timeout(seconds=5.4):
    return LifetimeTimeout(timeout=seconds, errors=[])


@pytest.mark.parametrize(
    "failure",
    [timeout(), NoNameservers()],
    ids=["lifetime-timeout", "no-nameservers"],
)
def test_resolve_hosts_survives_a_transient_dns_failure(failure):
    """A DNS hiccup must not take the whole container down.

    LifetimeTimeout and NoNameservers are transient. The resolver raising them
    used to escape the loop, kill sync-allowlist.py, and with it the container.
    """
    resolver = FakeResolver({"fonts.googleapis.com": failure})

    ipv4, ipv6 = sync_allowlist.resolve_hosts(
        resolver, {"fonts.googleapis.com"}, enable_ipv4=True, enable_ipv6=False
    )

    assert ipv4 == set()
    assert ipv6 == set()


def test_resolve_hosts_keeps_resolving_after_a_transient_failure():
    """One flaky host must not cost the allowlist the other hosts."""
    resolver = FakeResolver(
        {
            "flaky.example.com": timeout(),
            "cdnjs.cloudflare.com": ["104.17.24.14"],
        }
    )

    ipv4, _ = sync_allowlist.resolve_hosts(
        resolver,
        {"flaky.example.com", "cdnjs.cloudflare.com"},
        enable_ipv4=True,
        enable_ipv6=False,
    )

    assert ipv4 == {"104.17.24.14"}


def test_resolve_hosts_still_skips_a_name_that_does_not_exist():
    """The pre-existing NXDOMAIN behaviour must be unchanged."""
    resolver = FakeResolver({"madeupdomain.invalid": NXDOMAIN()})

    ipv4, ipv6 = sync_allowlist.resolve_hosts(
        resolver, {"madeupdomain.invalid"}, enable_ipv4=True, enable_ipv6=False
    )

    assert ipv4 == set()
    assert ipv6 == set()
