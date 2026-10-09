#!/usr/bin/env python3
import os
import sys
import glob
import json

CONFIGS_DIR = "./configs"
COMPOSE_FILE = "docker-compose.yml"
MAP_FILE = "locations.txt"
OUTBOUNDS_FILE = "xray_outbounds.json"

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

def main():
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    ovpn_files = sorted(glob.glob(os.path.join(CONFIGS_DIR, "*.ovpn")))

    if not ovpn_files:
        print(f"[-] No .ovpn files found in {CONFIGS_DIR}!")
        sys.exit(1)

    assigned = []
    used_ports = set()

    remaining_files = []
    for f in ovpn_files:
        base = os.path.splitext(os.path.basename(f))[0].lower()
        if base in FIXED_PORTS:
            port = FIXED_PORTS[base]
            used_ports.add(port)
            assigned.append((base, f, port))
        else:
            remaining_files.append((base, f))

    dyn_port = 1095
    for base, f in remaining_files:
        while dyn_port in used_ports:
            dyn_port += 1
        used_ports.add(dyn_port)
        assigned.append((base, f, dyn_port))
        dyn_port += 1

    assigned.sort(key=lambda x: x[2])

    auth_mount = ""
    if os.path.exists("./auth.txt"):
        auth_mount = "      - ./auth.txt:/etc/openvpn/auth.txt:ro\n"
    elif os.path.exists(os.path.join(CONFIGS_DIR, "auth.txt")):
        auth_mount = f"      - {CONFIGS_DIR}/auth.txt:/etc/openvpn/auth.txt:ro\n"

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
{auth_mount}    restart: unless-stopped

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
