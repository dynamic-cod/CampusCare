import io
import os
import re
import sys
import uuid
import warnings
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile

# Guard against image decompression bombs (max 10 Megapixels)
Image.MAX_IMAGE_PIXELS = 10_000_000
warnings.filterwarnings("error", category=Image.DecompressionBombWarning)


def validate_image_magic_bytes(uploaded_file):
    """
    Inspect the raw magic bytes of the uploaded file to ensure it is strictly
    image/jpeg, image/png, or image/webp.
    Returns detected MIME type string or None if invalid.
    """
    try:
        uploaded_file.seek(0)
        header = uploaded_file.read(16)
        uploaded_file.seek(0)
        if len(header) < 4:
            return None
        # JPEG: \xff\xd8\xff
        if header.startswith(b"\xff\xd8\xff"):
            return "image/jpeg"
        # PNG: \x89PNG\r\n\x1a\n
        if header.startswith(b"\x89PNG\r\n\x1a\n"):
            return "image/png"
        # WEBP: RIFF....WEBP
        if len(header) >= 12 and header[:4] == b"RIFF" and header[8:12] == b"WEBP":
            return "image/webp"
    except Exception:
        return None
    return None


def compress_uploaded_image(uploaded_file, max_dimension=1280, quality=75):
    """
    Compress and normalize an uploaded image in-memory using Pillow.
    - Validates strict magic bytes (allow only image/jpeg, image/png, image/webp)
    - Guards against image decompression bombs via Image.MAX_IMAGE_PIXELS = 10_000_000
    - Applies EXIF orientation via ImageOps.exif_transpose
    - Converts RGBA/P/other modes to RGB
    - Resizes down to max_dimension using LANCZOS while preserving aspect ratio
    - Encodes as JPEG (~150-250KB target)
    - Strips original client filenames and assigns a randomized UUID filename
    """
    if not uploaded_file:
        return None

    # Strict MIME-type validation via magic bytes (allow only JPEG, PNG, WEBP)
    detected_mime = validate_image_magic_bytes(uploaded_file)
    if not detected_mime:
        return None

    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        # Strictly verify format matches allowed raster types
        if getattr(img, "format", None) not in ("JPEG", "PNG", "WEBP"):
            return None
        # Enforce max pixel count guard before/during load
        if (img.size[0] * img.size[1]) > Image.MAX_IMAGE_PIXELS:
            return None
        # Load pixel data to verify image integrity & enforce decompression bomb cap
        img.load()
    except Exception:
        return None

    # 1. Handle EXIF orientation
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    # 2. Convert RGBA / P / LA / other modes to RGB
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba_img = img.convert("RGBA")
        background = Image.new("RGB", rgba_img.size, (255, 255, 255))
        background.paste(rgba_img, mask=rgba_img.split()[3])
        img = background
    elif img.mode != "RGB":
        img = img.convert("RGB")

    # 3. Resize via LANCZOS if larger than max_dimension
    resample_filter = getattr(Image, "Resampling", Image).LANCZOS
    if max(img.size) > max_dimension:
        img.thumbnail((max_dimension, max_dimension), resample_filter)

    # 4. Save to JPEG buffer
    output = io.BytesIO()
    img.save(output, format="JPEG", quality=quality, optimize=True)
    output.seek(0)

    # Strip original client filename completely and store under randomized UUID filename
    new_filename = f"{uuid.uuid4().hex}.jpg"

    field_name = getattr(uploaded_file, "field_name", "image")
    return InMemoryUploadedFile(
        file=output,
        field_name=field_name,
        name=new_filename,
        content_type="image/jpeg",
        size=output.getbuffer().nbytes,
        charset=None,
    )


def get_scoped_complaints(user):
    from .permissions import get_scoped_complaints_for_user
    return get_scoped_complaints_for_user(user)


def get_scoped_complaints_for_user(user):
    from .permissions import get_scoped_complaints_for_user as _scoped
    return _scoped(user)
