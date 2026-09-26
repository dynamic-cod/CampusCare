"""Image compression and multi-tenant scoping utilities for CampusCare."""
import io
import os
import sys
from PIL import Image, ImageOps
from django.core.files.uploadedfile import InMemoryUploadedFile


def compress_uploaded_image(uploaded_file, max_dimension=1280, quality=75):
    """
    Compress and normalize an uploaded image in-memory using Pillow.
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
    except Exception:
        uploaded_file.seek(0)
        return uploaded_file

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

    # Build .jpg filename
    original_name = getattr(uploaded_file, "name", "upload.jpg") or "upload.jpg"
    base_name = os.path.splitext(os.path.basename(original_name))[0]
    new_filename = f"{base_name}.jpg"

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
