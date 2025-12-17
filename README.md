# LINE AI Chatbot

ระบบแชทบอท AI ที่รองรับหลาย LLM providers พร้อม LINE integration และระบบ RAG (Retrieval-Augmented Generation)

## Features

- **Multi-LLM Support** - รองรับหลาย LLM providers:
  - Ollama (Local models)
  - OpenAI GPT (gpt-4o-mini, gpt-4, etc.)
  - Google Gemini
  - DeepSeek

- **LINE Integration** - เชื่อมต่อกับ LINE Messaging API

- **RAG System** - อัปโหลดเอกสารเพื่อใช้เป็นข้อมูลอ้างอิง
  - รองรับไฟล์: PDF, DOCX, TXT, MD, JSON, CSV
  - Vector store ด้วย ChromaDB
  - Embedding ด้วย HuggingFace

- **Web UI** - หน้าเว็บสำหรับใช้งาน
  - หน้า Chat
  - หน้าจัดการเอกสาร
  - หน้า Settings

## Project Structure

```
lineAI/
├── app/
│   ├── api/              # API routes
│   │   └── routes.py
│   ├── core/             # Configuration
│   │   └── config.py
│   ├── llm/              # LLM providers
│   │   ├── base.py
│   │   ├── ollama_llm.py
│   │   ├── openai_llm.py
│   │   ├── gemini_llm.py
│   │   ├── deepseek_llm.py
│   │   └── factory.py
│   ├── line/             # LINE integration
│   │   └── line_handler.py
│   ├── models/           # Pydantic schemas
│   │   └── schemas.py
│   ├── rag/              # RAG system
│   │   ├── document_processor.py
│   │   ├── vector_store.py
│   │   └── rag_service.py
│   └── utils/
├── static/               # Static files (CSS, JS)
│   ├── css/
│   └── js/
├── templates/            # HTML templates
├── uploads/              # Uploaded documents
├── chroma_db/            # Vector database
├── main.py               # Application entry point
├── requirements.txt
├── .env.example
└── README.md
```

## Installation

### 1. Clone และสร้าง Virtual Environment

```bash
cd D:\Projects\AI\lineAI
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/Mac
source venv/bin/activate
```

### 2. ติดตั้ง Dependencies

```bash
pip install -r requirements.txt

# ติดตั้ง packages เพิ่มเติม (ถ้าจำเป็น)
pip install langchain-chroma langchain-huggingface
```

### 3. ตั้งค่า Environment Variables

```bash
# Copy ไฟล์ตัวอย่าง
copy .env.example .env   # Windows
cp .env.example .env     # Linux/Mac

# แก้ไขไฟล์ .env ตามต้องการ
```

### 4. รัน Server

```bash
python main.py
```

Server จะรันที่ `http://localhost:8000`

## Configuration (.env)

```env
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=true

# LINE (ถ้าต้องการใช้ LINE integration)
LINE_CHANNEL_SECRET=your_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_access_token

# OpenAI
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# Google Gemini
GOOGLE_API_KEY=your_google_api_key
GEMINI_MODEL=gemini-pro

# DeepSeek
DEEPSEEK_API_KEY=your_deepseek_api_key
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
DEEPSEEK_MODEL=deepseek-chat

# Ollama (Local)
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# Default Provider
DEFAULT_LLM_PROVIDER=openai

# RAG
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHROMA_PERSIST_DIR=./chroma_db
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## Usage

### Web UI

เปิด browser ไปที่ `http://localhost:8000`

- **Chat** - แชทกับ AI, เลือก provider, เปิด/ปิด RAG
- **Documents** - อัปโหลดและจัดการเอกสารสำหรับ RAG
- **Settings** - ตั้งค่า default provider และ system prompt

### API Endpoints

#### Chat
```bash
# ส่งข้อความ
POST /api/v1/chat
{
  "message": "สวัสดี",
  "provider": "openai",
  "use_rag": false
}

# Streaming response
POST /api/v1/chat/stream
```

#### RAG / Documents
```bash
# อัปโหลดเอกสาร
POST /api/v1/rag/upload
Content-Type: multipart/form-data
file: <your_file>

# Query เอกสาร
POST /api/v1/rag/query
{
  "query": "คำถามของคุณ",
  "top_k": 5
}

# ดูรายการเอกสาร
GET /api/v1/rag/documents

# ลบเอกสาร
DELETE /api/v1/rag/documents/{filename}
```

#### System
```bash
# Health check
GET /api/v1/health

# ดู providers ที่ใช้ได้
GET /api/v1/providers

# ดู models ของ provider
GET /api/v1/providers/{provider}/models
```

#### LINE Webhook
```bash
POST /api/v1/webhook/line
```

### LINE Commands

เมื่อแชทผ่าน LINE สามารถใช้คำสั่งได้:

| Command | Description |
|---------|-------------|
| `/help` | แสดงคำสั่งทั้งหมด |
| `/clear` | ล้างประวัติการสนทนา |
| `/rag on` | เปิดใช้ RAG |
| `/rag off` | ปิดใช้ RAG |
| `/provider ollama` | เปลี่ยนเป็น Ollama |
| `/provider openai` | เปลี่ยนเป็น OpenAI |
| `/provider gemini` | เปลี่ยนเป็น Gemini |
| `/provider deepseek` | เปลี่ยนเป็น DeepSeek |
| `/docs` | แสดงรายการเอกสารที่อัปโหลด |

## LINE Setup

1. สร้าง LINE Messaging API channel ที่ [LINE Developers Console](https://developers.line.biz/)

2. เปิด Messaging API และดึง:
   - Channel Secret
   - Channel Access Token

3. ใส่ค่าใน `.env`:
   ```env
   LINE_CHANNEL_SECRET=your_channel_secret
   LINE_CHANNEL_ACCESS_TOKEN=your_access_token
   ```

4. ตั้งค่า Webhook URL ใน LINE Console:
   ```
   https://your-domain.com/api/v1/webhook/line
   ```

5. เปิด "Use webhook" และปิด "Auto-reply messages"

## Ollama Setup (Local LLM)

1. ติดตั้ง Ollama จาก [ollama.ai](https://ollama.ai/)

2. ดาวน์โหลด model:
   ```bash
   ollama pull llama2
   # หรือ models อื่น
   ollama pull mistral
   ollama pull codellama
   ```

3. Ollama จะรันที่ `http://localhost:11434`

## API Documentation

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## Troubleshooting

### ModuleNotFoundError
```bash
pip install langchain-core langchain-text-splitters langchain-chroma langchain-huggingface
```

### LINE Webhook Error
- ตรวจสอบ Channel Secret และ Access Token
- ตรวจสอบว่า Webhook URL ถูกต้องและเข้าถึงได้จากภายนอก

### Ollama Connection Error
- ตรวจสอบว่า Ollama กำลังรันอยู่: `ollama serve`
- ตรวจสอบ URL: `http://localhost:11434`

### RAG/Embedding Error
- ครั้งแรกอาจใช้เวลาโหลด embedding model
- ตรวจสอบว่ามี disk space เพียงพอ

## License

MIT License
