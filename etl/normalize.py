"""
Normalize + Validate stage (single merged pass).

Reads extracted/places.jsonl (RawOSMObjects), runs inline validation as a
gate, then normalises passing records into Place objects and writes them to
normalized/places.jsonl.  A validation report is saved as a side-effect.

Parallelised with multiprocessing.Pool — each worker is stateless.
"""

from __future__ import annotations

import json
import multiprocessing as mp
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from shapely.geometry import shape
from shapely.validation import explain_validity
from tqdm import tqdm

from etl.category_mapper import get_category, get_name
from etl.config import EXTRACTED_FILE, NORMALIZED_FILE, VALIDATED_DIR
from etl.enums import OSMObjectType
from etl.hydration import hydrate_raw_osm_object
from etl.models import ImportMetadata, Place, RawOSMObject


# ─────────────────────────────────────────────────────────────────────────────
# Validation
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(slots=True)
class ValidationIssue:
    issue_type: str
    severity:   str           # "error" | "warning"
    message:    str
    object_id:  str
    details:    dict[str, Any] = field(default_factory=dict)


def _validate_geometry(obj: RawOSMObject) -> list[ValidationIssue]:
    issues = []
    oid = str(obj.id)

    if not obj.geometry:
        issues.append(ValidationIssue("missing_geometry", "error", "No geometry", oid))
        return issues

    try:
        geom = shape(obj.geometry)
        if not geom.is_valid:
            issues.append(ValidationIssue(
                "invalid_geometry", "error",
                f"Invalid: {explain_validity(geom)}", oid,
                {"geometry_type": geom.geom_type},
            ))
        if geom.is_empty:
            issues.append(ValidationIssue("empty_geometry", "error", "Empty geometry", oid))
        if geom.geom_type == "Point":
            x, y = geom.x, geom.y
            if not (-180 <= x <= 180):
                issues.append(ValidationIssue("invalid_longitude", "error", f"lon={x}", oid))
            if not (-90 <= y <= 90):
                issues.append(ValidationIssue("invalid_latitude", "error", f"lat={y}", oid))
    except Exception as e:
        issues.append(ValidationIssue("geometry_parse_error", "error", str(e), oid))

    return issues


def _validate_required(obj: RawOSMObject) -> list[ValidationIssue]:
    issues = []
    if obj.osm_id == 0:
        issues.append(ValidationIssue("missing_osm_id", "error", "osm_id=0", str(obj.id)))
    if not obj.raw_tags:
        issues.append(ValidationIssue("missing_tags", "warning", "No tags", str(obj.id)))
    return issues


def _run_validators(obj: RawOSMObject) -> list[ValidationIssue]:
    return _validate_geometry(obj) + _validate_required(obj)


# ─────────────────────────────────────────────────────────────────────────────
# Normalisation helpers
# ─────────────────────────────────────────────────────────────────────────────

def _looks_like_qid(v: Any) -> bool:
    if not v:
        return False
    s = str(v).strip()
    return len(s) >= 2 and s[0].upper() == "Q" and s[1:].isdigit()


def _parse_wikipedia_url(value: Any) -> str | None:
    if not value:
        return None
    s = str(value).strip()
    if ":" not in s:
        return f"https://en.wikipedia.org/wiki/{s.replace(' ', '_')}"
    lang, _, title = s.partition(":")
    lang, title = lang.strip().lower(), title.strip()
    if not title:
        return None
    return f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"


# ─────────────────────────────────────────────────────────────────────────────
# Normalise a single object
# ─────────────────────────────────────────────────────────────────────────────

def normalize_object(raw: RawOSMObject) -> Place | None:
    """Convert a validated RawOSMObject to a Place.  Returns None if unmappable."""
    cat = get_category(raw.raw_tags)
    if not cat:
        return None

    name = get_name(raw.raw_tags)
    if not name:
        return None

    # Centroid from Point geometry (nodes always carry their own coordinates)
    centroid: tuple[float, float] | None = None
    if raw.geometry and raw.geometry.get("type") == "Point":
        coords = raw.geometry.get("coordinates", [])
        if len(coords) == 2:
            centroid = (float(coords[0]), float(coords[1]))

    osm_type = raw.osm_type
    if isinstance(osm_type, str):
        try:
            osm_type = OSMObjectType(osm_type)
        except ValueError:
            return None

    raw_tags = raw.raw_tags or {}
    wikidata_id = str(raw_tags["wikidata"]).strip() if _looks_like_qid(raw_tags.get("wikidata")) else None
    wikipedia_url = _parse_wikipedia_url(raw_tags.get("wikipedia"))

    return Place(
        id=raw.id,
        osm_id=raw.osm_id,
        osm_type=osm_type,
        name=name,
        category=cat.name,
        group=cat.group,
        geometry=raw.geometry,
        centroid=centroid,
        raw_tags=raw_tags,
        import_metadata=raw.import_metadata,
        wikidata_id=wikidata_id,
        wikipedia_url=wikipedia_url,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Worker (stateless — safe for multiprocessing)
# ─────────────────────────────────────────────────────────────────────────────

def _process_line(line: str) -> tuple[str | None, list[ValidationIssue], str]:
    """
    Returns (place_json | None, issues, skip_reason).
    skip_reason in {"valid","validation_error","no_category","no_name","parse_error","empty"}
    """
    line = line.strip()
    if not line:
        return None, [], "empty"

    try:
        raw = hydrate_raw_osm_object(json.loads(line))
    except Exception as e:
        return None, [ValidationIssue("parse_error", "error", str(e), "unknown")], "parse_error"

    issues = _run_validators(raw)
    if any(i.severity == "error" for i in issues):
        return None, issues, "validation_error"

    place = normalize_object(raw)
    if place is None:
        reason = "no_category" if not get_category(raw.raw_tags) else "no_name"
        return None, issues, reason

    return json.dumps(place.to_dict()), issues, "valid"


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class NormalizationPipeline:
    def __init__(
        self,
        input_file:  Path = EXTRACTED_FILE,
        output_file: Path = NORMALIZED_FILE,
        report_dir:  Path = VALIDATED_DIR,
        num_workers: int | None = None,
    ) -> None:
        self.input_file  = input_file
        self.output_file = output_file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.report_dir  = report_dir
        self.report_dir.mkdir(parents=True, exist_ok=True)
        self.num_workers = num_workers or max(1, mp.cpu_count() - 1)

        self.stats: dict[str, int] = {
            "total_input":             0,
            "normalized":              0,
            "skipped_validation_error":0,
            "skipped_no_category":     0,
            "skipped_no_name":         0,
            "skipped_parse_error":     0,
            "skipped_other":           0,
            "validation_errors":       0,
            "validation_warnings":     0,
        }
        self._all_issues: list[ValidationIssue] = []

    def run(self) -> None:
        print(f"[normalize] {self.input_file} → {self.output_file}")
        print(f"[normalize] workers={self.num_workers}")

        with open(self.input_file, "r", encoding="utf-8") as f:
            lines = f.readlines()

        self.stats["total_input"] = sum(1 for l in lines if l.strip())

        if self.num_workers > 1 and len(lines) > 200:
            with mp.Pool(self.num_workers) as pool:
                results = list(tqdm(
                    pool.imap(_process_line, lines, chunksize=256),
                    total=len(lines), desc="Normalize", unit=" obj",
                ))
        else:
            results = [_process_line(l) for l in tqdm(lines, desc="Normalize", unit=" obj")]

        with open(self.output_file, "w", encoding="utf-8") as out:
            for place_json, issues, reason in results:
                self._all_issues.extend(issues)
                for i in issues:
                    if i.severity == "error":
                        self.stats["validation_errors"] += 1
                    else:
                        self.stats["validation_warnings"] += 1

                if place_json is not None:
                    out.write(place_json + "\n")
                    self.stats["normalized"] += 1
                elif reason != "empty":
                    key = f"skipped_{reason}"
                    if key in self.stats:
                        self.stats[key] += 1
                    else:
                        self.stats["skipped_other"] += 1

        self._save_report()
        self._print_summary()

    def _save_report(self) -> None:
        report = {
            "total_objects":        self.stats["total_input"],
            "normalized":           self.stats["normalized"],
            "dropped_validation":   self.stats["skipped_validation_error"],
            "dropped_no_category":  self.stats["skipped_no_category"],
            "dropped_no_name":      self.stats["skipped_no_name"],
            "total_issues":         len(self._all_issues),
            "errors":               self.stats["validation_errors"],
            "warnings":             self.stats["validation_warnings"],
        }
        with open(self.report_dir / "validation_report.json", "w") as f:
            json.dump(report, f, indent=2)
        with open(self.report_dir / "validation_issues.jsonl", "w") as f:
            for issue in self._all_issues:
                f.write(json.dumps(asdict(issue)) + "\n")

    def _print_summary(self) -> None:
        s = self.stats
        print(f"\nNormalize complete:")
        print(f"  Input:             {s['total_input']:,}")
        print(f"  Normalized:        {s['normalized']:,}")
        print(f"  Dropped (val err): {s['skipped_validation_error']:,}")
        print(f"  Dropped (no cat):  {s['skipped_no_category']:,}")
        print(f"  Dropped (no name): {s['skipped_no_name']:,}")
        print(f"  Val errors total:  {s['validation_errors']:,}")
        print(f"  Val warnings:      {s['validation_warnings']:,}")


def main() -> None:
    NormalizationPipeline().run()


if __name__ == "__main__":
    main()
