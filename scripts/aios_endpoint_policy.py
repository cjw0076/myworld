#!/usr/bin/env python3
"""Endpoint allowlist policy for AIOS outbound requests.

Third security-enforcement primitive absorbed from ironclaw (peer Agent OS:
endpoint allowlisting — outbound HTTP only to explicitly approved hosts). AIOS
makes outbound calls (GitHub API, raw.githubusercontent, local ollama); this
restricts them to an allowlist at the network boundary, so a poisoned config or
injected URL cannot exfiltrate to an arbitrary host.

Schema: aios.endpoint_policy.v1
Usage (library):
    from aios_endpoint_policy import is_allowed, guarded_urlopen
    with guarded_urlopen(url) as resp: ...
"""
from __future__ import annotations

import urllib.request
from urllib.parse import urlparse

SCHEMA_VERSION = "aios.endpoint_policy.v1"

# hosts AIOS legitimately reaches. Subdomains of these are allowed too.
DEFAULT_ALLOWLIST: frozenset[str] = frozenset({
    "api.github.com",
    "github.com",
    "raw.githubusercontent.com",
    "objects.githubusercontent.com",
    "127.0.0.1",
    "localhost",
    "::1",
})


def host_of(url: str) -> str:
    netloc = urlparse(str(url)).netloc or urlparse("//" + str(url)).netloc
    host = netloc.rsplit("@", 1)[-1]  # strip userinfo
    if host.startswith("["):  # ipv6 [::1]:port
        return host[1 : host.index("]")] if "]" in host else host
    return host.rsplit(":", 1)[0] if ":" in host else host


def is_allowed(url: str, allow: frozenset[str] | None = None) -> bool:
    allow = allow or DEFAULT_ALLOWLIST
    host = host_of(url).lower()
    if not host:
        return False
    return host in allow or any(host == a or host.endswith("." + a) for a in allow)


class EndpointDenied(RuntimeError):
    pass


def guarded_urlopen(url: str, *, allow: frozenset[str] | None = None, **kwargs):
    """urllib.request.urlopen that refuses non-allowlisted hosts."""
    target = url.full_url if isinstance(url, urllib.request.Request) else url
    if not is_allowed(target, allow):
        raise EndpointDenied(f"outbound to non-allowlisted host: {host_of(target)!r}")
    return urllib.request.urlopen(url, **kwargs)
