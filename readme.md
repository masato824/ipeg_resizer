
📄 **`README.md`（最終版）**

```markdown
# JPEG画像圧縮ツール（Exif保持・オリジナル保存付き）

このツールは、1つのフォルダーに格納された複数のJPEG画像を、指定した最大ファイルサイズ（MB）以下に一括で圧縮します。  
Exif情報（撮影日時など）とファイルのタイムスタンプを保持しつつ、圧縮前のオリジナル画像は選択したフォルダー内の `original/` フォルダーに自動でバックアップされるため、安心してご利用いただけます。

---

## 🧰 主な機能

- JPEG画像を指定サイズ（20 / 10 / 5 / 2 / 1MB）以下に圧縮  
- Exif情報（撮影日時など）を保持  
- ファイルの作成日時・更新日時を保持  
- 圧縮前の画像を `original/` フォルダーに自動保存  
- 壊れたJPEGファイルを検出し、警告表示  
- 処理の進行状況を表示  

---

## 💻 動作環境

- Python 3.8 以上  
- Windows（macOSでも動作可能ですが未検証）  

---

## 📦 必要なライブラリ

Pythonがインストールされている状態で、以下のコマンドを実行してください：

```bash
pip install pillow piexif
```

---

## 📱 Streamlit版（Webアプリ）の使い方

このツールは、Webブラウザからも利用できます。スマートフォンやタブレットからもJPEG画像をアップロードしてリサイズ可能です。

🔗 **Webアプリはこちら**  
👉 [https://masato824-ipegresizer.streamlit.app/](https://masato824-ipegresizer.streamlit.app/)

### ✅ 使い方

1. 上記リンクをクリックしてWebアプリを開く
2. 最大ファイルサイズ（20 / 10 / 5 / 2 / 1 MB）を選択
3. JPEG画像（または複数画像をまとめたZIPファイル）をアップロード
4. 自動でリサイズ処理が行われ、ダウンロードボタンが表示されます

### 📌 特徴

- 単体JPEGまたはZIPファイルに対応
- Exif情報（撮影日時・カメラ情報など）を保持
- 指定サイズ以下に収まらない画像はスキップ
- スマホからも操作しやすいシンプルなUI

---

## 🖥️ コマンドライン版（ローカル実行）

（※既存のCLI版の説明がここに続く）
## 🚀 使い方（CL版）

1. このリポジトリをクローンまたはZIPでダウンロード  
2. `resize.py` をダブルクリック、またはターミナルで実行：

   ```bash
   python resize.py
   ```

3. フォルダー選択ダイアログが表示されるので、JPEG画像が入ったフォルダーを選択  
4. 圧縮後の最大サイズ（MB）を選択（20 / 10 / 5 / 2 / 1MB）  
5. 自動で処理が開始され、完了後に結果が表示されます  

---

## 📁 出力構成

- `original/`：圧縮前のオリジナル画像を保存（Exif・タイムスタンプ保持）  
- 元のフォルダー：圧縮後の画像で上書き保存  

---

## ⚠️ 注意事項

- `.jpg` / `.jpeg` 拡張子以外のファイルは無視されます  
- 拡張子が `.jpg` でも中身が壊れているファイルはスキップされ、警告が表示されます  
- 圧縮できない画像（指定サイズ以下にできないもの）はスキップされます  
- 処理対象のファイル数が多い場合、処理に時間がかかることがあります  

---

## 📄 ライセンス

MIT License  
自由にご利用・改変・再配布いただけますが、著作権表示を残してください。

---

## 🙋‍♂️ 作者

- 作成者：たかはし　まさと 
- ご意見・ご要望は GitHub Issues または Pull Request にてお気軽にお寄せください
---


```

