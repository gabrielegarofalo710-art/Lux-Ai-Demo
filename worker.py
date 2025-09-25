import pdfplumber
import spacy

# Carica il modello linguistico di spaCy per l'italiano
try:
    nlp = spacy.load("it_core_news_sm")
except OSError:
    print("Modello spaCy 'it_core_news_sm' non trovato. Eseguire 'py -m spacy download it_core_news_sm'")
    exit()

# Le parole chiave che hai definito
KEYWORDS = ["garanzia", "responsabilità", "indennizzo", "penale", "risoluzione", "limite di responsabilità", "compenso", "recesso", "penalità", "forza maggiore", "confidenzialità"]

# Esempio di regole di scoring di rischio
RISK_RULES = {
    "HIGH": ["illimitato", "senza limiti", "nessuna responsabilità per", "penale X%"],
    "MEDIUM": ["limitazioni forti", "obblighi onerosi"],
    "LOW": [] # Le clausole standard
}

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

def find_clauses(text: str) -> list:
    """
    Identifica le clausole basate su parole chiave e le segmenta.
    """
    clauses = []
    doc = nlp(text)
    
    # Segmentazione per frasi
    for sentence in doc.sents:
        sentence_text = sentence.text.strip()
        # Controlla se la frase contiene una delle parole chiave
        if any(keyword in sentence_text.lower() for keyword in KEYWORDS):
            # Aggiunge la frase come clausola se è abbastanza lunga
            if len(sentence_text.split()) > 6:
                clauses.append({"text": sentence_text})
    
    return clauses

def score_clause(clause_text: str) -> str:
    """
    Applica le regole per assegnare un livello di rischio (LOW, MEDIUM, HIGH).
    """
    clause_text_lower = clause_text.lower()
    
    # Regole per rischio ALTO
    for rule in RISK_RULES["HIGH"]:
        if rule in clause_text_lower:
            return "HIGH"
    
    # Regole per rischio MEDIO
    for rule in RISK_RULES["MEDIUM"]:
        if rule in clause_text_lower:
            return "MEDIUM"
            
    return "LOW"

# --- Parte di Esecuzione ---
# Ricorda di avviare lo script con il comando: py worker.py

# Specifica il nome del file da analizzare
pdf_file_path = "uploads/finta_clausola.pdf" 

extracted_text = extract_text_from_pdf(pdf_file_path)

if extracted_text:
    print("Testo estratto con successo. Ora analizzo le clausole.")
    
    identified_clauses = find_clauses(extracted_text)
    
    if not identified_clauses:
        print("Nessuna clausola legale identificata in questo documento.")
    else:
        print(f"Trovate {len(identified_clauses)} possibili clausole legali.")
        
        final_report_clauses = []
        
        for clause in identified_clauses:
            risk_level = score_clause(clause["text"])
            final_report_clauses.append({
                "text": clause["text"],
                "risk": risk_level
            })

        # Stampa i risultati
        print("\n--- REPORT CLAUSOLE ---")
        for i, clause in enumerate(final_report_clauses):
            print(f"Clausola {i+1}:")
            print(f"Testo: {clause['text'][:100]}...")
            print(f"Rischio: {clause['risk']}\n")
else:
    print("Impossibile procedere con l'analisi. Errore nell'estrazione del testo.")