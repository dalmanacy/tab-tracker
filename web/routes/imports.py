import csv
import io
import json
import os
from typing import Dict

from flask import Blueprint, Response, render_template, request

from moveon import MoveOn, MoveOnAPIError

imports_bp = Blueprint("imports", __name__, url_prefix="/import")

CATALOGUE_COURSE_COLUMNS = {
    "course_name":          "catalogue_course_name",
    "institution_name":     None,   # → catalogue_course_subinstitution_id via lookup
    "academic_period_name": None,   # → catalogue_course_academic_period_id via lookup
    "teacher":              "catalogue_course_teacher",
    "credits":              "catalogue_course_credits",
    "ects_credits":         "catalogue_course_ectscredits",
    "description":          "catalogue_course_description",
    "reference":            "catalogue_course_reference",
    "external_id":          "externalId",
    "remarks":              "catalogue_course_remarks",
    "code":                 "catalogue_course_code",
}

TEMPLATE_EXAMPLE = [
    "Introduction to Python",
    "Université de Lille",
    "1er semestre 2026/27",
    "Prof. Smith",
    "3",
    "6",
    "Introductory Python programming course",
    "PY101",
    "EXT-PY101",
    "Required for all CS students",
    "1001",
]

TEMPLATE_HINTS = [
    "Course name (required)",
    "Exact institution name from MoveOn",
    "Exact academic period name from MoveOn",
    "Teacher name",
    "Number of credits",
    "ECTS credits",
    "Course description",
    "Course reference code",
    "Your internal ID for this course",
    "Additional remarks",
    "Numeric code",
]


def _config_file():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), ".moveon_config.json")


def _get_client():
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


def _parse_periods_csv(content: bytes) -> Dict[str, int]:
    """Parse a MoveOn academic-periods export (UTF-16 TSV) → {name: id}."""
    lookup = {}
    try:
        text = content.decode("utf-16")
    except Exception:
        text = content.decode("utf-8-sig", errors="replace")

    reader = csv.DictReader(io.StringIO(text), delimiter="\t")
    for row in reader:
        row = {k.strip(): v.strip() for k, v in row.items() if k}
        id_val = next((row[k] for k in row if "ID" in k and "riode" in k), None)
        name_val = row.get("Nom") or row.get("Name")
        if id_val and name_val:
            try:
                lookup[name_val] = int(id_val)
            except ValueError:
                pass
    return lookup


def _institution_lookup(client: MoveOn) -> Dict[str, int]:
    """Fetch all internal institutions from MoveOn → {name: id}."""
    lookup = {}
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


@imports_bp.route("/catalogue-courses")
def catalogue_courses_page():
    return render_template("imports/catalogue_courses.html")


@imports_bp.route("/catalogue-courses/template")
def download_template():
    headers = list(CATALOGUE_COURSE_COLUMNS.keys())
    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(headers)
    writer.writerow(["# " + hint for hint in TEMPLATE_HINTS])
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
    periods_file = request.files.get("periods_csv")

    if not data_file or data_file.filename == "":
        return render_template("imports/catalogue_courses.html", error="Please upload a data CSV file.")

    # Build institution lookup (live from MoveOn)
    try:
        inst_lookup = _institution_lookup(client)
    except Exception as e:
        return render_template(
            "imports/catalogue_courses.html",
            error=f"Could not fetch institutions from MoveOn: {e}",
        )

    # Build academic period lookup (from uploaded CSV)
    period_lookup = {}
    if periods_file and periods_file.filename != "":
        period_lookup = _parse_periods_csv(periods_file.read())

    # Parse data CSV
    try:
        content = data_file.read().decode("utf-8-sig")
        rows = list(csv.DictReader(io.StringIO(content)))
    except Exception as e:
        return render_template("imports/catalogue_courses.html", error=f"Could not read CSV: {e}")

    results = []
    for i, row in enumerate(rows, start=1):
        if row.get("course_name", "").startswith("#"):
            continue

        payload = {}
        warnings = []

        # Resolve institution name → ID
        inst_name = row.get("institution_name", "").strip()
        if inst_name:
            inst_id = inst_lookup.get(inst_name)
            if inst_id:
                payload["catalogue_course_subinstitution_id"] = inst_id
            else:
                warnings.append(f"Institution '{inst_name}' not found in MoveOn")

        # Resolve academic period name → ID
        period_name = row.get("academic_period_name", "").strip()
        if period_name:
            if not period_lookup:
                warnings.append("No academic periods file uploaded — period skipped")
            else:
                period_id = period_lookup.get(period_name)
                if period_id:
                    payload["catalogue_course_academic_period_id"] = period_id
                else:
                    warnings.append(f"Academic period '{period_name}' not found in lookup file")

        # Map remaining columns directly
        for csv_col, api_field in CATALOGUE_COURSE_COLUMNS.items():
            if api_field and row.get(csv_col, "").strip():
                payload[api_field] = row[csv_col].strip()

        # Create record in MoveOn
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
