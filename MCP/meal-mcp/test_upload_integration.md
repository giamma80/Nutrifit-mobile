# Upload Image Integration - Clear Instructions for AI Assistants

## 🚨 CRITICAL: When to Use upload_meal_image

**IF the user provides an image FILE (not a URL), you MUST:**
1. First call `upload_meal_image` with the image data
2. Then use the returned URL in `analyze_meal_photo`

**DO NOT try to encode images yourself - use the tool!**

## Overview
Il meal-mcp server supporta l'upload di immagini tramite il tool `upload_meal_image`.

## Workflow completo con upload

### 1. Upload dell'immagine
```json
{
  "tool": "upload_meal_image",
  "arguments": {
    "user_id": "user123",
    "image_data": "<base64-encoded-image>",
    "filename": "meal.jpg"
  }
}
```

**Response:**
```json
{
  "url": "https://llcqkesfwgkncxculmhf.supabase.co/storage/v1/object/public/meal-photos/user123/20251102_143022_abc123_meal.jpg",
  "filename": "user123/20251102_143022_abc123_meal.jpg",
  "size": 187432,
  "content_type": "image/jpeg"
}
```

### 2. Analisi della foto caricata
```json
{
  "tool": "analyze_meal_photo",
  "arguments": {
    "user_id": "user123",
    "photo_url": "https://llcqkesfwgkncxculmhf.supabase.co/storage/v1/object/public/meal-photos/user123/20251102_143022_abc123_meal.jpg",
    "meal_type": "LUNCH"
  }
}
```

### 3. Conferma analisi
```json
{
  "tool": "confirm_meal_analysis",
  "arguments": {
    "meal_id": "meal_abc123",
    "user_id": "user123",
    "confirmed_entry_ids": ["entry1", "entry2"]
  }
}
```

## Benefici dell'integrazione

1. **Workflow unificato**: L'AI assistant può gestire l'intero processo senza interventi esterni
2. **Conversione automatica**: Tutte le immagini vengono convertite in JPEG (85% quality)
3. **Organizzazione**: Le immagini sono organizzate per `user_id` in Supabase Storage
4. **Formato consistente**: Il path ritornato include sempre `user_id/timestamp_hash_filename.jpg`

## Requisiti di configurazione

### Backend (.env)
```bash
SUPABASE_URL=https://llcqkesfwgkncxculmhf.supabase.co
SUPABASE_KEY=eyJhbGci...
SUPABASE_BUCKET=meal-photos
```

### MCP Server
Il server deve essere raggiungibile all'endpoint REST configurato:
- Default: `http://localhost:8080/api/v1`
- Configurable via `REST_API_ENDPOINT` variable

## Note di implementazione

- Il tool usa `httpx` per chiamare il REST endpoint `/api/v1/upload-image/{user_id}`
- L'immagine viene inviata come multipart/form-data
- Il server backend gestisce validazione (max 5MB), conversione JPEG, e upload a Supabase
- Il URL ritornato è pubblico e può essere usato direttamente in `analyze_meal_photo`

## Esempio di utilizzo con Claude

```
User: "Ho appena mangiato questo piatto [carica foto]"