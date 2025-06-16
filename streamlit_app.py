import streamlit as st
from openai import OpenAI
import fitz  # PyMuPDF per estrarre testo dal PDF
import pandas as pd  # Per leggere file Excel
import os
import tempfile
import sys

# Inietta CSS per personalizzare il colore delle icone nella chat
st.markdown(
    """
    <style>
      /* Icona utente (umano) */
      [data-testid="stHorizontalBlock"] [data-testid="stAvatar"][aria-label="user avatar"] svg path {
        fill: #4CAF50 !important;  /* utente */
      }
      /* Icona assistente (robot) */
      [data-testid="stHorizontalBlock"] [data-testid="stAvatar"][aria-label="assistant avatar"] svg path {
        fill: #00a1df !important;  /* robot */
      }

      .st-emotion-cache-16tyu1 h1 {
        font-size: 2.50rem !important;
      }
    </style>
    """,
    unsafe_allow_html=True
)

# Controllo autenticazione
if 'authenticated' not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.title("🔒 Accesso a Landini ARBO BOT")
    password = st.text_input("Inserisci la password per accedere:", type="password")
    
    if st.button("Accedi"):
        if password == st.secrets["pw"]:
            st.session_state.authenticated = True
            st.rerun()
        else:
            st.error("Password errata. Riprova.")
    
    st.stop()  # Ferma l'esecuzione del resto del codice finché non autenticati

# Imposta la lingua italiana per tutta l'app
def set_italian_locale():
    import locale
    try:
        locale.setlocale(locale.LC_ALL, 'it_IT.UTF-8')
    except:
        pass
set_italian_locale()

# Configura il client OpenAI con l'API Key
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Configura lo stato della sessione
if "chats" not in st.session_state:
    st.session_state.chats = []  # Lista per memorizzare le chat
if "selected_chat" not in st.session_state:
    st.session_state.selected_chat = None  # Chat selezionata
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""  # Testo estratto dal PDF
if "tone_of_voice" not in st.session_state:
    st.session_state.tone_of_voice = "Rispondi in modo sintetico, chiaro e professionale."  # Prompt predefinito
if "show_tone_settings" not in st.session_state:
    st.session_state.show_tone_settings = False  # Controllo per mostrare il box di impostazione del tone of voice
if "tone_of_voice" not in st.session_state:
    # Imposta il valore predefinito come costante separata
    DEFAULT_TONE = "Rispondi in modo sintetico, chiaro e professionale."
    st.session_state.tone_of_voice = DEFAULT_TONE
if "messages" not in st.session_state:
    st.session_state.messages = []  # Memorizza la chat corrente

# Se non esiste alcuna conversazione, ne creo una ed apro la prima
if not st.session_state.chats:
    st.session_state.chats.append({"id": "Conversazione 1", "messages": []})
if not st.session_state.selected_chat:
    st.session_state.selected_chat = st.session_state.chats[0]["id"]

# Mostra il logo dell'app
st.image("media/mida_logo_1000.png", width=350)
# st.image("media/landini_logo_web.png", width=350)

# Funzione per estrarre testo dal PDF
def extract_text_from_pdf(pdf_path):
    doc = fitz.open(pdf_path)
    text = "\n".join([page.get_text() for page in doc])
    return text

# Selezione automatica del PDF di default dalla cartella media
media_dir = "media"
available_pdfs = [f for f in os.listdir(media_dir) if f.lower().endswith(".pdf")]
default_pdf = None
if available_pdfs:
    default_pdf = available_pdfs[0]

# Carica un documento (PDF o Excel) dalla sidebar
if default_pdf:
    # Se non viene caricato nulla dall'utente, uso il PDF di default
    default_path = os.path.join(media_dir, default_pdf)
    st.session_state.pdf_text = extract_text_from_pdf(default_path)
    st.sidebar.info(f"PDF pre-caricato: '{default_pdf}'")
else:
    uploaded_file = st.sidebar.file_uploader("📄 Carica il documento da memorizzare", type=["pdf", "xlsx", "xls"])
    if uploaded_file:
        file_ext = uploaded_file.name.split('.')[-1].lower()
        if file_ext == "pdf":
            # Salva il file temporaneamente e ne estrae il testo
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
                temp_file.write(uploaded_file.read())
                temp_pdf_path = temp_file.name
            st.session_state.pdf_text = extract_text_from_pdf(temp_pdf_path)
            st.sidebar.success("PDF caricato e analizzato con successo!")
        elif file_ext in ["xlsx", "xls"]:
            # Usa Pandas per leggere il file Excel e convertirlo in una stringa
            df = pd.read_excel(uploaded_file)
            # Pulizia avanzata del DataFrame
            cleaned_data = (
                df.fillna('')  # Sostituisce i NaN con stringhe vuote
                .applymap(lambda x: str(x).strip() if pd.notnull(x) else '')  # Rimuove spazi extra e converte a stringa
                .replace(r'^\s*$', '', regex=True)  # Sostituisce celle vuote/whitespace con stringa vuota
            )
            # Generazione testo compatto
            excel_text = "\n".join(
                "|".join(row) 
                for row in cleaned_data.astype(str).values
                if any(field.strip() for field in row)
            )
            st.session_state.pdf_text = excel_text
            st.sidebar.success("Excel caricato e analizzato con successo!")

#st.warning(sys.getsizeof(st.session_state.pdf_text), icon="⚠️")

# Visualizza le chat esistenti nella sidebar
st.sidebar.title("Gestione conversazioni")
if st.sidebar.button("➕ Nuova Conversazione"):
    chat_id = f"Conversazione {len(st.session_state.chats) + 1}"
    st.session_state.chats.append({"id": chat_id, "messages": []})
    st.session_state.selected_chat = chat_id

for chat in st.session_state.chats:
    if st.sidebar.button(chat["id"]):
        st.session_state.selected_chat = chat["id"]

# Pulsante per mostrare/nascondere le impostazioni del tone of voice
if st.sidebar.button("⚙️ Imposta Tone of Voice"):
    st.session_state.show_tone_settings = not st.session_state.show_tone_settings

# Modifica nella sezione delle impostazioni del tone of voice
if st.session_state.show_tone_settings:
    # Usa value per mantenere esplicitamente lo stato corrente
    new_tone = st.sidebar.text_area(
        "Modifica il tone of voice:",
        value=st.session_state.tone_of_voice,
        key="tone_input",
        help="Il tone of voice verrà applicato a tutte le nuove risposte"
    )
    # Pulsanti per gestire il reset
    col1, col2 = st.sidebar.columns(2)
    if col1.button("💾 Salva modifiche"):
        st.session_state.tone_of_voice = new_tone
    if col2.button("↩️ Ripristina default"):
        st.session_state.tone_of_voice = DEFAULT_TONE

# Visualizza la chat
st.title("🤖 Chiedi a ARGOBOT tutto sul REX 4")
if not st.session_state.selected_chat:
    st.write("Seleziona una conversazione o creane una nuova dalla barra laterale.")
else:
    chat_data = next(c for c in st.session_state.chats if c["id"] == st.session_state.selected_chat)
    
    # Visualizza i messaggi esistenti
    for message in chat_data["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Input per l'utente
    if user_input := st.chat_input("Fai una domanda sul tuo PDF"):
        # Aggiungi e visualizza il messaggio dell'utente
        chat_data["messages"].append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)

        # Prepara i messaggi per la chiamata all'API
        messages_for_api = []
        # Se è stato caricato un PDF, includi il suo contenuto come contesto
        if st.session_state.pdf_text:
            messages_for_api.append({
                "role": "system",
                "content": f"Utilizza il seguente testo del PDF come contesto per rispondere alle domande:\n\n{st.session_state.pdf_text}\n\n"
            })
        # Aggiungi il tone of voice come indicazione per lo stile delle risposte
        if st.session_state.tone_of_voice:
            messages_for_api.append({
                "role": "system",
                #"content": f"Mantieni questo tone of voice nelle risposte: {st.session_state.tone_of_voice}\n\n"
                "content": f"ISTRUZIONE PRIORITARIA: {st.session_state.tone_of_voice}"
            })
        # Aggiungi i messaggi della conversazione
        messages_for_api.extend([{"role": m["role"], "content": m["content"]} for m in chat_data["messages"]])
        
        # Genera la risposta in streaming
        #st.warning(messages_for_api, icon="⚠️")
        with st.chat_message("assistant"):
            response = st.write_stream(
                client.chat.completions.create(
                    model="gpt-4o",
                    messages=messages_for_api,
                    stream=True,
                )
            )
        # Aggiungi la risposta generata alla conversazione
        chat_data["messages"].append({"role": "assistant", "content": response})