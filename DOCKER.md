# 🐳 Docker Setup - Nutrifit

Architettura multi-container per local development e production.

## 📁 Struttura

```
Nutrifit-mobile/
├── docker-compose.yml       # Orchestrazione containers
├── backend/
│   ├── Dockerfile           # Backend FastAPI + GraphQL
│   ├── .dockerignore
│   └── .env                 # Config backend (API keys + repository choice)
└── mongodb/
    ├── Dockerfile           # MongoDB 7.0 custom
    ├── .env                 # Credenziali MongoDB
    └── init-mongo.js        # Script inizializzazione DB
```

## ⚙️ Configurazione

### 1. Backend Configuration (`backend/.env`)

Copia da `backend/.env.example` e configura:

```bash
# API Keys
OPENAI_API_KEY=sk-proj-xxx
AI_USDA_API_KEY=xxx

# Repository choice (TUA DECISIONE!)
MEAL_REPOSITORY=inmemory              # Dev veloce, no persistenza
# MEAL_REPOSITORY=mongodb             # Production-like, persistenza completa

# MongoDB connection (se MEAL_REPOSITORY=mongodb)
MONGODB_URI=mongodb://nutrifit_app:nutrifit_app_password@mongodb:27017/nutrifit?authSource=nutrifit
```

**Nota:** Il backend sceglie automaticamente il repository basandosi su `MEAL_REPOSITORY`:
- `inmemory`: In-memory (default, veloce, dati persi al restart)
- `mongodb`: Persistenza completa (richiede container MongoDB)

### 2. MongoDB Configuration (`mongodb/.env`)

Già configurato con credenziali di default:
```bash
MONGO_INITDB_ROOT_USERNAME=nutrifit
MONGO_INITDB_ROOT_PASSWORD=nutrifit_dev_password
MONGO_INITDB_DATABASE=nutrifit
MONGO_APP_USERNAME=nutrifit_app
MONGO_APP_PASSWORD=nutrifit_app_password
```

**Modifica solo se necessario** (es. produzione).

## 🚀 Quick Start

### Opzione A: Dev con In-Memory (veloce, no DB)

```bash
# 1. Configura backend
cd backend
cp .env.example .env
# Compila OPENAI_API_KEY, AI_USDA_API_KEY
# Assicurati: MEAL_REPOSITORY=inmemory

# 2. Avvia solo backend
make docker-up  # oppure: cd .. && docker-compose up backend
```

Backend disponibile: http://localhost:8000

### Opzione B: Full Stack con MongoDB (production-like)

```bash
# 1. Configura backend per MongoDB
cd backend
cp .env.example .env
# Compila API keys + imposta:
# MEAL_REPOSITORY=mongodb
# MONGODB_URI=mongodb://nutrifit_app:nutrifit_app_password@mongodb:27017/nutrifit?authSource=nutrifit

# 2. Avvia stack completo
cd ..
make docker-up  # oppure: docker-compose up -d
```

Stack completo:
- Backend: http://localhost:8000
- MongoDB: localhost:27017

## 📝 Comandi Utili

```bash
# Avvia stack
make docker-up
docker-compose up -d

# Stop stack
make docker-down
docker-compose down

# Logs
make docker-logs-all
docker-compose logs -f backend
docker-compose logs -f mongodb

# Status containers
make docker-ps
docker-compose ps

# MongoDB shell
make docker-mongo-shell
docker-compose exec mongodb mongosh -u nutrifit_app -p nutrifit_app_password --authenticationDatabase nutrifit

# Rebuild (dopo modifiche Dockerfile)
docker-compose build
docker-compose up -d --build

# Reset completo (ATTENZIONE: cancella dati!)
docker-compose down -v  # -v rimuove volumes
```

## 🔄 Hot Reload

Il backend è montato come volume read-only in development:

```yaml
volumes:
  - ./backend:/app:ro
```

**Modifiche al codice Python** → riavvio automatico (uvicorn --reload)

## 🗄️ Persistenza MongoDB

Dati salvati in Docker volumes:
- `mongodb_data`: Database MongoDB
- `mongodb_config`: Config MongoDB

**Persistono tra restart** a meno che non usi `docker-compose down -v`

## 🧪 Test Setup

```bash
# Test backend con in-memory
cd backend
MEAL_REPOSITORY=inmemory ./make.sh test

# Test backend con MongoDB
docker-compose up -d mongodb
MEAL_REPOSITORY=mongodb MONGODB_URI=mongodb://nutrifit_app:nutrifit_app_password@localhost:27017/nutrifit ./make.sh test
```

## 🏭 Production Notes

Per produzione:
1. Usa `mongodb/.env` con password sicure
2. Imposta `MEAL_REPOSITORY=mongodb` in `backend/.env`
3. Considera MongoDB Atlas invece di self-hosted
4. Remove volume mount `./backend:/app:ro` (usa solo COPY in Dockerfile)
5. Set `restart: always` nei containers

## 📚 Troubleshooting

**Backend non si connette a MongoDB:**
```bash
# Verifica MongoDB è healthy
docker-compose ps
# Deve mostrare: healthy

# Verifica credenziali
docker-compose exec mongodb mongosh -u nutrifit_app -p nutrifit_app_password --authenticationDatabase nutrifit
```

**Reset DB:**
```bash
docker-compose down -v
docker-compose up -d
```

**Rebuild da zero:**
```bash
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```
