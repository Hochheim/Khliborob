
function toggleIpfs(id){
  var e=document.getElementById(id);
  if(e) e.style.display=e.style.display==='none'?'block':'none';
}
const STRINGS = {"uk": {"nav_browse": "ÐŸÐµÑ€ÐµÐ³Ð»ÑÐ½ÑƒÑ‚Ð¸", "nav_search": "ÐŸÐ¾ÑˆÑƒÐº", "nav_gpu": "Ð”Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚Ð¸ Ð“ÐŸÐ£", "nav_about": "ÐŸÑ€Ð¾ Ð¿Ñ€Ð¾Ñ”ÐºÑ‚", "nav_maps": "ÐœÐ°Ð¿Ð¸ Ñ‚Ð° Ð³Ñ€Ð°Ñ„Ð¸", "nav_chat": "Ð”Ð¾ÑÐ»Ñ–Ð´Ð½Ð¸Ñ†ÑŒÐºÐ¸Ð¹ Ð°Ð³ÐµÐ½Ñ‚", "hero_subtitle": "Ð¦Ð¸Ñ„Ñ€Ð¾Ð²Ð¸Ð¹ Ð°Ñ€Ñ…Ñ–Ð² Ð³Ð°Ð·ÐµÑ‚Ð¸ Ð¥Ð»Ñ–Ð±Ð¾Ñ€Ð¾Ð± / O Lavrador â€” Ð¾Ñ€Ð³Ð°Ð½Ñƒ ÑƒÐºÑ€Ð°Ñ—Ð½ÑÑŒÐºÐ¾Ñ— Ð´Ñ–Ð°ÑÐ¿Ð¾Ñ€Ð¸ Ñƒ Ð‘Ñ€Ð°Ð·Ð¸Ð»Ñ–Ñ— (1924 â€” Ð´Ð¾Ñ‚ÐµÐ¿ÐµÑ€)", "search_placeholder": "ÐŸÐ¾ÑˆÑƒÐº Ð¿Ð¾ Ð²ÑÑ–Ñ… ÑÑ‚Ð¾Ñ€Ñ–Ð½ÐºÐ°Ñ… â€” Ð½Ð°Ð¿Ñ€. Ð“Ð¾Ð»Ð¾Ð´Ð¾Ð¼Ð¾Ñ€, Ð¡Ñ‚Ð°Ð¼Ð±ÑƒÐ», 1932", "search_btn": "Ð¨ÑƒÐºÐ°Ñ‚Ð¸", "gpu_banner": "ÐÑ€Ñ…Ñ–Ð²Ð½Ðµ Ð²Ñ–Ð´ÐºÑ€Ð¸Ñ‚Ñ‚Ñ: Ñ€Ð¾Ð·ÑÐµÐºÑ€ÐµÑ‡ÐµÐ½Ñ– Ð´Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚Ð¸ Ð“ÐŸÐ£ Ð¡Ð Ð¡Ð  ÑÐ²Ñ–Ð´Ñ‡Ð°Ñ‚ÑŒ, Ñ‰Ð¾ Ð³Ð°Ð·ÐµÑ‚Ð° Ð¥Ð»Ñ–Ð±Ð¾Ñ€Ð¾Ð± Ñ‡Ð¸Ñ‚Ð°Ð»Ð°ÑÑ Ñ€Ð°Ð´ÑÐ½ÑÑŒÐºÐ¸Ð¼Ð¸ ÑÐ¿ÐµÑ†ÑÐ»ÑƒÐ¶Ð±Ð°Ð¼Ð¸ Ð¿Ñ–Ð´ Ñ‡Ð°Ñ Ð“Ð¾Ð»Ð¾Ð´Ð¾Ð¼Ð¾Ñ€Ñƒ (1932) Ñ– Ñ†Ð¸Ñ‚ÑƒÐ²Ð°Ð»Ð°ÑÑ Ñƒ Ð·Ð²ÐµÐ´ÐµÐ½Ð½ÑÑ…, ÑÐºÐ»Ð°Ð´ÐµÐ½Ð¸Ñ… Ð´Ð»Ñ ÑÐ¿Ð¾Ð½ÑÑŒÐºÐ¾Ñ— Ð´Ð¸Ð¿Ð»Ð¾Ð¼Ð°Ñ‚Ñ–Ñ—.", "gpu_link": "ÐŸÐµÑ€ÐµÐ³Ð»ÑÐ½ÑƒÑ‚Ð¸ Ð´Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚Ð¸", "browse_title": "ÐŸÐµÑ€ÐµÐ³Ð»ÑÐ½ÑƒÑ‚Ð¸ Ð²Ð¸Ð¿ÑƒÑÐºÐ¸", "issues_label": "Ð²Ð¸Ð¿ÑƒÑÐºÐ¸", "pages_label": "ÑÑ‚Ð¾Ñ€Ñ–Ð½ÐºÐ¸", "gpu_doc_label": "Ð”Ð¾ÐºÑƒÐ¼ÐµÐ½Ñ‚ Ð“ÐŸÐ£", "transcript_uk": "ÐžÑ€Ð¸Ð³Ñ–Ð½Ð°Ð»ÑŒÐ½Ð¸Ð¹ Ñ‚ÐµÐºÑÑ‚ (ÑƒÐºÑ€Ð°Ñ—Ð½ÑÑŒÐºÐ°)", "transcript_pt": "TraduÃ§Ã£o (PortuguÃªs Brasileiro)", "transcript_en": "ÐŸÐµÑ€ÐµÐºÐ»Ð°Ð´ (Ð°Ð½Ð³Ð»Ñ–Ð¹ÑÑŒÐºÐ°)", "locations": "ÐœÑ–ÑÑ†Ñ", "persons": "ÐžÑÐ¾Ð±Ð¸", "blockchain": "Ð‘Ð»Ð¾ÐºÑ‡ÐµÐ¹Ð½", "ipfs": "IPFS", "stat_issues": "Ð¾Ñ†Ð¸Ñ„Ñ€Ð¾Ð²Ð°Ð½Ð¸Ñ… Ð²Ð¸Ð¿ÑƒÑÐºÑ–Ð²", "stat_pages": "ÑÑ‚Ð¾Ñ€Ñ–Ð½Ð¾Ðº Ð· Ð¼Ð¾Ð¶Ð»Ð¸Ð²Ñ–ÑÑ‚ÑŽ Ð¿Ð¾ÑˆÑƒÐºÑƒ", "stat_from": "Ð¿ÐµÑ€ÑˆÐ¸Ð¹ Ð½Ð¾Ð¼ÐµÑ€", "person_index_title": "ÐŸÐ¾ÐºÐ°Ð¶Ñ‡Ð¸Ðº Ð¾ÑÑ–Ð±", "location_index_title": "ÐŸÐ¾ÐºÐ°Ð¶Ñ‡Ð¸Ðº Ð¼Ñ–ÑÑ†ÑŒ", "filter_persons": "Ð¤Ñ–Ð»ÑŒÑ‚Ñ€ Ð¾ÑÑ–Ð±â€¦", "filter_locations": "Ð¤Ñ–Ð»ÑŒÑ‚Ñ€ Ð¼Ñ–ÑÑ†ÑŒâ€¦", "sort_alpha": "Ðâ€“Ð¯", "sort_freq": "ÐÐ°Ð¹Ñ‡Ð°ÑÑ‚Ñ–ÑˆÑ–", "footer_credit": "Ð—Ð±ÐµÑ€Ñ–Ð³Ð°Ñ”Ñ‚ÑŒÑÑ SUBRAS (Sociedade Ucraniana do Brasil). Ð¦Ð¸Ñ„Ñ€Ð¾Ð²Ð¸Ð¹ Ð°Ñ€Ñ…Ñ–Ð² ÑÑ‚Ð²Ð¾Ñ€ÐµÐ½Ð¾ Ð² Ñ€Ð°Ð¼ÐºÐ°Ñ… Ð´Ð¾ÑÐ»Ñ–Ð´Ð½Ð¸Ñ†ÑŒÐºÐ¾Ð³Ð¾ Ð¿Ñ€Ð¾Ñ”ÐºÑ‚Ñƒ Ð£Ð½Ñ–Ð²ÐµÑ€ÑÐ¸Ñ‚ÐµÑ‚Ñƒ ÐœÑŽÐ½ÑÑ‚ÐµÑ€Ð°."}, "en": {"nav_browse": "Browse", "nav_search": "Search", "nav_gpu": "GPU Documents", "nav_about": "About", "nav_maps": "Maps & Graphs", "nav_chat": "Research Agent", "hero_subtitle": "Digital archive of Khliborob / O Lavrador â€” the Ukrainian diaspora newspaper in Brazil (1924â€“present)", "search_placeholder": "Search all pages â€” e.g. Holodomor, Istanbul, 1932", "search_btn": "Search", "gpu_banner": "Historical discovery: declassified Soviet GPU documents reveal that Khliborob was monitored by Soviet intelligence during the Holodomor (1932) and cited in reports compiled for Japanese diplomatic services.", "gpu_link": "View documents", "browse_title": "Browse issues", "issues_label": "issues", "pages_label": "pages", "gpu_doc_label": "GPU document", "transcript_uk": "Original text (Ukrainian)", "transcript_pt": "Translation (Brazilian Portuguese)", "transcript_en": "Translation (English)", "locations": "Locations", "persons": "Persons", "blockchain": "Blockchain", "ipfs": "IPFS", "stat_issues": "digitized issues", "stat_pages": "searchable pages", "stat_from": "first issue", "person_index_title": "Person Index", "location_index_title": "Location Index", "filter_persons": "Filter personsâ€¦", "filter_locations": "Filter locationsâ€¦", "sort_alpha": "Aâ€“Z", "sort_freq": "Most mentions", "footer_credit": "Preserved by SUBRAS (Sociedade Ucraniana do Brasil). Digital archive created as part of a research project at the University of MÃ¼nster."}, "pt": {"nav_browse": "EdiÃ§Ãµes", "nav_search": "Pesquisa", "nav_gpu": "Documentos GPU", "nav_about": "Sobre", "nav_maps": "Mapas e Grafos", "nav_chat": "Agente de Pesquisa", "hero_subtitle": "Arquivo digital do jornal Khliborob / O Lavrador â€” Ã³rgÃ£o da diÃ¡spora ucraniana no Brasil (1924â€“presente)", "search_placeholder": "Pesquisar em todas as pÃ¡ginas â€” ex: Holodomor, Istambul, 1932", "search_btn": "Pesquisar", "gpu_banner": "Descoberta histÃ³rica: documentos desclassificados do GPU soviÃ©tico revelam que o Khliborob foi lido por serviÃ§os de inteligÃªncia durante o Holodomor (1932) e citado em relatÃ³rios preparados para a diplomacia japonesa.", "gpu_link": "Ver documentos", "browse_title": "Navegar por ediÃ§Ãµes", "issues_label": "ediÃ§Ãµes", "pages_label": "pÃ¡ginas", "gpu_doc_label": "Documento GPU", "transcript_uk": "Texto original (ucraniano)", "transcript_pt": "TraduÃ§Ã£o (PortuguÃªs Brasileiro)", "transcript_en": "TraduÃ§Ã£o (inglÃªs)", "locations": "Locais", "persons": "Pessoas", "blockchain": "Blockchain", "ipfs": "IPFS", "stat_issues": "ediÃ§Ãµes digitalizadas", "stat_pages": "pÃ¡ginas pesquisÃ¡veis", "stat_from": "primeiro nÃºmero", "person_index_title": "Ãndice de Pessoas", "location_index_title": "Ãndice de Lugares", "filter_persons": "Filtrar pessoasâ€¦", "filter_locations": "Filtrar locaisâ€¦", "sort_alpha": "Aâ€“Z", "sort_freq": "Mais citados", "footer_credit": "Preservado pela SUBRAS (Sociedade Ucraniana do Brasil). Arquivo digital criado no Ã¢mbito de um projeto de pesquisa da Universidade de MÃ¼nster."}};
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
