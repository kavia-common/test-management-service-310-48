import ipaddress
import hashlib
from typing import Optional


# PUBLIC_INTERFACE
def deterministic_ip(subnet_cidr: str, subscriber_id: str) -> str:
    """Deterministically compute an IPv4 address in subnet for a given subscriber_id.

    Strategy:
    - Hash subscriber_id to an integer.
    - Map to host index within subnet (skip network and broadcast).
    - Return resulting IP.
    """
    net = ipaddress.ip_network(subnet_cidr, strict=False)
    total_hosts = net.num_addresses - 2 if net.version == 4 else net.num_addresses
    if total_hosts <= 0:
        raise ValueError(f"Invalid subnet or no hosts available: {subnet_cidr}")
    h = hashlib.sha256(subscriber_id.encode("utf-8")).digest()
    host_index = int.from_bytes(h[:4], "big") % total_hosts
    host_index = max(1, min(host_index, total_hosts))  # ensure not 0
    return str(net.network_address + host_index)


# PUBLIC_INTERFACE
def allocate_ip(subnet_cidr: str, subscriber_id: str, requested_ip: Optional[str] = None) -> str:
    """Allocate IP deterministically unless requested_ip is provided."""
    if requested_ip:
        return requested_ip
    return deterministic_ip(subnet_cidr, subscriber_id)
