import csv
import io
import json
import os
import sys
import unicodedata
from typing import Dict, Optional

from flask import Blueprint, Response, render_template, request

# Make web/data importable regardless of working directory
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from data.academic_periods import ACADEMIC_PERIODS

from moveon import MoveOn, MoveOnAPIError

imports_bp = Blueprint("imports", __name__, url_prefix="/import")

# ---------------------------------------------------------------------------
# Field map: CSV column → API field (None = resolved separately)
# ---------------------------------------------------------------------------
CATALOGUE_COURSE_COLUMNS = {
    "course_name":           "catalogue_course_name",
    "institution_name":      None,   # → catalogue_course_subinstitution_id
    "academic_period_name":  None,   # → catalogue_course_academic_period_id
    "language":              None,   # → catalogue_course_lang_id
    "degree_program_name":   None,   # → searched live → catalogue_course_course_id
    "teacher":               "catalogue_course_teacher",
    "credits":               "catalogue_course_credits",
    "ects_credits":          "catalogue_course_ectscredits",
    "description":           "catalogue_course_description",
    "reference":             "catalogue_course_reference",
    "external_id":           "externalId",
    "remarks":               "catalogue_course_remarks",
    "code":                  "catalogue_course_code",
}

TEMPLATE_HINTS = [
    "Course name (required)",
    "Exact institution name from MoveOn",
    "Period name or short name, e.g. 1er semestre 2025/26 or S12025/26",
    "English / French / German / Spanish  (or EN/FR/DE/ES  or Anglais/Français/Allemand/Espagnol)",
    "Degree program name — looked up live in MoveOn",
    "Teacher full name",
    "Number of credits",
    "ECTS credits",
    "Course description",
    "Course reference code",
    "Your internal ID for this course",
    "Additional remarks",
    "Numeric code",
]

TEMPLATE_EXAMPLE = [
    "Introduction to Python",
    "Université de Lille",
    "1er semestre 2025/26",
    "English",
    "Master Informatique",
    "Prof. Smith",
    "3",
    "6",
    "Introductory Python programming course",
    "PY101",
    "EXT-PY101",
    "Required for all CS students",
    "1001",
]

# ---------------------------------------------------------------------------
# Language normalisation → lang_id
# Accepts: English/Anglais/EN, French/Français/FR, German/Allemand/DE, Spanish/Espagnol/ES
# IDs below are fetched dynamically from MoveOn at import time; this map is
# used to normalise the user-supplied string before matching against API data.
# ---------------------------------------------------------------------------
_LANG_ALIASES: Dict[str, str] = {
    "english": "english", "anglais": "english", "en": "english",
    "french": "french",   "français": "french", "francais": "french", "fr": "french",
    "german": "german",   "allemand": "german", "de": "german",
    "spanish": "spanish", "espagnol": "spanish", "es": "spanish",
}

_LANG_NAME_FRAGMENTS: Dict[str, list] = {
    "english":  ["english", "anglais"],
    "french":   ["french", "français", "francais"],
    "german":   ["german", "allemand", "deutsch"],
    "spanish":  ["spanish", "espagnol", "español"],
}


def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )


def _normalise_lang(raw: str) -> Optional[str]:
    key = _strip_accents(raw.strip().lower())
    return _LANG_ALIASES.get(key)


def _fetch_lang_lookup(client: MoveOn) -> Dict[str, int]:
    """Fetch language reference list from MoveOn → {normalised_key: id}."""
    try:
        data = client._client._get("reference-lists")
        entries = data.get("data", {})
        # reference-lists may return a dict of lists keyed by list name
        if isinstance(entries, dict):
            for key, items in entries.items():
                if "lang" in key.lower() and isinstance(items, list):
                    return _parse_lang_list(items)
        # Or a flat list
        if isinstance(entries, list):
            return _parse_lang_list(entries)
    except Exception:
        pass
    return {}


def _parse_lang_list(items: list) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    for item in items:
        name = str(item.get("name") or item.get("label") or "").lower()
        item_id = item.get("id")
        if not item_id:
            continue
        for lang_key, fragments in _LANG_NAME_FRAGMENTS.items():
            if any(f in name for f in fragments):
                lookup[lang_key] = int(item_id)
    return lookup


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _config_file() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".moveon_config.json")


def _get_client() -> Optional[MoveOn]:
    path = _config_file()
    if not os.path.exists(path):
        return None
    with open(path) as f:
        cfg = json.load(f)
    return MoveOn(
        f"https://{cfg['instance']}.restapi.moveonfr.com/api/v1/",
        cfg["username"],
        cfg["password"],
    )


def _institution_lookup(client: MoveOn) -> Dict[str, int]:
    lookup: Dict[str, int] = {}
    for inst in client.internal_institutions.iter_all():
        name = (
            inst.get("internal_institution_name")
            or inst.get("institution_name")
            or inst.get("name", "")
        ).strip()
        id_ = inst.get("id")
        if name and id_:
            lookup[name] = int(id_)
    return lookup


def _degree_program_lookup(client: MoveOn, name: str) -> Optional[int]:
    """Search degree-programs by name and return the first matching ID."""
    results = client.degree_programs.list(
        criteria=[{"field": "degree_program_name", "operator": "ct", "value": name}],
        limit=1,
    )
    if results:
        return results[0].get("id")
    return None


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@imports_bp.route("/catalogue-courses")
def catalogue_courses_page():
    return render_template("imports/catalogue_courses.html")


@imports_bp.route("/catalogue-courses/template")
def download_template():
    headers = list(CATALOGUE_COURSE_COLUMNS.keys())
    out = io.StringIO()
    writer = csv.writer(out, delimiter=";")
    writer.writerow(headers)
    writer.writerow(["# " + h for h in TEMPLATE_HINTS])
    writer.writerow(TEMPLATE_EXAMPLE)
    return Response(
        out.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=catalogue_courses_template.csv"},
    )


@imports_bp.route("/catalogue-courses/run", methods=["POST"])
def run_import():
    client = _get_client()
    if not client:
        return render_template(
            "imports/catalogue_courses.html",
            error="Not connected to MoveOn. Please configure the connection first.",
        )

    data_file = request.files.get("data_csv")
    if not data_file or data_file.filename == "":
        return render_template("imports/catalogue_courses.html", error="Please upload a data CSV file.")

    # One-time lookups
    try:
        inst_lookup = _institution_lookup(client)
    except Exception as e:
        return render_template(
            "imports/catalogue_courses.html",
            error=f"Could not fetch institutions from MoveOn: {e}",
        )

    lang_lookup = _fetch_lang_lookup(client)

    # Parse CSV (semicolon-separated, UTF-8 BOM-safe)
    try:
        content = data_file.read().decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(content), delimiter=";"))
    except Exception as e:
        return render_template("imports/catalogue_courses.html", error=f"Could not read CSV: {e}")

    results = []
    for i, row in enumerate(rows, start=1):
        if row.get("course_name", "").startswith("#"):
            continue

        payload: Dict = {}
        warnings = []

        # Institution name → ID
        inst_name = row.get("institution_name", "").strip()
        if inst_name:
            inst_id = inst_lookup.get(inst_name)
            if inst_id:
                payload["catalogue_course_subinstitution_id"] = inst_id
            else:
                warnings.append(f"Institution '{inst_name}' not found in MoveOn")

        # Academic period name → ID (bundled lookup)
        period_name = row.get("academic_period_name", "").strip()
        if period_name:
            period_id = ACADEMIC_PERIODS.get(period_name)
            if period_id:
                payload["catalogue_course_academic_period_id"] = period_id
            else:
                warnings.append(f"Academic period '{period_name}' not found in lookup")

        # Language → lang_id
        lang_raw = row.get("language", "").strip()
        if lang_raw:
            lang_key = _normalise_lang(lang_raw)
            if lang_key:
                lang_id = lang_lookup.get(lang_key)
                if lang_id:
                    payload["catalogue_course_lang_id"] = lang_id
                else:
                    warnings.append(
                        f"Language '{lang_raw}' recognised but ID not found in MoveOn reference lists"
                    )
            else:
                warnings.append(
                    f"Language '{lang_raw}' not recognised. Use English/French/German/Spanish or EN/FR/DE/ES"
                )

        # Degree program name → ID (live search)
        dp_name = row.get("degree_program_name", "").strip()
        if dp_name:
            try:
                dp_id = _degree_program_lookup(client, dp_name)
                if dp_id:
                    payload["catalogue_course_course_id"] = dp_id
                else:
                    warnings.append(f"Degree program '{dp_name}' not found in MoveOn")
            except Exception as e:
                warnings.append(f"Degree program lookup failed: {e}")

        # Direct column mappings
        for csv_col, api_field in CATALOGUE_COURSE_COLUMNS.items():
            if api_field and row.get(csv_col, "").strip():
                payload[api_field] = row[csv_col].strip()

        # Create
        try:
            resp = client.catalogue_courses.create(payload)
            new_id = resp.get("data", {}).get("id") if isinstance(resp.get("data"), dict) else None
            results.append({
                "row": i,
                "name": row.get("course_name", ""),
                "status": "ok",
                "id": new_id,
                "warnings": warnings,
            })
        except MoveOnAPIError as e:
            results.append({
                "row": i,
                "name": row.get("course_name", ""),
                "status": "error",
                "message": e.message,
                "warnings": warnings,
            })
        except Exception as e:
            results.append({
                "row": i,
                "name": row.get("course_name", ""),
                "status": "error",
                "message": str(e),
                "warnings": warnings,
            })

    return render_template("imports/catalogue_courses.html", results=results)
