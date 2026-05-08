"""
H&A · PDF Vencimientos Editable
Haz clic directamente sobre los cuadros del PDF para activarlos.
"""

import io
import base64
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
import pdfplumber
import fitz
from PIL import Image, ImageDraw, ImageFont
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, BooleanObject, DecodedStreamObject,
    DictionaryObject, FloatObject, IndirectObject, NameObject,
    NumberObject, TextStringObject,
)

# ── Config ─────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF Vencimientos Editable · H&A",
    page_icon="📋",
    layout="wide",
)

st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background: #f5f5f5; }
    .block-container { padding-top: 1.5rem; }
    .step-badge {
        display:inline-block; background:#9b0000; color:white;
        border-radius:50%; width:26px; height:26px; text-align:center;
        line-height:26px; font-weight:bold; margin-right:8px; font-size:13px;
    }
    .step-title { font-size:18px; font-weight:600; margin-bottom:10px; }
    .hint { background:#fff3cd; border-left:4px solid #e6a817;
            padding:8px 14px; border-radius:4px; font-size:13px; margin-bottom:12px; }
    .ok   { background:#d4edda; border-left:4px solid #28a745;
            padding:8px 14px; border-radius:4px; font-size:13px; margin-bottom:12px; }
</style>
""", unsafe_allow_html=True)

# ── Header ─────────────────────────────────────────────────────────────────────
st.markdown("## 📋 PDF Vencimientos Editable")
st.caption("Herrero & Asociados · Herramienta interna")
st.divider()

# ── Session state ──────────────────────────────────────────────────────────────
for key, default in [
    ("pdf_bytes", None),
    ("checkboxes", []),
    ("cb_enabled", []),
    ("output_bytes", None),
    ("current_page", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default

DPI       = 150
MIN_CB    = 5.0
MAX_CB    = 20.0
HIT_PAD   = 12   # extra pixels around each checkbox that count as a click

# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def detect_checkboxes(pdf_bytes: bytes) -> list[dict]:
    results = []
    seen = set()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            ph = float(page.height)
            words = page.extract_words(keep_blank_chars=False)
            for r in (page.rects or []):
                x0, top, x1, bottom = r["x0"], r["top"], r["x1"], r["bottom"]
                w, h = x1 - x0, bottom - top
                if not (MIN_CB <= w <= MAX_CB and MIN_CB <= h <= MAX_CB):
                    continue
                cx = round((x0 + x1) / 2, 0)
                cy = round((top + bottom) / 2, 0)
                key = (page_num, cx, cy)
                if key in seen:
                    continue
                seen.add(key)
                label = ""
                best_dist = 999
                for wo in words:
                    wy = (wo["top"] + wo["bottom"]) / 2
                    if abs(wy - cy) >= 12:
                        continue
                    ld = x0 - wo["x1"]
                    rd = wo["x0"] - x1
                    dist = min((d for d in (ld, rd) if 0 <= d <= 60), default=999)
                    if dist < best_dist:
                        best_dist = dist
                        label = wo["text"]
                results.append({
                    "page": page_num, "x0": x0, "top": top,
                    "x1": x1, "bottom": bottom,
                    "cx": cx, "cy": cy, "ph": ph, "label": label,
                })
    return results


def get_scale(pdf_bytes: bytes, page_num: int, dpi: int = DPI):
    """Return (scale_x, scale_y, img_w, img_h) for a given page."""
    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    sx = pix.width  / page.rect.width
    sy = pix.height / page.rect.height
    doc.close()
    return sx, sy, pix.width, pix.height


def render_page(pdf_bytes: bytes, page_num: int,
                checkboxes: list[dict], enabled: list[bool],
                dpi: int = DPI) -> Image.Image:
    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    page_w = page.rect.width   # capture before closing
    page_h_pt = page.rect.height
    doc.close()

    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    sx = pix.width  / page_w
    sy = pix.height / page_h_pt
    draw = ImageDraw.Draw(img, "RGBA")

    page_cbs = [(i, cb) for i, cb in enumerate(checkboxes) if cb["page"] == page_num]
    for i, cb in page_cbs:
        ix0 = cb["x0"] * sx - HIT_PAD
        iy0 = cb["top"] * sy - HIT_PAD
        ix1 = cb["x1"] * sx + HIT_PAD
        iy1 = cb["bottom"] * sy + HIT_PAD
        if enabled[i]:
            # Active: red fill + strong border
            draw.rectangle([ix0, iy0, ix1, iy1],
                           fill=(155, 0, 0, 70), outline=(155, 0, 0, 255), width=2)
            # Checkmark
            mx, my = (ix0 + ix1) / 2, (iy0 + iy1) / 2
            s = (ix1 - ix0) * 0.28
            draw.line([mx - s, my, mx - s*0.2, my + s, mx + s, my - s],
                      fill=(155, 0, 0, 255), width=2)
        else:
            # Inactive: grey dashed border
            draw.rectangle([ix0, iy0, ix1, iy1],
                           fill=(200, 200, 200, 30), outline=(160, 160, 160, 180), width=1)
    return img


def cb_at_click(click_x, click_y, checkboxes, page_num, sx, sy):
    """Return index of checkbox hit by a click, or None."""
    for i, cb in enumerate(checkboxes):
        if cb["page"] != page_num:
            continue
        ix0 = cb["x0"] * sx - HIT_PAD
        iy0 = cb["top"] * sy - HIT_PAD
        ix1 = cb["x1"] * sx + HIT_PAD
        iy1 = cb["bottom"] * sy + HIT_PAD
        if ix0 <= click_x <= ix1 and iy0 <= click_y <= iy1:
            return i
    return None


def generate_editable_pdf(pdf_bytes: bytes, checkboxes: list[dict],
                           enabled: list[bool]) -> bytes:
    selected = [cb for i, cb in enumerate(checkboxes) if enabled[i]]
    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)

    fields_array = ArrayObject()
    acroform = DictionaryObject({
        NameObject("/Fields"):          fields_array,
        NameObject("/NeedAppearances"): BooleanObject(True),
        NameObject("/DA"):              TextStringObject("/Helvetica 8 Tf 0 g"),
    })
    writer._root_object[NameObject("/AcroForm")] = acroform

    def get_ref(obj):
        for i, o in enumerate(writer._objects):
            if o is obj:
                return IndirectObject(i + 1, 0, writer)
        raise ValueError

    def ap_stream(content, w, h):
        s = DecodedStreamObject()
        s.set_data(content.encode())
        s.update({
            NameObject("/Type"):    NameObject("/XObject"),
            NameObject("/Subtype"): NameObject("/Form"),
            NameObject("/BBox"):    ArrayObject([FloatObject(0), FloatObject(0),
                                                 FloatObject(w), FloatObject(h)]),
        })
        return s

    for idx, cb in enumerate(selected):
        page_obj = writer.pages[cb["page"]]
        if NameObject("/Annots") not in page_obj:
            page_obj[NameObject("/Annots")] = ArrayObject()

        x0, top, x1, bottom, ph = cb["x0"], cb["top"], cb["x1"], cb["bottom"], cb["ph"]
        w, h = x1 - x0, bottom - top
        rect = ArrayObject([FloatObject(x0), FloatObject(ph - bottom),
                             FloatObject(x1), FloatObject(ph - top)])
        label = cb.get("label", "") or f"cb_{idx}"

        on_ref  = writer._add_object(ap_stream(f"q 0.6 0 0 rg 1 1 {w-2:.1f} {h-2:.1f} re f Q", w, h))
        off_ref = writer._add_object(ap_stream("", w, h))
        ap = DictionaryObject({NameObject("/N"): DictionaryObject({
            NameObject("/On"): on_ref, NameObject("/Off"): off_ref})})

        widget = DictionaryObject({
            NameObject("/Type"):    NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"):      NameObject("/Btn"),
            NameObject("/T"):       TextStringObject(f"check_{idx}_{label}"),
            NameObject("/V"):       NameObject("/Off"),
            NameObject("/AS"):      NameObject("/Off"),
            NameObject("/Ff"):      NumberObject(0),
            NameObject("/Rect"):    rect,
            NameObject("/P"):       get_ref(page_obj),
            NameObject("/AP"):      ap,
            NameObject("/DA"):      TextStringObject("/Helvetica 8 Tf 0 g"),
            NameObject("/MK"):      DictionaryObject({
                NameObject("/BC"): ArrayObject([FloatObject(0.4), FloatObject(0), FloatObject(0)]),
                NameObject("/BG"): ArrayObject([FloatObject(1), FloatObject(1), FloatObject(1)]),
            }),
        })
        widget_ref = writer._add_object(widget)
        page_obj[NameObject("/Annots")].append(widget_ref)
        fields_array.append(widget_ref)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# PASO 1 — SUBIR PDF
# ══════════════════════════════════════════════════════════════════════════════
st.markdown('<div class="step-title"><span class="step-badge">1</span>Sube el aviso de vencimientos</div>', unsafe_allow_html=True)

uploaded = st.file_uploader("PDF hyaip.com", type=["pdf"], label_visibility="collapsed")

if uploaded:
    pdf_bytes = uploaded.read()
    if pdf_bytes != st.session_state.pdf_bytes:
        st.session_state.pdf_bytes    = pdf_bytes
        st.session_state.output_bytes = None
        st.session_state.current_page = 0
        with st.spinner("Analizando checkboxes…"):
            cbs = detect_checkboxes(pdf_bytes)
        st.session_state.checkboxes = cbs
        st.session_state.cb_enabled = [True] * len(cbs)
        if not cbs:
            st.warning("No se han detectado checkboxes en este PDF.")

if st.session_state.checkboxes:
    n = len(st.session_state.checkboxes)
    n_on = sum(st.session_state.cb_enabled)
    st.markdown(f'<div class="ok">✓ {n} checkboxes detectados · <b>{n_on} activados</b></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# PASO 2 — VISUALIZACIÓN INTERACTIVA
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.pdf_bytes and st.session_state.checkboxes:
    st.divider()
    st.markdown('<div class="step-title"><span class="step-badge">2</span>Haz clic sobre los cuadros para activar / desactivar</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint">🟥 Rojo = se incluirá como campo editable · ⬜ Gris = desactivado · Haz clic para cambiar</div>', unsafe_allow_html=True)

    checkboxes = st.session_state.checkboxes
    pages_with_cb = sorted(set(cb["page"] for cb in checkboxes))
    total_pages   = pages_with_cb

    # Page selector
    page_labels = [f"Página {p+1}" for p in pages_with_cb]
    col_prev, col_sel, col_next = st.columns([1, 4, 1])
    with col_sel:
        sel_label = st.selectbox("Página", page_labels,
                                  index=min(st.session_state.current_page, len(page_labels)-1),
                                  label_visibility="collapsed")
    page_idx = pages_with_cb[page_labels.index(sel_label)]
    st.session_state.current_page = page_labels.index(sel_label)

    with col_prev:
        if st.button("◀", use_container_width=True) and st.session_state.current_page > 0:
            st.session_state.current_page -= 1
            st.rerun()
    with col_next:
        if st.button("▶", use_container_width=True) and st.session_state.current_page < len(page_labels)-1:
            st.session_state.current_page += 1
            st.rerun()

    # Render current page
    img = render_page(
        st.session_state.pdf_bytes, page_idx,
        checkboxes, st.session_state.cb_enabled
    )

    # Scale for display (fit to ~700px width)
    display_w = 700
    scale_factor = display_w / img.width
    display_img = img.resize((display_w, int(img.height * scale_factor)), Image.LANCZOS)

    # Click detector
    coords = streamlit_image_coordinates(display_img, key=f"img_{page_idx}")

    if coords:
        # Convert display coords back to full-res coords
        full_x = coords["x"] / scale_factor
        full_y = coords["y"] / scale_factor
        sx, sy, _, _ = get_scale(st.session_state.pdf_bytes, page_idx)
        hit = cb_at_click(full_x, full_y, checkboxes, page_idx, sx, sy)
        if hit is not None:
            st.session_state.cb_enabled[hit] = not st.session_state.cb_enabled[hit]
            st.session_state.output_bytes = None
            st.rerun()

    # Selección rápida con botones
    n_on = sum(st.session_state.cb_enabled)
    c1, c2, c3 = st.columns(3)
    if c1.button("✅ Activar todos", use_container_width=True):
        st.session_state.cb_enabled = [True] * len(checkboxes)
        st.session_state.output_bytes = None
        st.rerun()
    if c2.button("☐ Desactivar todos", use_container_width=True):
        st.session_state.cb_enabled = [False] * len(checkboxes)
        st.session_state.output_bytes = None
        st.rerun()
    if c3.button("🔄 Invertir selección", use_container_width=True):
        st.session_state.cb_enabled = [not e for e in st.session_state.cb_enabled]
        st.session_state.output_bytes = None
        st.rerun()

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 3 — GENERAR Y DESCARGAR
    # ══════════════════════════════════════════════════════════════════════════
    st.divider()
    st.markdown('<div class="step-title"><span class="step-badge">3</span>Genera el PDF editable</div>', unsafe_allow_html=True)

    n_sel = sum(st.session_state.cb_enabled)
    if n_sel == 0:
        st.warning("Activa al menos un checkbox.")
    else:
        st.markdown(f'<div class="ok">{n_sel} de {len(checkboxes)} checkboxes se incluirán como campos editables.</div>', unsafe_allow_html=True)

        if st.button("⚡ Generar PDF editable", type="primary", use_container_width=True):
            with st.spinner("Generando…"):
                out = generate_editable_pdf(
                    st.session_state.pdf_bytes,
                    checkboxes,
                    st.session_state.cb_enabled
                )
            st.session_state.output_bytes = out

        if st.session_state.output_bytes:
            fname = (uploaded.name.replace(".pdf", "_editable.pdf")
                     if uploaded else "vencimientos_editable.pdf")
            st.download_button(
                "⬇️ Descargar PDF editable",
                data=st.session_state.output_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
            )
