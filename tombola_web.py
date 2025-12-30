import streamlit as st
import random
import time
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- CONFIGURAZIONE PAGINA E CSS FIX ---
st.set_page_config(page_title="Tombola Online MySQL", layout="wide", page_icon="🎄")

# Fix per colori su Android/Chrome Dark Mode
st.markdown("""
    <style>
        .stApp { background-color: #ffffff; color: #000000; }
        input, .stTextInput > div > div > input { color: #000000 !important; background-color: #ffffff !important; }
        section[data-testid="stSidebar"] { background-color: #f0f2f6; }
        p, h1, h2, h3, h4, h5, h6, li, span, div { color: #2c3e50; }
        .c-cell, .cell-tab { color: #000000; }
        /* Stile messaggi di errore/successo */
        .stAlert { color: #000000; }
    </style>
""", unsafe_allow_html=True)

# --- GESTIONE DATABASE MYSQL ---
def get_connection():
    if "mysql" not in st.secrets:
        st.error("Manca la configurazione [mysql] in .streamlit/secrets.toml")
        st.stop()
        
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=st.secrets["mysql"].get("port", 3306)
    )

def load_stanza_db(nome_stanza):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT dati_partita FROM stanze_tombola WHERE nome_stanza = %s"
        cursor.execute(query, (nome_stanza,))
        result = cursor.fetchone()
        
        if result:
            return json.loads(result['dati_partita'])
        return None
    except Error as e:
        st.error(f"Errore connessione DB: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()

def save_stanza_db(nome_stanza, dati_dizionario):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        json_data = json.dumps(dati_dizionario)
        query = """
        INSERT INTO stanze_tombola (nome_stanza, dati_partita)
        VALUES (%s, %s)
        ON DUPLICATE KEY UPDATE dati_partita = %s
        """
        cursor.execute(query, (nome_stanza, json_data, json_data))
        conn.commit()
    except Error as e:
        st.error(f"Errore salvataggio DB: {e}")
    finally:
        if conn and conn.is_connected():
            conn.close()

# --- IMPORT SMORFIA ---
try:
    from smorfia_dati import SMORFIA
except ImportError:
    SMORFIA = {}

def get_smorfia_text(num):
    return SMORFIA.get(num, "...")

# --- FUNZIONI AUDIO (JS) ---
def speak_js(text):
    if not text: return
    text_safe = text.replace("'", "\\'").replace('"', '\\"')
    u_id = int(time.time() * 1000)
    js = f"""
        <div style="display:none" id="audio_{u_id}"></div>
        <script>
            (function() {{
                window.speechSynthesis.cancel();
                var msg = new SpeechSynthesisUtterance('{text_safe}');
                msg.lang = 'it-IT';
                window.speechSynthesis.speak(msg);
            }})();
        </script>
    """
    st.components.v1.html(js, height=0, width=0)

# --- GENERATORE CARTELLE ---
class GeneratoreCartelle:
    @staticmethod
    def genera_matrice_3x9():
        matrice = [[0] * 9 for _ in range(3)]
        numeri_usati = set()
        range_colonne = [(1, 10), (10, 20), (20, 30), (30, 40), (40, 50), (50, 60), (60, 70), (70, 80), (80, 91)]
        for r in range(3):
            colonne_scelte = random.sample(range(9), 5)
            colonne_scelte.sort()
            for c in colonne_scelte:
                start, end = range_colonne[c]
                while True:
                    num = random.randint(start, end - 1)
                    if num not in numeri_usati:
                        matrice[r][c] = num
                        numeri_usati.add(num)
                        break
        for c in range(9):
            col_nums, row_indices = [], []
            for r in range(3):
                if matrice[r][c] != 0:
                    col_nums.append(matrice[r][c])
                    row_indices.append(r)
            col_nums.sort()
            for i, r_idx in enumerate(row_indices):
                matrice[r_idx][c] = col_nums[i]
        return matrice

# --- CONTROLLO VINCITE ---
def controlla_vincite(dati_stanza):
    """
    Ritorna una tupla: (dati_aggiornati, vincita_avvenuta_bool)
    """
    target = dati_stanza.get("obbiettivo_corrente", 2)
    estratti = set(dati_stanza["numeri_estratti"])
    nomi_premi = {2: "AMBO", 3: "TERNO", 4: "QUATERNA", 5: "CINQUINA", 15: "TOMBOLA"}
    nome_premio = nomi_premi.get(target, "TOMBOLA")
    vincitori_round = []
    
    # Flag per sapere se in QUESTO controllo abbiamo trovato una nuova vincita
    nuova_vincita_trovata = False

    for nome_g, cartelle in dati_stanza["giocatori"].items():
        for cartella in cartelle:
            punti_tot = 0
            win = False
            for riga in cartella:
                punti_riga = sum(1 for n in riga if n > 0 and n in estratti)
                punti_tot += punti_riga
                if target <= 5 and punti_riga >= target: win = True
            if target == 15 and punti_tot == 15: win = True
            if win and nome_g not in vincitori_round: vincitori_round.append(nome_g)

    if vincitori_round:
        testo = ", ".join(vincitori_round)
        msg = f"Attenzione! {nome_premio} per {testo}!"
        
        # Evitiamo di ripetere l'audio se è lo stesso messaggio
        if msg not in dati_stanza.get("messaggio_audio", ""):
            dati_stanza["messaggio_audio"] += f" ... {msg}"
            dati_stanza["messaggio_toast"] = f"🏆 {msg}"
            nuova_vincita_trovata = True # Segnaliamo che c'è stata una vincita
        
        # Avanzamento obiettivo
        if target < 5: dati_stanza["obbiettivo_corrente"] += 1
        elif target == 5: dati_stanza["obbiettivo_corrente"] = 15
        else: 
            dati_stanza["messaggio_audio"] += " ... Gioco Finito!"
            dati_stanza["gioco_finito"] = True
            nuova_vincita_trovata = True

    return dati_stanza, nuova_vincita_trovata

# --- INTERFACCIA ---
st.title("🌍 TOMBOLA ONLINE MULTIPLAYER")
menu = st.sidebar.radio("Menu", ["🏠 Home", "🆕 Crea Stanza (Admin)", "🎮 Entra in Stanza"])

# --- AGGIUNTA QR CODE IN SIDEBAR ---
import qrcode
from io import BytesIO
from PIL import Image
with st.sidebar:
    st.divider()
    st.markdown("### 📲 Invita Amici")
    # Nota: Sostituisci questo link con il tuo link reale
    link_app = "https://share.streamlit.io" 
    qr = qrcode.QRCode(box_size=10, border=4)
    qr.add_data(link_app)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    img.save(buffer, format="PNG")
    st.image(buffer, caption="Scansiona per entrare!", use_container_width=True)

if menu == "🏠 Home":
    st.markdown("### Benvenuto! I dati sono su MySQL. Connessione multi-utente stabile.")

elif menu == "🆕 Crea Stanza (Admin)":
    st.header("Impostazioni Banco (Admin)")
    st.info("L'Admin gestisce l'estrazione ma non possiede cartelle di gioco.")
    
    with st.form("crea"):
        nome = st.text_input("Nome Stanza", max_chars=15).upper().strip()
        pwd = st.text_input("Password Admin", type="password")
        # MODIFICA 3: Rimosso checkbox "Banco gioca"
        
        if st.form_submit_button("Crea Stanza"):
            if not nome or not pwd: st.error("Dati mancanti.")
            else:
                exist = load_stanza_db(nome)
                if exist: st.warning("Sovrascritta stanza esistente.")
                numeri = list(range(1, 91)); random.shuffle(numeri)
                dati = {
                    "admin_pwd": pwd, "created_at": str(datetime.now()),
                    "numeri_tabellone": numeri, "numeri_estratti": [],
                    "ultimo_numero": None, "messaggio_audio": "", "messaggio_toast": "",
                    "giocatori": {}, "obbiettivo_corrente": 2, "gioco_finito": False
                }
                # Nessun giocatore Banco aggiunto qui
                save_stanza_db(nome, dati)
                
                st.session_state.ruolo = "ADMIN"
                st.session_state.stanza_corrente = nome
                st.session_state.nome_giocatore = "ADMIN"
                st.rerun()

elif menu == "🎮 Entra in Stanza":
    if 'stanza_corrente' not in st.session_state:
        c1, c2 = st.columns(2)
        inp_stanza = c1.text_input("Nome Stanza").upper().strip()
        inp_nome = c2.text_input("Il tuo Nome").strip().upper()
        
        is_admin = st.checkbox("Sono l'Admin (Banco)")
        pwd_in = st.text_input("Password", type="password") if is_admin else ""
        n_cart = st.slider("Cartelle", 1, 6, 1)
        
        if st.button("ENTRA"):
            d = load_stanza_db(inp_stanza)
            if not d: st.error("Stanza non trovata.")
            else:
                if is_admin:
                    if pwd_in == d["admin_pwd"]:
                        st.session_state.ruolo = "ADMIN"
                        st.session_state.stanza_corrente = inp_stanza
                        st.session_state.nome_giocatore = "ADMIN"
                        st.rerun()
                    else: st.error("Password errata.")
                else:
                    if inp_nome:
                        # MODIFICA 1: Controllo Nomi Univoci
                        if inp_nome in d["giocatori"]:
                            st.error(f"Il nome '{inp_nome}' è già usato in questa stanza. Scegline un altro.")
                        else:
                            if len(d["giocatori"]) >= 20: st.error("Stanza piena.")
                            else:
                                d["giocatori"][inp_nome] = [GeneratoreCartelle.genera_matrice_3x9() for _ in range(n_cart)]
                                save_stanza_db(inp_stanza, d)
                                st.session_state.ruolo = "PLAYER"
                                st.session_state.stanza_corrente = inp_stanza
                                st.session_state.nome_giocatore = inp_nome
                                st.rerun()
                    else: st.error("Inserisci nome.")
    else:
        # --- PARTITA IN CORSO ---
        stanza = st.session_state.stanza_corrente
        ruolo = st.session_state.ruolo
        mio_nome = st.session_state.nome_giocatore
        dati = load_stanza_db(stanza)
        
        if not dati:
            st.error("Errore connessione."); st.stop()

        # LISTA PARTECIPANTI
        with st.sidebar:
            st.divider()
            lista_giocatori = list(dati["giocatori"].keys())
            st.markdown(f"### 👥 Partecipanti ({len(lista_giocatori)})")
            lista_ordinata = sorted(lista_giocatori)
            for g in lista_ordinata:
                n_c = len(dati["giocatori"][g])
                icona = "👤"
                if g == mio_nome: st.markdown(f"👉 **{icona} {g}** ({n_c})")
                else: st.markdown(f"{icona} {g} ({n_c})")
            st.divider()

        # LOGICA GIOCO
        estratti = dati["numeri
