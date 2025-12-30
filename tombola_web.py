import streamlit as st
import random
import time
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- CONFIGURAZIONE PAGINA E STILE ROCK ---
st.set_page_config(page_title="TombolaRock", layout="wide", page_icon="🤟")

# CSS: Fix per Android Dark Mode + Stile Rock + Regolamento
st.markdown("""
    <style>
        /* Base chiara per compatibilità mobile */
        .stApp { background-color: #ffffff; color: #000000; }
        input, .stTextInput > div > div > input { color: #000000 !important; background-color: #ffffff !important; }
        section[data-testid="stSidebar"] { background-color: #f0f2f6; }
        p, h1, h2, h3, h4, h5, h6, li, span, div { color: #2c3e50; }
        .c-cell, .cell-tab { color: #000000; }
        
        /* STILE ROCK */
        .rock-title { 
            color: #d63031; 
            font-weight: 900; 
            text-align: center; 
            text-transform: uppercase; 
            font-family: 'Arial Black', sans-serif;
            text-shadow: 2px 2px 0px #000000;
        }
        .rule-box {
            background-color: #ecf0f1;
            padding: 20px;
            border-radius: 10px;
            border-left: 5px solid #d63031;
            margin-bottom: 10px;
        }
        .win-title { color: #2ecc71; font-weight: bold; }
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
        for c
