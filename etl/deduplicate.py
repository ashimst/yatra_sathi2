"""
Deduplication stage — spatial-grid O(N) candidate matching.

Input:  enriched/places.jsonl
Output: curated/places.jsonl
"""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from tqdm import tqdm

from etl.config import CURATED_FILE, ENRICHED_FILE
from etl.hydration import stream_places
from etl.models import Place


# ─────────────────────────────────────────────────────────────────────────────
# Similarity helpers
# ─────────────────────────────────────────────────────────────────────────────

def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6_371_000.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dl   = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dl / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def jaccard_name(a: str, b: str) -> float:
    a_l, b_l = a.lower().strip(), b.lower().strip()
    if a_l == b_l:
        return 1.0
    t1, t2 = set(a_l.split()), set(b_l.split())
    if not t1 or not t2:
        return 0.0
    j = len(t1 & t2) / len(t1 | t2)
    if a_l in b_l or b_l in a_l:
        return max(0.85, j)
    return j


def similarity(p1: Place, p2: Place) -> float:
    # Coordinate score
    if not p1.centroid or not p2.centroid:
        coord_score = 0.0
    else:
        lon1, lat1 = p1.centroid
        lon2, lat2 = p2.centroid
        dist = haversine_m(lat1, lon1, lat2, lon2)
        if dist > 1000:
            return 0.0
        coord_score = 1.0 if dist < 50 else 0.8 if dist < 200 else 0.5

    name_score = jaccard_name(p1.name or "", p2.name or "")

    cat_score = (
        1.0 if p1.category == p2.category
        else 0.7 if p1.group == p2.group
        else 0.2
    )

    return 0.55 * name_score + 0.30 * coord_score + 0.15 * cat_score


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class DeduplicationPipeline:

    GRID = 0.01          # ~1.1 km cell size
    THRESHOLD = 0.72

    def __init__(
        self,
        input_file:  Path = ENRICHED_FILE,
        output_file: Path = CURATED_FILE,
    ) -> None:
        self.input_file  = input_file
        self.output_file = output_file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.stats = {"total": 0, "unique": 0, "merged": 0}

    def _cell(self, centroid) -> tuple[int, int]:
        if not centroid:
            return (999_999, 999_999)
        lon, lat = centroid
        return (int(math.floor(lon / self.GRID)), int(math.floor(lat / self.GRID)))

    def _priority(self, p: Place) -> int:
        score = 0
        src = (p.import_metadata.source.value if p.import_metadata else "")
        if src == "osm":
            score += 100
        if p.name:
            score += 10
        if p.wikidata_id:
            score += 5
        if p.wikipedia_url:
            score += 5
        if (p.raw_tags or {}).get("website"):
            score += 3
        return score

    def _merge(self, group: list[Place]) -> Place:
        primary = max(group, key=self._priority)
        merged_tags = dict(primary.raw_tags)
        for p in group:
            if p is primary:
                continue
            for k, v in (p.raw_tags or {}).items():
                if k not in merged_tags or not merged_tags[k]:
                    merged_tags[k] = v
            if not primary.wikidata_id and p.wikidata_id:
                primary.wikidata_id = p.wikidata_id
            if not primary.wikipedia_url and p.wikipedia_url:
                primary.wikipedia_url = p.wikipedia_url

        merged_tags["merge_count"] = str(len(group))
        primary.raw_tags = merged_tags
        return primary

    def run(self) -> None:
        print(f"[deduplicate] {self.input_file} → {self.output_file}")
        places = list(stream_places(self.input_file))
        self.stats["total"] = len(places)

        # Build spatial grid index
        grid: dict[tuple[int, int], list[int]] = defaultdict(list)
        for i, p in enumerate(places):
            grid[self._cell(p.centroid)].append(i)

        processed: set[int] = set()
        dup_groups: list[list[int]] = []

        for i, p1 in enumerate(tqdm(places, desc="Dedup", unit=" places")):
            if i in processed:
                continue
            cx, cy = self._cell(p1.centroid)
            if cx == 999_999:
                continue
            candidates = []
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    candidates.extend(grid.get((cx + dx, cy + dy), []))

            group = [i]
            for j in candidates:
                if j == i or j in processed:
                    continue
                if similarity(p1, places[j]) >= self.THRESHOLD:
                    group.append(j)
                    processed.add(j)

            if len(group) > 1:
                dup_groups.append(group)
                processed.add(i)

        merged_indices: set[int] = set()
        output: list[Place] = []

        for group in tqdm(dup_groups, desc="Merge"):
            merged = self._merge([places[i] for i in group])
            output.append(merged)
            merged_indices.update(group)
            self.stats["merged"] += 1

        for i, p in enumerate(places):
            if i not in merged_indices:
                output.append(p)

        self.stats["unique"] = len(output)

        with open(self.output_file, "w", encoding="utf-8") as f:
            for p in output:
                f.write(json.dumps(p.to_dict()) + "\n")

        print(f"\nDeduplicate complete:")
        print(f"  Total input: {self.stats['total']:,}")
        print(f"  Unique:      {self.stats['unique']:,}")
        print(f"  Merges:      {self.stats['merged']:,}")
        print(f"  Reduction:   {self.stats['total'] - self.stats['unique']:,}")


def main() -> None:
    DeduplicationPipeline().run()


if __name__ == "__main__":
    main()
