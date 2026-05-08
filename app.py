"""
H&A · PDF Vencimientos Editable
Convierte los avisos de vencimientos en PDFs con checkboxes interactivos.
"""

import io
import streamlit as st
import pdfplumber
import fitz  # pymupdf
from PIL import Image, ImageDraw
from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject, BooleanObject, DecodedStreamObject,
    DictionaryObject, FloatObject, IndirectObject, NameObject,
    NumberObject, TextStringObject,
)

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="PDF Vencimientos Editable · H&A",
    page_icon="📋",
    layout="centered",
)

st.markdown("""
<style>
    .main { max-width: 860px; }
    .step-badge {
        display:inline-block; background:#9b0000; color:white;
        border-radius:50%; width:28px; height:28px; text-align:center;
        line-height:28px; font-weight:bold; margin-right:8px; font-size:14px;
    }
    .step-title { font-size:20px; font-weight:600; margin-bottom:12px; }
    .info-box {
        background:#f8f8f8; border-left:4px solid #9b0000;
        padding:10px 16px; border-radius:4px; margin-bottom:16px;
        font-size:14px;
    }
</style>
""", unsafe_allow_html=True)

# ── Header ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns([1, 5])
with col1:
    st.markdown("## 📋")
with col2:
    st.markdown("## PDF Vencimientos Editable")
    st.caption("Herrero & Asociados · Herramienta interna")

st.divider()

# ── Session state ─────────────────────────────────────────────────────────────
if "step" not in st.session_state:
    st.session_state.step = 1
if "pdf_bytes" not in st.session_state:
    st.session_state.pdf_bytes = None
if "checkboxes" not in st.session_state:
    st.session_state.checkboxes = []
if "output_bytes" not in st.session_state:
    st.session_state.output_bytes = None


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════════════════════

MIN_CB = 5.0    # minimum checkbox side (pt)
MAX_CB = 20.0   # maximum checkbox side (pt)

def detect_checkboxes(pdf_bytes: bytes) -> list[dict]:
    """
    Detect small square-ish rectangles in the PDF and find nearby text labels.
    Returns a list of dicts with page, coords, label, and a default enabled flag.
    """
    results = []
    seen = set()

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages):
            ph = float(page.height)
            pw = float(page.width)

            # Collect all text words with bbox
            words = page.extract_words(keep_blank_chars=False, extra_attrs=["size"])

            rects = page.rects or []
            for r in rects:
                x0, top, x1, bottom = r["x0"], r["top"], r["x1"], r["bottom"]
                w = x1 - x0
                h = bottom - top
                # Filter to checkbox-sized squares
                if not (MIN_CB <= w <= MAX_CB and MIN_CB <= h <= MAX_CB):
                    continue
                # Deduplicate overlapping detections (same center ±2pt)
                cx, cy = round((x0 + x1) / 2, 0), round((top + bottom) / 2, 0)
                key = (page_num, cx, cy)
                if key in seen:
                    continue
                seen.add(key)

                # Find nearest text label (within 60pt, same row, left or right)
                label = ""
                best_dist = 999
                for w_obj in words:
                    wy = (w_obj["top"] + w_obj["bottom"]) / 2
                    if abs(wy - cy) >= 12:
                        continue
                    # Distance: left side (label ends before checkbox starts)
                    left_dist  = x0 - w_obj["x1"]
                    # Distance: right side (label starts after checkbox ends)
                    right_dist = w_obj["x0"] - x1
                    dist = min(d for d in (left_dist, right_dist) if 0 <= d <= 60)                            if any(0 <= d <= 60 for d in (left_dist, right_dist)) else 999
                    if dist < best_dist:
                        best_dist = dist
                        label = w_obj["text"]

                results.append({
                    "page":    page_num,
                    "x0":      x0,
                    "top":     top,
                    "x1":      x1,
                    "bottom":  bottom,
                    "cx":      cx,
                    "cy":      cy,
                    "ph":      ph,
                    "pw":      pw,
                    "label":   label,
                    "enabled": True,
                })

    return results


def render_page(pdf_bytes: bytes, page_num: int,
                checkboxes: list[dict], enabled_ids: set[int],
                dpi: int = 144) -> Image.Image:
    """Render a PDF page as PIL image with checkbox highlights."""
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    page = doc[page_num]
    mat = fitz.Matrix(dpi / 72, dpi / 72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    doc.close()

    scale_x = pix.width  / page.rect.width
    scale_y = pix.height / page.rect.height

    draw = ImageDraw.Draw(img, "RGBA")
    for i, cb in enumerate(checkboxes):
        if cb["page"] != page_num:
            continue
        ix0 = cb["x0"] * scale_x
        iy0 = cb["top"] * scale_y
        ix1 = cb["x1"] * scale_x
        iy1 = cb["bottom"] * scale_y
        if i in enabled_ids:
            # Highlighted = semi-transparent red fill + solid border
            draw.rectangle([ix0-2, iy0-2, ix1+2, iy1+2],
                           fill=(155, 0, 0, 60), outline=(155, 0, 0, 220), width=2)
        else:
            # Dimmed
            draw.rectangle([ix0-2, iy0-2, ix1+2, iy1+2],
                           fill=(180, 180, 180, 40), outline=(180, 180, 180, 160), width=1)
    return img


def to_pdf_rect(x0, top, x1, bottom, ph):
    return ArrayObject([
        FloatObject(x0),
        FloatObject(ph - bottom),
        FloatObject(x1),
        FloatObject(ph - top),
    ])

def make_ap_stream(content: str, w: float, h: float) -> DecodedStreamObject:
    s = DecodedStreamObject()
    s.set_data(content.encode())
    s.update({
        NameObject("/Type"):    NameObject("/XObject"),
        NameObject("/Subtype"): NameObject("/Form"),
        NameObject("/BBox"):    ArrayObject([FloatObject(0), FloatObject(0),
                                             FloatObject(w), FloatObject(h)]),
    })
    return s

def get_indirect_ref(writer, obj):
    for i, o in enumerate(writer._objects):
        if o is obj:
            return IndirectObject(i + 1, 0, writer)
    raise ValueError("Object not found in writer")

def generate_editable_pdf(pdf_bytes: bytes, selected_checkboxes: list[dict]) -> bytes:
    """Add AcroForm checkboxes to the PDF at the selected positions."""
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

    for idx, cb in enumerate(selected_checkboxes):
        page_obj = writer.pages[cb["page"]]
        if not hasattr(page_obj, "_checkbox_ref_cached"):
            page_obj._checkbox_ref_cached = get_indirect_ref(writer, page_obj)
        page_ref = page_obj._checkbox_ref_cached

        if NameObject("/Annots") not in page_obj:
            page_obj[NameObject("/Annots")] = ArrayObject()

        x0, top, x1, bottom, ph = cb["x0"], cb["top"], cb["x1"], cb["bottom"], cb["ph"]
        w = x1 - x0
        h = bottom - top
        rect = to_pdf_rect(x0, top, x1, bottom, ph)

        label = cb.get("label", "") or f"cb_{idx}"
        field_name = f"check_{idx}_{label}"

        on_content  = f"q 0.6 0.0 0.0 rg 1 1 {w-2:.1f} {h-2:.1f} re f Q"
        on_ref  = writer._add_object(make_ap_stream(on_content,  w, h))
        off_ref = writer._add_object(make_ap_stream("", w, h))

        ap = DictionaryObject({
            NameObject("/N"): DictionaryObject({
                NameObject("/On"):  on_ref,
                NameObject("/Off"): off_ref,
            })
        })

        widget = DictionaryObject({
            NameObject("/Type"):    NameObject("/Annot"),
            NameObject("/Subtype"): NameObject("/Widget"),
            NameObject("/FT"):      NameObject("/Btn"),
            NameObject("/T"):       TextStringObject(field_name),
            NameObject("/V"):       NameObject("/Off"),
            NameObject("/AS"):      NameObject("/Off"),
            NameObject("/Ff"):      NumberObject(0),
            NameObject("/Rect"):    rect,
            NameObject("/P"):       page_ref,
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

uploaded = st.file_uploader(
    "Arrastra aquí el PDF generado por hyaip.com",
    type=["pdf"],
    label_visibility="collapsed",
)

if uploaded:
    pdf_bytes = uploaded.read()
    if pdf_bytes != st.session_state.pdf_bytes:
        # New file — reset state
        st.session_state.pdf_bytes    = pdf_bytes
        st.session_state.step         = 2
        st.session_state.checkboxes   = []
        st.session_state.output_bytes = None

        with st.spinner("Analizando el PDF…"):
            st.session_state.checkboxes = detect_checkboxes(pdf_bytes)

        if not st.session_state.checkboxes:
            st.warning("No se han detectado checkboxes en este PDF.")
            st.session_state.step = 1
        else:
            st.success(f"✓ {len(st.session_state.checkboxes)} checkboxes detectados")


# ══════════════════════════════════════════════════════════════════════════════
# PASO 2 — SELECCIÓN VISUAL
# ══════════════════════════════════════════════════════════════════════════════

if st.session_state.step >= 2 and st.session_state.checkboxes:
    st.divider()
    st.markdown('<div class="step-title"><span class="step-badge">2</span>Elige qué checkboxes activar</div>', unsafe_allow_html=True)
    st.markdown('<div class="info-box">Los cuadros <b>resaltados en rojo</b> quedarán interactivos en el PDF final. Desmarca los que no quieras activar.</div>', unsafe_allow_html=True)

    checkboxes = st.session_state.checkboxes
    pages_with_cb = sorted(set(cb["page"] for cb in checkboxes))

    # Build per-checkbox toggle state
    if "cb_enabled" not in st.session_state or len(st.session_state.cb_enabled) != len(checkboxes):
        st.session_state.cb_enabled = [True] * len(checkboxes)

    # Show selection table
    st.markdown("**Checkboxes detectados:**")
    cols = st.columns([1, 2, 3, 1])
    cols[0].markdown("**Activar**")
    cols[1].markdown("**Página**")
    cols[2].markdown("**Etiqueta**")
    cols[3].markdown("**Posición**")

    for i, cb in enumerate(checkboxes):
        c1, c2, c3, c4 = st.columns([1, 2, 3, 1])
        enabled = c1.checkbox("", value=st.session_state.cb_enabled[i], key=f"cb_{i}", label_visibility="collapsed")
        st.session_state.cb_enabled[i] = enabled
        c2.write(f"Pág. {cb['page'] + 1}")
        c3.write(cb["label"] if cb["label"] else "—")
        c4.write(f"({cb['cx']:.0f}, {cb['cy']:.0f})")

    # Preview
    st.markdown("**Vista previa por página:**")
    enabled_ids = {i for i, e in enumerate(st.session_state.cb_enabled) if e}

    for page_num in pages_with_cb:
        page_cbs = [cb for cb in checkboxes if cb["page"] == page_num]
        if not page_cbs:
            continue
        with st.spinner(f"Generando preview página {page_num + 1}…"):
            img = render_page(st.session_state.pdf_bytes, page_num, checkboxes, enabled_ids)
        st.image(img, caption=f"Página {page_num + 1}", use_container_width=True)

    st.divider()

    # ══════════════════════════════════════════════════════════════════════════
    # PASO 3 — GENERAR Y DESCARGAR
    # ══════════════════════════════════════════════════════════════════════════
    st.markdown('<div class="step-title"><span class="step-badge">3</span>Genera el PDF editable</div>', unsafe_allow_html=True)

    n_selected = sum(st.session_state.cb_enabled)
    if n_selected == 0:
        st.warning("Selecciona al menos un checkbox para continuar.")
    else:
        st.markdown(f'<div class="info-box">Se activarán <b>{n_selected} checkboxes</b> en el PDF final.</div>', unsafe_allow_html=True)

        if st.button("⚡ Generar PDF editable", type="primary", use_container_width=True):
            selected = [cb for i, cb in enumerate(checkboxes) if st.session_state.cb_enabled[i]]
            with st.spinner("Generando…"):
                output = generate_editable_pdf(st.session_state.pdf_bytes, selected)
            st.session_state.output_bytes = output
            st.success("✓ PDF generado correctamente")

        if st.session_state.output_bytes:
            fname = uploaded.name.replace(".pdf", "_editable.pdf") if uploaded else "vencimientos_editable.pdf"
            st.download_button(
                label="⬇️ Descargar PDF editable",
                data=st.session_state.output_bytes,
                file_name=fname,
                mime="application/pdf",
                use_container_width=True,
            )
