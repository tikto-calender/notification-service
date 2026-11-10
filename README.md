# TikTo Telegram Notification Service

Dedicated microservice built with **FastAPI (Python 3.11)** for delivering reminder notifications to **Telegram**.

Designed as a lightweight, decoupled notification worker for the TikTo backend:
1. **Health Check (`GET /health`)**: Queried by the backend to monitor uptime, service status, and Telegram connection state.
2. **Send Notifications (`POST /notifications`)**: Receives Task or Event payloads from the backend and dispatches formatted alerts directly to Telegram.
3. **Send Test Alerts (`POST /notifications/test`)**: Sends an immediate test message to verify the Telegram bot credentials.

---

## 🚀 Interactive API Documentation (Swagger UI)

FastAPI automatically generates an interactive API playground:
👉 **`http://localhost:8000/docs`** (Swagger UI) or **`http://localhost:8000/redoc`**

Use the **"Try it out"** button on any endpoint to send live notifications or test requests directly from your browser without needing curl or Postman.

---

## ⚙️ Environment Configuration (`.env`)

Configure the service by creating or updating `.env` in the `Notification-service` folder:

```dotenv
PORT=8000

# 1. Obtain your Bot Token from @BotFather on Telegram
TELEGRAM_BOT_TOKEN=123456789:ABCdefGhIJKlmNoPQRsTUVwxyZ

# 2. Obtain your Chat ID (user ID or group ID, e.g. via @userinfobot)
TELEGRAM_CHAT_ID=-1001234567890

# Provider metadata reported to the backend /health probe
NOTIFICATION_PROVIDER=telegram
NOTIFICATION_ACCOUNT_NAME=@tikto_bot
```

---

## 🛠️ Local Development

### Requirements
* **Python** `>= 3.11`

### 1. Install Dependencies
```bash
pip install -r requirements.txt
# Or using the ultra-fast uv package manager:
uv pip install -r requirements.txt
```

### 2. Start the Server
```bash
# Option A: Run directly with Python
python main.py

# Option B: Run via Uvicorn with hot-reload
python -m uvicorn main:app --reload --port 8000

# Option C: Run with uv
uv run uvicorn main:app --reload --port 8000
```

The service will listen on `http://localhost:8000`.

---

## 📡 API Endpoints

| Method | Endpoint | Description | Sample Request Body |
| :--- | :--- | :--- | :--- |
| `GET` | `/health` | Health and provider status probe for Backend / Kubernetes | *None* |
| `POST` | `/notifications` | Dispatches task/event reminders to Telegram | `{"message": "Sprint planning meeting", "scheduledAt": "2026-11-08T09:00:00Z"}` |
| `POST` | `/notifications/test` | Sends an immediate test alert to Telegram | `{"message": "TikTo test notification"}` |
| `GET` | `/notifications` | Retrieves recently processed notifications | *None* |
| `DELETE` | `/notifications/{id}` | Cancels a notification by ID | *None* |

---

## 🧪 Testing

```bash
# Run unit tests with coverage
python -m unittest discover --start-directory test --verbose
```

---

## 🐳 Docker Deployment

```bash
# 1. Build Docker image
docker build -t tikto-notification .

# 2. Run container with Telegram credentials
docker run -p 8000:8000 \
  -e TELEGRAM_BOT_TOKEN="your_token" \
  -e TELEGRAM_CHAT_ID="your_chat_id" \
  tikto-notification
```
