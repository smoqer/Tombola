import streamlit as st
import random
import time
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

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
        .winner-badge { color: #e1b12c; font-weight: bold; }
        
        /* Stile Lobby */
        .lobby-box {
            text-align: center; padding: 40px; background-color: #2c3e50; color: white;
            border-radius: 15px; margin-top: 20px;
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
    """Cancella fisicamente la stanza dal DB (Logout Admin)"""
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

# --- IMPORT SMORFIA ---
try: from smorfia_dati import SMORFIA
except ImportError: SMORFIA = {}
def get_smorfia_text(num): return SMORFIA.get(num, "...")

# --- AUDIO JS ---
def speak_js(text):
    if not text: return
    text_safe = text.replace("'", "\\'").replace('"', '\\"')
    u_id = int(time.time() * 1000)
    js = f"""<div style="display:none" id="audio_{u_id}"></div><script>(function(){{window.speechSynthesis.cancel();var msg=new SpeechSynthesisUtterance('{text_safe}');msg.lang='it-IT';window.speechSynthesis.speak(msg);}})();</script>"""
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
            vecchio_saldo =
