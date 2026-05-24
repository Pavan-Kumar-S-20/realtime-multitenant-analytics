# Real-Time Multi-Tenant Analytics Platform

A high-performance, real-time analytics data ingestion pipeline built using FastAPI, PostgreSQL, Redis, and Next.js. The platform implements secure row-level multi-tenant isolation, dynamic API key provision masking, and scalable event streaming hooks.

---

## 🏗️ System Architecture

* **Backend Engine:** FastAPI (Python 3.11+) utilizing asynchronous database drivers (`asyncpg` + SQLAlchemy v2).
* **Frontend Portal:** Next.js dashboard tracking analytical event counts, processing delays, and performance bar charts.
* **Storage Layers:** PostgreSQL (relational event metadata tables) and Redis (caching and rate-limiting blocks).

---

## 🛠️ Local Development Quick Start

### 1. Database Configuration
Ensure your local PostgreSQL instance is running and create an empty database named `analytics_db`:
```sql
CREATE DATABASE analytics_db;

```

### 2. Backend Installation & Server Run

Navigate to your backend repository folder, spin up a virtual environment, install dependencies, and trigger the initialization script to generate database tables:

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Reset and update database tables to latest schemas
python -m app.reset_db

# Launch the Uvicorn application server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

```

### 3. Frontend Installation & Dashboard Run

In a separate terminal tab, initialize your frontend framework dependencies and start the local development interface:

```bash
cd frontend
npm install
npm run dev

```

* Access the graphical browser dashboard at: **`http://localhost:3000`**
* Access the interactive API Swagger UI at: **`http://localhost:8000/docs`**

---

## 🏁 End-to-End API Pipeline Testing Flow

To test the system architecture from scratch without a user interface form, run these three flattened single-line commands inside your client terminal sequentially:

### Step 1: Register a New Tenant Organization

Provisions a dedicated company workspace and administrative owner row inside your PostgreSQL cluster:

```bash
curl -X POST "http://localhost:8000/api/v1/auth/signup" -H "Content-Type: application/json" -d '{"email": "admin@company.com", "password": "SecurePassword123", "org_name": "Acme Analytics Inc"}'

```

### Step 2: Authenticate and Extract Session JWT Bearer Token

Logs into the tenant node using a clean JSON profile and captures the dynamic string payload straight into a local `$TOKEN` variable environment cache:

```bash
TOKEN=$(curl -s -X POST "http://localhost:8000/api/v1/auth/login" -H "Content-Type: application/json" -d '{"email": "admin@company.com", "password": "SecurePassword123"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))") && echo "Session Token Loaded Successfully!"

```

### Step 3: Provision a Valid Multi-Tenant Ingestion API Key

Utilizes your secure `$TOKEN` credentials to construct an authorization handshake and requests an encrypted API access key stored under variable cache `$API_KEY`:

```bash
API_KEY=$(curl -s -X POST "http://localhost:8000/api/v1/events/keys" -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -d '{"name": "Production Key"}' | python3 -c "import sys, json; print(json.load(sys.stdin).get('raw_key', ''))") && echo "Your Generated Ingestion Key is: $API_KEY"

```

### Step 4: Stream High-Throughput Batch Event Logs

Simulates a live system firing an isolated array block of event structures directly into the secure data ingestion pool using your active authentication header string:

```bash
curl -X POST "http://localhost:8000/api/v1/events/ingest" -H "X-API-Key: $API_KEY" -H "Content-Type: application/json" -d '[{"event_name": "user_signup", "properties": {"plan": "enterprise"}}, {"event_name": "dashboard_load", "properties": {"browser": "chrome"}}]'

```

* **Verification Confirmation:** The terminal will instantly return a **`202 Accepted`** verification status code, and the dynamic metrics tables on your frontend UI at `http://localhost:3000` will automatically refresh with live streaming visual counts!

```

```