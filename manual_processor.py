import json
import psycopg2
from config import DB_CONFIG

def update_document_report(document_id: str, report: dict):
    """
    Aggiorna un record nel database con il report e cambia lo stato a 'ready'.
    """
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        
        # Aggiorna lo stato e il report_data del documento
        cur.execute(
            "UPDATE documents SET status = %s, report_data = %s WHERE document_id = %s",
            ("ready", json.dumps(report), document_id)
        )
        conn.commit()
        
        print(f"✅ Report per il documento '{document_id}' salvato e stato aggiornato a 'ready'.")

    except (Exception, psycopg2.DatabaseError) as error:
        print(f"❌ Errore durante l'aggiornamento del database: {error}")
    finally:
        if conn:
            cur.close()
            conn.close()

if __name__ == "__main__":
    # Sostituisci questo ID con quello che ti viene dato dal frontend
    # Esempio: document_id = "c11c4a98-a7ec-47b1-9c1c-d1e93b23ccb1"
    document_id_to_update = input("Inserisci l'ID del documento da aggiornare: ")
    
    print("\nAdesso inserisci manualmente il report JSON.")
    print("Ricorda la struttura: 'status', 'summary', 'clauses'.")

    # Esempio di report JSON che puoi copiare e incollare
    # Assicurati che il tuo input sia in una sola riga per facilità
    example_report = """
{
    "status": "ready",
    "summary": {
        "n_clauses": 3,
        "n_high": 1,
        "n_medium": 1,
        "n_low": 1,
        "tempo_attuale_min": 30,
        "tempo_ridotto_min": 15,
        "tempo_risparmiato_min": 15,
        "costo_risparmiato_eur": 15.0
    },
    "clauses": [
        {
            "risk": "HIGH",
            "text": "La penale per il mancato pagamento è del 100% dell'importo totale."
        },
        {
            "risk": "MEDIUM",
            "text": "Il compenso per il servizio è di 150 euro l'ora, per un massimo di 10 ore settimanali."
        },
        {
            "risk": "LOW",
            "text": "La garanzia è valida per 12 mesi dalla data di acquisto."
        }
    ]
}
"""

    report_input = input(f"\nPuoi copiare e incollare l'esempio sopra (o scriverne uno tuo).\nPremi Invio per confermare:\n")
    
    try:
        # Tenta di convertire l'input in un oggetto JSON
        report_json = json.loads(report_input)
        
        # Aggiorna il database con i dati che hai inserito
        update_document_report(document_id_to_update, report_json)
        
    except json.JSONDecodeError:
        print("\nErrore: Il testo inserito non è un JSON valido.")