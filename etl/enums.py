"""
ETL enums — canonical definitions, no bridge wrappers.
"""

from __future__ import annotations

from enum import Enum


class OSMObjectType(str, Enum):
    NODE     = "node"
    WAY      = "way"
    RELATION = "relation"


class Source(str, Enum):
    OSM       = "osm"
    WIKIDATA  = "wikidata"
    WIKIPEDIA = "wikipedia"
    MANUAL    = "manual"
