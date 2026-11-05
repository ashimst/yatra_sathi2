"""
Tests for Milestone 2: Place Photos, Database Schema, and Dual Spatial Engine.
Validates SQLite compatibility, PlacePhoto model, User avatar, Memory foreign keys,
and spatial querying fallbacks on SQLite without PostGIS.
"""
import asyncio
import io
import uuid
import pytest
from fastapi import UploadFile, HTTPException

from tests.auth_helpers import make_test_user
from backend.app.db.database import SessionLocal, init_db
from backend.app.models.user import User
from backend.app.models.place import Place
from backend.app.models.memory import Memory
from backend.app.models.place_photo import PlacePhoto
from backend.app.services.place_service import place_service
from backend.app.services.recommendation_service import recommendation_service
from backend.app.api.places import upload_place_photo, get_place_photos


def _run_coro(coro):
    """Run a coroutine on a real event loop (UploadFile.read may use a threadpool)."""
    return asyncio.run(coro)


@pytest.fixture(scope="module")
def setup_place_id():
    init_db()
    db = SessionLocal()
    place = db.query(Place).first()
    if not place:
        place = Place(
            id=uuid.uuid4(),
            name="Kathmandu Durbar Square",
            category="Cultural Heritage",
            centroid="POINT(85.3075 27.7042)",
            bbox_min_lat=27.703,
            bbox_min_lon=85.306,
            bbox_max_lat=27.705,
            bbox_max_lon=85.309,
            popularity=9.5,
            rating=4.8
        )
        db.add(place)
        db.commit()
    place_id = str(place.id)
    db.close()
    return place_id


def test_models_exported():
    from backend.app.models import (
        User as MUser,
        Itinerary as MItinerary,
        Place as MPlace,
        PlacePhoto as MPlacePhoto,
        Memory as MMemory,
        TrailReport as MTrailReport,
        TrailSteward as MTrailSteward,
    )
    assert MUser is not None
    assert MItinerary is not None
    assert MPlace is not None
    assert MPlacePhoto is not None
    assert MMemory is not None
    assert MTrailReport is not None
    assert MTrailSteward is not None


def test_user_avatar_url_column():
    assert hasattr(User, "avatar_url")


def test_memory_foreign_keys():
    user_fks = {fk.column.table.name for fk in Memory.__table__.c.user_id.foreign_keys}
    assert "users" in user_fks
    itinerary_fks = {fk.column.table.name for fk in Memory.__table__.c.itinerary_id.foreign_keys}
    assert "itineraries" in itinerary_fks


def test_place_photo_model():
    photo_id = uuid.uuid4()
    place_id = uuid.uuid4()
    photo = PlacePhoto(
        id=photo_id,
        place_id=place_id,
        image_url="/uploads/places/sample.jpg",
        caption="Sample view",
        is_cover=True
    )
    d = photo.to_dict()
    assert d["id"] == str(photo_id)
    assert d["place_id"] == str(place_id)
    assert d["image_url"] == "/uploads/places/sample.jpg"
    assert d["caption"] == "Sample view"
    assert d["is_cover"] is True


def test_nearby_places_sqlite_engine(setup_place_id):
    res = place_service.get_nearby_places(27.7, 85.3, radius=10.0, limit=10)
    assert isinstance(res, dict)
    assert "places" in res
    assert "count" in res
    assert "total_count" in res
    assert res["count"] >= 0
    if res["places"]:
        first = res["places"][0]
        assert "distance_km" in first
        assert first["distance_km"] <= 10.0


def test_recommendations_sqlite_engine(setup_place_id):
    res = place_service.get_recommendations(
        origin_lat=27.7,
        origin_lng=85.3,
        dest_lat=28.2,
        dest_lng=83.98,
        corridor_km=30.0,
        limit=10
    )
    assert isinstance(res, dict)
    assert "places" in res
    assert res["count"] >= 0


def test_recommendation_service_route_buffer_sqlite(setup_place_id):
    route_coords = [[85.324, 27.7172], [84.4525, 27.5341], [83.9856, 28.2096]]
    pois = recommendation_service._get_pois_in_route_buffer(route_coords, buffer_km=25.0)
    assert isinstance(pois, list)


def test_upload_place_photo_endpoint(setup_place_id):
    db = SessionLocal()

    bmp_bytes = (
        b"BM"
        b"\x3a\x00\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x36\x00\x00\x00"
        b"\x28\x00\x00\x00"
        b"\x01\x00\x00\x00"
        b"\x01\x00\x00\x00"
        b"\x01\x00"
        b"\x18\x00"
        b"\x00\x00\x00\x00"
        b"\x04\x00\x00\x00"
        b"\x13\x0b\x00\x00"
        b"\x13\x0b\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x00\x00\x00\x00"
        b"\x00\x00\xff\x00"
    )

    file_obj = io.BytesIO(bmp_bytes)
    upload_file = UploadFile(file=file_obj, filename="stupa.bmp", headers={"content-type": "image/bmp"})

    data = _run_coro(upload_place_photo(
        id=setup_place_id,
        file=upload_file,
        caption="Majestic Kathmandu Stupa",
        is_cover=True,
        db=db, user=make_test_user(db, admin=True)))

    assert data["place_id"] == setup_place_id
    assert data["caption"] == "Majestic Kathmandu Stupa"
    assert data["is_cover"] is True
    assert data["image_url"].startswith("/uploads/places/")

    saved = db.query(PlacePhoto).filter(PlacePhoto.id == uuid.UUID(data["id"])).first()
    assert saved is not None
    assert saved.caption == "Majestic Kathmandu Stupa"
    assert saved.is_cover is True

    get_res = _run_coro(get_place_photos(id=setup_place_id, db=db))
    assert any(p["id"] == data["id"] for p in get_res["photos"])
    db.close()


def test_upload_place_photo_invalid_place():
    db = SessionLocal()
    fake_id = str(uuid.uuid4())
    bmp_bytes = b"BM" + b"\x00" * 60
    file_obj = io.BytesIO(bmp_bytes)
    upload_file = UploadFile(file=file_obj, filename="test.bmp")

    with pytest.raises(HTTPException) as exc_info:
        _run_coro(upload_place_photo(
            id=fake_id,
            file=upload_file,
            caption="Test",
            is_cover=False,
            db=db, user=make_test_user(db, admin=True)))
    assert exc_info.value.status_code == 404
    assert "Place not found" in exc_info.value.detail
    db.close()


def test_upload_place_photo_invalid_format(setup_place_id):
    db = SessionLocal()
    corrupted_bytes = b"NOT_AN_IMAGE_PAYLOAD"
    file_obj = io.BytesIO(corrupted_bytes)
    upload_file = UploadFile(file=file_obj, filename="bad.exe")

    with pytest.raises(HTTPException) as exc_info:
        _run_coro(upload_place_photo(
            id=setup_place_id,
            file=upload_file,
            caption="Test",
            is_cover=False,
            db=db, user=make_test_user(db, admin=True)))
    assert exc_info.value.status_code == 400
    assert "Unsupported file format" in exc_info.value.detail
    db.close()
