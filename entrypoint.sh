#!/bin/bash
set -e

# Ensure /dev/net/tun exists
mkdir -p /dev/net
if [ ! -c /dev/net/tun ]; then
    mknod /dev/net/tun c 10 200
fi

# Find an ovpn configuration file in /etc/openvpn
OVPN_FILE=$(find /etc/openvpn -maxdepth 1 -name "*.ovpn" | head -n 1)

if [ -z "$OVPN_FILE" ]; then
    echo "[-] ERROR: No .ovpn file found in /etc/openvpn"
    echo "    Please mount your .ovpn configuration file into /etc/openvpn"
    exit 1
fi

echo "[+] Using OpenVPN config: $OVPN_FILE"

# Preserve local / Docker subnet routing to eth0 so inbound SOCKS connections never break
DEFAULT_GW=$(ip route | awk '/default/ {print $3}' | head -n 1)
if [ -n "$DEFAULT_GW" ]; then
    ip route add 10.0.0.0/8 via "$DEFAULT_GW" dev eth0 2>/dev/null || true
    ip route add 172.16.0.0/12 via "$DEFAULT_GW" dev eth0 2>/dev/null || true
    ip route add 192.168.0.0/16 via "$DEFAULT_GW" dev eth0 2>/dev/null || true
fi

# OpenVPN authentication credentials check
EXTRA_ARGS=()
if [ -f /etc/openvpn/auth.txt ]; then
    # If config explicitly asks for auth-user-pass or has it enabled
    if grep -qiE '^[[:space:]]*auth-user-pass' "$OVPN_FILE" 2>/dev/null; then
        EXTRA_ARGS+=(--auth-user-pass /etc/openvpn/auth.txt)
        echo "[+] Auth credentials attached from auth.txt"
    fi
fi

# Backward compatibility for older ciphers (e.g. VPNBook / SoftEther AES-CBC)
EXTRA_ARGS+=(--data-ciphers "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-256-CBC:AES-128-CBC")

# Start OpenVPN daemon with file logging
openvpn --config "$OVPN_FILE" "${EXTRA_ARGS[@]}" --daemon --log /tmp/openvpn.log

echo "[+] Waiting for OpenVPN tunnel (tun0) to come up..."
timeout=30
while [ $timeout -gt 0 ] && ! ip link show tun0 > /dev/null 2>&1; do
    sleep 1
    timeout=$((timeout - 1))
done

if ! ip link show tun0 > /dev/null 2>&1; then
    echo "[-] ERROR: OpenVPN failed to connect within 30s. Connection log:"
    echo "------------------------------------------------------------"
    cat /tmp/openvpn.log 2>/dev/null || echo "No log available"
    echo "------------------------------------------------------------"
    exit 1
fi

echo "[+] VPN tunnel connected (tun0 is up)."
echo "[+] Starting Dante SOCKS5 proxy on 0.0.0.0:1080 (routing via tun0)..."
exec sockd -f /etc/sockd.conf
