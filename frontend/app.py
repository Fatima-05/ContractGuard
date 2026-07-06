import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import streamlit as st
from datetime import datetime
from fpdf import FPDF

# Import backend classifier directly (no FastAPI needed)
from backend.agents.clause_extractor_agent import extract_clauses_from_file

st.set_page_config(
    page_title="ContractGuard",
    page_icon="",
    layout="wide",
)

# Keep hamburger menu visible so sidebar can be re-opened
st.markdown("""
<style>
  footer {visibility: hidden;}
  .stDeployButton {display:none;}
</style>
""", unsafe_allow_html=True)

# Session state
if "history" not in st.session_state:
    st.session_state.history = []
if "current_results" not in st.session_state:
    st.session_state.current_results = None
if "current_file" not in st.session_state:
    st.session_state.current_file = None

# ── Sidebar ──
with st.sidebar:
    st.markdown("## ContractGuard")
    st.caption("Offline-first. No data leaves your machine.")
    st.divider()

    st.markdown("### Analyze")
    uploaded_file = st.file_uploader(
        "Upload contract",
        type=["txt"],
        label_visibility="collapsed",
    )

    col1, col2 = st.columns([1, 1])
    with col1:
        analyze_btn = st.button(
            "Analyze", type="primary", use_container_width=True,
            disabled=uploaded_file is None,
        )
    with col2:
        clear_btn = st.button("Clear", use_container_width=True)

    if clear_btn:
        st.session_state.current_results = None
        st.session_state.current_file = None
        st.rerun()

    st.divider()

    if st.session_state.history:
        st.markdown("### History")
        for h in reversed(st.session_state.history[-10:]):
            name = h.get("name", "")
            total = h.get("total", 0)
            flagged = h.get("flagged", 0)
            dot_color = "#ff6b6b" if flagged > 0 else "#51cf66"
            st.markdown(
                f"<div style='font-size:0.85rem;padding:2px 0;'>"
                f"<span style='display:inline-block;width:8px;height:8px;"
                f"border-radius:50%;background:{dot_color};margin-right:4px;'></span>"
                f"{name[:24]} -- {flagged}/{total}</div>",
                unsafe_allow_html=True,
            )

    st.divider()
    st.caption("ContractGuard v1.0")


# ── PDF generator ──
def _find_unicode_font():
    for path in [
        "C:\\Windows\\Fonts\\arial.ttf",
        "C:\\Windows\\Fonts\\segoeui.ttf",
        "C:\\Windows\\Fonts\\calibri.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf",
    ]:
        if Path(path).exists():
            return path
    return None

_UNICODE_FONT = _find_unicode_font()

if not _UNICODE_FONT:
    try:
        import requests as req
        url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/master/ttf/DejaVuSans.ttf"
        r = req.get(url, timeout=15)
        if r.status_code == 200:
            cache = Path.home() / ".cache" / "contractguard"
            cache.mkdir(parents=True, exist_ok=True)
            font_path = cache / "DejaVuSans.ttf"
            font_path.write_bytes(r.content)
            _UNICODE_FONT = str(font_path)
    except Exception:
        pass

def _sanitize(text):
    if _UNICODE_FONT:
        return text
    return text.encode("ascii", errors="replace").decode("ascii")

def generate_pdf(file_name, clauses, total, flagged, safe, concerning, critical):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    font_name = "UniFont"
    if _UNICODE_FONT:
        pdf.add_font(font_name, "", _UNICODE_FONT)
    else:
        font_name = "Helvetica"
    pdf.add_page()

    def h(text, size=18, color=(200, 40, 40)):
        pdf.set_font(font_name, "", size)
        pdf.set_text_color(*color)
        pdf.cell(0, size + 4, _sanitize(text), new_x="LMARGIN", new_y="NEXT")

    def body(text, size=10, color=(60, 60, 60)):
        pdf.set_font(font_name, "", size)
        pdf.set_text_color(*color)
        pdf.multi_cell(0, size + 2, _sanitize(text), new_x="LMARGIN", new_y="NEXT")

    h("ContractGuard Analysis Report", 18, (200, 40, 40))
    pdf.ln(4)

    body(f"File: {file_name}")
    body(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}", color=(100, 100, 100))
    pdf.ln(6)

    h("Summary", 13, (40, 40, 40))

    body(f"Total Clauses: {total}")
    body(f"Safe: {safe}", color=(40, 180, 80))
    body(f"Concerning: {concerning}", color=(220, 180, 40))
    body(f"Critical: {critical}", color=(200, 40, 40))
    pdf.ln(6)

    h("Clause Analysis", 13, (40, 40, 40))
    pdf.ln(2)

    for clause in clauses:
        name = clause.get("name", "Clause")
        content = clause.get("content", "")
        harmful = clause.get("harmful", False)
        reasons = clause.get("reason", [])

        n_reasons = len(reasons)
        if n_reasons > 2:
            status_color = (200, 40, 40)
            status = "CRITICAL"
        elif n_reasons > 0:
            status_color = (220, 180, 40)
            status = "CONCERNING"
        else:
            status_color = (40, 180, 80)
            status = "SAFE"

        pdf.set_font(font_name, "", 10)
        pdf.set_text_color(*status_color)
        pdf.cell(0, 7, f"[{status}] {name}", new_x="LMARGIN", new_y="NEXT")

        pdf.set_text_color(80, 80, 80)
        display = content[:500] + "..." if len(content) > 500 else content
        body(display, 8, (80, 80, 80))

        if reasons:
            for r in reasons:
                body(f"- {r}", 8, (200, 80, 80))

        pdf.ln(4)

    pdf.set_font(font_name, "", 8)
    pdf.set_text_color(150, 150, 150)
    pdf.cell(0, 10, "Generated by ContractGuard v1.0", new_x="LMARGIN", new_y="NEXT", align="C")

    return bytes(pdf.output())


# ── Main area ──

# Title row
title_col1, title_col2 = st.columns([3, 1])
with title_col1:
    st.markdown("## Contract Analysis")
with title_col2:
    st.markdown(
        f"<div style='text-align:right;padding-top:8px;color:#888;font-size:0.9rem;'>"
        f"{datetime.now().strftime('%b %d, %Y')}</div>",
        unsafe_allow_html=True,
    )

# ── Analyze trigger ──
if analyze_btn and uploaded_file:
    with st.spinner("Analyzing contract..."):
        try:
            clauses = asyncio.run(extract_clauses_from_file(uploaded_file.getvalue()))
            st.session_state.current_results = clauses
            st.session_state.current_file = uploaded_file.name
            flagged = sum(1 for c in clauses if c.get("harmful"))
            st.session_state.history.append({
                "timestamp": datetime.now().isoformat(),
                "name": uploaded_file.name,
                "total": len(clauses),
                "flagged": flagged,
            })
        except Exception as e:
            st.error(f"Analysis failed: {e}")
    st.rerun()

# ── Display results ──
clauses = st.session_state.current_results
file_name = st.session_state.current_file

if clauses is not None:
    total = len(clauses)
    flagged = sum(1 for c in clauses if c.get("harmful"))
    safe = total - flagged
    pct = int(flagged / total * 100) if total else 0

    critical = sum(1 for c in clauses if len(c.get("reason", [])) > 2)
    concerning = flagged - critical

    # Summary dashboard
    st.markdown(f"**{file_name}**")
    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
    with c1:
        bar_color = "#ff6b6b" if pct > 50 else "#ffd43b" if pct > 0 else "#51cf66"
        st.markdown(
            f"<div style='background:#1a1a2e;border-radius:8px;padding:12px 16px;'>"
            f"<div style='display:flex;justify-content:space-between;font-size:0.85rem;color:#aaa;'>"
            f"<span>Risk score</span><span>{pct}% flagged</span></div>"
            f"<div style='background:#333;height:6px;border-radius:3px;margin-top:6px;'>"
            f"<div style='background:{bar_color};width:{pct}%;height:6px;border-radius:3px;'></div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )
    with c2:
        st.metric("Safe", safe, border=True)
    with c3:
        st.metric("Concerning", concerning, border=True)
    with c4:
        st.metric("Critical", critical, border=True)

    st.divider()

    # Clause cards (no emojis)
    for clause in clauses:
        name = clause.get("name", "Clause")
        content = clause.get("content", "")
        harmful = clause.get("harmful", False)
        reasons = clause.get("reason", [])

        if harmful:
            n_reasons = len(reasons)
            if n_reasons > 2:
                badge = "CRITICAL"
                border = "#ff6b6b"
                bg = "#2a1515"
                color = "#ff6b6b"
            else:
                badge = "CONCERNING"
                border = "#ffd43b"
                bg = "#2a2515"
                color = "#ffd43b"

            with st.container():
                st.markdown(
                    f"<div style='border:1px solid {border};border-radius:8px;padding:12px 16px;"
                    f"margin-bottom:12px;background:{bg};'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<strong>{name}</strong>"
                    f"<span style='font-size:0.85rem;color:{color};font-weight:600;'>{badge}</span>"
                    f"</div>"
                    f"<div style='margin-top:8px;color:#ddd;font-size:0.9rem;line-height:1.5;'>{content}</div>",
                    unsafe_allow_html=True,
                )
                if reasons:
                    for r in reasons:
                        st.markdown(
                            f"<div style='margin-top:4px;font-size:0.85rem;color:#ff8787;'>"
                            f"- {r}</div>",
                            unsafe_allow_html=True,
                        )
                st.markdown("</div>", unsafe_allow_html=True)

        else:
            with st.container():
                st.markdown(
                    f"<div style='border:1px solid #2d2d2d;border-radius:8px;padding:12px 16px;"
                    f"margin-bottom:12px;background:#0f0f0f;'>"
                    f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
                    f"<strong>{name}</strong>"
                    f"<span style='font-size:0.85rem;color:#51cf66;font-weight:600;'>SAFE</span>"
                    f"</div>"
                    f"<div style='margin-top:8px;color:#aaa;font-size:0.9rem;line-height:1.5;'>{content}</div>"
                    f"</div>",
                    unsafe_allow_html=True,
                )

    # PDF export
    st.divider()
    pdf_bytes = generate_pdf(
        file_name, clauses, total, flagged, safe, concerning, critical
    )
    st.download_button(
        "Download PDF Report",
        data=pdf_bytes,
        file_name=f"contractguard_{Path(file_name).stem}.pdf",
        mime="application/pdf",
    )

elif st.session_state.current_results is None:
    # Empty state -- fallback uploader also visible here when sidebar is collapsed
    st.markdown(
        "<div style='text-align:center;padding:60px 20px 20px;color:#555;'>"
        "<div style='font-size:1.2rem;margin-bottom:8px;'>Upload a contract to begin</div>"
        "<div style='font-size:0.9rem;margin-bottom:20px;'>Upload a .txt file</div>"
        "</div>",
        unsafe_allow_html=True,
    )
