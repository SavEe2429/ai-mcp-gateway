# คู่มือการใช้งาน Web Dashboard

> ภาษา: [English](../../en/manual/dashboard-guide.md) | **ภาษาไทย**

Web Dashboard (`http://localhost:3000/ui`) คือศูนย์ควบคุมหลักของ `ai-mcp-gateway` บนเครื่องของคุณ เพื่อความปลอดภัย หน้านี้รับเฉพาะการเชื่อมต่อจากเครื่องตัวเอง (`127.0.0.1`, `::1`, `localhost`) และปฏิเสธการเข้าถึงจาก Tailscale Funnel หรือ Reverse Proxy ด้วย `403 Forbidden` เสมอ

---

## 1. แถบนำทางด้านบน (Top Navigation Header)

แถบด้านบนจะแสดงอยู่ตลอดเวลาในทุกหน้า ประกอบด้วย:

- **ปุ่มซ่อน/ขยาย Sidebar** (มุมซ้ายบน): พับหรือกางแถบควบคุมด้านซ้าย
- **สถานะการเชื่อมต่อ**: แสดง `ONLINE • STREAMABLE HTTP` เมื่อ WebSocket (`/ws/ui`) เชื่อมต่ออยู่ หรือ `DISCONNECTED` เมื่อ Server หยุดทำงาน
- **ปุ่มสลับโหมดตรงกลาง** (3 หน้าจอหลัก):
  1. **MCP Server**: ดูสถิติการใช้งานของ AI แต่ละเจ้า, คิวอนุมัติคำสั่งแบบ HITL, Activity Logs และ Developer Inspector
  2. **MCP Client Hub**: แสดงจำนวน MCP Server ภายนอกที่ติดตั้งไว้ และหน้าติดตั้งเพิ่มเติมจาก GitHub
  3. **Banned IPs**: แสดงจำนวน IP ที่ถูกบล็อก และเปิดตารางจัดการ Security Shield
- **แถบ MCP Endpoint** (มุมขวาบน):
  - **Privacy Masking**: ซ่อนชื่อโดเมน Tailscale Funnel ไว้โดยค่าเริ่มต้น (`https://••••••••••••••••/mcp`) เพื่อความปลอดภัยเวลาแคปหน้าจอแชร์ สามารถกด `Show` / `Hide` เพื่อดูหรือซ่อนได้
  - **Copy**: คัดลอก `mcp_url` ฉบับเต็มลง Clipboard ทันที
- **ปุ่มสลับธีม (Dark / Light Mode)**: เปลี่ยนโหมดมืด/สว่างและบันทึกค่าไว้ในเบราว์เซอร์ (`localStorage`)

---

## 2. แถบควบคุมด้านซ้าย (Left Control Sidebar)

### 2.1 Workspace
กำหนดโฟลเดอร์ราก (Sandboxed Root) ที่ AI สามารถเข้าถึงผ่านเครื่องมือจัดการไฟล์และเทอร์มินัล (`list_workspace_files`, `read_workspace_file`, `write_workspace_file`, `patch_workspace_file`, `run_command`):
- **ช่องกรอก Path + ปุ่ม `Save`**: พิมพ์หรือวางตำแหน่งโฟลเดอร์แล้วกด `Enter` หรือ `Save` (หากโฟลเดอร์ยังไม่มี ระบบจะสร้างให้อัตโนมัติ)
- **ปุ่ม `Browse`**: เปิดหน้าต่างเลือกโฟลเดอร์ของระบบปฏิบัติการและเปลี่ยน Workspace ทันทีเมื่อเลือกเสร็จ
- การเข้าถึงไฟล์ทุกคำสั่งจะผ่านฟังก์ชัน `safe_path()` เพื่อป้องกันการเจาะออกนอกโฟลเดอร์ (`../`, Symlink, หรือ Junction)

### 2.2 Access Control
แสดงจำนวนสิทธิ์ที่เปิดอยู่ (`X/5 Active`) พร้อมสวิตช์เปิด/ปิดสิทธิ์แบบเรียลไทม์:
- **`Read Files`** (`allow_read`): เปิด/ปิดการดูรายชื่อและอ่านไฟล์ใน `workspace/`
- **`Write & Patch`** (`allow_write`): เปิด/ปิดการสร้าง เขียนทับ และแก้ไขไฟล์
- **`Terminal Commands`** (`allow_bash`): เปิด/ปิดการรันคำสั่ง Shell ผ่าน `run_command`
- **`Vision & Screenshots`** (`allow_vision`): เปิด/ปิดการอ่านรูปใน Workspace และเครื่องมือจับภาพหน้าต่าง/หน้าจอเดสก์ท็อป
- **`HITL Manual Approval`** (`require_approval`): เมื่อเปิด (`ON`) ทุกครั้งที่ AI เรียกใช้คำสั่งแก้ไขไฟล์หรือรันคำสั่งเทอร์มินัล (`write_workspace_file`, `patch_workspace_file`, `run_command`) ระบบจะหยุดรอให้คุณกด **`Approve`** หรือ **`Deny`** ในหน้า Dashboard ก่อน (มีเวลาตัดสินใจ 5 นาที)

### 2.3 OAuth Credentials
แสดงข้อมูลรับรองสำหรับนำไปกรอกเวลาเชื่อมต่อ AI ภายนอก:
- **`Client ID`**: รหัสตัวระบุ Client (ค่าเริ่มต้น `local-mcp`) กดคัดลอกได้ทันที
- **`Client Secret`**: ซ่อนเป็นจุด (`••••••••••••••••••••`) โดยค่าเริ่มต้น กด `Show` / `Hide` เพื่อดู หรือกด `Copy` เพื่อคัดลอกค่าที่เก็บใน `data/client_secret.key`

### 2.4 Shield Protection Quick Card
แสดงจำนวน IP ที่ถูกแบนในขณะนั้น พร้อมปุ่มลัด **`Open Banned List`** เพื่อกระโดดไปยังหน้าจัดการความปลอดภัย

---

## 3. หน้าจอที่ 1: MCP Server Mode

### 3.1 การ์ดสถิติ AI Provider (Telemetry Cards)
การ์ด 3 ใบสำหรับติดตามสถานะของ AI ค่ายหลัก:
- **Google Gemini** (`Custom MCP Client`)
- **Claude AI** (`Remote Connector`)
- **ChatGPT** (`OpenAI Actions`)

แต่ละการ์ดแสดง **จำนวน Request ทั้งหมด** และ **Session TTL** (อายุ Token ที่เหลืออยู่ ค่าเริ่มต้น 7 วันแบบต่ออายุอัตโนมัติ) พร้อมสีเตือน: เขียว (มากกว่า 1 วัน), เหลืองอำพัน (น้อยกว่า 1 วัน), แดง (หมดอายุ)

### 3.2 คิวรออนุมัติคำสั่ง (Pending Approvals Queue - HITL)
จะแสดงขึ้นมาอัตโนมัติเมื่อเปิด `HITL Manual Approval` และมีคำสั่งเขียนไฟล์/แก้ไขไฟล์/รันเทอร์มินัลเข้ามา:
- แสดงชื่อ Tool, ชื่อไฟล์เป้าหมาย หรือคำสั่ง Shell ที่กำลังจะรัน
- **`Approve`**: อนุญาตให้คำสั่งทำงานต่อทันที
- **`Deny`**: ปฏิเสธคำสั่ง ส่งข้อความปฏิเสธกลับไปหา AI และบันทึก Audit Log สถานะ `DENIED`

### 3.3 แท็บ Activity Log
แสดงบันทึกการทำงานจากฐานข้อมูล SQLite แบบเรียลไทม์ (`logs.length`):
- ป้ายสถานะ (`SUCCESS`, `ERROR`, `DENIED`)
- ป้ายระบุตัวตน AI Client (`Gemini`, `Claude`, `ChatGPT`, `Cursor` ฯลฯ)
- ชื่อ Tool, พารามิเตอร์ที่เรียกใช้, เวลา, และผลลัพธ์ (Output)
- **`Clear Logs`**: ล้างประวัติ Audit Log และรีเซ็ตตัวนับ Request บนทุกหน้าต่างที่เปิดอยู่

### 3.4 แท็บ Developer Inspector
แสดง HTTP Traffic สดๆ ที่ยิงเข้า `/mcp` และ `/oauth` (เก็บล่าสุด 100 รายการในหน่วยความจำ):
- ชื่อ Client ที่ตรวจจับได้
- HTTP Method (`POST`, `GET`, `DELETE`) และ Path
- ระยะเวลาตอบสนอง (`ms`) และ HTTP Status Code (สีเขียว `< 400`, สีแดง `>= 400`)

---

## 4. หน้าจอที่ 2: MCP Client Hub

ใช้เปลี่ยน `ai-mcp-gateway` ให้เป็นตัวรวมเครื่องมือ (**MCP Aggregator**) โดยดึง MCP Server อื่นๆ จาก GitHub มารันแบบ stdio แล้วส่งต่อเครื่องมือให้ AI ใช้งานร่วมกัน

### 4.1 ติดตั้ง MCP Server ใหม่จาก GitHub
1. **GitHub URL**: วางลิงก์ Repo เต็ม (เช่น `https://github.com/owner/repo`) หรือลิงก์เจาะจงโฟลเดอร์ย่อย (`/tree/main/src/...`)
2. **Environment (ตัวเลือกเสริม)**: กรอกตัวแปร Env คั่นด้วยลูกน้ำ เช่น `API_KEY=xyz, PORT=8080`
3. **Custom Command / Args (พับเก็บได้)**: กดขยายเมื่อ Repo ปลายทางต้องใช้คำสั่งสตาร์ทแบบพิเศษ (เช่นกำหนด `Command` เป็น `uv` หรือ `node` พร้อม `Arguments`)
4. กด **`Install & Connect`**:
   - โคลนโค้ดมาเก็บไว้ใน `data/mcp_servers/`
   - ตรวจจับ Node.js (`package.json`, รัน `npm install`) หรือ Python (`pyproject.toml`, `requirements.txt`, รันผ่าน `uv run`) ให้อัตโนมัติ
   - เชื่อมต่อแบบ stdio และนำ Tool ทั้งหมดมาเผยแพร่ใน Gateway ภายใต้ชื่อ `<owner>_<repo>__<tool_name>`

### 4.2 รายการ MCP Server ที่ติดตั้งแล้ว
- **`Refresh Status`**: โหลดสถานะล่าสุดและรายการ Tool ใหม่
- แต่ละการ์ดแสดงชื่อ Repo, ประเภท Runtime (`PYTHON` / `NODE`), สถานะ (`RUNNING` / `STOPPED`), รายชื่อ **Bridged Tools** (ชี้เมาส์เพื่อดูคำอธิบาย Tool), ปุ่ม **`Start` / `Stop`**, และปุ่ม **`Uninstall`** (หยุดโปรเซส ลบโฟลเดอร์ที่โคลน และลบออกจากฐานข้อมูล)

---

## 5. หน้าจอที่ 3: Security Shield & Banned IPs

ระบบป้องกันเครื่องเมื่อเปิด Funnel ออกอินเทอร์เน็ต:

- **Automatic Scanner Shield**: เมื่อมีบอทหรือผู้ไม่หวังดียิง Path สแกนหาช่องโหว่เข้ามา (เช่น `.php`, `.env`, `.bak`, `/wp-`, `/wordpress`, `/vendor`, `/token.json` ตั้งค่าเพิ่มได้ใน `config/config.yaml`) ระบบจะตอบ `404 Not Found` และ **แบน IP นั้นชั่วคราวอัตโนมัติ** (ค่าเริ่มต้น 1 ชั่วโมง; ครั้งถัดไปจะโดน `403 Forbidden` ทันที) โดยไม่แบน Localhost
- **Manual IP Ban**: พิมพ์ IP ที่ต้องการบล็อกแล้วกด **`Ban IP`** (หรือ `Enter`) เพื่อแบนทันที
- **ตาราง Banned IPs**: แสดง `IP Address`, เหตุผลและ Path ที่ถูกยิง, จำนวน `Hits`, เวลาที่เหลือ, ปุ่ม **`Unban`** รายตัว และ **`Clear All Bans`** เพื่อล้างรายการแบนทั้งหมด
