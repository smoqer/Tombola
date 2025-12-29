import streamlit as st
import random
import time
import base64
from gtts import gTTS
from io import BytesIO

# Importiamo la Smorfia (assicurati che il file smorfia_dati.py sia presente)
try:
    from smorfia_dati import SMORFIA
except ImportError:
    SMORFIA = {}

# --- FUNZIONI DI SUPPORTO ---

def autoplay_audio(text):
    """Genera audio e lo riproduce automaticamente nel browser"""
    if not text: return
    try:
        sound_file = BytesIO()
        tts = gTTS(text, lang='it')
        tts.write_to_fp(sound_file)
        
        # Convertiamo l'audio in stringa base64 per HTML
        b64 = base64.b64encode(sound_file.getvalue()).decode()
        md = f"""
            <audio autoplay>
            <source src="data:audio/mp3;base64,{b64}" type="audio/mp3">
            </audio>
            """
        st.markdown(md, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Errore audio: {e}")

def get_smorfia_text(num):
    return SMORFIA.get(num, "...")

# --- SETUP STATO DEL GIOCO (MEMORIA) ---
if 'numeri_tabellone' not in st.session_state:
    nums = list(range(1, 91))
    random.shuffle(nums)
    st.session_state.numeri_tabellone = nums
    st.session_state.numeri_estratti = []
    st.session_state.ultimo_numero = None
    st.session_state.messaggio_audio = ""

# --- INTERFACCIA GRAFICA ---

st.set_page_config(page_title="Tombola Web", layout="wide")

st.title("🎄 TOMBOLA DI NATALE ONLINE 🎄")

# Layout: Colonna Sinistra (Comandi/Ultimo Num) - Colonna Destra (Tabellone)
col_comandi, col_tabellone = st.columns([1, 2])

with col_comandi:
    st.write("### Estrazione")
    
    # Bottone Estrai
    remaining = len(st.session_state.numeri_tabellone)
    if remaining > 0:
        if st.button("ESTRAI NUMERO", type="primary", use_container_width=True):
            # Logica estrazione
            numero = st.session_state.numeri_tabellone.pop(0)
            st.session_state.numeri_estratti.append(numero)
            st.session_state.ultimo_numero = numero
            
            # Preparazione Audio e Testo
            testo_smorfia = get_smorfia_text(numero)
            st.session_state.messaggio_audio = f"{numero}. {testo_smorfia}"
            
            # Forza il ricaricamento per aggiornare la UI
            st.rerun()
    else:
        st.success("Tutti i numeri estratti!")
        if st.button("Ricomincia Partita"):
            st.session_state.clear()
            st.rerun()

    st.divider()

    # Visualizzazione Ultimo Numero Gigante
    if st.session_state.ultimo_numero:
        num = st.session_state.ultimo_numero
        smorfia = get_smorfia_text(num)
        
        st.markdown(f"""
        <div style="text-align: center;">
            <span style="font-size: 120px; font-weight: bold; color: #d63031;">{num}</span>
            <br>
            <span style="font-size: 24px; color: #0984e3;">{smorfia}</span>
        </div>
        """, unsafe_allow_html=True)
        
        # Riproduzione Audio (Solo se c'è un messaggio nuovo)
        if st.session_state.messaggio_audio:
            autoplay_audio(st.session_state.messaggio_audio)
            st.session_state.messaggio_audio = "" # Pulisce per non ripeterlo al refresh

    else:
        st.info("Premi ESTRAI per iniziare")

with col_tabellone:
    st.write("### Tabellone")
    
    # CSS per creare la griglia del tabellone
    st.markdown("""
    <style>
    .tombola-grid {
        display: grid;
        grid-template-columns: repeat(10, 1fr);
        gap: 5px;
    }
    .tombola-cell {
        border: 1px solid #ddd;
        border-radius: 5px;
        text-align: center;
        padding: 10px;
        font-weight: bold;
        font-size: 18px;
    }
    .extracted {
        background-color: #e74c3c;
        color: white;
    }
    .missing {
        background-color: #f1f2f6;
        color: #b2bec3;
    }
    </style>
    """, unsafe_allow_html=True)

    # Generazione HTML del tabellone
    html_board = '<div class="tombola-grid">'
    for i in range(1, 91):
        css_class = "extracted" if i in st.session_state.numeri_estratti else "missing"
        html_board += f'<div class="tombola-cell {css_class}">{i}</div>'
    html_board += '</div>'
    
    st.markdown(html_board, unsafe_allow_html=True)

# --- SEZIONE CARTELLE GENERATE (Opzionale) ---
st.divider()
with st.expander("Genera Cartelle per Giocatori (Da stampare o screenshottare)"):
    num_cartelle = st.slider("Quante cartelle vuoi generare?", 1, 6, 1)
    if st.button("Genera Cartelle"):
        # Qui potresti reinserire la tua logica GeneratoreCartelle
        # Per ora metto un placeholder
        st.write(f"Ecco {num_cartelle} cartelle simulate...")
        # (Qui andrebbe integrato GeneratoreCartelle.genera_matrice_3x9)
