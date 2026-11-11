# คู่มือเชื่อมต่อ AI ภายนอก (MCP Integration Guide)

> ภาษา: [English](../../en/manual/mcp-integration.md) | **ภาษาไทย**

คู่มือนี้อธิบายวิธีเชื่อมต่อแพลตฟอร์ม AI ภายนอก (**Google Gemini**, **Anthropic Claude**, **OpenAI ChatGPT** และ Client ที่รองรับ MCP) เข้ากับ `ai-mcp-gateway`

---

## 1. ภาพรวมโปรโตคอลและ OAuth Endpoints

`ai-mcp-gateway` รองรับมาตรฐาน MCP Specification (`2024-11-05+`) ผ่าน **Streamable HTTP**:

- **MCP Endpoint**: `https://<your-funnel-domain>/mcp` (ดูได้จากแถบมุมขวาบนของ [Web Dashboard](dashboard-guide.md) หรือหน้าต่างเทอร์มินัลตอนเปิดโปรแกรม)
- **Transport**: `POST /mcp` (JSON-RPC 2.0) และ `DELETE /mcp` (ปิด Session); หาก Client เก่ายิง `/sse` เข้ามา Gateway จะแปลงเส้นทางไปที่ `/mcp` ให้อัตโนมัติ
- **Session Recovery**: หากปิด/เปิด Gateway ใหม่แล้ว AI Client ส่ง `mcp-session-id` เดิมกลับมา ระบบจะจำลองการเชื่อมต่อใหม่ให้อัตโนมัติโดย Session ไม่หลุด
- **OAuth 2.0 / 2.1 + PKCE (`S256`) (รองรับ RFC 8414 & RFC 9728)**:
  - `GET /.well-known/oauth-protected-resource`
  - `GET /.well-known/oauth-authorization-server`
  - `GET /oauth/authorize`
  - `POST /oauth/token` (รองรับ `authorization_code`, `refresh_token`, และ `client_credentials`)

---

## 2. การดูรหัส Credentials (`Client ID` / `Client Secret`)

ค่าเริ่มต้นใน `config/config.yaml` กำหนด `auth.client_id: "local-mcp"` และระบบจะสุ่มสร้าง `Client Secret` เก็บไว้ใน `data/client_secret.key` คุณสามารถดูหรือคัดลอกได้จาก:
1. ข้อความแบนเนอร์ในเทอร์มินัลตอนเริ่มรันโปรแกรม
2. กล่อง **OAuth Credentials** ใน Sidebar ด้านซ้ายของ Web Dashboard (`http://localhost:3000/ui`) — กด `Show` / `Copy`

*(โดเมนสำหรับ OAuth Redirect ที่อนุญาตไว้เป็นค่าเริ่มต้น ได้แก่ `claude.ai`, `anthropic.com`, `chatgpt.com`, `openai.com`, `google.com`, `googleapis.com`, `googleusercontent.com`, `gemini.google.com` รวมถึง `localhost` / `127.0.0.1`)*

---

## 3. ขั้นตอนการเชื่อมต่อแต่ละแพลตฟอร์ม

### Google Gemini (Custom Apps / Connectors)
1. ตรวจสอบว่า Tailscale Funnel ทำงานอยู่และเข้าถึง `https://<your-funnel-domain>/mcp` ได้ (ดู [คู่มือตั้งค่า Tailscale Funnel](tailscale-setup.md))
2. สร้าง Custom App หรือ MCP Connector ใน Gemini / Google AI Studio แล้วกรอกค่า:
   - **MCP Server URL**: `https://<your-funnel-domain>/mcp`
   - **Authentication**: OAuth 2.0
   - **Client ID**: `local-mcp` (หรือค่าที่คุณตั้งเอง)
   - **Client Secret**: ค่าที่คัดลอกจาก Web Dashboard
   - **Authorization Endpoint**: `https://<your-funnel-domain>/oauth/authorize`
   - **Token Endpoint**: `https://<your-funnel-domain>/oauth/token`
3. ยืนยันหน้า Redirect ในเบราว์เซอร์ หลังจากเชื่อมต่อสำเร็จ การ์ด **Google Gemini** บน Dashboard จะเริ่มนับจำนวน Request และแสดงอายุ Token (`Session TTL`)

### Anthropic Claude
1. เพิ่ม Custom MCP Connector โดยใส่ URL เป็น `https://<your-funnel-domain>/mcp`
2. Claude จะค้นหา OAuth Endpoints อัตโนมัติผ่าน `/.well-known/oauth-protected-resource` และ `/.well-known/oauth-authorization-server`
3. กรอก `Client ID` และ `Client Secret` หากระบบถาม จากนั้นกดยืนยันผ่านเบราว์เซอร์ การใช้งานจะแสดงในการ์ด **Claude AI**

### OpenAI ChatGPT
1. ลงทะเบียน Remote MCP Connector ด้วย URL `https://<your-funnel-domain>/mcp` และทำขั้นตอน OAuth 2.1 + PKCE ให้เสร็จ
2. Request ที่มีข้อมูล `_meta` ของ OpenAI จะถูกระบุตัวตนและนับสถิติในการ์ด **ChatGPT** อัตโนมัติ

### ทดสอบในเครื่องเดียวกัน (Cursor / Local Client)
- หากปิด Tailscale (`enable_tailscale_funnel: false`) สามารถชี้ Client มาที่ `http://localhost:3000/mcp` ได้โดยตรง
- สามารถขอ Bearer Token ภายในเครื่องผ่าน `/oauth/authorize` + `/oauth/token` (หรือ `client_credentials` grant ด้วย `Client ID` และ `Client Secret`)

---

## 4. รายการเครื่องมือ (MCP Tools) ที่เปิดให้ AI ใช้งาน

เมื่อเชื่อมต่อสำเร็จ AI จะเรียกใช้เครื่องมือเหล่านี้ได้ตามสวิตช์สิทธิ์ใน **Access Control** และระบบอนุมัติ **HITL Manual Approval**:

- **จัดการไฟล์ใน Workspace** (`allow_read` / `allow_write`):
  - `list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `patch_workspace_file`
- **รันคำสั่งเทอร์มินัล** (`allow_bash`):
  - `run_command` (ย้ายคำสั่งที่ใช้เวลานานไปรันเบื้องหลังอัตโนมัติเมื่อเกิน `session.terminal_timeout`), `check_task_status`, `kill_task`
- **รูปภาพและจับภาพหน้าจอ** (`allow_vision`):
  - `read_workspace_image`, `list_active_windows`, `switch_active_window`, `capture_window_screenshot`, `take_desktop_screenshot`
- **เครื่องมือจาก MCP Client Hub (Bridged Tools)**:
  - เครื่องมือจาก Repo ภายนอกที่ติดตั้งผ่าน Hub จะปรากฏเป็นชื่อ `<owner>_<repo>__<tool_name>` อัตโนมัติ
