import shutil
import uuid
import json
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber
import psycopg2
import google.generativeai as genai

from config import DB_CONFIG, GEMINI_API_KEY

# Inizializza l'applicazione FastAPI
app = FastAPI()

# Aggiungi il middleware CORS
origins = ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Definisci la directory dove verranno salvati i file caricati
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Configura l'API di Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Funzioni di Analisi con Gemini ---

def extract_text_from_pdf(pdf_path: str) -> str:
    """Estrae il testo completo da un file PDF."""
    full_text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                full_text += page.extract_text() or ""
    except Exception as e:
        print(f"Errore durante l'estrazione del testo: {e}")
        return None
    return full_text

def analyze_with_gemini(document_text: str) -> dict:
    """
    Invia il testo a Google Gemini per l'analisi e riceve un report strutturato.
    """
    prompt = f"""
Sei un assistente legale esperto e il tuo compito è analizzare contratti legali in italiano. Analizza il seguente testo e genera un report dettagliato in formato JSON.
Il JSON deve avere la seguente struttura:
{{
    "status": "ready",
    "summary": {{
        "n_clauses": [numero totale di clausole analizzate],
        "n_high": [numero di clausole ad alto rischio],
        "n_medium": [numero di clausole a medio rischio],
        "n_low": [numero di clausole a basso rischio]
    }},
    "AI_opinion": "Una breve frase di 2-3 righe che sintetizza il parere dell'IA sul documento, magari indicando il livello di complessità o le aree di maggiore attenzione.",
    "clauses": [
        {{
            "risk": "HIGH"|"MEDIUM"|"LOW",
            "text": "la clausola legale",
            "explanation": "spiegazione del rischio e dell'impatto"
        }}
    ]
}}

Considera i seguenti criteri per il rischio:
- HIGH: Clausole con penali elevate, limitazioni di responsabilità estreme o termini che potrebbero portare a perdite finanziarie significative.
- MEDIUM: Clausole complesse, ambigue o che richiedono un'attenzione particolare.
- LOW: Clausole standard, equo e non problematiche.

Testo del documento da analizzare:
---
{document_text}
---
Rispondi SOLO con il blocco JSON e nessun altro testo aggiuntivo.
"""
    try:
        response = model.generate_content(prompt)
        report_json_string = response.text.strip().replace('```json\n', '').replace('```', '')
        report_data = json.loads(report_json_string)
        return report_data
    except Exception as e:
        print(f"Errore nella chiamata all'API di Gemini: {e}")
        return {"status": "failed", "detail": "Errore di analisi con l'IA."}

def estimate_cost(n_clauses: int, efficacia: float = 0.8, tariffa_oraria: int = 100) -> dict:
    """
    Calcola la stima di tempo e costo in base al numero di clausole.
    """
    tempo_medio_per_clausola = 15  # minuti, più alto per l'analisi dettagliata
    
    tempo_attuale = n_clauses * tempo_medio_per_clausola
    tempo_ridotto = tempo_attuale * (1 - efficacia)
    tempo_risparmiato = tempo_attuale - tempo_ridotto
    
    # Calcolo del costo: (tempo risparmiato in minuti / 60) * tariffa oraria
    costo_risparmiato = (tempo_risparmiato / 60) * tariffa_oraria
    
    return {
        "tempo_risparmiato_min": int(tempo_risparmiato),
        "costo_risparmiato_eur": round(costo_risparmiato, 2)
    }

# --- Endpoint API ---

@app.post("/api/v1/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint per caricare un documento PDF e analizzarlo con Google Gemini.
    """
    conn = None
    try:
        document_id = str(uuid.uuid4())
        file_path = UPLOAD_DIR / f"{document_id}.pdf"
        
        # 1. Salva il file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # 2. Estrai il testo
        extracted_text = extract_text_from_pdf(file_path)
        
        if not extracted_text:
            return {"status": "failed", "detail": "Testo non estraibile."}
        
        # 3. Analizza il testo con l'IA di Gemini
        gemini_report = analyze_with_gemini(extracted_text)
        
        if gemini_report.get("status") == "failed":
            return gemini_report
        
        # 4. Calcola le stime economiche e aggiorna il summary
        n_clauses = len(gemini_report.get("clauses", []))
        estimated_costs = estimate_cost(n_clauses)
        gemini_report["summary"].update(estimated_costs)
        
        # 5. Salva il report nel database
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()
        cur.execute(
            "INSERT INTO documents (document_id, status, report_data) VALUES (%s, %s, %s)",
            (document_id, "ready", json.dumps(gemini_report))
        )
        conn.commit()
        
        print("Report salvato nel database con successo.")
        
        # 6. Restituisci il report completo
        return gemini_report

    except (Exception, psycopg2.DatabaseError) as e:
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"Errore nel salvataggio o nell'analisi del file: {e}")
    finally:
        if conn:
            cur.close()
            conn.close()