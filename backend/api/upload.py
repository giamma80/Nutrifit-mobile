"""REST API endpoint for image upload to Supabase Storage.

Provides a simple utility endpoint for uploading images (max 5MB)
to Supabase Storage bucket and returning the public URL.
"""

import os
import logging
import io
from typing import Optional
from datetime import datetime

from fastapi import APIRouter, UploadFile, File, HTTPException, Path
from pydantic import BaseModel
from supabase import create_client, Client
from PIL import Image
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# Maximum file size: 5MB
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB in bytes

# Allowed image MIME types
ALLOWED_MIME_TYPES = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}

# Allowed file extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


class UploadResponse(BaseModel):
    """Response model for successful image upload."""

    url: str
    filename: str
    size: int
    content_type: str


class ErrorResponse(BaseModel):
    """Response model for upload errors."""

    error: str
    detail: Optional[str] = None


def get_supabase_client() -> Client:
    """Get Supabase client instance.

    Raises:
        RuntimeError: If Supabase credentials are not configured.
    """
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")

    if not url or not key:
        raise RuntimeError("SUPABASE_URL and SUPABASE_KEY must be set in environment")

    return create_client(url, key)


def validate_file(file: UploadFile) -> None:
    """Validate uploaded file.

    Args:
        file: Uploaded file to validate.

    Raises:
        HTTPException: If file is invalid.
    """
    # Check content type
    if file.content_type not in ALLOWED_MIME_TYPES:
        allowed = ", ".join(ALLOWED_MIME_TYPES)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file type. Allowed: {allowed}",
        )

    # Check file extension
    if file.filename:
        ext = os.path.splitext(file.filename)[1].lower()
        if ext not in ALLOWED_EXTENSIONS:
            allowed_ext = ", ".join(ALLOWED_EXTENSIONS)
            raise HTTPException(
                status_code=400,
                detail=f"Invalid file extension. Allowed: {allowed_ext}",
            )


def generate_unique_filename(original_filename: str, user_id: str) -> str:
    """Generate a unique filename with user folder and timestamp."""
    import uuid

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    random_str = uuid.uuid4().hex[:8]
    base_name = os.path.splitext(original_filename)[0]
    safe_name = secure_filename(base_name) or "image"
    # Always use .jpg extension since we convert to JPEG
    filename = f"{timestamp}_{random_str}_{safe_name}.jpg"
    return f"{user_id}/{filename}"


router = APIRouter(prefix="/api/v1", tags=["upload"])


def convert_to_jpeg(image_data: bytes) -> bytes:
    """Convert any image format to JPEG."""
    try:
        # Open image from bytes
        img: Image.Image = Image.open(io.BytesIO(image_data))

        # Convert to RGB if necessary (PNG with transparency, etc.)
        rgb_img: Image.Image
        if img.mode in ("RGBA", "LA", "P"):
            background = Image.new("RGB", img.size, (255, 255, 255))
            if img.mode == "P":
                img = img.convert("RGBA")
            # Get alpha channel for transparency
            has_alpha = img.mode in ("RGBA", "LA")
            mask = img.split()[-1] if has_alpha else None
            background.paste(img, mask=mask)
            rgb_img = background
        elif img.mode != "RGB":
            rgb_img = img.convert("RGB")
        else:
            rgb_img = img

        # Save as JPEG
        output = io.BytesIO()
        rgb_img.save(output, format="JPEG", quality=85, optimize=True)
        return output.getvalue()
    except Exception as e:
        logger.error(f"Error converting image to JPEG: {e}")
        raise HTTPException(
            status_code=400,
            detail="Invalid image format or corrupted file",
        )


@router.post("/upload-image/{user_id}", response_model=UploadResponse)
async def upload_image(
    user_id: str = Path(..., description="User ID for organizing images"),
    file: UploadFile = File(..., description="Image file to upload"),
) -> UploadResponse:
    """Upload a meal image to Supabase Storage.

    This endpoint is designed to work with the meal analysis workflow:
    1. Upload image here to get a public URL
    2. Use that URL in analyzeMealPhoto GraphQL mutation

    The endpoint handles image processing automatically:
    - Validates file type and size (max 5MB)
    - Converts any format to optimized JPEG (quality 85)
    - Organizes files by user_id in storage
    - Returns public URL for immediate use

    Args:
        user_id: User ID for organizing images in dedicated folder
        file: Image file (any format: JPEG, PNG, WebP, GIF)

    Returns:
        UploadResponse with public URL ready for analyzeMealPhoto

    Raises:
        HTTPException: If upload fails, file is invalid, or too large

    Example:
        ```bash
        curl -X POST http://localhost:8080/api/v1/upload-image/user123 \\
          -F "file=@/path/to/image.png"
        ```

        Response:
        ```json
        {
          "url": "https://xxx.supabase.co/.../user123/20251102_a1b2c3d4_image.jpg",
          "filename": "user123/20251102_143022_a1b2c3d4_image.jpg",
          "size": 187432,
          "content_type": "image/jpeg"
        }
        ```

    Note:
        - All images are converted to JPEG (quality 85, optimized)
        - PNG transparency is preserved by compositing on white background
        - File path includes user_id for organized storage
    """
    logger.info(
        "Image upload request",
        extra={
            "user_id": user_id,
            "file_name": file.filename,
            "content_type": file.content_type,
        },
    )

    # Validate file type and extension
    validate_file(file)

    # Read file content
    content = await file.read()
    file_size = len(content)

    # Check file size (before conversion)
    if file_size > MAX_FILE_SIZE:
        logger.warning(
            "File too large",
            extra={
                "user_id": user_id,
                "size": file_size,
                "max": MAX_FILE_SIZE,
            },
        )
        max_mb = MAX_FILE_SIZE / 1024 / 1024
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {max_mb}MB",
        )

    # Convert to JPEG
    logger.info("Converting image to JPEG", extra={"user_id": user_id})
    jpeg_content = convert_to_jpeg(content)
    jpeg_size = len(jpeg_content)

    # Generate unique filename with user folder
    original_name = file.filename or "image.jpg"
    unique_filename = generate_unique_filename(original_name, user_id)

    try:
        # Get Supabase client
        supabase = get_supabase_client()

        # Bucket name (configurable via env, default: meal-images)
        bucket_name = os.getenv("SUPABASE_BUCKET", "meal-images")

        # Upload file to storage (always as JPEG)
        supabase.storage.from_(bucket_name).upload(
            path=unique_filename,
            file=jpeg_content,
            file_options={"content-type": "image/jpeg"},
        )

        # Get public URL
        storage = supabase.storage.from_(bucket_name)
        public_url = storage.get_public_url(unique_filename)

        logger.info(
            "Image uploaded successfully",
            extra={
                "user_id": user_id,
                "file_name": unique_filename,
                "original_size": file_size,
                "jpeg_size": jpeg_size,
                "url": public_url,
            },
        )

        return UploadResponse(
            url=public_url,
            filename=unique_filename,
            size=jpeg_size,
            content_type="image/jpeg",
        )

    except Exception as e:
        logger.error(
            "Image upload failed",
            extra={"file_name": file.filename, "error": str(e)},
            exc_info=True,
        )
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}") from e
