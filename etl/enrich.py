"""
Enrichment stage — Wikidata & Wikipedia metadata with local SQLite cache.

Input:  normalized/places.jsonl
Output: enriched/places.jsonl

Priority order
--------------
Wikidata:
  1. OSM raw_tags["wikidata"] Q-ID  (exact, no fuzzy search)
  2. Fuzzy name search via wbsearchentities

Wikipedia summary:
  1. Wikidata enwiki sitelink
  2. OSM raw_tags["wikipedia"] parsed tag
  3. English name fallback
"""

from __future__ import annotations

import json
import sqlite3
import ssl
import threading
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any
from urllib.parse import quote

import requests
from requests.adapters import HTTPAdapter
from tqdm import tqdm
from urllib3.util.ssl_ import create_urllib3_context

from etl.config import ENRICHED_FILE, ENRICHMENT_CACHE, NORMALIZED_FILE
from etl.hydration import stream_places
from etl.models import Place


# ─────────────────────────────────────────────────────────────────────────────
# Shared HTTP session with graceful SSL fallback
# ─────────────────────────────────────────────────────────────────────────────

def _build_session() -> requests.Session:
    sess = requests.Session()
    sess.headers.update({"User-Agent": "YatraSathi/1.0 (contact@yatrasathi.com)"})

    default_ok = True
    try:
        with requests.Session() as probe:
            probe.headers.update(dict(sess.headers))
            probe.get("https://www.wikidata.org/wiki/Special:EntityData/Q2.json", timeout=5)
    except Exception as e:
        msg = str(e).lower()
        default_ok = not any(k in msg for k in ("certificate verify failed", "certificate has expired", "ssl.c"))

    class _LenientSSL(HTTPAdapter):
        def init_poolmanager(self, *a, **kw):
            if not default_ok:
                ctx = create_urllib3_context()
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                kw["ssl_context"] = ctx
            return super().init_poolmanager(*a, **kw)

    sess.mount("https://", _LenientSSL())
    sess.verify = default_ok
    if not default_ok:
        warnings.warn("SSL cert issue — using unverified HTTPS for Wikidata enrichment only.")
        try:
            import urllib3
            urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except Exception:
            pass
    return sess


_SESSION_LOCK = threading.Lock()
_SHARED_SESSION: requests.Session | None = None


def _http() -> requests.Session:
    global _SHARED_SESSION
    with _SESSION_LOCK:
        if _SHARED_SESSION is None:
            _SHARED_SESSION = _build_session()
    return _SHARED_SESSION


# ─────────────────────────────────────────────────────────────────────────────
# SQLite cache
# ─────────────────────────────────────────────────────────────────────────────

class EnrichmentCache:
    """Thread-safe persistent SQLite cache for Wikidata / Wikipedia API responses."""

    def __init__(self, db_path: Path = ENRICHMENT_CACHE) -> None:
        db_path.parent.mkdir(parents=True, exist_ok=True)
        self._path = db_path
        self._local = threading.local()
        with sqlite3.connect(str(db_path)) as c:
            c.execute(
                "CREATE TABLE IF NOT EXISTS api_cache "
                "(cache_key TEXT PRIMARY KEY, data_json TEXT, "
                "created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"
            )
            c.commit()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn"):
            self._local.conn = sqlite3.connect(str(self._path))
        return self._local.conn

    def get(self, key: str) -> dict[str, Any] | None:
        row = self._conn().execute(
            "SELECT data_json FROM api_cache WHERE cache_key=?", (key,)
        ).fetchone()
        if row and row[0]:
            return json.loads(row[0])
        return None

    def set(self, key: str, value: dict[str, Any] | None) -> None:
        c = self._conn()
        c.execute(
            "INSERT OR REPLACE INTO api_cache (cache_key, data_json) VALUES (?,?)",
            (key, json.dumps(value) if value else ""),
        )
        c.commit()


CACHE = EnrichmentCache()


# ─────────────────────────────────────────────────────────────────────────────
# Wikidata client
# ─────────────────────────────────────────────────────────────────────────────

class WikidataClient:

    def __init__(self, cache: EnrichmentCache = CACHE) -> None:
        self.cache = cache

    @staticmethod
    def is_qid(v: Any) -> bool:
        if not v:
            return False
        s = str(v).strip()
        return len(s) >= 2 and s[0].upper() == "Q" and s[1:].isdigit()

    @staticmethod
    def best_latin_name(raw_tags: dict, fallback: str | None) -> str | None:
        for k in ("name:en", "int_name", "name", "alt_name:en"):
            v = raw_tags.get(k)
            if v and isinstance(v, str) and v.strip():
                return v.strip()
        return fallback.strip() if fallback else None

    def _extract_entity(self, qid: str, entity: dict) -> dict[str, Any]:
        claims = entity.get("claims", {})
        labels = entity.get("labels", {})
        descs  = entity.get("descriptions", {})
        result: dict[str, Any] = {
            "wikidata_id":    qid,
            "wikidata_label": labels.get("en", {}).get("value"),
            "description":    descs.get("en", {}).get("value"),
        }
        if "P18" in claims:
            img = claims["P18"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
            if img:
                result["image"] = f"https://commons.wikimedia.org/wiki/Special:FilePath/{img}"
        if "P856" in claims:
            ws = claims["P856"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
            if ws:
                result["website"] = ws
        if "P625" in claims:
            coord = claims["P625"][0].get("mainsnak", {}).get("datavalue", {}).get("value")
            if coord:
                result["wikidata_coordinates"] = {
                    "latitude": coord.get("latitude"),
                    "longitude": coord.get("longitude"),
                }
        sitelinks = entity.get("sitelinks", {})
        if "enwiki" in sitelinks:
            title = sitelinks["enwiki"]["title"].replace(" ", "_")
            result["wikipedia_url"]   = f"https://en.wikipedia.org/wiki/{title}"
            result["wikipedia_title"] = sitelinks["enwiki"]["title"]
        return result

    def query_by_qid(self, qid: str) -> dict[str, Any] | None:
        qid = str(qid).strip()
        if not self.is_qid(qid):
            return None
        key = f"wikidata_qid:{qid.lower()}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached or None
        try:
            r = _http().get(
                f"https://www.wikidata.org/wiki/Special:EntityData/{qid}.json",
                timeout=8,
            )
            if r.status_code != 200:
                self.cache.set(key, {})
                return None
            entities = r.json().get("entities", {})
            entity = entities.get(qid) or (next(iter(entities.values()), None) if entities else None)
            if not entity:
                self.cache.set(key, {})
                return None
            result = self._extract_entity(qid, entity)
            self.cache.set(key, result)
            return result
        except Exception as e:
            print(f"[enrich] QID lookup error {qid!r}: {e}")
            return None

    def query_by_name(self, name: str) -> dict[str, Any] | None:
        if not name:
            return None
        key = f"wikidata_search:{name.lower().strip()}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached or None
        try:
            r = _http().get(
                "https://www.wikidata.org/w/api.php",
                params={"action": "wbsearchentities", "search": name,
                        "language": "en", "format": "json", "limit": 1, "type": "item"},
                timeout=8,
            )
            if r.status_code != 200:
                return None
            items = r.json().get("search", [])
            if not items:
                self.cache.set(key, {})
                return None
            item = items[0]
            result = self.query_by_qid(item["id"]) or {
                "wikidata_id":    item["id"],
                "wikidata_label": item.get("label"),
                "description":    item.get("description"),
            }
            if not result.get("description") and item.get("description"):
                result["description"] = item["description"]
            self.cache.set(key, result)
            return result
        except Exception as e:
            print(f"[enrich] name search error {name!r}: {e}")
            return None


# ─────────────────────────────────────────────────────────────────────────────
# Wikipedia client
# ─────────────────────────────────────────────────────────────────────────────

class WikipediaClient:

    def __init__(self, cache: EnrichmentCache = CACHE) -> None:
        self.cache = cache

    def get_summary(self, title: str) -> dict[str, Any] | None:
        if not title:
            return None
        key = f"wikipedia:{title.lower().strip()}"
        cached = self.cache.get(key)
        if cached is not None:
            return cached or None
        try:
            r = _http().get(
                f"https://en.wikipedia.org/api/rest_v1/page/summary/{quote(title)}",
                timeout=8,
            )
            if r.status_code == 200:
                data = r.json()
                result = {
                    "wikipedia_extract": data.get("extract"),
                    "wikipedia_url": data.get("content_urls", {}).get("desktop", {}).get("page"),
                }
                self.cache.set(key, result)
                return result
        except Exception:
            pass
        self.cache.set(key, {})
        return None

    def get_summary_from_osm_tag(self, tag: str) -> dict[str, Any] | None:
        """Parse an OSM `wikipedia=*` tag (e.g. 'en:Everest') and fetch summary."""
        if not tag:
            return None
        s = str(tag).strip()
        if ":" not in s:
            return self.get_summary(s)
        lang, _, title = s.partition(":")
        lang, title = lang.strip().lower(), title.strip()
        if not title:
            return None
        url = f"https://{lang}.wikipedia.org/wiki/{title.replace(' ', '_')}"
        if lang != "en":
            return {"wikipedia_url": url, "wikipedia_title": title}
        return self.get_summary(title)


# ─────────────────────────────────────────────────────────────────────────────
# Enrich a single place
# ─────────────────────────────────────────────────────────────────────────────

_wikidata = WikidataClient()
_wikipedia = WikipediaClient()


def enrich_place(place: Place) -> Place:
    """Enrich one place in-place and return it."""
    rt = place.raw_tags or {}

    # ── Wikidata ──────────────────────────────────────────────────────────────
    osm_qid = rt.get("wikidata") or place.wikidata_id
    wd_data: dict[str, Any] | None = None

    if WikidataClient.is_qid(osm_qid):
        wd_data = _wikidata.query_by_qid(str(osm_qid))
    else:
        search_name = WikidataClient.best_latin_name(rt, place.name)
        if search_name:
            wd_data = _wikidata.query_by_name(search_name)

    # ── Wikipedia ─────────────────────────────────────────────────────────────
    wp_data: dict[str, Any] | None = None
    if wd_data and wd_data.get("wikipedia_title"):
        wp_data = _wikipedia.get_summary(wd_data["wikipedia_title"])
    else:
        osm_wp = rt.get("wikipedia")
        if osm_wp:
            wp_data = _wikipedia.get_summary_from_osm_tag(osm_wp)
        if not wp_data:
            fallback = WikidataClient.best_latin_name(rt, place.name)
            if fallback:
                wp_data = _wikipedia.get_summary(fallback)

    # ── Promote onto Place ────────────────────────────────────────────────────
    if wd_data:
        place.wikidata_id = wd_data.get("wikidata_id") or place.wikidata_id
        if wd_data.get("description"):
            rt["wikidata_description"] = wd_data["description"]
        if wd_data.get("image"):
            rt["wikidata_image"] = wd_data["image"]
        if wd_data.get("website"):
            place.website = wd_data["website"]
        if wd_data.get("wikipedia_url") and not place.wikipedia_url:
            place.wikipedia_url = wd_data["wikipedia_url"]

    if wp_data:
        if wp_data.get("wikipedia_url") and not place.wikipedia_url:
            place.wikipedia_url = wp_data["wikipedia_url"]
        if wp_data.get("wikipedia_extract"):
            rt["wikipedia_extract"] = wp_data["wikipedia_extract"]

    # Fallback: promote OSM tag Q-ID even if API failed
    if not place.wikidata_id and WikidataClient.is_qid(osm_qid):
        place.wikidata_id = str(osm_qid)

    place.raw_tags = rt
    return place


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class EnrichmentPipeline:

    def __init__(
        self,
        input_file:  Path = NORMALIZED_FILE,
        output_file: Path = ENRICHED_FILE,
        max_workers: int  = 10,
    ) -> None:
        self.input_file  = input_file
        self.output_file = output_file
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.max_workers = max_workers
        self.stats = {"total": 0, "enriched": 0, "wikidata": 0, "wikipedia": 0}

    def run(self) -> None:
        print(f"[enrich] {self.input_file} → {self.output_file} (workers={self.max_workers})")
        places = list(stream_places(self.input_file))
        self.stats["total"] = len(places)
        enriched: list[Place | None] = [None] * len(places)

        with ThreadPoolExecutor(max_workers=self.max_workers) as ex:
            futs = {ex.submit(enrich_place, p): i for i, p in enumerate(places)}
            with tqdm(total=len(places), desc="Enrich", unit=" places") as bar:
                for fut in as_completed(futs):
                    idx = futs[fut]
                    try:
                        enriched[idx] = fut.result()
                    except Exception:
                        enriched[idx] = places[idx]
                    bar.update()

        with open(self.output_file, "w", encoding="utf-8") as f:
            for p in enriched:
                if p:
                    if p.wikidata_id:
                        self.stats["wikidata"] += 1
                    if p.wikipedia_url:
                        self.stats["wikipedia"] += 1
                    self.stats["enriched"] += 1
                    f.write(json.dumps(p.to_dict()) + "\n")

        print(f"\nEnrich complete:")
        print(f"  Total:     {self.stats['total']:,}")
        print(f"  Wikidata:  {self.stats['wikidata']:,}")
        print(f"  Wikipedia: {self.stats['wikipedia']:,}")


def main() -> None:
    EnrichmentPipeline().run()


if __name__ == "__main__":
    main()
