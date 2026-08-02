
function toggleIpfs(id){
  var e=document.getElementById(id);
  if(e) e.style.display=e.style.display==='none'?'block':'none';
}
const STRINGS = {"uk": {"nav_browse": "Переглянути", "nav_search": "Пошук", "nav_gpu": "Документи ГПУ", "nav_about": "Про проєкт", "nav_maps": "Мапи та графи", "nav_chat": "Дослідницький агент", "hero_subtitle": "Цифровий архів газети Хлібороб / O Lavrador — органу української діаспори у Бразилії (1924 — дотепер)", "search_placeholder": "Пошук по всіх сторінках — напр. Голодомор, Стамбул, 1932", "search_btn": "Шукати", "gpu_banner": "Архівне відкриття: розсекречені документи ГПУ СРСР свідчать, що газета Хлібороб читалася радянськими спецслужбами під час Голодомору (1932) і цитувалася у зведеннях, складених для японської дипломатії.", "gpu_link": "Переглянути документи", "browse_title": "Переглянути випуски", "issues_label": "випуски", "pages_label": "сторінки", "gpu_doc_label": "Документ ГПУ", "transcript_uk": "Оригінальний текст (українська)", "transcript_pt": "Tradução (Português Brasileiro)", "transcript_en": "Переклад (англійська)", "locations": "Місця", "persons": "Особи", "blockchain": "Блокчейн", "ipfs": "IPFS", "stat_issues": "оцифрованих випусків", "stat_pages": "сторінок з можливістю пошуку", "stat_from": "перший номер", "person_index_title": "Покажчик осіб", "location_index_title": "Покажчик місць", "filter_persons": "Фільтр осіб…", "filter_locations": "Фільтр місць…", "sort_alpha": "А–Я", "sort_freq": "Найчастіші", "footer_credit": "Зберігається SUBRAS (Sociedade Ucraniana do Brasil). Цифровий архів створено в рамках дослідницького проєкту Університету Мюнстера."}, "en": {"nav_browse": "Browse", "nav_search": "Search", "nav_gpu": "GPU Documents", "nav_about": "About", "nav_maps": "Maps & Graphs", "nav_chat": "Research Agent", "hero_subtitle": "Digital archive of Khliborob / O Lavrador — the Ukrainian diaspora newspaper in Brazil (1924–present)", "search_placeholder": "Search all pages — e.g. Holodomor, Istanbul, 1932", "search_btn": "Search", "gpu_banner": "Historical discovery: declassified Soviet GPU documents reveal that Khliborob was monitored by Soviet intelligence during the Holodomor (1932) and cited in reports compiled for Japanese diplomatic services.", "gpu_link": "View documents", "browse_title": "Browse issues", "issues_label": "issues", "pages_label": "pages", "gpu_doc_label": "GPU document", "transcript_uk": "Original text (Ukrainian)", "transcript_pt": "Translation (Brazilian Portuguese)", "transcript_en": "Translation (English)", "locations": "Locations", "persons": "Persons", "blockchain": "Blockchain", "ipfs": "IPFS", "stat_issues": "digitized issues", "stat_pages": "searchable pages", "stat_from": "first issue", "person_index_title": "Person Index", "location_index_title": "Location Index", "filter_persons": "Filter persons…", "filter_locations": "Filter locations…", "sort_alpha": "A–Z", "sort_freq": "Most mentions", "footer_credit": "Preserved by SUBRAS (Sociedade Ucraniana do Brasil). Digital archive created as part of a research project at the University of Münster."}, "pt": {"nav_browse": "Edições", "nav_search": "Pesquisa", "nav_gpu": "Documentos GPU", "nav_about": "Sobre", "nav_maps": "Mapas e Grafos", "nav_chat": "Agente de Pesquisa", "hero_subtitle": "Arquivo digital do jornal Khliborob / O Lavrador — órgão da diáspora ucraniana no Brasil (1924–presente)", "search_placeholder": "Pesquisar em todas as páginas — ex: Holodomor, Istambul, 1932", "search_btn": "Pesquisar", "gpu_banner": "Descoberta histórica: documentos desclassificados do GPU soviético revelam que o Khliborob foi lido por serviços de inteligência durante o Holodomor (1932) e citado em relatórios preparados para a diplomacia japonesa.", "gpu_link": "Ver documentos", "browse_title": "Navegar por edições", "issues_label": "edições", "pages_label": "páginas", "gpu_doc_label": "Documento GPU", "transcript_uk": "Texto original (ucraniano)", "transcript_pt": "Tradução (Português Brasileiro)", "transcript_en": "Tradução (inglês)", "locations": "Locais", "persons": "Pessoas", "blockchain": "Blockchain", "ipfs": "IPFS", "stat_issues": "edições digitalizadas", "stat_pages": "páginas pesquisáveis", "stat_from": "primeiro número", "person_index_title": "Índice de Pessoas", "location_index_title": "Índice de Lugares", "filter_persons": "Filtrar pessoas…", "filter_locations": "Filtrar locais…", "sort_alpha": "A–Z", "sort_freq": "Mais citados", "footer_credit": "Preservado pela SUBRAS (Sociedade Ucraniana do Brasil). Arquivo digital criado no âmbito de um projeto de pesquisa da Universidade de Münster."}};
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
