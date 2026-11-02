"""Streamlit deployment wrapper; the bundled frontend stays unchanged."""
from pathlib import Path
from html.parser import HTMLParser
from urllib.parse import urlsplit

import streamlit as st
import streamlit.components.v1 as components

TITLE = "GlobalGuard - AI Driven Global Marketing Safety & Strategy Engine"
DIST = Path(__file__).resolve().parent / "dist" / "index.html"


class DependencyAudit(HTMLParser):
    """Reject unresolved runtime assets in a srcdoc iframe."""
    def __init__(self):
        super().__init__()
        self.local_assets = []
        self.external_assets = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        urls = []
        if tag in {"script", "img", "iframe", "source", "video", "audio"}:
            if attrs.get("src"):
                urls.append(attrs["src"])
        if tag == "link" and attrs.get("rel", "").lower() in {"stylesheet", "preload", "modulepreload"}:
            urls.append(attrs.get("href", ""))
        for url in urls:
            if url.startswith(("data:", "blob:", "#")):
                continue
            if urlsplit(url).scheme in {"https", "http"} or url.startswith("//"):
                self.external_assets.append(url)
            else:
                self.local_assets.append(url)


def load_frontend(path=DIST):
    html = path.read_text(encoding="utf-8")
    if "</html>" not in html.lower() or "landingPage" not in html or "dashboardShell" not in html:
        raise ValueError("dist/index.html 不包含完整版叙事首页与决策工作台。")
    audit = DependencyAudit()
    audit.feed(html)
    if audit.local_assets:
        raise ValueError("构建仍有相对路径资源：" + ", ".join(audit.local_assets))
    return html, audit.external_assets


def main():
    st.set_page_config(page_title=TITLE, page_icon="🛡️", layout="wide", initial_sidebar_state="collapsed")
    st.markdown("""
    <style>
    .stApp, [data-testid="stAppViewContainer"] {background:#0d131e;}
    [data-testid="stHeader"] {display:none;}
    [data-testid="stMainBlockContainer"], .block-container {
        padding:0!important; max-width:100%!important;
    }
    [data-testid="stMain"] {overflow:hidden;}
    iframe[title="st.iframe"] {
        display:block; width:100%!important; border:0;
        height:100vh!important; height:100dvh!important;
    }
    </style>
    """, unsafe_allow_html=True)
    try:
        html, external = load_frontend()
    except (OSError, ValueError) as exc:
        st.error(f"完整版前端加载失败：{exc}")
        st.code("cd globalguard-v4\nnpm ci\nnpm run build\nnpm test\nstreamlit run app.py")
        st.stop()
    if external:
        st.warning("前端包含外部运行资源，需联网访问：" + ", ".join(external))
    # srcdoc receives the entire bundle, not a URL relative to Streamlit.
    # CSS overrides this pixel fallback where Streamlit/browser support permits.
    components.html(html, height=900, scrolling=True)


if __name__ == "__main__":
    main()
