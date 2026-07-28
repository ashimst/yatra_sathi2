"""
Script to create the embeddings table in the database.

This script creates the embeddings table for storing vector embeddings
of places using pgvector.
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sqlalchemy import text
from app.db.database import engine


def create_embeddings_table():
    """Create the embeddings table."""
    print("=" * 60)
    print("Creating Embeddings Table")
    print("=" * 60)
    
    try:
        with engine.connect() as conn:
            # Drop existing table if it exists to ensure clean schema
            drop_table_sql = "DROP TABLE IF EXISTS embeddings CASCADE;"
            conn.execute(text(drop_table_sql))
            
            # Create the embeddings table with all columns
            create_table_sql = """
            CREATE TABLE embeddings (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                place_id UUID NOT NULL REFERENCES places(id) ON DELETE CASCADE,
                model_name VARCHAR(100) NOT NULL,
                model_version VARCHAR(50),
                dimensions INTEGER,
                vector REAL[],
                embedding_text TEXT,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
            """
            
            conn.execute(text(create_table_sql))
            
            # Create indexes for performance
            create_indexes_sql = """
            CREATE INDEX IF NOT EXISTS idx_embeddings_place_id ON embeddings(place_id);
            CREATE INDEX IF NOT EXISTS idx_embeddings_model_name ON embeddings(model_name);
            """
            
            conn.execute(text(create_indexes_sql))
            
            # Create trigger for updated_at
            create_trigger_sql = """
            CREATE OR REPLACE FUNCTION update_updated_at_column()
            RETURNS TRIGGER AS $$
            BEGIN
                NEW.updated_at = CURRENT_TIMESTAMP;
                RETURN NEW;
            END;
            $$ language 'plpgsql';
            
            DROP TRIGGER IF EXISTS update_embeddings_updated_at ON embeddings;
            CREATE TRIGGER update_embeddings_updated_at
                BEFORE UPDATE ON embeddings
                FOR EACH ROW
                EXECUTE FUNCTION update_updated_at_column();
            """
            
            conn.execute(text(create_trigger_sql))
            
            conn.commit()
            
            print("[OK] Embeddings table created successfully")
            print("[OK] Indexes created")
            print("[OK] Update trigger created")
            
            # Verify table creation
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'embeddings';
            """))
            
            if result.scalar() > 0:
                print("[OK] Table verification successful")
            else:
                print("[ERROR] Table verification failed")
                return False
            
    except Exception as e:
        print(f"[ERROR] Failed to create embeddings table: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    print("\n" + "=" * 60)
    print("[OK] Database setup complete")
    print("=" * 60)
    return True


if __name__ == "__main__":
    success = create_embeddings_table()
    sys.exit(0 if success else 1)
