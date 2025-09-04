import os
import io
import re
import platform
import subprocess
from typing import List, Set, Optional

from fastapi import FastAPI, UploadFile, File, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from PIL import Image, ImageOps
import pytesseract
from pytesseract import Output

app = FastAPI(title="Noah's Converter - Image to Text (OCR)")

# ---------- TESSERACT DISCOVERY ----------
t_cmd_env = os.getenv("TESSERACT_CMD")
if t_cmd_env:
    pytesseract.pytesseract.tesseract_cmd = t_cmd_env
else:
    system = platform.system().lower()
    possible = []
    if "windows" in system:
        possible = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
        ]
    elif "darwin" in system:  # macOS
        possible = ["/opt/homebrew/bin/tesseract", "/usr/local/bin/tesseract"]
    else:  # linux
        possible = ["/usr/bin/tesseract", "/usr/local/bin/tesseract"]
    for p in possible:
        if os.path.exists(p):
            pytesseract.pytesseract.tesseract_cmd = p
            break
# ----------------------------------------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.mount("/static", StaticFiles(directory=os.path.join(BASE_DIR, "static")), name="static")
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

@app.get("/")
def root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/api/health")
def health():
    # Also report installed langs so you can diagnose coverage from the UI if needed
    return {"ok": True, "langs": sorted(list(_installed_langs()))}


# ---------- OCR UTILITIES ----------

def _installed_langs() -> Set[str]:
    """Return the set of installed Tesseract language codes."""
    try:
        # pytesseract >=0.3.8
        langs = pytesseract.get_languages(config="")
        return set(langs)
    except Exception:
        # Fallback: shell out to --list-langs
        try:
            out = subprocess.check_output(
                [pytesseract.pytesseract.tesseract_cmd, "--list-langs"],
                stderr=subprocess.STDOUT, universal_newlines=True
            )
            lines = [l.strip() for l in out.splitlines()
                     if l.strip() and not l.lower().startswith("list of available")]
            return set(lines) if lines else {"eng"}
        except Exception:
            return {"eng"}

# Script → preferred languages (use only those actually installed)
SCRIPT_TO_PREF_LANGS = {
    "Arabic": ["ara", "fas", "urd", "pus", "uig", "snd", "kur"],   # Arabic script family
    "Hebrew": ["heb", "yid"],
    "Han": ["chi_sim", "chi_tra"],                                 # Simplified/Traditional Chinese
    "Japanese": ["jpn"],
    "Korean": ["kor"],
    "Cyrillic": ["rus", "ukr", "bul", "srp", "mkd", "bel", "kaz", "uzb_cyrl"],
    "Greek": ["ell"],
    "Devanagari": ["hin", "mar", "nep", "san"],
    "Bengali": ["ben"],
    "Gujarati": ["guj"],
    "Gurmukhi": ["pan"],
    "Tamil": ["tam"],
    "Telugu": ["tel"],
    "Kannada": ["kan"],
    "Malayalam": ["mal"],
    "Sinhala": ["sin"],
    "Thai": ["tha"],
    "Lao": ["lao"],
    "Khmer": ["khm"],
    "Myanmar": ["mya"],
    "Latin": [
        # Broad Latin set
        "eng","fra","deu","spa","ita","por","nld","ron","pol","ces","slk","slv",
        "hrv","hun","fin","swe","nor","dan","isl","cat","epo","tur","aze",
        "ind","msa","tgl","vie","est","lav","lit","sqi","bos","glg","eus","afr"
    ],
}

POPULAR_FALLBACK = [
    "eng","fra","deu","spa","ita","por","nld",
    "chi_sim","chi_tra","jpn","kor",
    "ara","heb","rus","ukr",
    "hin","ben","tur","vie"
]

def preprocess(img: Image.Image) -> Image.Image:
    """Upscale + gentle normalization."""
    if img.width < 1200:
        scale = 1200 / img.width
        img = img.resize((1200, int(img.height * scale)), Image.LANCZOS)
    img = img.convert("L")
    img = ImageOps.autocontrast(img)
    return img

def detect_langs_with_osd(img: Image.Image, installed: Set[str]) -> Optional[str]:
    """Use OSD to detect script, then map to installed language codes."""
    try:
        osd = pytesseract.image_to_osd(img, output_type=Output.DICT)
        script = (osd.get("script") or "").strip()
        if not script:
            return None
        prefs = SCRIPT_TO_PREF_LANGS.get(script)
        if not prefs:
            return None
        available = [l for l in prefs if l in installed]
        return "+".join(available) if available else None
    except Exception:
        return None

def _is_rtl_langs(lang_str: str) -> bool:
    rtl = {"ara","fas","urd","pus","uig","snd","heb","yid"}
    return any(l in rtl for l in lang_str.split("+"))

def clean_text(text: str, langs: str) -> str:
    """CJK: remove hard breaks; LTR/RTL: keep paragraphs but normalize."""
    t = text.replace("\u200b", "").replace("\r", "").strip()
    if any(x in langs for x in ("chi_", "jpn", "kor")):
        t = t.replace("\n", "")
    else:
        t = re.sub(r"[ \t]+\n", "\n", t)
        t = re.sub(r"\n{3,}", "\n\n", t)
    return t

def choose_fallback_langs(installed: Set[str], limit: int = 8) -> str:
    available = [l for l in POPULAR_FALLBACK if l in installed]
    if not available and "eng" in installed:
        available = ["eng"]
    return "+".join(available[:limit])


# ---------- OCR ENDPOINT ----------

@app.post("/api/ocr")
async def ocr_endpoint(
    files: List[UploadFile] = File(...),
):
    installed = _installed_langs()
    results = []
    for f in files:
        try:
            raw = await f.read()
            img = Image.open(io.BytesIO(raw))
            img = preprocess(img)

            lang_hint = detect_langs_with_osd(img, installed)
            langs = lang_hint or choose_fallback_langs(installed)

            config = r'--oem 1 --psm 6 -c preserve_interword_spaces=1'
            text = pytesseract.image_to_string(img, lang=langs, config=config)
            text = clean_text(text, langs)

            if len(text) < 8:
                broad_langs = choose_fallback_langs(installed, limit=12)
                if broad_langs != langs:
                    text_retry = pytesseract.image_to_string(img, lang=broad_langs, config=config)
                    text_retry = clean_text(text_retry, broad_langs)
                    if len(text_retry) > len(text):
                        text, langs = text_retry, broad_langs

            results.append({
                "filename": f.filename,
                "text": text,
                "langs_used": langs
            })
        except Exception as e:
            results.append({
                "filename": f.filename,
                "error": str(e),
                "text": ""
            })

    return JSONResponse({"items": results, "count": len(results)})
