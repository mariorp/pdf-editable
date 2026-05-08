"""
H&A · Vencimientos — Marcado Sí/No   v4 (UI mejorada)
"""

import io, hashlib
import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates
import pdfplumber
import fitz
from PIL import Image, ImageDraw
from logo_b64 import LOGO_B64

st.set_page_config(
    page_title="Vencimientos · H&A",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@500;700&family=DM+Sans:wght@300;400;500;600&display=swap');

/* ── Reset / base ── */
html, body, [data-testid="stAppViewContainer"] {
    background: #F7F6F3 !important;
    font-family: 'DM Sans', sans-serif;
}
[data-testid="stSidebar"] {
    background: #1A1A1A !important;
    border-right: none !important;
}
[data-testid="stSidebar"] * { color: #E8E3DC !important; }
[data-testid="stSidebarContent"] { padding: 0 !important; }
.block-container { padding: 4rem 2rem 3rem 2rem !important; max-width: 940px; }
/* Hide the default Streamlit top padding */
[data-testid="stHeader"] { display: none !important; }

/* ── Header bar ── */
.ha-header {
    background: linear-gradient(135deg, #8B0000 0%, #5A0000 100%);
    margin: -4rem -2rem 2rem -2rem;
    padding: 2rem 2.5rem 1.4rem;
    display: flex; align-items: center; gap: 20px;
    box-shadow: 0 6px 32px rgba(139,0,0,0.3);
    position: relative;
}
.ha-header-logo-img {
    width: 52px; height: 52px; object-fit: contain;
    border-radius: 6px; flex-shrink: 0;
}
.ha-header-text { display: flex; flex-direction: column; gap: 2px; }
.ha-header-name {
    font-family: 'Playfair Display', serif;
    font-size: 20px; font-weight: 700;
    color: white; letter-spacing: -0.3px; line-height: 1;
}
.ha-header-sub {
    font-family: 'DM Sans', sans-serif; font-weight: 300;
    font-size: 11px; color: rgba(255,255,255,0.5);
    letter-spacing: 2.5px; text-transform: uppercase;
}
.ha-header-sep { width: 1px; height: 40px; background: rgba(255,255,255,0.18); margin: 0 4px; }
.ha-header-title {
    font-family: 'DM Sans', sans-serif; font-weight: 400;
    font-size: 15px; color: rgba(255,255,255,0.8); letter-spacing: 0.2px;
}

/* ── Step pills ── */
.steps-row {
    display: flex; gap: 0; margin-bottom: 2rem;
    border-radius: 10px; overflow: hidden;
    border: 1px solid #E0DDD6; background: white;
    box-shadow: 0 1px 6px rgba(0,0,0,0.06);
}
.step-pill {
    flex: 1; padding: 12px 16px; text-align: center;
    font-size: 12px; font-weight: 500; letter-spacing: 0.5px;
    text-transform: uppercase; color: #999; background: white;
    border-right: 1px solid #E0DDD6; transition: all .2s;
    display: flex; align-items: center; justify-content: center; gap: 8px;
}
.step-pill:last-child { border-right: none; }
.step-pill.active {
    background: #8B0000; color: white;
}
.step-pill.done {
    background: #F9F6F0; color: #8B0000;
}
.step-num {
    width: 22px; height: 22px; border-radius: 50%;
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 11px; font-weight: 700;
    background: rgba(255,255,255,0.25); color: inherit;
}
.step-pill.active .step-num { background: rgba(255,255,255,0.3); }
.step-pill.done .step-num { background: #8B0000; color: white; }

/* ── Cards ── */
.card {
    background: white; border-radius: 12px;
    border: 1px solid #E8E4DC;
    box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    padding: 1.6rem 1.8rem; margin-bottom: 1.4rem;
}
.card-title {
    font-family: 'Playfair Display', serif;
    font-size: 17px; font-weight: 500; color: #1A1A1A;
    margin-bottom: 1rem; padding-bottom: 0.7rem;
    border-bottom: 1px solid #F0ECE4;
    display: flex; align-items: center; gap: 10px;
}
.card-title .icon { font-size: 20px; }

/* ── Badges ── */
.badge-green {
    display: inline-flex; align-items: center; gap: 6px;
    background: #EFF8F1; border: 1px solid #B8DFC0;
    color: #2D7A3F; padding: 6px 12px; border-radius: 6px;
    font-size: 13px; font-weight: 500;
}
.badge-amber {
    display: inline-flex; align-items: center; gap: 6px;
    background: #FFF8EC; border: 1px solid #F0D98C;
    color: #8A6200; padding: 6px 12px; border-radius: 6px;
    font-size: 13px; font-weight: 500;
}
.badge-red {
    display: inline-flex; align-items: center; gap: 6px;
    background: #FDF0F0; border: 1px solid #E8BBBB;
    color: #8B0000; padding: 6px 12px; border-radius: 6px;
    font-size: 13px; font-weight: 500;
}

/* ── Hint box ── */
.hint-box {
    background: #FFF8EC; border-left: 3px solid #D4A017;
    padding: 10px 14px; border-radius: 0 8px 8px 0;
    font-size: 13px; color: #6B4F00; margin-bottom: 1rem;
}

/* ── Streamlit overrides ── */
.stButton > button {
    font-family: 'DM Sans', sans-serif !important;
    font-weight: 500 !important; border-radius: 8px !important;
    border: 1.5px solid #D0CAC0 !important;
    background: white !important; color: #1A1A1A !important;
    transition: all .15s !important; font-size: 13px !important;
    padding: 0.45rem 1rem !important;
}
.stButton > button:hover {
    border-color: #8B0000 !important; color: #8B0000 !important;
    background: #FDF5F5 !important;
}
[data-testid="stBaseButton-primary"] > button,
.stButton > button[kind="primary"] {
    background: #8B0000 !important; color: white !important;
    border-color: #8B0000 !important;
}
[data-testid="stBaseButton-primary"] > button:hover,
.stButton > button[kind="primary"]:hover {
    background: #6B0000 !important; border-color: #6B0000 !important;
    color: white !important;
}
.stDownloadButton > button {
    background: #1A1A1A !important; color: white !important;
    border-color: #1A1A1A !important; font-weight: 600 !important;
    letter-spacing: 0.3px !important;
}
.stDownloadButton > button:hover {
    background: #333 !important; border-color: #333 !important; color: white !important;
}
[data-testid="stFileUploader"] {
    border: 2px dashed #D0CAC0 !important;
    border-radius: 10px !important; background: #FAFAF8 !important;
    padding: 1rem !important;
}
[data-testid="stFileUploader"]:hover { border-color: #8B0000 !important; }
div[data-testid="stSelectbox"] > div > div {
    border-color: #D0CAC0 !important; border-radius: 8px !important;
    font-family: 'DM Sans', sans-serif !important;
}
.stSpinner > div { border-color: #8B0000 transparent transparent !important; }

/* ── Sidebar styles ── */
.sb-header {
    padding: 1.4rem 1.2rem 1rem;
    border-bottom: 1px solid rgba(255,255,255,0.08);
    margin-bottom: 0.5rem;
}
.sb-title {
    font-family: 'Playfair Display', serif;
    font-size: 14px; color: rgba(255,255,255,0.9);
    letter-spacing: 0.3px; margin-bottom: 2px;
}
.sb-subtitle { font-size: 11px; color: rgba(255,255,255,0.4);
    text-transform: uppercase; letter-spacing: 1.5px; }
.sb-item {
    display: flex; align-items: center; justify-content: space-between;
    padding: 7px 1.2rem; font-size: 12px;
    border-bottom: 1px solid rgba(255,255,255,0.04);
    color: rgba(255,255,255,0.7) !important;
}
.sb-item:hover { background: rgba(255,255,255,0.04); }
.sb-badge {
    font-size: 11px; padding: 2px 8px; border-radius: 4px; font-weight: 600;
}
.sb-badge.si  { background: rgba(45,122,63,0.3); color: #7DD896; }
.sb-badge.no  { background: rgba(139,0,0,0.3); color: #F08080; }
.sb-badge.vacio { background: rgba(255,255,255,0.08); color: rgba(255,255,255,0.35); }
.sb-stats {
    padding: 1rem 1.2rem; margin-top: auto;
    border-top: 1px solid rgba(255,255,255,0.08);
    display: flex; gap: 8px; flex-wrap: wrap;
}
.sb-stat { flex: 1; min-width: 60px; text-align: center;
    background: rgba(255,255,255,0.05); border-radius: 8px; padding: 8px 4px; }
.sb-stat-num { font-size: 20px; font-weight: 700;
    color: white; font-family: 'Playfair Display', serif; }
.sb-stat-lbl { font-size: 10px; color: rgba(255,255,255,0.4);
    text-transform: uppercase; letter-spacing: 1px; }
</style>
""", unsafe_allow_html=True)

# ── Constants ──────────────────────────────────────────────────────────────────
DPI     = 150
MIN_CB  = 5.0
MAX_CB  = 20.0
HIT_PAD = 14
DISP_W  = 820

for k, v in [("pdf_bytes", None), ("groups", []), ("selections", {}),
              ("output_bytes", None), ("cur_page_idx", 0), ("last_click", None)]:
    if k not in st.session_state:
        st.session_state[k] = v

# ══════════════════════════════════════════════════════════════════════════════
# LOGIC (sin cambios)
# ══════════════════════════════════════════════════════════════════════════════

def detect_and_group(pdf_bytes):
    raw, seen = [], set()
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pn, page in enumerate(pdf.pages):
            ph = float(page.height)
            words = page.extract_words(keep_blank_chars=False)
            for r in (page.rects or []):
                x0, top, x1, bot = r["x0"], r["top"], r["x1"], r["bottom"]
                w, h = x1-x0, bot-top
                if not (MIN_CB <= w <= MAX_CB and MIN_CB <= h <= MAX_CB): continue
                cx, cy = round((x0+x1)/2,0), round((top+bot)/2,0)
                key = (pn, cx, cy)
                if key in seen: continue
                seen.add(key)
                label, best = "", 999
                for wo in words:
                    wy = (wo["top"]+wo["bottom"])/2
                    if abs(wy-cy) >= 12: continue
                    ld, rd = x0-wo["x1"], wo["x0"]-x1
                    d = min((v for v in (ld,rd) if 0<=v<=60), default=999)
                    if d < best: best, label = d, wo["text"]
                raw.append({"page":pn,"x0":x0,"top":top,"x1":x1,
                             "bottom":bot,"cx":cx,"cy":cy,"ph":ph,"label":label})
    groups, used = [], set()
    for i, cb in enumerate(raw):
        if i in used: continue
        for j, cb2 in enumerate(raw):
            if j in used or j==i: continue
            if cb2["page"]!=cb["page"]: continue
            if abs(cb2["cy"]-cb["cy"])>8: continue
            if cb2["label"]=="No" or (cb2["cx"]>cb["cx"] and cb2["label"]==""):
                si_cb, no_cb = (cb,cb2) if cb["cx"]<cb2["cx"] else (cb2,cb)
                groups.append({"id":len(groups),"page":cb["page"],"ph":cb["ph"],
                                "si":si_cb,"no":no_cb})
                used.add(i); used.add(j); break
    return groups


@st.cache_data(show_spinner=False)
def render_base(pdf_bytes, page_num):
    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    page = doc[page_num]
    mat = fitz.Matrix(DPI/72, DPI/72)
    pix = page.get_pixmap(matrix=mat, alpha=False)
    pw, ph = page.rect.width, page.rect.height
    doc.close()
    img = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
    return img, pix.width/pw, pix.height/ph


def draw_overlay(base, groups, selections, page_num, sx, sy):
    img = base.copy()
    draw = ImageDraw.Draw(img, "RGBA")
    for g in groups:
        if g["page"] != page_num: continue
        sel = selections.get(g["id"])
        for which, cb in (("si", g["si"]), ("no", g["no"])):
            ix0 = cb["x0"]*sx - HIT_PAD
            iy0 = cb["top"]*sy - HIT_PAD
            ix1 = cb["x1"]*sx + HIT_PAD
            iy1 = cb["bottom"]*sy + HIT_PAD
            if sel == which:
                color = (45,122,63) if which=="si" else (139,0,0)
                draw.rectangle([ix0,iy0,ix1,iy1], fill=(*color,70),
                               outline=(*color,230), width=2)
                mx, my = (ix0+ix1)/2, (iy0+iy1)/2
                s = (ix1-ix0)*0.3
                draw.line([mx-s,my-s,mx+s,my+s], fill=(*color,230), width=2)
                draw.line([mx+s,my-s,mx-s,my+s], fill=(*color,230), width=2)
            else:
                draw.rectangle([ix0,iy0,ix1,iy1], fill=(80,100,160,12),
                               outline=(100,120,180,100), width=1)
    return img


def group_at_click(fx, fy, groups, page_num, sx, sy):
    for g in groups:
        if g["page"] != page_num: continue
        for which, cb in (("si",g["si"]),("no",g["no"])):
            if (cb["x0"]*sx-HIT_PAD <= fx <= cb["x1"]*sx+HIT_PAD and
                cb["top"]*sy-HIT_PAD <= fy <= cb["bottom"]*sy+HIT_PAD):
                return g["id"], which
    return None


def generate_marked_pdf(pdf_bytes, groups, selections):
    doc = fitz.open(stream=io.BytesIO(pdf_bytes), filetype="pdf")
    GREEN = (0.18, 0.48, 0.25)
    RED   = (0.55, 0.0,  0.0)
    for g in groups:
        sel = selections.get(g["id"])
        if not sel: continue
        page = doc[g["page"]]
        cb = g[sel]
        color = GREEN if sel=="si" else RED
        rect = fitz.Rect(cb["x0"], cb["top"], cb["x1"], cb["bottom"])
        page.draw_rect(rect, color=color, fill=color, fill_opacity=0.2, width=0)
        m = 1.5
        x0,y0,x1,y1 = rect.x0+m, rect.y0+m, rect.x1-m, rect.y1-m
        page.draw_line(fitz.Point(x0,y0), fitz.Point(x1,y1), color=color, width=1.3)
        page.draw_line(fitz.Point(x1,y0), fitz.Point(x0,y1), color=color, width=1.3)
    buf = io.BytesIO(); doc.save(buf); doc.close()
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════════════════════

groups     = st.session_state.groups
selections = st.session_state.selections

with st.sidebar:
    st.markdown(f"""
    <div class="sb-header">
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:6px">
            <img src="data:image/png;base64,{LOGO_B64}" 
                 style="width:34px;height:34px;object-fit:contain;border-radius:4px">
            <div>
                <div class="sb-title">Herrero &amp; Asociados</div>
                <div class="sb-subtitle">Vencimientos</div>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    if groups:
        pages_with_g = sorted(set(g["page"] for g in groups))
        n_si  = sum(1 for v in selections.values() if v=="si")
        n_no  = sum(1 for v in selections.values() if v=="no")
        n_vac = len(groups) - n_si - n_no

        st.markdown(f"""
        <div class="sb-stats">
            <div class="sb-stat">
                <div class="sb-stat-num">{len(groups)}</div>
                <div class="sb-stat-lbl">Total</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-num" style="color:#7DD896">{n_si}</div>
                <div class="sb-stat-lbl">Sí</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-num" style="color:#F08080">{n_no}</div>
                <div class="sb-stat-lbl">No</div>
            </div>
            <div class="sb-stat">
                <div class="sb-stat-num" style="color:rgba(255,255,255,0.4)">{n_vac}</div>
                <div class="sb-stat-lbl">Pendiente</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        items_html = ""
        for i, g in enumerate(groups):
            sel = selections.get(g["id"])
            badge_cls = "si" if sel=="si" else ("no" if sel=="no" else "vacio")
            badge_txt = "✓ Sí" if sel=="si" else ("✗ No" if sel=="no" else "—")
            items_html += f'<div class="sb-item"><span>Exp. {i+1} · Pág.{g["page"]+1}</span><span class="sb-badge {badge_cls}">{badge_txt}</span></div>'
        st.markdown(items_html, unsafe_allow_html=True)
    else:
        st.markdown('<div style="padding:1.2rem;font-size:13px;color:rgba(255,255,255,0.35);text-align:center;">Sube un PDF para comenzar</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MAIN
# ══════════════════════════════════════════════════════════════════════════════

# Header
st.markdown(f"""
<div class="ha-header">
    <img class="ha-header-logo-img" src="data:image/png;base64,{LOGO_B64}" alt="H&A logo">
    <div class="ha-header-text">
        <div class="ha-header-name">Herrero &amp; Asociados</div>
        <div class="ha-header-sub">Propiedad Industrial</div>
    </div>
    <div class="ha-header-sep"></div>
    <div class="ha-header-title">Marcado de Vencimientos &nbsp;·&nbsp; Sí / No</div>
</div>
""", unsafe_allow_html=True)

# Determine step
has_pdf    = st.session_state.pdf_bytes is not None
has_groups = bool(groups)
has_output = st.session_state.output_bytes is not None
step = 1 if not has_pdf else (3 if has_output else 2)

# Step pills
def pill(n, label, icon, current):
    cls = "active" if current==n else ("done" if current>n else "")
    return f'<div class="step-pill {cls}"><span class="step-num">{n}</span>{icon} {label}</div>'

st.markdown(f"""
<div class="steps-row">
    {pill(1,"Subir PDF","📄",step)}
    {pill(2,"Marcar Sí / No","✏️",step)}
    {pill(3,"Descargar","⬇️",step)}
</div>
""", unsafe_allow_html=True)

# ── PASO 1 ─────────────────────────────────────────────────────────────────────
st.markdown('<div class="card"><div class="card-title"><span class="icon">📄</span>Sube el aviso de vencimientos</div>', unsafe_allow_html=True)
uploaded = st.file_uploader("PDF generado por hyaip.com", type=["pdf"],
                             label_visibility="collapsed")
if uploaded:
    raw = uploaded.read()
    h = hashlib.md5(raw).hexdigest()
    prev_h = hashlib.md5(st.session_state.pdf_bytes or b"").hexdigest()
    if h != prev_h:
        st.session_state.pdf_bytes    = raw
        st.session_state.output_bytes = None
        st.session_state.cur_page_idx = 0
        st.session_state.last_click   = None
        st.session_state.selections   = {}
        with st.spinner("Analizando expedientes…"):
            st.session_state.groups = detect_and_group(raw)
        groups = st.session_state.groups
        selections = st.session_state.selections
        st.rerun()

if has_groups:
    n_si  = sum(1 for v in selections.values() if v=="si")
    n_no  = sum(1 for v in selections.values() if v=="no")
    n_vac = len(groups) - n_si - n_no
    st.markdown(f'<div class="badge-green">✓ &nbsp;{len(groups)} expedientes detectados</div>', unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ── PASO 2 ─────────────────────────────────────────────────────────────────────
if has_pdf and has_groups:
    st.markdown('<div class="card"><div class="card-title"><span class="icon">✏️</span>Marca Sí o No para cada expediente</div>', unsafe_allow_html=True)
    st.markdown('<div class="hint-box">Haz clic directamente sobre el cuadro <b>Sí</b> o <b>No</b> en el PDF · Clic de nuevo para desmarcar · Verde = Sí · Rojo = No</div>', unsafe_allow_html=True)

    pages_with_g = sorted(set(g["page"] for g in groups))
    page_labels  = [f"Página {p+1}" for p in pages_with_g]
    idx = min(st.session_state.cur_page_idx, len(page_labels)-1)

    # Navegación de páginas
    cp, cs, cn = st.columns([1, 5, 1])
    with cp:
        if st.button("◀", use_container_width=True, key="prev") and idx > 0:
            st.session_state.cur_page_idx = idx - 1
            st.session_state.last_click = None
            st.rerun()
    with cs:
        sel_label = st.selectbox("", page_labels, index=idx,
                                 label_visibility="collapsed", key="psel")
        new_idx = page_labels.index(sel_label)
        if new_idx != idx:
            st.session_state.cur_page_idx = new_idx
            st.session_state.last_click = None
            st.rerun()
    with cn:
        if st.button("▶", use_container_width=True, key="next") and idx < len(page_labels)-1:
            st.session_state.cur_page_idx = idx + 1
            st.session_state.last_click = None
            st.rerun()

    page_num = pages_with_g[idx]
    base_img, sx, sy = render_base(st.session_state.pdf_bytes, page_num)
    overlay = draw_overlay(base_img, groups, selections, page_num, sx, sy)
    scale = DISP_W / overlay.width
    disp  = overlay.resize((DISP_W, int(overlay.height*scale)), Image.LANCZOS)

    coords = streamlit_image_coordinates(disp, key=f"img_p{page_num}")
    if coords and coords != st.session_state.last_click:
        st.session_state.last_click = coords
        fx, fy = coords["x"]/scale, coords["y"]/scale
        hit = group_at_click(fx, fy, groups, page_num, sx, sy)
        if hit is not None:
            gid, which = hit
            st.session_state.selections[gid] = None if selections.get(gid)==which else which
            st.session_state.output_bytes = None
            st.rerun()

    # Acciones rápidas
    st.markdown("<br>", unsafe_allow_html=True)
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("✅ Todos Sí",   use_container_width=True):
        for g in groups: st.session_state.selections[g["id"]] = "si"
        st.session_state.output_bytes = None; st.rerun()
    if b2.button("❌ Todos No",   use_container_width=True):
        for g in groups: st.session_state.selections[g["id"]] = "no"
        st.session_state.output_bytes = None; st.rerun()
    if b3.button("🔄 Invertir",   use_container_width=True):
        inv = {"si":"no","no":"si"}
        for g in groups:
            st.session_state.selections[g["id"]] = inv.get(selections.get(g["id"]))
        st.session_state.output_bytes = None; st.rerun()
    if b4.button("⬜ Limpiar",    use_container_width=True):
        st.session_state.selections = {}
        st.session_state.output_bytes = None; st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # ── PASO 3 ─────────────────────────────────────────────────────────────────
    st.markdown('<div class="card"><div class="card-title"><span class="icon">⬇️</span>Descarga el PDF marcado</div>', unsafe_allow_html=True)

    n_si  = sum(1 for v in st.session_state.selections.values() if v=="si")
    n_no  = sum(1 for v in st.session_state.selections.values() if v=="no")
    n_vac = len(groups) - n_si - n_no

    cols = st.columns(3)
    cols[0].markdown(f'<div class="badge-green">✓ Sí &nbsp;·&nbsp; {n_si}</div>', unsafe_allow_html=True)
    cols[1].markdown(f'<div class="badge-red">✗ No &nbsp;·&nbsp; {n_no}</div>',   unsafe_allow_html=True)
    cols[2].markdown(f'<div class="badge-amber">— Pendiente &nbsp;·&nbsp; {n_vac}</div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    if st.button("⚡  Generar PDF marcado", type="primary", use_container_width=True):
        with st.spinner("Generando PDF…"):
            st.session_state.output_bytes = generate_marked_pdf(
                st.session_state.pdf_bytes, groups, st.session_state.selections)
        st.rerun()

    if st.session_state.output_bytes:
        fname = (uploaded.name.replace(".pdf","_marcado.pdf")
                 if uploaded else "vencimientos_marcado.pdf")
        st.download_button(
            "⬇️  Descargar PDF marcado",
            data=st.session_state.output_bytes,
            file_name=fname, mime="application/pdf",
            use_container_width=True,
        )
        st.markdown('<div class="badge-green" style="margin-top:10px">✓ PDF listo para descargar</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)
