import streamlit as st
from PIL import Image
import piexif
import io
import zipfile
import os
import tempfile

# 最大サイズ選択
max_size_mb = st.radio("最大ファイルサイズ（MB）を選択", [20, 10, 5, 2, 1])

uploaded_file = st.file_uploader("JPEG画像またはZIPファイルをアップロード", type=["jpg", "jpeg", "zip"])

def compress_image(image_bytes, max_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    exif_bytes = image.info.get("exif", b"")
    quality = 95
    while quality > 10:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True, exif=exif_bytes)
        if buffer.tell() <= max_bytes:
            return buffer.getvalue()
        quality -= 5
    return None

if uploaded_file:
    max_bytes = max_size_mb * 1024 * 1024
    output_files = []

    with tempfile.TemporaryDirectory() as tmpdir:
        if uploaded_file.name.endswith(".zip"):
            with zipfile.ZipFile(uploaded_file, "r") as zip_ref:
                zip_ref.extractall(tmpdir)
                for filename in os.listdir(tmpdir):
                    if filename.lower().endswith((".jpg", ".jpeg")):
                        filepath = os.path.join(tmpdir, filename)
                        with open(filepath, "rb") as f:
                            compressed = compress_image(f.read(), max_bytes)
                            if compressed:
                                output_files.append((filename, compressed))
        else:
            compressed = compress_image(uploaded_file.read(), max_bytes)
            if compressed:
                output_files.append((uploaded_file.name, compressed))

    if output_files:
        if len(output_files) == 1:
            filename, data = output_files[0]
            st.download_button("圧縮画像をダウンロード", data, file_name=filename, mime="image/jpeg")
        else:
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "w") as zip_out:
                for filename, data in output_files:
                    zip_out.writestr(filename, data)
            st.download_button("圧縮画像をZIPでダウンロード", zip_buffer.getvalue(), file_name="resized_images.zip", mime="application/zip")
    else:
        st.warning("指定サイズ以下に圧縮できる画像がありませんでした。")