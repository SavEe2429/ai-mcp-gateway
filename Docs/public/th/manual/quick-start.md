# คู่มือติดตั้งและเริ่มใช้งาน (Quick Start)

> ภาษา: [English](../../en/manual/quick-start.md) | **ภาษาไทย**

คู่มือนี้อธิบายวิธีติดตั้ง ตั้งค่า และเปิดใช้งาน `ai-mcp-gateway` ตั้งแต่เริ่มต้นจนพร้อมเชื่อมต่อกับ
AI

---

## วิธีที่ 1: ใช้ไฟล์ติดตั้ง Windows `.exe` (แนะนำสำหรับผู้ใช้งานทั่วไป)

1. ดาวน์โหลดไฟล์ `ai-mcp-gateway-windows-x64.zip` จากหน้า
   [GitHub Releases](https://github.com/SavEe2429/ai-mcp-gateway/releases)
2. แตกไฟล์ (Extract) ไปไว้ในโฟลเดอร์ที่โปรแกรมเขียนไฟล์ได้ เช่น `C:\Tools\ai-mcp-gateway\`
   - **ห้าม** นำไปวางใน `C:\Program Files\` เพราะระบบต้องสร้างฐานข้อมูลและโฟลเดอร์ `workspace/`
     ไว้ข้างๆ ไฟล์ `.exe`
3. _(สำหรับเชื่อมต่อ AI บนคลาวด์อย่าง Gemini / Claude / ChatGPT)_ ติดตั้งและตั้งค่า **Tailscale**
   พร้อมเปิด **MagicDNS**, **HTTPS Certificates** และ **Funnel** ให้เรียบร้อย อ่านขั้นตอนละเอียดที่
   [คู่มือตั้งค่า Tailscale Funnel](tailscale-setup.md)
4. เปิดใช้งานโดยดับเบิลคลิก `ai-mcp-gateway.exe` หรือรันใน PowerShell:
   ```powershell
   cd C:\Tools\ai-mcp-gateway
   .\ai-mcp-gateway.exe
   ```
5. เมื่อโปรแกรมเริ่มทำงาน หน้าต่างเทอร์มินัลจะแสดงข้อมูลเชื่อมต่อ:
   ```text
   =================================================================
   AI Agent MCP Gateway Starting
   Local Web Dashboard : http://localhost:3000/ui
   Active Workspace    : C:\Tools\ai-mcp-gateway\workspace
   MCP Server Endpoint : https://<your-machine>.ts.net/mcp
   Client ID           : local-mcp
   Client Secret       : ************xxxx (view full secret in /ui)
   =================================================================
   ```
   เบราว์เซอร์จะเปิดหน้า `http://localhost:3000/ui` ขึ้นมาอัตโนมัติพร้อมหน้าต่าง **เลือกโฟลเดอร์
   Workspace** และโปรแกรมจะจัดการไฟล์ข้อมูลไว้ข้างไฟล์ `.exe`:
   - `data/gateway.db`: ฐานข้อมูล SQLite เก็บ OAuth Token, Audit Log, รายการ IP ที่ถูกแบน และ MCP
     Server ภายนอกที่ติดตั้งไว้
   - `data/client_secret.key`: รหัส `Client Secret`
     ที่ระบบสุ่มสร้างให้อัตโนมัติในการเปิดใช้งานครั้งแรก
   - `data/gateway.lock`: ไฟล์ Lock ระดับ OS เพื่อป้องกันไม่ให้เปิดโปรแกรมซ้ำซ้อน 2 ตัวพร้อมกัน
     (ปรับตำแหน่งผ่าน Env `GATEWAY_LOCK_FILE` ได้)
   - `workspace/`: โฟลเดอร์พื้นที่ทำงานที่ AI สามารถเข้ามาอ่าน/เขียนไฟล์และรันคำสั่งได้
     (ปลอดภัยจากไฟล์ส่วนอื่นในเครื่อง)

---

## วิธีที่ 2: รันจากซอร์สโค้ดด้วย `uv` (สำหรับนักพัฒนา)

### สิ่งที่ต้องมีในเครื่อง

- Python `3.14` ขึ้นไป
- [`uv`](https://docs.astral.sh/uv/) Package Manager
- _(ทางเลือก)_ [Tailscale CLI](https://tailscale.com/download) ที่เรียกใช้ผ่าน `PATH` ได้

### ขั้นตอนติดตั้งและรัน

```bash
git clone https://github.com/SavEe2429/ai-mcp-gateway.git
cd ai-mcp-gateway
uv sync --dev

# รันผ่านคำสั่งที่ลงทะเบียนไว้
uv run ai-mcp-gateway

# หรือรันผ่าน Python module
uv run python -m ai_mcp_gateway
```

---

## การปรับแต่งการตั้งค่า (`config/config.yaml`)

ค่าคอนฟิกทั้งหมดถูกควบคุมจากจุดเดียว (SSOT) และตรวจสอบความถูกต้องตอนเปิดโปรแกรมด้วย Pydantic

### วิธีปรับแต่งค่าเมื่อใช้งานแบบ `.exe`

1. สร้างโฟลเดอร์ชื่อ `config/` ข้างๆ ไฟล์ `ai-mcp-gateway.exe`
2. คัดลอกไฟล์ต้นแบบ [config/config.yaml](../../../../config/config.yaml) มาวางเป็น
   `config/config.yaml` แล้วแก้ไขตามต้องการ
3. ลำดับการค้นหาไฟล์คอนฟิก (`find_config_yaml`):
   1. ตัวแปรสภาพแวดล้อม `GATEWAY_CONFIG_PATH`
   2. `<โฟลเดอร์ที่รัน>/config/config.yaml` (ข้าง `.exe` หรือโฟลเดอร์หลักโปรเจกต์)
   3. `<โฟลเดอร์ปัจจุบัน>/config/config.yaml`
   4. ค่าเริ่มต้นที่ฝังมาในไฟล์ `.exe`

### ค่าสำคัญที่นิยมปรับแต่ง

- `server.port`: พอร์ตของ Gateway (ค่าเริ่มต้น `3000`)
- `server.enable_tailscale_funnel`: ตั้งเป็น `true` (ค่าเริ่มต้น) เพื่อเปิดออกเน็ตผ่าน Tailscale
  Funnel หรือ `false` เมื่อใช้ทดสอบเฉพาะในเครื่อง (`http://localhost:3000/mcp`)
- `session.ttl`: อายุ OAuth Access Token เป็นวินาที (ค่าเริ่มต้น `604800` = 7 วัน
  แบบต่ออายุเมื่อใช้งาน)
- `session.terminal_timeout`: จำนวนวินาทีก่อนให้คำสั่ง `run_command` ย้ายไปรันเบื้องหลัง
  (ค่าเริ่มต้น `60.0` วินาที)
- `auth.client_id` / `auth.client_secret`: ปรับชื่อ Client ID (ค่าเริ่มต้น `local-mcp`) หรือกำหนด
  Secret ตายตัวแทนการใช้ไฟล์ `data/client_secret.key` (หรือใช้ Env Var `MCP_CLIENT_ID`,
  `MCP_CLIENT_SECRET`, `GATEWAY_SECRET_KEY`)

---

## ขั้นตอนการใช้งานประจำวัน

1. **เช็ก URL เชื่อมต่อ**: ดูช่อง `MCP Server Endpoint` ในหน้าต่างเทอร์มินัล หรือแถบ **MCP
   Endpoint** มุมขวาบนของ Web Dashboard (`http://localhost:3000/ui`)
2. **เลือกโฟลเดอร์ Workspace**: เลือกหรือยืนยันโฟลเดอร์ในหน้าต่าง **Select Workspace**
   ที่เด้งขึ้นมาเมื่อเปิด Dashboard (หรือเปลี่ยนภายหลังได้ที่ปุ่ม **Browse** ใน Sidebar ด้านซ้าย)
3. **กำหนดสิทธิ์ความปลอดภัย**: เปิด/ปิดสิทธิ์ `Read Files`, `Write & Patch`, `Terminal Commands`,
   `Vision & Screenshots` และแนะนำให้เปิด **`HITL Manual Approval`** ไว้
   เพื่อให้โปรแกรมถามคุณก่อนทุกครั้งที่ AI จะแก้ไขไฟล์หรือรันคำสั่ง
4. **เชื่อมต่อ AI**: นำ `MCP Endpoint`, `Client ID`, และ `Client Secret` ไปกรอกใน Gemini, Claude
   หรือ ChatGPT ตาม [คู่มือเชื่อมต่อ AI](mcp-integration.md)
5. **ปิดโปรแกรมอย่างถูกต้อง**: กด `Ctrl+C` ในหน้าต่างเทอร์มินัล เพื่อให้ระบบปิดการเชื่อมต่อ MCP
   Server ภายนอกและฐานข้อมูล SQLite อย่างสมบูรณ์

---

## ขั้นตอนถัดไป

- [คู่มือการติดตั้งและทำงานของ Tailscale Funnel](tailscale-setup.md)
- [คู่มือการใช้งาน Web Dashboard](dashboard-guide.md)
- [คู่มือเชื่อมต่อ AI (MCP Integration)](mcp-integration.md)
