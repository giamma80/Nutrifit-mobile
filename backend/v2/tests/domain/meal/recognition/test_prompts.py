"""
Tests for recognition prompts.

Test prompt building and message formatting.
"""

from v2.domain.meal.recognition.prompts import (
    build_vision_messages,
    build_text_extraction_messages,
    VISION_SYSTEM_PROMPT,
    TEXT_EXTRACTION_SYSTEM_PROMPT,
    VISION_OUTPUT_SCHEMA,
    TEXT_EXTRACTION_OUTPUT_SCHEMA,
)


class TestPrompts:
    """Test prompt builders."""

    def test_vision_system_prompt_exists(self) -> None:
        """Test vision system prompt is defined."""
        assert VISION_SYSTEM_PROMPT
        assert "food recognition" in VISION_SYSTEM_PROMPT.lower()
        assert "USDA" in VISION_SYSTEM_PROMPT

    def test_text_extraction_system_prompt_exists(self) -> None:
        """Test text extraction system prompt is defined."""
        assert TEXT_EXTRACTION_SYSTEM_PROMPT
        assert "extract" in TEXT_EXTRACTION_SYSTEM_PROMPT.lower()
        assert "USDA" in TEXT_EXTRACTION_SYSTEM_PROMPT

    def test_vision_output_schema_structure(self) -> None:
        """Test vision output schema has required fields."""
        assert "items" in VISION_OUTPUT_SCHEMA["properties"]
        assert "image_url" in VISION_OUTPUT_SCHEMA["properties"]

    def test_text_extraction_output_schema_structure(self) -> None:
        """Test text extraction output schema has required fields."""
        assert "items" in TEXT_EXTRACTION_OUTPUT_SCHEMA["properties"]
        assert "dish_name" in TEXT_EXTRACTION_OUTPUT_SCHEMA["properties"]

    def test_build_vision_messages_without_hint(self) -> None:
        """Test building vision messages without hint."""
        image_url = "https://example.com/meal.jpg"
        messages = build_vision_messages(image_url)

        # Should have system and user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # System message should be text only (cacheable)
        assert messages[0]["content"] == VISION_SYSTEM_PROMPT

        # User message should have text and image
        user_content = messages[1]["content"]
        assert isinstance(user_content, list)
        assert len(user_content) == 2

        # Text part
        assert user_content[0]["type"] == "text"

        # Image part
        assert user_content[1]["type"] == "image_url"
        assert user_content[1]["image_url"]["url"] == image_url
        assert user_content[1]["image_url"]["detail"] == "high"

    def test_vision_messages_with_hint(self) -> None:
        """Test building vision messages with hint."""
        image_url = "https://example.com/meal.jpg"
        hint = "pasta"
        messages = build_vision_messages(image_url, hint)

        # Should have system and user messages
        assert len(messages) == 2

        # User text should mention hint
        user_content = messages[1]["content"]
        text_part = user_content[0]["text"]
        assert "pasta" in text_part.lower()

    def test_build_text_extraction_messages(self) -> None:
        """Test building text extraction messages."""
        description = "I ate pasta and chicken"
        messages = build_text_extraction_messages(description)

        # Should have system and user messages
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

        # System message should be text only (cacheable)
        assert messages[0]["content"] == TEXT_EXTRACTION_SYSTEM_PROMPT

        # User message should contain description
        assert description in messages[1]["content"]

    def test_vision_messages_structure_for_caching(self) -> None:
        """Test vision messages are structured for OpenAI caching."""
        messages = build_vision_messages("https://example.com/meal.jpg")

        # System message should be simple string (cacheable)
        assert isinstance(messages[0]["content"], str)

        # User message can be complex (not cached)
        assert isinstance(messages[1]["content"], list)

    def test_text_messages_structure_for_caching(self) -> None:
        """Test text messages are structured for OpenAI caching."""
        messages = build_text_extraction_messages("pasta and salad")

        # System message should be simple string (cacheable)
        assert isinstance(messages[0]["content"], str)

        # User message should be simple string (not cached)
        assert isinstance(messages[1]["content"], str)
