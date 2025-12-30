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
        
        if msg not in dati_stanza.get("messaggio_audio", ""):
            dati_stanza["messaggio_audio"] += f" ... {msg}"
            dati_stanza["messaggio_toast"] = f"🏆 {msg}"
            nuova_vincita_trovata = True
        
        # Logica avanzamento premio
        if target < 5: 
            dati_stanza["obbiettivo_corrente"] += 1
        elif target == 5: 
            dati_stanza["obbiettivo_corrente"] = 15
        else: 
            dati_stanza["messaggio_audio"] += " ... Gioco Finito!"
            dati_stanza["gioco_finito"] = True
            nuova_vincita_trovata = True

    return dati_stanza, nuova_vincita_trovata

# --- INTERFACCIA ---
st.markdown("<h1 class='rock-title'>🤟 TOMBOLA ROCK 🤟</h1>", unsafe_allow_html=True)

menu = st.sidebar.radio("Menu", ["🏠 Home", "🆕 Crea Stanza (Admin)", "🎮 Entra in Stanza"])

# --- HOMEPAGE CON REGOLAMENTO ---
if menu == "🏠 Home":
    st.markdown("### Benvenuti alla Tombola più Rock del Web! 🎸")
    
    st.markdown("""
    <div class='rule-box'>
        <h3>📜 REGOLAMENTO DI GIOCO</h3>
        <p>Le regole sono quelle classiche della Tombola Napoletana. Si vince raggiungendo le combinazioni seguenti su una singola riga:</p>
        <ul>
            <li><span class='win-title'>AMBO (2)</span>: Due numeri estratti sulla stessa riga.</li>
            <li><span class='win-title'>TERNO (3)</span>: Tre numeri estratti sulla stessa riga.</li>
            <li><span class='win-title'>QUATERNA (4)</span>: Quattro numeri estratti sulla stessa riga.</li>
            <li><span class='win-title'>CINQUINA (5)</span>: Cinque numeri estratti sulla stessa riga.</li>
        </ul>
        <hr>
        <p>Il premio finale è:</p>
        <ul>
            <li><span class='win-title'>🏆 TOMBOLA (15)</span>: Tutti i numeri della cartella estratti!</li>
        </ul>
    </div>
    
    <div class='rule-box'>
        <h3>🕹️ COME PARTECIPARE</h3>
        <ol>
            <li><b>L'Admin</b> crea la stanza (il Banco non gioca, gestisce solo l'estrazione).</li>
            <li><b>I Giocatori</b> entrano inserendo il nome della stanza e il proprio nome.</li>
            <li>Il sistema controlla <b>automaticamente</b> le vincite e ferma il gioco per festeggiare!</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# --- CREAZIONE STANZA (ADMIN) ---
elif menu == "🆕 Crea Stanza (Admin)":
    st.header("Impostazioni Banco (Admin)")
    st.info("L'Admin gestisce l'estrazione ma non possiede cartelle di gioco.")
    
    with st.form("crea"):
        nome = st.text_input("Nome Stanza", max_chars=15).upper().strip()
        pwd = st.text_input("Password Admin", type="password")
        
        if st.form_submit_button("Crea Stanza 🎸"):
            if not nome or not pwd: st.error("Dati mancanti.")
            else:
                exist = load_stanza_db(nome)
                if exist: st.warning("Attenzione: Stanza esistente resettata.")
                numeri = list(range(1, 91)); random.shuffle(numeri)
                dati = {
                    "admin_pwd": pwd, "created_at": str(datetime.now()),
                    "numeri_tabellone": numeri, "numeri_estratti": [],
                    "ultimo_numero": None, "messaggio_audio": "", "messaggio_toast": "",
                    "giocatori": {}, "obbiettivo_corrente": 2, "gioco_finito": False
                }
                save_stanza_db(nome, dati)
                
                st.session_state.ruolo = "ADMIN"
                st.session_state.stanza_corrente = nome
                st.session_state.nome_giocatore = "ADMIN"
                st.rerun()

# --- ACCESSO GIOCATORI ---
elif menu == "🎮 Entra in Stanza":
    if 'stanza_corrente' not in st.session_state:
        c1, c2 = st.columns(2)
        inp_stanza = c1.text_input("Nome Stanza").upper().strip()
        inp_nome = c2.text_input("Il tuo Nome").strip().upper()
        
        is_admin = st.checkbox("Sono l'Admin (Banco)")
        pwd_in = st.text_input("Password", type="password") if is_admin else ""
        n_cart = st.slider("Cartelle", 1, 6, 1)
        
        if st.button("ENTRA 🤟"):
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
                        # Check Nomi Univoci
                        if inp_nome in d["giocatori"]:
                            st.error(f"Il nome '{inp_nome}' è già preso! Usa un nickname Rock diverso.")
                        else:
                            if len(d["giocatori"]) >= 30: st.error("Stanza piena.")
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

        # LISTA PARTECIPANTI (SIDEBAR)
        with st.sidebar:
            st.divider()
            lista_giocatori = list(dati["giocatori"].keys())
            st.markdown(f"### 🎸 Partecipanti ({len(lista_giocatori)})")
            lista_ordinata = sorted(lista_giocatori)
            for g in lista_ordinata:
                n_c = len(dati["giocatori"][g])
                icona = "🤟" # Icona Rock
                if g == mio_nome: st.markdown(f"👉 **{icona} {g}** ({n_c})")
                else: st.markdown(f"{icona} {g} ({n_c})")
            st.divider()

        # LOGICA GIOCO E NOTIFICHE
        estratti = dati["numeri_estratti"]
        ultimo = dati["ultimo_numero"]
        msg_audio = dati.get("messaggio_audio", "")
        msg_toast = dati.get("messaggio_toast", "")

        c1, c2 = st.columns([3,1])
        c1.markdown(f"## Stanza: **{stanza}** | Utente: *{mio_nome}*")
        if c2.button("🚪 Esci"): st.session_state.clear(); st.rerun()

        if msg_toast:
            if 'last_toast' not in st.session_state or st.session_state.last_toast != msg_toast:
                st.toast(msg_toast, icon="🎉"); st.session_state.last_toast = msg_toast
                if dati.get("gioco_finito"): st.balloons()

        # --- PANNELLO ADMIN ---
        if ruolo == "ADMIN":
            st.info(f"👮 PANNELLO BANCO - Si gioca per: {dati.get('obbiettivo_corrente', '?')}")
            col_auto, col_man = st.columns(2)
            
            def estrai():
                """Ritorna (successo, vincita_flag)"""
                if len(dati["numeri_tabellone"]) > 0 and not dati.get("gioco_finito"):
                    n = dati["numeri_tabellone"].pop(0)
                    dati["numeri_estratti"].append(n)
                    dati["ultimo_numero"] = n
                    dati["messaggio_audio"] = f"{n}. {get_smorfia_text(n)}."
                    dati["messaggio_toast"] = ""
                    # Controlla vincite
                    d_agg, win_flag = controlla_vincite(dati)
                    save_stanza_db(stanza, d_agg)
                    return True, win_flag
                return False, False

            with col_auto:
                usa_auto = st.toggle("Auto-Play 🚀", key="auto_play_toggle")
                tempo = st.slider("Secondi", 3, 20, 6)
                p_bar = st.progress(0); stat = st.empty()
            
            with col_man:
                if st.button("🎱 ESTRAI MANUALE", type="primary", disabled=usa_auto): 
                    succ, win = estrai()
                    if succ: st.rerun()

            # LOGICA AUTO PLAY
            if usa_auto and not dati.get("gioco_finito"):
                if len(dati["numeri_tabellone"]) > 0:
                    stat.write(f"⏳ Estrazione in {tempo}s...")
                    esito, vincita_rilevata = estrai()
                    
                    if esito:
                        if vincita_rilevata:
                            st.session_state.auto_play_toggle = False 
                            st.rerun() 
                        else:
                            for i in range(100): 
                                time.sleep(tempo/100)
                                p_bar.progress(i+1)
                            st.rerun()
                else: 
                    st.warning("Fine numeri.")

        # AUDIO
        if 'last_audio_msg' not in st.session_state: st.session_state.last_audio_msg = ""
        if msg_audio and msg_audio != st.session_state.last_audio_msg:
            speak_js(msg_audio); st.session_state.last_audio_msg = msg_audio

        # VISUALIZZAZIONE ULTIMO NUMERO
        if ultimo:
            st.markdown(f"""
            <div style="text-align: center; background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <span style="font-size: 80px; font-weight: bold; color: #e74c3c;">{ultimo}</span><br>
                <span style="font-size: 24px; font-style: italic;">{get_smorfia_text(ultimo)}</span>
            </div>
            """, unsafe_allow_html=True)
            nomi_p = {2:"AMBO", 3:"TERNO", 4:"QUATERNA", 5:"CINQUINA", 15:"TOMBOLA"}
            st.info(f"Prossimo Obiettivo: **{nomi_p.get(dati.get('obbiettivo_corrente', 2), 'FINE')}**")
        else: st.info("In attesa inizio...")

        # TABELLONE
        with st.expander("Tabellone", expanded=True):
            st.markdown("""<style>.g{display:grid;grid-template-columns:repeat(10,1fr);gap:2px}.c{border:1px solid #ccc;text-align:center;padding:5px;font-size:12px;background:#eee}.Ex{background:#e74c3c;color:white;font-weight:bold}</style>""", unsafe_allow_html=True)
            h = '<div class="g">'
            for i in range(1, 91): h+=f'<div class="c {"Ex" if i in estratti else ""}">{i}</div>'
            st.markdown(h+'</div>', unsafe_allow_html=True)

        # CARTELLE (SOLO SE SEI PLAYER)
        if ruolo == "PLAYER":
            st.divider(); st.subheader("Le Tue Cartelle")
            mie = dati["giocatori"].get(mio_nome, [])
            cols = st.columns(3)
            st.markdown("""<style>.ct{width:100%;border-collapse:collapse;margin-bottom:10px;background:white}.cc{border:1px solid #333;width:11%;text-align:center;height:30px;font-weight:bold}.ch{background-color:#2ecc71;color:white}.ce{background-color:#bdc3c7}</style>""", unsafe_allow_html=True)
            for idx, m in enumerate(mie):
                with cols[idx%3]:
                    h = f"<b>C. {idx+1}</b><table class='ct'>"
                    for r in m:
                        h+="<tr>"
                        for v in r: h+=f"<td class='cc {'ce' if v==0 else ('ch' if v in estratti else '')}'>{v if v!=0 else ''}</td>"
                        h+="</tr>"
                    st.markdown(h+"</table>", unsafe_allow_html=True)
            time.sleep(3); st.rerun()
