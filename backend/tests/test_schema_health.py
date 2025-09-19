from app import schema


def test_health_field_present() -> None:
    sdl = schema.as_str()
    # Basic assertion on field presence
    assert (
        "health:" in sdl or "health: String" in sdl
    ), "Campo 'health' mancante nello schema GraphQL"
    # Optional: verify it's under Query type
    assert "type Query" in sdl
    # Ensure no accidental duplication
    assert sdl.count("health:") == 1, "Campo 'health' presente più volte inatteso"
