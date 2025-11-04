// MongoDB Initialization Script
// Eseguito automaticamente al primo avvio del container
// Crea database, collezioni e indici per Nutrifit

// Switch al database nutrifit
db = db.getSiblingDB('nutrifit');

// Crea application user (non-root) per sicurezza
db.createUser({
  user: process.env.MONGO_APP_USERNAME || 'nutrifit_app',
  pwd: process.env.MONGO_APP_PASSWORD || 'nutrifit_app_password',
  roles: [
    {
      role: 'readWrite',
      db: 'nutrifit'
    }
  ]
});

print('✅ Application user created: ' + (process.env.MONGO_APP_USERNAME || 'nutrifit_app'));

// Crea collezioni con schema validation (opzionale)
db.createCollection('meals', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['meal_id', 'user_id', 'timestamp'],
      properties: {
        meal_id: {
          bsonType: 'string',
          description: 'UUID del pasto'
        },
        user_id: {
          bsonType: 'string',
          description: 'ID utente proprietario'
        },
        timestamp: {
          bsonType: 'string',
          description: 'ISO8601 timestamp'
        },
        meal_type: {
          enum: ['breakfast', 'lunch', 'dinner', 'snack'],
          description: 'Tipo di pasto'
        },
        entries: {
          bsonType: 'array',
          description: 'Lista entry del pasto'
        }
      }
    }
  }
});

db.createCollection('nutritional_profiles', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['profile_id', 'user_id'],
      properties: {
        profile_id: {
          bsonType: 'string',
          description: 'UUID del profilo'
        },
        user_id: {
          bsonType: 'string',
          description: 'ID utente'
        }
      }
    }
  }
});

db.createCollection('activity_events', {
  validator: {
    $jsonSchema: {
      bsonType: 'object',
      required: ['user_id', 'ts'],
      properties: {
        user_id: {
          bsonType: 'string'
        },
        ts: {
          bsonType: 'string',
          description: 'ISO8601 timestamp'
        }
      }
    }
  }
});

print('✅ Collections created: meals, nutritional_profiles, activity_events');

// Crea indici per performance
db.meals.createIndex({ user_id: 1, timestamp: -1 });
db.meals.createIndex({ meal_id: 1 }, { unique: true });
db.nutritional_profiles.createIndex({ profile_id: 1 }, { unique: true });
db.nutritional_profiles.createIndex({ user_id: 1 });
db.activity_events.createIndex({ user_id: 1, ts: -1 });

print('✅ Indexes created successfully');
print('🚀 MongoDB initialization complete');
