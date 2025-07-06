

## 📄 `README.en.md`（英語版）

```markdown
# JPEG Image Compression Tool (Preserves Exif & Original Files)

This tool compresses multiple JPEG images in a selected folder to fit within a specified maximum file size (in MB).  
It preserves Exif metadata (such as shooting date and camera info) and file timestamps.  
Before compression, original images are automatically backed up into an `original/` subfolder for safety.

---

## 🧰 Features

- Compress JPEG images to fit within 20 / 10 / 5 / 2 / 1 MB  
- Preserve Exif metadata (e.g., shooting date, camera model)  
- Retain original file timestamps (created/modified)  
- Automatically back up original images to `original/` folder  
- Detect and skip corrupted JPEG files with warnings  
- Display progress with filenames and status  

---

## 💻 Requirements

- Python 3.8 or higher  
- Windows (macOS may work but is untested)  

---

## 📦 Required Libraries

Install the following libraries using pip:

```bash
pip install pillow piexif
```

---

## 🚀 How to Use

1. Download or clone this repository  
2. Run `resize.py` by double-clicking or via terminal:

   ```bash
   python resize.py
   ```

3. Select a folder containing JPEG images  
4. Choose the maximum file size (20 / 10 / 5 / 2 / 1 MB)  
5. The tool will compress the images and display a summary upon completion  

---

## 📁 Output Structure

- `original/`: Stores original images before compression (with Exif and timestamps preserved)  
- Original folder: Compressed images overwrite the originals  

---

## ⚠️ Notes

- Only `.jpg` / `.jpeg` files are processed  
- Files with `.jpg` extension but invalid content will be skipped with a warning  
- Images that cannot be compressed below the target size will be skipped  
- Processing large numbers of files may take time  

---

## 📄 License

MIT License  
You are free to use, modify, and redistribute this tool. Please retain the copyright notice.

---

## 🙋‍♂️ Author

- Created by: Masato Takahashi  
- Feedback and contributions are welcome via GitHub Issues or Pull Requests
```

