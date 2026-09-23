from __future__ import annotations

import ipaddress
import socket

import psutil


def lan_ipv4_addresses() -> list[str]:
    addresses: list[str] = []
    try:
        for _, entries in psutil.net_if_addrs().items():
            for entry in entries:
                if entry.family != socket.AF_INET:
                    continue
                ip = entry.address
                try:
                    obj = ipaddress.ip_address(ip)
                except ValueError:
                    continue
                if obj.is_loopback or obj.is_link_local or not obj.is_private:
                    continue
                addresses.append(ip)
    except Exception:
        pass
    return sorted(set(addresses))
