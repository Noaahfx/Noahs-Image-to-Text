# Noah’s Image to Text (OCR)
---

## ✨ Features

* 🖼️ Drag-and-drop upload (multi-file), preview thumbnails
* 🌐 **Multi-language OCR** with **automatic script detection**
* 🧠 Accuracy tuning: LSTM engine (`--oem 1`), `--psm 6`, smart upscale for thin strokes
* 🧹 Output cleanup for CJK/RTL/LTR (sensible newlines, zero-width chars removed)
* 📋 One-click copy & per-file `.txt` download
* 🟢 Health pill in header; `GET /api/health` returns status + installed languages
* ⚡ Clean, responsive UI with DM Sans & premium buttons (no “cheap” outlines)

---

## 🧱 Tech Stack

* **Backend:** FastAPI, Uvicorn (Gunicorn in production), Pillow, pytesseract
* **Frontend:** HTML + CSS + vanilla JS (no frameworks), DM Sans from Google Fonts
* **OCR Engine:** Tesseract (system binary)

---

## 📁 Project Structure

```
.
├─ main.py
├─ requirements.txt
├─ README.md
├─ templates/
│  └─ index.html
└─ static/
   ├─ style.css
   ├─ app.js
   ├─ logo.svg
   └─ favicon.svg
```

---

## ✅ Prerequisites

### 1) Install Tesseract (the OCR engine)

* **Windows:** Install Tesseract (default path `C:\Program Files\Tesseract-OCR\tesseract.exe`)
* **macOS (Homebrew):** `brew install tesseract`
* **Ubuntu/Debian:** `sudo apt install tesseract-ocr`

Confirm:

```bash
tesseract --version
```

### 2) Install language packs (very important)

Tesseract can only recognize languages that are **installed** on your system.

Check what you have:

```bash
tesseract --list-langs
```

Install more:

* **Windows:** Download `*.traineddata` files (prefer `tessdata_best`) and copy into
  `C:\Program Files\Tesseract-OCR\tessdata\`
  Examples: `ara` (Arabic), `chi_sim`/`chi_tra` (Chinese), `jpn`, `kor`, `hin`, `ben`, `rus`, etc.
* **macOS:**

  ```bash
  brew install tesseract-lang
  ```
* **Ubuntu/Debian:**

  ```bash
  sudo apt install \
    tesseract-ocr-ara tesseract-ocr-chi-sim tesseract-ocr-chi-tra \
    tesseract-ocr-jpn tesseract-ocr-kor tesseract-ocr-hin \
    tesseract-ocr-ben tesseract-ocr-rus
  ```

> If your traineddata lives elsewhere, set `TESSDATA_PREFIX` to that folder.

---

## 🚀 Quickstart (Development)

```bash
# 0) (Windows only) optionally allow venv activation
#   PowerShell: Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned

# 1) Create & activate venv
python -m venv venv
# Windows: .\venv\Scripts\Activate.ps1
# macOS/Linux: source venv/bin/activate

# 2) Install deps
pip install -r requirements.txt

# 3) (Windows) If tesseract isn't on PATH, set the binary path:
#   $env:TESSERACT_CMD="C:\Program Files\Tesseract-OCR\tesseract.exe"

# 4) Run dev server
uvicorn main:app --reload
# open http://127.0.0.1:8000
```

> If `uvicorn main:app --reload` fails due to a stale shim, run `python -m uvicorn main:app --reload` once, then `pip install --force-reinstall uvicorn[standard] watchfiles` and try again.

---

## 🛠️ Configuration

Environment variables:

* `TESSERACT_CMD` – full path to the Tesseract binary (Windows commonly needed)
* `TESSDATA_PREFIX` – directory containing `*.traineddata` files (optional if default path is correct)
