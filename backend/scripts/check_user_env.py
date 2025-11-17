"""Environment variables configuration for User domain.

Required environment variables:
- AUTH0_DOMAIN: Auth0 tenant domain (e.g., dev-abc123.us.auth0.com)
- AUTH0_AUDIENCE: Auth0 API identifier (e.g., https://api.nutrifit.com)
- AUTH0_CLIENT_ID: Auth0 client ID for Management API
- AUTH0_CLIENT_SECRET: Auth0 client secret for Management API

Optional environment variables:
- AUTH_REQUIRED: Enable/disable authentication (default: true)
- MONGODB_URL: MongoDB connection string (default: mongodb://localhost:27017)
- MONGODB_DATABASE: MongoDB database name (default: nutrifit)
- USER_REPOSITORY: Repository type "inmemory" | "mongodb" (default: inmemory)
"""

import os
from pathlib import Path


def check_required_vars() -> dict[str, str]:
    """Check that all required environment variables are set.

    Returns:
        Dictionary of environment variable names to values

    Raises:
        ValueError: If required variables are missing
    """
    required: dict[str, str | None] = {
        "AUTH0_DOMAIN": os.getenv("AUTH0_DOMAIN"),
        "AUTH0_AUDIENCE": os.getenv("AUTH0_AUDIENCE"),
        "AUTH0_CLIENT_ID": os.getenv("AUTH0_CLIENT_ID"),
        "AUTH0_CLIENT_SECRET": os.getenv("AUTH0_CLIENT_SECRET"),
    }

    missing = [k for k, v in required.items() if not v]
    if missing:
        raise ValueError(
            f"Missing required environment variables: {', '.join(missing)}\n"
            "Please set them in your .env file or environment."
        )

    # All values are guaranteed non-None after the check
    return {k: v for k, v in required.items() if v is not None}


def check_optional_vars() -> dict[str, str]:
    """Check optional environment variables and return their values."""
    return {
        "AUTH_REQUIRED": os.getenv("AUTH_REQUIRED", "true"),
        "MONGODB_URL": os.getenv("MONGODB_URL", "mongodb://localhost:27017"),
        "MONGODB_DATABASE": os.getenv("MONGODB_DATABASE", "nutrifit"),
        "USER_REPOSITORY": os.getenv("USER_REPOSITORY", "inmemory"),
    }


def print_config() -> None:
    """Print current configuration (safe - no secrets)."""
    try:
        required = check_required_vars()
        optional = check_optional_vars()

        print("=== User Domain Configuration ===\n")

        print("Auth0 Settings:")
        print(f"  Domain: {required['AUTH0_DOMAIN']}")
        print(f"  Audience: {required['AUTH0_AUDIENCE']}")
        print(f"  Client ID: {required['AUTH0_CLIENT_ID'][:8]}...")
        print(f"  Client Secret: {'*' * 20}")

        print("\nApplication Settings:")
        print(f"  Auth Required: {optional['AUTH_REQUIRED']}")
        print(f"  Repository Type: {optional['USER_REPOSITORY']}")

        print("\nDatabase Settings:")
        print(f"  MongoDB URL: {optional['MONGODB_URL']}")
        print(f"  Database: {optional['MONGODB_DATABASE']}")

        print("\n✓ All required variables are set")

    except ValueError as e:
        print(f"⚠ Configuration Error: {e}")
        return


def create_env_template() -> None:
    """Create a .env.user.template file with all required variables."""
    template = """# User Domain Environment Variables
# Copy this file to .env and fill in the values

# Auth0 Configuration (Required)
AUTH0_DOMAIN=your-tenant.us.auth0.com
AUTH0_AUDIENCE=https://api.nutrifit.com
AUTH0_CLIENT_ID=your_client_id
AUTH0_CLIENT_SECRET=your_client_secret

# Application Settings (Optional)
AUTH_REQUIRED=true

# Database Settings (Optional)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=nutrifit
USER_REPOSITORY=inmemory

# Notes:
# - AUTH0_DOMAIN: Your Auth0 tenant domain (without https://)
# - AUTH0_AUDIENCE: API identifier from Auth0 dashboard
# - AUTH0_CLIENT_ID: M2M application client ID for Management API
# - AUTH0_CLIENT_SECRET: M2M application client secret
# - AUTH_REQUIRED: Set to "false" to disable authentication (development only)
# - USER_REPOSITORY: Use "mongodb" for production, "inmemory" for testing
"""

    template_path = Path(__file__).parent.parent / ".env.user.template"
    template_path.write_text(template)
    print(f"✓ Created template: {template_path}")


if __name__ == "__main__":
    print_config()
    print("\n" + "=" * 50)
    print("\nTo create a .env template:")
    print("  python -m scripts.check_user_env --create-template")

    import sys

    if "--create-template" in sys.argv:
        create_env_template()
