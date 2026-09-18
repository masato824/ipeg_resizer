"""Offline tests for the shared compression engine and ZIP builder.

Every image is generated on the fly — no network, no external services.
Size targets are self-calibrated against the actual encoder output so the
tests stay stable across Pillow versions.
"""

from __future__ import annotations

import io
import os
import zipfile

import pytest
from PIL import Image, UnidentifiedImageError

from compressor import (
    CompressionError,
    build_download_zip,
    compress_bytes,
)

MB = 1024 * 1024


def make_noisy_jpeg(width: int = 800, height: int = 600, quality: int = 95) -> bytes:
    """A JPEG full of random noise — worst case for compression."""
    img = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    return buf.getvalue()


def save_at(data: bytes, quality: int) -> bytes:
    """Re-encode ``data`` at ``quality`` the same way the engine does."""
    img = Image.open(io.BytesIO(data))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


# ---------------------------------------------------------------- compress_bytes


def test_already_small_returns_none():
    data = make_noisy_jpeg(64, 64)
    assert compress_bytes(data, len(data) * 2) is None


def test_compress_reduces_below_target():
    data = make_noisy_jpeg(600, 400)
    target = len(data) // 2
    out = compress_bytes(data, target)
    assert out is not None
    assert len(out) <= target
    assert len(out) < len(data)
    # output must still be a decodable JPEG
    Image.open(io.BytesIO(out)).load()


def test_compressed_result_is_valid_jpeg_of_same_pixels():
    data = make_noisy_jpeg(200, 150)
    out = compress_bytes(data, len(data) // 2)
    assert out is not None
    back = Image.open(io.BytesIO(out))
    assert back.format == "JPEG"
    assert back.size == (200, 150)


def test_zero_or_negative_max_bytes_rejected():
    with pytest.raises(ValueError):
        compress_bytes(b"junk", 0)
    with pytest.raises(ValueError):
        compress_bytes(b"junk", -1)


def test_non_image_raises():
    with pytest.raises(UnidentifiedImageError):
        compress_bytes(b"this is definitely not an image" * 100, 1)


def _scaled_at(data: bytes, scale: float, quality: int = 30) -> bytes:
    """Downscale ``data`` and re-encode exactly like the engine does."""
    img = Image.open(io.BytesIO(data))
    w, h = img.size
    img = img.resize((round(w * scale), round(h * scale)), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality, optimize=True)
    return buf.getvalue()


def test_exif_preserved_through_downscale():
    # noise content + half-size target forces the dimension-downscale phase
    img = Image.frombytes("RGB", (800, 600), os.urandom(800 * 600 * 3))
    ex = Image.Exif()
    ex[0x010F] = "TestCam"  # Make
    ex[0x0132] = "2024:05:04 03:02:01"  # DateTimeOriginal
    buf = io.BytesIO()
    img.save(buf, "JPEG", exif=ex.tobytes())
    data = buf.getvalue()

    out = compress_bytes(data, len(data) // 2)
    assert out is not None
    back = Image.open(io.BytesIO(out)).getexif()
    assert back.get(0x010F) == "TestCam"
    assert back.get(0x0132) == "2024:05:04 03:02:01"


def test_rgba_converted_to_rgb():
    img = Image.frombytes("RGBA", (256, 256), os.urandom(256 * 256 * 4))
    buf = io.BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()
    # RGBA directly as JPEG crashes Pillow ("cannot write mode RGBA as JPEG")
    out = compress_bytes(data, len(data) // 2)
    assert out is not None
    back = Image.open(io.BytesIO(out))
    assert back.mode == "RGB"  # alpha dropped by design
    assert len(out) <= len(data) // 2


def test_palette_mode_converted_to_rgb():
    img = Image.new("P", (256, 256))
    pal = bytes(sum(([i % 255, (i * 3) % 255, (i * 7) % 255] for i in range(256)), []))
    img.putpalette(pal)
    for y in range(256):
        for x in range(256):
            img.putpixel((x, y), (x * y) % 256)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    data = buf.getvalue()
    out = compress_bytes(data, len(data) // 2)
    assert out is not None
    assert Image.open(io.BytesIO(out)).mode == "RGB"


def test_cmyk_jpeg_passes_through():
    img = Image.frombytes("CMYK", (256, 256), os.urandom(256 * 256 * 4))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)  # CMYK JPEG is a valid input
    data = buf.getvalue()
    out = compress_bytes(data, len(data) // 2)
    assert out is not None
    # CMYK is a JPEG-safe mode — the engine leaves it alone
    assert Image.open(io.BytesIO(out)).mode == "CMYK"


def test_downscale_fallback_when_quality_floor_reached():
    data = make_noisy_jpeg(1200, 900)
    floor_size = len(save_at(data, 30))  # full-res size at the quality floor
    target = int(floor_size * 0.75)  # quality alone can never reach this

    out = compress_bytes(data, target, min_quality=30)
    assert out is not None
    assert len(out) <= target
    # it must have been the dimension-downscale phase that succeeded
    back = Image.open(io.BytesIO(out))
    assert back.size != (1200, 900)
    assert back.size[0] < 1200


def test_unreachable_target_raises():
    data = make_noisy_jpeg(200, 150)
    with pytest.raises(CompressionError):
        compress_bytes(data, 1)


def test_min_scale_respected():
    data = make_noisy_jpeg(800, 600)
    s30 = len(save_at(data, 30))  # full-res size at the quality floor
    s08 = len(_scaled_at(data, 0.8))  # one downscale step
    s512 = len(_scaled_at(data, 0.512))  # last step above the 50% floor

    # a target that even the smallest legal scale cannot reach must be refused
    with pytest.raises(CompressionError):
        compress_bytes(data, s512 - 1, min_scale=0.5)

    # a target reachable at exactly one 0.8 step succeeds and stays >= floor
    target = (s30 + s08) // 2  # above the 0.8-step output, below full-res q30
    out = compress_bytes(data, target)
    assert out is not None
    back = Image.open(io.BytesIO(out))
    assert back.size == (640, 480)  # exactly one 0.8 step, nothing more
    assert back.size[0] >= 400 and back.size[1] >= 300  # never below min_scale


# ------------------------------------------------------------ build_download_zip


def test_zip_deduplicates_names():
    data = build_download_zip(
        [("a.jpg", b"one"), ("a.jpg", b"two"), ("a.jpg", b"three")]
    )
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert sorted(zf.namelist()) == ["a (1).jpg", "a (2).jpg", "a.jpg"]
        assert zf.read("a (1).jpg") == b"two"
        assert zf.read("a (2).jpg") == b"three"


def test_zip_roundtrip_contents():
    data = build_download_zip([("x.jpg", b"\xff\xd8abc"), ("y.jpeg", b"\xff\xd8def")])
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.read("x.jpg") == b"\xff\xd8abc"
        assert zf.read("y.jpeg") == b"\xff\xd8def"


def test_zip_strips_directory_components():
    data = build_download_zip([("sub/dir/pic.jpg", b"data")])
    with zipfile.ZipFile(io.BytesIO(data)) as zf:
        assert zf.namelist() == ["pic.jpg"]