"""
Debug script to check embedding data and place ID matching.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from backend.app.db.database import SessionLocal
from backend.app.models.place import Place as PlaceDB
from backend.app.models.embedding import Embedding as EmbeddingDB


def main():
    """Debug embedding data."""
    print("=" * 70)
    print("Debugging Embedding Data")
    print("=" * 70)
    
    session = SessionLocal()
    try:
        # Check total places
        place_count = session.query(PlaceDB).count()
        print(f"\n[INFO] Total places in database: {place_count}")
        
        # Check total embeddings
        embedding_count = session.query(EmbeddingDB).count()
        print(f"[INFO] Total embeddings in database: {embedding_count}")
        
        # Get sample place
        sample_place = session.query(PlaceDB).first()
        if sample_place:
            print(f"\n[INFO] Sample place:")
            print(f"  ID: {sample_place.id}")
            print(f"  Name: {sample_place.name}")
            print(f"  Type: {type(sample_place.id)}")
        
        # Check if this place has embedding
        if sample_place:
            embedding = session.query(EmbeddingDB).filter(
                EmbeddingDB.place_id == sample_place.id
            ).first()
            
            if embedding:
                print(f"\n[OK] Embedding found for sample place:")
                print(f"  Embedding ID: {embedding.id}")
                print(f"  Place ID: {embedding.place_id}")
                print(f"  Type: {type(embedding.place_id)}")
                print(f"  Model: {embedding.model_name}")
                print(f"  Dimensions: {embedding.dimensions}")
                print(f"  Vector length: {len(embedding.vector) if embedding.vector else 0}")
            else:
                print(f"\n[WARNING] No embedding found for sample place")
        
        # Check a few random places and their embeddings
        print(f"\n[INFO] Checking 5 random places for embeddings:")
        random_places = session.query(PlaceDB).limit(5).all()
        
        for i, place in enumerate(random_places, 1):
            embedding = session.query(EmbeddingDB).filter(
                EmbeddingDB.place_id == place.id
            ).first()
            has_embedding = "YES" if embedding else "NO"
            print(f"  {i}. {place.name}: {has_embedding}")
            if embedding:
                print(f"     Embedding dimensions: {embedding.dimensions}")
        
    except Exception as e:
        print(f"\n[ERROR] Debug failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    main()
