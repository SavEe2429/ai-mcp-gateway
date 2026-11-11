# คู่มือการติดตั้งและทำงานของ Tailscale Funnel

> ภาษา: [English](../../en/manual/tailscale-setup.md) | **ภาษาไทย**

AI บนคลาวด์อย่าง Google Gemini, Anthropic Claude และ OpenAI ChatGPT ไม่สามารถยิง Request มาที่ `http://localhost:3000/mcp` ในเครื่องคอมพิวเตอร์ของเราได้โดยตรง อีกทั้งมาตรฐาน OAuth 2.1 บังคับว่าต้องใช้ URL แบบ **HTTPS ที่มี Certificate น่าเชื่อถือ** — โปรเจกต์ `ai-mcp-gateway` จึงนำ **Tailscale Funnel** เข้ามาทำหน้าที่นี้ให้อัตโนมัติ

---

## 1. ทำไมต้องใช้ Tailscale Funnel?

- **ไม่ต้องตั้งค่า Router (No Port Forwarding):** ไม่ต้องเข้าไปเปิดพอร์ตใน Router บ้าน/ออฟฟิศ ไม่ต้องมี Public IP จริง หรือเช่า Domain/VPS แยก
- **ได้ HTTPS Certificate อัตโนมัติ:** Tailscale ออกใบรับรอง Let's Encrypt ที่เบราว์เซอร์และผู้ให้บริการ AI ยอมรับให้ฟรีในชื่อ `https://<ชื่อเครื่อง>.<ชื่อ-tailnet>.ts.net`
- **จัดการให้อัตโนมัติตอนเปิดโปรแกรม:** ผู้ใช้ไม่ต้องจำคำสั่งเปิด Tunnel เองทุกครั้ง โปรแกรมจะดึงชื่อโดเมนจาก Tailscale และเปิด Funnel ให้ทันที
- **แยกส่วนการเข้าถึงอย่างปลอดภัย:** แม้พอร์ตจะเชื่อมต่อกับภายนอกผ่าน Tailscale แต่ Gateway จะตรวจ Header ของ Tailscale และล็อกหน้าควบคุม Dashboard (`/ui`) ไว้ให้เปิดได้เฉพาะบนเครื่องตัวเองเท่านั้น

---

## 2. กลไกการทำงานในโค้ด (`core/tunnel.py`)

เมื่อตั้ง `server.enable_tailscale_funnel: true` ใน `config/config.yaml` (ค่าเริ่มต้น) ตอนเรียก `run_server()` โปรแกรมจะทำงานตามลำดับนี้ก่อนเริ่ม Web Server:

```text
ai-mcp-gateway เริ่มทำงาน
   │
   ├─► 1. รันคำสั่ง `tailscale status --json`
   │      └─► อ่านค่า `Self.DNSName` (เช่น "workstation.tailnet-abc.ts.net")
   │
   ├─► 2. รันคำสั่ง `tailscale funnel --bg <port>` (ค่าเริ่มต้นพอร์ต 3000)
   │      └─► Tailscale ผูก https://<DNSName>:443 เข้ากับ http://127.0.0.1:3000 แบบเบื้องหลัง
   │
   └─► 3. สร้าง URL `https://<DNSName>/mcp` เก็บใน state.mcp_url
          ├─► แสดงในแบนเนอร์เทอร์มินัลตอนเปิดโปรแกรม
          └─► แสดง (แบบซ่อนอักษรเริ่มต้น) ที่แถบมุมขวาบนของ Web Dashboard
```

### การคัดแยกความปลอดภัยของทราฟฟิก (`interfaces/middleware/shield.py`)
ทุก Request ที่วิ่งเข้ามาผ่าน Tailscale Funnel จะถูก Tailscale แปะ Header เช่น `Tailscale-Funnel-Request` และ `X-Forwarded-*` เข้ามาด้วย ตัว Middleware ของ Gateway จึงแยกสิทธิ์ตามเส้นทางได้ชัดเจน:

| กลุ่มเส้นทาง (Route) | เข้ามาจาก Tailscale Funnel (ภายนอก) | เข้ามาจากเครื่องตัวเอง (`127.0.0.1` / `::1`) |
| :--- | :--- | :--- |
| `POST /mcp`, `DELETE /mcp`, `/sse` | **อนุญาต** (ต้องแนบ OAuth Bearer Token ที่ถูกต้อง) | **อนุญาต** (ต้องแนบ OAuth Bearer Token) |
| `/oauth/*`, `/.well-known/*` | **อนุญาต** (ใช้ทำ OAuth 2.1 PKCE และค้นหา Endpoint) | **อนุญาต** |
| `/ui`, `/api/ui/*`, `/ws/ui` | **บล็อกทันที (`403 Forbidden`)** | **อนุญาต** (ใช้ควบคุม Dashboard ในเครื่อง) |
| Path สแกนช่องโหว่ (`.php`, `.env`, `/wp-*`) | **แบน IP ชั่วคราวอัตโนมัติ** (ตอบ `404` แล้วแบน -> `403`) | ไม่แบน Localhost |

---

## 3. วิธีตั้งค่า Tailscale สำหรับผู้ใช้งานครั้งแรก (ทำครั้งเดียว)

ก่อนเปิด `ai-mcp-gateway` เพื่อใช้งานกับ AI ภายนอก ให้เตรียม Tailscale ในบัญชีของคุณดังนี้:

1. **ติดตั้งและเข้าสู่ระบบ Tailscale**
   - ดาวน์โหลดและติดตั้ง Tailscale จาก [tailscale.com/download](https://tailscale.com/download)
   - กด Log in ให้เรียบร้อย และเช็กใน PowerShell/Terminal ว่าเรียกคำสั่ง `tailscale version` ได้ (อยู่ใน `PATH`)
2. **เปิด MagicDNS และ HTTPS Certificates**
   - เข้าหน้า [Tailscale Admin Console](https://login.tailscale.com/admin/dns) -> เมนู **DNS**
   - เปิดใช้งาน **MagicDNS**
   - ในหัวข้อ **HTTPS Certificates** กด **Enable HTTPS**
3. **เปิดสิทธิ์ Funnel ใน Access Controls (`nodeAttrs`)**
   โดยค่าเริ่มต้น Tailscale จะปิดสิทธิ์ใช้งาน Funnel ไว้จนกว่าจะมีการอนุญาต `"funnel"` ในนโยบาย ACL ของ Tailnet คุณสามารถเปิดสิทธิ์ได้ **2 วิธี** (เลือกวิธีใดวิธีหนึ่ง):

   - **วิธีที่ A — ใช้คำสั่ง CLI ให้สร้างลิงก์เปิดสิทธิ์อัตโนมัติ (ง่ายที่สุด):**
     1. เปิด PowerShell / Terminal แล้วลองรันคำสั่งนี้ 1 ครั้ง:
        ```powershell
        tailscale funnel --bg 3000
        ```
     2. หาก Tailnet ยังไม่ได้เปิดสิทธิ์ Funnel ตัว CLI จะพิมพ์ลิงก์เปิดใช้งานออกมา:
        ```text
        To allow Funnel, visit:
        https://login.tailscale.com/f/funnel?node=...
        ```
     3. เปิดลิงก์นั้นในเบราว์เซอร์ (ด้วยบัญชี Admin ของ Tailnet) แล้วกดยืนยันเปิดใช้งาน — Tailscale จะเพิ่มสิทธิ์ `"funnel"` เข้าไฟล์นโยบายให้อัตโนมัติ
     4. เช็กผลลัพธ์ด้วย `tailscale funnel status` ควรเห็น `https://<your-node>.ts.net` ชี้ไปที่ `http://127.0.0.1:3000` (หากยังไม่เริ่มใช้งาน Gateway ตอนนี้ สามารถสั่งปิดชั่วคราวด้วย `tailscale funnel 3000 off` ได้)

   - **วิธีที่ B — แก้ไขไฟล์นโยบายเองในหน้า Access Controls:**
     1. เข้าหน้า [Access Controls](https://login.tailscale.com/admin/acls) ใน Tailscale Admin Console
     2. ในกล่อง **Policy File** ให้มองหาหรือเพิ่มคีย์ `"nodeAttrs"` ที่ระดับบนสุดของไฟล์ JSON แล้วใส่สิทธิ์ `"funnel"`:
        - **อนุญาตทุกเครื่องของสมาชิกใน Tailnet (เหมาะสำหรับใช้ส่วนตัว):**
          ```json
          "nodeAttrs": [
            {
              "target": ["autogroup:member"],
              "attr": ["funnel"]
            }
          ]
          ```
        - **หรือจำกัดเฉพาะอีเมล/Tag ที่ต้องการ (แนะนำเมื่อใช้ Tailnet ร่วมกับทีม):**
          ```json
          "nodeAttrs": [
            {
              "target": ["your-email@example.com"],
              "attr": ["funnel"]
            }
          ]
          ```
     3. กดปุ่ม **Save** เพื่อบันทึกนโยบาย

   > **หมายเหตุความปลอดภัย:** การเปิด `"funnel"` ทำให้ทราฟฟิก HTTPS จากอินเทอร์เน็ตภายนอกเข้ามาถึงพอร์ตที่เปิดไว้ได้โดยไม่ต้องอยู่ใน Tailnet ด้วยเหตุนี้ `ai-mcp-gateway` จึงบังคับใช้ OAuth 2.1 Bearer Token บน `/mcp` และบล็อกหน้าควบคุม `/ui` ไม่ให้เปิดจากภายนอกได้เด็ดขาดครับ
4. **ทดสอบว่าพร้อมใช้งาน**
   ```powershell
   tailscale status
   ```
   ตรวจสอบว่าเครื่องของคุณแสดงสถานะออนไลน์ และหลังจากเปิด `ai-mcp-gateway` แล้ว สามารถตรวจการแมปพอร์ตด้วย:
   ```powershell
   tailscale funnel status
   ```
   จะเห็นว่า `https://<your-node>.ts.net` ชี้มายัง `http://127.0.0.1:3000` แล้ว

---

## 4. การปิด Funnel หรือใช้งานเฉพาะในเครื่อง (Local-Only)

### ปิด Tailscale Funnel ด้วยตนเอง
เนื่องจากคำสั่ง `tailscale funnel --bg 3000` ทำงานค้างใน Tailscale Daemon เบื้องหลังแม้ปิดหน้าต่างโปรแกรมไปแล้ว หากต้องการปิดไม่ให้พอร์ต `3000` ออกสู่ภายนอก ให้รันคำสั่ง:
```powershell
tailscale funnel 3000 off
```
*(หรือล้างกฎทั้งหมดด้วย `tailscale funnel reset`)*

### โหมดไม่ใช้ Tailscale (ทดสอบเฉพาะในเครื่อง)
หากเครื่องยังไม่ได้ติดตั้ง Tailscale หรือต้องการให้โปรแกรม/IDE ภายในเครื่องเดียวกันเรียกผ่าน `localhost` เท่านั้น:
1. แก้ไฟล์ `config/config.yaml`:
   ```yaml
   server:
     enable_tailscale_funnel: false
   ```
2. เปิดโปรแกรมใหม่ Endpoint จะเป็น `http://localhost:3000/mcp` แทน

---

## 5. การแก้ปัญหา Tailscale ที่พบบ่อย

| ข้อความที่พบในเทอร์มินัล | สาเหตุ | วิธีแก้ไข |
| :--- | :--- | :--- |
| `'tailscale' executable not found in PATH` | ยังไม่ได้ติดตั้ง Tailscale หรือ Windows ยังไม่เห็น `tailscale.exe` ใน `PATH` | ติดตั้ง Tailscale แล้วรีสตาร์ท Terminal/IDE หรือเพิ่ม `C:\Program Files\Tailscale\` ลงใน `PATH` |
| `Unable to query status` | โปรแกรม Tailscale ปิดอยู่หรือหลุดจากการล็อกอิน | เปิดแอป Tailscale ที่ System Tray มุมขวาล่างแล้ว Sign in ใหม่ |
| `DNSName unavailable; verify MagicDNS is enabled` | ยังไม่ได้เปิด **MagicDNS** ในหน้า Admin Console | เข้า Tailscale Admin -> **DNS** -> กดเปิด **MagicDNS** |
| `[Tailscale Funnel Error] ...` | ยังไม่ได้เปิด **HTTPS Certificates** หรือ **Funnel ACL** | ลองรัน `tailscale funnel --bg 3000` ใน PowerShell หนึ่งครั้ง แล้วคลิกลิงก์เปิดใช้งานที่ Tailscale แสดงขึ้นมา |
| เปิดหน้า `/ui` แล้วขึ้น `403 Forbidden` | เผลอเอาลิงก์สาธารณะ `https://<domain>/ui` มาเปิดแทน `localhost` | เปิด Dashboard จาก `http://localhost:3000/ui` บนเครื่องตัวเองเท่านั้น |
