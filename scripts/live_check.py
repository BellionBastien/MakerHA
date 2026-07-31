#!/usr/bin/env python3
"""Standalone sanity check, no Home Assistant required.

Listens a few seconds for Carvera UDP announcements, then fetches
/status from every machine found (or from a host passed as argument).

    python3 scripts/live_check.py [host[:port]]
"""

import json
import socket
import sys
import urllib.request

BEACON_PORT = 3333
HTTP_PORT = 8080
LISTEN_S = 4.0


def listen_for_beacons() -> dict[str, str]:
    machines: dict[str, str] = {}
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind(("0.0.0.0", BEACON_PORT))
    sock.settimeout(LISTEN_S)
    try:
        while True:
            data, _ = sock.recvfrom(1024)
            parts = data.decode(errors="replace").strip().split(",")
            if len(parts) == 4:
                machines[parts[0]] = parts[1]
    except socket.timeout:
        pass
    finally:
        sock.close()
    return machines


def fetch_status(host: str, port: int = HTTP_PORT) -> None:
    url = f"http://{host}:{port}/status"
    with urllib.request.urlopen(url, timeout=4) as resp:
        doc = json.load(resp)
    print(f"  {url} -> {doc['name']} [{doc['model']}] state={doc['state']}")
    print(f"    {json.dumps(doc, indent=2)[:400]}...")


def main() -> None:
    if len(sys.argv) > 1:
        host, _, port = sys.argv[1].partition(":")
        fetch_status(host, int(port) if port else HTTP_PORT)
        return
    print(f"listening {LISTEN_S:.0f}s for machine announcements on UDP {BEACON_PORT}...")
    machines = listen_for_beacons()
    if not machines:
        print("no machine announced itself (powered off, or UDP 3333 not reachable)")
        return
    for name, ip in machines.items():
        print(f"found {name} at {ip}")
        try:
            fetch_status(ip)
        except OSError as err:
            print(f"  status API unreachable ({err}) - is wifi.http_enable true?")


if __name__ == "__main__":
    main()
