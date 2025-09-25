import psycopg2
from config import DB_CONFIG

def create_tables():
    """Crea la tabella 'documents' nel database PostgreSQL."""
    conn = None
    try:
        # Connessione al database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Query per creare la tabella documents
        cur.execute("""
            CREATE TABLE IF NOT EXISTS documents (
                document_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50) NOT NULL,
                report_data JSONB,
                uploaded_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Conferma le modifiche
        conn.commit()
        print("Tabella 'documents' creata con successo o già esistente.")
        
    except (Exception, psycopg2.DatabaseError) as error:
        print(f"Errore durante la creazione della tabella: {error}")
    finally:
        if conn is not None:
            cur.close()
            conn.close()

if __name__ == '__main__':
    create_tables()