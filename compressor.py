"""Core JPEG compression engine shared by the Streamlit app and the desktop tool.

Both UIs used to carry their own copy of the quality-sweep loop, and they
disagreed about the floor (the desktop tool stopped at quality 30, the web
app at quality 10). This module is the single implementation both entry
points delegate to, so behaviour and limits stay consistent everywhere.

The two-phase strategy:

1. Sweep the JPEG quality setting down to ``min_quality``.
2. If the file is still too big, downscale the dimensions (LANCZOS) in
   ``scale_step`` increments down to ``min_scale`` of the original size,
   re-encoding at the floor quality.

EXIF bytes are carried through every re-encode, so shooting date, camera
model and GPS metadata survive compression.
"""

from __future__ import annotations

import io
import os
import shutil
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

from PIL import Image

DEFAULT_QUALITY_START = 95
DEFAULT_QUALITY_STEP = 5
DEFAULT_MIN_QUALITY = 30
DEFAULT_SCALE_STEP = 0.8
DEFAULT_MIN_SCALE = 0.5

# Modes Pillow can write to JPEG directly. Anything else (RGBA, P, LA,
# F, "I;16", ...) is converted to RGB first — RGBA loses its alpha
# channel, by design: JPEG has none.
JPEG_SAFE_MODES = frozenset({"RGB", "L", "YCbCr", "CMYK"})

IMAGE_EXTENSIONS = (".jpg", ".jpeg")

TEMP_PREFIX = ".jpeg_resizer_tmp_"

STATUS_COMPRESSED = "compressed"
STATUS_UNCHANGED = "unchanged"
STATUS_SKIPPED = "skipped"


class CompressionError(Exception):
    """Raised when a JPEG cannot be brought under the size target."""


def _jpeg_safe(image: Image.Image) -> Image.Image:
    """Return the image in a mode that Pillow can write as JPEG."""
    if image.mode not in JPEG_SAFE_MODES:
        return image.convert("RGB")
    return image


def _save_jpeg(image: Image.Image, quality: int, exif: bytes | None) -> bytes:
    buf = io.BytesIO()
    kwargs: dict = {"quality": quality, "optimize": True}
    if exif:
        kwargs["exif"] = exif
    _jpeg_safe(image).save(buf, "JPEG", **kwargs)
    return buf.getvalue()


def compress_bytes(
    data: bytes,
    max_bytes: int,
    *,
    min_quality: int = DEFAULT_MIN_QUALITY,
    quality_step: int = DEFAULT_QUALITY_STEP,
    scale_step: float = DEFAULT_SCALE_STEP,
    min_scale: float = DEFAULT_MIN_SCALE,
) -> bytes | None:
    """Compress JPEG ``data`` to ``<= max_bytes``.

    Returns ``None`` when the input already fits within the limit (the
    caller can skip re-encoding entirely). Otherwise returns the re-encoded
    JPEG bytes.

    Raises:
        ValueError: if ``max_bytes`` is not positive.
        PIL.UnidentifiedImageError / OSError: for input that is not a
            decodable image.
        CompressionError: when the target is unreachable — the quality floor
            and the ``min_scale`` dimension floor were both reached.
    """
    if max_bytes <= 0:
        raise ValueError(f"max_bytes must be positive, got {max_bytes}")
    if len(data) <= max_bytes:
        return None

    image = Image.open(io.BytesIO(data))
    image.load()  # fully decode — raises for truncated/corrupt input
    exif = image.info.get("exif")

    # Phase 1: quality sweep.
    quality = DEFAULT_QUALITY_START
    while quality >= min_quality:
        out = _save_jpeg(image, quality, exif)
        if len(out) <= max_bytes:
            return out
        quality -= quality_step

    # Phase 2: dimension downscale at the floor quality.
    orig_w, orig_h = image.size
    scale = 1.0
    while True:
        scale *= scale_step
        if scale < min_scale:
            break
        width = max(1, round(orig_w * scale))
        height = max(1, round(orig_h * scale))
        out = _save_jpeg(image.resize((width, height), Image.LANCZOS), min_quality, exif)
        if len(out) <= max_bytes:
            return out

    raise CompressionError(
        f"target {max_bytes} bytes unreachable at quality {min_quality} "
        f"and {int(min_scale * 100)}% minimum scale"
    )


@dataclass
class FileResult:
    """Outcome for one image in a batch run."""

    name: str
    status: str  # STATUS_COMPRESSED | STATUS_UNCHANGED | STATUS_SKIPPED
    detail: str = ""


@dataclass
class FolderResult:
    """Aggregated outcome of processing a folder of JPEGs."""

    results: list[FileResult] = field(default_factory=list)

    @property
    def processed(self) -> int:
        return sum(r.status == STATUS_COMPRESSED for r in self.results)

    @property
    def unchanged(self) -> int:
        return sum(r.status == STATUS_UNCHANGED for r in self.results)

    @property
    def skipped(self) -> int:
        return sum(r.status == STATUS_SKIPPED for r in self.results)

    @property
    def errors(self) -> list[tuple[str, str]]:
        return [(r.name, r.detail) for r in self.results if r.status == STATUS_SKIPPED]


def _iter_jpegs(folder: Path):
    """Yield JPEG files in a folder, newest first, ignoring leftover temp files."""
    for path in sorted(folder.iterdir(), key=lambda p: p.name):
        if (
            path.is_file()
            and path.suffix.lower() in IMAGE_EXTENSIONS
            and not path.name.startswith(TEMP_PREFIX)
        ):
            yield path


def process_folder(
    folder: str | Path,
    max_bytes: int,
    *,
    backup_dir_name: str = "original",
) -> FolderResult:
    """Compress every JPEG in ``folder`` to ``<= max_bytes`` in place.

    For each file that needs shrinking:

    - the original is first copied into ``<folder>/<backup_dir_name>/``
      (EXIF and timestamps preserved via ``shutil.copy2``);
    - if that backup fails, the file is skipped and the original is left
      untouched — a compression run must never destroy the last copy;
    - the compressed bytes replace the original atomically and the
      original access/modification times are restored.

    Corrupt files and files whose target is unreachable are skipped with a
    reason recorded in the result, so nothing silently vanishes.
    """
    folder = Path(folder)
    if max_bytes <= 0:
        raise ValueError(f"max_bytes must be positive, got {max_bytes}")

    backup_dir = folder / backup_dir_name
    result = FolderResult()

    for path in _iter_jpegs(folder):
        size = path.stat().st_size
        if size <= max_bytes:
            result.results.append(FileResult(path.name, STATUS_UNCHANGED))
            continue

        # Validate before touching anything.
        try:
            probe = Image.open(path)
            probe.load()
            probe.close()
        except Exception as exc:
            result.results.append(
                FileResult(path.name, STATUS_SKIPPED, f"could not open as image: {exc}")
            )
            continue

        # Data-loss guard: never overwrite without a backup on disk.
        try:
            backup_dir.mkdir(exist_ok=True)
            shutil.copy2(path, backup_dir / path.name)
        except Exception as exc:
            result.results.append(
                FileResult(
                    path.name,
                    STATUS_SKIPPED,
                    f"backup failed, original left untouched: {exc}",
                )
            )
            continue

        try:
            # size > max_bytes was already checked, so this is never None here.
            data = compress_bytes(path.read_bytes(), max_bytes)
            assert data is not None
        except CompressionError as exc:
            result.results.append(
                FileResult(path.name, STATUS_SKIPPED, f"target size unreachable: {exc}")
            )
            continue
        except Exception as exc:
            result.results.append(
                FileResult(path.name, STATUS_SKIPPED, f"compression failed: {exc}")
            )
            continue

        atime, mtime = path.stat().st_atime, path.stat().st_mtime
        temp_path = folder / f"{TEMP_PREFIX}{os.getpid()}_{path.name}"
        temp_path.write_bytes(data)
        os.replace(temp_path, path)
        os.utime(path, (atime, mtime))
        result.results.append(FileResult(path.name, STATUS_COMPRESSED))

    return result


def build_download_zip(files: list[tuple[str, bytes]]) -> bytes:
    """Pack ``(name, data)`` pairs into a ZIP archive.

    Duplicate names get a `` (1)`` / `` (2)`` suffix instead of silently
    overwriting each other, and any directory components are stripped so
    entries never escape the archive root.
    """
    out = io.BytesIO()
    seen: set[str] = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, data in files:
            base = os.path.basename(name)
            stem, suffix = os.path.splitext(base)
            candidate, counter = base, 1
            while candidate in seen:
                candidate = f"{stem} ({counter}){suffix}"
                counter += 1
            seen.add(candidate)
            zf.writestr(candidate, data)
    return out.getvalue()