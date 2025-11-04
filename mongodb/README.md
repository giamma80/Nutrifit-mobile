# MongoDB Configuration

## 🏗️ Architecture

This directory contains MongoDB setup for **local development** via Docker Compose.

For **production**, we use **MongoDB Atlas** (managed service).

## 📦 Environments

### Local Development (Docker)
- **Service**: `docker-compose.yml` mongodb service
- **Database**: `nutrifit`
- **Collections**: Created by `init-mongo.js`
- **Port**: 27017 (localhost)
- **Start**: `make docker-up` (from backend/)

### Production (Render + MongoDB Atlas)
- **Service**: MongoDB Atlas Free Tier (or paid)
- **Connection**: Via `MONGODB_URI` environment variable
- **Managed by**: render.yaml configuration

## 🚀 Production Setup (MongoDB Atlas)

### 1. Create MongoDB Atlas Cluster

1. Go to https://cloud.mongodb.com
2. Create a free cluster (M0 Sandbox - 512MB)
3. Choose region close to your Render deployment (e.g., Oregon)

### 2. Configure Network Access

**Option A - Whitelist Render IPs** (more secure):
- Add Render's outbound IP ranges to IP Whitelist
- Get IPs from: https://render.com/docs/outbound-static-ip-addresses

**Option B - Allow All** (simpler for development):
- Add `0.0.0.0/0` to IP Whitelist
- ⚠️ Ensure strong password for database user

### 3. Create Database User

1. Go to Database Access → Add New Database User
2. Username: `nutrifit_app` (or your choice)
3. Password: Generate strong password
4. Role: `readWrite` on `nutrifit` database

### 4. Get Connection String

1. Click "Connect" on your cluster
2. Choose "Connect your application"
3. Copy connection string:
   ```
   mongodb+srv://<username>:<password>@cluster0.xxxxx.mongodb.net/nutrifit?retryWrites=true&w=majority
   ```
4. Replace `<username>` and `<password>` with your credentials

### 5. Configure Render Environment Variables

In Render Dashboard (or via `render.yaml` sync):

```yaml
MONGODB_URI: mongodb+srv://nutrifit_app:YOUR_PASSWORD@cluster0.xxxxx.mongodb.net/nutrifit?retryWrites=true&w=majority
MEAL_REPOSITORY: mongodb
PROFILE_REPOSITORY: mongodb
```

⚠️ **Never commit `MONGODB_URI` to git!** Set it via Render dashboard.

## 📊 Database Schema

Collections are automatically created with schema validation:

- **meals**: User meal entries with nutritional data
- **nutritional_profiles**: User profiles with BMR/TDEE calculations
- **activity_events**: User activity tracking events

### Indexes

See `init-mongo.js` for index definitions:
- `meals`: `(user_id, timestamp)`, `meal_id` (unique)
- `nutritional_profiles`: `profile_id` (unique), `user_id`
- `activity_events`: `(user_id, timestamp)`, `(user_id, event_type)`

## 🔄 Migrations

Currently using **schema validation** in MongoDB for data integrity.

Future: Consider migration tool like:
- `mongodb-migrate`
- `migrate-mongo`
- Custom migration scripts in `backend/scripts/migrations/`

## 🧪 Testing

CI/CD uses **in-memory repository** for tests:
- Fast test execution
- No external dependencies
- Configurable via `MEAL_REPOSITORY=inmemory`

## 📝 Local Connection Strings

### Docker Compose (from host)
```
mongodb://localhost:27017/nutrifit
```

### Docker Compose (from backend container)
```
mongodb://mongodb:27017/nutrifit
```

### With Authentication (production-like)
```
mongodb://nutrifit_app:nutrifit_app_password@mongodb:27017/nutrifit?authSource=nutrifit
```

## 🔍 Monitoring

### Atlas Dashboard
- Go to Atlas dashboard → Metrics
- Monitor: Connections, Operations, Network

### Application Logs
```bash
make docker-logs  # View all container logs
```

## 🛠️ Troubleshooting

### Connection Refused
```bash
# Check MongoDB container is running
make docker-ps

# Check logs
docker logs nutrifit-mongodb
```

### Authentication Failed
```bash
# Verify credentials in mongodb/.env
cat mongodb/.env

# Test connection
docker exec nutrifit-mongodb mongosh -u nutrifit_app -p nutrifit_app_password --authenticationDatabase nutrifit
```

### Collections Not Created
```bash
# Check init script ran
docker logs nutrifit-mongodb | grep "Collections created"

# Manually run init script
docker exec nutrifit-mongodb mongosh < mongodb/init-mongo.js
```

## 📚 References

- [MongoDB Atlas Docs](https://www.mongodb.com/docs/atlas/)
- [MongoDB Connection Strings](https://www.mongodb.com/docs/manual/reference/connection-string/)
- [Render + MongoDB Atlas](https://render.com/docs/databases#mongodb-atlas)
- [Docker Compose MongoDB](https://hub.docker.com/_/mongo)
