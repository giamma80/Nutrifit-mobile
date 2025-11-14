# MongoDB Index Setup Script

Script per creare tutti gli indici MongoDB necessari per ottimizzare le performance delle query del backend Nutrifit.

## 📋 Indici Creati

### 1. **meals** Collection
- `idx_user_created`: (user_id, created_at DESC) - Per listing pasti ordinati per data
- `idx_user_date`: (user_id, meal_date) - Per query su date specifiche
- `idx_meal_date`: (meal_date) - Per range queries su date

### 2. **nutritional_profiles** Collection
- `idx_user_unique`: (user_id) UNIQUE - Un profilo per utente

### 3. **activity_events** Collection
- `idx_user_ts`: (user_id, ts ASC) - Per range queries su timestamp
- `idx_user`: (user_id) - Per query generiche utente

### 4. **health_snapshots** Collection
- `idx_user_date_ts_asc`: (user_id, date, timestamp ASC) - Per query delta in ordine cronologico
- `idx_user_date_ts_desc`: (user_id, date, timestamp DESC) - Per ottenere l'ultimo snapshot
- `idx_user_date`: (user_id, date) - Per aggregazioni giornaliere

## 🚀 Utilizzo

### Requisiti
- MongoDB URI configurato in `.env`
- Database MongoDB esistente

### Esecuzione

```bash
# Dalla directory backend/
uv run python scripts/setup_mongodb_indexes.py
```

### Variabili d'Ambiente

```bash
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/?retryWrites=true&w=majority
MONGODB_DATABASE=nutrifit  # default se non specificato
```

## 📊 Output

Lo script:
1. ✅ Si connette a MongoDB
2. ✅ Crea tutti gli indici (in background mode)
3. ✅ Verifica gli indici esistenti
4. ✅ Mostra un riepilogo completo

Esempio output:
```
============================================================
MongoDB Index Setup for Nutrifit Backend
============================================================

Connecting to MongoDB: nutrifit
✓ Connected to MongoDB successfully

Creating indexes for 'meals' collection...
  ✓ Created index: user_id + created_at (descending)
  ✓ Created index: user_id + meal_date
  ✓ Created index: meal_date

Creating indexes for 'nutritional_profiles' collection...
  ✓ Created unique index: user_id

Creating indexes for 'activity_events' collection...
  ✓ Created index: user_id + ts (ascending)
  ✓ Created index: user_id

Creating indexes for 'health_snapshots' collection...
  ✓ Created index: user_id + date + timestamp (ascending)
  ✓ Created index: user_id + date + timestamp (descending)
  ✓ Created index: user_id + date

✅ All indexes created successfully!

============================================================
Existing Indexes Summary
============================================================

meals:
  • _id_: [_id:1]
  • idx_user_created: [user_id:1, created_at:-1]
  • idx_user_date: [user_id:1, meal_date:1]
  • idx_meal_date: [meal_date:1]

nutritional_profiles:
  • _id_: [_id:1]
  • idx_user_unique: [user_id:1] (unique)

activity_events:
  • _id_: [_id:1]
  • idx_user_ts: [user_id:1, ts:1]
  • idx_user: [user_id:1]

health_snapshots:
  • _id_: [_id:1]
  • idx_user_date_ts_asc: [user_id:1, date:1, timestamp:1]
  • idx_user_date_ts_desc: [user_id:1, date:1, timestamp:-1]
  • idx_user_date: [user_id:1, date:1]

✓ MongoDB connection closed
```

## ⚠️ Note

- Gli indici vengono creati in **background mode** per non bloccare le operazioni
- Se un indice esiste già, MongoDB lo ignora (nessun errore)
- Gli indici `_id` sono automatici (creati da MongoDB)
- Lo script è **idempotente**: può essere eseguito più volte senza problemi

## 🔧 Troubleshooting

### Errore: "MONGODB_URI not configured"
```bash
export MONGODB_URI="mongodb+srv://..."
```

### Errore di connessione
- Verifica che l'URI sia corretto
- Controlla firewall/whitelist IP su MongoDB Atlas
- Verifica credenziali utente

### Performance lente dopo creazione indici
- Gli indici in background possono richiedere tempo per grandi collezioni
- Monitora progress: `db.currentOp()` su MongoDB shell
