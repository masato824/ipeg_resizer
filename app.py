import streamlit as st
from PIL import Image
import piexif
import io
import zipfile
import os
import qrcode

# 🔗 共有時に使う公開URL（Streamlit Cloud上の固定URL）
PUBLIC_URL = "https://masato824-ipegresizer.streamlit.app/"

# タイトルと説明
st.markdown('<h1 style="font-size:180%; margin-bottom:0;">Jpegサイズ圧縮</h1>', unsafe_allow_html=True)
st.markdown("""
✅ JPEG画像を一度に複数枚圧縮可能です（1ファイルあたり200MB以下）  
📷 EXIF情報（日時・GPSなど）を保持します  
""")

st.markdown(
    f"🌐 このアプリは Streamlit Cloud で公開中です。\n"
    f"`{PUBLIC_URL}`"
)

# 📢 共有UI（LINE/X共有・URL表示・QRコードは常に公開URLを使用）
st.markdown(f"""
<div style="background-color:#f2f2f2; padding:10px; border-radius:8px;">
  <h4 style="color:#333; margin-bottom:10px;">📢 <strong>友達に知らせる</strong></h4>
  <a href="https://line.me/R/msg/text/?JPEGサイズ圧縮ツール%0A{PUBLIC_URL}" target="_blank">
    <button style="background-color:#00b900; color:white; padding:6px 10px; font-size:90%; border:none; border-radius:5px; margin:4px;">
      💬 LINEで送る
    </button>
  </a>
  <a href="https://twitter.com/share?url={PUBLIC_URL}&text=JPEGサイズ圧縮アプリ" target="_blank">
    <button style="background-color:#1DA1F2; color:white; padding:6px 10px; font-size:90%; border:none; border-radius:5px; margin:4px;">
      🐦 X（旧Twitter）で共有
    </button>
  </a>
</div>
""", unsafe_allow_html=True)

st.markdown('<p style="margin-top:12px; margin-bottom:4px;">🔗 <strong>公開URL（タップでコピー）</strong></p>', unsafe_allow_html=True)
st.code(PUBLIC_URL, language=None)

qr_image = qrcode.make(PUBLIC_URL)
qr_buffer = io.BytesIO()
qr_image.save(qr_buffer, format="PNG")
st.image(qr_buffer.getvalue(), caption="📱 スマホのカメラで読み取って開く", width=180)

# 🔧 圧縮目標サイズ（ラジオボタン）
st.markdown('<h4 style="color:#333; margin-top:20px;">🔧 <strong>圧縮目標サイズ</strong></h4>', unsafe_allow_html=True)
selected_size = st.radio(
    label="圧縮サイズを選択",
    options=[20, 10, 5, 2, 1],
    format_func=lambda x: f"{x}MB",
    horizontal=True
)
max_bytes = selected_size * 1024 * 1024

# 📤 JPEGアップロード
uploaded_files = st.file_uploader(
    "JPEG画像をアップロード（ZIPファイルは非対応）",
    type=["jpg", "jpeg"],
    accept_multiple_files=True
)

if uploaded_files:
    st.success(f"{len(uploaded_files)}枚の画像が選択されました。")
    for file in uploaded_files:
        st.write("✅ 選択ファイル:", file.name)

# 圧縮関数（EXIF保持）
def compress_image(image_bytes, max_bytes):
    image = Image.open(io.BytesIO(image_bytes))
    exif_bytes = image.info.get("exif", b"")

    if len(image_bytes) <= max_bytes:
        return None

    quality = 95
    while quality > 10:
        buffer = io.BytesIO()
        image.save(buffer, format="JPEG", quality=quality, optimize=True, exif=exif_bytes)
        if buffer.tell() <= max_bytes:
            return buffer.getvalue()
        quality -= 5
    return None

# 圧縮処理
output_files = []

if uploaded_files:
    for file in uploaded_files:
        try:
            image_bytes = file.read()
            size_mb = round(len(image_bytes) / 1024 / 1024, 2)

            if size_mb > 200:
                st.warning(f"{file.name} は {size_mb}MB → 200MB超過のため未処理")
                continue

            if len(image_bytes) <= max_bytes:
                st.info(f"{file.name} は {size_mb}MB → 対象外（スキップ）")
                continue

            st.info(f"処理中：{file.name}（{size_mb}MB）")
            compressed = compress_image(image_bytes, max_bytes)
            if compressed:
                final_size = round(len(compressed) / 1024 / 1024, 2)
                st.success(f"{file.name} → {final_size}MB に圧縮完了")
                output_files.append((file.name, compressed))
        except Exception as e:
            st.error(f"{file.name} の処理でエラー: {e}")

# 📥 ダウンロード表示
if output_files:
    if len(output_files) == 1:
        fname, data = output_files[0]
        st.download_button("📥 圧縮画像をダウンロード", data, file_name=fname, mime="image/jpeg")
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w") as zip_out:
            for fname, data in output_files:
                zip_out.writestr(fname, data)
        st.download_button("📦 圧縮画像をZIPでダウンロード", zip_buffer.getvalue(), file_name="resized_images.zip", mime="application/zip")
else:
    if uploaded_files:
        st.warning("指定サイズ以上の画像が見つかりませんでした。")

# 赤字で目立つ制限事項
st.markdown(
    '<p style="color:red; font-size:90%; font-weight:bold; margin-top:20px;">'
    '＜制限事項＞スマホで利用する場合は画像ファイル１枚ずつ処理してください。'
    '</p>',
    unsafe_allow_html=True
)
