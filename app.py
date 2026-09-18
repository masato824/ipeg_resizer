import io

import streamlit as st
import qrcode

from compressor import CompressionError, build_download_zip, compress_bytes

# ブラウザタブ名・favicon（ホーム画面追加時の表示名にも一部反映される）
st.set_page_config(page_title="JPEG画像圧縮", page_icon="📷")

# 🔗 共有時に使う公開URL
# Streamlit CloudのSecretsに PUBLIC_URL を設定すればここだけで一括反映される。
# 未設定（ローカル実行など）の場合は下記フォールバック値を使用する。
try:
    PUBLIC_URL = st.secrets["PUBLIC_URL"]
except Exception:
    PUBLIC_URL = "https://ipegresizer-bfxbqsxxjmhfc727zrdkzr.streamlit.app/"

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

# 圧縮処理（共通エンジン compressor.compress_bytes を使用）
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
            compressed = compress_bytes(image_bytes, max_bytes)
            if compressed:
                final_size = round(len(compressed) / 1024 / 1024, 2)
                st.success(f"{file.name} → {final_size}MB に圧縮完了")
                output_files.append((file.name, compressed))
        except CompressionError:
            st.error(f"{file.name} は指定サイズ以下に圧縮できませんでした")
        except Exception as e:
            st.error(f"{file.name} の処理でエラー: {e}")

# 📥 ダウンロード表示
if output_files:
    if len(output_files) == 1:
        fname, data = output_files[0]
        st.download_button("📥 圧縮画像をダウンロード", data, file_name=fname, mime="image/jpeg")
    else:
        zip_data = build_download_zip(output_files)
        st.download_button("📦 圧縮画像をZIPでダウンロード", zip_data, file_name="resized_images.zip", mime="application/zip")
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
