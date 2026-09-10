"""
Stage 2 - fetch each decision page, pull the attached document, and turn it
into clean plain text.

V5.2 change: PDFs are extracted LAYOUT-AWARE. The previous version used plain
reading-order text, which broke the boxed tables on pre-RRA forms - the amount
and its period could end up many lines apart, or interleaved with other cells.

We now read positioned blocks, group them into visual rows by vertical overlap,
and join each row left-to-right. That keeps

    1.  |  The rent is  |  £1300  |  per calendar month

on a single line, which is what `boxes.read_numbered_box` needs to read the
amount box and the period box together.
"""
from __future__ import annotations

import io
import re
import zipfile
from pathlib import Path

from bs4 import BeautifulSoup

import config
from . import httpclient as http

TEXT_CACHE = config.CACHE / "text"
TEXT_CACHE.mkdir(parents=True, exist_ok=True)
ATTACH_EXT = (".pdf", ".doc", ".docx", ".rtf", ".odt")


# ------------------------------------------------------------------ page
def decision_page(url: str) -> dict:
    html = http.cached_get(url, config.CACHE / "pages", ".html")
    if not html:
        return {"html_text": "", "attachments": [], "meta": {}}

    soup = BeautifulSoup(html, "lxml")
    body = soup.select_one("div.govspeak") or soup.select_one("main") or soup
    html_text = clean(body.get_text("\n", strip=True))

    attachments = []
    for a in soup.select("a[href]"):
        href = a["href"].split("?")[0]
        if href.lower().endswith(ATTACH_EXT):
            attachments.append(href if href.startswith("http") else config.BASE + href)
    attachments = list(dict.fromkeys(attachments))

    meta = {}
    for dl in soup.select("dl"):
        for dt, dd in zip(dl.select("dt"), dl.select("dd")):
            meta[clean(dt.get_text(" ", strip=True)).lower().rstrip(":")] = \
                clean(dd.get_text(" ", strip=True))

    return {"html_text": html_text, "attachments": attachments, "meta": meta}


# ------------------------------------------------------------------ documents
def document_text(url: str) -> str:
    cached = TEXT_CACHE / f"{http.cache_key(url)}.txt"
    if cached.exists():
        return cached.read_text("utf-8", errors="ignore")

    blob = http.cached_get(url, config.RAW, Path(url).suffix.lower() or ".bin",
                           binary=True)
    if not blob:
        return ""

    low = url.lower()
    if low.endswith(".pdf"):
        text = pdf_text(blob)
    elif low.endswith((".docx", ".odt")):
        text = _zip_office(blob)
    elif low.endswith(".rtf"):
        text = _rtf(blob)
    elif low.endswith(".doc"):
        text = _legacy_doc(blob)
    else:
        text = ""

    text = clean(text)
    cached.write_text(text, encoding="utf-8")
    return text


def pdf_text(blob: bytes) -> str:
    """Layout-aware first, plain reading order as a fallback, then pdfminer."""
    try:
        import fitz  # PyMuPDF
        with fitz.open(stream=blob, filetype="pdf") as doc:
            pages = []
            for page in doc:
                laid = _rows_from_blocks(page)
                plain = page.get_text("text") or ""
                # Keep both: the row view preserves boxes, the plain view keeps
                # prose that block grouping can occasionally split awkwardly.
                pages.append(laid if laid.strip() else plain)
                if laid.strip() and plain.strip():
                    pages.append("\n<<<PLAIN>>>\n" + plain)
            return "\n".join(pages)
    except Exception:  # noqa: BLE001
        pass
    try:
        from pdfminer.high_level import extract_text
        return extract_text(io.BytesIO(blob)) or ""
    except Exception:  # noqa: BLE001
        return ""


def _rows_from_blocks(page, y_tol: float = 6.0) -> str:
    """
    Group positioned text blocks into visual rows.

    Blocks whose vertical centres are within `y_tol` points are treated as the
    same row and joined left-to-right, so table cells stay together.
    """
    try:
        blocks = page.get_text("blocks")     # (x0, y0, x1, y1, text, bno, btype)
    except Exception:  # noqa: BLE001
        return ""

    items = []
    for b in blocks:
        if len(b) < 5:
            continue
        x0, y0, x1, y1, txt = b[0], b[1], b[2], b[3], b[4]
        if not isinstance(txt, str) or not txt.strip():
            continue
        items.append((y0, y1, x0, txt.strip()))

    if not items:
        return ""

    items.sort(key=lambda t: (t[0], t[2]))
    rows: list[list[tuple[float, str]]] = []
    current: list[tuple[float, str]] = []
    centre = None

    for y0, y1, x0, txt in items:
        c = (y0 + y1) / 2.0
        if centre is None or abs(c - centre) <= y_tol:
            current.append((x0, txt))
            centre = c if centre is None else (centre + c) / 2.0
        else:
            rows.append(current)
            current = [(x0, txt)]
            centre = c
    if current:
        rows.append(current)

    out = []
    for row in rows:
        row.sort(key=lambda t: t[0])
        cells = [t.replace("\n", " ").strip() for _, t in row]
        out.append("   ".join(c for c in cells if c))
    return "\n".join(out)


def _zip_office(blob: bytes) -> str:
    try:
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            names = [n for n in z.namelist()
                     if n in ("word/document.xml", "content.xml")]
            xml = b"".join(z.read(n) for n in names).decode("utf-8", "ignore")
        # Table cells -> tab, paragraphs -> newline, so boxes stay on one line.
        xml = re.sub(r"</w:tc>|</table:table-cell>", "\t", xml)
        xml = re.sub(r"</w:tr>|</table:table-row>", "\n", xml)
        xml = re.sub(r"</w:p>|</text:p>", "\n", xml)
        xml = re.sub(r"<w:tab[^>]*/>", "\t", xml)
        return re.sub(r"<[^>]+>", "", xml)
    except Exception:  # noqa: BLE001
        return ""


def _rtf(blob: bytes) -> str:
    s = blob.decode("latin-1", "ignore")
    s = re.sub(r"\\'([0-9a-fA-F]{2})", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"\\cell", "\t", s)
    s = re.sub(r"\\row", "\n", s)
    s = re.sub(r"\\par[d]?", "\n", s)
    s = re.sub(r"\\[a-zA-Z]+-?\d* ?", "", s)
    return s.replace("{", "").replace("}", "")


def _legacy_doc(blob: bytes) -> str:
    out = "\n".join(re.findall(r"[\x20-\x7E\n\r\t\xa3]{6,}",
                               blob.decode("latin-1", "ignore")))
    try:
        alt = "\n".join(re.findall(r"[\x20-\x7E\n\r\t\xa3]{6,}",
                                   blob.decode("utf-16-le", "ignore")))
        if len(alt) > len(out):
            out = alt
    except Exception:  # noqa: BLE001
        pass
    return out


# ------------------------------------------------------------------ tidy
_WS = re.compile(r"[ \t\xa0]{2,}")
_NL = re.compile(r"\n{3,}")

# PDF extractors emit several different glyphs for the pound sign.
POUND_VARIANTS = ["\uf0a3", "\u00a3", "\uf02d", "\ue0a3", "GBP"]


def clean(text: str) -> str:
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    for a, b in [("\u2019", "'"), ("\u2018", "'"), ("\u201c", '"'),
                 ("\u201d", '"'), ("\u2013", "-"), ("\u2014", "-"),
                 ("\u00a0", " ")]:
        text = text.replace(a, b)
    for v in POUND_VARIANTS:
        text = text.replace(v, "£")
    # "£ 1300" -> "£1300" so the money pattern sees a tight token
    text = re.sub(r"£\s+(?=\d)", "£", text)
    text = _WS.sub("   ", text)
    text = _NL.sub("\n\n", text)
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


def full_text(decision_url: str) -> tuple[str, str]:
    page = decision_page(decision_url)
    doc_url = page["attachments"][0] if page["attachments"] else ""
    doc_text = document_text(doc_url) if doc_url else ""
    return (page["html_text"] + "\n\n" + doc_text).strip(), doc_url
