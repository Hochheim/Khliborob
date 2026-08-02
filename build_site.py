# =====================================================================
# 🌐 build_site.py — STATIC SITE GENERATOR
# Reads all JSON files from output_data\ and generates a complete
# static website in output_site\.
#
# HOW TO RUN:
#   python build_site.py
#
# After running, upload output_site\ to GitHub Pages or any
# static file host. Run Pagefind afterwards for full-text search:
#   pagefind --site output_site
# =====================================================================

import os
import json
import shutil
from pathlib import Path
from collections import defaultdict

PROJECT_FOLDER = os.environ.get("PROJECT_FOLDER", "C:\\Projekt")
DATA_DIR   = os.environ.get("DATA_DIR",   os.path.join(PROJECT_FOLDER, "output_data"))
SITE_DIR   = os.environ.get("SITE_DIR",   r"C:\Users\walte\OneDrive\Dokumente\GitHub\Khliborob")
OUTPUT_XML = os.environ.get("OUTPUT_XML", os.path.join(PROJECT_FOLDER, "output_xml"))
ASSETS_DIR = os.path.join(SITE_DIR, "assets")

SITE_TITLE = "Khliborob Digital Archive"
SITE_URL   = "https://yourusername.github.io/khliborob"  # Update before deploying

IPFS_GATEWAY = "https://gateway.pinata.cloud/ipfs"

# =====================================================================
# FLAGGED TOKEN HIGHLIGHTING
# =====================================================================
def _highlight_flagged(text, tokens):
    """Wrap unresolved flagged words in amber <mark> spans with tooltips."""
    import re, html
    if not text or not tokens:
        return html.escape(text) if text else ""
    result = html.escape(text)
    for tok in tokens:
        if tok.get("resolved"):
            continue
        word   = tok.get("original_word", "").strip()
        reason = html.escape(tok.get("reason_flagged", "uncertain OCR reading"))
        if not word:
            continue
        mark = (
            f'<mark class="flagged-token" '
            f'title="{reason}" '
            f'style="background:#fef3c7;color:#92400e;border-bottom:2px solid #f59e0b;'
            f'border-radius:2px;padding:0 2px;cursor:help;text-decoration:none">'
            f'{html.escape(word)}</mark>'
        )
        result = re.sub(
            r'(?<!\w)' + re.escape(html.escape(word)) + r'(?!\w)',
            mark, result, flags=re.IGNORECASE
        )
    return result


# =====================================================================
# TRANSLATIONS
# =====================================================================
STRINGS = {
    "uk": {
        "nav_browse":    "Переглянути",
        "nav_search":    "Пошук",
        "nav_gpu":       "Документи ГПУ",
        "nav_about":     "Про проєкт",
        "nav_maps":      "Мапи та графи",
        "nav_chat":      "Дослідницький агент",
        "hero_subtitle": "Цифровий архів газети Хлібороб / O Lavrador — "
                         "органу української діаспори у Бразилії (1924 — дотепер)",
        "search_placeholder": "Пошук по всіх сторінках — напр. Голодомор, Стамбул, 1932",
        "search_btn":    "Шукати",
        "gpu_banner":    "Архівне відкриття: розсекречені документи ГПУ СРСР "
                         "свідчать, що газета Хлібороб читалася радянськими "
                         "спецслужбами під час Голодомору (1932) і цитувалася "
                         "у зведеннях, складених для японської дипломатії.",
        "gpu_link":      "Переглянути документи",
        "browse_title":  "Переглянути випуски",
        "issues_label":  "випуски",
        "pages_label":   "сторінки",
        "gpu_doc_label": "Документ ГПУ",
        "transcript_uk": "Оригінальний текст (українська)",
        "transcript_pt": "Tradução (Português Brasileiro)",
        "transcript_en": "Переклад (англійська)",
        "locations":     "Місця",
        "persons":       "Особи",
        "blockchain":    "Блокчейн",
        "ipfs":          "IPFS",
        "stat_issues":   "оцифрованих випусків",
        "stat_pages":    "сторінок з можливістю пошуку",
        "stat_from":     "перший номер",
        "person_index_title": "Покажчик осіб",
        "location_index_title": "Покажчик місць",
        "filter_persons":     "Фільтр осіб…",
        "filter_locations":   "Фільтр місць…",
        "sort_alpha":         "А–Я",
        "sort_freq":          "Найчастіші",
        "footer_credit": "Зберігається SUBRAS (Sociedade Ucraniana do Brasil). "
                         "Цифровий архів створено в рамках дослідницького проєкту "
                         "Університету Мюнстера.",
    },
    "en": {
        "nav_browse":    "Browse",
        "nav_search":    "Search",
        "nav_gpu":       "GPU Documents",
        "nav_about":     "About",
        "nav_maps":      "Maps & Graphs",
        "nav_chat":      "Research Agent",
        "hero_subtitle": "Digital archive of Khliborob / O Lavrador — "
                         "the Ukrainian diaspora newspaper in Brazil (1924–present)",
        "search_placeholder": "Search all pages — e.g. Holodomor, Istanbul, 1932",
        "search_btn":    "Search",
        "gpu_banner":    "Historical discovery: declassified Soviet GPU documents "
                         "reveal that Khliborob was monitored by Soviet intelligence "
                         "during the Holodomor (1932) and cited in reports compiled "
                         "for Japanese diplomatic services.",
        "gpu_link":      "View documents",
        "browse_title":  "Browse issues",
        "issues_label":  "issues",
        "pages_label":   "pages",
        "gpu_doc_label": "GPU document",
        "transcript_uk": "Original text (Ukrainian)",
        "transcript_pt": "Translation (Brazilian Portuguese)",
        "transcript_en": "Translation (English)",
        "locations":     "Locations",
        "persons":       "Persons",
        "blockchain":    "Blockchain",
        "ipfs":          "IPFS",
        "stat_issues":   "digitized issues",
        "stat_pages":    "searchable pages",
        "stat_from":     "first issue",
        "person_index_title": "Person Index",
        "location_index_title": "Location Index",
        "filter_persons":     "Filter persons…",
        "filter_locations":   "Filter locations…",
        "sort_alpha":         "A–Z",
        "sort_freq":          "Most mentions",
        "footer_credit": "Preserved by SUBRAS (Sociedade Ucraniana do Brasil). "
                         "Digital archive created as part of a research project "
                         "at the University of Münster.",
    },
    "pt": {
        "nav_browse":    "Edições",
        "nav_search":    "Pesquisa",
        "nav_gpu":       "Documentos GPU",
        "nav_about":     "Sobre",
        "nav_maps":      "Mapas e Grafos",
        "nav_chat":      "Agente de Pesquisa",
        "hero_subtitle": "Arquivo digital do jornal Khliborob / O Lavrador — "
                         "órgão da diáspora ucraniana no Brasil (1924–presente)",
        "search_placeholder": "Pesquisar em todas as páginas — ex: Holodomor, Istambul, 1932",
        "search_btn":    "Pesquisar",
        "gpu_banner":    "Descoberta histórica: documentos desclassificados do "
                         "GPU soviético revelam que o Khliborob foi lido por "
                         "serviços de inteligência durante o Holodomor (1932) "
                         "e citado em relatórios preparados para a diplomacia japonesa.",
        "gpu_link":      "Ver documentos",
        "browse_title":  "Navegar por edições",
        "issues_label":  "edições",
        "pages_label":   "páginas",
        "gpu_doc_label": "Documento GPU",
        "transcript_uk": "Texto original (ucraniano)",
        "transcript_pt": "Tradução (Português Brasileiro)",
        "transcript_en": "Tradução (inglês)",
        "locations":     "Locais",
        "persons":       "Pessoas",
        "blockchain":    "Blockchain",
        "ipfs":          "IPFS",
        "stat_issues":   "edições digitalizadas",
        "stat_pages":    "páginas pesquisáveis",
        "stat_from":     "primeiro número",
        "person_index_title": "Índice de Pessoas",
        "location_index_title": "Índice de Lugares",
        "filter_persons":     "Filtrar pessoas…",
        "filter_locations":   "Filtrar locais…",
        "sort_alpha":         "A–Z",
        "sort_freq":          "Mais citados",
        "footer_credit": "Preservado pela SUBRAS (Sociedade Ucraniana do Brasil). "
                         "Arquivo digital criado no âmbito de um projeto de pesquisa "
                         "da Universidade de Münster.",
    }
}

# =====================================================================
# SHARED CSS + JS ASSETS
# =====================================================================
MAIN_CSS = """
:root {
  --blue:    #1a4a8a;
  --yellow:  #FFD500;
  --blue-lt: #e8f0fb;
  --gpu-bg:  #fff8e6;
  --gpu-bd:  #c8a800;
  --gpu-tx:  #7a5c00;
  --text:    #1a1a1a;
  --muted:   #666;
  --border:  #ddd;
  --bg:      #f8f8f6;
  --card-bg: #fff;
  --radius:  8px;
  --nav-h:   52px;
}
@media (prefers-color-scheme: dark) {
  :root {
    --text:    #eee;
    --muted:   #aaa;
    --border:  #333;
    --bg:      #111;
    --card-bg: #1c1c1c;
    --blue-lt: #0d2545;
    --gpu-bg:  #2a2000;
    --gpu-bd:  #9a7a00;
    --gpu-tx:  #e8c840;
  }
}
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;
     background:var(--bg);color:var(--text);font-size:15px;line-height:1.6}
a{color:var(--blue);text-decoration:none}
a:hover{text-decoration:underline}

/* NAV */
nav{position:sticky;top:0;z-index:100;background:var(--blue);height:var(--nav-h);
    display:flex;align-items:center;justify-content:space-between;padding:0 1.5rem}
.nav-brand{display:flex;align-items:center;gap:.6rem}
.flag{width:24px;height:16px;display:flex;flex-direction:column;
      border-radius:2px;overflow:hidden;flex-shrink:0}
.flag-top{background:#005BBB;flex:1}
.flag-bot{background:#FFD500;flex:1}
.nav-title{font-size:14px;font-weight:500;color:#fff}
.nav-links{display:flex;gap:1.2rem;align-items:center}
.nav-links a{font-size:13px;color:rgba(255,255,255,.85)}
.lang-switcher{display:flex;gap:.3rem;margin-left:.8rem;
               border-left:1px solid rgba(255,255,255,.3);padding-left:.8rem}
.lang-btn{font-size:11px;padding:3px 7px;border-radius:3px;cursor:pointer;
          border:1px solid rgba(255,255,255,.4);color:rgba(255,255,255,.8);
          background:transparent}
.lang-btn.active{background:#FFD500;color:#1a1a1a;border-color:#FFD500;font-weight:500}

/* GPU BANNER */
.gpu-banner{background:var(--gpu-bg);border-bottom:2px solid var(--gpu-bd);
            padding:.75rem 1.5rem;font-size:13px;color:var(--gpu-tx);
            display:flex;align-items:center;gap:.75rem;flex-wrap:wrap}
.gpu-banner strong{font-weight:500}
.gpu-banner a{color:var(--blue);font-weight:500}
.gpu-icon{font-size:18px;flex-shrink:0}

/* HERO */
.hero{background:var(--blue);color:#fff;padding:2.5rem 1.5rem}
.hero h1{font-size:26px;font-weight:500;margin-bottom:.4rem}
.hero p{font-size:14px;opacity:.85;max-width:520px;margin-bottom:1.2rem;line-height:1.6}
.search-box{display:flex;gap:.5rem;max-width:560px}
.search-box input{flex:1;font-size:14px;padding:.55rem .9rem;
                  border:none;border-radius:var(--radius);
                  background:rgba(255,255,255,.95);color:#222}
.search-box input:focus{outline:2px solid var(--yellow);outline-offset:1px}
.search-box button{font-size:13px;padding:.55rem 1.1rem;border:none;
                   border-radius:var(--radius);background:var(--yellow);
                   color:#1a1a1a;font-weight:500;cursor:pointer}
.search-box button:hover{background:#e8c800}

/* STATS */
.stats{display:grid;grid-template-columns:repeat(3,1fr);
       border-bottom:1px solid var(--border)}
.stat{padding:1rem 1.5rem;text-align:center;border-right:1px solid var(--border)}
.stat:last-child{border-right:none}
.stat-num{font-size:22px;font-weight:500;color:var(--blue)}
.stat-lbl{font-size:12px;color:var(--muted);margin-top:.1rem}

/* BROWSE */
.browse-layout{display:grid;grid-template-columns:200px 1fr;gap:0;
               min-height:calc(100vh - var(--nav-h) - 200px)}
.sidebar{border-right:1px solid var(--border);padding:1.2rem;
         background:var(--card-bg)}
.sidebar h3{font-size:11px;font-weight:500;color:var(--muted);
            text-transform:uppercase;letter-spacing:.06em;margin-bottom:.7rem}
.decade-group{margin-bottom:.6rem}
.decade-toggle{display:flex;align-items:center;justify-content:space-between;
               font-size:12px;font-weight:500;color:var(--text);cursor:pointer;
               padding:.3rem .4rem;border-radius:4px;user-select:none;
               background:var(--blue-lt)}
.decade-toggle:hover{background:var(--blue);color:#fff}
.decade-toggle .arrow{font-size:10px;transition:transform .2s}
.decade-toggle.collapsed .arrow{transform:rotate(-90deg)}
.decade-years{overflow:hidden;transition:max-height .2s ease}
.year-link{display:block;font-size:13px;color:var(--text);
           padding:.15rem .6rem;border-radius:4px;text-decoration:none}
.year-link:hover{background:var(--blue-lt);color:var(--blue)}
.year-link.active{background:var(--blue);color:#fff;font-weight:500}
.year-link.has-gpu::after{content:" ●";color:var(--gpu-bd);font-size:9px}

.main-content{padding:1.5rem}
.main-content h2{font-size:18px;font-weight:500;margin-bottom:1rem}
.issue-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(160px,1fr));gap:.8rem}
.issue-card{background:var(--card-bg);border:1px solid var(--border);
            border-radius:var(--radius);padding:.75rem;cursor:pointer;
            text-decoration:none;display:block;transition:border-color .15s}
.issue-card:hover{border-color:var(--blue)}
.issue-card.gpu-linked{border-color:var(--gpu-bd)}
.issue-date{font-size:11px;color:var(--muted)}
.issue-num{font-size:14px;font-weight:500;color:var(--text);margin:.2rem 0}
.issue-meta{font-size:11px;color:var(--muted)}
.gpu-tag{display:inline-block;font-size:10px;padding:1px 5px;border-radius:3px;
         background:var(--gpu-bg);color:var(--gpu-tx);margin-top:.3rem;
         border:1px solid var(--gpu-bd)}

/* ISSUE PAGE */
.issue-layout{max-width:960px;margin:0 auto;padding:1.5rem}
.issue-header{margin-bottom:1.2rem;padding-bottom:1rem;
              border-bottom:1px solid var(--border)}
.issue-header h1{font-size:22px;font-weight:500;margin-bottom:.2rem}
.issue-header p{font-size:13px;color:var(--muted)}
.gpu-connection{background:var(--gpu-bg);border:.5px solid var(--gpu-bd);
                border-left:4px solid var(--gpu-bd);border-radius:0 var(--radius) var(--radius) 0;
                padding:.8rem 1rem;margin-bottom:1.2rem}
.gpu-connection h3{font-size:13px;font-weight:500;color:var(--gpu-tx);margin-bottom:.3rem}
.gpu-connection p{font-size:12px;color:var(--gpu-tx);line-height:1.5}
.gpu-connection .gpu-meta{font-size:11px;color:var(--muted);margin-top:.4rem}

.content-grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:1.2rem;margin-bottom:1.2rem}
.content-panel{background:var(--card-bg);border:1px solid var(--border);
               border-radius:var(--radius);padding:1rem}
.content-panel h3{font-size:12px;font-weight:500;color:var(--muted);
                  text-transform:uppercase;letter-spacing:.05em;margin-bottom:.7rem}
.transcript{font-size:13px;line-height:1.7;max-height:320px;overflow-y:auto;
            white-space:pre-wrap;word-break:break-word}
.map-frame{width:100%;height:420px;border:none;border-radius:var(--radius)}
.graph-frame{width:100%;height:320px;border:none;border-radius:var(--radius)}
.meta-table{width:100%;font-size:12px;border-collapse:collapse}
.meta-table td{padding:.3rem .4rem;border-bottom:1px solid var(--border);
               vertical-align:top}
.meta-table td:first-child{color:var(--muted);width:120px;font-weight:500}
.meta-table td a{word-break:break-all;font-size:11px}
.entity-list{display:flex;flex-wrap:wrap;gap:.3rem}
.entity-tag{font-size:11px;padding:2px 7px;border-radius:3px;
            background:var(--blue-lt);color:var(--blue)}

/* GPU DOCS PAGE */
.gpu-page{max-width:800px;margin:0 auto;padding:1.5rem}
.gpu-doc-card{background:var(--card-bg);border:1px solid var(--border);
              border-radius:var(--radius);padding:1.2rem;margin-bottom:1rem}
.gpu-doc-card h2{font-size:16px;font-weight:500;margin-bottom:.4rem}
.gpu-doc-card .arch-ref{font-size:12px;color:var(--muted);margin-bottom:.7rem;
                        font-family:monospace}
.gpu-doc-card p{font-size:13px;line-height:1.6;margin-bottom:.5rem}
.issue-links{display:flex;gap:.4rem;flex-wrap:wrap}
.issue-link{font-size:11px;padding:2px 7px;border-radius:3px;
            background:var(--blue-lt);color:var(--blue);text-decoration:none}

/* FOOTER */
footer{border-top:1px solid var(--border);padding:1.2rem 1.5rem;
       font-size:12px;color:var(--muted);text-align:center;margin-top:2rem}

/* SEARCH RESULTS */
#search-results{padding:1.5rem;max-width:800px;margin:0 auto}
.result-card{background:var(--card-bg);border:1px solid var(--border);
             border-radius:var(--radius);padding:.8rem 1rem;margin-bottom:.6rem}
.result-date{font-size:11px;color:var(--muted)}
.result-title{font-size:14px;font-weight:500;margin:.2rem 0}
.result-snippet{font-size:12px;color:var(--muted);line-height:1.5}
mark{background:var(--yellow);color:#1a1a1a;border-radius:2px;padding:0 2px}

@media(max-width:640px){
  .browse-layout{grid-template-columns:1fr}
  .sidebar{border-right:none;border-bottom:1px solid var(--border)}
  .content-grid{grid-template-columns:1fr}
  .content-grid .content-panel:not(:first-child){margin-top:.8rem}
  .stats{grid-template-columns:1fr}
  .stat{border-right:none;border-bottom:1px solid var(--border)}
}
"""

LANG_JS = """
function toggleIpfs(id){
  var e=document.getElementById(id);
  if(e) e.style.display=e.style.display==='none'?'block':'none';
}
const STRINGS = """ + json.dumps(STRINGS, ensure_ascii=False) + """;
let currentLang = localStorage.getItem('lang') || 'en';

function toggleIpfs(id){
  var e=document.getElementById(id);
  if(e) e.style.display=e.style.display==='none'?'block':'none';
}

function toggleBibtex(id) {
  var popup = document.getElementById('bibtex-popup-' + id);
  if (popup) popup.style.display = popup.style.display === 'none' ? 'block' : 'none';
}

function toggleChicago(id) {
  var popup = document.getElementById('chicago-popup-' + id);
  if (popup) popup.style.display = popup.style.display === 'none' ? 'block' : 'none';
}

function applyLang(lang) {
  currentLang = lang;
  localStorage.setItem('lang', lang);
  // Translate data-i18n elements
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.dataset.i18n;
    if (STRINGS[lang] && STRINGS[lang][key]) {
      if (el.tagName === 'INPUT') el.placeholder = STRINGS[lang][key];
      else el.textContent = STRINGS[lang][key];
    }
  });
  // Update active button
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.lang === lang);
  });
  // Show/hide data-lang-* elements
  ['en','uk','pt'].forEach(l => {
    document.querySelectorAll('[data-lang-' + l + ']').forEach(el => {
      el.style.display = (l === lang) ? '' : 'none';
    });
  });
}

document.addEventListener('DOMContentLoaded', () => {
  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.addEventListener('click', () => applyLang(btn.dataset.lang));
  });
  applyLang(currentLang);
});
"""


# =====================================================================
# HTML HELPERS
# =====================================================================
def nav_html(active_page="", base=""):
    return f"""
<nav>
  <div class="nav-brand">
    <a href="{base}index.html" style="display:flex;align-items:center;gap:.6rem;text-decoration:none">
      <div class="flag"><div class="flag-top"></div><div class="flag-bot"></div></div>
      <span class="nav-title">{SITE_TITLE}</span>
    </a>
  </div>
  <div class="nav-links">
    <a href="{base}browse/" data-i18n="nav_browse">Browse</a>
    <a href="{base}search/" data-i18n="nav_search">Search</a>
    <a href="{base}gpu-documents/" data-i18n="nav_gpu">GPU Documents</a>
    <a href="{base}aggregated/" data-i18n="nav_maps">Maps &amp; Graphs</a>
    <a href="{base}chat/" data-i18n="nav_chat">Research Agent</a>
    <a href="{base}about/" data-i18n="nav_about">About</a>
    <a href="{base}persons/">Persons</a>
    <a href="{base}locations/">Locations</a>
    <div class="lang-switcher">
      <button class="lang-btn" data-lang="uk">УКР</button>
      <button class="lang-btn active" data-lang="en">ENG</button>
      <button class="lang-btn" data-lang="pt">PT-BR</button>
    </div>
  </div>
</nav>"""


def gpu_banner_html(base=""):
    return f"""
<div class="gpu-banner" id="gpu-banner" style="display:flex;align-items:center;justify-content:space-between;gap:.5rem;padding:.4rem 1.5rem;font-size:12px">
  <span style="display:flex;align-items:center;gap:.5rem;color:var(--gpu-tx)">
    <span style="font-size:13px">🔍</span>
    <span data-i18n="gpu_banner" style="opacity:.85">Historical discovery: declassified Soviet GPU documents reveal that Khliborob was monitored by Soviet intelligence during the Holodomor (1932) and cited in reports compiled for Japanese diplomatic services.</span>
    &nbsp;<a href="{base}gpu-documents/" data-i18n="gpu_link" style="font-size:12px;white-space:nowrap">View documents</a>
  </span>
  <button onclick="closeBanner()" aria-label="Close"
    style="flex-shrink:0;background:none;border:none;cursor:pointer;font-size:14px;
           color:var(--gpu-tx);opacity:.5;padding:0 .2rem;line-height:1">✕</button>
</div>
<script>
function closeBanner(){{
  const b=document.getElementById("gpu-banner");
  if(b){{b.style.display="none";sessionStorage.setItem("gpuBannerClosed","1");}}
}}
(function(){{
  if(sessionStorage.getItem("gpuBannerClosed")==="1"){{
    document.addEventListener("DOMContentLoaded",function(){{
      const b=document.getElementById("gpu-banner");
      if(b)b.style.display="none";
    }});
  }}
}})();
</script>"""


def page_shell(title, content, extra_head="", depth=1, show_gpu_banner=False):
    base = "../" * depth
    banner = gpu_banner_html(base=base) if show_gpu_banner else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title} — {SITE_TITLE}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="{base}assets/main.css">
{extra_head}
</head>
<body>
{nav_html(base=base)}
{banner}
{content}
<footer>
  <span data-i18n="footer_credit">Preserved by SUBRAS (Sociedade Ucraniana do Brasil). Digital archive created as part of a research project at the University of Münster.</span>
</footer>
<script src="{base}assets/lang.js"></script>
</body>
</html>"""


# =====================================================================
# LOAD ALL ISSUE DATA
# =====================================================================
def load_all_issues():
    issues = []
    if not os.path.exists(DATA_DIR):
        print(f"⚠️  Data directory not found: {DATA_DIR}")
        return issues
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.endswith(".json"):
            with open(os.path.join(DATA_DIR, fname), encoding="utf-8") as f:
                try:
                    issues.append(json.load(f))
                except json.JSONDecodeError as e:
                    print(f"⚠️  Could not parse {fname}: {e}")
    return issues


# =====================================================================
# PAGE GENERATORS
# =====================================================================
def build_homepage(issues, total_pages):
    _depth = 0
    years = sorted(set(i["year"] for i in issues if i.get("year") != "unknown"))
    first_year = years[0] if years else "1924"

    # Featured issue — earliest issue with content
    sorted_issues = sorted([i for i in issues if i.get('pages')],
                           key=lambda x: x.get('date',''), reverse=False)
    featured = sorted_issues[0] if sorted_issues else None
    featured_html = ''
    if featured:
        abstract = featured.get('translations', {}).get('abstract_en', '')[:300]
        persons = featured.get('entities', {}).get('persons', [])
        person_names = ', '.join(
            (p.get('name_en') or p.get('name_uk','')) if isinstance(p, dict) else str(p)
            for p in persons[:5]
        )
        locs = featured.get('entities', {}).get('locations', [])
        loc_names = ', '.join(l.get('name_en','') for l in locs[:5] if l.get('name_en'))
        gpu_badge = ''
        if featured.get('gpu_connections'):
            gpu_badge = '<span style="background:var(--gpu-bg);color:var(--gpu-tx);border:1px solid var(--gpu-bd);border-radius:4px;padding:2px 8px;font-size:11px;margin-left:.5rem">GPU document</span>'
        featured_html = f"""
<div style='background:var(--card-bg);border:2px solid var(--blue);border-radius:var(--radius);padding:1.5rem;margin:1.5rem 0'>
  <div style='font-size:11px;color:var(--blue);text-transform:uppercase;letter-spacing:.08em;font-weight:500;margin-bottom:.4rem'>Featured issue</div>
  <h2 style='font-size:18px;font-weight:500;margin-bottom:.4rem'>
    <a href='issues/{featured['issue_id']}/' style='color:var(--text);text-decoration:none'>
      {featured.get('newspaper_name_uk','Хлібороб')} — {featured.get('date','')} (No. {featured.get('issue_number','')})
    </a>{gpu_badge}
  </h2>
  <p style='font-size:13px;line-height:1.6;margin-bottom:.8rem;color:var(--text)'>{abstract}...</p>
  <div style='display:flex;gap:1.5rem;font-size:12px;color:var(--muted);flex-wrap:wrap;margin-bottom:.8rem'>
    {'<span>👤 ' + person_names + '</span>' if person_names else ''}
    {'<span>📍 ' + loc_names + '</span>' if loc_names else ''}
    <span>📄 {len(featured.get('pages',[]))} pages</span>
  </div>
  <a href='issues/{featured['issue_id']}/' style='font-size:13px;color:#1a4a8a;font-weight:500'>Read this issue →</a>
</div>"""

    # Recent GPU-linked issues for featured section
    gpu_issues = [i for i in issues if i.get("gpu_connections")][:4]
    gpu_cards = ""
    for iss in gpu_issues:
        abstract_short = iss.get("translations",{}).get("abstract_en","")[:120]
        scan_cid_preview = iss.get("pages",[{}])[0].get("cids",{}).get("scan","") if iss.get("pages") else ""
        _img_style = "width:100%;height:120px;object-fit:cover;border-radius:var(--radius) var(--radius) 0 0;display:block"
        img_html = (
            f'<img src="{IPFS_GATEWAY}/{scan_cid_preview}" style="{_img_style}" alt="Newspaper scan" loading="lazy">'
            if scan_cid_preview and not scan_cid_preview.startswith("bafybeisimulated") else ""
        )
        gpu_cards += f"""
<a class="issue-card gpu-linked" href="issues/{iss['issue_id']}/" style="display:block;overflow:hidden;text-decoration:none">
  {img_html}
  <div style="padding:.7rem">
    <div class="gpu-tag" data-i18n="gpu_doc_label">GPU document</div>
    <div class="issue-num" style="margin:.3rem 0">No. {iss.get('issue_number','')} · {iss.get('date','')}</div>
    <div style="font-size:11px;color:var(--muted);line-height:1.4">{abstract_short}{"…" if abstract_short else ""}</div>
  </div>
</a>"""

    content = f"""
{featured_html}
<div class="hero">
  <h1>Хлібороб · O Lavrador</h1>
  <p data-i18n="hero_subtitle">Digital archive of Khliborob / O Lavrador — the Ukrainian diaspora newspaper in Brazil (1924–present)</p>
  <div class="search-box">
    <input type="search" data-i18n="search_placeholder" placeholder="Search all pages — e.g. Holodomor, Istanbul, 1932" id="q" />
    <button onclick="doSearch()" data-i18n="search_btn">Search</button>
  </div>
</div>

<div class="stats">
  <div class="stat">
    <div class="stat-num">{len(issues)}</div>
    <div class="stat-lbl" data-i18n="stat_issues">digitized issues</div>
  </div>
  <div class="stat">
    <div class="stat-num">{total_pages:,}</div>
    <div class="stat-lbl" data-i18n="stat_pages">searchable pages</div>
  </div>
  <div class="stat">
    <div class="stat-num">{first_year}</div>
    <div class="stat-lbl" data-i18n="stat_from">first issue</div>
  </div>
</div>

<div style="padding:1.5rem">
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:1.2rem;margin-bottom:1.2rem">

    <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);overflow:hidden;
         transition:box-shadow .15s;cursor:pointer" onclick="location.href='browse/'"
         onmouseover="this.style.boxShadow='0 4px 12px rgba(26,74,138,.15)'"
         onmouseout="this.style.boxShadow='none'">
      {'<img src="' + IPFS_GATEWAY + '/' + (sorted_issues[0].get("pages",[{}])[0].get("cids",{}).get("scan","") if sorted_issues else "") + '" style="width:100%;height:140px;object-fit:cover;object-position:top;display:block" alt="Newspaper scan">' if sorted_issues and sorted_issues[0].get("pages",[{}])[0].get("cids",{}).get("scan","") and not sorted_issues[0].get("pages",[{}])[0].get("cids",{}).get("scan","").startswith("bafybeisimulated") else '<div style="background:var(--blue-lt);height:140px;display:flex;align-items:center;justify-content:center;font-size:48px">📰</div>'}
      <div style="padding:1rem">
        <h3 style="font-size:15px;font-weight:500;margin-bottom:.3rem">Browse the Archive</h3>
        <p style="font-size:12px;color:var(--muted);margin-bottom:.8rem;line-height:1.5">
          {len(issues)} digitized issues from {first_year} to present.
          Navigate by year and decade.
        </p>
        <span style="display:inline-flex;align-items:center;gap:.4rem;
          background:#1a4a8a;color:#fff;padding:.5rem 1rem;border-radius:var(--radius);
          font-size:13px;font-weight:500">
          📂 Browse all issues →
        </span>
      </div>
    </div>

    <div style="background:var(--gpu-bg);border:1px solid var(--gpu-bd);border-radius:var(--radius);overflow:hidden;
         transition:box-shadow .15s;cursor:pointer" onclick="location.href='gpu-documents/'" 
         onmouseover="this.style.boxShadow='0 4px 12px rgba(200,168,0,.2)'" 
         onmouseout="this.style.boxShadow='none'">
      <div style="background:linear-gradient(135deg,#1a4a8a,#c8a800);height:140px;
           display:flex;align-items:center;justify-content:center;font-size:48px">🔍</div>
      <div style="padding:1rem">
        <h3 style="font-size:15px;font-weight:500;margin-bottom:.3rem;color:var(--gpu-tx)">GPU Documents</h3>
        <p style="font-size:12px;color:var(--gpu-tx);margin-bottom:.8rem;line-height:1.5;opacity:.8">
          Declassified Soviet intelligence files linking Khliborob to the Holodomor period.
        </p>
        <span style="display:inline-flex;align-items:center;gap:.4rem;
          background:var(--gpu-bd);color:#fff;padding:.5rem 1rem;border-radius:var(--radius);
          font-size:13px;font-weight:500">
          🔍 View documents →
        </span>
      </div>
    </div>

<script>
function doSearch() {{
  const q = document.getElementById('q').value.trim();
  if (q) window.location.href = '/search/?q=' + encodeURIComponent(q);
}}
document.getElementById('q').addEventListener('keydown', e => {{
  if (e.key === 'Enter') doSearch();
}});
</script>"""
    return page_shell("Home", content, depth=0, show_gpu_banner=True)


def build_browse_page(issues):
    by_year = defaultdict(list)
    for iss in issues:
        by_year[iss.get("year", "unknown")].append(iss)

    gpu_years = set(
        iss["year"] for iss in issues
        if iss.get("gpu_connections") and iss.get("year")
    )

    decades = defaultdict(list)
    for year in sorted(by_year.keys()):
        if year == "unknown":
            continue
        decade = str(int(year) // 10 * 10) + "s"
        decades[decade].append(year)

    sidebar = '<div class="sidebar"><h3 data-i18n="nav_browse">Browse</h3>'
    for decade, years in sorted(decades.items()):
        sidebar += f'<div class="decade-group"><div class="decade-label">{decade}</div>'
        for year in years:
            gpu_class = " has-gpu" if year in gpu_years else ""
            sidebar += (f'<a class="year-link{gpu_class}" '
                        f'href="{year}/">{year}</a>')
        sidebar += '</div>'
    sidebar += '<div style="margin-top:1.2rem;padding-top:.8rem;border-top:1px solid var(--border)">'
    sidebar += '<a href="../" style="font-size:12px;color:var(--muted)">← Back to archive</a>'
    sidebar += '</div>'
    sidebar += '</div>'

    # Show most recent year by default
    recent_year = max((y for y in by_year if y != "unknown"), default="")
    issue_cards = _issue_cards_html(by_year.get(recent_year, []), base="../")

    main = f"""
<div class="main-content">
  <h2 data-i18n="browse_title">{recent_year} — {len(by_year.get(recent_year, []))} issues</h2>
  <div class="issue-grid">{issue_cards}</div>
</div>"""

    content = f'<div class="browse-layout">{sidebar}{main}</div>'
    return page_shell("Browse", content, depth=1)


def build_year_page(year, issues, all_issues=None):
    issue_cards = _issue_cards_html(issues, base="../../")
    sidebar = _sidebar_html(all_issues or issues, active_year=year)
    main = f"""
<div class="main-content">
  <h2>{year} — {len(issues)} issues</h2>
  <div class="issue-grid">{issue_cards}</div>
</div>"""
    content = f'<div class="browse-layout">{sidebar}{main}</div>'
    return page_shell(year, content, depth=2)


def _sidebar_html(all_issues, active_year=""):
    by_year = defaultdict(list)
    for iss in all_issues:
        by_year[iss.get("year", "unknown")].append(iss)
    gpu_years = set(
        iss["year"] for iss in all_issues
        if iss.get("gpu_connections") and iss.get("year")
    )
    decades = defaultdict(list)
    for year in sorted(by_year.keys()):
        if year == "unknown":
            continue
        decade = str(int(year) // 10 * 10) + "s"
        decades[decade].append(year)

    html = '<div class="sidebar"><h3 data-i18n="nav_browse">Browse</h3>'
    for decade, years in sorted(decades.items()):
        html += f'<div class="decade-group">'
        # Decade label links to first year in that decade
        html += (f'<a class="decade-label" href="../{years[0]}/" '
                 f'style="font-size:11px;font-weight:600;color:var(--muted);'
                 f'margin:.4rem 0 .2rem .4rem;display:block;text-decoration:none;'
                 f'cursor:pointer">{decade}</a>')
        for year in years:
            gpu_class = " has-gpu" if year in gpu_years else ""
            active_class = " active" if year == active_year else ""
            html += (f'<a class="year-link{gpu_class}{active_class}" '
                     f'href="../{year}/">{year}</a>')
        html += '</div>'
    html += '<div style="margin-top:1rem;padding-top:.8rem;border-top:1px solid var(--border)">'
    html += '<a href="../../" style="font-size:12px;color:var(--muted)">← Back to archive</a>'
    html += '</div>'
    html += '</div>'
    return html


def _issue_cards_html(issues, base="../"):
    html = ""
    for iss in sorted(issues, key=lambda x: x.get("date", "")):
        gpu = " gpu-linked" if iss.get("gpu_connections") else ""
        gpu_tag = ('<div class="gpu-tag" data-i18n="gpu_doc_label">GPU document</div>'
                   if iss.get("gpu_connections") else "")
        page_count = sum(len(i.get("pages", [])) for i in [iss])
        loc_count = len(iss.get("entities", {}).get("locations", []))
        # Scan thumbnail from first page IPFS CID
        scan_cid = iss.get("pages", [{}])[0].get("cids", {}).get("scan", "") if iss.get("pages") else ""
        has_real_cid = scan_cid and not scan_cid.startswith("bafybeisimulated")
        thumb_html = (
            f'<img src="{IPFS_GATEWAY}/{scan_cid}" '            f'style="width:100%;height:110px;object-fit:cover;display:block;'            f'border-radius:var(--radius) var(--radius) 0 0" '            f'alt="Scan preview" loading="lazy">'            if has_real_cid else
            '<div style="width:100%;height:110px;background:var(--blue-lt);'            'display:flex;align-items:center;justify-content:center;'            'border-radius:var(--radius) var(--radius) 0 0;'            'font-size:28px">📰</div>'
        )
        html += f"""
<a class="issue-card{gpu}" href="{base}issues/{iss['issue_id']}/" style="display:block;overflow:hidden;padding:0;text-decoration:none">
  {thumb_html}
  <div style="padding:.65rem">
    <div class="issue-date">{iss.get('date','')}</div>
    <div class="issue-num">No. {iss.get('issue_number','')}</div>
    <div class="issue-meta">{page_count} pages · {loc_count} locations</div>
    {gpu_tag}
  </div>
</a>"""
    return html


def build_issue_page(iss, all_issues):
    gpu_blocks = ""
    for gpu in iss.get("gpu_connections", []):
        gpu_blocks += f"""
<div class="gpu-connection">
  <h3>🔍 GPU Document Connection</h3>
  <p>{gpu.get('description_en','')}</p>
  <div class="gpu-meta">
    Archive reference: <code>{gpu.get('archive_ref','')}</code> &nbsp;·&nbsp;
    {gpu.get('date','')} &nbsp;·&nbsp;
    {gpu.get('sender','')} → {gpu.get('recipient','')}
  </div>
</div>"""

    # Transcripts from all pages — with flagged token highlighting on the Ukrainian original
    def _page_label(p):
        return f"[Page {p.get('page_number','')}]"

    transcript_uk_parts = []
    for p in iss.get("pages", []):
        raw = p.get("transcript_uk", "")
        tokens = p.get("low_confidence_tokens", [])
        highlighted = _highlight_flagged(raw, tokens)
        transcript_uk_parts.append(f"<strong>{_page_label(p)}</strong><br>{highlighted}")
    transcript_uk = "<br><br>".join(transcript_uk_parts)

    transcript_en = "<br><br>".join(
        f"<strong>{_page_label(p)}</strong><br>{p.get('transcript_en','')}"
        for p in iss.get("pages", [])
    )
    transcript_pt = "<br><br>".join(
        f"<strong>{_page_label(p)}</strong><br>{p.get('transcript_pt','')}"
        for p in iss.get("pages", [])
        if p.get('transcript_pt')
    )

    # Map iframe — use IPFS if real CID, else local XAMPP fallback
    issue_id  = iss.get("issue_id", "")
    map_cid   = iss.get("cids", {}).get("map", "")
    graph_cid = iss.get("cids", {}).get("graph", "")

    # Detect sandbox fake CIDs (start with "bafybeisimulated")
    def real_cid(cid):
        return cid and not cid.startswith("bafybeisimulated")

    import shutil as _shutil
    _OUTPUT_XML = OUTPUT_XML  # module-level, env-var driven
    maps_dir   = os.path.join(SITE_DIR, "maps")
    graphs_dir = os.path.join(SITE_DIR, "graphs")
    os.makedirs(maps_dir, exist_ok=True)
    os.makedirs(graphs_dir, exist_ok=True)

    # Find local map/graph files for first page of this issue
    first_page_id = iss.get("pages", [{}])[0].get("page_id", "") if iss.get("pages") else ""
    local_map   = os.path.join(_OUTPUT_XML, f"{first_page_id}_map.html")
    local_graph = os.path.join(_OUTPUT_XML, f"{first_page_id}_graph.html")

    if real_cid(map_cid):
        map_html = (f'<iframe class="map-frame" src="{IPFS_GATEWAY}/{map_cid}" '
                    f'title="Location map"></iframe>')
    elif os.path.exists(local_map):
        _shutil.copy2(local_map, os.path.join(maps_dir, f"{first_page_id}_map.html"))
        map_html = (f'<iframe class="map-frame" '
                    f'src="../../maps/{first_page_id}_map.html" '
                    f'title="Location map"></iframe>')
    else:
        map_html = '<p style="font-size:12px;color:var(--muted);padding:1rem">📌 Location map not yet generated</p>'

    if real_cid(graph_cid):
        graph_html = (f'<iframe class="graph-frame" src="{IPFS_GATEWAY}/{graph_cid}" '
                      f'title="Knowledge graph"></iframe>')
    elif os.path.exists(local_graph):
        _shutil.copy2(local_graph, os.path.join(graphs_dir, f"{first_page_id}_graph.html"))
        graph_html = (f'<iframe class="graph-frame" '
                      f'src="../../graphs/{first_page_id}_graph.html" '
                      f'title="Knowledge graph"></iframe>')
    else:
        graph_html = '<p style="font-size:12px;color:var(--muted);padding:1rem">📊 Knowledge graph not yet generated</p>'

    # Entities — handle both dict and legacy string formats
    persons = iss.get("entities", {}).get("persons", [])
    locations = iss.get("entities", {}).get("locations", [])

    def person_label(p):
        if isinstance(p, dict):
            name = p.get("name_en") or p.get("name_uk", "")
            qid  = p.get("wikidata_id", "")
            url  = p.get("wikidata_url", "")
            if url:
                return f'<a class="entity-tag" href="{url}" target="_blank" rel="noopener">{name}</a>'
            return f'<span class="entity-tag">{name}</span>'
        return f'<span class="entity-tag">{p}</span>'

    person_tags = "".join(person_label(p) for p in persons)
    loc_tags = "".join(
        f'<span class="entity-tag">{l.get("name_en","")}</span>'
        for l in locations
    )

    # Metadata table
    tx = iss.get("tx_hash", "")
    mets_cid = iss.get("cids", {}).get("mets", "")

    # Only show blockchain/IPFS rows when real values exist
    def real_cid(cid): return cid and not cid.startswith("bafybeisimulated")
    def real_tx(tx):   return tx and tx not in ("sandbox", "", None) and len(tx) > 10

    blockchain_row = (
        f'<tr><td data-i18n="blockchain">Blockchain</td>'
        f'<td><a href="https://polygonscan.com/tx/{tx}" target="_blank" '
        f'rel="noopener">{tx[:20]}…</a></td></tr>'
        if real_tx(tx) else ""
    )
    # Individual IPFS links per file type
    def ipfs_link(label, cid):
        if not real_cid(cid): return ""
        return (f'<tr><td>{label}</td>'
                f'<td><a href="{IPFS_GATEWAY}/{cid}" target="_blank" '
                f'rel="noopener">{cid[:16]}… ↗</a></td></tr>')

    pages = iss.get("pages", [])
    iiif_cid_val = iss.get("cids", {}).get("iiif", "")
    net_cid_val  = iss.get("cids", {}).get("network", "")

    meta_rows = f"""
<tr><td>Date</td><td>{iss.get('date','')}</td></tr>
<tr><td>Issue</td><td>No. {iss.get('issue_number','')}</td></tr>
<tr><td>Pages</td><td>{len(pages)}</td></tr>
{blockchain_row}
{ipfs_link("🗂️ IIIF manifest", iiif_cid_val)}
{ipfs_link("🕸️ Network graph", net_cid_val)}
{ipfs_link("📦 METS package", mets_cid)}
"""

    # Stacked scan images — all pages loaded at once, scrollable, draggable
    _pages = iss.get("pages", [])
    _scan_cids = []
    for _p in _pages:
        _c = _p.get("cids", {}).get("scan", "")
        if _c and not _c.startswith("bafybeisimulated") and len(_c) >= 46:
            _scan_cids.append(_c)

    _pdf_cid = iss.get("pdf_cid","") or iss.get("cids",{}).get("pdf","")
    _has_pdf = bool(_pdf_cid) and not _pdf_cid.startswith("bafybeisimulated") and len(_pdf_cid) >= 46
    _pdf_link = (f'<a href="{IPFS_GATEWAY}/{_pdf_cid}" target="_blank" rel="noopener" '
                 f'style="font-size:13px;color:var(--blue)">📥 Download full issue PDF ↗</a>'
                 if _has_pdf else "")

    if _scan_cids:
        _imgs = "".join(
            f'<img src="{IPFS_GATEWAY}/{c}" '
            f'style="width:100%;display:block;margin-bottom:6px;border-radius:4px" '
            f'alt="Page {i+1}" loading="{"eager" if i==0 else "lazy"}">'
            for i, c in enumerate(_scan_cids)
        )
        pdf_cid_html = f'''<div style="margin-top:1rem">
<div id="scan-wrap" style="position:relative;width:100%;height:880px;overflow:hidden;
     background:#1a1a1a;border-radius:var(--radius);border:1px solid var(--border);
     cursor:grab;touch-action:none;user-select:none">
  <div id="scan-inner" style="position:absolute;top:0;left:0;transform-origin:0 0;padding:8px;box-sizing:border-box;width:100%">
    {_imgs}
  </div>
  <div style="position:absolute;top:8px;right:10px;font-size:11px;color:#fff;opacity:.5;pointer-events:none">
    Drag to pan · Scroll to zoom · {len(_scan_cids)} page(s)</div>
</div>
<div style="margin-top:.4rem">{_pdf_link}</div>
</div>
<script>
(function(){{
  var wrap=document.getElementById("scan-wrap");
  var inner=document.getElementById("scan-inner");
  var scale=1,ox=0,oy=0,drag=false,sx,sy,sox,soy;
  function clamp(v,a,b){{return Math.max(a,Math.min(b,v));}}
  function apply(){{inner.style.transform="translate("+ox+"px,"+oy+"px) scale("+scale+")";}}
  // Fit width on load
  var bw=wrap.clientWidth;
  ox=0; oy=0; scale=1; apply();
  wrap.addEventListener("mousedown",function(e){{drag=true;sx=e.clientX;sy=e.clientY;sox=ox;soy=oy;wrap.style.cursor="grabbing";e.preventDefault();}});
  window.addEventListener("mouseup",function(){{drag=false;wrap.style.cursor="grab";}});
  window.addEventListener("mousemove",function(e){{if(!drag)return;ox=sox+(e.clientX-sx);oy=soy+(e.clientY-sy);apply();}});
  wrap.addEventListener("wheel",function(e){{e.preventDefault();
    var r=wrap.getBoundingClientRect(),mx=e.clientX-r.left,my=e.clientY-r.top;
    var f=e.deltaY<0?1.1:1/1.1,ns=clamp(scale*f,0.2,5);
    ox=mx-(mx-ox)*(ns/scale);oy=my-(my-oy)*(ns/scale);scale=ns;apply();
  }},{{passive:false}});
  wrap.addEventListener("touchstart",function(e){{if(e.touches.length===1){{drag=true;sx=e.touches[0].clientX;sy=e.touches[0].clientY;sox=ox;soy=oy;}}}},{{passive:true}});
  wrap.addEventListener("touchend",function(){{drag=false;}});
  wrap.addEventListener("touchmove",function(e){{if(drag&&e.touches.length===1){{ox=sox+(e.touches[0].clientX-sx);oy=soy+(e.touches[0].clientY-sy);apply();}}}},{{passive:true}});
}})();
</script>'''
    elif _has_pdf:
        # Fallback: PDF iframe if no scan images
        pdf_cid_html = (f'<div style="margin-top:1rem">{_pdf_link}</div>')
    else:
        pdf_cid_html = ""

    # --- Feature 1: Issue stats ---
    word_count = sum(len((p.get("transcript_uk") or "").split()) for p in iss.get("pages", []))
    low_conf_count = sum(len(p.get("low_confidence_tokens", [])) for p in iss.get("pages", []))
    stats_panel_html = (
        f'<div style="display:flex;flex-wrap:wrap;gap:.5rem;margin-bottom:1rem">'
        f'<span style="font-size:12px;padding:4px 10px;border-radius:12px;background:var(--blue-lt);color:var(--blue)">📄 {len(pages)} pages</span>'
        f'<span style="font-size:12px;padding:4px 10px;border-radius:12px;background:var(--blue-lt);color:var(--blue)">👤 {len(persons)} persons</span>'
        f'<span style="font-size:12px;padding:4px 10px;border-radius:12px;background:var(--blue-lt);color:var(--blue)">📍 {len(locations)} locations</span>'
        f'<span style="font-size:12px;padding:4px 10px;border-radius:12px;background:var(--blue-lt);color:var(--blue)">📝 {word_count:,} words</span>'
        f'<span style="font-size:12px;padding:4px 10px;border-radius:12px;background:var(--blue-lt);color:var(--blue)">⚠ {low_conf_count} flagged tokens</span>'
        f'</div>'
    )

    # --- Feature 2: Citations (plain-text, copy-paste) ---
    chicago_citation = (
        f'Editorial Board. "Khliborob / O Lavrador," '
        f'No. {iss.get("issue_number","")}, {iss.get("date","")}. '
        f'{len(pages)} pages. Digitized via Khliborob Digital Archive. '
        f'https://hochheim.github.io/Khliborob/issues/{issue_id}/'
    )
    bibtex_citation = (
        f'@article{{khliborob_{issue_id},\n'
        f'  author = {{Editorial Board}},\n'
        f'  title  = {{Khliborob / O Lavrador}},\n'
        f'  year   = {{{iss.get("year", iss.get("date","")[:4])}}},\n'
        f'  note   = {{Issue No. {iss.get("issue_number","")}, {len(pages)} pages. '
        f'Digitized via Khliborob Digital Archive.}},\n'
        f'  url    = {{https://hochheim.github.io/Khliborob/issues/{issue_id}/}}\n'
        f'}}'
    )
    pre_style = (
        'display:none;margin-top:.8rem;font-size:11px;font-family:monospace;'
        'white-space:pre-wrap;color:var(--text);background:var(--bg);'
        'padding:.7rem;border-radius:4px;border:1px solid var(--border);'
        'user-select:all;cursor:text'
    )
    downloads_html = (
        f'<div style="margin-bottom:1.2rem;padding:1rem;background:var(--card-bg);'
        f'border:1px solid var(--border);border-radius:var(--radius)">'
        f'<h3 style="font-size:12px;font-weight:500;color:var(--muted);text-transform:uppercase;'
        f'letter-spacing:.05em;margin-bottom:.7rem">Citations</h3>'
        f'<div style="display:flex;gap:.6rem;flex-wrap:wrap;align-items:center">'
        f'<button onclick="toggleBibtex(\'{issue_id}\')" '
        f'style="font-size:12px;padding:5px 12px;border-radius:4px;background:var(--blue-lt);'
        f'color:var(--blue);cursor:pointer;border:1px solid var(--blue)">BibTeX</button>'
        f'<button onclick="toggleChicago(\'{issue_id}\')" '
        f'style="font-size:12px;padding:5px 12px;border-radius:4px;background:var(--blue-lt);'
        f'color:var(--blue);cursor:pointer;border:1px solid var(--blue)">Chicago</button>'
        f'</div>'
        f'<pre id="bibtex-popup-{issue_id}" style="{pre_style}">{bibtex_citation}</pre>'
        f'<div id="chicago-popup-{issue_id}" style="display:none;margin-top:.8rem;font-size:12px;'
        f'color:var(--text);background:var(--bg);padding:.7rem;border-radius:4px;'
        f'border:1px solid var(--border);user-select:all;cursor:text;font-style:italic">'
        f'{chicago_citation}</div></div>'
    )

    content = f"""
<div class="issue-layout">
  <div class="issue-header">
    <h1>Хлібороб / O Lavrador — {iss.get('date','')} (No. {iss.get('issue_number','')})</h1>
    {pdf_cid_html}
    <p>
  <span data-lang-en>{iss.get('translations',{}).get('abstract_en','')}</span>
  <span data-lang-uk style='display:none'>{iss.get('translations',{}).get('abstract_uk','') or iss.get('translations',{}).get('abstract_en','')}</span>
  <span data-lang-pt style='display:none'>{iss.get('translations',{}).get('abstract_pt','') or iss.get('translations',{}).get('abstract_en','')}</span>
</p>
  </div>

  {stats_panel_html}

  {gpu_blocks}

  <div class="content-grid">
    <div class="content-panel">
      <h3 data-i18n="transcript_uk">Original text (Ukrainian)</h3>
      <div class="transcript" lang="uk">{transcript_uk or '—'}</div>
    </div>
    <div class="content-panel">
      <h3 data-i18n="transcript_en">Translation (English)</h3>
      <div class="transcript" lang="en">{transcript_en or '—'}</div>
    </div>
    <div class="content-panel">
      <h3 data-i18n="transcript_pt">Tradução (Português Brasileiro)</h3>
      <div class="transcript" lang="pt-BR">{transcript_pt or '—'}</div>
    </div>
  </div>

  {downloads_html}

  <div class="content-grid">
    <div class="content-panel">
      <h3 data-i18n="locations">Locations</h3>
      {map_html}
      <div class="entity-list" style="margin-top:.6rem">{loc_tags or '—'}</div>
    </div>
    <div class="content-panel">
      <h3>Knowledge graph</h3>
      {graph_html}
      <div class="entity-list" style="margin-top:.6rem">{person_tags or '—'}</div>
    </div>
  </div>

  <div class="content-panel" style="margin-top:1.2rem">
    <h3>Metadata &amp; provenance</h3>
    <table class="meta-table">{meta_rows}</table>
  </div>
</div>"""
    return page_shell(f"{iss.get('date','')} No. {iss.get('issue_number','')}", content, depth=2)


def build_gpu_page(all_issues):
    from data_writer import GPU_CONNECTIONS

    issue_map = {iss["issue_id"]: iss for iss in all_issues}
    cards = ""
    for doc in GPU_CONNECTIONS:
        issue_links = ""
        for iid in doc.get("issues_referenced", []):
            if iid in issue_map:
                iss = issue_map[iid]
                issue_links += (f'<a class="issue-link" href="../issues/{iid}/">'
                                f'{iss.get("date","")} No.{iss.get("issue_number","")}</a>')

        cards += f"""
<div class="gpu-doc-card">
  <h2>{doc['document_type'].replace('_',' ').title()} — {doc['date']}</h2>
  <div class="arch-ref">{doc['archive_ref']}</div>
  <p><strong>From:</strong> {doc['sender']}</p>
  <p><strong>To:</strong> {doc['recipient']}</p>
  <p style="margin-top:.5rem">{doc['description_en']}</p>
  {f'<div style="margin-top:.6rem"><strong style="font-size:12px">Referenced issues:</strong><div class="issue-links" style="margin-top:.3rem">{issue_links}</div></div>' if issue_links else ''}
</div>"""

    content = f"""
<div class="gpu-page">
  <h1 style="font-size:20px;font-weight:500;margin-bottom:.4rem">GPU Documents</h1>
  <p style="font-size:13px;color:var(--muted);margin-bottom:1.2rem">
    Four declassified documents from the Branch State Archives of the Ukrainian
    Foreign Intelligence Service (SZRU), FISU F.1, Case 7408, Operation Nadiya.
    Source: <a href="https://szru.gov.ua/en/history/stories/the-holodomor-of-19321933--real-facts-and-the-chekists-disinformation"
    target="_blank" rel="noopener">SZRU, published 23 November 2025</a>.
  </p>
  {cards}
</div>"""
    return page_shell("GPU Documents", content, depth=1)


def build_search_page():
    content = """
<div id="search-results" style="padding-top:1.5rem">
  <div style="max-width:560px;margin-bottom:1.5rem">
    <div class="search-box">
      <input type="search" id="q" data-i18n="search_placeholder"
             placeholder="Search all pages" />
      <button onclick="doSearch()" data-i18n="search_btn">Search</button>
    </div>
  </div>
  <div id="results"></div>
</div>
<script>
function doSearch() {
  const q = document.getElementById('q').value.trim();
  if (!q) return;
  window.history.replaceState({},'','/search/?q='+encodeURIComponent(q));
  document.getElementById('results').innerHTML = '<p style="font-size:13px;color:var(--muted)">Searching…</p>';
  if (window.pagefind) {
    pagefind.search(q).then(r => {
      if (!r.results.length) {
        document.getElementById('results').innerHTML =
          '<p style="font-size:13px;color:var(--muted)">No results found.</p>';
        return;
      }
      Promise.all(r.results.slice(0,20).map(x => x.data())).then(data => {
        document.getElementById('results').innerHTML = data.map(d => `
          <div class="result-card">
            <div class="result-date">${d.meta?.date||''} ${d.meta?.issue||''}</div>
            <div class="result-title"><a href="${d.url}">${d.meta?.title||d.url}</a></div>
            <div class="result-snippet">${d.excerpt}</div>
          </div>`).join('');
      });
    });
  } else {
    document.getElementById('results').innerHTML =
      '<p style="font-size:13px;color:var(--muted)">Search index not built yet. Run: <code>pagefind --site output_site</code></p>';
  }
}
const params = new URLSearchParams(window.location.search);
const q = params.get('q');
if (q) { document.getElementById('q').value = q; doSearch(); }
document.getElementById('q').addEventListener('keydown', e => {
  if (e.key === 'Enter') doSearch();
});
</script>
<script src="../pagefind/pagefind.js" type="module"></script>"""
    return page_shell("Search", content, depth=1)


def build_about_page():
    content = """
<div style="max-width:720px;margin:2rem auto;padding:0 1.5rem">
  <h1 style="font-size:22px;font-weight:500;margin-bottom:1rem">About this archive</h1>

  <h2 style="font-size:16px;font-weight:500;margin:1.2rem 0 .4rem">The newspaper</h2>
  <p style="font-size:14px;line-height:1.7;color:var(--text)">
    Khliborob (Хлібороб, "The Farmer") was founded in Porto União, Paraná, Brazil
    in 1924 by the Ukrainian poet Petro Karmansky. It is one of the longest-running
    Ukrainian diaspora newspapers in the world, published continuously to the present
    day (under the name O Lavrador since the Vargas-era forced Portuguese transition
    of 1940–46). It is published by SUBRAS (Sociedade Ucraniana do Brasil) in Curitiba.
  </p>

  <h2 style="font-size:16px;font-weight:500;margin:1.2rem 0 .4rem">The GPU discovery</h2>
  <p style="font-size:14px;line-height:1.7;color:var(--text)">
    Four declassified documents from the Branch State Archives of the Ukrainian
    Foreign Intelligence Service (SZRU) demonstrate that Khliborob circulated
    within a transnational Ukrainian political network connecting Curitiba, São Paulo,
    and Istanbul during the Holodomor period (1929–1933). GPU intelligence summaries
    compiled for Japanese diplomatic services in November 1932 cite the newspaper
    as a source for information about executions of starving peasants in Soviet Ukraine.
  </p>

  <h2 style="font-size:16px;font-weight:500;margin:1.2rem 0 .4rem">The pipeline</h2>
  <p style="font-size:14px;line-height:1.7;color:var(--text)">
    This archive was built using an open-source digitization pipeline developed at
    the University of Münster. Issues are processed using Gemini 2.5 Flash for OCR
    and bilingual (Ukrainian/English) transcription, stored permanently on IPFS via
    Pinata, and cryptographically anchored on the Polygon blockchain. The pipeline
    source code is available at
    <a href="https://github.com/yourusername/khliborob-pipeline" target="_blank"
       rel="noopener">GitHub</a>.
  </p>

  <h2 style="font-size:16px;font-weight:500;margin:1.2rem 0 .4rem">Partners</h2>
  <p style="font-size:14px;line-height:1.7;color:var(--text)">
    <strong>SUBRAS</strong> (Sociedade Ucraniana do Brasil) — institutional partner
    and custodian of the physical archive.<br>
    <strong>University of Münster</strong> — Institut für Osteuropäische Geschichte.<br>
    <strong>SZRU</strong> (Foreign Intelligence Service of Ukraine) — provided
    declassified archival documents.
  </p>

  <p style="font-size:12px;color:var(--muted);margin-top:2rem">
    All digitized materials are deposited in the
    <a href="https://archive.org" target="_blank" rel="noopener">Internet Archive</a>
    for permanent preservation. Blockchain provenance is anchored on the Polygon
    mainnet. This archive is free and open access.
  </p>
</div>"""
    return page_shell("About", content, depth=1)



# =====================================================================
# AGGREGATED VIEWS — year and all-history maps/graphs from local data
# =====================================================================
def build_aggregated_views(issues):
    """Generates aggregated location maps and knowledge graphs from
    local JSON data, without requiring Omeka S to be running."""
    from xml_generators import generate_aggregated_map, generate_aggregated_graph
    import shutil

    agg_dir = os.path.join(SITE_DIR, "aggregated")
    os.makedirs(agg_dir, exist_ok=True)

    # Collect all locations and entities across all issues
    all_locs  = []
    all_nodes = []
    all_edges = []
    by_year   = defaultdict(list)

    for iss in issues:
        year = iss.get("year", "unknown")
        by_year[year].append(iss)

        for loc in iss.get("entities", {}).get("locations", []):
            lat = loc.get("lat", 0.0)
            lon = loc.get("lon", 0.0)
            if lat == 0.0 and lon == 0.0:
                continue
            all_locs.append({
                "name_en":    loc.get("name_en", ""),
                "name_uk":    loc.get("name_uk", ""),
                "lat":        lat,
                "lon":        lon,
                "source_page": iss.get("issue_id", "")
            })

        issue_id = iss.get("issue_id", "")
        all_nodes.append({"id": issue_id, "type": "page", "label": issue_id})
        for person in iss.get("entities", {}).get("persons", []):
            if isinstance(person, dict):
                name = person.get("name_en") or person.get("name_uk", "")
            else:
                name = str(person)
            if name:
                all_nodes.append({"id": name, "type": "person", "label": name})
                all_edges.append({"source": issue_id, "target": name, "label": "MENTIONS"})
        for loc in iss.get("entities", {}).get("locations", []):
            name = loc.get("name_en", "")
            if name:
                all_nodes.append({"id": name, "type": "location", "label": name})
                all_edges.append({"source": issue_id, "target": name, "label": "LOCATED IN"})

    output_xml_dir = OUTPUT_XML  # module-level, env-var driven

    site_url = "https://hochheim.github.io/Khliborob/"

    # All-history map and graph
    if all_locs:
        map_path = generate_aggregated_map(
            "all_history", all_locs,
            "Full Archive — Location Map",
            f"{len(issues)} total issues", output_xml_dir,
            site_base_url=site_url
        )
        shutil.copy2(map_path, agg_dir)
    if all_nodes:
        graph_path = generate_aggregated_graph(
            "all_history", all_nodes, all_edges,
            "Full Archive — Knowledge Graph",
            f"{len(issues)} total issues", output_xml_dir,
            site_base_url=site_url
        )
        shutil.copy2(graph_path, agg_dir)

    # Per-decade maps and graphs
    decades = defaultdict(list)
    for year, yiss in by_year.items():
        if year == "unknown":
            continue
        decade = str(int(year) // 10 * 10) + "s"
        decades[decade].extend(yiss)

    for decade, decade_issues in decades.items():
        dec_locs, dec_nodes, dec_edges = [], [], []
        for iss in decade_issues:
            iid = iss.get("issue_id", "")
            dec_nodes.append({"id": iid, "type": "page", "label": iid})
            for loc in iss.get("entities", {}).get("locations", []):
                lat, lon = loc.get("lat", 0.0), loc.get("lon", 0.0)
                if lat != 0.0 or lon != 0.0:
                    dec_locs.append({"name_en": loc.get("name_en",""), "name_uk": loc.get("name_uk",""),
                                     "lat": lat, "lon": lon, "source_page": iid})
                name = loc.get("name_en","")
                if name:
                    dec_nodes.append({"id": name, "type": "location", "label": name})
                    dec_edges.append({"source": iid, "target": name, "label": "LOCATED IN"})
            for person in iss.get("entities", {}).get("persons", []):
                name = person.get("name_en") or person.get("name_uk","") if isinstance(person, dict) else str(person)
                if name:
                    dec_nodes.append({"id": name, "type": "person", "label": name})
                    dec_edges.append({"source": iid, "target": name, "label": "MENTIONS"})
        if dec_locs:
            map_path = generate_aggregated_map(
                f"decade_{decade}", dec_locs, f"{decade} — Location Map",
                f"{len(decade_issues)} issue(s)", output_xml_dir, site_base_url=site_url)
            shutil.copy2(map_path, agg_dir)
        if dec_nodes:
            graph_path = generate_aggregated_graph(
                f"decade_{decade}", dec_nodes, dec_edges, f"{decade} — Knowledge Graph",
                f"{len(decade_issues)} issue(s)", output_xml_dir, site_base_url=site_url)
            shutil.copy2(graph_path, agg_dir)

    # Per-year maps and graphs
    for year, year_issues in by_year.items():
        if year == "unknown":
            continue
        year_locs, year_nodes, year_edges = [], [], []
        for iss in year_issues:
            iid = iss.get("issue_id", "")
            year_nodes.append({"id": iid, "type": "page", "label": iid})
            for loc in iss.get("entities", {}).get("locations", []):
                lat, lon = loc.get("lat", 0.0), loc.get("lon", 0.0)
                if lat != 0.0 or lon != 0.0:
                    year_locs.append({"name_en": loc.get("name_en",""), "name_uk": loc.get("name_uk",""),
                                      "lat": lat, "lon": lon, "source_page": iid})
                name = loc.get("name_en","")
                if name:
                    year_nodes.append({"id": name, "type": "location", "label": name})
                    year_edges.append({"source": iid, "target": name, "label": "LOCATED IN"})
            for person in iss.get("entities", {}).get("persons", []):
                name = person.get("name_en") or person.get("name_uk","") if isinstance(person, dict) else str(person)
                if name:
                    year_nodes.append({"id": name, "type": "person", "label": name})
                    year_edges.append({"source": iid, "target": name, "label": "MENTIONS"})
        if year_locs:
            map_path = generate_aggregated_map(
                f"year_{year}", year_locs, f"{year} — Location Map",
                f"{len(year_issues)} issue(s)", output_xml_dir, site_base_url=site_url)
            shutil.copy2(map_path, agg_dir)
        if year_nodes:
            graph_path = generate_aggregated_graph(
                f"year_{year}", year_nodes, year_edges, f"{year} — Knowledge Graph",
                f"{len(year_issues)} issue(s)", output_xml_dir, site_base_url=site_url)
            shutil.copy2(graph_path, agg_dir)

    # --- Feature 8: Person co-mention network ---
    try:
        from itertools import combinations as _combinations
        person_cocount = defaultdict(int)
        all_net_persons = set()
        for iss in issues:
            pnames = []
            for p in iss.get("entities", {}).get("persons", []):
                nm = (p.get("name_en") or p.get("name_uk","")) if isinstance(p, dict) else str(p)
                if nm:
                    pnames.append(nm)
                    all_net_persons.add(nm)
            for pair in _combinations(sorted(set(pnames)), 2):
                person_cocount[pair] += 1
        if person_cocount:
            net_nodes_pn = [{"id": nm, "type": "person", "label": nm} for nm in all_net_persons]
            net_edges_pn = [
                {"source": p1, "target": p2, "label": f"co-mentioned {cnt}x"}
                for (p1, p2), cnt in person_cocount.items()
            ]
            pnet_path = generate_aggregated_graph(
                "person_network", net_nodes_pn, net_edges_pn,
                "Person Co-mention Network",
                f"{len(all_net_persons)} persons across {len(issues)} issues",
                output_xml_dir, site_base_url=site_url
            )
            shutil.copy2(pnet_path, agg_dir)
            print("   ✅ Person co-mention network")
    except Exception as _e:
        print(f"   ⚠ Person network skipped: {_e}")

    # --- Feature 9: Migration arc map ---
    try:
        ukraine_locs = []
        brazil_locs  = []
        for iss in issues:
            for loc in iss.get("entities", {}).get("locations", []):
                lat = loc.get("lat") or 0.0
                lon = loc.get("lon") or 0.0
                if lat == 0.0 and lon == 0.0:
                    continue
                name_en = loc.get("name_en","")
                if lat > 40 and 20 < lon < 50:
                    ukraine_locs.append({"name": name_en, "lat": lat, "lon": lon})
                elif lat < 10 and lon < -30:
                    brazil_locs.append({"name": name_en, "lat": lat, "lon": lon})

        arc_pairs = []
        seen_pairs = set()
        for ul in ukraine_locs:
            for bl in brazil_locs:
                key = (ul["name"], bl["name"])
                if key not in seen_pairs:
                    arc_pairs.append((ul, bl))
                    seen_pairs.add(key)

        import json as _json
        arcs_json = _json.dumps(arc_pairs[:200])
        migration_html = f"""<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Migration Arc Map — Khliborob</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  body{{margin:0;font-family:sans-serif;background:#111;color:#eee}}
  #map{{width:100%;height:100vh}}
  #legend{{position:absolute;top:10px;left:50%;transform:translateX(-50%);z-index:1000;
           background:rgba(0,0,0,.75);color:#eee;padding:8px 16px;border-radius:6px;font-size:13px}}
</style>
</head><body>
<div id="legend">Migration Arcs: Ukrainian/Eastern European ↔ Brazilian/South American locations</div>
<div id="map"></div>
<script>
var map = L.map('map',{{center:[20,-20],zoom:3,
  preferCanvas:true}});
L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{
  attribution:'&copy; OpenStreetMap &copy; CARTO',maxZoom:19}}).addTo(map);
var arcs = {arcs_json};
arcs.forEach(function(pair){{
  var ul=pair[0], bl=pair[1];
  var latlngs = [];
  // Bezier-style arc: add intermediate point
  var midLat=(ul.lat+bl.lat)/2+15;
  var midLon=(ul.lon+bl.lon)/2;
  for(var t=0;t<=1;t+=0.05){{
    var lat=(1-t)*(1-t)*ul.lat + 2*(1-t)*t*midLat + t*t*bl.lat;
    var lon=(1-t)*(1-t)*ul.lon + 2*(1-t)*t*midLon + t*t*bl.lon;
    latlngs.push([lat,lon]);
  }}
  L.polyline(latlngs,{{color:'#FFD500',weight:1.5,opacity:.6}}).addTo(map)
    .bindPopup(ul.name + ' ↔ ' + bl.name);
  L.circleMarker([ul.lat,ul.lon],{{radius:4,color:'#005BBB',fillOpacity:.8}}).addTo(map)
    .bindPopup(ul.name);
  L.circleMarker([bl.lat,bl.lon],{{radius:4,color:'#e63946',fillOpacity:.8}}).addTo(map)
    .bindPopup(bl.name);
}});
</script></body></html>"""
        with open(os.path.join(agg_dir, "migration_arcs.html"), "w", encoding="utf-8") as _f:
            _f.write(migration_html)
        print("   ✅ Migration arc map")
    except Exception as _e:
        print(f"   ⚠ Migration arc map skipped: {_e}")

    # --- Features 6 & 7: Per-year language stats for charts ---
    import json as _json
    year_chart_data = {}
    keywords = ["Україна", "Бразилія", "церква", "голод", "праця"]
    for yr, yiss in sorted(by_year.items()):
        if yr == "unknown":
            continue
        total_chars = 0
        cyrillic_chars = 0
        romance_words = 0
        total_words = 0
        kw_counts = {kw: 0 for kw in keywords}
        for iss in yiss:
            for pg in iss.get("pages", []):
                txt = pg.get("transcript_uk") or ""
                total_chars += len(txt)
                cyrillic_chars += sum(1 for c in txt if 'Ѐ' <= c <= 'ӿ')
                words = txt.split()
                total_words += len(words)
                for w in words:
                    wl = w.lower().rstrip(".,!?;:")
                    if (wl.endswith("ção") or wl.endswith("ão") or
                            wl.endswith("inho") or wl.endswith("eiro") or
                            wl in ("brasil", "fazenda", "estado", "cidade", "curitiba")):
                        romance_words += 1
                for kw in keywords:
                    kw_counts[kw] += txt.count(kw)
        year_chart_data[yr] = {
            "cyrillic_ratio": round(cyrillic_chars / total_chars, 4) if total_chars else 0,
            "romance_per_1k": round(romance_words / total_words * 1000, 2) if total_words else 0,
            "kw": {kw: round(kw_counts[kw] / total_words * 1000, 3) if total_words else 0
                   for kw in keywords},
        }

    chart_years = _json.dumps(sorted(year_chart_data.keys()))
    cyr_ratios  = _json.dumps([year_chart_data[y]["cyrillic_ratio"] for y in sorted(year_chart_data)])
    romance_vals= _json.dumps([year_chart_data[y]["romance_per_1k"]  for y in sorted(year_chart_data)])
    kw_datasets = []
    kw_colors   = ["#FFD500","#e63946","#2a9d8f","#e9c46a","#a8dadc"]
    for i, kw in enumerate(keywords):
        vals = [year_chart_data[y]["kw"][kw] for y in sorted(year_chart_data)]
        kw_datasets.append({
            "label": kw, "data": vals,
            "borderColor": kw_colors[i % len(kw_colors)],
            "backgroundColor": "transparent",
            "tension": 0.3, "pointRadius": 3,
        })
    kw_datasets_json = _json.dumps(kw_datasets, ensure_ascii=False)

    charts_html = f"""
<div style="margin-top:2.5rem">
  <h2 style="font-size:14px;font-weight:700;text-transform:uppercase;letter-spacing:.06em;
             color:var(--muted);margin-bottom:.8rem">Language Analysis</h2>

  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);
              padding:1.2rem;margin-bottom:1.2rem">
    <h3 style="font-size:13px;font-weight:600;margin-bottom:.8rem">
      Language Drift: Cyrillic vs. Romance Loanwords over Time
    </h3>
    <canvas id="langDriftChart" height="80"></canvas>
  </div>

  <div style="background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);
              padding:1.2rem;margin-bottom:1.2rem">
    <h3 style="font-size:13px;font-weight:600;margin-bottom:.8rem">
      Keyword Frequency Timeline (per 1,000 words)
    </h3>
    <canvas id="kwChart" height="80"></canvas>
  </div>
</div>

<script src="https://cdn.jsdelivr.net/npm/chart.js@4/dist/chart.umd.min.js"></script>
<script>
(function(){{
  var years   = {chart_years};
  var cyrRat  = {cyr_ratios};
  var romVals = {romance_vals};

  var isDark = window.matchMedia && window.matchMedia('(prefers-color-scheme:dark)').matches;
  var gridColor = isDark ? 'rgba(255,255,255,.1)' : 'rgba(0,0,0,.08)';
  var fontColor = isDark ? '#aaa' : '#666';

  new Chart(document.getElementById('langDriftChart'), {{
    type: 'line',
    data: {{
      labels: years,
      datasets: [
        {{
          label: 'Cyrillic character ratio',
          data: cyrRat,
          borderColor: '#005BBB',
          backgroundColor: 'rgba(0,91,187,.1)',
          fill: true,
          tension: 0.3,
          pointRadius: 3,
          yAxisID: 'y',
        }},
        {{
          label: 'Romance loanwords per 1,000 words',
          data: romVals,
          borderColor: '#e63946',
          backgroundColor: 'transparent',
          tension: 0.3,
          pointRadius: 3,
          yAxisID: 'y1',
        }},
      ]
    }},
    options: {{
      responsive: true,
      interaction: {{mode:'index',intersect:false}},
      plugins: {{ legend: {{ labels: {{ color: fontColor }} }} }},
      scales: {{
        x: {{ ticks: {{ color: fontColor, maxTicksLimit: 12 }}, grid: {{ color: gridColor }} }},
        y: {{ type:'linear', position:'left', ticks:{{ color:'#005BBB' }}, grid:{{ color: gridColor }},
              title:{{ display:true, text:'Cyrillic ratio', color:fontColor }} }},
        y1: {{ type:'linear', position:'right', ticks:{{ color:'#e63946' }}, grid:{{ drawOnChartArea:false }},
               title:{{ display:true, text:'Romance / 1k words', color:fontColor }} }},
      }}
    }}
  }});

  var kwData = {kw_datasets_json};
  new Chart(document.getElementById('kwChart'), {{
    type: 'line',
    data: {{ labels: years, datasets: kwData }},
    options: {{
      responsive: true,
      interaction: {{mode:'index',intersect:false}},
      plugins: {{ legend: {{ labels: {{ color: fontColor }} }} }},
      scales: {{
        x: {{ ticks:{{ color:fontColor, maxTicksLimit:12 }}, grid:{{ color:gridColor }} }},
        y: {{ ticks:{{ color:fontColor }}, grid:{{ color:gridColor }},
              title:{{ display:true, text:'Occurrences per 1,000 words', color:fontColor }} }},
      }}
    }}
  }});
}})();
</script>"""

    # Build the aggregated views page — structured by scope
    # Collect available files, grouped
    avail = {f for f in os.listdir(agg_dir) if f.endswith(".html") and f != "index.html"
             and "bukovina" not in f.lower()}

    def view_card(fname, label, icon):
        if fname not in avail:
            return ""
        kind = "📍 Location Map" if "map" in fname else "🧠 Knowledge Graph"
        return (f'<a href="{fname}" target="_blank" style="display:flex;align-items:center;gap:12px;'
                f'padding:12px 16px;border:1px solid var(--border);border-radius:var(--radius);'
                f'background:var(--card-bg);text-decoration:none;color:var(--text);'
                f'transition:box-shadow .15s" '
                f'onmouseover="this.style.boxShadow=\'0 2px 8px rgba(0,0,0,.12)\'" '
                f'onmouseout="this.style.boxShadow=\'\'">'
                f'<span style="font-size:22px">{icon}</span>'
                f'<div><div style="font-weight:600;font-size:14px">{label}</div>'
                f'<div style="font-size:12px;color:var(--muted);margin-top:2px">{kind} — opens in new tab</div>'
                f'</div></a>')

    def section(title, cards_html):
        if not cards_html.strip():
            return ""
        return (f'<div style="margin-bottom:2rem">'
                f'<h2 style="font-size:14px;font-weight:700;text-transform:uppercase;'
                f'letter-spacing:.06em;color:var(--muted);margin-bottom:.8rem">{title}</h2>'
                f'<div style="display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:.7rem">'
                f'{cards_html}</div></div>')

    full_archive = (
        view_card("all_history_agg_map.html",   "Full Archive", "🌍") +
        view_card("all_history_agg_graph.html",  "Full Archive", "🧠")
    )

    # Decades
    decade_cards = ""
    for fname in sorted(avail):
        if not fname.startswith("decade_"): continue
        decade = fname.split("_")[1]  # e.g. "1920s"
        icon = "🌍" if "map" in fname else "🧠"
        decade_cards += view_card(fname, f"{decade} Decade", icon)

    # Years
    year_cards = ""
    for fname in sorted(avail):
        if not fname.startswith("year_"): continue
        year = fname.split("_")[1]
        icon = "🌍" if "map" in fname else "🧠"
        year_cards += view_card(fname, f"Year {year}", icon)

    # Networks section
    network_cards = view_card("person_network_agg_graph.html", "Person Co-mention Network", "🕸️")

    # Migration section
    migration_card = ""
    if "migration_arcs.html" in avail:
        migration_card = (
            f'<a href="migration_arcs.html" target="_blank" style="display:flex;align-items:center;gap:12px;'
            f'padding:12px 16px;border:1px solid var(--border);border-radius:var(--radius);'
            f'background:var(--card-bg);text-decoration:none;color:var(--text);transition:box-shadow .15s" '
            f'onmouseover="this.style.boxShadow=\'0 2px 8px rgba(0,0,0,.12)\'" '
            f'onmouseout="this.style.boxShadow=\'\'">'
            f'<span style="font-size:22px">🗺️</span>'
            f'<div><div style="font-weight:600;font-size:14px">Migration Arc Map</div>'
            f'<div style="font-size:12px;color:var(--muted);margin-top:2px">Ukrainian ↔ Brazilian location arcs — opens in new tab</div>'
            f'</div></a>'
        )

    agg_body = (section("Full Archive", full_archive) +
                section("Networks", network_cards) +
                section("Migration", migration_card) +
                section("By Decade", decade_cards) +
                section("By Year", year_cards))

    if not agg_body.strip():
        agg_body = '<p style="color:var(--muted);font-size:13px">No aggregated views available yet.</p>'

    agg_page = page_shell("Aggregated Views", f"""
<div style="max-width:860px;margin:2rem auto;padding:0 1.5rem">
  <h1 style="font-size:20px;font-weight:600;margin-bottom:.3rem">Maps &amp; Knowledge Graphs</h1>
  <p style="font-size:13px;color:var(--muted);margin-bottom:1.8rem">
    Location maps and knowledge graphs aggregated across all issues — explore by decade, year, or the full archive.
    Each view opens in a new tab with full interactivity.
  </p>
  {agg_body}
  {charts_html}
</div>""")

    with open(os.path.join(SITE_DIR, "aggregated", "index.html"), "w", encoding="utf-8") as f:
        f.write(agg_page)
    print("   ✅ aggregated/index.html")


def build_chat_page():
    """Builds the AI research chatbot page that connects to rag_query.py."""
    content = """
<div style="max-width:800px;margin:0 auto;padding:1.5rem;display:flex;flex-direction:column;height:calc(100vh - 120px)">
  <div style="margin-bottom:1rem">
    <h1 style="font-size:20px;font-weight:500;margin-bottom:.3rem" data-i18n="nav_chat">Research Agent</h1>
    <p style="font-size:13px;color:var(--muted)">
      Ask questions about the archive in Ukrainian, English, or Brazilian Portuguese.
      Answers are grounded exclusively in the digitized corpus with full citations.
      <strong>Start the RAG server first:</strong> <code>python rag_query.py</code>
    </p>
  </div>

  <div id="chat-messages" style="flex:1;overflow-y:auto;border:1px solid var(--border);
       border-radius:var(--radius);padding:1rem;background:var(--card-bg);margin-bottom:1rem;
       display:flex;flex-direction:column;gap:.8rem">
    <div class="msg msg-system">
      <div class="msg-bubble msg-bubble-system">
        👋 Welcome to the Khliborob Research Agent. I can answer questions about the
        digitized issues of <em>Хлібороб / O Lavrador</em> — try asking about people,
        places, or events mentioned in the archive.
      </div>
    </div>
  </div>

  <div style="display:flex;gap:.5rem">
    <input id="chat-input" type="text" placeholder="Ask a question about the archive…"
           style="flex:1;font-size:14px;padding:.55rem .9rem;border:1px solid var(--border-strong,#ccc);
                  border-radius:var(--radius);background:var(--card-bg);color:var(--text)" />
    <button onclick="sendQuestion()" id="send-btn"
            style="font-size:13px;padding:.55rem 1.1rem;border:none;border-radius:var(--radius);
                   background:#1a4a8a;color:#fff;font-weight:500;cursor:pointer;white-space:nowrap">
      Ask
    </button>
  </div>

  <p style="font-size:11px;color:var(--muted);margin-top:.5rem;text-align:center">
    Answers are generated from the digitized corpus only. All claims cite their source.
  </p>
</div>

<style>
.msg { display:flex; flex-direction:column; }
.msg-user { align-items:flex-end; }
.msg-assistant { align-items:flex-start; }
.msg-system { align-items:flex-start; }
.msg-bubble {
  max-width:85%; font-size:13px; line-height:1.6; padding:.6rem .9rem;
  border-radius:10px; white-space:pre-wrap; word-break:break-word;
}
.msg-bubble-user      { background:#1a4a8a; color:#fff; }
.msg-bubble-assistant { background:var(--card-bg); border:1px solid var(--border); color:var(--text); }
.msg-bubble-system    { background:var(--blue-lt,#e8f0fb); color:var(--text); }
.msg-bubble-error     { background:#fff0f0; border:1px solid #fcc; color:#900; }
.citations-block {
  margin-top:.5rem; font-size:11px; color:var(--muted);
  border-top:1px solid var(--border); padding-top:.4rem;
}
.citation-item { margin-bottom:.2rem; }
.citation-item a { color:#1a4a8a; }
.typing { opacity:.6; font-style:italic; }
</style>

<script>
const RAG_URL = "http://localhost:5050/query";

async function sendQuestion() {
  const input = document.getElementById("chat-input");
  const q = input.value.trim();
  if (!q) return;

  input.value = "";
  document.getElementById("send-btn").disabled = true;

  // Add user bubble
  appendMsg("user", q);

  // Add typing indicator
  const typingId = appendMsg("assistant", "Searching the archive…", "typing");

  try {
    const resp = await fetch(RAG_URL, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({question: q, top_k: 8})
    });

    if (!resp.ok) {
      const err = await resp.json();
      replaceMsg(typingId, "error",
        "⚠️ Server error: " + (err.error || resp.statusText) +
        "\n\nMake sure the RAG server is running: python rag_query.py");
      return;
    }

    const data = await resp.json();

    // Format citations
    let citBlock = "";
    if (data.citations && data.citations.length) {
      citBlock = '<div class="citations-block"><strong>Sources:</strong><br>';
      data.citations.forEach(c => {
        const link = c.ipfs_url
          ? `<a href="${c.ipfs_url}" target="_blank" rel="noopener">IPFS</a>`
          : "";
        const poly = c.tx_hash && c.tx_hash !== "sandbox"
          ? `<a href="https://polygonscan.com/tx/${c.tx_hash}" target="_blank" rel="noopener">Blockchain</a>`
          : "";
        const links = [link, poly].filter(Boolean).join(" · ");
        citBlock += `<div class="citation-item">[${c.citation_number}] ${c.newspaper_en}, `
          + `${c.publication_date}, No. ${c.issue_number} — score: ${c.similarity_score}`
          + (links ? ` — ${links}` : "") + `</div>`;
      });
      citBlock += "</div>";
    }

    replaceMsg(typingId, "assistant", data.answer, "", citBlock);

  } catch (err) {
    replaceMsg(typingId, "error",
      "⚠️ Could not reach the RAG server at localhost:5050.\n\n" +
      "Run: python rag_query.py\n\nError: " + err.message);
  } finally {
    document.getElementById("send-btn").disabled = false;
    input.focus();
  }
}

function appendMsg(role, text, extra_class = "", citBlock = "") {
  const id = "msg-" + Date.now() + "-" + Math.random();
  const box = document.getElementById("chat-messages");
  const div = document.createElement("div");
  div.className = "msg msg-" + role;
  div.id = id;
  div.innerHTML = `<div class="msg-bubble msg-bubble-${extra_class || role}">${
    escHtml(text)
  }</div>${citBlock}`;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  return id;
}

function replaceMsg(id, role, text, extra_class = "", citBlock = "") {
  const div = document.getElementById(id);
  if (!div) return;
  div.className = "msg msg-" + role;
  div.innerHTML = `<div class="msg-bubble msg-bubble-${extra_class || role}">${
    escHtml(text)
  }</div>${citBlock}`;
  document.getElementById("chat-messages").scrollTop = 99999;
}

function escHtml(t) {
  return t.replace(/&/g,"&amp;").replace(/</g,"&lt;")
          .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}

document.getElementById("chat-input").addEventListener("keydown", e => {
  if (e.key === "Enter") sendQuestion();
});
</script>"""
    return page_shell("Research Agent", content, depth=1)

# =====================================================================
# PERSON INDEX PAGE  (Feature 3)
# =====================================================================
def build_person_index(issues):
    """Alphabetically sorted, filterable list of all unique persons."""
    # Collect person -> list of issues
    person_issues = defaultdict(list)
    for iss in issues:
        for p in iss.get("entities", {}).get("persons", []):
            if isinstance(p, dict):
                name_en = p.get("name_en") or p.get("name_uk", "")
                name_uk = p.get("name_uk", "")
            else:
                name_en = str(p)
                name_uk = ""
            if name_en:
                person_issues[name_en].append({
                    "issue_id": iss.get("issue_id",""),
                    "date": iss.get("date",""),
                    "issue_number": iss.get("issue_number",""),
                    "name_uk": name_uk,
                })

    # Group by first letter
    by_letter = defaultdict(list)
    for name in sorted(person_issues.keys(), key=lambda x: x.upper()):
        letter = name[0].upper() if name else "?"
        by_letter[letter].append(name)

    letter_nav = "".join(
        f'<a href="#letter-{l}" style="font-size:12px;padding:2px 6px;border-radius:3px;'
        f'background:var(--blue-lt);color:var(--blue);text-decoration:none">{l}</a> '
        for l in sorted(by_letter.keys())
    )

    rows_html = ""
    for letter in sorted(by_letter.keys()):
        rows_html += (f'<h2 class="letter-head" id="letter-{letter}" '
                      f'style="font-size:14px;font-weight:600;'
                      f'color:var(--muted);border-bottom:1px solid var(--border);'
                      f'padding-bottom:.3rem;margin:1.2rem 0 .5rem">{letter}</h2>')
        for name in by_letter[letter]:
            issue_list = person_issues[name]
            name_uk = issue_list[0]["name_uk"] if issue_list else ""
            count = len(issue_list)
            links = " ".join(
                f'<a href="../issues/{i["issue_id"]}/" style="font-size:11px;padding:2px 7px;'
                f'border-radius:3px;background:var(--blue-lt);color:var(--blue);'
                f'text-decoration:none">{i["date"]} No.{i["issue_number"]}</a>'
                for i in issue_list[:10]
            )
            rows_html += (
                f'<div class="person-row" data-name="{name.lower()}" data-count="{count}" '
                f'style="padding:.5rem .2rem;border-bottom:1px solid var(--border);display:flex;'
                f'align-items:baseline;gap:.6rem;flex-wrap:wrap">'
                f'<span style="font-weight:500;font-size:13px;min-width:180px">{name}</span>'
                f'{"<span style=\'font-size:11px;color:var(--muted)\'>" + name_uk + "</span>" if name_uk and name_uk != name else ""}'
                f'<span style="font-size:11px;color:var(--muted);margin-right:.3rem">'
                f'{count} issue{"s" if count!=1 else ""}</span>'
                f'{links}</div>'
            )

    content = f"""
<div style="max-width:860px;margin:2rem auto;padding:0 1.5rem">
  <h1 data-i18n="person_index_title" style="font-size:20px;font-weight:600;margin-bottom:.3rem">Person Index</h1>
  <p style="font-size:13px;color:var(--muted);margin-bottom:1rem">
    {len(person_issues)} unique persons across {len(issues)} issues.
  </p>
  <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:1rem;flex-wrap:wrap">
    <input id="person-filter" type="search" data-i18n="filter_persons" placeholder="Filter persons…"
      oninput="filterPersons(this.value)"
      style="font-size:13px;padding:.45rem .8rem;border:1px solid var(--border);
             border-radius:var(--radius);background:var(--card-bg);color:var(--text);width:100%;max-width:280px">
    <div style="display:flex;gap:.3rem">
      <button id="psort-alpha" onclick="sortPersons('alpha')"
        style="font-size:12px;padding:4px 12px;border-radius:4px;cursor:pointer;
               background:var(--blue);color:#fff;border:none" data-i18n="sort_alpha">A–Z</button>
      <button id="psort-freq" onclick="sortPersons('freq')"
        style="font-size:12px;padding:4px 12px;border-radius:4px;cursor:pointer;
               background:var(--card-bg);color:var(--text);border:1px solid var(--border)"
        data-i18n="sort_freq">Most mentions</button>
    </div>
  </div>
  <div id="person-letter-nav" style="display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:1.2rem">{letter_nav}</div>
  <div id="person-list">{rows_html}</div>
</div>
<script>
var _personSortMode = 'alpha';
function filterPersons(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('.person-row').forEach(function(row) {{
    var name = row.dataset.name || '';
    row.style.display = (!q || name.includes(q)) ? '' : 'none';
  }});
}}
function sortPersons(mode) {{
  _personSortMode = mode;
  var list = document.getElementById('person-list');
  var heads = list.querySelectorAll('.letter-head');
  var rows = Array.from(list.querySelectorAll('.person-row'));
  if (mode === 'freq') {{
    rows.sort(function(a,b){{ return parseInt(b.dataset.count||0) - parseInt(a.dataset.count||0); }});
    heads.forEach(function(h){{ h.style.display='none'; }});
    rows.forEach(function(r){{ list.appendChild(r); }});
  }} else {{
    rows.sort(function(a,b){{ return (a.dataset.name||'').localeCompare(b.dataset.name||''); }});
    heads.forEach(function(h){{ h.style.display=''; }});
    // re-interleave letter heads before their first letter
    var placed = {{}};
    rows.forEach(function(r){{
      var letter = (r.dataset.name||'?')[0].toUpperCase();
      if (!placed[letter]) {{
        var head = document.getElementById('letter-'+letter);
        if (head) list.appendChild(head);
        placed[letter] = true;
      }}
      list.appendChild(r);
    }});
  }}
  document.getElementById('psort-alpha').style.background = mode==='alpha'?'var(--blue)':'var(--card-bg)';
  document.getElementById('psort-alpha').style.color     = mode==='alpha'?'#fff':'var(--text)';
  document.getElementById('psort-alpha').style.border    = mode==='alpha'?'none':'1px solid var(--border)';
  document.getElementById('psort-freq').style.background = mode==='freq'?'var(--blue)':'var(--card-bg)';
  document.getElementById('psort-freq').style.color      = mode==='freq'?'#fff':'var(--text)';
  document.getElementById('psort-freq').style.border     = mode==='freq'?'none':'1px solid var(--border)';
  document.getElementById('person-letter-nav').style.display = mode==='freq'?'none':'flex';
}}
</script>"""
    return page_shell("Person Index", content, depth=1)


# =====================================================================
# LOCATION INDEX PAGE  (Feature 4)
# =====================================================================
def build_location_index(issues):
    """Alphabetically sorted, filterable list of all unique locations."""
    loc_issues = defaultdict(list)
    loc_meta = {}
    for iss in issues:
        for loc in iss.get("entities", {}).get("locations", []):
            name_en = loc.get("name_en", "")
            if not name_en:
                continue
            loc_meta[name_en] = {
                "name_uk": loc.get("name_uk", ""),
                "lat": loc.get("lat"),
                "lon": loc.get("lon"),
            }
            loc_issues[name_en].append({
                "issue_id": iss.get("issue_id",""),
                "date": iss.get("date",""),
                "issue_number": iss.get("issue_number",""),
            })

    by_letter = defaultdict(list)
    for name in sorted(loc_issues.keys(), key=lambda x: x.upper()):
        letter = name[0].upper() if name else "?"
        by_letter[letter].append(name)

    letter_nav = "".join(
        f'<a href="#loc-letter-{l}" style="font-size:12px;padding:2px 6px;border-radius:3px;'
        f'background:var(--blue-lt);color:var(--blue);text-decoration:none">{l}</a> '
        for l in sorted(by_letter.keys())
    )

    rows_html = ""
    for letter in sorted(by_letter.keys()):
        rows_html += (f'<h2 class="loc-letter-head" id="loc-letter-{letter}" '
                      f'style="font-size:14px;font-weight:600;'
                      f'color:var(--muted);border-bottom:1px solid var(--border);'
                      f'padding-bottom:.3rem;margin:1.2rem 0 .5rem">{letter}</h2>')
        for name in by_letter[letter]:
            issue_list = loc_issues[name]
            meta = loc_meta.get(name, {})
            name_uk = meta.get("name_uk","")
            lat = meta.get("lat")
            lon = meta.get("lon")
            count = len(issue_list)
            coord_badge = ""
            if lat and lon:
                coord_badge = (f'<span style="font-size:10px;padding:1px 6px;border-radius:10px;'
                               f'background:var(--bg);border:1px solid var(--border);'
                               f'color:var(--muted);font-family:monospace">'
                               f'{lat:.2f}, {lon:.2f}</span>')
            links = " ".join(
                f'<a href="../issues/{i["issue_id"]}/" style="font-size:11px;padding:2px 7px;'
                f'border-radius:3px;background:var(--blue-lt);color:var(--blue);'
                f'text-decoration:none">{i["date"]} No.{i["issue_number"]}</a>'
                for i in issue_list[:10]
            )
            rows_html += (
                f'<div class="loc-row" data-name="{name.lower()}" data-count="{count}" '
                f'style="padding:.5rem .2rem;border-bottom:1px solid var(--border);display:flex;'
                f'align-items:baseline;gap:.6rem;flex-wrap:wrap">'
                f'<span style="font-weight:500;font-size:13px;min-width:180px">{name}</span>'
                f'{"<span style=\'font-size:11px;color:var(--muted)\'>" + name_uk + "</span>" if name_uk and name_uk != name else ""}'
                f'{coord_badge}'
                f'<span style="font-size:11px;color:var(--muted);margin-right:.3rem">'
                f'{count} issue{"s" if count!=1 else ""}</span>'
                f'{links}</div>'
            )

    content = f"""
<div style="max-width:860px;margin:2rem auto;padding:0 1.5rem">
  <h1 data-i18n="location_index_title" style="font-size:20px;font-weight:600;margin-bottom:.3rem">Location Index</h1>
  <p style="font-size:13px;color:var(--muted);margin-bottom:1rem">
    {len(loc_issues)} unique locations across {len(issues)} issues.
  </p>
  <div style="display:flex;align-items:center;gap:.8rem;margin-bottom:1rem;flex-wrap:wrap">
    <input id="loc-filter" type="search" data-i18n="filter_locations" placeholder="Filter locations…"
      oninput="filterLocs(this.value)"
      style="font-size:13px;padding:.45rem .8rem;border:1px solid var(--border);
             border-radius:var(--radius);background:var(--card-bg);color:var(--text);width:100%;max-width:280px">
    <div style="display:flex;gap:.3rem">
      <button id="lsort-alpha" onclick="sortLocs('alpha')"
        style="font-size:12px;padding:4px 12px;border-radius:4px;cursor:pointer;
               background:var(--blue);color:#fff;border:none" data-i18n="sort_alpha">A–Z</button>
      <button id="lsort-freq" onclick="sortLocs('freq')"
        style="font-size:12px;padding:4px 12px;border-radius:4px;cursor:pointer;
               background:var(--card-bg);color:var(--text);border:1px solid var(--border)"
        data-i18n="sort_freq">Most mentions</button>
    </div>
  </div>
  <div id="loc-letter-nav" style="display:flex;flex-wrap:wrap;gap:.3rem;margin-bottom:1.2rem">{letter_nav}</div>
  <div id="loc-list">{rows_html}</div>
</div>
<script>
function filterLocs(q) {{
  q = q.toLowerCase();
  document.querySelectorAll('.loc-row').forEach(function(row) {{
    var name = row.dataset.name || '';
    row.style.display = (!q || name.includes(q)) ? '' : 'none';
  }});
}}
function sortLocs(mode) {{
  var list = document.getElementById('loc-list');
  var heads = list.querySelectorAll('.loc-letter-head');
  var rows = Array.from(list.querySelectorAll('.loc-row'));
  if (mode === 'freq') {{
    rows.sort(function(a,b){{ return parseInt(b.dataset.count||0) - parseInt(a.dataset.count||0); }});
    heads.forEach(function(h){{ h.style.display='none'; }});
    rows.forEach(function(r){{ list.appendChild(r); }});
  }} else {{
    rows.sort(function(a,b){{ return (a.dataset.name||'').localeCompare(b.dataset.name||''); }});
    heads.forEach(function(h){{ h.style.display=''; }});
    var placed = {{}};
    rows.forEach(function(r){{
      var letter = (r.dataset.name||'?')[0].toUpperCase();
      if (!placed[letter]) {{
        var head = document.getElementById('loc-letter-'+letter);
        if (head) list.appendChild(head);
        placed[letter] = true;
      }}
      list.appendChild(r);
    }});
  }}
  document.getElementById('lsort-alpha').style.background = mode==='alpha'?'var(--blue)':'var(--card-bg)';
  document.getElementById('lsort-alpha').style.color     = mode==='alpha'?'#fff':'var(--text)';
  document.getElementById('lsort-alpha').style.border    = mode==='alpha'?'none':'1px solid var(--border)';
  document.getElementById('lsort-freq').style.background = mode==='freq'?'var(--blue)':'var(--card-bg)';
  document.getElementById('lsort-freq').style.color      = mode==='freq'?'#fff':'var(--text)';
  document.getElementById('lsort-freq').style.border     = mode==='freq'?'none':'1px solid var(--border)';
  document.getElementById('loc-letter-nav').style.display = mode==='freq'?'none':'flex';
}}
</script>"""
    return page_shell("Location Index", content, depth=1)


# =====================================================================
# RSS / ATOM FEED  (Feature 5)
# =====================================================================
def build_rss_feed(issues):
    """Generate Atom 1.0 feed for all issues."""
    import xml.etree.ElementTree as ET
    from datetime import datetime

    site_url = "https://hochheim.github.io/Khliborob/"

    feed_lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<feed xmlns="http://www.w3.org/2005/Atom">',
        f'  <title>Khliborob Digital Archive</title>',
        f'  <link href="{site_url}feed.xml" rel="self"/>',
        f'  <link href="{site_url}"/>',
        f'  <id>{site_url}</id>',
        f'  <updated>{datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}</updated>',
        f'  <author><name>Khliborob Digital Archive</name></author>',
    ]

    def esc(s):
        return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    sorted_issues = sorted(
        [i for i in issues if i.get("date")],
        key=lambda x: x.get("date",""), reverse=True
    )

    for iss in sorted_issues[:50]:
        issue_id = iss.get("issue_id","")
        issue_url = f"{site_url}issues/{issue_id}/"
        title = f"Khliborob No. {iss.get('issue_number','')} — {iss.get('date','')}"
        date_str = iss.get("date","1970-01-01")
        # Try to make an ISO date
        try:
            parts = date_str.split("-")
            if len(parts) == 3:
                updated = f"{date_str}T00:00:00Z"
            elif len(parts) == 2:
                updated = f"{date_str}-01T00:00:00Z"
            else:
                updated = f"{date_str}-01-01T00:00:00Z"
        except Exception:
            updated = "1970-01-01T00:00:00Z"

        abstract = iss.get("translations",{}).get("abstract_en","")
        if not abstract:
            all_text = " ".join(
                p.get("transcript_en","") or "" for p in iss.get("pages",[])
            )
            abstract = all_text[:200] + ("…" if len(all_text) > 200 else "")

        feed_lines += [
            "  <entry>",
            f"    <id>{esc(issue_url)}</id>",
            f"    <title>{esc(title)}</title>",
            f"    <link href=\"{esc(issue_url)}\"/>",
            f"    <updated>{updated}</updated>",
            f"    <summary>{esc(abstract)}</summary>",
            "  </entry>",
        ]

    feed_lines.append("</feed>")
    return "\n".join(feed_lines)


# =====================================================================
# REVIEW PAGE  (password-protected, for SUBRAS/student reviewers)
# =====================================================================
def build_review_page(issues):
    """
    Password-protected page listing all unresolved flagged tokens.
    Reviewers submit corrections via GitHub Actions workflow_dispatch.
    Password is SHA-256 hashed client-side and compared to stored hash.
    The GitHub token embedded here has ONLY workflow_dispatch scope on
    this one repo — it cannot read code, delete branches, or do anything
    else destructive.
    """
    import json as _json, hashlib as _hashlib

    REPO_OWNER  = "Hochheim"
    REPO_NAME   = "Khliborob"
    WORKFLOW_ID = "apply_correction.yml"

    # Collect all unresolved tokens across all issues/pages
    all_tokens = []
    for iss in issues:
        for page in iss.get("pages", []):
            for tok in page.get("low_confidence_tokens", []):
                if tok.get("resolved"):
                    continue
                all_tokens.append({
                    "issue_id":    iss.get("issue_id", ""),
                    "issue_label": f'{iss.get("date","")} No.{iss.get("issue_number","")}',
                    "page_id":     page.get("page_id", ""),
                    "page_number": page.get("page_number", ""),
                    "word":        tok.get("original_word", ""),
                    "context":     tok.get("context", ""),
                    "reason":      tok.get("reason_flagged", ""),
                    "location":    tok.get("visual_location_descriptor", ""),
                })

    tokens_json = _json.dumps(all_tokens, ensure_ascii=False)

    # Password hash — SHA-256 of "khliborob-review-2024"
    # Change this string to change the password; recompute the hash below.
    # Python: import hashlib; hashlib.sha256(b"your-password").hexdigest()
    REVIEW_PASSWORD = "khliborob-review-2024"
    PASSWORD_HASH   = _hashlib.sha256(REVIEW_PASSWORD.encode()).hexdigest()

    content = f"""
<div id="review-lock" style="max-width:400px;margin:5rem auto;padding:2rem;
  background:var(--card-bg);border:1px solid var(--border);border-radius:var(--radius);text-align:center">
  <h1 style="font-size:18px;font-weight:600;margin-bottom:.5rem">Transcript Review</h1>
  <p style="font-size:13px;color:var(--muted);margin-bottom:1.5rem">
    Enter the reviewer password to access flagged tokens.
  </p>
  <input id="pw-input" type="password" placeholder="Password"
    style="width:100%;font-size:14px;padding:.5rem .8rem;border:1px solid var(--border);
           border-radius:var(--radius);background:var(--bg);color:var(--text);margin-bottom:.8rem">
  <button onclick="checkPassword()"
    style="width:100%;font-size:14px;padding:.55rem;border-radius:var(--radius);
           background:var(--blue);color:#fff;border:none;cursor:pointer;font-weight:500">
    Enter
  </button>
  <p id="pw-error" style="font-size:12px;color:#ef4444;margin-top:.5rem;display:none">
    Incorrect password.
  </p>
</div>

<div id="review-app" style="display:none;max-width:900px;margin:2rem auto;padding:0 1.5rem">
  <div style="display:flex;align-items:baseline;gap:1rem;margin-bottom:1.5rem;flex-wrap:wrap">
    <h1 style="font-size:20px;font-weight:600">Transcript Review</h1>
    <span id="token-counter" style="font-size:13px;color:var(--muted)"></span>
  </div>

  <div id="reviewer-info" style="margin-bottom:1.5rem;padding:1rem;background:var(--card-bg);
    border:1px solid var(--border);border-radius:var(--radius)">
    <label style="font-size:13px;font-weight:500;display:block;margin-bottom:.4rem">Your name</label>
    <input id="reviewer-name" type="text" placeholder="e.g. Maria Silva"
      style="font-size:13px;padding:.4rem .7rem;border:1px solid var(--border);border-radius:4px;
             background:var(--bg);color:var(--text);width:100%;max-width:300px">
  </div>

  <div id="token-list"></div>

  <p id="all-done" style="display:none;text-align:center;font-size:14px;
    color:var(--muted);padding:3rem">
    ✅ All flagged tokens have been reviewed. Thank you!
  </p>
</div>

<script>
const PASSWORD_HASH = "{PASSWORD_HASH}";
const TOKENS = {tokens_json};
const REPO_OWNER  = "{REPO_OWNER}";
const REPO_NAME   = "{REPO_NAME}";
const WORKFLOW_ID = "{WORKFLOW_ID}";

// GitHub fine-grained PAT — workflow_dispatch only on this repo
// Replace with a real token after creating it in GitHub Settings → Developer settings
// → Fine-grained tokens → New token → Repository: Khliborob → Permissions: Actions (write)
const GH_TOKEN = "REPLACE_WITH_GITHUB_ACTIONS_WRITE_TOKEN";

async function sha256(str) {{
  const buf = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(str));
  return Array.from(new Uint8Array(buf)).map(b => b.toString(16).padStart(2,"0")).join("");
}}

async function checkPassword() {{
  const pw = document.getElementById("pw-input").value;
  const hash = await sha256(pw);
  if (hash === PASSWORD_HASH) {{
    document.getElementById("review-lock").style.display = "none";
    document.getElementById("review-app").style.display  = "block";
    renderTokens();
  }} else {{
    document.getElementById("pw-error").style.display = "block";
  }}
}}
document.getElementById("pw-input").addEventListener("keydown", e => {{
  if (e.key === "Enter") checkPassword();
}});

function renderTokens() {{
  const pending = TOKENS.filter(t => !localStorage.getItem("reviewed_" + t.page_id + "_" + t.word));
  document.getElementById("token-counter").textContent =
    pending.length + " token" + (pending.length !== 1 ? "s" : "") + " awaiting review";
  const list = document.getElementById("token-list");
  list.innerHTML = "";
  if (pending.length === 0) {{
    document.getElementById("all-done").style.display = "block";
    return;
  }}
  pending.forEach((tok, i) => {{
    const card = document.createElement("div");
    card.style.cssText = "margin-bottom:1.2rem;padding:1rem;background:var(--card-bg);" +
      "border:1px solid var(--border);border-radius:var(--radius)";
    const ctx = tok.context.replace(
      new RegExp('(?<!\\\\w)' + tok.word.replace(/[.*+?^${{}}()|[\\]\\\\]/g,'\\\\$&') + '(?!\\\\w)', 'i'),
      '<mark style="background:#fef3c7;color:#92400e;border-bottom:2px solid #f59e0b;padding:0 2px">$&</mark>'
    );
    card.innerHTML = `
      <div style="display:flex;align-items:baseline;gap:.6rem;flex-wrap:wrap;margin-bottom:.5rem">
        <span style="font-size:11px;padding:2px 7px;border-radius:3px;background:var(--blue-lt);color:var(--blue)">
          ${{tok.issue_label}}</span>
        <span style="font-size:11px;color:var(--muted)">Page ${{tok.page_number}}</span>
        <span style="font-size:11px;color:var(--muted)">${{tok.location}}</span>
      </div>
      <p style="font-size:13px;margin-bottom:.4rem;line-height:1.6">${{ctx}}</p>
      <p style="font-size:11px;color:var(--muted);margin-bottom:.8rem">
        ⚠ <em>${{tok.reason}}</em></p>
      <div style="display:flex;align-items:center;gap:.6rem;flex-wrap:wrap">
        <input id="corr-${{i}}" type="text" value="${{tok.word}}"
          style="font-size:13px;padding:.35rem .7rem;border:1px solid var(--border);
                 border-radius:4px;background:var(--bg);color:var(--text);min-width:180px">
        <button onclick="submitCorrection(${{i}}, this)"
          data-issue="${{tok.issue_id}}" data-page="${{tok.page_id}}" data-word="${{tok.word}}"
          style="font-size:12px;padding:5px 14px;border-radius:4px;background:var(--blue);
                 color:#fff;border:none;cursor:pointer">Submit</button>
        <button onclick="skipToken(${{i}}, '${{tok.page_id}}', '${{tok.word}}')"
          style="font-size:12px;padding:5px 10px;border-radius:4px;background:var(--card-bg);
                 color:var(--muted);border:1px solid var(--border);cursor:pointer">Skip</button>
      </div>
      <p id="status-${{i}}" style="font-size:12px;margin-top:.5rem;display:none"></p>
    `;
    list.appendChild(card);
  }});
}}

async function submitCorrection(i, btn) {{
  const reviewerName = document.getElementById("reviewer-name").value.trim();
  if (!reviewerName) {{
    alert("Please enter your name before submitting.");
    return;
  }}
  const corrected = document.getElementById("corr-" + i).value.trim();
  if (!corrected) return;
  btn.disabled = true;
  btn.textContent = "Submitting…";
  const status = document.getElementById("status-" + i);
  status.style.display = "block";
  status.style.color = "var(--muted)";
  status.textContent = "Sending to archive…";
  try {{
    const resp = await fetch(
      `https://api.github.com/repos/${{REPO_OWNER}}/${{REPO_NAME}}/actions/workflows/${{WORKFLOW_ID}}/dispatches`,
      {{
        method: "POST",
        headers: {{
          "Authorization": "Bearer " + GH_TOKEN,
          "Accept": "application/vnd.github+json",
          "Content-Type": "application/json"
        }},
        body: JSON.stringify({{
          ref: "source",
          inputs: {{
            issue_id:       btn.dataset.issue,
            page_id:        btn.dataset.page,
            original_word:  btn.dataset.word,
            corrected_word: corrected,
            reviewer_name:  reviewerName
          }}
        }})
      }}
    );
    if (resp.status === 204) {{
      status.style.color = "#16a34a";
      status.textContent = "✅ Correction submitted. The archive will update in ~3 minutes.";
      localStorage.setItem("reviewed_" + btn.dataset.page + "_" + btn.dataset.word, "1");
      setTimeout(renderTokens, 1500);
    }} else {{
      const err = await resp.json().catch(() => ({{}}));
      status.style.color = "#ef4444";
      status.textContent = "Error " + resp.status + ": " + (err.message || "unknown error");
      btn.disabled = false;
      btn.textContent = "Submit";
    }}
  }} catch(e) {{
    status.style.color = "#ef4444";
    status.textContent = "Network error. Please try again.";
    btn.disabled = false;
    btn.textContent = "Submit";
  }}
}}

function skipToken(i, pageId, word) {{
  localStorage.setItem("reviewed_" + pageId + "_" + word, "1");
  renderTokens();
}}
</script>"""
    return page_shell("Transcript Review", content, depth=1)


# =====================================================================
# MAIN BUILD FUNCTION
# =====================================================================
def build():
    print("🌐 Building static site...")

    # Setup directories
    os.makedirs(ASSETS_DIR, exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "issues"), exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "browse"), exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "search"), exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "gpu-documents"), exist_ok=True)
    os.makedirs(os.path.join(SITE_DIR, "about"), exist_ok=True)

    # Write assets
    with open(os.path.join(ASSETS_DIR, "main.css"), "w", encoding="utf-8") as f:
        f.write(MAIN_CSS)
    with open(os.path.join(ASSETS_DIR, "lang.js"), "w", encoding="utf-8") as f:
        f.write(LANG_JS)

    # Load data
    issues = load_all_issues()
    total_pages = sum(len(i.get("pages", [])) for i in issues)
    print(f"   Found {len(issues)} issues, {total_pages} total pages")

    # Homepage
    with open(os.path.join(SITE_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_homepage(issues, total_pages))
    print("   ✅ index.html")

    # Browse index
    with open(os.path.join(SITE_DIR, "browse", "index.html"), "w", encoding="utf-8") as f:
        f.write(build_browse_page(issues))
    print("   ✅ browse/index.html")

    # Per-year browse pages
    by_year = defaultdict(list)
    for iss in issues:
        by_year[iss.get("year", "unknown")].append(iss)
    for year, year_issues in by_year.items():
        year_dir = os.path.join(SITE_DIR, "browse", str(year))
        os.makedirs(year_dir, exist_ok=True)
        with open(os.path.join(year_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_year_page(year, year_issues, all_issues=issues))
    print(f"   ✅ {len(by_year)} year pages")

    # Per-issue pages
    for iss in issues:
        issue_dir = os.path.join(SITE_DIR, "issues", iss["issue_id"])
        os.makedirs(issue_dir, exist_ok=True)
        with open(os.path.join(issue_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(build_issue_page(iss, issues))
    print(f"   ✅ {len(issues)} issue pages")

    # GPU documents page
    with open(os.path.join(SITE_DIR, "gpu-documents", "index.html"),
              "w", encoding="utf-8") as f:
        f.write(build_gpu_page(issues))
    print("   ✅ gpu-documents/index.html")

    # Search page
    with open(os.path.join(SITE_DIR, "search", "index.html"), "w", encoding="utf-8") as f:
        f.write(build_search_page())
    print("   ✅ search/index.html")

    # About page
    with open(os.path.join(SITE_DIR, "about", "index.html"), "w", encoding="utf-8") as f:
        f.write(build_about_page())
    print("   ✅ about/index.html")

    # Chat / Research Agent page
    os.makedirs(os.path.join(SITE_DIR, "chat"), exist_ok=True)
    with open(os.path.join(SITE_DIR, "chat", "index.html"), "w", encoding="utf-8") as f:
        f.write(build_chat_page())
    print("   ✅ chat/index.html")

    # Person index
    persons_dir = os.path.join(SITE_DIR, "persons")
    os.makedirs(persons_dir, exist_ok=True)
    with open(os.path.join(persons_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_person_index(issues))
    print("   ✅ persons/index.html")

    # Location index
    locations_dir = os.path.join(SITE_DIR, "locations")
    os.makedirs(locations_dir, exist_ok=True)
    with open(os.path.join(locations_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_location_index(issues))
    print("   ✅ locations/index.html")

    # RSS/Atom feed
    with open(os.path.join(SITE_DIR, "feed.xml"), "w", encoding="utf-8") as f:
        f.write(build_rss_feed(issues))
    print("   ✅ feed.xml")

    # Review page (password-protected, not linked from nav)
    review_dir = os.path.join(SITE_DIR, "review")
    os.makedirs(review_dir, exist_ok=True)
    with open(os.path.join(review_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(build_review_page(issues))
    print("   ✅ review/index.html")

    # Aggregated maps and graphs from local data
    build_aggregated_views(issues)

    print(f"\n✅ Site built at: {SITE_DIR}")

    # Auto-run Pagefind to build search index
    import subprocess
    print("\n🔍 Building Pagefind search index...")
    try:
        result = subprocess.run(
            ["pagefind", "--site", SITE_DIR, "--output-subdir", "pagefind"],
            capture_output=True, text=True, timeout=120
        )
        if result.returncode == 0:
            print("   ✅ Search index built successfully")
        else:
            print(f"   ⚠️  Pagefind warning: {result.stderr[:200]}")
            print("   Run manually: pagefind --site output_site")
    except FileNotFoundError:
        print("   ⚠️  Pagefind not installed. Run:")
        print("      pip install pagefind")
        print("      Then: pagefind --site output_site")
    except subprocess.TimeoutExpired:
        print("   ⚠️  Pagefind timed out. Run manually: pagefind --site output_site")

    deploy_to_github()


def deploy_to_github():
    import subprocess
    from datetime import datetime

    GITHUB_USER = "Hochheim"
    GITHUB_REPO = "Khliborob"

    def run(cmd, check=True):
        return subprocess.run(cmd, cwd=SITE_DIR, capture_output=True, text=True, check=check)

    print("\n🚀 Deploying to GitHub Pages...")

    run(["git", "add", "-A"])

    commit_msg = f"Deploy {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    commit_result = run(["git", "commit", "-m", commit_msg], check=False)
    if "nothing to commit" in commit_result.stdout + commit_result.stderr:
        print("   ℹ️  Nothing changed since last deploy.")
        return

    push_result = run(["git", "push", "origin", "main"], check=False)
    if push_result.returncode == 0:
        print(f"   ✅ Deployed → https://{GITHUB_USER}.github.io/{GITHUB_REPO}/")
    else:
        print(f"   ⚠️  Push failed:\n{push_result.stderr}")
        print("   Try: gh auth login")


if __name__ == "__main__":
    build()
