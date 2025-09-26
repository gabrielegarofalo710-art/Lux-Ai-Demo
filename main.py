import shutil
import uuid
import json
import os # Importato per leggere le variabili d'ambiente
from pathlib import Path

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import pdfplumber

# --- PARTE MODIFICATA: Non importiamo più 'config' e 'psycopg2' ---
import google.generativeai as genai
# import psycopg2 
# from config import DB_CONFIG, GEMINI_API_KEY # Rimosso l'import di config

# --- RECUPERO LA CHIAVE API DALLA VARIABILE D'AMBIENTE DI VERCEL ---
# Uso os.getenv per leggere la variabile che hai impostato su Vercel
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY") 
if not GEMINI_API_KEY:
    # Se la chiave non c'è, blocca l'avvio o usa una chiave di placeholder (meno sicuro, meglio bloccare)
    print("ERRORE: La variabile d'ambiente GEMINI_API_KEY non è impostata!") 
    # Non solleviamo un errore qui per non bloccare l'app, ma fallirà dopo
# --- FINE PARTE MODIFICATA ---


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
UPLOAD_DIR = Path("/tmp/uploads") # Usiamo /tmp su Vercel/Railway per i file temporanei
UPLOAD_DIR.mkdir(exist_ok=True)

# Configura l'API di Google Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- Funzioni di Analisi con Gemini (CODICE NON MODIFICATO) ---
def extract_text_from_pdf(pdf_path: str) -> str:
    # ... [Tutto il codice di extract_text_from_pdf rimane invariato] ...
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
    # ... [Tutto il codice di analyze_with_gemini rimane invariato, compreso il prompt] ...
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
    # ... [Tutto il codice di estimate_cost rimane invariato] ...
    tempo_medio_per_clausola = 15
    tempo_attuale = n_clauses * tempo_medio_per_clausola
    tempo_ridotto = tempo_attuale * (1 - efficacia)
    tempo_risparmiato = tempo_attuale - tempo_ridotto
    costo_risparmiato = (tempo_risparmiato / 60) * tariffa_oraria
    return {
        "tempo_risparmiato_min": int(tempo_risparmiato),
        "costo_risparmiato_eur": round(costo_risparmiato, 2)
    }

# --- Endpoint API (PARTE MODIFICATA) ---

@app.post("/api/v1/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Endpoint per caricare un documento PDF e analizzarlo con Google Gemini.
    """
    conn = None
    file_path = None # Definiamo file_path qui per poterlo eliminare nella finally
    
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
        
        # --- PARTE COMMENTATA: NON SALVARE NEL DB SU VERCEL ---
        # conn = psycopg2.connect(**DB_CONFIG)
        # cur = conn.cursor()
        # cur.execute(
        #     "INSERT INTO documents (document_id, status, report_data) VALUES (%s, %s, %s)",
        #     (document_id, "ready", json.dumps(gemini_report))
        # )
        # conn.commit()
        # print("Report salvato nel database con successo.")
        # --- FINE PARTE COMMENTATA ---
        
        # 5. Restituisci il report completo
        return gemini_report

    except Exception as e:
        # Se c'è un errore, gestiamo l'eccezione generale
        raise HTTPException(status_code=500, detail=f"Errore generale: {e}")
    
    finally:
        # Pulisci il file PDF temporaneo
        if file_path and file_path.exists():
            os.remove(file_path) # Assicurati di importare 'os' in cima al file!