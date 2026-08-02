# =====================================================================
# 📄 xml_generators.py — ALTO, METS, IIIF & NETWORK GRAPH GENERATORS
# All XML / JSON archival format builders live here.
# =====================================================================

import os
import re
import json
import unicodedata
from datetime import datetime, timezone
import xml.etree.ElementTree as ET
from xml.dom import minidom

from config import METS_NS, MODS_NS, ALTO_NS, XLINK_NS, CURRENT_VERSION


# =====================================================================
# ALTO XML
# =====================================================================
def generate_alto_xml(vlm_data, text_flow, output_filepath):
    """Generates a schema-compliant ALTO XML layout structure representation."""
    ET.register_namespace('', ALTO_NS)
    meta = vlm_data["page_metadata"]
    root = ET.Element(f"{{{ALTO_NS}}}alto", {"SCHEMAVERSION": "4.2"})

    description = ET.SubElement(root, f"{{{ALTO_NS}}}Description")
    measurement_unit = ET.SubElement(description, f"{{{ALTO_NS}}}MeasurementUnit")
    measurement_unit.text = "pixel"

    source_img_info = ET.SubElement(description, f"{{{ALTO_NS}}}sourceImageInformation")
    filename_el = ET.SubElement(source_img_info, f"{{{ALTO_NS}}}fileName")
    filename_el.text = f"{meta.get('page_id', 'unknown')}.jpg"

    layout = ET.SubElement(root, f"{{{ALTO_NS}}}Layout")
    page = ET.SubElement(layout, f"{{{ALTO_NS}}}Page", {
        "ID": "P0",
        "PHYSICAL_IMG_NR": "1",
        "WIDTH":  str(meta.get("width_pixels", 2400)),
        "HEIGHT": str(meta.get("height_pixels", 3600))
    })

    print_space = ET.SubElement(page, f"{{{ALTO_NS}}}PrintSpace", {
        "HPOS": "50", "VPOS": "50",
        "WIDTH":  str(meta.get("width_pixels",  2400) - 100),
        "HEIGHT": str(meta.get("height_pixels", 3600) - 100)
    })

    text_block = ET.SubElement(print_space, f"{{{ALTO_NS}}}TextBlock", {
        "ID": "TXT_BLOCK_01",
        "HPOS": "100", "VPOS": "1400",
        "WIDTH":  str(meta.get("width_pixels", 2400) - 200),
        "HEIGHT": "1800"
    })

    for idx, sentence in enumerate(text_flow.split("\n"), start=1):
        line = ET.SubElement(text_block, f"{{{ALTO_NS}}}TextLine", {
            "ID": f"LINE_{idx:02d}",
            "HPOS": "120",
            "VPOS": str(1450 + (idx * 60)),
            "WIDTH": str(meta.get("width_pixels", 2400) - 240),
            "HEIGHT": "50"
        })
        for w_idx, word in enumerate(sentence.split()):
            ET.SubElement(line, f"{{{ALTO_NS}}}String", {
                "ID": f"STR_{idx}_{w_idx}",
                "CONTENT": word,
                "HPOS": str(120 + (w_idx * 110)),
                "VPOS": str(1450 + (idx * 60)),
                "WIDTH": "100", "HEIGHT": "45"
            })
            if w_idx < len(sentence.split()) - 1:
                ET.SubElement(line, f"{{{ALTO_NS}}}SP")

    for ill in vlm_data.get("illustrations", []):
        coords = ill["coordinates"]
        illustration_node = ET.SubElement(print_space, f"{{{ALTO_NS}}}Illustration", {
            "ID":     ill["id"],
            "TYPE":   ill["type"],
            "HPOS":   str(coords["hpos"]),
            "VPOS":   str(coords["vpos"]),
            "WIDTH":  str(coords["width"]),
            "HEIGHT": str(coords["height"])
        })
        desc_node = ET.SubElement(illustration_node, f"{{{ALTO_NS}}}Description")
        desc_node.text = (
            f"[Type: {ill['type']}] Location: {ill['location_description']}\n"
            f"English Summary: {ill['visual_resume_en']}\n"
            f"Ukrainian Summary: {ill['visual_resume_uk']}"
        )

    raw_xml_string = ET.tostring(root, 'utf-8')
    parsed_dom = minidom.parseString(raw_xml_string)
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(parsed_dom.toprettyxml(indent="  "))
    print(f" -> ALTO XML compiled at: {output_filepath}")


# =====================================================================
# TEI-XML (Text Encoding Initiative)
# The gold standard for scholarly digital editions. Marks up the
# transcript with structured persName/placeName tags linked to
# Wikidata identifiers, alongside full bibliographic metadata.
# =====================================================================
TEI_NS = "http://www.tei-c.org/ns/1.0"


def _tei_mark_entities(text: str, persons: list, locations: list) -> str:
    """
    Wraps occurrences of person and location names in the text with
    TEI <persName>/<placeName> tags carrying Wikidata @ref links.
    Longer names are replaced first to avoid partial-match collisions.
    """
    import xml.sax.saxutils as saxutils

    # Escape XML special characters in the base text first
    escaped = saxutils.escape(text)

    replacements = []
    for p in persons:
        if isinstance(p, dict):
            name = p.get("name_uk") or p.get("name_en", "")
            qid  = p.get("wikidata_id", "")
        else:
            name, qid = str(p), ""
        if name:
            replacements.append((name, "persName", qid))

    for loc in locations:
        name = loc.get("name_uk") or loc.get("name_en", "")
        qid  = loc.get("wikidata_id", "")
        if name:
            replacements.append((name, "placeName", qid))

    # Longest names first so multi-word names aren't broken by shorter substrings
    replacements.sort(key=lambda r: len(r[0]), reverse=True)

    for name, tag, qid in replacements:
        name_escaped = saxutils.escape(name)
        if not name_escaped or name_escaped not in escaped:
            continue
        ref_attr = f' ref="https://www.wikidata.org/entity/{qid}"' if qid else ""
        replacement = f'<{tag}{ref_attr}>{name_escaped}</{tag}>'
        # Replace only the first occurrence to keep markup readable and avoid
        # re-tagging already-tagged spans
        escaped = escaped.replace(name_escaped, replacement, 1)

    return escaped


def generate_tei_xml(vlm_data: dict, text_flow: str, text_flow_en: str,
                     scan_cid: str, tx_hash: str, output_filepath: str) -> str:
    """
    Generates a TEI P5-compliant scholarly digital edition of the page.
    Includes full bibliographic header, encoding description, and a
    body with persons/locations marked up as <persName>/<placeName>
    carrying Wikidata references where available.
    """
    meta      = vlm_data["page_metadata"]
    entities  = vlm_data.get("entities", {})
    persons   = entities.get("persons", [])
    locations = entities.get("locations", [])
    abstract_uk = vlm_data.get("translations", {}).get("abstract_uk", "")
    abstract_en = vlm_data.get("translations", {}).get("abstract_en", "")

    page_id      = meta.get("page_id", "unknown")
    newspaper_uk = meta.get("newspaper_name_uk", "")
    newspaper_en = meta.get("newspaper_name_en", "")
    pub_date     = meta.get("publication_date", "")
    issue_number = meta.get("issue_number", "")

    marked_uk = _tei_mark_entities(text_flow, persons, locations) if text_flow else ""
    marked_en = _tei_mark_entities(text_flow_en, persons, locations) if text_flow_en else ""

    paragraphs_uk = "".join(
        f"        <p>{line}</p>\n" for line in marked_uk.split("\n") if line.strip()
    )
    paragraphs_en = "".join(
        f"        <p>{line}</p>\n" for line in marked_en.split("\n") if line.strip()
    )

    import xml.sax.saxutils as saxutils
    abstract_uk_esc = saxutils.escape(abstract_uk)
    abstract_en_esc = saxutils.escape(abstract_en)

    tei = f"""<?xml version="1.0" encoding="UTF-8"?>
<TEI xmlns="{TEI_NS}">
  <teiHeader>
    <fileDesc>
      <titleStmt>
        <title type="main" xml:lang="uk">{saxutils.escape(newspaper_uk)} — {page_id}</title>
        <title type="main" xml:lang="en">{saxutils.escape(newspaper_en)} — {page_id}</title>
        <respStmt>
          <resp>Digitization and transcription</resp>
          <name>Ukrainian Diaspora Press Digital Archive Pipeline</name>
        </respStmt>
      </titleStmt>
      <publicationStmt>
        <publisher>Ukrainian Diaspora Press Digital Archive</publisher>
        <date when="{pub_date}">{pub_date}</date>
        <idno type="IPFS">ipfs://{scan_cid}</idno>
        <idno type="blockchain-tx">{tx_hash}</idno>
        <idno type="page-id">{page_id}</idno>
        <availability status="free">
          <p>Freely available under open access for non-commercial scholarly use.</p>
        </availability>
      </publicationStmt>
      <sourceDesc>
        <bibl>
          <title xml:lang="uk">{saxutils.escape(newspaper_uk)}</title>
          <title xml:lang="en">{saxutils.escape(newspaper_en)}</title>
          <date when="{pub_date}">{pub_date}</date>
          <idno type="issue">{saxutils.escape(issue_number)}</idno>
        </bibl>
      </sourceDesc>
    </fileDesc>
    <encodingDesc>
      <p>Transcribed using Google Gemini 2.5 Flash (vision-language model) from a
      digitized newspaper scan. Named entities (persons, locations) automatically
      extracted and linked to Wikidata identifiers where available. Manual
      correction by native-speaker volunteers is recorded in the version history.</p>
    </encodingDesc>
    <profileDesc>
      <langUsage>
        <language ident="uk">Ukrainian</language>
        <language ident="en">English (translation)</language>
      </langUsage>
      <textClass>
        <keywords>
          <list>
{"".join(f'            <item xml:lang="uk">{saxutils.escape(k)}</item>{chr(10)}' for k in vlm_data.get("translations", {}).get("keywords_uk", []))}
          </list>
        </keywords>
      </textClass>
    </profileDesc>
  </teiHeader>
  <text>
    <front>
      <div type="abstract" xml:lang="uk">
        <p>{abstract_uk_esc}</p>
      </div>
      <div type="abstract" xml:lang="en">
        <p>{abstract_en_esc}</p>
      </div>
    </front>
    <body>
      <div type="page" xml:lang="uk" n="{page_id}">
{paragraphs_uk}      </div>
      <div type="translation" xml:lang="en" n="{page_id}">
{paragraphs_en}      </div>
    </body>
  </text>
</TEI>"""

    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(tei)
    print(f" -> TEI-XML written at: {output_filepath}")
    return output_filepath


# =====================================================================
# CITATION EXPORT (BibTeX, RIS, Zotero RDF)
# Lets researchers download ready-to-use citations for reference
# managers directly from the archive.
# =====================================================================
def generate_citation_formats(page_id: str, vlm_data: dict, omeka_url: str,
                              scan_cid: str, tx_hash: str, output_dir: str) -> dict:
    """
    Produces BibTeX (.bib) and RIS (.ris) citation files for a page.
    Returns a dict of {format: filepath}.
    """
    meta      = vlm_data["page_metadata"]
    newspaper_uk = meta.get("newspaper_name_uk", "")
    newspaper_en = meta.get("newspaper_name_en", "")
    pub_date     = meta.get("publication_date", "")
    issue_number = meta.get("issue_number", "")

    year, month, day = (pub_date.split("-") + ["", "", ""])[:3]

    # --- BibTeX ---
    bibtex_key = page_id.replace(" ", "_")
    bibtex = f"""@article{{{bibtex_key},
  title        = {{{newspaper_en} --- {page_id}}},
  journal      = {{{newspaper_en} [{newspaper_uk}]}},
  year         = {{{year}}},
  month        = {{{month}}},
  day          = {{{day}}},
  note         = {{Issue {issue_number}. IPFS: ipfs://{scan_cid}. Blockchain tx: {tx_hash}.}},
  url          = {{{omeka_url}}},
  howpublished = {{Ukrainian Diaspora Press Digital Archive}}
}}
"""
    bib_path = os.path.join(output_dir, f"{page_id}.bib")
    with open(bib_path, "w", encoding="utf-8") as f:
        f.write(bibtex)

    # --- RIS (used by EndNote, Mendeley, Zotero) ---
    ris = (
        "TY  - NEWS\n"
        f"TI  - {newspaper_en} --- {page_id}\n"
        f"JO  - {newspaper_en} [{newspaper_uk}]\n"
        f"PY  - {year}/{month}/{day}\n"
        f"IS  - {issue_number}\n"
        f"UR  - {omeka_url}\n"
        f"N1  - IPFS: ipfs://{scan_cid}; Blockchain tx: {tx_hash}\n"
        "PB  - Ukrainian Diaspora Press Digital Archive\n"
        "ER  - \n"
    )
    ris_path = os.path.join(output_dir, f"{page_id}.ris")
    with open(ris_path, "w", encoding="utf-8") as f:
        f.write(ris)

    print(f" -> Citations written: {bib_path}, {ris_path}")
    return {"bibtex": bib_path, "ris": ris_path}


# =====================================================================
# METS XML — DFG-Viewer METS Application Profile compliant
#
# Conforms to the structure used by the Deutsches Zeitungsportal
# (Kitodo.Presentation / DFG-Viewer), so this file can be loaded
# directly into the public DFG-Viewer at https://dfg-viewer.de/ for
# verification. Adds:
#   - dmdSec with proper mods:mods descriptive metadata
#   - fileGrp USE values DFG-Viewer recognises (DEFAULT, MAX,
#     FULLTEXT) alongside the project's own custom groups, which
#     DFG-Viewer simply ignores rather than rejecting
#   - logical + physical structMap with structLink, matching the
#     newspaper -> issue -> page hierarchy DFG-Viewer expects
# =====================================================================
def generate_mets_xml(vlm_data, scan_cid, trans_cid, alto_cid,
                      iiif_cid, net_cid, output_filepath):
    """
    Generates a DFG-Viewer-compliant METS file while preserving every
    custom fileGrp (transcript, IIIF, network graph) the rest of the
    pipeline relies on. No existing output is removed — only the
    structure required for DFG-Viewer/Kitodo compatibility is added.
    """
    ET.register_namespace('',     METS_NS)
    ET.register_namespace('xlink', XLINK_NS)
    ET.register_namespace('mods', MODS_NS)

    meta         = vlm_data["page_metadata"]
    page_id      = meta.get("page_id", "unknown")
    newspaper_uk = meta.get("newspaper_name_uk", "")
    newspaper_en = meta.get("newspaper_name_en", "")
    pub_date     = meta.get("publication_date", "")
    issue_number = meta.get("issue_number", "")
    width_px     = meta.get("width_pixels",  2400)
    height_px    = meta.get("height_pixels", 3600)

    root = ET.Element(f"{{{METS_NS}}}mets", {
        "OBJID": page_id,
        "TYPE":  "newspaper",
        "LABEL": f"{newspaper_en} — {page_id}",
    })

    # ── metsHdr ──────────────────────────────────────────────────────
    iso_time_str = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    header = ET.SubElement(root, f"{{{METS_NS}}}metsHdr", {"CREATEDATE": iso_time_str})
    agent  = ET.SubElement(header, f"{{{METS_NS}}}agent", {"ROLE": "CREATOR", "TYPE": "ORGANIZATION"})
    agent_name = ET.SubElement(agent, f"{{{METS_NS}}}name")
    agent_name.text = "Ukrainian Diaspora Press Digital Archive Pipeline"

    # ── dmdSec: proper MODS descriptive metadata (DFG-Viewer requirement) ──
    dmd_sec   = ET.SubElement(root, f"{{{METS_NS}}}dmdSec", {"ID": "DMD_PAGE"})
    md_wrap   = ET.SubElement(dmd_sec, f"{{{METS_NS}}}mdWrap", {"MDTYPE": "MODS"})
    xml_data  = ET.SubElement(md_wrap, f"{{{METS_NS}}}xmlData")
    mods_root = ET.SubElement(xml_data, f"{{{MODS_NS}}}mods")

    title_info_uk = ET.SubElement(mods_root, f"{{{MODS_NS}}}titleInfo", {"lang": "uk"})
    ET.SubElement(title_info_uk, f"{{{MODS_NS}}}title").text = f"{newspaper_uk} — {page_id}"
    title_info_en = ET.SubElement(mods_root, f"{{{MODS_NS}}}titleInfo", {"lang": "en"})
    ET.SubElement(title_info_en, f"{{{MODS_NS}}}title").text = f"{newspaper_en} — {page_id}"

    genre = ET.SubElement(mods_root, f"{{{MODS_NS}}}genre", {"authority": "marcgt"})
    genre.text = "newspaper"

    origin_info = ET.SubElement(mods_root, f"{{{MODS_NS}}}originInfo")
    date_issued = ET.SubElement(origin_info, f"{{{MODS_NS}}}dateIssued", {"encoding": "iso8601"})
    date_issued.text = pub_date

    lang_el = ET.SubElement(mods_root, f"{{{MODS_NS}}}language")
    ET.SubElement(lang_el, f"{{{MODS_NS}}}languageTerm",
                  {"type": "code", "authority": "iso639-2b"}).text = "ukr"

    part_el = ET.SubElement(mods_root, f"{{{MODS_NS}}}part")
    detail_issue = ET.SubElement(part_el, f"{{{MODS_NS}}}detail", {"type": "issue"})
    ET.SubElement(detail_issue, f"{{{MODS_NS}}}number").text = issue_number

    phys_desc = ET.SubElement(mods_root, f"{{{MODS_NS}}}physicalDescription")
    ET.SubElement(phys_desc, f"{{{MODS_NS}}}extent").text = f"{width_px}x{height_px}px"

    identifier = ET.SubElement(mods_root, f"{{{MODS_NS}}}identifier", {"type": "local"})
    identifier.text = page_id

    # ── fileSec ──────────────────────────────────────────────────────
    # DFG-Viewer-recognised groups (DEFAULT image, MAX master, FULLTEXT ALTO)
    # PLUS every custom fileGrp the rest of the pipeline already produces.
    # Unrecognised fileGrp names are simply ignored by DFG-Viewer, so
    # nothing already built is lost by adding the standard ones.
    file_sec = ET.SubElement(root, f"{{{METS_NS}}}fileSec")
    mappings = [
        ("DEFAULT",    "image/jpeg",       scan_cid,  "FILE_DEFAULT_01"),
        ("MAX",        "image/jpeg",       scan_cid,  "FILE_MAX_01"),
        ("FULLTEXT",   "text/xml",         alto_cid,  "FILE_FULLTEXT_01"),
        ("TRANSCRIPT", "text/plain",        trans_cid, "FILE_TRANSCRIPT_01"),
        ("ALTO",       "text/xml",          alto_cid,  "FILE_ALTO_01"),
        ("IIIF",       "application/json",  iiif_cid,  "FILE_IIIF_01"),
        ("NETWORK",    "application/json",  net_cid,   "FILE_NET_01"),
    ]

    # DFG-Viewer and other external tools can only resolve http(s) URLs,
    # not the ipfs:// scheme. Use a public gateway for the href so the
    # file is actually fetchable, while the raw CID remains the permanent
    # content-addressed identifier (recoverable from the URL itself).
    ipfs_gateway = "https://gateway.pinata.cloud/ipfs"
    for use_val, mime, cid, file_id in mappings:
        group     = ET.SubElement(file_sec, f"{{{METS_NS}}}fileGrp", {"USE": use_val})
        file_node = ET.SubElement(group,    f"{{{METS_NS}}}file",    {"ID": file_id, "MIMETYPE": mime})
        ET.SubElement(file_node, f"{{{METS_NS}}}FLocat", {
            "LOCTYPE": "URL",
            f"{{{XLINK_NS}}}href": f"{ipfs_gateway}/{cid}"
        })

    # ── structMap TYPE="LOGICAL" — newspaper > issue > page ─────────
    logical_map = ET.SubElement(root, f"{{{METS_NS}}}structMap", {"TYPE": "LOGICAL"})
    log_newspaper = ET.SubElement(logical_map, f"{{{METS_NS}}}div", {
        "ID": "LOG_NEWSPAPER", "TYPE": "newspaper",
        "LABEL": newspaper_en or "Newspaper",
    })
    log_issue = ET.SubElement(log_newspaper, f"{{{METS_NS}}}div", {
        "ID": "LOG_ISSUE", "TYPE": "newspaper_issue",
        "LABEL": f"{newspaper_en} {issue_number} ({pub_date})",
        "DMDID": "DMD_PAGE",
    })
    log_page = ET.SubElement(log_issue, f"{{{METS_NS}}}div", {
        "ID": "LOG_PAGE", "TYPE": "newspaper_page",
        "LABEL": f"Page 1",
    })

    # ── structMap TYPE="PHYSICAL" — same hierarchy, links to files ──
    physical_map = ET.SubElement(root, f"{{{METS_NS}}}structMap", {"TYPE": "PHYSICAL"})
    phys_root = ET.SubElement(physical_map, f"{{{METS_NS}}}div", {
        "ID": "PHYS_ROOT", "TYPE": "physSequence",
    })
    phys_page = ET.SubElement(phys_root, f"{{{METS_NS}}}div", {
        "ID": "PHYS_PAGE", "TYPE": "page", "ORDER": "1",
        "ORDERLABEL": "1", "LABEL": "Page 1",
    })
    for _, _, _, file_id in mappings:
        ET.SubElement(phys_page, f"{{{METS_NS}}}fptr", {"FILEID": file_id})

    # ── structLink — connects logical and physical structures ───────
    struct_link = ET.SubElement(root, f"{{{METS_NS}}}structLink")
    ET.SubElement(struct_link, f"{{{METS_NS}}}smLink", {
        f"{{{XLINK_NS}}}from": "LOG_PAGE",
        f"{{{XLINK_NS}}}to":   "PHYS_PAGE",
    })

    raw_xml_string = ET.tostring(root, 'utf-8')
    parsed_dom = minidom.parseString(raw_xml_string)
    with open(output_filepath, "w", encoding="utf-8") as f:
        f.write(parsed_dom.toprettyxml(indent="  "))
    print(f" -> METS XML (DFG-Viewer profile) written at: {output_filepath}")


# =====================================================================
# IIIF MANIFEST
# =====================================================================
def generate_iiif_manifest(page_id, scan_cid, width, height, output_dir):
    """Compiles a fully compliant IIIF Presentation v3.0 Manifest JSON structure."""
    manifest_url = f"https://gateway.pinata.cloud/ipfs/item_{page_id}_manifest.json"
    image_url    = f"https://gateway.pinata.cloud/ipfs/{scan_cid}"

    manifest = {
        "@context": "http://iiif.io/api/presentation/3/context.json",
        "id": manifest_url,
        "type": "Manifest",
        "label": {
            "uk": [f"Новий Шлях — Сторінка {page_id}"],
            "en": [f"New Path — Page {page_id}"]
        },
        "behavior": ["paged"],
        "items": [{
            "id":     f"https://gateway.pinata.cloud/ipfs/{page_id}/canvas/p1",
            "type":   "Canvas",
            "width":  width,
            "height": height,
            "items": [{
                "id":   f"https://gateway.pinata.cloud/ipfs/{page_id}/page/p1/1",
                "type": "AnnotationPage",
                "items": [{
                    "id":         f"https://gateway.pinata.cloud/ipfs/{page_id}/annotation/p1-image",
                    "type":       "Annotation",
                    "motivation": "painting",
                    "target":     f"https://gateway.pinata.cloud/ipfs/{page_id}/canvas/p1",
                    "body": {
                        "id":     image_url,
                        "type":   "Image",
                        "format": "image/jpeg",
                        "width":  width,
                        "height": height
                    }
                }]
            }]
        }]
    }

    output_path = os.path.join(output_dir, f"{page_id}_iiif_manifest.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=4, ensure_ascii=False)
    return output_path


# =====================================================================
# TRANSCRIPT HTML WRAPPER
# Produces a self-contained HTML file that displays the English
# translation and directs readers to download the Ukrainian original.
# This file is what gets pinned to IPFS as the transcript CID,
# so it renders correctly in any browser regardless of encoding.
# =====================================================================
def generate_transcript_html(page_id, text_en, text_uk_cid, meta, output_dir):
    """
    Builds a readable HTML page containing the English translation.
    Links to the raw Ukrainian .txt via its IPFS CID for download.
    """
    newspaper = meta.get("newspaper_name_en", "")
    newspaper_uk = meta.get("newspaper_name_uk", "")
    date      = meta.get("publication_date", "")
    issue     = meta.get("issue_number", "")

    uk_download = (
        f'<p class="dl-note">🇺🇦 <strong>Ukrainian original transcript:</strong> '
        f'The source-language text is stored separately in UTF-8 plain text. '
        f'<a href="https://gateway.pinata.cloud/ipfs/{text_uk_cid}" download>Download Ukrainian transcript ↓</a>'
        f'</p>'
    ) if text_uk_cid else ""

    # Render each paragraph as a <p> block
    paragraphs = "".join(
        f"<p>{line}</p>" for line in text_en.split("\n") if line.strip()
    ) if text_en.strip() else "<p><em>English translation not available for this page.</em></p>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Transcript — {page_id}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <style>
    body {{ max-width: 740px; margin: 0 auto; padding: 24px 20px 60px;
           font-family: Georgia, serif; font-size: 16px; line-height: 1.8;
           color: #1a1a1a; background: #faf9f5; }}
    header {{ border-bottom: 2px solid #2c4a7c; padding-bottom: 12px; margin-bottom: 24px; }}
    header h1 {{ font-size: 1.15rem; color: #2c4a7c; margin: 0 0 4px; }}
    header p  {{ margin: 0; font-size: 0.85rem; color: #666; }}
    .dl-note  {{ background: #e8edf5; border-left: 4px solid #2c4a7c;
                 padding: 10px 14px; border-radius: 0 6px 6px 0;
                 font-family: sans-serif; font-size: 0.85rem; margin-bottom: 28px; }}
    .dl-note a {{ color: #2c4a7c; }}
    article p {{ margin: 0 0 1em; text-align: justify; }}
    footer {{ margin-top: 40px; border-top: 1px solid #ddd; padding-top: 12px;
              font-family: sans-serif; font-size: 0.75rem; color: #999; }}
  </style>
</head>
<body>
  <header>
    <h1>{newspaper} [{newspaper_uk}] — English Transcript</h1>
    <p>Page: {page_id} &nbsp;·&nbsp; {date} &nbsp;·&nbsp; {issue}</p>
  </header>
  {uk_download}
  <article>
    {paragraphs}
  </article>
  <footer>
    Digitized and translated by the Bukovina Digital Archive Pipeline.
    Source page: {page_id}. Publication date: {date}.
  </footer>
</body>
</html>"""

    output_path = os.path.join(output_dir, f"{page_id}_transcript.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Transcript HTML written to: {output_path}")
    return output_path


# =====================================================================
# NETWORK GRAPH EDGE LIST
# =====================================================================
def generate_network_edge_list(page_id, entities, output_dir):
    """Generates a structured relational Graph Edge List for network modelling analyses."""
    edges = []
    source_node = f"Page_{page_id}"

    for person in entities.get("persons", []):
        name = (person.get("name_uk") or person.get("name_en", "")) if isinstance(person, dict) else str(person)
        if name:
            edges.append({"source": source_node, "target": name,
                          "type": "MENTIONS_PERSON", "weight": 1.0})
    for loc in entities.get("locations", []):
        edges.append({"source": source_node, "target": loc.get("name_en", "Unknown"),
                      "type": "MENTIONS_LOCATION", "weight": 1.0})

    output_path = os.path.join(output_dir, f"{page_id}_network_graph.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump({"edges": edges}, f, indent=4, ensure_ascii=False)
    print(f" -> DH Network Analysis Edge-List written to: {output_path}")
    return output_path


# =====================================================================
# 🗺️ PER-PAGE LEAFLET MAP (Feature #2)
# Generates a self-contained HTML file with an interactive Leaflet.js
# map highlighting all locations extracted from this page.
# =====================================================================
def generate_location_map(page_id, entities, meta, output_dir):
    """
    Builds a standalone HTML Leaflet map for all locations on this page.
    Locations with valid coordinates appear as map markers.
    Locations without coordinates are listed in a sidebar so they are
    never silently discarded.
    """
    locations     = entities.get("locations", [])
    markers_js    = ""
    bounds_coords = []
    ungeocoded    = []

    for loc in locations:
        lat       = loc.get("lat", 0.0)
        lon       = loc.get("lon", 0.0)
        name_en   = loc.get("name_en", "Unknown")
        name_uk   = loc.get("name_uk", "")
        is_region = loc.get("is_region", False)
        label     = f"{name_en} ({name_uk})" if name_uk else name_en

        if lat == 0.0 and lon == 0.0:
            ungeocoded.append(label)
            continue

        label_safe = label.replace("'", "\\'")
        polygon_json = loc.get("polygon_json")
        is_waterway  = loc.get("is_waterway", False) or _is_waterway_name(name_en, loc.get("name_uk", ""))

        if is_waterway and polygon_json:
            popup_safe = f"💧 {label_safe}<br><small><em>River / waterway course shown.</em></small>"
            markers_js += (
                f"    L.geoJSON({polygon_json}, {{"
                f"style: {{color:'#2980b9',fillColor:'#3498db',fillOpacity:0.2,weight:3}}"
                f"}}).addTo(map).bindPopup('{popup_safe}');\n"
            )
        elif is_waterway:
            popup_safe = f"💧 {label_safe}"
            markers_js += (
                f"    L.circleMarker([{lat}, {lon}], "
                f"{{radius:8, color:'#2980b9', fillColor:'#3498db', fillOpacity:0.8}})"
                f".addTo(map).bindPopup('{popup_safe}');\n"
            )
        elif is_region and polygon_json:
            popup_safe = f"{label_safe}<br><small><em>Region boundary shown.</em></small>"
            markers_js += (
                f"    L.geoJSON({polygon_json}, {{"
                f"style: {{color:'#e67e22',fillColor:'#f39c12',fillOpacity:0.15,weight:2}}"
                f"}}).addTo(map).bindPopup('{popup_safe}');\n"
            )
        elif is_region:
            popup_safe = (
                f"⚠️ {label_safe}<br>"
                f"<small><em>Large region — pin marks approximate centroid.</em></small>"
            )
            markers_js += (
                f"    L.circleMarker([{lat}, {lon}], "
                f"{{radius:10, color:'#e67e22', fillColor:'#f39c12', fillOpacity:0.8}})"
                f".addTo(map).bindPopup('{popup_safe}');\n"
            )
        else:
            popup_safe = label_safe
            markers_js += (
                f"    L.marker([{lat}, {lon}]).addTo(map)"
                f".bindPopup('{popup_safe}');\n"
            )
        bounds_coords.append([lat, lon])

    if bounds_coords:
        fit_bounds = f"map.fitBounds({json.dumps(bounds_coords)}, {{padding: [40, 40]}});"
    else:
        fit_bounds = "map.setView([48.0, 31.0], 5);"

    newspaper = meta.get("newspaper_name_en", "")
    date      = meta.get("publication_date", "")
    issue     = meta.get("issue_number", "")

    # Sidebar listing locations that have no geocoordinates
    if ungeocoded:
        sidebar_items = "".join(
            f"<li style='padding:4px 0;border-bottom:1px solid #444'>{loc}</li>"
            for loc in ungeocoded
        )
        sidebar = (
            f"<div id='sidebar' style='position:fixed;top:60px;right:0;width:220px;"
            f"height:calc(100vh - 60px);background:#2c3e50;color:#eee;overflow-y:auto;"
            f"padding:10px;font-size:0.8rem;z-index:1000'>"
            f"<strong>📋 Без координат:</strong><ul style='padding-left:16px;margin:6px 0'>"
            f"{sidebar_items}</ul></div>"
            f"<style>#map {{ margin-right: 220px; }}</style>"
        )
    else:
        sidebar = ""

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>Location Map — {page_id}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    body {{ margin: 0; font-family: sans-serif; }}
    #header {{ background: #2c3e50; color: #fff; padding: 10px 16px; }}
    #header h2 {{ margin: 0; font-size: 1rem; }}
    #header p  {{ margin: 2px 0 0; font-size: 0.8rem; opacity: 0.7; }}
    #map {{ width: 100%; height: calc(100vh - 60px); }}
  </style>
</head>
<body>
  <div id="header">
    <h2>📍 Location Map — {page_id}</h2>
    <p>{newspaper} &nbsp;·&nbsp; {date} &nbsp;·&nbsp; {issue}
       &nbsp;·&nbsp; {len(bounds_coords)} geocoded, {len(ungeocoded)} without coordinates
       &nbsp;·&nbsp; <span style="display:inline-block;width:10px;height:10px;background:#f39c12;border-radius:50%;vertical-align:middle"></span> = large region (approximate)</p>
  </div>
  {sidebar}
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    var map = L.map('map');
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd', maxZoom: 19
    }}).addTo(map);
{markers_js}
    {fit_bounds}
  </script>
</body>
</html>"""

    output_path = os.path.join(output_dir, f"{page_id}_map.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Location map written to: {output_path}")
    return output_path


# =====================================================================
# 🧠 PER-PAGE D3 KNOWLEDGE GRAPH (Feature #3)
# Generates a self-contained HTML file with an interactive D3.js
# force-directed graph built from the network edge list JSON.
# =====================================================================
from geocoder import _is_waterway_name


def _extract_snippet(text: str, name: str, window: int = 180) -> str:
    """
    Returns a short excerpt surrounding the entity name.
    Search order:
    1. Exact full-name match
    2. Case-insensitive full-name match
    3. Surname stem (last word, first 4 chars) — handles Ukrainian declension
       e.g. 'Міхайло Бойтор' → searches 'Бойт', finds 'Бойтора', 'Бойторові'
    4. First-word stem — fallback
    """
    if not text or not name:
        return ""

    lower_text = text.lower()
    lower_name = name.lower()
    idx = -1

    # 1 & 2: full name
    idx = text.find(name)
    if idx < 0:
        idx = lower_text.find(lower_name)

    # 3: surname stem (last word)
    if idx < 0:
        words = name.split()
        if len(words) > 1:
            surname   = words[-1].lower()
            stem_len  = max(3, min(len(surname), 5))
            idx = lower_text.find(surname[:stem_len])

    # 4: first-word stem
    if idx < 0:
        words = name.split()
        first = words[0].lower() if words else ""
        stem_len = max(3, min(len(first), max(4, len(first) // 2)))
        if len(first) >= 3:
            idx = lower_text.find(first[:stem_len])

    if idx < 0:
        return ""

    start   = max(0, idx - window // 2)
    end     = min(len(text), idx + max(len(name), 20) + window // 2)
    snippet = text[start:end].replace("\n", " ").replace('"', "'")
    return ("…" if start > 0 else "") + snippet + ("…" if end < len(text) else "")


def _entity_positions(text, names):
    """Return all character positions where any of the names appear in text."""
    positions = []
    text_lower = text.lower()
    for name in names:
        if not name:
            continue
        name_lower = name.lower()
        start = 0
        while True:
            pos = text_lower.find(name_lower, start)
            if pos == -1:
                break
            positions.append(pos)
            start = pos + 1
    return positions


def generate_knowledge_graph(page_id, entities, meta, output_dir,
                             text_flow="", text_flow_en="", site_base_url=""):
    """
    Per-page entity graph.
    - Only includes entities actually found in this page's transcript text.
    - Edges drawn between entities that appear within 600 chars of each other.
    - Falls back to full bipartite (persons x locations) when proximity yields no edges.
    - Layout: cose force-directed (built into Cytoscape, no CDN dependency).
    """
    combined = (text_flow + " " + text_flow_en).lower()

    nodes = []
    node_positions = {}   # id -> list of char positions in combined text

    for person in entities.get("persons", []):
        if isinstance(person, dict):
            name_uk = person.get("name_uk", "")
            name_en = person.get("name_en", "")
            label   = f"{name_uk} / {name_en}" if name_en else name_uk
            pid     = name_uk or name_en
        else:
            label = pid = str(person)
        if not pid:
            continue
        names = [n for n in [name_uk if isinstance(person, dict) else "", pid] if n]
        positions = _entity_positions(combined, names)
        if combined and not positions:
            continue   # not on this page
        snippet_uk = _extract_snippet(text_flow,    (names[0] if names else pid))
        snippet_en = _extract_snippet(text_flow_en, pid)
        nodes.append({"id": pid, "type": "person", "label": label,
                       "snippet_uk": snippet_uk, "snippet_en": snippet_en,
                       "name_uk": names[0] if names else ""})
        node_positions[pid] = positions

    for loc in entities.get("locations", []):
        name    = loc.get("name_en", "Unknown")
        name_uk = loc.get("name_uk", "")
        names   = [n for n in [name_uk, name] if n]
        positions = _entity_positions(combined, names)
        if combined and not positions:
            continue   # not on this page
        snippet_uk = _extract_snippet(text_flow,    name_uk) or _extract_snippet(text_flow,    name)
        snippet_en = _extract_snippet(text_flow_en, name)
        nodes.append({"id": name, "type": "location", "label": name,
                       "snippet_uk": snippet_uk, "snippet_en": snippet_en,
                       "lat": loc.get("lat", 0.0), "lon": loc.get("lon", 0.0),
                       "name_uk": name_uk})
        node_positions[name] = positions

    # Build entity-entity edges from extracted relations (LLM-provided typed relationships).
    # Fall back to no entity-entity edges if none were extracted.
    links = []
    raw_relations = entities.get("relations", [])
    # Build a lookup of all known entity names so we can validate relation endpoints
    known_ids = {n["id"] for n in nodes}
    known_labels = {n["label"]: n["id"] for n in nodes}
    for rel in raw_relations:
        subj = rel.get("subject", "")
        obj  = rel.get("object", "")
        pred = rel.get("predicate", "CO_OCCURS")
        # Try to match subject/object to known node ids or labels
        src = known_ids and (subj if subj in known_ids else known_labels.get(subj))
        tgt = known_ids and (obj  if obj  in known_ids else known_labels.get(obj))
        if src and tgt and src != tgt:
            links.append({"source": src, "target": tgt, "label": pred,
                          "evidence": rel.get("evidence", "")})

    import re as _re
    newspaper  = meta.get("newspaper_name_en", "")
    date       = meta.get("publication_date", "")
    issue      = meta.get("issue_number", "")

    # Add center page node and hub edges to every entity
    issue_id   = _re.sub(r'_page\d+$', '', page_id)
    page_label = f"{newspaper}\\n{date}\\nNo. {issue}"
    nodes.insert(0, {"id": "__page__", "type": "page", "label": page_label})
    for n in nodes:
        if n["id"] != "__page__":
            links.append({"source": "__page__", "target": n["id"]})
    issue_url  = (f"{site_base_url}issues/{issue_id}/" if site_base_url
                  else f"../../issues/{issue_id}/")
    nodes_json = json.dumps(nodes, ensure_ascii=False)
    links_json = json.dumps(links, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Knowledge Graph — {page_id}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#f5f4f0;font-family:'Segoe UI',system-ui,sans-serif;color:#1a1a1a;
         display:flex;flex-direction:column;height:100vh;overflow:hidden}}
    #topbar{{background:#fff;border-bottom:1px solid #ddd;padding:8px 16px;flex-shrink:0;
             display:flex;align-items:center;gap:12px;flex-wrap:wrap;
             box-shadow:0 1px 4px rgba(0,0,0,.08)}}
    #topbar h2{{font-size:.88rem;font-weight:700;color:#1a1a1a}}
    #topbar .sub{{font-size:.7rem;color:#999}}
    #topbar .issue-link{{font-size:.78rem;color:#2b6cb0;text-decoration:none;
                         border:1px solid #bfdbfe;border-radius:5px;padding:3px 9px;white-space:nowrap}}
    #topbar .issue-link:hover{{background:#eff6ff}}
    #search{{flex:1;min-width:130px;max-width:200px;border:1px solid #ccc;
             border-radius:6px;padding:4px 9px;font-size:.8rem;outline:none}}
    #search:focus{{border-color:#2b6cb0;box-shadow:0 0 0 2px rgba(43,108,176,.15)}}
    #layout{{display:flex;flex:1;overflow:hidden}}
    #cy{{flex:1;background:#f5f4f0}}
    #panel{{width:250px;background:#fff;border-left:1px solid #e0e0e0;padding:14px;
            font-size:.8rem;overflow-y:auto;flex-shrink:0;
            box-shadow:-2px 0 6px rgba(0,0,0,.04)}}
    #panel h3{{font-size:.9rem;font-weight:700;margin-bottom:4px;line-height:1.3}}
    .badge{{display:inline-block;border-radius:99px;padding:2px 10px;margin-bottom:8px;
            font-size:.66rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em}}
    .bp{{background:#dbeafe;color:#1e40af}}
    .bl{{background:#d1fae5;color:#065f46}}
    .field{{margin-bottom:9px}}
    .field b{{display:block;font-size:.65rem;text-transform:uppercase;
              letter-spacing:.06em;color:#bbb;margin-bottom:3px}}
    .field a{{color:#2b6cb0;text-decoration:none;font-size:.78rem}}
    .field a:hover{{text-decoration:underline}}
    .field ul{{list-style:none;padding:0}}
    .field li{{padding:2px 0;border-bottom:1px solid #f0f0f0;font-size:.76rem}}
    .field li:last-child{{border-bottom:none}}
    .snip{{border-left:3px solid #ccc;padding:3px 8px;margin:4px 0;
           font-size:.73rem;font-style:italic;color:#555;background:#fafafa;
           border-radius:0 3px 3px 0;line-height:1.5}}
    .snip.uk{{border-color:#3b82f6}}
    .snip.en{{border-color:#10b981}}
    .hint{{color:#ccc;font-size:.78rem;margin-top:24px;text-align:center;line-height:1.7}}
    #legend{{position:absolute;bottom:10px;left:10px;background:rgba(255,255,255,.93);
             padding:6px 12px;border-radius:8px;font-size:.7rem;color:#555;
             border:1px solid #e0e0e0;display:flex;gap:12px;pointer-events:none}}
    .dot{{display:inline-block;width:9px;height:9px;border-radius:50%;
          margin-right:4px;vertical-align:middle}}
    .dia{{display:inline-block;width:9px;height:9px;background:#10b981;
          margin-right:4px;vertical-align:middle;transform:rotate(45deg)}}
    #fitbtn{{margin-left:auto;background:#f3f4f6;border:1px solid #d1d5db;
             border-radius:5px;padding:3px 10px;font-size:.75rem;cursor:pointer}}
    #fitbtn:hover{{background:#e5e7eb}}
  </style>
</head>
<body>
  <div id="topbar">
    <div>
      <h2>🧠 {newspaper} · {date} · No. {issue}</h2>
      <span class="sub">Nodes = entities on this page · Edges = mentioned near each other · Click for details</span>
    </div>
    <input id="search" type="search" placeholder="Search…" autocomplete="off"/>
    <a class="issue-link" href="{issue_url}" target="_blank">↗ Open issue page</a>
    <button id="fitbtn">⊡ Fit</button>
  </div>
  <div id="layout">
    <div style="position:relative;flex:1;display:flex">
      <div id="cy"></div>
      <div id="legend">
        <span><span class="dot" style="background:#f59e0b"></span>Issue</span>
        <span><span class="dot" style="background:#3b82f6"></span>Person</span>
        <span><span class="dia"></span>Location</span>
        <span style="color:#94a3b8">— typed relation</span>
      </div>
    </div>
    <div id="panel"><p class="hint">Click any node<br>to see details.</p></div>
  </div>

  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
  <script>
  if (window.self !== window.top) {{
    document.body.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                  height:100vh;background:#f5f4f0;font-family:sans-serif;gap:16px;padding:20px;text-align:center">
        <p style="font-size:.9rem;color:#666">The Knowledge Graph needs its own tab to be fully interactive.</p>
        <a href="${{window.location.href}}" target="_blank"
           style="background:#2b6cb0;color:#fff;padding:12px 28px;border-radius:8px;
                  text-decoration:none;font-size:.9rem;font-weight:600">
          🧠 Open Knowledge Graph ↗
        </a>
      </div>`;
  }}

  const RAW = {nodes_json};
  const EDGES = {links_json};
  function nid(x) {{ return typeof x==="object"?x.id:String(x); }}

  // Layout: page hub at centre, persons top, locations bottom.
  // Horizontal spacing is proportional to label length — not equidistant.
  function twoRowPositions() {{
    const persons   = RAW.filter(n => n.type==="person");
    const locations = RAW.filter(n => n.type==="location");
    const W = document.getElementById("cy").clientWidth  || 900;
    const H = document.getElementById("cy").clientHeight || 620;
    const PAD = 70;
    const usableW = W - PAD * 2;
    const pos = {{}};

    // Centre: page hub node
    pos["__page__"] = {{x: W / 2, y: H / 2}};

    function placeRow(list, y, minSpacing) {{
      if (!list.length) return;
      const widths = list.map(n => Math.max(minSpacing, n.label.length * 7 + 70));
      const total  = widths.reduce((s,w) => s+w, 0);
      const scale  = total > usableW ? usableW / total : 1;
      let x = PAD + (usableW - total * scale) / 2 + widths[0] * scale / 2;
      list.forEach((n,i) => {{
        pos[n.id] = {{x, y}};
        x += (widths[i] * scale / 2) + (widths[i+1] ? widths[i+1] * scale / 2 : 0);
      }});
    }}

    // Persons top; locations bottom (1 or 2 rows)
    if (persons.length)   placeRow(persons,   H * 0.14, 160);
    if (locations.length) {{
      if (locations.length <= 8) {{
        placeRow(locations, H * 0.80, 140);
      }} else {{
        const mid  = Math.ceil(locations.length / 2);
        placeRow(locations.slice(0, mid), H * 0.70, 130);
        placeRow(locations.slice(mid),    H * 0.90, 130);
      }}
    }}
    // single-type fallback
    if (!persons.length)   placeRow(locations, H * 0.20, 140);
    if (!locations.length) placeRow(persons,   H * 0.80, 160);

    return pos;
  }}

  const pos = twoRowPositions();

  const cy = cytoscape({{
    container: document.getElementById("cy"),
    elements: [
      ...RAW.map(n => ({{ data:{{
          id:n.id, label:n.label, type:n.type,
          lat:n.lat||0, lon:n.lon||0, name_uk:n.name_uk||"",
          snippet_uk:n.snippet_uk||"", snippet_en:n.snippet_en||""
      }}, position: pos[n.id] || {{x:400,y:300}} }})),
      ...EDGES.map((e,i) => ({{ data:{{ id:"e"+i, source:nid(e.source), target:nid(e.target),
          label:e.label||"", evidence:e.evidence||"" }} }}))
    ],
    style:[
      {{ selector:"node[type='page']", style:{{
        "background-color":"#f59e0b","border-color":"#b45309","border-width":2,
        "width":60,"height":60,"shape":"ellipse",
        "label":"data(label)","color":"#78350f","font-size":11,"font-weight":700,
        "text-valign":"center","text-halign":"center","text-wrap":"wrap","text-max-width":"90px",
        "text-background-color":"rgba(255,255,255,.0)","text-background-opacity":0,
      }} }},
      {{ selector:"node[type='person']", style:{{
        "background-color":"#3b82f6","border-color":"#1d4ed8","border-width":2,
        "width":46,"height":46,
        "label":"data(label)","color":"#1e3a5f","font-size":12,"font-weight":600,
        "text-valign":"bottom","text-halign":"center","text-margin-y":8,
        "text-background-color":"rgba(255,255,255,.85)","text-background-opacity":1,
        "text-background-padding":"2px","text-background-shape":"roundrectangle",
        "text-max-width":"150px","text-wrap":"wrap",
      }} }},
      {{ selector:"node[type='location']", style:{{
        "background-color":"#10b981","border-color":"#047857","border-width":2,
        "width":42,"height":42,"shape":"diamond",
        "label":"data(label)","color":"#064e3b","font-size":12,"font-weight":600,
        "text-valign":"bottom","text-halign":"center","text-margin-y":12,
        "text-background-color":"rgba(255,255,255,.85)","text-background-opacity":1,
        "text-background-padding":"2px","text-background-shape":"roundrectangle",
        "text-max-width":"150px","text-wrap":"wrap",
      }} }},
      {{ selector:"node.dim",  style:{{"opacity":0.15}} }},
      {{ selector:"node.hi",   style:{{"border-color":"#e11d48","border-width":4}} }},
      {{ selector:"edge", style:{{
        "line-color":"#94a3b8","opacity":0.55,"width":2,"curve-style":"bezier",
        "label":"data(label)","font-size":9,"color":"#6b7280",
        "text-background-color":"rgba(255,255,255,.8)","text-background-opacity":1,
        "text-background-padding":"1px","text-rotation":"autorotate",
      }} }},
      {{ selector:"edge.dim",  style:{{"opacity":0.04}} }},
      {{ selector:"edge.hi",   style:{{"line-color":"#e11d48","opacity":1,"width":3}} }},
    ],
    layout:{{ name:"preset" }},
    userZoomingEnabled:true, userPanningEnabled:true, boxSelectionEnabled:false,
  }});
  cy.fit(cy.elements(), 60);

  document.getElementById("fitbtn").onclick = () => cy.fit(cy.elements(), 60);

  document.getElementById("search").addEventListener("input", function(){{
    const q = this.value.trim().toLowerCase();
    if (!q) {{ cy.elements().removeClass("dim hi"); return; }}
    cy.elements().addClass("dim");
    cy.nodes().filter(n => n.data("label").toLowerCase().includes(q))
      .removeClass("dim").addClass("hi").neighborhood().removeClass("dim");
  }});

  cy.on("mouseover","node", e => {{
    const h = e.target.closedNeighborhood();
    cy.elements().not(h).addClass("dim");
    h.removeClass("dim"); h.edges().addClass("hi"); e.target.addClass("hi");
    cy.container().style.cursor="pointer";
  }});
  cy.on("mouseout","node", () => {{
    cy.elements().removeClass("dim hi");
    cy.container().style.cursor="";
  }});

  cy.on("tap","node", e => {{
    const d = e.target.data();
    const uk = d.snippet_uk ? `<div class="snip uk">🇺🇦 ${{d.snippet_uk}}</div>` : "";
    const en = d.snippet_en ? `<div class="snip en">🇬🇧 ${{d.snippet_en}}</div>` : "";
    const conn = e.target.neighborhood("node")
      .map(n=>`<li>${{n.data("label")}} <span style="color:#aaa;font-size:.68rem">[${{n.data("type")}}]</span></li>`).join("");
    let extra = "";
    if (d.type==="location" && (d.lat||d.lon)) {{
      const url=`https://www.openstreetmap.org/?mlat=${{d.lat}}&mlon=${{d.lon}}&zoom=8`;
      extra = `<div class="field"><b>Map</b><a href="${{url}}" target="_blank">Open in OpenStreetMap ↗</a></div>`;
      if (d.name_uk) extra += `<div class="field"><b>Ukrainian</b><p style="font-size:.78rem">${{d.name_uk}}</p></div>`;
    }}
    document.getElementById("panel").innerHTML = `
      <h3>${{d.label}}</h3>
      <span class="badge ${{d.type==="person"?"bp":"bl"}}">${{d.type}}</span>
      ${{uk}}${{en}}${{extra}}
      ${{conn?`<div class="field"><b>Connected to</b><ul>${{conn}}</ul></div>`:""}}`;
  }});
  cy.on("tap", e => {{
    if (e.target===cy) {{
      cy.elements().removeClass("dim hi");
      document.getElementById("panel").innerHTML="<p class='hint'>Click any node<br>to see details.</p>";
    }}
  }});
  </script>
</body>
</html>"""

    output_path = os.path.join(output_dir, f"{page_id}_graph.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Knowledge graph written to: {output_path}")
    return output_path


# =====================================================================
# 🗺️ AGGREGATED MAP GENERATOR (edition / year / all-history levels)
# locations_list: [{"name_en":..., "name_uk":..., "lat":..., "lon":..., "source_page":...}]
# =====================================================================
_MONTHS_EN = ["","January","February","March","April","May","June",
              "July","August","September","October","November","December"]


def _format_issue_id(issue_id: str) -> str:
    """Converts an issue_id like khliborob_19270316_no11 into a readable label."""
    import re
    m = re.match(r"[a-z]+_(\d{4})(\d{2})(\d{2})_([^_]+)", issue_id, re.I)
    if not m:
        return issue_id
    year, mon_n, day = m.group(1), int(m.group(2)), int(m.group(3))
    mon  = _MONTHS_EN[mon_n] if mon_n <= 12 else str(mon_n)
    issue = m.group(4).replace("no", "No. ").replace("ch", "Ch. ")
    return f"{day} {mon} {year}, {issue}"


def _format_page_citation(page_id: str) -> str:
    """Converts a raw page_id into a readable citation string."""
    import re
    # Issue-level ID (no _page suffix) — delegate to issue formatter
    if "_page" not in page_id:
        return _format_issue_id(page_id)
    m = re.match(r"([a-z]+)_(\d{4})(\d{2})(\d{2})_([^_]+)_page(\d+)", page_id, re.I)
    if not m:
        return page_id
    paper = m.group(1).capitalize()
    mon   = _MONTHS_EN[int(m.group(3))] if int(m.group(3)) <= 12 else m.group(3)
    day   = int(m.group(4))
    issue = m.group(5).replace("no", "No. ").replace("ch", "Ch. ")
    page  = int(m.group(6))
    return f"{paper}, {day} {mon} {m.group(2)}, {issue}, p. {page}"


def generate_aggregated_map(level_id, locations_list, title, subtitle, output_dir, site_base_url=""):
    """
    Builds a multi-source Leaflet map aggregating locations from
    multiple pages. Each marker popup shows the source page(s).
    """
    markers_js = ""
    bounds_coords = []

    def _loc_key(name_en: str, name_uk: str) -> str:
        """
        Normalise a location name for deduplication.
        Strips parenthetical qualifiers, decomposes unicode diacritics,
        and lowercases so 'Maramureș (Мармарощина)' == 'Maramures'.
        """
        raw = (name_en or name_uk).strip()
        raw = re.sub(r"\(.*?\)", "", raw).strip()
        raw = unicodedata.normalize("NFKD", raw)
        raw = "".join(c for c in raw if not unicodedata.combining(c))
        return raw.lower()

    # Merge duplicate locations by normalised name so the same place
    # mentioned on multiple pages gets one pin listing all sources.
    merged = {}
    for loc in locations_list:
        lat     = loc.get("lat", 0.0)
        lon     = loc.get("lon", 0.0)
        name_en = loc.get("name_en", "").strip()
        name_uk = loc.get("name_uk", "").strip()
        key     = _loc_key(name_en, name_uk)
        if not key:
            continue

        if key not in merged:
            merged[key] = {
                "lat":          lat,
                "lon":          lon,
                "name_en":      name_en,
                "name_uk":      name_uk,
                "is_region":    loc.get("is_region", False),
                "polygon_json": loc.get("polygon_json"),
                "pages":        [],
                "omeka_urls":   {},
            }
        else:
            if (merged[key]["lat"] == 0.0 and merged[key]["lon"] == 0.0
                    and (lat != 0.0 or lon != 0.0)):
                merged[key]["lat"]          = lat
                merged[key]["lon"]          = lon
                merged[key]["is_region"]    = loc.get("is_region", False)
                merged[key]["polygon_json"] = loc.get("polygon_json")

        src       = loc.get("source_page", "")
        omeka_url = loc.get("omeka_url", "")
        if src and src not in merged[key]["pages"]:
            merged[key]["pages"].append(src)
        if src and omeka_url:
            merged[key]["omeka_urls"][src] = omeka_url

    for key, loc in merged.items():
        lat       = loc["lat"]
        lon       = loc["lon"]
        name_en     = loc["name_en"]
        name_uk     = loc["name_uk"]
        is_region   = loc.get("is_region", False)
        is_waterway = loc.get("is_waterway", False) or _is_waterway_name(name_en, name_uk)
        def _page_link(pid):
            citation = _format_page_citation(pid)
            if site_base_url:
                return f'<a href="{site_base_url}issues/{pid}/" target="_blank" style="color:#1a4a8a">{citation}</a>'
            return citation
        pages = "<br>".join(_page_link(p) for p in loc["pages"]) if loc["pages"] else "—"
        label       = f"{name_en} ({name_uk})" if name_uk else name_en

        polygon_json = loc.get("polygon_json")
        has_coords   = lat != 0.0 or lon != 0.0
        if not has_coords and not polygon_json:
            continue

        if is_waterway and polygon_json:
            popup = f"💧 {label}<br><small>Sources: {pages}</small><br><small><em>Waterway course shown.</em></small>"
            markers_js += (
                f'    L.geoJSON({polygon_json}, {{'
                f'style: {{color:"#2980b9",fillColor:"#3498db",fillOpacity:0.2,weight:3}}'
                f'}}).addTo(map).bindPopup("{popup}");\n'
            )
        elif is_waterway:
            popup = f"💧 {label}<br><small>Sources: {pages}</small>"
            markers_js += (
                f'    L.circleMarker([{lat}, {lon}], '
                f'{{radius:8, color:"#2980b9", fillColor:"#3498db", fillOpacity:0.8}})'
                f'.addTo(map).bindPopup("{popup}");\n'
            )
        elif is_region and polygon_json:
            popup = f"{label}<br><small>Sources: {pages}</small><br><small><em>Region boundary shown.</em></small>"
            markers_js += (
                f'    L.geoJSON({polygon_json}, {{'
                f'style: {{color:"#e67e22",fillColor:"#f39c12",fillOpacity:0.15,weight:2}}'
                f'}}).addTo(map).bindPopup("{popup}");\n'
            )
        elif is_region:
            popup = f"{label}<br><small>Sources: {pages}</small><br><small><em>⚠️ Large region — centroid only.</em></small>"
            markers_js += (
                f'    L.circleMarker([{lat}, {lon}], '
                f'{{radius:10, color:"#e67e22", fillColor:"#f39c12", fillOpacity:0.8}})'
                f'.addTo(map).bindPopup("{popup}");\n'
            )
        else:
            popup = f"{label}<br><small>Sources: {pages}</small>"
            markers_js += f'    L.marker([{lat}, {lon}]).addTo(map).bindPopup("{popup}");\n'
        bounds_coords.append([lat, lon])

    # Serialise all merged locations to JSON for dynamic JS filtering
    max_mentions = max((len(v["pages"]) for v in merged.values()), default=1)
    locations_data = json.dumps([
        {
            "label":       (f"{v['name_en']} ({v['name_uk']})" if v["name_uk"] else v["name_en"]),
            "lat":         v["lat"],
            "lon":         v["lon"],
            "is_region":   v.get("is_region", False),
            "is_waterway": v.get("is_waterway", False) or _is_waterway_name(v["name_en"], v["name_uk"]),
            "polygon":     v.get("polygon_json"),
            "pages":       v["pages"],
            "omeka_urls":  v.get("omeka_urls", {}),
            "count":       len(v["pages"]),
        }
        for v in merged.values()
        if v["lat"] != 0.0 or v["lon"] != 0.0 or v.get("polygon_json")
    ], ensure_ascii=False)

    if bounds_coords:
        initial_fit = f"map.fitBounds({json.dumps(bounds_coords)}, {{padding: [40, 40]}});"
    else:
        initial_fit = "map.setView([48.0, 31.0], 5);"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <title>{title}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <style>
    body {{ margin:0; font-family:sans-serif; }}
    #header {{ background:#2c3e50; color:#fff; padding:10px 16px;
               display:flex; align-items:center; gap:20px; flex-wrap:wrap; }}
    #header h2 {{ margin:0; font-size:1rem; flex-shrink:0; }}
    #header p  {{ margin:0; font-size:0.8rem; opacity:0.7; }}
    #filter-bar {{ margin-left:auto; display:flex; align-items:center; gap:8px;
                   font-size:0.78rem; background:rgba(255,255,255,0.1);
                   padding:4px 12px; border-radius:5px; }}
    #min-pages {{ width:110px; accent-color:#f39c12; }}
    #map {{ width:100%; height:calc(100vh - 56px); }}
  </style>
</head>
<body>
  <div id="header">
    <div>
      <h2>📍 {title}</h2>
      <p id="loc-count">{subtitle}</p>
    </div>
    <div id="filter-bar">
      <label for="min-pages">Min. page mentions:</label>
      <input type="range" id="min-pages" min="1" max="{max_mentions}" value="1" step="1"/>
      <span id="filter-val">1</span>
    </div>
  </div>
  <div id="map"></div>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <script>
    var map = L.map('map');
    L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png', {{
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors © <a href="https://carto.com/">CARTO</a>',
      subdomains: 'abcd', maxZoom: 19
    }}).addTo(map);

    const allLocations = {locations_data};
    var layerGroup = L.layerGroup().addTo(map);

    var MONTHS = ["","January","February","March","April","May","June",
                  "July","August","September","October","November","December"];
    var SITE_BASE = {json.dumps(site_base_url)};

    function formatIssueId(pid) {{
      // Matches both issue IDs (khliborob_19270316_no11) and page IDs (_page01 suffix)
      var m = pid.match(/[a-z]+_([0-9]{{4}})([0-9]{{2}})([0-9]{{2}})_([^_]+)/i);
      if (!m) return pid;
      var year  = m[1], mon = MONTHS[parseInt(m[2],10)] || m[2], day = parseInt(m[3],10);
      var issue = m[4].replace(/^no/i,"No. ").replace(/^ch/i,"Ch. ");
      return day + " " + mon + " " + year + ", " + issue;
    }}

    function renderMarkers(minPages) {{
      layerGroup.clearLayers();
      var visible = 0;
      allLocations.forEach(function(loc) {{
        if (loc.count < minPages) return;
        visible++;
          var citedIn = loc.pages.map(function(p) {{
          // Strip _pageNN suffix to get the issue ID for the link
          var issueId = p.includes("_page") ? p.substring(0, p.lastIndexOf("_page")) : p;
          var url = (loc.omeka_urls && loc.omeka_urls[p]) ? loc.omeka_urls[p]
                    : (SITE_BASE ? SITE_BASE + "issues/" + issueId + "/" : "");
          var cite = formatIssueId(p);
          return url
            ? '<a href="' + url + '" target="_blank" style="color:#2980b9">' + cite + ' ↗</a>'
            : cite;
        }}).join("<br>");
        var popup = loc.label + "<br><small><b>Cited in:</b><br>" + citedIn + "</small>";

        if ((loc.is_waterway || loc.is_region) && loc.polygon) {{
          var color = loc.is_waterway ? "#2980b9" : "#e67e22";
          var fill  = loc.is_waterway ? "#3498db" : "#f39c12";
          L.geoJSON(JSON.parse(loc.polygon), {{
            style: {{color: color, fillColor: fill, fillOpacity: 0.15, weight: loc.is_waterway ? 3 : 2}}
          }}).addTo(layerGroup).bindPopup(popup);
        }} else if (loc.is_waterway) {{
          L.circleMarker([loc.lat, loc.lon], {{radius:8, color:"#2980b9", fillColor:"#3498db", fillOpacity:0.8}})
           .addTo(layerGroup).bindPopup("💧 " + popup);
        }} else if (loc.is_region) {{
          L.circleMarker([loc.lat, loc.lon], {{radius:10, color:"#e67e22", fillColor:"#f39c12", fillOpacity:0.8}})
           .addTo(layerGroup).bindPopup("⚠️ " + popup + "<br><small><em>Approximate centroid.</em></small>");
        }} else {{
          L.marker([loc.lat, loc.lon]).addTo(layerGroup).bindPopup(popup);
        }}
      }});
      document.getElementById("loc-count").textContent =
        visible + " location(s) visible of " + allLocations.length + " total";
    }}

    renderMarkers(1);
    {initial_fit}

    document.getElementById("min-pages").addEventListener("input", function() {{
      document.getElementById("filter-val").textContent = this.value;
      renderMarkers(parseInt(this.value));
    }});
  </script>
</body>
</html>"""

    output_path = os.path.join(output_dir, f"{level_id}_agg_map.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Aggregated map written: {output_path}")
    return output_path


# =====================================================================
# 🧠 AGGREGATED KNOWLEDGE GRAPH GENERATOR
# nodes_list: [{"id":..., "type":"page"|"person"|"location", "label":...}]
# edges_list: [{"source":..., "target":..., "label":...}]
# =====================================================================
def generate_aggregated_graph(level_id, nodes_list, edges_list, title, subtitle, output_dir, site_base_url=""):
    """
    Builds a multi-source Cytoscape.js knowledge graph.
    Light theme, fcose layout, proportional node size, co-occurrence mode,
    search, and hover-highlight.
    """
    seen_nodes = {}
    for n in nodes_list:
        nid = n["id"]
        if nid not in seen_nodes:
            seen_nodes[nid] = dict(n)
            seen_nodes[nid].setdefault("pages", [])
            seen_nodes[nid].setdefault("snippets_uk", {})
            seen_nodes[nid].setdefault("snippets_en", {})
        else:
            for pg in n.get("pages", []):
                if pg not in seen_nodes[nid]["pages"]:
                    seen_nodes[nid]["pages"].append(pg)
            seen_nodes[nid]["snippets_uk"].update(n.get("snippets_uk", {}))
            seen_nodes[nid]["snippets_en"].update(n.get("snippets_en", {}))
            seen_nodes[nid].setdefault("omeka_urls", {}).update(n.get("omeka_urls", {}))
    unique_nodes = list(seen_nodes.values())

    seen_edges = set()
    unique_edges = []
    for e in edges_list:
        key = f"{e['source']}|{e['target']}"
        if key not in seen_edges:
            seen_edges.add(key)
            unique_edges.append(e)

    nodes_json = json.dumps(unique_nodes, ensure_ascii=False)
    links_json = json.dumps(unique_edges, ensure_ascii=False)

    page_ids_set = {n["id"] for n in unique_nodes if n["type"] == "page"}
    mention_counts = {}
    for e in unique_edges:
        src, tgt = e["source"], e["target"]
        if src in page_ids_set:
            mention_counts[tgt] = mention_counts.get(tgt, 0) + 1
        elif tgt in page_ids_set:
            mention_counts[src] = mention_counts.get(src, 0) + 1
    max_mentions = max(mention_counts.values(), default=1)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    *{{box-sizing:border-box;margin:0;padding:0}}
    body{{background:#f5f4f0;font-family:'Segoe UI',system-ui,sans-serif;color:#1a1a1a;
         display:flex;flex-direction:column;height:100vh;overflow:hidden}}

    /* ── top bar ── */
    #topbar{{background:#fff;border-bottom:1px solid #ddd;padding:8px 14px;flex-shrink:0;
             display:flex;align-items:center;gap:12px;flex-wrap:wrap;box-shadow:0 1px 4px rgba(0,0,0,.08)}}
    #topbar h2{{font-size:.9rem;font-weight:700;color:#1a1a1a;white-space:nowrap}}
    #topbar .sub{{font-size:.72rem;color:#888;white-space:nowrap}}
    #search{{flex:1;min-width:140px;max-width:200px;border:1px solid #ccc;border-radius:6px;
             padding:4px 9px;font-size:.8rem;outline:none}}
    #search:focus{{border-color:#2b6cb0;box-shadow:0 0 0 2px rgba(43,108,176,.2)}}
    .ctrl{{display:flex;align-items:center;gap:6px;font-size:.76rem;color:#555;white-space:nowrap}}
    .ctrl label{{color:#555}}
    #min-mentions{{width:100px;accent-color:#2b6cb0}}
    #node-count{{font-size:.72rem;color:#888}}
    #toggle-pages{{font-size:.76rem;padding:3px 10px;border:1px solid #ccc;border-radius:5px;
                   cursor:pointer;background:#fff;color:#333}}
    #toggle-pages.active{{background:#2b6cb0;color:#fff;border-color:#2b6cb0}}

    /* ── main area ── */
    #main{{display:flex;flex:1;overflow:hidden}}
    #cy{{flex:1;background:#f5f4f0}}

    /* ── detail panel ── */
    #detail{{width:260px;background:#fff;border-left:1px solid #e0e0e0;
             padding:14px;font-size:.8rem;overflow-y:auto;flex-shrink:0;
             box-shadow:-2px 0 6px rgba(0,0,0,.04)}}
    #detail h3{{font-size:.95rem;font-weight:700;color:#1a1a1a;margin-bottom:4px;line-height:1.3}}
    #detail .badge{{display:inline-block;border-radius:99px;padding:2px 10px;
                    font-size:.68rem;font-weight:600;text-transform:uppercase;
                    letter-spacing:.04em;margin-bottom:10px}}
    .badge-person{{background:#dbeafe;color:#1e40af}}
    .badge-location{{background:#d1fae5;color:#065f46}}
    .badge-page{{background:#fef3c7;color:#92400e}}
    #detail .field{{margin-bottom:10px}}
    #detail .field b{{display:block;font-size:.68rem;text-transform:uppercase;
                      letter-spacing:.05em;color:#aaa;margin-bottom:4px}}
    #detail a{{color:#2b6cb0;text-decoration:none}}
    #detail a:hover{{text-decoration:underline}}
    #detail ul{{list-style:none;padding:0}}
    #detail li{{padding:4px 0;border-bottom:1px solid #f0f0f0;font-size:.78rem}}
    #detail li:last-child{{border-bottom:none}}
    .snippet{{background:#f8f8f8;border-left:3px solid #ccc;padding:4px 8px;
              margin-top:3px;font-size:.74rem;font-style:italic;color:#555;
              border-radius:0 4px 4px 0}}
    .snippet.uk{{border-color:#2b6cb0}}
    .snippet.en{{border-color:#059669}}
    #detail .hint{{color:#bbb;font-size:.78rem;margin-top:20px;line-height:1.6;text-align:center}}

    /* ── legend ── */
    #legend{{position:absolute;bottom:12px;left:12px;background:rgba(255,255,255,.92);
             padding:7px 12px;border-radius:8px;font-size:.72rem;color:#444;
             border:1px solid #e0e0e0;backdrop-filter:blur(4px);display:flex;gap:14px}}
    .dot{{display:inline-block;width:10px;height:10px;border-radius:50%;
          margin-right:4px;vertical-align:middle}}

    /* ── loading overlay ── */
    #loading{{position:absolute;inset:0;background:#f5f4f0;display:flex;
              align-items:center;justify-content:center;font-size:.85rem;
              color:#888;z-index:10;pointer-events:none}}
  </style>
</head>
<body>
  <div id="topbar">
    <div>
      <h2>🧠 {title}</h2>
      <span class="sub">{subtitle} &nbsp;·&nbsp; Scroll to zoom · Drag to pan · Click for details</span>
    </div>
    <input id="search" type="search" placeholder="Search person or place…" autocomplete="off"/>
    <div class="ctrl">
      <label for="min-mentions">Min. mentions</label>
      <input type="range" id="min-mentions" min="1" max="{max_mentions}" value="1" step="1"/>
      <span id="filter-val">1</span>
      <span id="node-count"></span>
    </div>
    <button id="toggle-pages">Show issue nodes</button>
  </div>
  <div id="main" style="position:relative">
    <div id="cy"></div>
    <div id="loading">Building graph…</div>
    <div id="legend">
      <span><span class="dot" style="background:#3b82f6"></span>Person</span>
      <span><span class="dot" style="background:#10b981"></span>Location</span>
      <span><span class="dot" style="background:#f59e0b" id="legend-page"></span>Issue</span>
    </div>
  </div>
  <div id="detail"><p class="hint">Click any node<br>to see details.</p></div>

  <script src="https://cdn.jsdelivr.net/npm/cytoscape@3.26.0/dist/cytoscape.min.js"></script>
  <script>
  // ── iframe redirect ──
  if (window.self !== window.top) {{
    document.body.innerHTML = `
      <div style="display:flex;flex-direction:column;align-items:center;justify-content:center;
                  height:100vh;background:#f5f4f0;font-family:sans-serif;gap:16px;padding:20px;text-align:center">
        <p style="font-size:.9rem;color:#666">The Knowledge Graph needs its own tab to be fully interactive.</p>
        <a href="${{window.location.href}}" target="_blank"
           style="background:#2b6cb0;color:#fff;padding:12px 28px;border-radius:8px;
                  text-decoration:none;font-size:.9rem;font-weight:600">
          🧠 Open Knowledge Graph ↗
        </a>
      </div>`;
  }}

  const SITE_BASE = {json.dumps(site_base_url)};
  const rawNodes  = {nodes_json};
  const rawEdges  = {links_json};

  function nodeId(x) {{ return (x && typeof x === "object") ? x.id : String(x); }}

  // ── mention counts ──
  const pageIds = new Set(rawNodes.filter(n => n.type === "page").map(n => n.id));
  const mentionCount = {{}};
  rawEdges.forEach(e => {{
    const s = nodeId(e.source), t = nodeId(e.target);
    if (pageIds.has(s)) mentionCount[t] = (mentionCount[t]||0)+1;
    if (pageIds.has(t)) mentionCount[s] = (mentionCount[s]||0)+1;
  }});

  // ── co-occurrence edges (entity ↔ entity sharing a page) ──
  const pageToEntities = {{}};
  rawEdges.forEach(e => {{
    const s = nodeId(e.source), t = nodeId(e.target);
    const pg = pageIds.has(s) ? s : (pageIds.has(t) ? t : null);
    const en = pg === s ? t : s;
    if (pg) {{ pageToEntities[pg] = pageToEntities[pg] || []; pageToEntities[pg].push(en); }}
  }});
  const coEdges = [];
  const coSeen  = new Set();
  Object.values(pageToEntities).forEach(ents => {{
    for (let i = 0; i < ents.length; i++)
      for (let j = i+1; j < ents.length; j++) {{
        const key = [ents[i],ents[j]].sort().join("|");
        if (!coSeen.has(key)) {{ coSeen.add(key); coEdges.push({{source:ents[i],target:ents[j]}}); }}
      }}
  }});

  // ── node size: 28-70px proportional to mention count ──
  function nodeSize(n) {{
    const mc = mentionCount[n.id] || 0;
    const max = {max_mentions};
    return max <= 1 ? 32 : 28 + Math.round((mc / max) * 16);
  }}

  // ── build Cytoscape elements ──
  let showPages = false;
  function buildElements(minM) {{
    const vis = new Set(
      rawNodes.filter(n => n.type==="page" || (mentionCount[n.id]||0) >= minM).map(n => n.id)
    );
    const nodes = rawNodes
      .filter(n => vis.has(n.id) && (showPages || n.type !== "page"))
      .map(n => ({{ data:{{
        id: n.id, label: n.label || n.id, type: n.type,
        pages: (n.pages||[]).join(","),
        mentions: mentionCount[n.id]||0,
        size: nodeSize(n),
        snippets_uk: JSON.stringify(n.snippets_uk||{{}}),
        snippets_en: JSON.stringify(n.snippets_en||{{}}),
      }} }}));
    const visIds = new Set(nodes.map(n => n.data.id));

    let edgeSource = showPages ? rawEdges : coEdges;
    const edges = edgeSource
      .filter(e => visIds.has(nodeId(e.source)) && visIds.has(nodeId(e.target)))
      .map((e,i) => ({{ data:{{ id:"e"+i, source:nodeId(e.source), target:nodeId(e.target) }} }}));
    return [...nodes, ...edges];
  }}

  function updateCount(min) {{
    const n = rawNodes.filter(r => r.type!=="page" && (mentionCount[r.id]||0)>=min).length;
    document.getElementById("node-count").textContent = "(" + n + " entities)";
  }}

  // ── Cytoscape styles ──
  const STYLES = [
    {{ selector:"node[type='person']", style:{{
        "background-color":"#3b82f6","border-color":"#1d4ed8","border-width":2,
        "width":"data(size)","height":"data(size)",
        "label":"data(label)","color":"#1e3a5f","font-size":13,"font-weight":600,
        "text-valign":"bottom","text-halign":"center","text-margin-y":5,
        "text-background-color":"#fff","text-background-opacity":1,
        "text-background-padding":"3px","text-background-shape":"roundrectangle",
        "text-max-width":"140px","text-wrap":"ellipsis",
    }} }},
    {{ selector:"node[type='location']", style:{{
        "background-color":"#10b981","border-color":"#065f46","border-width":2,
        "width":"data(size)","height":"data(size)",
        "label":"data(label)","color":"#064e3b","font-size":13,"font-weight":600,
        "text-valign":"bottom","text-halign":"center","text-margin-y":5,
        "text-background-color":"#fff","text-background-opacity":1,
        "text-background-padding":"3px","text-background-shape":"roundrectangle",
        "text-max-width":"140px","text-wrap":"ellipsis",
    }} }},
    {{ selector:"node[type='page']", style:{{
        "background-color":"#f59e0b","border-color":"#b45309","border-width":1.5,
        "width":22,"height":22,"shape":"rectangle",
        "label":"data(label)","color":"#78350f","font-size":10,
        "text-valign":"bottom","text-halign":"center","text-margin-y":4,
        "text-background-color":"#fff","text-background-opacity":1,
        "text-background-padding":"2px","text-background-shape":"roundrectangle",
        "text-max-width":"110px","text-wrap":"ellipsis",
    }} }},
    {{ selector:"node:selected", style:{{
        "border-color":"#e11d48","border-width":4,"overlay-opacity":0,
    }} }},
    {{ selector:"node.dimmed", style:{{"opacity":0.12}} }},
    {{ selector:"node.highlighted", style:{{"border-color":"#e11d48","border-width":3}} }},
    {{ selector:"edge", style:{{
        "line-color":"#cbd5e1","opacity":0.7,"width":1.5,
        "curve-style":"bezier","target-arrow-shape":"none",
    }} }},
    {{ selector:"edge.dimmed", style:{{"opacity":0.04}} }},
    {{ selector:"edge.highlighted", style:{{
        "line-color":"#e11d48","opacity":1,"width":2.5,
    }} }},
  ];

  const LAYOUT_OPTS = {{
    name:"cose", animate:false, padding:80,
    nodeRepulsion:28000, idealEdgeLength:160, edgeElasticity:0.3,
    gravity:0.08, numIter:1200, nodeDimensionsIncludeLabels:true,
    randomize:true,
  }};

  const cy = cytoscape({{
    container: document.getElementById("cy"),
    elements: buildElements(1),
    style: STYLES,
    layout: LAYOUT_OPTS,
    userZoomingEnabled:true, userPanningEnabled:true, boxSelectionEnabled:false,
  }});

  document.getElementById("loading").style.display = "none";
  updateCount(1);

  // ── search ──
  document.getElementById("search").addEventListener("input", function() {{
    const q = this.value.trim().toLowerCase();
    if (!q) {{ cy.elements().removeClass("dimmed highlighted"); return; }}
    cy.elements().addClass("dimmed");
    cy.nodes().filter(n => n.data("label").toLowerCase().includes(q))
      .removeClass("dimmed").addClass("highlighted")
      .neighborhood().removeClass("dimmed");
  }});

  // ── min-mentions slider ──
  const slider = document.getElementById("min-mentions");
  slider.addEventListener("input", function() {{
    const min = parseInt(this.value);
    document.getElementById("filter-val").textContent = min;
    updateCount(min);
    cy.elements().remove();
    cy.add(buildElements(min));
    cy.layout(Object.assign({{}}, LAYOUT_OPTS, {{animate:true,animationDuration:500}})).run();
    resetDetail();
  }});

  // ── toggle issue nodes ──
  document.getElementById("toggle-pages").addEventListener("click", function() {{
    showPages = !showPages;
    this.classList.toggle("active", showPages);
    document.getElementById("legend-page").parentElement.style.opacity = showPages ? "1" : "0.3";
    const min = parseInt(slider.value);
    cy.elements().remove();
    cy.add(buildElements(min));
    cy.layout(Object.assign({{}}, LAYOUT_OPTS, {{animate:true,animationDuration:500}})).run();
    resetDetail();
  }});

  // ── hover: dim/highlight ──
  cy.on("mouseover", "node", function(e) {{
    const hood = e.target.closedNeighborhood();
    cy.elements().not(hood).addClass("dimmed");
    hood.removeClass("dimmed");
    hood.edges().addClass("highlighted");
    e.target.addClass("highlighted");
    cy.container().style.cursor = "pointer";
  }});
  cy.on("mouseout", "node", function() {{
    cy.elements().removeClass("dimmed highlighted");
    cy.container().style.cursor = "";
  }});

  // ── helpers ──
  function resetDetail() {{
    document.getElementById("detail").innerHTML = "<p class='hint'>Click any node<br>to see details.</p>";
  }}

  function formatPageId(pid) {{
    const mo = ["","January","February","March","April","May","June",
                "July","August","September","October","November","December"];
    const m = pid.match(/([a-z]+)_([0-9]{{4}})([0-9]{{2}})([0-9]{{2}})_([^_]+)(?:_page([0-9]+))?/i);
    if (!m) return pid;
    const paper = m[1].charAt(0).toUpperCase()+m[1].slice(1);
    const mon = mo[parseInt(m[3],10)]||m[3];
    const iss = m[5].replace(/^no/i,"No. ");
    const pg  = m[6] ? ", p. "+parseInt(m[6],10) : "";
    return paper+", "+parseInt(m[4],10)+" "+mon+" "+m[2]+", "+iss+pg;
  }}

  // ── click: detail panel ──
  cy.on("tap", "node", function(e) {{
    const d = e.target.data();
    const badgeClass = "badge badge-" + d.type;
    const typeLabel  = d.type === "page" ? "Issue" : d.type.charAt(0).toUpperCase()+d.type.slice(1);

    let body = "";
    if (d.type === "page") {{
      const ents = e.target.neighborhood("node")
        .map(n => `<li>${{n.data("label")}} <span style="color:#aaa;font-size:.7rem">[${{n.data("type")}}]</span></li>`)
        .join("");
      body = `<div class="field"><b>Entities mentioned</b><ul>${{ents||"<li>—</li>"}}</ul></div>`;
    }} else {{
      const snUk = JSON.parse(d.snippets_uk||"{{}}");
      const snEn = JSON.parse(d.snippets_en||"{{}}");
      const pages = d.pages ? d.pages.split(",").filter(Boolean) : [];

      const items = pages.map(p => {{
        const cite    = formatPageId(p);
        const issueId = p.includes("_page") ? p.substring(0,p.lastIndexOf("_page")) : p;
        const url     = SITE_BASE ? SITE_BASE+"issues/"+issueId+"/" : "";
        const link    = url
          ? `<a href="${{url}}" target="_blank">📰 ${{cite}} ↗</a>`
          : `<span style="font-weight:600">${{cite}}</span>`;
        const uk = snUk[p] ? `<div class="snippet uk">🇺🇦 "${{snUk[p]}}"</div>` : "";
        const en = snEn[p] ? `<div class="snippet en">🇬🇧 "${{snEn[p]}}"</div>` : "";
        return `<li>${{link}}${{uk}}${{en}}</li>`;
      }}).join("")||"<li>—</li>";

      const connectedTo = e.target.neighborhood("node")
        .filter(n => n.data("type") !== "page")
        .map(n => `<li>${{n.data("label")}}</li>`).join("");

      body = `
        <div class="field"><b>Mentioned in</b><ul>${{items}}</ul></div>
        ${{connectedTo ? `<div class="field"><b>Co-occurs with</b><ul>${{connectedTo}}</ul></div>` : ""}}
      `;
    }}

    document.getElementById("detail").innerHTML = `
      <h3>${{d.label}}</h3>
      <span class="${{badgeClass}}">${{typeLabel}}</span>
      ${{d.mentions ? `<div style="font-size:.72rem;color:#888;margin-bottom:8px">${{d.mentions}} mention${{d.mentions>1?"s":""}}</div>` : ""}}
      ${{body}}`;
  }});

  cy.on("tap", function(e) {{
    if (e.target === cy) {{ resetDetail(); cy.elements().removeClass("dimmed highlighted"); }}
  }});
  </script>
</body>
</html>"""

    output_path = os.path.join(output_dir, f"{level_id}_agg_graph.html")
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f" -> Aggregated graph written: {output_path}")
    return output_path
