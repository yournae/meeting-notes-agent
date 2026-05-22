# Meeting Notes Agent

AI agent yang track action items dari meeting, dengan cross-meeting intelligence.

Upload transkrip meeting → AI extract task, owner, deadline, priority → Track across meetings.

---

## Features

- **Auto Extract** — Upload transkrip, AI deteksi task, owner, deadline, priority
- **Cross-Meeting Linking** — Otomatis hubungkan task yang berkaitan antar meeting
- **Status Detection** — Deteksi update status dari meeting baru ("kita udah selesai X")
- **Multi AI Provider** — Gemini (gratis), OpenAI, Anthropic, atau Mock Mode (tanpa API key)

---

## Quick Start

### 1. Clone & Install

```bash
git clone https://github.com/yournae/meeting-notes-agent.git
cd meeting-notes-agent

python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate

pip install -e .
```

### 2. Konfigurasi

```bash
cp .env.example .env
```

Edit `.env`:

```env
# Pilih salah satu:
MOCK_MODE=true                  # Tanpa API key, pakai regex (buat testing)
# MOCK_MODE=false              # Pakai AI beneran (butuh API key)

# Kalau MOCK_MODE=false, pilih provider + isi API key:
# AI_PROVIDER=gemini
# GEMINI_API_KEY=your_key

# Database (default SQLite, opsional)
DATABASE_URL=sqlite:///./meetings.db
```

### 3. Jalankan Server

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Server jalan di: **http://localhost:8000**

> **Catatan:** `localhost:8000` hanya bisa diakses dari komputer yang menjalankan server.
> Kalau mau diakses dari luar, deploy ke VPS (lihat bagian [Deploy ke VPS](#deploy-ke-vps)).

### 4. Test

```bash
# Health check
curl http://localhost:8000/health

# Buat meeting pertama
curl -X POST http://localhost:8000/meetings \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Sprint Planning",
    "transcript": "John: Fix login bug by Friday. Sarah: Handle database migration by Monday. Mike: Update documentation by end of week."
  }'

# Lihat semua action items
curl http://localhost:8000/action-items

# Lihat yang masih pending
curl http://localhost:8000/action-items/pending

# Update status
curl -X PATCH http://localhost:8000/action-items/1 \
  -H "Content-Type: application/json" \
  -d '{"status": "completed"}'
```

Buka **http://localhost:8000/docs** untuk interactive API documentation (Swagger UI).

---

## API Endpoints

| Method | Endpoint | Fungsi |
|--------|----------|--------|
| `GET` | `/` | Info API |
| `GET` | `/health` | Health check |
| `POST` | `/meetings` | Buat meeting + extract action items |
| `GET` | `/meetings` | List semua meeting |
| `GET` | `/meetings/{id}` | Detail meeting |
| `GET` | `/action-items` | List semua action items |
| `GET` | `/action-items/{id}` | Detail action item |
| `PATCH` | `/action-items/{id}` | Update action item |
| `GET` | `/action-items/owner/{owner}` | Items by owner |
| `GET` | `/action-items/pending` | Items yang masih pending |

---

## Cara Kerja

```
Upload transkrip meeting
        ↓
AI extract: task, owner, deadline, priority
        ↓
Cek relasi dengan action items sebelumnya
        ↓
Deteksi status update dari transkrip
        ↓
Simpan ke SQLite database
```

---

## AI Provider

Pilih di `.env`:

| Provider | Env Var | Model | Biaya |
|----------|---------|-------|-------|
| **Mock** (default) | `MOCK_MODE=true` | Regex-based | Gratis, offline |
| **Gemini** | `GEMINI_API_KEY` | gemini-pro | Gratis (free tier) |
| **OpenAI** | `OPENAI_API_KEY` | gpt-3.5-turbo | ~$0.002/meeting |
| **Anthropic** | `ANTHROPIC_API_KEY` | claude-3.5-sonnet | ~$0.015/meeting |

**Rekomendasi:** Pakai Mock Mode buat testing, Gemini buat production (gratis).

---

## Deploy ke VPS

### Opsi 1: Langsung (Development)

```bash
# SSH ke VPS
ssh user@VPS_IP

# Clone & install
git clone https://github.com/yournae/meeting-notes-agent.git
cd meeting-notes-agent
python3 -m venv venv && source venv/bin/activate
pip install -e .
cp .env.example .env && nano .env

# Jalankan
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Akses dari browser: **http://VPS_IP:8000**

> Pastikan port 8000 terbuka di firewall VPS:
> ```bash
> sudo ufw allow 8000
> ```

### Opsi 2: Dengan Nginx + Systemd (Production)

**Step 1: Setup Nginx**

```bash
sudo apt install nginx -y

sudo tee /etc/nginx/sites-available/meeting-notes << 'EOF'
server {
    listen 80;
    server_name YOUR_DOMAIN;  # atau VPS_IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/meeting-notes /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

**Step 2: Buat Systemd Service**

```bash
sudo tee /etc/systemd/system/meeting-notes.service << 'EOF'
[Unit]
Description=Meeting Notes Agent
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/home/user/meeting-notes-agent
Environment=PATH=/home/user/meeting-notes-agent/venv/bin
ExecStart=/home/user/meeting-notes-agent/venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable meeting-notes
sudo systemctl start meeting-notes
```

Akses: **http://YOUR_DOMAIN** atau **http://VPS_IP**

---

## Project Structure

```
meeting-notes-agent/
├── app/
│   ├── main.py         # FastAPI routes
│   ├── agent.py        # AI extraction logic
│   ├── models.py       # SQLAlchemy models
│   ├── schemas.py      # Pydantic schemas
│   ├── crud.py         # Database operations
│   └── database.py     # DB connection
├── tests/
│   ├── test_agent.py
│   └── test_api.py
├── demo.py             # Demo script
├── .env.example        # Config template
├── pyproject.toml      # Dependencies
└── README.md
```

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=app --cov-report=html

# Format & lint
black app/ tests/
ruff check app/ tests/
```

---

## Tech Stack

- **Backend:** FastAPI + SQLAlchemy
- **AI:** Gemini / OpenAI / Anthropic (configurable)
- **Database:** SQLite (bisa swap ke Postgres)
- **Testing:** pytest

---

## Roadmap

- [x] Core extraction & tracking
- [x] Cross-meeting relationships
- [x] Status update detection
- [ ] Linear integration
- [ ] Slack notifications
- [ ] Audio support (Whisper)
- [ ] Web UI
- [ ] Deadline reminders

---

## License

MIT
