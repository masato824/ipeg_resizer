# JPEG Image Compression Tool (Preserves Exif & Original Files)

This tool compresses multiple JPEG images to fit within a specified maximum
file size (in MB). It preserves Exif metadata (shooting date, camera
model, GPS, ...) and file timestamps. Before compression, original images
are automatically backed up into an `original/` subfolder for safety.

There are two ways to use it:

| | Streamlit app (`app.py`) | Desktop / CLI (`resize.py`) |
| --- | --- | --- |
| Input | JPEG uploads in the browser | a folder of JPEGs on disk |
| Multiple files | yes | yes |
| Output | single image or ZIP download | in-place, into the folder |
| Backup of originals | not needed (uploads) | `original/` subfolder |
| EXIF preserved | yes | yes |
| 200 MB per-file cap | yes | no |

---

## Features

- Compress JPEG images to fit within 20 / 10 / 5 / 2 / 1 MB
- **Two-phase compression**: quality is first swept down to 30, and if the
  file is still too large the dimensions are progressively downscaled
  (LANCZOS, down to 50% of the original size) at that floor quality —
  previously, images that could not reach the target via quality alone
  were simply reported as failures
- Preserve Exif metadata (e.g. shooting date, camera model, GPS)
- Retain original file timestamps (created/modified)
- Automatically back up original images to an `original/` folder
  **before** overwriting anything — if the backup fails, the original is
  left untouched (data-loss guard)
- Handle images Pillow cannot encode as JPEG directly (RGBA, palette, ...)
  by converting to RGB instead of crashing
- Detect and skip corrupted JPEG files with warnings
- Display progress with filenames and status

---

## Requirements

- Python 3.9 or higher
- Windows, macOS, or Linux (GUI mode needs a desktop; the CLI mode
  works headless, e.g. on a server or in CI)

---

## Installation

CLI / desktop tools only need Pillow:

```bash
pip install -r requirements.txt   # or: pip install -e ".[dev]" for tests
```

The Streamlit app additionally needs `streamlit` and `qrcode`
(both already in `requirements.txt`).

---

## Desktop GUI

```bash
python resize.py
```

1. Select a folder containing JPEG images
2. Choose the maximum file size (20 / 10 / 5 / 2 / 1 MB)
3. The tool compresses the images and shows a summary

## Headless CLI

Same engine, no display needed — handy for scheduled runs or scripts:

```bash
python resize.py --folder ./photos --max-mb 5
```

Optional flags:

| Flag | Default | Meaning |
| --- | --- | --- |
| `--folder DIR` | GUI mode | folder of JPEGs to process (switches to CLI mode) |
| `--max-mb {20,10,5,2,1}` | — (required with `--folder`) | size cap in MB |
| `--backup-dir NAME` | `original` | backup subfolder name |

The exit code is `1` if any file was skipped, `0` otherwise — usable as a
fail-fast check in scripts.

---

## Output Structure

- `original/`: stores original images before compression (with Exif and
  timestamps preserved)
- The original folder: compressed images overwrite the originals
  (atomically, and only after a successful backup)

---

## Notes

- Only `.jpg` / `.jpeg` files are processed; temporary files written by
  the tool itself (`.jpeg_resizer_tmp_*`) are always ignored
- Files with a `.jpg` extension but invalid content are skipped with a
  warning
- Images that cannot be compressed below the target size (quality floor
  and 50% minimum scale both reached) are skipped with a warning — the
  original file is never deleted
- RGBA/alpha images lose their alpha channel when converted to JPEG
- Processing large numbers of files may take time

---

## Tests

```bash
pip install -e ".[dev]"
pytest
```

The test suite generates synthetic images on the fly (no network, no
external services) and covers the compression engine, the batch folder
processor (backup guard, timestamps, corrupt-input handling) and the
ZIP download builder.

---

## License

MIT License — you are free to use, modify, and redistribute this tool.
Please retain the copyright notice.

---

## Author

- Created by: Masato Takahashi
- Feedback and contributions are welcome via GitHub Issues or Pull Requests