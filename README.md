# OpenVPN Multi-Country SOCKS5 Proxy (Docker)

Run multiple isolated OpenVPN client tunnels inside lightweight Docker containers (Alpine + Dante SOCKS5). Each country or VPN profile gets a dedicated, deterministic SOCKS5 port (`127.0.0.1:1081`, `1082`, etc.) without altering the host server's routing table or disrupting SSH/existing services.

Includes an automated server fetcher for [VPNGate](https://www.vpngate.net) and generates ready-to-use **Xray / X-UI Outbound JSON** with country flag emojis.

---

## Key Features

- **Isolated Routing**: OpenVPN runs strictly inside each container's network namespace (`tun0`). Your host's default gateway and SSH connections remain completely untouched.
- **Deterministic Fixed Ports**: Pre-mapped ports for countries (e.g., UAE 🇦🇪 on `1081`, Japan 🇯🇵 on `1082`, Korea 🇰🇷 on `1083`, USA 🇺🇸 on `1084`).
- **VPNGate Integration**: Automatically queries VPNGate API, selects top-scoring servers per country, and downloads `.ovpn` profiles.
- **Xray / X-UI Integration**: Automatically generates `xray_outbounds.json` with country flag tags (e.g. `🇦🇪 UAE-ovpn`, `🇯🇵 Japan-ovpn`).
- **Lightweight**: Built on Alpine Linux with `dante-server`. Each container uses only ~30–50 MB RAM and near-zero idle CPU.

---

## Quick Start

### 1. Prerequisites

- Docker & Docker Compose
- Python 3

### 2. Fetch Configs & Launch

Run the automated script to fetch fresh configs, generate Docker Compose, and start the containers:

```bash
chmod +x generate.sh generate.py update_configs.py entrypoint.sh
./generate.sh --up
```

This will:
1. Fetch top servers from VPNGate API into `configs/` (`uae.ovpn`, `jp.ovpn`, `us.ovpn`, etc.).
2. Assign fixed ports and generate `docker-compose.yml`.
3. Generate `xray_outbounds.json` and `locations.txt`.
4. Launch all containers in detached mode (`docker compose up -d`).

---

## Port Mapping

| Port | Country | Xray Outbound Tag | Container Name |
| :---: | :---: | :---: | :---: |
| **`1081`** | 🇦🇪 UAE | `🇦🇪 UAE-ovpn` | `vpn-uae` |
| **`1082`** | 🇯🇵 Japan | `🇯🇵 Japan-ovpn` | `vpn-jp` |
| **`1083`** | 🇰🇷 South Korea | `🇰🇷 Korea-ovpn` | `vpn-kr` |
| **`1084`** | 🇺🇸 USA | `🇺🇸 USA-ovpn` | `vpn-us` |
| **`1085`** | 🇩🇪 Germany | `🇩🇪 Germany-ovpn` | `vpn-de` |
| **`1086`** | 🇬🇧 UK | `🇬🇧 UK-ovpn` | `vpn-uk` |
| **`1087`** | 🇨🇦 Canada | `🇨🇦 Canada-ovpn` | `vpn-ca` |
| **`1088`** | 🇷🇴 Romania | `🇷🇴 Romania-ovpn` | `vpn-ro` |
| **`1089`** | 🇹🇷 Turkey | `🇹🇷 Turkey-ovpn` | `vpn-tr` |

*(Additional countries automatically receive ports from `1095` onwards).*

---

## Testing Connections

Test any SOCKS5 port from your terminal:

```bash
# Test UAE proxy (Port 1081)
curl --socks5-hostname 127.0.0.1:1081 https://api.ipify.org?format=json

# Test Japan proxy (Port 1082)
curl --socks5-hostname 127.0.0.1:1082 https://api.ipify.org?format=json
```

---

## Using Custom `.ovpn` Files

You can place your own custom `.ovpn` files directly in `configs/`:

```text
configs/
  ├── uae.ovpn
  ├── germany.ovpn
  └── ...
```

If your configuration requires username/password authentication, create an `auth.txt` file in the root directory:
```text
username
password
```

Then regenerate and reload:
```bash
./generate.sh --skip-fetch --up
```

---

## Xray / X-UI Outbound Integration

Whenever you run `./generate.sh`, it generates `xray_outbounds.json`. Simply copy the array into your Xray configuration's `"outbounds"` section:

```json
[
  {
    "tag": "🇦🇪 UAE-ovpn",
    "protocol": "socks",
    "settings": {
      "servers": [
        {
          "address": "127.0.0.1",
          "port": 1081,
          "users": []
        }
      ]
    }
  },
  {
    "tag": "🇯🇵 Japan-ovpn",
    "protocol": "socks",
    "settings": {
      "servers": [
        {
          "address": "127.0.0.1",
          "port": 1082,
          "users": []
        }
      ]
    }
  }
]
```

---

## Useful Commands

```bash
# View all running VPN tunnels
docker compose ps

# View logs for a specific tunnel
docker compose logs -f vpn-uae

# Restart a specific tunnel
docker compose restart vpn-uae

# Stop all tunnels
docker compose down
```

## License

MIT
