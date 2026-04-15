"""URL safety helpers — shared between webhook registration and delivery.

The same ``is_public_url`` check runs in two places:

1. ``app/api/v1/webhooks.py::WebhookCreate.url_must_be_public`` — at
   registration time, so an attacker can't even record a malicious URL.
2. ``app/services/webhook_dispatch.py::_deliver`` — at delivery time,
   re-runs the check because DNS can flip between registration and
   delivery (intentional DNS rebinding OR domain takeover).

Keeping both call sites on the same helper means one definition of
"public URL" across the codebase. Pure-function module with no
framework dependencies so it can be imported from anywhere without
risking a circular import.
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


# IP ranges that must be blocked for webhook URLs (SSRF prevention).
# These cover every RFC1918 private block, loopback (v4 and v6), link-local,
# and the cloud metadata ranges that AWS/GCP/Azure expose on 169.254.169.254.
_BLOCKED_NETWORKS: list[ipaddress._BaseNetwork] = [
    ipaddress.ip_network("0.0.0.0/8"),          # "this network" / unspecified
    ipaddress.ip_network("10.0.0.0/8"),         # Private
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-grade NAT
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-local / cloud metadata
    ipaddress.ip_network("172.16.0.0/12"),      # Private
    ipaddress.ip_network("192.0.0.0/24"),       # IETF protocol assignments
    ipaddress.ip_network("192.168.0.0/16"),     # Private
    ipaddress.ip_network("198.18.0.0/15"),      # Benchmarking
    ipaddress.ip_network("::1/128"),            # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),           # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),          # IPv6 link-local
    ipaddress.ip_network("::ffff:0:0/96"),      # IPv4-mapped IPv6 (SSRF vector)
]

# Hostnames that should never be allowed regardless of how they resolve —
# the cloud-metadata hosts in particular can serve credentials on 169.254.169.254.
_BLOCKED_HOSTNAMES: frozenset[str] = frozenset({
    "localhost",
    "0.0.0.0",
    "metadata",
    "metadata.google.internal",
    "metadata.internal",
    "instance-data",
    "instance-data.ec2.internal",
})


def _ip_is_blocked(addr: ipaddress._BaseAddress) -> bool:
    return any(addr in net for net in _BLOCKED_NETWORKS)


def _resolve_hostname(hostname: str) -> list[ipaddress._BaseAddress]:
    """Return every A/AAAA record for ``hostname``, empty on failure.

    Uses a blocking ``getaddrinfo``. That's acceptable for both call sites:
    webhook registration is a low-volume admin path, and webhook delivery
    already runs inside a background task where the resolution latency
    doesn't affect the user request.
    """
    try:
        infos = socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
    except socket.gaierror:
        return []
    out: list[ipaddress._BaseAddress] = []
    for info in infos:
        sockaddr = info[4]
        if not sockaddr:
            continue
        ip_str = sockaddr[0]
        try:
            out.append(ipaddress.ip_address(ip_str))
        except ValueError:
            continue
    return out


def is_public_url(url: str) -> bool:
    """Reject URLs that would let a user probe internal infrastructure.

    Strategy:
      1. Reject obvious internal hostnames (localhost, metadata endpoints).
      2. If the host is a literal IP, reject anything in ``_BLOCKED_NETWORKS``.
      3. Otherwise resolve the hostname NOW and reject if *any* resolved IP
         is blocked. A hostname that currently resolves publicly but later
         flips to an internal IP (DNS rebinding) is defended against at
         delivery time by re-calling this function — see
         ``app/services/webhook_dispatch.py::_deliver``.

    Returns True when the URL is safe to dispatch to.
    """
    parsed = urlparse(str(url))
    hostname = parsed.hostname
    if not hostname:
        return False
    if hostname.lower() in _BLOCKED_HOSTNAMES:
        return False

    # Literal IP — check directly.
    try:
        addr = ipaddress.ip_address(hostname)
        return not _ip_is_blocked(addr)
    except ValueError:
        pass

    # Hostname — resolve and reject if any record is blocked. A hostname
    # that fails DNS entirely is also rejected: we'd rather force the user
    # to register a real URL than silently accept a dead endpoint.
    resolved = _resolve_hostname(hostname)
    if not resolved:
        return False
    return all(not _ip_is_blocked(ip) for ip in resolved)
