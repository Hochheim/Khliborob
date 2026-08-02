# =====================================================================
# 📄 data_writer.py — STRUCTURED JSON OUTPUT MODULE
# Replaces omeka.py as the primary pipeline output.
# Writes one JSON file per issue to output_data\, which build_site.py
# reads to generate the complete static website.
# =====================================================================

import os
import json
from datetime import datetime, timezone

from config import CURRENT_VERSION


def write_issue_json(
    page_id, vlm, full_transcript_text, full_transcript_text_en,
    scan_cid, trans_cid, alto_cid, mets_cid, iiif_cid, net_cid,
    map_cid, graph_cid, tx_hash, output_data_dir
):
    """
    Writes a structured JSON file for one processed page/issue.
    Multiple pages belonging to the same issue are merged into one file.
    """
    meta = vlm.get("page_metadata", {})
    page_num = meta.get("page_id", page_id).split("page")[-1] if "page" in page_id else "1"

    # Derive issue_id from page_id by stripping _pageXX suffix
    if "_page" in page_id:
        issue_id = page_id.rsplit("_page", 1)[0]
    else:
        issue_id = page_id

    issue_file = os.path.join(output_data_dir, f"{issue_id}.json")

    # Load existing issue file if it exists (multi-page issues)
    if os.path.exists(issue_file):
        with open(issue_file, "r", encoding="utf-8") as f:
            issue_data = json.load(f)
    else:
        # Create new issue record
        pub_date = meta.get("publication_date", "")
        issue_data = {
            "issue_id": issue_id,
            "date": pub_date,
            "year": pub_date[:4] if len(pub_date) >= 4 else "unknown",
            "month": pub_date[5:7] if len(pub_date) >= 7 else "unknown",
            "issue_number": meta.get("issue_number", ""),
            "newspaper_name_uk": meta.get("newspaper_name_uk", "Хлібороб"),
            "newspaper_name_en": meta.get("newspaper_name_en", "Khliborob"),
            "version": CURRENT_VERSION,
            "processed_at": datetime.now(timezone.utc).isoformat(),
            "pages": [],
            "entities": {"persons": [], "locations": []},
            "translations": {
                "abstract_uk": "",
                "abstract_en": "",
                "keywords_uk": [],
                "keywords_en": []
            },
            "low_confidence_tokens": [],
            "network_edges": [],
            "gpu_connections": [],
            "cids": {
                "mets": mets_cid,
                "iiif": iiif_cid,
                "network": net_cid,
                "map": map_cid,
                "graph": graph_cid
            },
            "tx_hash": tx_hash
        }

    # Add or update this page
    # Load Portuguese transcript if available
    _project = os.environ.get("PROJECT_FOLDER", "C:\\Projekt")
    pt_path = os.path.join(_project, "output_text", f"{page_id}_flow_pt.txt")
    full_transcript_text_pt = ""
    if os.path.exists(pt_path):
        with open(pt_path, "r", encoding="utf-8") as f:
            full_transcript_text_pt = f.read()

    page_record = {
        "page_id": page_id,
        "page_number": page_num,
        "transcript_uk": full_transcript_text,
        "transcript_en": full_transcript_text_en,
        "transcript_pt": full_transcript_text_pt,
        "cids": {
            "scan": scan_cid,
            "transcript": trans_cid,
            "alto": alto_cid
        },
        "tx_hash": tx_hash
    }

    # Check if page already exists and update, else append
    existing_pages = [p["page_id"] for p in issue_data["pages"]]
    if page_id in existing_pages:
        idx = existing_pages.index(page_id)
        issue_data["pages"][idx] = page_record
    else:
        issue_data["pages"].append(page_record)

    # Merge entities (deduplicate)
    existing_persons = set(issue_data["entities"]["persons"])
    for person in vlm.get("entities", {}).get("persons", []):
        existing_persons.add(person)
    issue_data["entities"]["persons"] = sorted(list(existing_persons))

    existing_locs = {loc.get("name_en", ""): loc
                     for loc in issue_data["entities"]["locations"]}
    for loc in vlm.get("entities", {}).get("locations", []):
        name = loc.get("name_en", "")
        if name and name not in existing_locs:
            existing_locs[name] = loc
    issue_data["entities"]["locations"] = list(existing_locs.values())

    # Use translations from most recent page (usually page 1)
    trans = vlm.get("translations", {})
    if trans.get("abstract_en") and not issue_data["translations"]["abstract_en"]:
        issue_data["translations"]["abstract_en"] = trans.get("abstract_en", "")
        issue_data["translations"]["abstract_uk"] = trans.get("abstract_uk", "")
        issue_data["translations"]["keywords_en"] = trans.get("keywords_en", [])
        issue_data["translations"]["keywords_uk"] = trans.get("keywords_uk", [])

    # Append low confidence tokens
    for token in vlm.get("low_confidence_tokens", []):
        issue_data["low_confidence_tokens"].append(token)

    # Write back
    with open(issue_file, "w", encoding="utf-8") as f:
        json.dump(issue_data, f, ensure_ascii=False, indent=2)

    print(f"    💾 Issue JSON written: {issue_file}")
    return issue_file


def add_gpu_connection(issue_id, gpu_doc, output_data_dir):
    """
    Adds a GPU document connection to an existing issue JSON file.
    Call this after all pages are processed to annotate relevant issues.

    gpu_doc: dict with keys:
        document_id, archive_ref, date, sender, recipient, description
    """
    issue_file = os.path.join(output_data_dir, f"{issue_id}.json")
    if not os.path.exists(issue_file):
        print(f"    ⚠️ Cannot add GPU connection — issue file not found: {issue_file}")
        return

    with open(issue_file, "r", encoding="utf-8") as f:
        issue_data = json.load(f)

    existing_ids = [g["document_id"] for g in issue_data.get("gpu_connections", [])]
    if gpu_doc["document_id"] not in existing_ids:
        issue_data.setdefault("gpu_connections", []).append(gpu_doc)
        with open(issue_file, "w", encoding="utf-8") as f:
            json.dump(issue_data, f, ensure_ascii=False, indent=2)
        print(f"    🔗 GPU connection added to {issue_id}: {gpu_doc['document_id']}")


# =====================================================================
# PRE-DEFINED GPU CONNECTIONS
# Add these after processing the relevant issues.
# =====================================================================
GPU_CONNECTIONS = [
    {
        "document_id": "FISU_F1_Case7408_Vol4_P8",
        "archive_ref": "FISU — F.1 — Case 7408 — Vol. 4 — P. 8",
        "date": "1932-11-14",
        "document_type": "intelligence_summary",
        "sender": "INO OOS GPU",
        "recipient": "Japanese intelligence (intercepted)",
        "description_en": (
            "GPU intelligence summary No. 23 (14 Nov 1932), compiled for Japanese "
            "diplomatic services, cites Ukraïns'kyi Khliborob as source for "
            "information about executions of starving peasants during the Holodomor."
        ),
        "description_uk": (
            "Зведення ГПУ № 23 (14 листопада 1932 р.), складене для японської "
            "дипломатичної служби, посилається на «Українській хлібороб» як "
            "джерело інформації про розстріли голодуючих селян під час Голодомору."
        ),
        "issues_referenced": ["khliborob_19320131_no3"]
    },
    {
        "document_id": "FISU_F1_Case7408_Letter_Oct1930",
        "archive_ref": "FISU — F.1 — Case 7408 — Vol. 4",
        "date": "1930-10-27",
        "document_type": "intercepted_letter",
        "sender": "GPU agent, Istanbul",
        "recipient": "Editor, Ukraïns'kyi Khliborob, Brazil",
        "description_en": (
            "Letter intercepted by GPU sent to the editor of Khliborob from "
            "an Istanbul GPU contact, requesting information about the "
            "Ukrainian community in Brazil and acknowledging receipt of the newspaper."
        ),
        "description_uk": (
            "Лист, перехоплений ГПУ, відправлений до редактора «Хлібороба» "
            "від стамбульського контакту ГПУ, із запитом про українську "
            "громаду в Бразилії та підтвердженням отримання газети."
        ),
        "issues_referenced": []
    },
    {
        "document_id": "FISU_F1_Case7408_SPUnion_Nov1930",
        "archive_ref": "FISU — F.1 — Case 7408",
        "date": "1930-11-23",
        "document_type": "intercepted_letter",
        "sender": "Ukraïns'kyi Narodnyi Soiuz, São Caetano, São Paulo",
        "recipient": "Ukrainian Hromada, Istanbul",
        "description_en": (
            "Letter from the previously undocumented Ukrainian People's Union "
            "(São Caetano, São Paulo), intercepted by GPU, describing the "
            "organisation's anti-Soviet programme and seeking coordination "
            "with the Istanbul Ukrainian community."
        ),
        "description_uk": (
            "Лист від раніше незадокументованого Українського народного союзу "
            "(Сан-Каетану, Сан-Паулу), перехоплений ГПУ, де описується "
            "антирадянська програма організації та пропонується координація "
            "з українською громадою в Стамбулі."
        ),
        "issues_referenced": []
    },
    {
        "document_id": "FISU_F1_Case7408_Curitiba_Feb1932",
        "archive_ref": "FISU — F.1 — Case 7408",
        "date": "1932-02-22",
        "document_type": "intercepted_letter",
        "sender": "Ukraïns'kyi Tsentr v Kuritiba, Brazil",
        "recipient": "Ukrainian Society, Istanbul",
        "description_en": (
            "Letter from the Ukrainian Centre in Curitiba intercepted by GPU, "
            "referencing a Christmas greeting published in Khliborob No. 3 "
            "(31 Jan 1932) and requesting ongoing correspondence with Istanbul."
        ),
        "description_uk": (
            "Лист від Українського центру в Куритибі, перехоплений ГПУ, "
            "з посиланням на різдвяне привітання, опубліковане в «Хліборобі» "
            "№ 3 (31 січня 1932 р.), та проханням про подальше листування "
            "зі Стамбулом."
        ),
        "issues_referenced": ["khliborob_19320131_no3"]
    }
]
