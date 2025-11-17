# Auth0 Integration Guide

Guida completa per integrare l'autenticazione Auth0 con il backend Nutrifit da client React, Next.js e Mobile (Flutter/React Native).

## Indice

1. [Panoramica](#panoramica)
2. [Setup Auth0](#setup-auth0)
3. [Integrazione React/Next.js](#integrazione-reactnextjs)
4. [Integrazione Mobile (Flutter)](#integrazione-mobile-flutter)
5. [Integrazione Mobile (React Native)](#integrazione-mobile-react-native)
6. [API GraphQL](#api-graphql)
7. [Testing](#testing)
8. [Troubleshooting](#troubleshooting)

---

## Panoramica

Il backend Nutrifit usa **Auth0** per l'autenticazione JWT con algoritmo **RS256**. Supporta:

- **User Authentication**: Token utente standard (`auth0|id`, `google-oauth2|id`, etc.)
- **Client Credentials (M2M)**: Token machine-to-machine per testing (`client_id@clients`)

### Architettura

```
Client (React/Mobile)
    ↓ (1) Login via Auth0
Auth0
    ↓ (2) JWT Token
Client
    ↓ (3) GraphQL Request + Bearer Token
Backend FastAPI
    ↓ (4) JWT Verification (RS256 JWKS)
    ↓ (5) GraphQL Resolvers
Database
```

### Endpoint Backend

- **GraphQL**: `https://api.nutrifit.app/graphql` (o `http://localhost:8000/graphql` in dev)
- **Health Check**: `https://api.nutrifit.app/health`

---

## Setup Auth0

### 1. Configurazione Tenant

```
Domain: dev-1grp81dl273fd86f.us.auth0.com (esempio)
Region: US
```

### 2. Creare API

1. Dashboard Auth0 → **Applications** → **APIs** → **Create API**
2. Configurazione:
   ```
   Name: Nutrifit API
   Identifier: https://api.nutrifit.app
   Signing Algorithm: RS256
   ```

### 3. Creare Application

#### Per Web App (React/Next.js)

```
Type: Single Page Application (SPA)
Name: Nutrifit Web
```

**Settings**:
```
Allowed Callback URLs: http://localhost:3000/callback, https://app.nutrifit.app/callback
Allowed Logout URLs: http://localhost:3000, https://app.nutrifit.app
Allowed Web Origins: http://localhost:3000, https://app.nutrifit.app
```

#### Per Mobile App (Flutter/React Native)

```
Type: Native
Name: Nutrifit Mobile
```

**Settings**:
```
Allowed Callback URLs: com.nutrifit.app://callback
Allowed Logout URLs: com.nutrifit.app://logout
```

### 4. Note Credenziali

```
Domain: <your-tenant>.auth0.com
Client ID: <your-client-id>
API Audience: https://api.nutrifit.app
```

---

## Integrazione React/Next.js

### Installazione

```bash
npm install @auth0/auth0-react
# oppure
pnpm add @auth0/auth0-react
```

### Setup Provider (React)

```tsx
// src/App.tsx
import { Auth0Provider } from '@auth0/auth0-react';

function App() {
  return (
    <Auth0Provider
      domain="dev-1grp81dl273fd86f.us.auth0.com"
      clientId="YOUR_CLIENT_ID"
      authorizationParams={{
        redirect_uri: window.location.origin + '/callback',
        audience: 'https://api.nutrifit.app',
        scope: 'openid profile email'
      }}
    >
      <YourApp />
    </Auth0Provider>
  );
}
```

### Setup Provider (Next.js App Router)

```tsx
// app/providers.tsx
'use client';

import { Auth0Provider } from '@auth0/auth0-react';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <Auth0Provider
      domain={process.env.NEXT_PUBLIC_AUTH0_DOMAIN!}
      clientId={process.env.NEXT_PUBLIC_AUTH0_CLIENT_ID!}
      authorizationParams={{
        redirect_uri: typeof window !== 'undefined' ? window.location.origin + '/callback' : '',
        audience: process.env.NEXT_PUBLIC_AUTH0_AUDIENCE,
      }}
    >
      {children}
    </Auth0Provider>
  );
}

// app/layout.tsx
import { Providers } from './providers';

export default function RootLayout({ children }) {
  return (
    <html>
      <body>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
```

### Environment Variables

```env
# .env.local
NEXT_PUBLIC_AUTH0_DOMAIN=dev-1grp81dl273fd86f.us.auth0.com
NEXT_PUBLIC_AUTH0_CLIENT_ID=your_client_id
NEXT_PUBLIC_AUTH0_AUDIENCE=https://api.nutrifit.app
NEXT_PUBLIC_GRAPHQL_ENDPOINT=https://api.nutrifit.app/graphql
```

### GraphQL Client con Apollo

```tsx
// src/lib/apollo-client.ts
import { ApolloClient, InMemoryCache, HttpLink, from } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import { useAuth0 } from '@auth0/auth0-react';

export function useApolloClient() {
  const { getAccessTokenSilently } = useAuth0();

  const httpLink = new HttpLink({
    uri: process.env.NEXT_PUBLIC_GRAPHQL_ENDPOINT,
  });

  const authLink = setContext(async (_, { headers }) => {
    try {
      const token = await getAccessTokenSilently();
      return {
        headers: {
          ...headers,
          authorization: token ? `Bearer ${token}` : '',
        },
      };
    } catch (error) {
      console.error('Failed to get access token:', error);
      return { headers };
    }
  });

  return new ApolloClient({
    link: from([authLink, httpLink]),
    cache: new InMemoryCache(),
  });
}

// Usage in component
function MyComponent() {
  const client = useApolloClient();
  
  return (
    <ApolloProvider client={client}>
      {/* Your GraphQL queries */}
    </ApolloProvider>
  );
}
```

### Login/Logout Components

```tsx
// components/AuthButton.tsx
import { useAuth0 } from '@auth0/auth0-react';

export function AuthButton() {
  const { isAuthenticated, loginWithRedirect, logout, user } = useAuth0();

  if (isAuthenticated) {
    return (
      <div>
        <span>Ciao, {user?.name}</span>
        <button onClick={() => logout({ logoutParams: { returnTo: window.location.origin } })}>
          Logout
        </button>
      </div>
    );
  }

  return <button onClick={() => loginWithRedirect()}>Login</button>;
}
```

### Esempio Query GraphQL

```tsx
// hooks/useCurrentUser.ts
import { gql, useQuery } from '@apollo/client';
import { useAuth0 } from '@auth0/auth0-react';

const GET_CURRENT_USER = gql`
  query GetCurrentUser {
    user {
      me {
        userId
        auth0Sub
        preferences {
          data
        }
        isActive
        createdAt
      }
    }
  }
`;

export function useCurrentUser() {
  const { isAuthenticated } = useAuth0();
  const { data, loading, error } = useQuery(GET_CURRENT_USER, {
    skip: !isAuthenticated,
  });

  return {
    user: data?.user?.me,
    loading,
    error,
  };
}

// Usage
function ProfilePage() {
  const { user, loading } = useCurrentUser();

  if (loading) return <div>Loading...</div>;
  if (!user) return <div>Please login</div>;

  return <div>Welcome {user.userId}</div>;
}
```

---

## Integrazione Mobile (Flutter)

### Installazione

```yaml
# pubspec.yaml
dependencies:
  flutter_appauth: ^6.0.0
  graphql_flutter: ^5.1.2
  flutter_secure_storage: ^9.0.0
```

### Setup Auth0 Client

```dart
// lib/services/auth_service.dart
import 'package:flutter_appauth/flutter_appauth.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

class AuthService {
  final FlutterAppAuth _appAuth = FlutterAppAuth();
  final FlutterSecureStorage _storage = FlutterSecureStorage();
  
  static const String _domain = 'dev-1grp81dl273fd86f.us.auth0.com';
  static const String _clientId = 'YOUR_CLIENT_ID';
  static const String _audience = 'https://api.nutrifit.app';
  static const String _redirectUri = 'com.nutrifit.app://callback';
  
  Future<String?> login() async {
    try {
      final AuthorizationTokenResponse? result = await _appAuth.authorizeAndExchangeCode(
        AuthorizationTokenRequest(
          _clientId,
          _redirectUri,
          serviceConfiguration: AuthorizationServiceConfiguration(
            authorizationEndpoint: 'https://$_domain/authorize',
            tokenEndpoint: 'https://$_domain/oauth/token',
          ),
          scopes: ['openid', 'profile', 'email', 'offline_access'],
          additionalParameters: {
            'audience': _audience,
          },
        ),
      );
      
      if (result != null) {
        await _storage.write(key: 'access_token', value: result.accessToken);
        await _storage.write(key: 'refresh_token', value: result.refreshToken);
        return result.accessToken;
      }
    } catch (e) {
      print('Login error: $e');
    }
    return null;
  }
  
  Future<String?> getAccessToken() async {
    return await _storage.read(key: 'access_token');
  }
  
  Future<void> logout() async {
    await _storage.deleteAll();
  }
}
```

### GraphQL Client Setup

```dart
// lib/services/graphql_service.dart
import 'package:graphql_flutter/graphql_flutter.dart';
import 'auth_service.dart';

class GraphQLService {
  final AuthService _authService = AuthService();
  
  Future<GraphQLClient> getClient() async {
    final HttpLink httpLink = HttpLink('https://api.nutrifit.app/graphql');
    
    final AuthLink authLink = AuthLink(
      getToken: () async {
        final token = await _authService.getAccessToken();
        return token != null ? 'Bearer $token' : '';
      },
    );
    
    final Link link = authLink.concat(httpLink);
    
    return GraphQLClient(
      cache: GraphQLCache(),
      link: link,
    );
  }
}
```

### Esempio Query

```dart
// lib/queries/user_queries.dart
const String getCurrentUserQuery = r'''
  query GetCurrentUser {
    user {
      me {
        userId
        auth0Sub
        preferences {
          data
        }
        isActive
      }
    }
  }
''';

// Usage
Future<void> fetchCurrentUser() async {
  final client = await GraphQLService().getClient();
  
  final QueryOptions options = QueryOptions(
    document: gql(getCurrentUserQuery),
  );
  
  final QueryResult result = await client.query(options);
  
  if (result.hasException) {
    print('Error: ${result.exception}');
    return;
  }
  
  final user = result.data?['user']?['me'];
  print('User ID: ${user['userId']}');
}
```

---

## Integrazione Mobile (React Native)

### Installazione

```bash
npm install react-native-auth0 @apollo/client graphql
# oppure
pnpm add react-native-auth0 @apollo/client graphql
```

### Setup Auth0

```tsx
// src/services/auth.ts
import Auth0 from 'react-native-auth0';

const auth0 = new Auth0({
  domain: 'dev-1grp81dl273fd86f.us.auth0.com',
  clientId: 'YOUR_CLIENT_ID',
});

export async function login() {
  try {
    const credentials = await auth0.webAuth.authorize({
      scope: 'openid profile email offline_access',
      audience: 'https://api.nutrifit.app',
    });
    return credentials.accessToken;
  } catch (error) {
    console.error('Login error:', error);
    throw error;
  }
}

export async function logout() {
  try {
    await auth0.webAuth.clearSession();
  } catch (error) {
    console.error('Logout error:', error);
  }
}
```

### GraphQL Client

```tsx
// src/lib/apollo.ts
import { ApolloClient, InMemoryCache, createHttpLink } from '@apollo/client';
import { setContext } from '@apollo/client/link/context';
import AsyncStorage from '@react-native-async-storage/async-storage';

const httpLink = createHttpLink({
  uri: 'https://api.nutrifit.app/graphql',
});

const authLink = setContext(async (_, { headers }) => {
  const token = await AsyncStorage.getItem('access_token');
  return {
    headers: {
      ...headers,
      authorization: token ? `Bearer ${token}` : '',
    },
  };
});

export const apolloClient = new ApolloClient({
  link: authLink.concat(httpLink),
  cache: new InMemoryCache(),
});
```

---

## API GraphQL

### Mutations

#### 1. Authenticate (primo login)

```graphql
mutation Authenticate {
  user {
    authenticate {
      userId
      auth0Sub
      lastAuthenticatedAt
      isActive
    }
  }
}
```

**Descrizione**: Crea l'utente nel database al primo login. Aggiorna `lastAuthenticatedAt` ai login successivi.

#### 2. Update Preferences

```graphql
mutation UpdatePreferences($preferences: UserPreferencesInput!) {
  user {
    updatePreferences(preferences: $preferences) {
      userId
      preferences {
        data
      }
      updatedAt
    }
  }
}
```

**Variabili**:
```json
{
  "preferences": {
    "data": {
      "theme": "dark",
      "language": "it",
      "notifications": true
    }
  }
}
```

#### 3. Deactivate Account

```graphql
mutation DeactivateAccount {
  user {
    deactivate {
      userId
      isActive
    }
  }
}
```

### Queries

#### 1. Current User

```graphql
query GetCurrentUser {
  user {
    me {
      userId
      auth0Sub
      preferences {
        data
      }
      isActive
      createdAt
      updatedAt
      lastAuthenticatedAt
    }
  }
}
```

#### 2. Check User Exists

```graphql
query CheckUserExists {
  user {
    exists
  }
}
```

### Headers Richiesti

```http
POST /graphql
Content-Type: application/json
Authorization: Bearer <JWT_TOKEN>
```

---

## Testing

### 1. Ottenere Token di Test (Client Credentials)

```bash
#!/bin/bash
# test_auth0.sh

curl --request POST \
  --url https://dev-1grp81dl273fd86f.us.auth0.com/oauth/token \
  --header 'content-type: application/json' \
  --data '{
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET",
    "audience": "https://api.nutrifit.app",
    "grant_type": "client_credentials"
  }'
```

### 2. Test Authenticate Mutation

```bash
TOKEN="<your-token>"

curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "mutation { user { authenticate { userId auth0Sub isActive } } }"
  }'
```

### 3. Test User Query

```bash
curl -X POST http://localhost:8000/graphql \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "query": "{ user { me { userId auth0Sub preferences { data } } } }"
  }'
```

### Script Automatico

Eseguire lo script fornito:

```bash
cd backend
./scripts/test_auth0.sh
```

Output atteso:
```
✅ Test 1: authenticate - User created
✅ Test 2: user.me - Retrieved user data
✅ Test 3: updatePreferences - Updated successfully
```

---

## Troubleshooting

### Errore: "Missing authentication"

**Causa**: Token JWT mancante o non valido nell'header `Authorization`.

**Soluzione**:
```typescript
// Verifica che il token sia presente
const headers = {
  'Authorization': `Bearer ${accessToken}`,
  'Content-Type': 'application/json'
};
```

### Errore: "Invalid token"

**Causa**: Token scaduto, firma non valida, o audience errata.

**Soluzioni**:
1. Verifica che `audience` sia `https://api.nutrifit.app`
2. Rigenera il token
3. Controlla che `domain` e `clientId` siano corretti

### Errore: "JWKS error"

**Causa**: Backend non riesce a recuperare le chiavi pubbliche da Auth0.

**Soluzione**:
- Verifica connessione internet del backend
- Controlla che `AUTH0_DOMAIN` sia configurato correttamente
- Verifica che il tenant Auth0 sia attivo

### Token Refresh (Mobile)

Per gestire il refresh automatico del token:

**Flutter**:
```dart
Future<String?> refreshToken() async {
  final refreshToken = await _storage.read(key: 'refresh_token');
  if (refreshToken == null) return null;
  
  final TokenResponse? result = await _appAuth.token(
    TokenRequest(
      _clientId,
      _redirectUri,
      serviceConfiguration: AuthorizationServiceConfiguration(
        authorizationEndpoint: 'https://$_domain/authorize',
        tokenEndpoint: 'https://$_domain/oauth/token',
      ),
      refreshToken: refreshToken,
    ),
  );
  
  if (result != null) {
    await _storage.write(key: 'access_token', value: result.accessToken);
    return result.accessToken;
  }
  return null;
}
```

**React Native**:
```typescript
async function refreshAccessToken() {
  const refreshToken = await AsyncStorage.getItem('refresh_token');
  if (!refreshToken) throw new Error('No refresh token');
  
  const credentials = await auth0.auth.refreshToken({ refreshToken });
  await AsyncStorage.setItem('access_token', credentials.accessToken);
  return credentials.accessToken;
}
```

### Query Pubbliche (senza Auth)

Alcune query possono essere pubbliche (es. `health`, `version`). Il backend ha `AUTH_REQUIRED=false` di default.

Per query che richiedono autenticazione (tutte le `user.*` queries/mutations), il token JWT è **obbligatorio**.

---

## Best Practices

### Sicurezza

1. **Non esporre Client Secret nel frontend** - Usare solo in backend/M2M
2. **Usare HTTPS in produzione** - Mai HTTP per token JWT
3. **Validare token lato server** - Mai fidarsi del client
4. **Implementare refresh token** - Migliore UX, token access brevi
5. **Logout completo** - Cancellare token da storage locale

### Performance

1. **Cache dei token** - Evitare chiamate eccessive a Auth0
2. **Apollo Cache** - Ridurre chiamate GraphQL duplicate
3. **Token Interceptor** - Gestire errori 401 centralmente

### UX

1. **Silent Authentication** - Refresh automatico senza redirect
2. **Loading States** - Feedback visivo durante login/logout
3. **Error Handling** - Messaggi chiari per l'utente
4. **Offline Support** - Cache locale per dati critici

---

## Riferimenti

- [Auth0 React SDK](https://auth0.com/docs/quickstart/spa/react)
- [Auth0 Flutter SDK](https://pub.dev/packages/flutter_appauth)
- [Auth0 React Native](https://auth0.com/docs/quickstart/native/react-native)
- [Apollo Client](https://www.apollographql.com/docs/react/)
- [GraphQL Flutter](https://pub.dev/packages/graphql_flutter)

---

**Domande o problemi?** Contattare il team backend o aprire una issue su GitHub.
