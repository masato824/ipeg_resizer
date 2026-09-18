"""Offline tests for the batch folder processor and the resize.py CLI."""

from __future__ import annotations

import io
import os
import time

import pytest
from PIL import Image

import compressor
from compressor import TEMP_PREFIX, process_folder
from resize import main


def write_noise_jpeg(path, width=800, height=600, quality=95) -> bytes:
    """Write a noisy JPEG to ``path`` and return its bytes."""
    img = Image.frombytes("RGB", (width, height), os.urandom(width * height * 3))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=quality)
    data = buf.getvalue()
    path.write_bytes(data)
    return data


def write_solid_jpeg(path, width=64, height=64) -> bytes:
    img = Image.new("RGB", (width, height), (200, 120, 40))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=95)
    data = buf.getvalue()
    path.write_bytes(data)
    return data


# ------------------------------------------------------------- process_folder


def test_process_folder_compresses_backs_up_and_keeps_timestamps(tmp_path):
    big1 = tmp_path / "a.jpg"
    big2 = tmp_path / "b.jpeg"
    small = tmp_path / "c.jpg"
    note = tmp_path / "note.txt"
    original1 = write_noise_jpeg(big1)
    write_noise_jpeg(big2)
    write_solid_jpeg(small)  # a few hundred bytes — well under target
    note.write_text("ignored")

    old_mtime = time.time() - 3600
    os.utime(big1, (old_mtime, old_mtime))

    target = 300 * 1024
    result = process_folder(tmp_path, target)

    assert result.processed == 2
    assert result.unchanged == 1
    assert result.skipped == 0
    assert result.errors == []

    # originals were backed up byte-for-byte before being replaced
    backup = tmp_path / "original"
    assert (backup / "a.jpg").read_bytes() == original1
    assert (backup / "b.jpeg").exists()
    assert not (backup / "note.txt").exists()
    assert not (backup / "c.jpg").exists()  # never needed compressing

    # compressed files now fit the limit; timestamp survived the swap
    assert big1.stat().st_size <= target
    assert big2.stat().st_size <= target
    assert abs(big1.stat().st_mtime - old_mtime) < 0.01


def test_corrupt_file_skipped_and_never_backed_up(tmp_path):
    bad = tmp_path / "broken.jpg"
    good = tmp_path / "ok.jpg"
    bad.write_bytes(b"not a jpeg at all" * 50000)  # > target, must be examined
    write_solid_jpeg(good)

    result = process_folder(tmp_path, 1024)

    assert result.skipped == 1
    assert result.processed == 0
    assert "could not open" in result.errors[0][1]
    assert bad.read_bytes().startswith(b"not a jpeg")
    assert not (tmp_path / "original" / "broken.jpg").exists()


def test_backup_failure_leaves_original_untouched(tmp_path, monkeypatch):
    photo = tmp_path / "photo.jpg"
    before = write_noise_jpeg(photo)

    def boom(*args, **kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(compressor.shutil, "copy2", boom)

    result = process_folder(tmp_path, 100 * 1024)

    assert result.skipped == 1
    assert "backup failed" in result.errors[0][1]
    assert photo.read_bytes() == before  # data-loss guard: never overwrite it


def test_uncompressible_file_skipped_original_untouched(tmp_path):
    photo = tmp_path / "photo.jpg"
    before = write_noise_jpeg(photo)

    result = process_folder(tmp_path, 100)  # 100 bytes — unreachable target

    assert result.skipped == 1
    assert "unreachable" in result.errors[0][1]
    assert photo.read_bytes() == before


def test_temp_files_ignored(tmp_path):
    leftover = tmp_path / f"{TEMP_PREFIX}42_photo.jpg"
    write_noise_jpeg(leftover)

    result = process_folder(tmp_path, 100 * 1024)

    assert result.unchanged == 0
    assert result.processed == 0
    assert result.skipped == 0
    assert not (tmp_path / "original").exists()  # nothing was touched


def test_empty_folder_is_clean_noop(tmp_path):
    result = process_folder(tmp_path, 1024)
    assert result.processed == 0
    assert result.unchanged == 0
    assert result.skipped == 0
    assert not (tmp_path / "original").exists()


def test_uppercase_extension_handled(tmp_path):
    photo = tmp_path / "PHOTO.JPG"
    original = write_noise_jpeg(photo)
    result = process_folder(tmp_path, 100 * 1024)
    assert result.processed == 1
    assert (tmp_path / "original" / "PHOTO.JPG").read_bytes() == original


def test_zero_max_bytes_rejected(tmp_path):
    with pytest.raises(ValueError):
        process_folder(tmp_path, 0)


# -------------------------------------------------------------------- CLI


def test_cli_requires_max_mb(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--folder", str(tmp_path)])
    assert exc.value.code == 2


def test_cli_rejects_invalid_size_choice(tmp_path):
    with pytest.raises(SystemExit) as exc:
        main(["--folder", str(tmp_path), "--max-mb", "7"])
    assert exc.value.code == 2


def test_cli_exit_zero_when_all_within_limit(tmp_path, capsys):
    write_solid_jpeg(tmp_path / "small.jpg")
    code = main(["--folder", str(tmp_path), "--max-mb", "5"])
    out = capsys.readouterr().out
    assert code == 0
    assert "圧縮不要: 1" in out


def test_cli_exit_one_when_file_skipped(tmp_path):
    (tmp_path / "broken.jpg").write_bytes(b"junk" * (6 * 1024 * 1024))  # > 5 MB
    code = main(["--folder", str(tmp_path), "--max-mb", "5"])
    assert code == 1


def test_cli_custom_backup_dir(tmp_path):
    write_noise_jpeg(tmp_path / "photo.jpg")
    result = process_folder(tmp_path, 100 * 1024, backup_dir_name="backup_originals")
    assert result.processed == 1
    assert (tmp_path / "backup_originals" / "photo.jpg").exists()