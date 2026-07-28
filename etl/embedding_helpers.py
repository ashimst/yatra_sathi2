"""
Shared embedding text-generation helpers.

Used by both the ETL EmbeddingPipeline and the runtime EmbeddingService
so the same input always produces byte-identical vectors.
"""

from __future__ import annotations

from typing import Any, Callable


class EmbeddingTextHelpers:

    @staticmethod
    def build_synthetic_structured_sentence(
        place: Any,
        raw_tags: dict | None,
        place_fields_getter: Callable[[str, Any], Any],
    ) -> str:
        """
        Build a rich, differentiated natural-language sentence from all
        available structured fields.

        The goal is that two different places NEVER produce the same sentence
        even if they share a category — location, OSM tags, elevation, and
        semantic metadata all contribute to make each vector unique.
        """
        rt = raw_tags or {}
        get = place_fields_getter
        parts: list[str] = []

        # ── Identity ────────────────────────────────────────────────────────
        name     = (get("name", None) or "").strip()
        category = (get("category", None) or "").strip()
        group    = (get("group", None) or "").strip()

        if name and category:
            parts.append(f"{name} is a {category}")
        elif name:
            parts.append(name)
        elif category:
            parts.append(f"A {category}")

        if group and group.lower() not in ("unknown", "other", ""):
            parts.append(f"in the {group} group")

        # ── Location — use every geographic signal available ────────────────
        district = rt.get("addr:district") or rt.get("district") or rt.get("is_in:district")
        city     = rt.get("addr:city") or rt.get("city") or rt.get("is_in:city")
        state    = (rt.get("addr:state") or rt.get("state") or
                    rt.get("is_in:state") or rt.get("addr:province"))
        country  = rt.get("addr:country") or rt.get("country")
        is_in    = rt.get("is_in")

        loc_parts: list[str] = []
        if city:
            loc_parts.append(city)
        if district and district.lower() != (city or "").lower():
            loc_parts.append(f"{district} district")
        if state and state.lower() not in [x.lower() for x in loc_parts]:
            loc_parts.append(state)
        if loc_parts:
            parts.append(f"located in {', '.join(loc_parts)}")
        elif is_in:
            # OSM free-form "is_in" tag — can contain "Pokhara, Kaski, Gandaki, Nepal"
            parts.append(f"situated in {is_in}")
        if country and country.lower() not in ("np", "nepal", ""):
            parts.append(f"in {country}")

        # ── Physical characteristics ────────────────────────────────────────
        ele = rt.get("ele") or rt.get("elevation")
        if ele:
            try:
                parts.append(f"at {float(ele):.0f} m elevation")
            except (ValueError, TypeError):
                parts.append(f"at {ele} elevation")

        prominence = rt.get("prominence")
        if prominence:
            parts.append(f"prominence {prominence} m")

        # ── OSM type / purpose tags ─────────────────────────────────────────
        # These are the most semantically rich OSM tags — use them all.
        osm_type_labels = [
            ("tourism",   "{v} tourism destination"),
            ("historic",  "historic {v} site"),
            ("natural",   "natural {v}"),
            ("amenity",   "{v} amenity"),
            ("leisure",   "{v} leisure facility"),
            ("religion",  "{v} religious site"),
            ("heritage",  "heritage {v}"),
            ("landuse",   "{v} land use"),
            ("man_made",  "{v}"),
            ("sport",     "{v} sport venue"),
        ]
        for tag_key, template in osm_type_labels:
            val = rt.get(tag_key)
            if val and str(val).lower() not in ("yes", "no", ""):
                parts.append(template.replace("{v}", str(val)))

        # Food & hospitality specifics
        cuisine = rt.get("cuisine")
        if cuisine:
            parts.append(f"serving {cuisine} cuisine")
        stars = rt.get("stars")
        if stars:
            parts.append(f"{stars}-star establishment")
        diet = rt.get("diet:vegetarian") or rt.get("diet:vegan") or rt.get("diet:halal")
        if diet and str(diet).lower() in ("yes", "only"):
            diet_type = ("vegetarian" if rt.get("diet:vegetarian") else
                         "vegan" if rt.get("diet:vegan") else "halal")
            parts.append(f"offers {diet_type} options")

        # ── Semantic metadata ───────────────────────────────────────────────
        travel_styles = list(get("travel_styles", None) or rt.get("travel_styles") or [])
        if travel_styles:
            parts.append(f"ideal for {', '.join(str(s) for s in travel_styles[:6])}")

        semantic_tags = list(get("semantic_tags", None) or [])
        # Filter out purely generic tags that would be identical across many places
        _boring = {category.lower(), group.lower(), "sightseeing", "wikidata linked",
                   "wikipedia linked", "", "none"}
        meaningful_tags = [t for t in semantic_tags
                           if str(t).lower() not in _boring][:8]
        if meaningful_tags:
            parts.append(f"features: {', '.join(str(t) for t in meaningful_tags)}")

        landscape = list(get("landscape", None) or rt.get("landscape") or [])
        if landscape:
            parts.append(f"{', '.join(str(l) for l in landscape[:4])} landscape")

        difficulty = get("difficulty", None) or rt.get("difficulty")
        if difficulty:
            parts.append(f"{difficulty} difficulty")

        visit_duration = get("visit_duration", None) or rt.get("visit_duration")
        if visit_duration:
            parts.append(f"typical visit {visit_duration}")

        best_seasons = list(get("best_seasons", None) or rt.get("best_seasons") or [])
        if best_seasons and best_seasons != ["All year"]:
            parts.append(f"best visited in {', '.join(str(s) for s in best_seasons)}")

        if get("family_friendly", None):
            parts.append("family-friendly")

        accessibility = get("accessibility", None) or rt.get("accessibility")
        if accessibility and accessibility.lower() not in ("fully accessible", "varies"):
            parts.append(f"access: {accessibility}")

        # ── Quality/recognition signals ─────────────────────────────────────
        pop = get("popularity", None)
        rat = get("rating", None)
        if pop is not None:
            try:
                if float(pop) >= 70:
                    parts.append("highly popular tourist destination")
                elif float(pop) >= 40:
                    parts.append("popular destination")
            except (ValueError, TypeError):
                pass
        if rat is not None:
            try:
                if float(rat) >= 4.0:
                    parts.append("highly rated")
            except (ValueError, TypeError):
                pass

        # Extra name variants — help the model pick up alternative spellings
        name_ne = rt.get("name:ne") or rt.get("name:nep")
        name_en = rt.get("name:en")
        alt_name = rt.get("alt_name") or rt.get("official_name")
        name_extras: list[str] = []
        if name_en and name_en.strip().lower() != name.lower():
            name_extras.append(name_en.strip())
        if name_ne and name_ne.strip():
            name_extras.append(name_ne.strip())
        if alt_name and alt_name.strip().lower() != name.lower():
            name_extras.append(alt_name.strip())
        if name_extras:
            parts.append(f"also known as {', '.join(name_extras)}")

        if parts:
            return ". ".join(parts) + "."
        return f"{name or 'Unknown'} is a {category or 'tourist attraction'} in Nepal."

    @staticmethod
    def compose_embedding_text(
        wikidata_description: str | None,
        wikipedia_extract: str | None,
        synthetic_sentence: str,
    ) -> str:
        """
        Compose final embedding text.

        Priority order (most authoritative first):
          1. Wikipedia extract  (real prose, most informative)
          2. Wikidata description (short, factual)
          3. Synthetic sentence  (always present, always differentiated)

        Wiki content is prepended so the model anchors on factual text.
        The synthetic sentence always follows to add structured signals
        (location, travel style, season) that wiki text often omits.
        """
        def _clean(t: str | None, max_chars: int) -> str | None:
            if not t:
                return None
            s = " ".join(str(t).split()).strip()
            if not s:
                return None
            if len(s) > max_chars:
                s = s[:max_chars].rstrip()
                for sep in (". ", "! ", "? "):
                    idx = s.rfind(sep)
                    if idx >= max_chars * 0.6:
                        s = s[: idx + 1]
                        break
            if not s.endswith((".", "!", "?")):
                s += "."
            return s

        chunks: list[str] = []

        # Wikipedia extract first — richest signal
        wp = _clean(wikipedia_extract, 600)
        if wp:
            chunks.append(wp)

        # Wikidata description — short factual label
        wd = _clean(wikidata_description, 300)
        if wd and (not chunks or wd.lower() not in chunks[0].lower()):
            chunks.append(wd)

        # Synthetic sentence — always last, always present
        syn = (synthetic_sentence or "").strip()
        if syn:
            chunks.append(syn)

        return " ".join(chunks) if chunks else "Unknown tourist place of interest in Nepal."
