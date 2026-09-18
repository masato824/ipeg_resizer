"""Desktop batch JPEG compressor — tkinter GUI, or headless CLI.

GUI (interactive folder picker + size choice):

    python resize.py

Headless CLI (for servers / scheduled runs / CI):

    python resize.py --folder ./photos --max-mb 5

Both modes share the same engine (:mod:`compressor`), so results are
identical either way. The CLI exits 1 when any file was skipped, making
it usable as a simple check in scripts.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from compressor import FolderResult, process_folder

SIZE_CHOICES_MB = (20, 10, 5, 2, 1)
SIZE_PROMPT = "1: 20MB\n2: 10MB\n3: 5MB\n4: 2MB\n5: 1MB"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compress all JPEGs in a folder to a maximum file size, "
        "preserving EXIF and backing up originals to an 'original/' subfolder."
    )
    parser.add_argument(
        "--folder",
        type=Path,
        metavar="DIR",
        help="folder of JPEG images to process (omit to open the GUI)",
    )
    parser.add_argument(
        "--max-mb",
        type=int,
        choices=SIZE_CHOICES_MB,
        metavar="{20,10,5,2,1}",
        help="maximum file size in MB (required with --folder)",
    )
    parser.add_argument(
        "--backup-dir",
        default="original",
        metavar="NAME",
        help="name of the backup subfolder inside --folder (default: original)",
    )
    return parser


def _format_summary(result: FolderResult) -> str:
    return (
        f"圧縮成功: {result.processed} 枚\n"
        f"圧縮不要: {result.unchanged} 枚\n"
        f"圧縮失敗: {result.skipped} 枚"
    )


def _print_errors(result: FolderResult) -> None:
    if not result.errors:
        return
    print("\n=== スキップされたファイル ===")
    for name, detail in result.errors:
        print(f"❌ {name}: {detail}")


def main_cli(args: argparse.Namespace) -> int:
    """Run the batch compression from the command line."""
    max_bytes = args.max_mb * 1024 * 1024
    print(f"対象フォルダー: {args.folder}")
    print(f"圧縮目標: {args.max_mb}MB 以下")
    print(f"バックアップ先: {args.folder / args.backup_dir}")

    result = process_folder(args.folder, max_bytes, backup_dir_name=args.backup_dir)

    for entry in result.results:
        marker = {"compressed": "✅", "unchanged": "⏩", "skipped": "❌"}[entry.status]
        suffix = f" — {entry.detail}" if entry.detail else ""
        print(f"{marker} {entry.name}{suffix}")

    print(f"\n{_format_summary(result)}")
    _print_errors(result)
    return 1 if result.skipped else 0


def main_gui() -> int:
    """Interactive mode: folder picker + console size choice (Windows-friendly)."""
    # Imported lazily so the headless CLI never needs a display/tkinter.
    from tkinter import Tk, filedialog, messagebox

    root = Tk()
    root.withdraw()
    input_folder = filedialog.askdirectory(title="探鳥写真フォルダーを選択してください")
    if not input_folder:
        messagebox.showinfo("キャンセル", "フォルダーが選択されませんでした。")
        return 0

    print("圧縮する最大サイズを選んでください：")
    print(SIZE_PROMPT)
    choice = input("番号を入力してください（1〜5）: ")
    choice_map = {str(i + 1): mb for i, mb in enumerate(SIZE_CHOICES_MB)}
    if choice not in choice_map:
        messagebox.showwarning("無効な選択", "無効な選択です。終了します。")
        return 1
    max_bytes = choice_map[choice] * 1024 * 1024

    result = process_folder(input_folder, max_bytes)
    messagebox.showinfo("完了", "処理が完了しました！\n\n" + _format_summary(result))
    if result.errors:
        error_msg = "以下のファイルは処理できませんでした：\n\n" + "\n".join(
            f"{name}（{detail}）" for name, detail in result.errors
        )
        messagebox.showwarning("警告", error_msg)
    return 1 if result.skipped else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.folder is not None:
        if args.max_mb is None:
            parser.error("--max-mb is required when --folder is given")
        return main_cli(args)
    return main_gui()


if __name__ == "__main__":
    sys.exit(main())