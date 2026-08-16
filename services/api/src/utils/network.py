from dataclasses import dataclass
import ipaddress
import socket
from urllib.parse import urlparse
from fastapi import HTTPException, status

# Explicit list of restricted networks (RFC 1918, RFC 3927, RFC 6598, etc.)
RESTRICTED_NETWORKS = [
    # IPv4 Private / Loopback / Link-Local / Reserved
    ipaddress.ip_network("0.0.0.0/8"),          # Current / Unspecified network
    ipaddress.ip_network("10.0.0.0/8"),         # RFC 1918 Private class A
    ipaddress.ip_network("100.64.0.0/10"),      # Carrier-Grade NAT (RFC 6598)
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("169.254.0.0/16"),     # Link-Local / Cloud Metadata (169.254.169.254)
    ipaddress.ip_network("172.16.0.0/12"),      # RFC 1918 Private class B
    ipaddress.ip_network("192.168.0.0/16"),     # RFC 1918 Private class C
    ipaddress.ip_network("224.0.0.0/4"),        # Multicast
    ipaddress.ip_network("240.0.0.0/4"),        # Reserved
    ipaddress.ip_network("255.255.255.255/32"), # Broadcast

    # IPv6 Loopback / Private / Link-Local / Multicast
    ipaddress.ip_network("::1/128"),            # Loopback
    ipaddress.ip_network("::/128"),             # Unspecified
    ipaddress.ip_network("fc00::/7"),           # Unique Local Address (ULA)
    ipaddress.ip_network("fe80::/10"),          # Link-Local Unicast
    ipaddress.ip_network("ff00::/8"),           # Multicast
]


@dataclass
class ValidatedTarget:
    original_url: str
    scheme: str
    hostname: str
    port: int
    resolved_ip: str
    pinned_url: str
    host_header: str


def is_ip_blocked(ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """
    Evaluates whether an IP address belongs to any restricted or private CIDR block.
    """
    # Check built-in properties
    if (
        ip_obj.is_loopback
        or ip_obj.is_link_local
        or ip_obj.is_multicast
        or ip_obj.is_unspecified
    ):
        return True

    # Handle IPv4-mapped IPv6 addresses (e.g., ::ffff:127.0.0.1)
    if isinstance(ip_obj, ipaddress.IPv6Address) and ip_obj.ipv4_mapped:
        return is_ip_blocked(ip_obj.ipv4_mapped)

    # Check against explicit restricted CIDRs (RFC 1918, CGNAT, Metadata, etc.)
    for net in RESTRICTED_NETWORKS:
        if isinstance(ip_obj, ipaddress.IPv4Address) and isinstance(net, ipaddress.IPv4Network):
            if ip_obj in net:
                return True
        elif isinstance(ip_obj, ipaddress.IPv6Address) and isinstance(net, ipaddress.IPv6Network):
            if ip_obj in net:
                return True

    return False


def resolve_and_validate_target(url: str) -> ValidatedTarget:
    """
    Parses and validates a URL, resolves all target IPs, ensures NONE are in restricted CIDRs,
    and returns a ValidatedTarget with an IP-pinned URL and Host header to prevent DNS rebinding (TOCTOU).
    """
    if not url or not isinstance(url, str):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL: URL parameter cannot be empty",
        )

    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()

    if scheme not in ("http", "https"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid URL scheme '{scheme}': Only 'http' and 'https' protocols are permitted",
        )

    hostname = parsed.hostname
    if not hostname:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid URL: Missing target hostname",
        )

    port = parsed.port or (443 if scheme == "https" else 80)
    host_header = hostname if (parsed.port is None or (scheme == "http" and port == 80) or (scheme == "https" and port == 443)) else f"{hostname}:{port}"

    # Direct IP address check
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(ip):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"SSRF validation blocked: Direct request to restricted IP address '{ip}' is not permitted",
            )
        return ValidatedTarget(
            original_url=url,
            scheme=scheme,
            hostname=hostname,
            port=port,
            resolved_ip=str(ip),
            pinned_url=url,
            host_header=host_header,
        )
    except ValueError:
        # Hostname is a domain name -> Perform DNS resolution
        pass

    try:
        # Resolve all IPv4 and IPv6 addresses for hostname
        addr_info = socket.getaddrinfo(
            hostname,
            port,
            socket.AF_UNSPEC,
            socket.SOCK_STREAM,
            socket.IPPROTO_TCP,
        )
        if not addr_info:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"DNS resolution failure: Hostname '{hostname}' could not be resolved",
            )

        resolved_ips: list[str] = []
        for entry in addr_info:
            sockaddr = entry[4]
            resolved_ip_str = sockaddr[0]
            try:
                ip_obj = ipaddress.ip_address(resolved_ip_str)
                if is_ip_blocked(ip_obj):
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"SSRF validation blocked: Hostname '{hostname}' resolved to restricted IP '{resolved_ip_str}'",
                    )
                resolved_ips.append(resolved_ip_str)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid resolved IP address: '{resolved_ip_str}'",
                )

        # Build IP-pinned URL to eliminate DNS rebinding TOCTOU window
        chosen_ip = resolved_ips[0]
        ip_formatted = f"[{chosen_ip}]" if ":" in chosen_ip else chosen_ip
        
        # Replace netloc with pinned IP and port
        netloc = f"{ip_formatted}:{port}" if parsed.port else ip_formatted
        pinned_url = parsed._replace(netloc=netloc).geturl()

        return ValidatedTarget(
            original_url=url,
            scheme=scheme,
            hostname=hostname,
            port=port,
            resolved_ip=chosen_ip,
            pinned_url=pinned_url,
            host_header=host_header,
        )
    except socket.gaierror as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"DNS resolution error for hostname '{hostname}': {str(e)}",
        )


def validate_safe_url(url: str) -> str:
    """
    Validates that a URL is well-formed, uses HTTP/HTTPS schemes, and resolves
    strictly to non-restricted, public Internet IP addresses (mitigating SSRF).
    Raises HTTPException(400) if validation fails.
    """
    target = resolve_and_validate_target(url)
    return target.original_url
