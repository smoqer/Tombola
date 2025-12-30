import streamlit as st
import random
import time
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- LISTA LITFIBA (Per Audio Italiano) ---
LITFIBA_HITS = [
    "Eroi nel vento", "El Diablo", "Tex", "Lulù e Marlene", 
    "Gioconda", "Cane", "Fata Morgana", "Maudit", 
    "Il volo", "Re del silenzio", "Cangaceiro", "Spirito", 
    "Regina di Cuori", "Lacio Drom", "La Paura", "Proibito", 
    "Apapaia", "Paname", "Louisiana", "Vivere il mio tempo",
    "Dimmi il nome", "Sotto il vulcano", "Ritmo 2", "Istanbul"
]

# --- IMPORT SMORFIA DA FILE ESTERNO ---
try:
    from smorfia_dati import SMORFIA
except ImportError:
    SMORFIA = {} 

# --- COSTANTI ECONOMICHE ---
COSTO_CARTELLA = 5
QUOTE = {
    2: 0.12, 3: 0.18, 4: 0.20, 5: 0.20, 15: 0.30
}

# --- CONFIGURAZIONE PAGINA E STILE ROCK ---
st.set_page_config(page_title="TombolaRock", layout="wide", page_icon="🤟")

st.markdown("""
    <style>
        .stApp { background-color: #ffffff; color: #000000; }
        input, .stTextInput > div > div > input { color: #000000 !important; background-color: #ffffff !important; }
        section[data-testid="stSidebar"] { background-color: #f0f2f6; }
        p, h1, h2, h3, h4, h5, h6, li, span, div { color: #2c3e50; }
        .c-cell, .cell-tab { color: #000000; }
        
        .rock-title { 
            color: #d63031; font-weight: 900; text-align: center; text-transform: uppercase; 
            font-family: 'Arial Black', sans-serif; text-shadow: 2px 2px 0px #000000;
        }
        .rule-box {
            background-color: #ecf0f1; padding: 20px; border-radius: 10px; 
            border-left: 5px solid #d63031; margin-bottom: 10px;
        }
        .win-title { color: #2ecc71; font-weight: bold; }
        .money-box {
            background-color: #ffeaa7; border: 2px solid #fdcb6e; 
            padding: 10px; border-radius: 8px; text-align: center; margin-bottom: 10px;
        }
        .money-val { font-size: 20px; font-weight: bold; color: #d35400; }
        .player-row { padding: 5px; border-bottom: 1px solid #ddd; font-size: 14px; }
        .winner-badge { color: #27ae60; font-weight: bold; background: #eafaf1; padding: 2px 5px; border-radius: 4px; }
        .prize-row { font-size: 14px; margin-bottom: 3px; }
        
        /* Stile Lobby */
        .lobby-box {
            text-align: center; padding: 40px; background-color: #2c3e50; color: white;
            border-radius: 15px; margin-top: 20px;
        }
        
        /* Titolo Canzone Grande */
        .song-title {
            font-size: 30px; font-weight: bold; color: #f1c40f; 
            margin-top: 10px; font-style: italic; text-shadow: 1px 1px 0 #000;
        }
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
        if result: return json.loads(result['dati_partita'])
        return None
    except Error as e:
        st.error(f"Errore connessione DB: {e}")
        return None
    finally:
        if conn and conn.is_connected(): conn.close()

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
        if conn and conn.is_connected(): conn.close()

def delete_stanza_db(nome_stanza):
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        query = "DELETE FROM stanze_tombola WHERE nome_stanza = %s"
        cursor.execute(query, (nome_stanza,))
        conn.commit()
    except Error as e:
        st.error(f"Errore cancellazione DB: {e}")
    finally:
        if conn and conn.is_connected(): conn.close()

# --- SMORFIA LOOKUP ---
def get_smorfia_text(num):
    return SMORFIA.get(int(num), "Rock n Roll")

# --- AUDIO JS AVANZATO ---
def speak_js(text_sequence):
    if not text_sequence: return
    
    parts = text_sequence.split("||")
    js_logic = "window.speechSynthesis.cancel();"
    
    for part in parts:
        clean_text = part.replace("'", "\\'").strip()
        if not clean_text: continue
        
        lang = 'en-GB' 
        lower_txt = clean_text.lower()
        
        if clean_text.isdigit():
            lang = 'it-IT'
        elif any(x in lower_txt for x in ["attenzione", "ambo", "terno", "quaterna", "cinquina", "tombola", "vinto"]):
            lang = 'it-IT'
        elif any(hit.lower() in lower_txt for hit in LITFIBA_HITS):
            lang = 'it-IT'
            
        js_logic += f"""
        var u = new SpeechSynthesisUtterance('{clean_text}');
        u.lang = '{lang}';
        u.rate = 1.0;
        window.speechSynthesis.speak(u);
        """
    
    u_id = int(time.time() * 1000)
    js = f"""<div style="display:none" id="audio_{u_id}"></div><script>(function(){{{js_logic}}})();</script>"""
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

# --- CALCOLO MONTEPREMI ---
def get_info_economiche(dati_stanza):
    tot_cartelle = sum(len(c) for c in dati_stanza["giocatori"].values())
    montepremi = tot_cartelle * COSTO_CARTELLA
    premi_valore = {
        2: round(montepremi * QUOTE[2]),
        3: round(montepremi * QUOTE[3]),
        4: round(montepremi * QUOTE[4]),
        5: round(montepremi * QUOTE[5]),
        15: round(montepremi * QUOTE[15])
    }
    return tot_cartelle, montepremi, premi_valore

# --- CONTROLLO VINCITE ---
def controlla_vincite(dati_stanza):
    target = dati_stanza.get("obbiettivo_corrente", 2)
    estratti = set(dati_stanza["numeri_estratti"])
    nomi_premi = {2: "AMBO", 3: "TERNO", 4: "QUATERNA", 5: "CINQUINA", 15: "TOMBOLA"}
    nome_premio = nomi_premi.get(target, "TOMBOLA")
    
    _, _, valori_premi = get_info_economiche(dati_stanza)
    valore_totale_premio = valori_premi.get(target, 0)
    
    vincitori_round = []
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
        quota_cadauno = int(valore_totale_premio / len(vincitori_round)) if len(vincitori_round) > 0 else 0
        if "classifica_vincite" not in dati_stanza: dati_stanza["classifica_vincite"] = {}
        for vincitore in vincitori_round:
            vecchio_saldo = dati_stanza["classifica_vincite"].get(vincitore, 0)
            dati_stanza["classifica_vincite"][vincitore] = vecchio_saldo + quota_cadauno

        testo = ", ".join(vincitori_round)
        msg = f"Attenzione! {nome_premio} ({valore_totale_premio} totali) per {testo}!"
        
        if msg not in dati_stanza.get("messaggio_audio", ""):
            dati_stanza["messaggio_audio"] += f" || {msg}"
            dati_stanza["messaggio_toast"] = f"🏆 {msg} (+{quota_cadauno} cad.)"
            nuova_vincita_trovata = True
        
        if target < 5: dati_stanza["obbiettivo_corrente"] += 1
        elif target == 5: dati_stanza["obbiettivo_corrente"] = 15
        else: 
            dati_stanza["messaggio_audio"] += " || Gioco Finito!"
            dati_stanza["gioco_finito"] = True
            nuova_vincita_trovata = True

    return dati_stanza, nuova_vincita_trovata

# --- INTERFACCIA ---
st.markdown("<h1 class='rock-title'>🤟 TOMBOLA ROCK 🤟</h1>", unsafe_allow_html=True)
menu = st.sidebar.radio("Menu", ["🏠 Home", "🆕 Crea Stanza (Admin)", "🎮 Entra in Stanza"])

if menu == "🏠 Home":
    st.markdown("### Benvenuti alla Tombola più Rock del Web! 🎸")
    st.markdown(f"""
    <div class='rule-box'>
        <h3>📜 REGOLAMENTO</h3>
        <p>Costo Cartella: <b>{COSTO_CARTELLA} gettoni</b>.</p>
        <p>I giocatori possono entrare in <b>LOBBY</b> finché l'Admin non dà il via al concerto.</p>
    </div>
