import psycopg2
import os

# Leggi le variabili d'ambiente di Railway
DB_HOST = os.getenv("PGHOST")
DB_NAME = os.getenv("PGDATABASE")
DB_USER = os.getenv("PGUSER")
DB_PASSWORD = os.getenv("PGPASSWORD")

# La porta è quasi sempre 5432, ma la prendiamo per sicurezza
DB_PORT = os.getenv("PGPORT", "5432") 

# Codice per la creazione della tabella
def create_documents_table():
    conn = None
    try:
        # Connessione al database usando le variabili di Railway
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            port=DB_PORT
        )
        cur = conn.cursor()
        
        # Query per creare la tabella
        print("Creazione della tabella 'documents'...")
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                document_id VARCHAR(255) PRIMARY KEY,
                status VARCHAR(50),
                report_data JSONB
            );
            """
        )
        conn.commit()
        print("Tabella 'documents' creata con successo o già esistente.")
        
    except Exception as error:
        print(f"Errore durante la creazione della tabella: {error}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == '__main__':
    create_documents_table()