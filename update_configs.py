#!/usr/bin/env python3
import sys
import os
import csv
import base64
import urllib.request
import argparse

VPNGATE_API_URL = "https://www.vpngate.net/api/iphone/"
CONFIGS_DIR = "./configs"

def fetch_and_save_configs(limit=10, selected_countries=None):
    os.makedirs(CONFIGS_DIR, exist_ok=True)
    print(f"[+] Requesting server list from VPNGate API ({VPNGATE_API_URL})...")
    
    req = urllib.request.Request(
        VPNGATE_API_URL,
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            content = response.read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[-] API request failed: {e}")
        return False

    lines = content.splitlines()
    data_lines = [l for l in lines if not l.startswith("*") and not l.startswith("#") and l.strip()]
    
    if not data_lines:
        print("[-] No data returned from VPNGate API!")
        return False

    reader = csv.reader(data_lines)
    servers_by_country = {}

    for row in reader:
        # Col 1: IP, Col 2: Score, Col 4: Speed, Col 5: CountryLong, Col 6: CountryShort, Col 14: Base64
        if len(row) < 15:
            continue
        
        country_code = row[6].strip().lower()
        country_name = row[5].strip()
        ip = row[1].strip()
        
        try:
            score = int(row[2])
            speed = int(row[4])
        except ValueError:
            score = 0
            speed = 0
            
        ovpn_b64 = row[14].strip()
        if not ovpn_b64:
            continue

        if selected_countries and country_code not in selected_countries:
            continue

        # Keep the best server per country (by score/speed)
        if country_code not in servers_by_country or score > servers_by_country[country_code]["score"]:
            servers_by_country[country_code] = {
                "code": country_code,
                "name": country_name,
                "ip": ip,
                "score": score,
                "speed_mbps": round(speed / (1024 * 1024), 1),
                "ovpn_b64": ovpn_b64
            }

    if not servers_by_country:
        print("[-] No servers matched the specified criteria.")
        return False

    # Sort countries by highest score
    sorted_countries = sorted(servers_by_country.values(), key=lambda x: x["score"], reverse=True)
    if limit and limit > 0:
        sorted_countries = sorted_countries[:limit]

    print(f"[+] Selected top {len(sorted_countries)} servers:\n")
    print(f"{'CODE':<6} | {'COUNTRY':<20} | {'IP':<16} | {'SPEED (Mbps)':<12}")
    print("-" * 65)

    for s in sorted_countries:
        filename = f"{s['code']}.ovpn"
        filepath = os.path.join(CONFIGS_DIR, filename)
        
        try:
            ovpn_data = base64.b64decode(s["ovpn_b64"]).decode("utf-8", errors="ignore")
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(ovpn_data)
            print(f"{s['code'].upper():<6} | {s['name']:<20} | {s['ip']:<16} | {s['speed_mbps']:<12}")
        except Exception as err:
            print(f"[-] Failed to write {filename}: {err}")

    print("-" * 65)
    print(f"[+] All configs saved to '{CONFIGS_DIR}/'.")
    return True

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="VPNGate Config Downloader")
    parser.add_argument("--limit", type=int, default=10, help="Number of top countries to fetch (default: 10)")
    parser.add_argument("--countries", type=str, default="", help="Comma-separated country codes, e.g. jp,us,kr")
    args = parser.parse_args()

    countries = [c.strip().lower() for c in args.countries.split(",") if c.strip()] if args.countries else None
    success = fetch_and_save_configs(limit=args.limit, selected_countries=countries)
    sys.exit(0 if success else 1)
