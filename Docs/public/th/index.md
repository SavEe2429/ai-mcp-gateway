# AI Agent MCP Gateway — คู่มือการใช้งานภาษาไทย

> ภาษา: [English](../en/index.md) | **ภาษาไทย**

ยินดีต้อนรับสู่คู่มือผู้ใช้งาน `ai-mcp-gateway` (`v1.1.0`) โปรแกรมตัวกลาง (MCP Streamable HTTP
Bridge) ที่ช่วยให้ AI บนเว็บอย่าง **Google Gemini**, **Anthropic Claude**, และ **OpenAI ChatGPT**
สามารถเข้ามาอ่าน/แก้ไขไฟล์ในโฟลเดอร์ที่จำกัดไว้ (`workspace/`), รันคำสั่งเทอร์มินัล, จับภาพหน้าจอ,
และเรียกใช้ MCP Server อื่นๆ ผ่าน HTTPS (Tailscale Funnel) พร้อมระบบความปลอดภัย OAuth 2.1 + PKCE,
หน้าต่างเลือก Workspace ตอนเปิดโปรแกรม, ไฟล์ Lock กันเปิดซ้ำ และ Gitleaks CI

## คู่มือผู้ใช้งานทั้งหมด

- [คู่มือติดตั้งและเริ่มใช้งาน (Quick Start)](manual/quick-start.md): วิธีติดตั้งจากไฟล์ Windows
  `.exe` หรือรันจากซอร์สโค้ดด้วย `uv`, การตั้งค่า `config/config.yaml` และขั้นตอนการใช้งานประจำวัน
- [คู่มือการติดตั้งและทำงานของ Tailscale Funnel](manual/tailscale-setup.md):
  อธิบายเหตุผลที่โปรเจกต์ใช้ Tailscale Funnel, กลไกการทำงานอัตโนมัติใน `core/tunnel.py`, วิธีตั้งค่า
  MagicDNS + HTTPS + Funnel ACL, และการป้องกัน `/ui` จากทราฟฟิกภายนอก
- [คู่มือการใช้งาน Web Dashboard](manual/dashboard-guide.md): อธิบายทุกปุ่มในหน้าควบคุม
  `http://localhost:3000/ui` ทั้งการเลือก Workspace, สวิตช์เปิด/ปิดสิทธิ์, ระบบอนุมัติคำสั่งแบบ
  HITL, Developer Inspector, MCP Client Hub และ Security Shield
- [คู่มือเชื่อมต่อ AI (MCP Integration)](manual/mcp-integration.md): วิธีนำ URL และ OAuth
  Credentials ไปตั้งค่าใน Google Gemini, Anthropic Claude, และ OpenAI ChatGPT บนเว็บ พร้อมรายการ
  Tool ทั้งหมด

## เอกสารเพิ่มเติม

- [สารบัญ Release Notes](../release-notes/README.md)
- [เอกสารสถาปัตยกรรมสำหรับนักพัฒนา (ภาษาอังกฤษ)](../../internal/design/system-architecture.md)
