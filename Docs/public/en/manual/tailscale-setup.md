# Tailscale Funnel Setup & Architecture

> Language: **English** | [ภาษาไทย](../../th/manual/tailscale-setup.md)

Remote cloud AI assistants (Google Gemini, Anthropic Claude, OpenAI ChatGPT) cannot call `http://localhost:3000/mcp` directly on your PC, and OAuth 2.1 requires a valid **HTTPS** URL with a trusted TLS certificate. `ai-mcp-gateway` solves this automatically with **Tailscale Funnel**.

---

## 1. Why Tailscale Funnel Is Used

- **Zero Router Configuration:** No router port-forwarding (`UPnP`, NAT rules) or public static IP required.
- **Managed HTTPS Certificates:** Tailscale automatically provisions and renews valid Let's Encrypt TLS certificates for `https://<machine>.<tailnet>.ts.net`.
- **Automatic Discovery at Startup:** You do not need to memorize commands or manually type domains into config files — `ai-mcp-gateway` reads your active Tailscale MagicDNS hostname and binds Funnel to the configured gateway port.
- **Strict Local Dashboard Isolation:** Even though your gateway is reachable externally over Funnel, security middleware inspects Tailscale Funnel proxy headers and restricts `/ui` and `/api/ui/*` strictly to localhost.

---

## 2. How `ai-mcp-gateway` Automates Tailscale (`core/tunnel.py`)

When `server.enable_tailscale_funnel: true` in `config/config.yaml` (default), `run_server()` invokes `start_tailscale_funnel(port)` before starting Uvicorn:

```text
ai-mcp-gateway startup
   │
   ├─► 1. Run `tailscale status --json`
   │      └─► Read `Self.DNSName` (e.g. "workstation.tailnet-abc.ts.net")
   │
   ├─► 2. Run `tailscale funnel --bg <port>` (default port 3000)
   │      └─► Tailscale maps https://<DNSName>:443 -> http://127.0.0.1:3000
   │
   └─► 3. Publish `https://<DNSName>/mcp` as `state.mcp_url`
          ├─► Printed in startup terminal banner
          └─► Displayed (masked by default) in Web Dashboard top-right bar
```

### Request Security Separation (`interfaces/middleware/shield.py`)
When traffic enters through Tailscale Funnel, Tailscale attaches proxy headers (`Tailscale-Funnel-Request` / `X-Forwarded-*`). Our ASGI security middleware handles each route differently:

| Route Group | Over Tailscale Funnel (External) | From Local Machine (`127.0.0.1` / `::1`) |
| :--- | :--- | :--- |
| `POST /mcp`, `DELETE /mcp`, `/sse` | **Allowed** (requires valid OAuth Bearer token) | **Allowed** (requires valid OAuth Bearer token) |
| `/oauth/*`, `/.well-known/*` | **Allowed** (OAuth 2.1 PKCE + RFC 8414/9728) | **Allowed** |
| `/ui`, `/api/ui/*`, `/ws/ui` | **Blocked (`403 Forbidden`)** | **Allowed** (Localhost control center) |
| Scanner paths (`.php`, `.env`, `/wp-*`) | **Auto-Banned** (`404` -> temporary IP ban -> `403`) | Never banned |

---

## 3. Prerequisites: Configuring Tailscale (One-Time Setup)

Before launching `ai-mcp-gateway` with Funnel enabled, configure your Tailscale account once:

1. **Install & Sign In to Tailscale**
   - Download Tailscale for Windows/macOS/Linux from [tailscale.com/download](https://tailscale.com/download).
   - Sign in on your PC and confirm `tailscale` is available in your terminal (`tailscale version`).
2. **Enable MagicDNS & HTTPS Certificates**
   - Open the [Tailscale Admin Console](https://login.tailscale.com/admin/dns) -> **DNS**.
   - Enable **MagicDNS**.
   - Under **HTTPS Certificates**, click **Enable HTTPS**.
3. **Allow Funnel in Access Controls (ACL / `nodeAttrs`)**
   By default, Tailscale blocks Funnel on new tailnets until a `nodeAttrs` rule grants the `"funnel"` capability. You can enable it using either method below:

   - **Method A — Automatic One-Click Link via CLI (Easiest):**
     1. Run the Funnel command once in PowerShell / Terminal:
        ```powershell
        tailscale funnel --bg 3000
        ```
     2. If Funnel is not yet allowed on your tailnet, Tailscale prints an activation link in the terminal:
        ```text
        To allow Funnel, visit:
        https://login.tailscale.com/f/funnel?node=...
        ```
     3. Open that URL in your browser (signed in as your Tailnet Admin) and click **Enable** — Tailscale automatically adds `"funnel"` to your policy file.
     4. Verify that `tailscale funnel status` shows `https://<your-node>.ts.net` pointing to `http://127.0.0.1:3000` (optional: run `tailscale funnel 3000 off` if you want to turn it off until `ai-mcp-gateway` starts).

   - **Method B — Manual Edit in Tailscale Admin Console (`Access Controls`):**
     1. Open [Access Controls](https://login.tailscale.com/admin/acls) in the Tailscale Admin Console.
     2. In the **Policy File** JSON editor, find the top-level `"nodeAttrs"` block (or add it if missing) and insert `"funnel"`:
        - **Allow all members/devices on your personal tailnet:**
          ```json
          "nodeAttrs": [
            {
              "target": ["autogroup:member"],
              "attr": ["funnel"]
            }
          ]
          ```
        - **Or restrict Funnel to a specific user/tag (recommended for shared/team tailnets):**
          ```json
          "nodeAttrs": [
            {
              "target": ["your-email@example.com"],
              "attr": ["funnel"]
            }
          ]
          ```
     3. Click **Save** to apply the updated ACL policy.

   > **Note:** Tailscale Funnel accepts public internet HTTPS traffic regardless of internal tailnet `acls` rules, which is why `ai-mcp-gateway` enforces OAuth 2.1 Bearer authentication on `/mcp` and locks `/ui` strictly to localhost.
4. **Verify from PowerShell / Terminal**:
   ```powershell
   tailscale status
   ```
   Confirm your node is online. Once `ai-mcp-gateway` starts, you can inspect the active Funnel mapping with:
   ```powershell
   tailscale funnel status
   ```
   You should see `https://<your-node>.ts.net` proxying to `http://127.0.0.1:3000`.

---

## 4. Managing Funnel Manually or Using Local-Only Mode

### Stopping Tailscale Funnel Manually
By default, `tailscale funnel --bg <port>` stays registered in the background Tailscale daemon even after closing the terminal. To stop exposing port `3000` externally at any time:
```powershell
tailscale funnel 3000 off
```
*(Or reset all serve/funnel rules with `tailscale funnel reset`.)*

### Disabling Tailscale (Local-Only Development Mode)
If you do not have Tailscale installed or only want local MCP clients (for example a local Cursor or IDE agent on the same machine) to connect over HTTP:
1. Edit `config/config.yaml`:
   ```yaml
   server:
     enable_tailscale_funnel: false
   ```
2. Restart `ai-mcp-gateway`. The MCP endpoint will be `http://localhost:3000/mcp`.

---

## 5. Troubleshooting Tailscale Funnel

| Symptom in Console | Cause | Resolution |
| :--- | :--- | :--- |
| `'tailscale' executable not found in PATH` | Tailscale CLI is not installed or not in `PATH`. | Install Tailscale, restart your terminal/IDE, or add `C:\Program Files\Tailscale\` to system `PATH`. |
| `Unable to query status` | Tailscale desktop service is stopped or signed out. | Open the Tailscale app in your system tray and sign in. |
| `DNSName unavailable; verify MagicDNS is enabled` | MagicDNS is turned off in your Tailscale Admin Console. | Enable **MagicDNS** under **DNS** in the Tailscale Admin Console. |
| `[Tailscale Funnel Error] ...` | HTTPS Certificates or Funnel ACL is not enabled yet. | Run `tailscale funnel --bg 3000` once in PowerShell and open the activation link printed by Tailscale. |
| Dashboard `/ui` returns `403 Forbidden` | You opened your public `https://<domain>/ui` Funnel URL instead of `localhost`. | Always open the dashboard locally at `http://localhost:3000/ui`. |
