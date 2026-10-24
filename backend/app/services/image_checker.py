"""Image intake: validate, read dominant colours, make a small thumbnail. The original file is NOT kept."""
import base64
import io

from app.core.errors import AppError

MAX_IMAGE_BYTES = 5 * 1024 * 1024
ALLOWED = {"PNG", "JPEG", "WEBP", "GIF"}


def analyze_image(data: bytes) -> dict:
    from PIL import Image, UnidentifiedImageError
    if len(data) > MAX_IMAGE_BYTES:
        raise AppError(413, "FILE_TOO_LARGE", "Images can be up to 5 MB.")
    Image.MAX_IMAGE_PIXELS = 40_000_000  # decompression-bomb guard
    try:
        img = Image.open(io.BytesIO(data))
        if img.format not in ALLOWED:
            raise AppError(400, "UNSUPPORTED_IMAGE", "Upload a PNG, JPEG, WEBP or GIF image.")
        img.load()
    except AppError:
        raise
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError) as e:
        raise AppError(400, "UNSUPPORTED_IMAGE", "This image could not be read.") from e
    rgb = img.convert("RGB")
    w, h = rgb.size
    small = rgb.copy()
    small.thumbnail((96, 96))
    q = small.quantize(colors=5)
    pal = q.getpalette() or []
    total = small.size[0] * small.size[1]
    dominant = []
    for count, idx in sorted(q.getcolors() or [], reverse=True):
        r, g, b = pal[idx * 3: idx * 3 + 3]
        dominant.append({"hex": f"#{r:02X}{g:02X}{b:02X}", "share": round(count / total, 3)})
    thumb = rgb.copy()
    thumb.thumbnail((240, 240))
    buf = io.BytesIO()
    thumb.save(buf, "JPEG", quality=80)
    return {"width": w, "height": h, "dominant": dominant,
            "thumb": "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()}
