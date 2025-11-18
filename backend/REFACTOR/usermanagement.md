# 👤 User Management Domain - Specification & Implementation Plan

**Data:** 17-18 Novembre 2025  
**Versione:** 3.0 (MVP Complete)  
**Status:** ✅ Fully Implemented and Deployed

---

## 🎯 Overview

Questo documento definisce l'implementazione del **User Domain** seguendo i principi di **Clean Architecture**, **Domain-Driven Design** e **Ports & Adapters** pattern già adottati nel progetto per i domini Meal, Activity e Nutritional Profile.

### Obiettivi Principali

1. ✅ **Clean Architecture**: Separazione domain/application/infrastructure
2. ✅ **Auth0 Integration**: OAuth2/OIDC come identity provider (no password storage)
3. ✅ **Minimal Persistence**: Solo dati app-specific (Auth0 = source of truth)
4. ✅ **GraphQL Only**: Coerenza con architettura esistente (no REST duplicati)
5. ✅ **Domain Events**: `UserCreated`, `UserAuthenticated`, `UserProfileUpdated`
6. ✅ **Secure by Default**: Authentication obbligatoria con opt-out esplicito
7. ✅ **Testing**: >80% coverage con unit/integration/e2e tests

---

## 📋 Table of Contents

1. [Architecture Overview](#architecture-overview)
2. [Domain Layer](#domain-layer)
3. [Application Layer](#application-layer)
4. [Infrastructure Layer](#infrastructure-layer)
5. [GraphQL API](#graphql-api)
6. [Auth0 Integration](#auth0-integration)
7. [Database Schema](#database-schema)
8. [Dependencies & Libraries](#dependencies--libraries)
9. [Implementation Plan](#implementation-plan)
10. [Testing Strategy](#testing-strategy)
11. [Security Considerations](#security-considerations)
12. [Deployment Checklist](#deployment-checklist)

---

## 1. Architecture Overview

### Clean Architecture Layers

```
┌─────────────────────────────────────────────┐
│          GraphQL API Layer                  │
│   (Resolvers, Types, Context)               │
├─────────────────────────────────────────────┤
│          Infrastructure Layer               │
│   (Auth0, MongoDB, JWKS Cache)              │
├─────────────────────────────────────────────┤
│          Application Layer                  │
│   (Commands, Queries, Event Handlers)       │
├─────────────────────────────────────────────┤
│          Domain Layer                       │
│   (User Entity, Value Objects, Events)      │
└─────────────────────────────────────────────┘
```

### Dependency Rule

Le dipendenze puntano SEMPRE verso il centro (Domain Layer). Il domain non conosce infrastructure/application/api.

### Bounded Context

**User Domain** gestisce:

- ✅ User identity (auth0_sub mapping)
- ✅ User preferences (app-specific settings)
- ✅ User authentication events
- ❌ Authorization/RBAC (future extension)
- ❌ User profile details (Auth0 /userinfo API)

### Project Structure

```
backend/
├── domain/
│   └── user/
│       ├── core/
│       │   ├── entities/
│       │   │   └── user.py              # User aggregate root
│       │   ├── value_objects/
│       │   │   ├── user_id.py           # UserId value object
│       │   │   ├── auth0_sub.py         # Auth0Sub value object
│       │   │   └── user_preferences.py  # UserPreferences value object
│       │   ├── events/
│       │   │   ├── user_created.py      # UserCreated event
│       │   │   ├── user_authenticated.py # UserAuthenticated event
│       │   │   └── user_updated.py      # UserProfileUpdated event
│       │   └── exceptions/
│       │       └── user_errors.py       # UserNotFound, InvalidAuth0Sub
│       └── auth/
│           └── ports/
│               └── auth_provider.py     # IAuthProvider interface
│
├── application/
│   └── user/
│       ├── commands/
│       │   ├── authenticate_user.py     # AuthenticateUserCommand
│       │   ├── update_preferences.py    # UpdatePreferencesCommand
│       │   └── deactivate_user.py       # DeactivateUserCommand
│       ├── queries/
│       │   ├── get_user.py              # GetUserQuery
│       │   └── get_authenticated_user.py # GetAuthenticatedUserQuery
│       └── event_handlers/
│           └── user_created_handler.py  # Handle UserCreated event
│
├── infrastructure/
│   └── user/
│       ├── auth0/
│       │   ├── auth0_provider.py        # Auth0AuthProvider (IAuthProvider impl)
│       │   ├── jwks_cache.py            # JWKS caching with TTL
│       │   └── token_verifier.py        # JWT verification logic
│       ├── persistence/
│       │   ├── mongodb/
│       │   │   └── user_repository.py   # MongoUserRepository
│       │   └── inmemory/
│       │       └── user_repository.py   # InMemoryUserRepository
│       └── fastapi/
│           └── middleware/
│               └── auth_middleware.py   # FastAPI auth middleware
│
└── graphql/
    ├── resolvers/
    │   └── user/
    │       ├── queries.py               # UserQueries resolver
    │       └── mutations.py             # UserMutations resolver
    └── types/
        └── user_types.py                # Strawberry UserType, UserInput
```

---

## 2. Domain Layer

### 2.1 User Entity (Aggregate Root)

```python
# domain/user/core/entities/user.py
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.value_objects.user_preferences import UserPreferences
from domain.user.core.events.user_created import UserCreated
from domain.user.core.events.user_authenticated import UserAuthenticated


@dataclass
class User:
    """User aggregate root.
    
    Represents an authenticated user in the system.
    Primary identifier is auth0_sub (Auth0 subject).
    
    Invariants:
    - auth0_sub must be unique and immutable
    - created_at cannot be in the future
    - last_authenticated_at cannot be before created_at
    """
    
    user_id: UserId
    auth0_sub: Auth0Sub
    preferences: UserPreferences
    created_at: datetime
    updated_at: datetime
    last_authenticated_at: Optional[datetime] = None
    is_active: bool = True
    _events: list = field(default_factory=list, init=False, repr=False)
    
    @staticmethod
    def create(auth0_sub: Auth0Sub, preferences: Optional[UserPreferences] = None) -> "User":
        """Factory method to create a new user.
        
        Args:
            auth0_sub: Auth0 subject identifier
            preferences: Optional user preferences (defaults to empty)
            
        Returns:
            New User instance with UserCreated event
            
        Raises:
            ValueError: If auth0_sub is invalid
        """
        now = datetime.utcnow()
        user_id = UserId.generate()
        prefs = preferences or UserPreferences.default()
        
        user = User(
            user_id=user_id,
            auth0_sub=auth0_sub,
            preferences=prefs,
            created_at=now,
            updated_at=now,
        )
        
        user._add_event(UserCreated(
            user_id=user_id,
            auth0_sub=auth0_sub,
            created_at=now,
        ))
        
        return user
    
    def authenticate(self, authenticated_at: Optional[datetime] = None) -> None:
        """Record user authentication.
        
        Updates last_authenticated_at and emits UserAuthenticated event.
        
        Args:
            authenticated_at: Timestamp of authentication (defaults to now)
        """
        auth_time = authenticated_at or datetime.utcnow()
        self.last_authenticated_at = auth_time
        self.updated_at = auth_time
        
        self._add_event(UserAuthenticated(
            user_id=self.user_id,
            auth0_sub=self.auth0_sub,
            authenticated_at=auth_time,
        ))
    
    def update_preferences(self, preferences: UserPreferences) -> None:
        """Update user preferences.
        
        Args:
            preferences: New preferences
        """
        self.preferences = preferences
        self.updated_at = datetime.utcnow()
    
    def deactivate(self) -> None:
        """Deactivate user account."""
        self.is_active = False
        self.updated_at = datetime.utcnow()
    
    def _add_event(self, event) -> None:
        """Add domain event to internal list."""
        self._events.append(event)
    
    def collect_events(self) -> list:
        """Collect and clear domain events."""
        events = self._events.copy()
        self._events.clear()
        return events
```

### 2.2 Value Objects

```python
# domain/user/core/value_objects/auth0_sub.py
from dataclasses import dataclass


@dataclass(frozen=True)
class Auth0Sub:
    """Auth0 subject identifier value object.
    
    Format: auth0|<user_id> or google-oauth2|<id> or email|<id>
    """
    
    value: str
    
    def __post_init__(self):
        if not self.value or "|" not in self.value:
            raise ValueError(f"Invalid Auth0 sub format: {self.value}")
        
        if len(self.value) > 255:
            raise ValueError("Auth0 sub too long")
    
    def __str__(self) -> str:
        return self.value


# domain/user/core/value_objects/user_preferences.py
from dataclasses import dataclass
from typing import Dict, Any


@dataclass(frozen=True)
class UserPreferences:
    """User application preferences.
    
    Stores app-specific settings (not Auth0 profile data).
    """
    
    data: Dict[str, Any]
    
    @staticmethod
    def default() -> "UserPreferences":
        """Create default empty preferences."""
        return UserPreferences(data={})
    
    def with_value(self, key: str, value: Any) -> "UserPreferences":
        """Return new preferences with updated value (immutable)."""
        new_data = self.data.copy()
        new_data[key] = value
        return UserPreferences(data=new_data)
```

### 2.3 Domain Events

```python
# domain/user/core/events/user_created.py
from dataclasses import dataclass
from datetime import datetime
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@dataclass(frozen=True)
class UserCreated:
    """Domain event: User was created."""
    
    user_id: UserId
    auth0_sub: Auth0Sub
    created_at: datetime


# domain/user/core/events/user_authenticated.py
@dataclass(frozen=True)
class UserAuthenticated:
    """Domain event: User successfully authenticated."""
    
    user_id: UserId
    auth0_sub: Auth0Sub
    authenticated_at: datetime
```

### 2.4 Repository Interface (Port)

```python
# domain/user/core/ports/user_repository.py
from abc import ABC, abstractmethod
from typing import Optional
from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub


class IUserRepository(ABC):
    """Repository interface for User aggregate."""
    
    @abstractmethod
    async def save(self, user: User) -> None:
        """Save user (create or update)."""
        pass
    
    @abstractmethod
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find user by internal ID."""
        pass
    
    @abstractmethod
    async def find_by_auth0_sub(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Find user by Auth0 subject identifier."""
        pass
    
    @abstractmethod
    async def exists(self, auth0_sub: Auth0Sub) -> bool:
        """Check if user exists."""
        pass
```

### 2.5 Auth Provider Interface (Port)

```python
# domain/user/auth/ports/auth_provider.py
from abc import ABC, abstractmethod
from typing import Dict, Any
from domain.user.core.value_objects.auth0_sub import Auth0Sub


class IAuthProvider(ABC):
    """Authentication provider interface (Auth0 abstraction)."""
    
    @abstractmethod
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token and return claims.
        
        Args:
            token: JWT access token
            
        Returns:
            Token claims (sub, email, etc.)
            
        Raises:
            InvalidTokenError: Token is invalid/expired
        """
        pass
    
    @abstractmethod
    async def get_user_info(self, auth0_sub: Auth0Sub) -> Dict[str, Any]:
        """Get user profile from Auth0 /userinfo endpoint.
        
        Args:
            auth0_sub: Auth0 subject identifier
            
        Returns:
            User profile (name, email, picture, etc.)
        """
        pass
```

---

## 3. Application Layer

### 3.1 Commands

```python
# application/user/commands/authenticate_user.py
from dataclasses import dataclass
from typing import Dict, Any
from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.ports.user_repository import IUserRepository
from domain.shared.ports.event_bus import IEventBus


@dataclass
class AuthenticateUserCommand:
    """Command: Authenticate user from JWT claims.
    
    Creates user if first login, updates last_authenticated_at otherwise.
    """
    
    repository: IUserRepository
    event_bus: IEventBus
    
    async def execute(self, claims: Dict[str, Any]) -> User:
        """Execute authentication command.
        
        Args:
            claims: JWT token claims from Auth0
            
        Returns:
            Authenticated User entity
        """
        auth0_sub = Auth0Sub(claims["sub"])
        
        # Find or create user
        user = await self.repository.find_by_auth0_sub(auth0_sub)
        
        if user is None:
            # First login - create user
            user = User.create(auth0_sub=auth0_sub)
        else:
            # Existing user - update last login
            user.authenticate()
        
        await self.repository.save(user)
        
        # Publish domain events
        for event in user.collect_events():
            await self.event_bus.publish(event)
        
        return user


# application/user/commands/update_preferences.py
@dataclass
class UpdatePreferencesCommand:
    """Command: Update user preferences."""
    
    repository: IUserRepository
    
    async def execute(self, auth0_sub: Auth0Sub, preferences_data: Dict[str, Any]) -> User:
        """Update user preferences.
        
        Args:
            auth0_sub: User identifier
            preferences_data: New preferences dictionary
            
        Returns:
            Updated User entity
            
        Raises:
            UserNotFoundError: User does not exist
        """
        from domain.user.core.value_objects.user_preferences import UserPreferences
        from domain.user.core.exceptions.user_errors import UserNotFoundError
        
        user = await self.repository.find_by_auth0_sub(auth0_sub)
        if user is None:
            raise UserNotFoundError(f"User {auth0_sub} not found")
        
        preferences = UserPreferences(data=preferences_data)
        user.update_preferences(preferences)
        
        await self.repository.save(user)
        return user
```

### 3.2 Queries

```python
# application/user/queries/get_user.py
from dataclasses import dataclass
from typing import Optional
from domain.user.core.entities.user import User
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.ports.user_repository import IUserRepository


@dataclass
class GetUserQuery:
    """Query: Get user by Auth0 subject."""
    
    repository: IUserRepository
    
    async def execute(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Get user by Auth0 subject.
        
        Args:
            auth0_sub: Auth0 subject identifier
            
        Returns:
            User entity or None if not found
        """
        return await self.repository.find_by_auth0_sub(auth0_sub)
```

---

## 4. Infrastructure Layer

### 4.1 Auth0 Provider Implementation

```python
# infrastructure/user/auth0/auth0_provider.py
import os
import aiohttp
from typing import Dict, Any
from jose import jwt, JWTError
from cachetools import TTLCache
from domain.user.auth.ports.auth_provider import IAuthProvider
from domain.user.core.value_objects.auth0_sub import Auth0Sub


class Auth0Provider(IAuthProvider):
    """Auth0 authentication provider implementation.
    
    Handles JWT verification with JWKS caching and token validation.
    """
    
    def __init__(self):
        self.domain = os.getenv("AUTH0_DOMAIN")
        self.audience = os.getenv("API_AUDIENCE")
        self.algorithms = ["RS256"]
        self.jwks_cache: TTLCache = TTLCache(maxsize=10, ttl=3600)  # 1h TTL
        
        if not self.domain or not self.audience:
            raise ValueError("AUTH0_DOMAIN and API_AUDIENCE must be set")
    
    async def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify JWT token using Auth0 JWKS.
        
        Args:
            token: JWT access token
            
        Returns:
            Decoded token claims
            
        Raises:
            InvalidTokenError: Token is invalid/expired
        """
        try:
            # Get JWKS (cached)
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            
            if kid not in self.jwks_cache:
                await self._refresh_jwks()
            
            rsa_key = self.jwks_cache.get(kid)
            if not rsa_key:
                raise ValueError(f"JWKS key {kid} not found")
            
            # Verify token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=f"https://{self.domain}/",
            )
            
            return payload
            
        except JWTError as e:
            raise InvalidTokenError(f"Token verification failed: {str(e)}")
    
    async def get_user_info(self, auth0_sub: Auth0Sub) -> Dict[str, Any]:
        """Get user profile from Auth0 Management API.
        
        Note: Requires M2M token with read:users scope.
        """
        # Implementation depends on Auth0 Management API setup
        # For now, return minimal data from token claims
        return {"sub": str(auth0_sub)}
    
    async def _refresh_jwks(self) -> None:
        """Refresh JWKS from Auth0 well-known endpoint."""
        jwks_url = f"https://{self.domain}/.well-known/jwks.json"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(jwks_url, timeout=aiohttp.ClientTimeout(total=5)) as resp:
                resp.raise_for_status()
                jwks = await resp.json()
        
        # Cache all keys by kid
        for key in jwks.get("keys", []):
            kid = key.get("kid")
            if kid:
                rsa_key = {
                    "kty": key["kty"],
                    "kid": key["kid"],
                    "use": key["use"],
                    "n": key["n"],
                    "e": key["e"],
                }
                self.jwks_cache[kid] = rsa_key


class InvalidTokenError(Exception):
    """Token verification failed."""
    pass
```

### 4.2 FastAPI Middleware

```python
# infrastructure/user/fastapi/middleware/auth_middleware.py
import os
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from typing import Optional
from domain.user.auth.ports.auth_provider import IAuthProvider


class AuthMiddleware(BaseHTTPMiddleware):
    """FastAPI authentication middleware.
    
    Verifies JWT token and populates request.state.auth_claims.
    Does NOT write to database (separation of concerns).
    
    Authentication is REQUIRED by default (secure by default).
    Use @skip_auth decorator for public endpoints.
    """
    
    def __init__(self, app, auth_provider: IAuthProvider):
        super().__init__(app)
        self.auth_provider = auth_provider
        self.auth_required = os.getenv("AUTH_REQUIRED", "true").lower() == "true"
    
    async def dispatch(self, request: Request, call_next):
        # Skip auth for health/version endpoints
        if request.url.path in ["/health", "/version"]:
            return await call_next(request)
        
        # Check if endpoint has @skip_auth marker
        if getattr(request.state, "skip_auth", False):
            return await call_next(request)
        
        # Extract token
        auth_header = request.headers.get("Authorization")
        token = self._extract_bearer_token(auth_header)
        
        if not self.auth_required and not token:
            # Development mode: allow unauthenticated requests
            request.state.auth_claims = None
            return await call_next(request)
        
        if not token:
            return JSONResponse(
                {"detail": "Missing Authorization header"},
                status_code=401
            )
        
        # Verify token
        try:
            claims = await self.auth_provider.verify_token(token)
            request.state.auth_claims = claims
        except Exception as e:
            return JSONResponse(
                {"detail": f"Invalid token: {str(e)}"},
                status_code=401
            )
        
        return await call_next(request)
    
    def _extract_bearer_token(self, auth_header: Optional[str]) -> Optional[str]:
        """Extract token from Authorization: Bearer <token> header."""
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        return auth_header.split(" ", 1)[1]
```

### 4.3 MongoDB Repository

```python
# infrastructure/user/persistence/mongodb/user_repository.py
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorCollection
from domain.user.core.entities.user import User
from domain.user.core.value_objects.user_id import UserId
from domain.user.core.value_objects.auth0_sub import Auth0Sub
from domain.user.core.ports.user_repository import IUserRepository


class MongoUserRepository(IUserRepository):
    """MongoDB implementation of IUserRepository."""
    
    def __init__(self, client: Optional[AsyncIOMotorClient] = None):
        import os
        if client is None:
            uri = os.getenv("MONGODB_URI", "mongodb://localhost:27017")
            client = AsyncIOMotorClient(uri)
        
        self._client = client
        self._db = client.get_database("nutrifit")
        self._collection: AsyncIOMotorCollection = self._db.get_collection("users")
    
    async def save(self, user: User) -> None:
        """Save user to MongoDB (upsert by auth0_sub)."""
        document = {
            "user_id": str(user.user_id),
            "auth0_sub": str(user.auth0_sub),
            "preferences": user.preferences.data,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
            "last_authenticated_at": user.last_authenticated_at,
            "is_active": user.is_active,
        }
        
        await self._collection.update_one(
            {"auth0_sub": str(user.auth0_sub)},
            {"$set": document},
            upsert=True
        )
    
    async def find_by_auth0_sub(self, auth0_sub: Auth0Sub) -> Optional[User]:
        """Find user by Auth0 subject."""
        doc = await self._collection.find_one({"auth0_sub": str(auth0_sub)})
        if not doc:
            return None
        
        return self._to_entity(doc)
    
    async def find_by_id(self, user_id: UserId) -> Optional[User]:
        """Find user by internal ID."""
        doc = await self._collection.find_one({"user_id": str(user_id)})
        if not doc:
            return None
        
        return self._to_entity(doc)
    
    async def exists(self, auth0_sub: Auth0Sub) -> bool:
        """Check if user exists."""
        count = await self._collection.count_documents(
            {"auth0_sub": str(auth0_sub)},
            limit=1
        )
        return count > 0
    
    def _to_entity(self, doc: dict) -> User:
        """Map MongoDB document to User entity."""
        from domain.user.core.value_objects.user_preferences import UserPreferences
        
        return User(
            user_id=UserId(doc["user_id"]),
            auth0_sub=Auth0Sub(doc["auth0_sub"]),
            preferences=UserPreferences(data=doc.get("preferences", {})),
            created_at=doc["created_at"],
            updated_at=doc["updated_at"],
            last_authenticated_at=doc.get("last_authenticated_at"),
            is_active=doc.get("is_active", True),
        )
```

---

## 5. GraphQL API

### 5.1 Strawberry Types

```python
# graphql/types/user_types.py
import strawberry
from typing import Optional, Dict, Any
from datetime import datetime


@strawberry.type
class UserType:
    """GraphQL type for User entity."""
    
    user_id: str
    auth0_sub: str
    preferences: strawberry.scalars.JSON
    created_at: datetime
    updated_at: datetime
    last_authenticated_at: Optional[datetime]
    is_active: bool


@strawberry.input
class UpdatePreferencesInput:
    """Input for updating user preferences."""
    
    preferences: strawberry.scalars.JSON
```

### 5.2 Resolvers

```python
# graphql/resolvers/user/queries.py
import strawberry
from typing import Optional
from strawberry.types import Info
from graphql.types.user_types import UserType
from application.user.queries.get_user import GetUserQuery
from domain.user.core.value_objects.auth0_sub import Auth0Sub


@strawberry.type
class UserQueries:
    """User domain queries."""
    
    @strawberry.field(description="Get current authenticated user")
    async def me(self, info: Info) -> Optional[UserType]:
        """Get current user from auth claims.
        
        Requires authentication (request.state.auth_claims must be set).
        
        Example:
            query {
              user {
                me {
                  userId
                  auth0Sub
                  preferences
                }
              }
            }
        """
        # Get auth claims from middleware
        request = info.context.get("request")
        auth_claims = getattr(request.state, "auth_claims", None)
        
        if not auth_claims:
            return None
        
        # Execute query
        repository = info.context.get("user_repository")
        query = GetUserQuery(repository=repository)
        
        auth0_sub = Auth0Sub(auth_claims["sub"])
        user = await query.execute(auth0_sub)
        
        if not user:
            return None
        
        return UserType(
            user_id=str(user.user_id),
            auth0_sub=str(user.auth0_sub),
            preferences=user.preferences.data,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_authenticated_at=user.last_authenticated_at,
            is_active=user.is_active,
        )


# graphql/resolvers/user/mutations.py
@strawberry.type
class UserMutations:
    """User domain mutations."""
    
    @strawberry.mutation(description="Update user preferences")
    async def update_preferences(
        self, 
        info: Info, 
        input: UpdatePreferencesInput
    ) -> UserType:
        """Update current user preferences.
        
        Requires authentication.
        
        Example:
            mutation {
              user {
                updatePreferences(input: {
                  preferences: {theme: "dark", language: "it"}
                }) {
                  userId
                  preferences
                }
              }
            }
        """
        from application.user.commands.update_preferences import UpdatePreferencesCommand
        
        # Get auth claims from middleware
        request = info.context.get("request")
        auth_claims = getattr(request.state, "auth_claims", None)
        
        if not auth_claims:
            raise Exception("Authentication required")
        
        # Execute command
        repository = info.context.get("user_repository")
        command = UpdatePreferencesCommand(repository=repository)
        
        auth0_sub = Auth0Sub(auth_claims["sub"])
        user = await command.execute(auth0_sub, input.preferences)
        
        return UserType(
            user_id=str(user.user_id),
            auth0_sub=str(user.auth0_sub),
            preferences=user.preferences.data,
            created_at=user.created_at,
            updated_at=user.updated_at,
            last_authenticated_at=user.last_authenticated_at,
            is_active=user.is_active,
        )
```

### 5.3 Schema Integration

```python
# app.py - Add to existing Query/Mutation types
@strawberry.type
class Query:
    # ... existing fields ...
    
    @strawberry.field(description="User domain queries")
    def user(self) -> UserQueries:
        """User domain queries.
        
        Example:
            query {
              user {
                me { userId preferences }
              }
            }
        """
        return UserQueries()


@strawberry.type
class Mutation:
    # ... existing fields ...
    
    @strawberry.field(description="User domain mutations")
    def user(self) -> UserMutations:
        """User domain mutations.
        
        Example:
            mutation {
              user {
                updatePreferences(input: {...}) { userId }
              }
            }
        """
        return UserMutations()
```

---

## 6. Auth0 Integration

### 6.1 Auth0 Configuration

#### Step 1: Create API in Auth0 Dashboard

1. Navigate to **Applications → APIs**
1. Click **Create API**
1. **Name**: `nutrifit-api`
1. **Identifier** (audience): `https://api.nutrifit.app`
1. **Signing Algorithm**: RS256

#### Step 2: Create Application (Mobile)

1. Navigate to **Applications → Applications**
1. Click **Create Application**
1. **Name**: `Nutrifit Mobile`
1. **Type**: Native
1. Configure:
   - **Allowed Callback URLs**: `nutrifit://callback`
   - **Allowed Logout URLs**: `nutrifit://logout`
   - **Allowed Web Origins**: (leave empty for mobile)

#### Step 3: Enable Social Connections (Optional)

1. Navigate to **Authentication → Social**
1. Enable Google, Apple, Facebook as needed
1. Configure OAuth credentials

#### Step 4: Custom Claims for Roles (Optional)

Create Auth0 Action to add roles to token:

```javascript
// Auth0 Action: Add roles to token
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://nutrifit.app/';
  const roles = event.authorization?.roles || [];
  
  // Add to access token (for API)
  api.accessToken.setCustomClaim(namespace + 'roles', roles);
  
  // Add to ID token (for client)
  api.idToken.setCustomClaim(namespace + 'roles', roles);
};
```

### 6.2 Client Authentication Flow

```mermaid
sequenceDiagram
    participant Mobile as Mobile App
    participant Auth0
    participant API as Backend API
    participant MongoDB

    Mobile->>Auth0: 1. Initiate login (Universal Login)
    Auth0-->>Mobile: 2. Access Token JWT + ID Token
    Mobile->>API: 3. GraphQL request + Bearer token
    API->>API: 4. AuthMiddleware verifies JWT
    API->>API: 5. AuthenticateUserCommand
    API->>MongoDB: 6. Upsert user (first login)
    MongoDB-->>API: 7. User saved
    API-->>Mobile: 8. GraphQL response
```

### 6.3 Token Verification Flow

```python
# Token verification happens in AuthMiddleware
# 1. Extract token from Authorization header
# 2. Fetch JWKS from Auth0 (cached 1h)
# 3. Verify signature with RSA public key
# 4. Validate audience, issuer, expiration
# 5. Populate request.state.auth_claims
# 6. Resolver executes AuthenticateUserCommand on first request
```

---

## 7. Database Schema

### 7.1 Minimal MongoDB Schema

```json
{
  "bsonType": "object",
  "required": ["user_id", "auth0_sub", "created_at", "updated_at"],
  "properties": {
    "user_id": {
      "bsonType": "string",
      "description": "Internal user UUID (generated)"
    },
    "auth0_sub": {
      "bsonType": "string",
      "description": "Auth0 subject identifier (auth0|123, google-oauth2|456)"
    },
    "preferences": {
      "bsonType": "object",
      "description": "App-specific user preferences (JSON)"
    },
    "created_at": {
      "bsonType": "date",
      "description": "User creation timestamp (UTC)"
    },
    "updated_at": {
      "bsonType": "date",
      "description": "Last update timestamp (UTC)"
    },
    "last_authenticated_at": {
      "bsonType": ["date", "null"],
      "description": "Last successful authentication (UTC)"
    },
    "is_active": {
      "bsonType": "bool",
      "description": "User account status (true = active)"
    }
  }
}
```

### 7.2 MongoDB Indexes

```javascript
// Create collection with validation
db.createCollection("users", {
  validator: { $jsonSchema: <above_schema> },
  validationLevel: "strict"
});

// Create indexes
db.users.createIndex({ auth0_sub: 1 }, { unique: true });
db.users.createIndex({ user_id: 1 }, { unique: true });
db.users.createIndex({ last_authenticated_at: -1 });
db.users.createIndex({ is_active: 1 });
```

**Rationale**:

- **auth0_sub**: Primary lookup key (unique)
- **user_id**: Internal UUID (unique)
- **last_authenticated_at**: For analytics/inactive user cleanup
- **is_active**: Filter active users

### 7.3 Why Minimal Schema?

**Auth0 is the source of truth for**:

- Email, email_verified
- Name, given_name, family_name
- Picture, locale, phone
- Roles (via custom claims)

**MongoDB stores only**:

- App-specific preferences
- Internal user_id mapping
- Activity timestamps (last_login)

**Benefits**:

- ✅ No data duplication
- ✅ GDPR compliance (delete Auth0 user = cascade delete)
- ✅ Single source of truth
- ✅ Simpler schema

---

## 8. Dependencies & Libraries

### 8.1 Required Dependencies

```toml
[project]
dependencies = [
  # ... existing dependencies ...
  
  # Auth & JWT
  "python-jose[cryptography]>=3.3.0",  # JWT + JWKS support
  "pyjwt[crypto]>=2.10.1",             # Fast JWT operations
  "cachetools>=5.5.0",                 # JWKS TTL cache
  
  # Already present (no changes needed)
  "motor>=3.7.1",                      # MongoDB async driver
  "aiohttp>=3.13.1",                   # HTTP client for JWKS
  "fastapi>=0.121.0",                  # Web framework
  "strawberry-graphql>=0.285.0",       # GraphQL
]
```

### 8.2 Why These Libraries?

#### python-jose[cryptography]

- ✅ Auth0 recommended library
- ✅ JWKS fetching built-in
- ✅ RS256 signature verification
- ✅ Mature & well-tested

#### pyjwt[crypto]

- ✅ Fast JWT decode (for header inspection)
- ✅ Standard library (fallback option)

#### cachetools

- ✅ TTL cache for JWKS (1h expiration)
- ✅ Key rotation handling
- ✅ Memory-efficient

### 8.3 Alternative: authlib

Se si preferisce una soluzione più completa:

```toml
dependencies = [
  "authlib>=1.3.2",  # OAuth2/OIDC complete client
]
```

**Vantaggi**:

- Integrated JWKS caching
- OAuth2 authorization code flow
- Token refresh automation
- Type hints

**Svantaggio**: Dipendenza più pesante (30+ packages)

---

## 9. Implementation Plan

### Phase 1: Domain Layer (Week 1)

**Tasks**:

1. ✅ Create `domain/user/core/` structure
1. ✅ Implement `User` entity with invariants
1. ✅ Create value objects: `UserId`, `Auth0Sub`, `UserPreferences`
1. ✅ Define domain events: `UserCreated`, `UserAuthenticated`
1. ✅ Define `IUserRepository` port
1. ✅ Define `IAuthProvider` port
1. ✅ Write unit tests (>90% coverage)

**Deliverables**:

- 7 files in `domain/user/`
- 50+ unit tests
- Zero infrastructure dependencies

**Validation**:

```bash
cd backend
pytest tests/unit/domain/user/ -v --cov=domain/user
# Expected: >90% coverage
```

---

### Phase 2: Infrastructure Layer (Week 2)

**Tasks**:

1. ✅ Implement `Auth0Provider` (JWKS + JWT verification)
1. ✅ Implement `MongoUserRepository`
1. ✅ Implement `InMemoryUserRepository` (for tests)
1. ✅ Create `AuthMiddleware` (FastAPI)
1. ✅ Add dependencies to `pyproject.toml`
1. ✅ Write integration tests with mocked Auth0

**Deliverables**:

- 5 files in `infrastructure/user/`
- MongoDB collection setup script
- 30+ integration tests

**Validation**:

```bash
pytest tests/integration/infrastructure/user/ -v
# Expected: All green with mocked Auth0 JWKS
```

---

### Phase 3: Application Layer (Week 2-3)

**Tasks**:

1. ✅ Implement `AuthenticateUserCommand`
1. ✅ Implement `UpdatePreferencesCommand`
1. ✅ Implement `GetUserQuery`
1. ✅ Create event handlers (if needed)
1. ✅ Write application tests

**Deliverables**:

- 5 files in `application/user/`
- 20+ application tests

**Validation**:

```bash
pytest tests/unit/application/user/ -v
```

---

### Phase 4: GraphQL API (Week 3)

**Tasks**:

1. ✅ Create Strawberry types (`UserType`, inputs)
1. ✅ Implement `UserQueries` resolver
1. ✅ Implement `UserMutations` resolver
1. ✅ Integrate with existing `Query`/`Mutation` types
1. ✅ Update GraphQL context factory
1. ✅ Write GraphQL integration tests

**Deliverables**:

- 3 files in `graphql/`
- Updated `app.py`
- 15+ GraphQL tests

**Validation**:

```bash
pytest tests/integration/graphql/user/ -v
# Test queries: user { me { ... } }
# Test mutations: user { updatePreferences(...) }
```

---

### Phase 5: Auth0 Setup & E2E (Week 4)

**Tasks**:

1. ✅ Configure Auth0 tenant (API + Application)
1. ✅ Set up Auth0 Action for custom claims
1. ✅ Create `.env.example` with Auth0 config
1. ✅ Write E2E test script with real Auth0 token
1. ✅ Update documentation

**Deliverables**:

- Auth0 tenant configured
- E2E test script: `scripts/test_user_auth_e2e.sh`
- Updated `REFACTOR/usermanagement.md`

**Validation**:

```bash
# With real Auth0 token
export AUTH0_TOKEN="eyJ..."
./scripts/test_user_auth_e2e.sh
# Expected: User created, preferences updated, me query works
```

---

### Phase 6: Deployment & Monitoring (Week 4)

**Tasks**:

1. ✅ Add Auth0 env vars to deployment config
1. ✅ Create MongoDB indexes in production
1. ✅ Enable AuthMiddleware in production
1. ✅ Add monitoring for auth failures
1. ✅ Update CI/CD pipeline

**Deliverables**:

- Deployed to production
- Monitoring dashboard
- CI/CD passing

---

## 10. Testing Strategy

### 10.1 Unit Tests (Domain Layer)

**Coverage Target**: >90%

```python
# tests/unit/domain/user/test_user_entity.py
def test_user_create_emits_user_created_event():
    """Test User.create() emits UserCreated event."""
    auth0_sub = Auth0Sub("auth0|123")
    user = User.create(auth0_sub)
    
    events = user.collect_events()
    assert len(events) == 1
    assert isinstance(events[0], UserCreated)
    assert events[0].auth0_sub == auth0_sub


def test_user_authenticate_updates_last_login():
    """Test User.authenticate() updates timestamp."""
    user = User.create(Auth0Sub("auth0|123"))
    assert user.last_authenticated_at is None
    
    auth_time = datetime(2025, 11, 17, 12, 0, 0)
    user.authenticate(authenticated_at=auth_time)
    
    assert user.last_authenticated_at == auth_time
    events = user.collect_events()
    assert any(isinstance(e, UserAuthenticated) for e in events)


def test_auth0_sub_validation():
    """Test Auth0Sub validates format."""
    with pytest.raises(ValueError):
        Auth0Sub("invalid")  # Missing pipe
    
    with pytest.raises(ValueError):
        Auth0Sub("a" * 300)  # Too long
    
    # Valid formats
    Auth0Sub("auth0|123")
    Auth0Sub("google-oauth2|456")
```

### 10.2 Integration Tests (Infrastructure)

```python
# tests/integration/infrastructure/user/test_auth0_provider.py
@pytest.mark.asyncio
async def test_verify_token_with_valid_jwt(mock_jwks_response):
    """Test Auth0Provider verifies valid JWT."""
    provider = Auth0Provider()
    
    # Mock JWKS endpoint
    with aioresponses() as m:
        m.get(f"https://{provider.domain}/.well-known/jwks.json", 
              payload=mock_jwks_response)
        
        # Create test JWT
        token = create_test_jwt(kid="test-key-id", 
                                audience=provider.audience)
        
        claims = await provider.verify_token(token)
        
        assert claims["sub"] == "auth0|test-user"
        assert claims["aud"] == provider.audience


@pytest.mark.asyncio
async def test_mongo_user_repository_save_and_find():
    """Test MongoUserRepository save and retrieval."""
    repo = MongoUserRepository()  # Uses test MongoDB
    
    user = User.create(Auth0Sub("auth0|test"))
    await repo.save(user)
    
    found = await repo.find_by_auth0_sub(user.auth0_sub)
    assert found is not None
    assert found.auth0_sub == user.auth0_sub
```

### 10.3 E2E Tests

```bash
# scripts/test_user_auth_e2e.sh
#!/bin/bash
set -e

echo "🧪 User Domain E2E Test"

# 1. Get Auth0 token (real or test)
TOKEN=$(curl -s -X POST "https://$AUTH0_DOMAIN/oauth/token" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id":"'$AUTH0_CLIENT_ID'",
    "client_secret":"'$AUTH0_CLIENT_SECRET'",
    "audience":"'$API_AUDIENCE'",
    "grant_type":"client_credentials"
  }' | jq -r '.access_token')

# 2. Query user (auto-creates on first request)
RESPONSE=$(curl -s -X POST http://localhost:8000/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { user { me { userId auth0Sub preferences } } }"
  }')

echo "✅ User created: $(echo $RESPONSE | jq -r '.data.user.me.userId')"

# 3. Update preferences
curl -s -X POST http://localhost:8000/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mutation { user { updatePreferences(input: {preferences: {theme: \"dark\"}}) { userId } } }"
  }'

echo "✅ Preferences updated"

# 4. Verify preferences persisted
PREFS=$(curl -s -X POST http://localhost:8000/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "query { user { me { preferences } } }"
  }' | jq -r '.data.user.me.preferences')

echo "✅ Preferences verified: $PREFS"

echo "🎉 All E2E tests passed"
```

---

## 11. Security Considerations

### 11.1 JWT Verification Checklist

- ✅ **Signature verification**: RS256 with Auth0 public key (JWKS)
- ✅ **Audience validation**: Token must match `API_AUDIENCE`
- ✅ **Issuer validation**: Token must come from `https://{AUTH0_DOMAIN}/`
- ✅ **Expiration check**: Token `exp` claim must be in future
- ✅ **JWKS caching**: Cache keys 1h, auto-refresh on rotation
- ✅ **Key rotation**: Fetch new JWKS if `kid` not in cache

### 11.2 Secure by Default

```python
# ✅ GOOD: Authentication required by default
class AuthMiddleware:
    def __init__(self, app, auth_provider: IAuthProvider):
        self.auth_required = True  # Secure default

# ❌ BAD: Authentication optional by default
class AuthMiddleware:
    def __init__(self, app, auth_provider, require_valid_token=False):
        ...  # Insecure default
```

### 11.3 GDPR Compliance

**Data Minimization**:

- Store only essential data (user_id, auth0_sub, preferences)
- Profile data (email, name, picture) in Auth0 only

**Right to be Forgotten**:

```python
# Delete user from Auth0 → cascade delete from MongoDB
async def delete_user(auth0_sub: Auth0Sub):
    # 1. Delete from Auth0 (Management API)
    await auth0_management_api.delete_user(auth0_sub)
    
    # 2. Cascade delete from MongoDB
    await user_repository.delete(auth0_sub)
    
    # 3. Publish UserDeleted event for cleanup
    await event_bus.publish(UserDeleted(auth0_sub))
```

### 11.4 Rate Limiting

Proteggere endpoint sensibili:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/graphql")
@limiter.limit("100/minute")  # 100 requests per minute per IP
async def graphql_endpoint():
    ...
```

---

## 12. Deployment Checklist

### 12.1 Environment Variables

```bash
# .env.production
# Auth0 Configuration
AUTH0_DOMAIN=nutrifit.us.auth0.com
API_AUDIENCE=https://api.nutrifit.app
AUTH_REQUIRED=true  # Enforce authentication

# MongoDB
MONGODB_URI=mongodb+srv://user:pass@cluster.mongodb.net/nutrifit?retryWrites=true&w=majority

# Feature Flags
USER_DOMAIN_ENABLED=true
```

### 12.2 Pre-Deployment Tasks

- [ ] Auth0 API created with correct audience
- [ ] Auth0 Application configured (Native, callback URLs)
- [ ] MongoDB `users` collection created with indexes
- [ ] Environment variables set in deployment platform
- [ ] JWKS endpoint reachable from backend (`https://{domain}/.well-known/jwks.json`)
- [ ] Auth0 Action deployed (if using custom claims)

### 12.3 Post-Deployment Validation

```bash
# 1. Health check
curl https://api.nutrifit.app/health
# Expected: {"status": "ok"}

# 2. GraphQL introspection
curl -X POST https://api.nutrifit.app/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "{ __schema { types { name } } }"}'
# Expected: UserType in types list

# 3. Authenticated request
curl -X POST https://api.nutrifit.app/graphql \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "query { user { me { userId } } }"}'
# Expected: User data or 401 if token invalid

# 4. Unauthenticated request (should fail)
curl -X POST https://api.nutrifit.app/graphql \
  -H "Content-Type: application/json" \
  -d '{"query": "query { user { me { userId } } }"}'
# Expected: 401 Unauthorized
```

### 12.4 Monitoring Setup

**Metrics to track**:

- Authentication success/failure rate
- JWKS cache hit rate
- User creation rate
- Token expiration errors
- MongoDB query latency

**Alerts**:

- Auth failure rate >5%
- JWKS fetch failures
- MongoDB connection errors

---

## 13. Future Extensions

### 13.1 RBAC (Role-Based Access Control)

```python
# domain/user/auth/value_objects/role.py
@dataclass(frozen=True)
class Role:
    """User role value object."""
    name: str
    permissions: List[str]

# Usage in resolver
@strawberry.field
async def admin_only_query(self, info: Info) -> str:
    user = await get_current_user(info)
    if "admin" not in user.roles:
        raise PermissionError("Admin role required")
    return "Secret data"
```

### 13.2 Audit Logging

```python
# domain/user/core/events/user_profile_updated.py
@dataclass(frozen=True)
class UserProfileUpdated:
    user_id: UserId
    changed_fields: Dict[str, Any]
    changed_by: UserId
    changed_at: datetime

# Event handler writes to audit collection
class AuditLogHandler:
    async def handle(self, event: UserProfileUpdated):
        await audit_collection.insert_one({
            "event_type": "USER_PROFILE_UPDATED",
            "user_id": str(event.user_id),
            "changes": event.changed_fields,
            "timestamp": event.changed_at,
        })
```

### 13.3 Social Login Analytics

Track authentication methods:

```python
# application/user/commands/authenticate_user.py
async def execute(self, claims: Dict[str, Any]) -> User:
    auth0_sub = Auth0Sub(claims["sub"])
    provider = auth0_sub.value.split("|")[0]  # "google-oauth2", "auth0", etc.
    
    # Track provider usage
    await analytics.track("user_authenticated", {
        "provider": provider,
        "user_id": str(user.user_id),
    })
```

---

## 14. Summary & Next Steps

### Key Achievements

✅ **Clean Architecture compliant**: Domain/Application/Infrastructure separation  
✅ **Secure by default**: Authentication required, JWKS caching, secure token verification  
✅ **Minimal persistence**: Only app-specific data in MongoDB  
✅ **GraphQL only**: No REST duplication, consistent API  
✅ **Domain events**: Extensible event-driven architecture  
✅ **Testable**: >80% coverage target, unit/integration/e2e tests  

### Implementation Timeline

- **Week 1**: Domain layer (entities, value objects, ports)
- **Week 2**: Infrastructure (Auth0 provider, MongoDB repository, middleware)
- **Week 3**: Application + GraphQL (commands, queries, resolvers)
- **Week 4**: Auth0 setup + E2E testing + deployment

### Getting Started

1. Read this document completely
1. Review existing domain implementations (Meal, Activity, Nutritional Profile)
1. Start with Phase 1 (Domain Layer)
1. Write tests first (TDD approach)
1. Validate each phase before moving to next

---
