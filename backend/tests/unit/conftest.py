"""Unit test configuration.

Isolates unit tests from integration test setup.
Unit tests should not depend on app.py or external services.
"""

# Empty conftest to prevent loading root conftest.py
# which has dependencies on removed modules.
