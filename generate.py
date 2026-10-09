#!/usr/bin/env python3
import os
import sys
import glob
import json
import socket
import subprocess
import re

CONFIGS_DIR = "./configs"
COMPOSE_FILE = "docker-compose.yml"
MAP_FILE = "locations.txt"
OUTBOUNDS_FILE = "xray_outbounds.json"

EXCLUDED_COUNTRIES = {"ru"}

FIXED_PORTS = {
    "ae": 1081,
    "uae": 1081,
    "jp": 1082,
    "kr": 1083,
    "us": 1084,
    "de": 1085,
    "gb": 1086,
    "uk": 1086,
    "ca": 1087,
    "ro": 1088,
    "tr": 1089,
    "fi": 1090,
    "fr": 1091,
    "nl": 1092,
    "sg": 1093,
    "se": 1094,
}

COUNTRY_NAMES = {
    "ae": "UAE",
    "uae": "UAE",
    "jp": "Japan",
    "kr": "Korea",
    "us": "USA",
    "de": "Germany",
    "gb": "UK",
    "uk": "UK",
    "ca": "Canada",
    "ro": "Romania",
    "tr": "Turkey",
    "fi": "Finland",
    "fr": "France",
    "nl": "Netherlands",
    "sg": "Singapore",
    "se": "Sweden",
    "ch": "Switzerland",
    "it": "Italy",
    "es": "Spain",
    "pl": "Poland",
    "in": "India",
    "au": "Australia",
}

def get_flag(code):
    c = code.lower()
    if c == "uae":
        c = "ae"
    elif c == "uk":
        c = "gb"
    if len(c) == 2 and c.isalpha():
        return "".join(chr(127397 + ord(char.upper())) for char in c)
    return "🌐"

def get_docker_port_owners():
    """Returns {port: container_name} for currently running docker containers."""
    owners = {}
    try:
        out = subprocess.check_output(
            ["docker", "ps", "--format", "{{.Names}}\t{{.Ports}}"],
            stderr=subprocess.DEVNULL, text=True
        )
        for line in out.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 2:
                cname = parts[0].strip()
                for match in re.findall(r":(\d+)->", parts[1]):
                    owners[int(match)] = cname
    except Exception:
        pass
    return owners

def is_port_in_use_by_external(port, my_container_name, docker_owners):
    """Checks whether the port is listening and occupied by an external service."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.2)
        in_use = (s.connect_ex(("127.0.0.1", port)) == 0)
    
    if not in_use:
        return False
    
    owner = docker_owners.get(port)
    if owner == my_container_name:
        return False
    
    return True

def find_available_port(target_port, used_ports, my_container_name, docker_owners, loc_name):
    """Finds target_port or the next free available port if occupied."""
    port = target_port
    while True:
        if port not in used_ports and not is_port_in_use_by_external(port, my_container_name, docker_owners):
            if port != target_port:
                print(f"[!] Warning: Port {target_port} is busy by an external service. Shifted {loc_name} to port {port}.")
            return port
        port += 1

def main():
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    raw_files = sorted(glob.glob(os.path.join(CONFIGS_DIR, "*.ovpn")))
    ovpn_files = [f for f in raw_files if os.path.isfile(f) and os.path.splitext(os.path.basename(f))[0].lower() not in EXCLUDED_COUNTRIES]

    if not ovpn_files:
        print(f"[-] No .ovpn files found in {CONFIGS_DIR}!")
        sys.exit(1)

    docker_owners = get_docker_port_owners()
    assigned = []
    used_ports = set()

    remaining_files = []
    for f in ovpn_files:
        base = os.path.splitext(os.path.basename(f))[0].lower()
        service_name = f"vpn-{base}"
        if base in FIXED_PORTS:
            target_port = FIXED_PORTS[base]
            final_port = find_available_port(target_port, used_ports, service_name, docker_owners, base)
            used_ports.add(final_port)
            assigned.append((base, f, final_port))
        else:
            remaining_files.append((base, f))

    dyn_port = 1095
    for base, f in remaining_files:
        service_name = f"vpn-{base}"
        final_port = find_available_port(dyn_port, used_ports, service_name, docker_owners, base)
        used_ports.add(final_port)
        assigned.append((base, f, final_port))
        dyn_port = final_port + 1

    assigned.sort(key=lambda x: x[2])

    global_auth = None
    if os.path.exists("./auth.txt"):
        global_auth = "./auth.txt"
    elif os.path.exists(os.path.join(CONFIGS_DIR, "auth.txt")):
        global_auth = os.path.join(CONFIGS_DIR, "auth.txt")

    compose_content = "services:\n"
    xray_outbounds = []
    locations_lines = []

    print("\n==================================================================")
    print(f"  {'PORT':<6} | {'LOCATION':<10} | {'XRAY OUTBOUND TAG':<25} | {'CONTAINER':<15}")
    print("==================================================================")

    for loc, fpath, port in assigned:
        c_code = "ae" if loc == "uae" else loc
        flag = get_flag(c_code)
        c_name = COUNTRY_NAMES.get(loc, loc.upper())
        tag_name = f"{flag} {c_name}-ovpn"
        service_name = f"vpn-{loc}"

        # Check for dedicated <loc>.auth or fallback to global_auth
        spec_auth = os.path.join(CONFIGS_DIR, f"{loc}.auth")
        container_auth_mount = ""
        if os.path.exists(spec_auth):
            container_auth_mount = f"      - {spec_auth}:/etc/openvpn/auth.txt:ro\n"
        elif global_auth:
            container_auth_mount = f"      - {global_auth}:/etc/openvpn/auth.txt:ro\n"

        compose_content += f"""  {service_name}:
    build: .
    container_name: {service_name}
    cap_add:
      - NET_ADMIN
    devices:
      - /dev/net/tun:/dev/net/tun
    ports:
      - "{port}:1080"
    volumes:
      - {fpath}:/etc/openvpn/config.ovpn:ro
{container_auth_mount}    restart: unless-stopped

"""

        xray_outbounds.append({
            "tag": tag_name,
            "protocol": "socks",
            "settings": {
                "servers": [
                    {
                        "address": "127.0.0.1",
                        "port": port,
                        "users": []
                    }
                ]
            }
        })

        print(f"  {port:<6} | {loc:<10} | {tag_name:<25} | {service_name:<15}")
        locations_lines.append(f"{port:<8} | {loc:<10} | {tag_name:<25} | {service_name}")

    print("==================================================================")

    with open(COMPOSE_FILE, "w", encoding="utf-8") as f:
        f.write(compose_content)

    with open(OUTBOUNDS_FILE, "w", encoding="utf-8") as f:
        json.dump(xray_outbounds, f, ensure_ascii=False, indent=2)

    with open(MAP_FILE, "w", encoding="utf-8") as f:
        f.write("Active SOCKS5 Ports & Xray Outbound Tags:\n")
        f.write("------------------------------------------------------------------\n")
        f.write("\n".join(locations_lines) + "\n")

    print(f"[+] Successfully generated '{COMPOSE_FILE}'.")
    print(f"[+] Exported Xray outbounds to '{OUTBOUNDS_FILE}'.")

if __name__ == "__main__":
    main()
