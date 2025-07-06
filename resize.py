import os
import shutil
from PIL import Image
import piexif
from tkinter import Tk, filedialog, messagebox

# === フォルダー選択 ===
root = Tk()
root.withdraw()
input_folder = filedialog.askdirectory(title="探鳥写真フォルダーを選択してください")
if not input_folder:
    messagebox.showinfo("キャンセル", "フォルダーが選択されませんでした。")
    exit()

# === サイズ選択（拡張済み） ===
size_options = {1: 20, 2: 10, 3: 5, 4: 2, 5: 1}
print("圧縮する最大サイズを選んでください：")
print("1: 20MB\n2: 10MB\n3: 5MB\n4: 2MB\n5: 1MB")
choice = input("番号を入力してください（1〜5）: ")

if choice not in map(str, size_options.keys()):
    print("❌ 無効な選択です。終了します。")
    exit()

max_size_mb = size_options[int(choice)]
quality_step = 5
min_quality = 30

# === original フォルダーの作成（元画像のバックアップ用） ===
original_folder = os.path.join(input_folder, "original")
os.makedirs(original_folder, exist_ok=True)

# === JPEGファイルの一覧取得 ===
file_list = [f for f in os.listdir(input_folder) if f.lower().endswith((".jpg", ".jpeg"))]
total_files = len(file_list)

processed = 0
skipped = 0
unchanged = 0
error_files = []

for i, filename in enumerate(file_list, start=1):
    filepath = os.path.join(input_folder, filename)

    # === 進行状況の表示 ===
    print(f"[{i}/{total_files}] 処理中: {filename}")

    # === 画像として開けるか確認（壊れたJPEG検出） ===
    try:
        img = Image.open(filepath)
        img.load()
    except Exception as e:
        print(f"❌ {filename} を開けませんでした: {e}")
        error_files.append(filename)
        skipped += 1
        continue

    # === ファイルサイズ確認 ===
    size_mb = os.path.getsize(filepath) / (1024 * 1024)
    if size_mb <= max_size_mb:
        print(f"⏩ {filename} は {size_mb:.2f}MB（圧縮不要）")
        unchanged += 1
        continue

    # === 元画像を original フォルダーにコピー（Exif・タイムスタンプ保持） ===
    try:
        shutil.copy2(filepath, os.path.join(original_folder, filename))
    except Exception as e:
        print(f"⚠️ {filename} のバックアップに失敗しました: {e}")

    # === Exifとタイムスタンプの保持 ===
    exif_bytes = img.info.get("exif", None)
    original_stat = os.stat(filepath)
    original_times = (original_stat.st_atime, original_stat.st_mtime)

    quality = 95
    temp_path = os.path.join(input_folder, "temp_" + filename)

    while quality >= min_quality:
        try:
            if exif_bytes:
                img.save(temp_path, "JPEG", quality=quality, optimize=True, exif=exif_bytes)
            else:
                img.save(temp_path, "JPEG", quality=quality, optimize=True)
        except Exception as e:
            print(f"❌ {filename} の保存中にエラーが発生しました: {e}")
            error_files.append(filename)
            skipped += 1
            break

        new_size_mb = os.path.getsize(temp_path) / (1024 * 1024)
        if new_size_mb <= max_size_mb:
            os.replace(temp_path, filepath)
            os.utime(filepath, original_times)
            print(f"✅ {filename} → {new_size_mb:.2f}MB (quality={quality})")
            processed += 1
            break
        quality -= quality_step

    if quality < min_quality and filename not in error_files:
        print(f"⚠️ {filename} は {max_size_mb}MB 以下に圧縮できませんでした")
        if os.path.exists(temp_path):
            os.remove(temp_path)
        skipped += 1

# === 結果表示 ===
summary = f"処理が完了しました！\n\n圧縮成功: {processed} 枚\n圧縮不要: {unchanged} 枚\n圧縮失敗: {skipped} 枚"
messagebox.showinfo("完了", summary)

# === エラー警告 ===
if error_files:
    error_msg = "以下のファイルは壊れている可能性があるため処理できませんでした：\n\n"
    error_msg += "\n".join(error_files)
    messagebox.showwarning("警告", error_msg)