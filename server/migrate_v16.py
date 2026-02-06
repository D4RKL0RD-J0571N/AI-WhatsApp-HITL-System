from sqlalchemy import create_engine, text
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./sql_app.db")

def migrate():
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        print("Running migration v16: Add License Key to AIConfig...")
        
        try:
            # Check if column exists
            result = conn.execute(text("PRAGMA table_info(ai_configs)"))
            columns = [row[1] for row in result.fetchall()]
            
            if "license_key" not in columns:
                print("Adding license_key column...")
                conn.execute(text("ALTER TABLE ai_configs ADD COLUMN license_key TEXT"))
                print("Column added successfully.")
            else:
                print("Column license_key already exists. Skipping.")
                
        except Exception as e:
            print(f"Migration failed: {e}")

if __name__ == "__main__":
    migrate()
