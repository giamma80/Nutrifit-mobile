"""Unit tests for image upload REST API endpoint."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from fastapi import UploadFile

from api.upload import (
    upload_image,
    validate_file,
    generate_unique_filename,
    get_supabase_client,
    MAX_FILE_SIZE,
)


@pytest.mark.asyncio
async def test_generate_unique_filename():
    """Test unique filename generation."""
    filename1 = generate_unique_filename("test.jpg", "user123")
    filename2 = generate_unique_filename("test.jpg", "user123")

    # Should be different (timestamp + hash)
    assert filename1 != filename2

    # Should preserve extension (always .jpg after conversion)
    assert filename1.endswith(".jpg")
    assert filename2.endswith(".jpg")

    # Should include user_id in path
    assert filename1.startswith("user123/")
    assert filename2.startswith("user123/")

    # Should have expected format: user_id/YYYYMMDD_HHMMSS_hash_name.ext
    parts = filename1.split("/")[1].split("_")
    assert len(parts) >= 3  # timestamp, hash, name


@pytest.mark.asyncio
async def test_validate_file_valid_jpeg():
    """Test validation with valid JPEG file."""
    mock_file = Mock(spec=UploadFile)
    mock_file.content_type = "image/jpeg"
    mock_file.filename = "test.jpg"

    # Should not raise
    validate_file(mock_file)


@pytest.mark.asyncio
async def test_validate_file_valid_png():
    """Test validation with valid PNG file."""
    mock_file = Mock(spec=UploadFile)
    mock_file.content_type = "image/png"
    mock_file.filename = "test.png"

    # Should not raise
    validate_file(mock_file)


@pytest.mark.asyncio
async def test_validate_file_invalid_content_type():
    """Test validation fails for invalid content type."""
    mock_file = Mock(spec=UploadFile)
    mock_file.content_type = "application/pdf"
    mock_file.filename = "test.pdf"

    with pytest.raises(Exception) as exc_info:
        validate_file(mock_file)

    assert "Invalid file type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_validate_file_invalid_extension():
    """Test validation fails for invalid extension."""
    mock_file = Mock(spec=UploadFile)
    mock_file.content_type = "image/jpeg"
    mock_file.filename = "test.exe"

    with pytest.raises(Exception) as exc_info:
        validate_file(mock_file)

    assert "Invalid file extension" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_supabase_client_missing_credentials(monkeypatch):
    """Test Supabase client creation fails without credentials."""
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_KEY", raising=False)

    with pytest.raises(RuntimeError) as exc_info:
        get_supabase_client()

    assert "SUPABASE_URL and SUPABASE_KEY" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_supabase_client_success(monkeypatch):
    """Test Supabase client creation with valid credentials."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    with patch("api.upload.create_client") as mock_create:
        mock_client = Mock()
        mock_create.return_value = mock_client

        client = get_supabase_client()

        mock_create.assert_called_once_with("https://test.supabase.co", "test-key")
        assert client == mock_client


@pytest.mark.asyncio
async def test_upload_image_success(monkeypatch):
    """Test successful image upload."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")
    monkeypatch.setenv("SUPABASE_BUCKET", "test-bucket")

    # Create mock file
    content = b"fake image content"
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read = AsyncMock(return_value=content)

    # Mock Supabase client
    mock_bucket = MagicMock()
    mock_client = MagicMock()

    mock_client.storage.from_.return_value = mock_bucket
    mock_bucket.upload.return_value = {"path": "uploaded.jpg"}
    mock_bucket.get_public_url.return_value = (
        "https://test.supabase.co/storage/v1/object/public/test-bucket/test.jpg"  # noqa: E501
    )

    with patch("api.upload.get_supabase_client", return_value=mock_client):
        with patch("api.upload.convert_to_jpeg", return_value=content):
            result = await upload_image(user_id="user123", file=mock_file)

        assert result.url.startswith("https://test.supabase.co")
        assert result.content_type == "image/jpeg"
        assert result.size == len(content)
        assert result.filename.endswith(".jpg")


@pytest.mark.asyncio
async def test_upload_image_file_too_large(monkeypatch):
    """Test upload fails for file exceeding size limit."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    # Create mock file larger than MAX_FILE_SIZE
    large_content = b"x" * (MAX_FILE_SIZE + 1)
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "large.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read = AsyncMock(return_value=large_content)

    with pytest.raises(Exception) as exc_info:
        await upload_image(user_id="user123", file=mock_file)

    error_str = str(exc_info.value).lower()
    assert "413" in str(exc_info.value) or "too large" in error_str


@pytest.mark.asyncio
async def test_upload_image_invalid_type(monkeypatch):
    """Test upload fails for invalid file type."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    # Create mock PDF file
    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "document.pdf"
    mock_file.content_type = "application/pdf"
    mock_file.read = AsyncMock(return_value=b"fake pdf")

    with pytest.raises(Exception) as exc_info:
        await upload_image(user_id="user123", file=mock_file)

    assert "Invalid file type" in str(exc_info.value)


@pytest.mark.asyncio
async def test_upload_image_supabase_error(monkeypatch):
    """Test upload handles Supabase errors."""
    monkeypatch.setenv("SUPABASE_URL", "https://test.supabase.co")
    monkeypatch.setenv("SUPABASE_KEY", "test-key")

    mock_file = MagicMock(spec=UploadFile)
    mock_file.filename = "test.jpg"
    mock_file.content_type = "image/jpeg"
    mock_file.read = AsyncMock(return_value=b"fake image")

    mock_client = MagicMock()
    mock_client.storage.from_.side_effect = Exception("Storage error")

    with patch("api.upload.get_supabase_client", return_value=mock_client):
        with patch("api.upload.convert_to_jpeg", return_value=b"fake image"):
            with pytest.raises(Exception) as exc_info:
                await upload_image(user_id="user123", file=mock_file)

            error_str = str(exc_info.value)
            assert "500" in error_str or "Upload failed" in error_str
