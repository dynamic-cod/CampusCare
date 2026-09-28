"""Image compression and multi-tenant scoping utilities for CampusCare."""
import io
import os
import re
import sys
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile


def compress_uploaded_image(uploaded_file, max_dimension=1280, quality=75):
    """
    Compress and normalize an uploaded image in-memory using Pillow.
    - Validates image integrity and format (rejects non-images by returning None)
    - Applies EXIF orientation via ImageOps.exif_transpose
    - Converts RGBA/P/other modes to RGB
    - Resizes down to max_dimension using LANCZOS while preserving aspect ratio
    - Encodes as JPEG (~150-250KB target) and returns an InMemoryUploadedFile
    """
    if not uploaded_file:
        return None

    try:
        uploaded_file.seek(0)
        img = Image.open(uploaded_file)
        # Strictly verify format is an accepted raster image type
        if getattr(img, "format", None) not in ("JPEG", "PNG", "WEBP", "MPO", "GIF", "BMP", "TIFF"):
            return None
        # Load pixel data to verify image integrity
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

    # Build sanitized .jpg filename (strip path traversal and unsafe characters)
    original_name = getattr(uploaded_file, "name", "upload.jpg") or "upload.jpg"
    base_name = os.path.splitext(os.path.basename(original_name))[0]
    safe_base = re.sub(r"[^a-zA-Z0-9_-]", "_", base_name).strip("_") or "upload"
    new_filename = f"{safe_base}.jpg"

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
