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
    """, unsafe_allow_html=True)

elif menu == "🆕 Crea Stanza (Admin)":
    st.header("Impostazioni Banco (Admin)")
    with st.form("crea"):
        nome = st.text_input("Nome Stanza", max_chars=15).upper().strip()
        pwd = st.text_input("Password Admin", type="password")
        if st.form_submit_button("Crea Stanza 🎸"):
            if not nome or not pwd: st.error("Dati mancanti.")
            else:
                exist = load_stanza_db(nome)
                if exist: st.warning("Reset stanza eseguito.")
                numeri = list(range(1, 91)); random.shuffle(numeri)
                dati = {
                    "admin_pwd": pwd, "created_at": str(datetime.now()),
                    "stato": "LOBBY",
                    "audio_attivo": True, # DEFAULT AUDIO ON
                    "numeri_tabellone": numeri, "numeri_estratti": [],
                    "ultimo_numero": None, "messaggio_audio": "", "messaggio_toast": "",
                    "giocatori": {}, "classifica_vincite": {},
                    "obbiettivo_corrente": 2, "gioco_finito": False
                }
                save_stanza_db(nome, dati)
                st.session_state.admin_msg = f"Stanza '{nome}' creata! 🎸"
                st.session_state.ruolo = "ADMIN"
                st.session_state.stanza_corrente = nome
                st.session_state.nome_giocatore = "TOMBOLONE"
                st.rerun()

elif menu == "🎮 Entra in Stanza":
    if 'stanza_corrente' not in st.session_state:
        c1, c2 = st.columns(2)
        inp_stanza = c1.text_input("Nome Stanza").upper().strip()
        
        is_admin = st.checkbox("Sono l'Admin (Banco)")
        
        if is_admin:
            inp_nome = "TOMBOLONE"
            st.info("Accesso come: **TOMBOLONE**")
            pwd_in = st.text_input("Password", type="password")
            n_cart = 0
        else:
            inp_nome = c2.text_input("Il tuo Nome").strip().upper()
            pwd_in = ""
            n_cart = st.slider(f"Cartelle ({COSTO_CARTELLA} gettoni l'una)", 1, 6, 1)
            costo_tot = n_cart * COSTO_CARTELLA
            st.info(f"💰 Costo ingresso: **{costo_tot} gettoni**")
        
        if st.button("ENTRA 🤟"):
            d = load_stanza_db(inp_stanza)
            if not d: st.error("Stanza non trovata.")
            else:
                if is_admin:
                    if pwd_in == d["admin_pwd"]:
                        st.session_state.ruolo = "ADMIN"
                        st.session_state.stanza_corrente = inp_stanza
                        st.session_state.nome_giocatore = "TOMBOLONE"
                        st.rerun()
                    else: st.error("Password errata.")
                else:
                    if inp_nome:
                        gia_presente = inp_nome in d["giocatori"]
                        stato_partita = d.get("stato", "LOBBY")
                        if not gia_presente and stato_partita != "LOBBY":
                            st.error("🚫 Concerto già iniziato! La biglietteria è chiusa.")
                        elif gia_presente:
                            st.session_state.ruolo = "PLAYER"
                            st.session_state.stanza_corrente = inp_stanza
                            st.session_state.nome_giocatore = inp_nome
                            st.rerun()
                        elif inp_nome not in d["giocatori"]:
                            if len(d["giocatori"]) >= 40: st.error("Stanza piena.")
                            else:
                                d["giocatori"][inp_nome] = [GeneratoreCartelle.genera_matrice_3x9() for _ in range(n_cart)]
                                if "classifica_vincite" not in d: d["classifica_vincite"] = {}
                                d["classifica_vincite"][inp_nome] = 0
                                save_stanza_db(inp_stanza, d)
                                st.session_state.ruolo = "PLAYER"
                                st.session_state.stanza_corrente = inp_stanza
                                st.session_state.nome_giocatore = inp_nome
                                st.rerun()
                    else: st.error("Inserisci nome.")
    else:
        # --- GIOCO / LOBBY ---
        stanza = st.session_state.stanza_corrente
        ruolo = st.session_state.ruolo
        mio_nome = st.session_state.nome_giocatore
        
        if "admin_msg" in st.session_state:
            st.toast(st.session_state.admin_msg, icon="✅")
            del st.session_state.admin_msg
        
        dati = load_stanza_db(stanza)
        
        if not dati:
            st.warning("⚠️ La stanza è stata chiusa dall'Admin.")
            time.sleep(2)
            st.session_state.clear()
            st.rerun()
            st.stop()

        stato_partita = dati.get("stato", "LOBBY")
        tot_c, montepremi, vals = get_info_economiche(dati)
        
        # --- SIDEBAR ---
        with st.sidebar:
            st.divider()
            st.markdown(f"""
            <div class='money-box'>
                <div>MONTEPREMI</div>
                <div class='money-val'>💰 {montepremi}</div>
                <div style='font-size:12px; color:#555'>Cartelle: {tot_c}</div>
            </div>
            """, unsafe_allow_html=True)
            
            st.markdown("#### 🏆 Premi in Palio")
            nomi_p_short = {2:"AMBO", 3:"TERNO", 4:"QUAT.", 5:"CINQ.", 15:"TOMBOLA"}
            curr_obj = dati.get("obbiettivo_corrente", 2)
            for k, val_p in vals.items():
                lbl = nomi_p_short.get(k, str(k))
                marker = "👉" if k == curr_obj and stato_partita == "IN_CORSO" else "-"
                style_p = "font-weight:bold; color:#d35400;" if k == curr_obj and stato_partita == "IN_CORSO" else ""
                st.markdown(f"<div class='prize-row'>{marker} <span style='{style_p}'>{lbl}: {val_p}</span></div>", unsafe_allow_html=True)
            
            st.divider()
            num_p = len(dati["giocatori"])
            st.markdown(f"### 👥 {num_p} Presenti")
            leaderboard = dati.get("classifica_vincite", {})
            lista_g = sorted(list(dati["giocatori"].keys()), key=lambda x: leaderboard.get(x, 0), reverse=True)
            st.markdown("<div style='max-height: 400px; overflow-y: auto;'>", unsafe_allow_html=True)
            for g in lista_g:
                nc = len(dati["giocatori"][g])
                vinto = leaderboard.get(g, 0)
                icona = "🏆" if vinto > 0 else "👤"
                badge = f" <span class='winner-badge'>+💰{vinto}</span>" if vinto > 0 else ""
                style_nome = "font-weight: bold; color: #d63031;" if g == mio_nome else ""
                st.markdown(f"<div class='player-row'>{icona} <span style='{style_nome}'>{g}</span> ({nc}) {badge}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            st.divider()

        # --- HEADER ---
        c1, c2 = st.columns([3,1])
        c1.markdown(f"## Stanza: **{stanza}** | Utente: *{mio_nome}*")
        
        if ruolo == "ADMIN":
            if c2.button("🚫 CHIUDI STANZA"):
                delete_stanza_db(stanza)
                st.session_state.clear()
                st.rerun()
        else:
            if c2.button("🚪 Esci"):
                st.session_state.clear()
                st.rerun()

        # --- FASE 1: VISUALIZZAZIONE & AUDIO (SOLO SE AUDIO ATTIVO) ---
        if stato_partita == "IN_CORSO":
            ultimo = dati["ultimo_numero"]
            msg_audio = dati.get("messaggio_audio", "")
            
            # Recupera flag audio (Default True per vecchie stanze)
            audio_attivo = dati.get("audio_attivo", True)
            
            # AUDIO JS (Solo se flag True)
            if 'last_audio_msg' not in st.session_state: st.session_state.last_audio_msg = ""
            if audio_attivo:
                if msg_audio and msg_audio != st.session_state.last_audio_msg:
                    speak_js(msg_audio); st.session_state.last_audio_msg = msg_audio

            # DISPLAY ULTIMO NUMERO
            if ultimo:
                smorfia_testo = get_smorfia_text(ultimo)
                st.markdown(f"""
                <div style="text-align: center; background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                    <span style="font-size: 80px; font-weight: bold; color: #e74c3c;">{ultimo}</span><br>
                    <div class='song-title'>{smorfia_testo}</div>
                </div>
                """, unsafe_allow_html=True)
                
                nomi_p = {2:"AMBO", 3:"TERNO", 4:"QUATERNA", 5:"CINQUINA", 15:"TOMBOLA"}
                next_val = vals.get(dati.get('obbiettivo_corrente'), 0)
                st.info(f"Prossimo Obiettivo: **{nomi_p.get(dati.get('obbiettivo_corrente', 2), 'FINE')}** (Vincita: {next_val} gettoni)")

        # --- FASE 2: LOGICA ADMIN & AUTO-PLAY ---
        if stato_partita == "LOBBY":
            if ruolo == "ADMIN":
                st.info("🕒 Fase di attesa giocatori. Quando sei pronto, dai il via!")
                st.markdown(f"<h1 style='text-align:center'>Biglietti venduti: {tot_c}</h1>", unsafe_allow_html=True)
                if st.button("🎸 DAI IL VIA AL CONCERTO!", type="primary", use_container_width=True):
                    dati["stato"] = "IN_CORSO"
                    save_stanza_db(stanza, dati)
                    st.rerun()
            else:
                st.markdown(f"""
                <div class='lobby-box'>
                    <h1>🎸 SOUNDCHECK IN CORSO...</h1>
                    <p>Attendi che l'Admin dia il via al concerto!</p>
                    <p>Nel frattempo controlla di avere le tue {len(dati['giocatori'][mio_nome])} cartelle.</p>
                </div>
                """, unsafe_allow_html=True)
                time.sleep(3)
                st.rerun()
        
        elif stato_partita == "IN_CORSO":
            estratti = dati["numeri_estratti"]
            curr_obj = dati.get("obbiettivo_corrente", 2)
            msg_toast = dati.get("messaggio_toast", "")

            if msg_toast:
                if 'last_toast' not in st.session_state or st.session_state.last_toast != msg_toast:
                    st.toast(msg_toast, icon="🎉"); st.session_state.last_toast = msg_toast
                    if dati.get("gioco_finito"): st.balloons()

            if ruolo == "ADMIN":
                nomi_p = {2:"AMBO", 3:"TERNO", 4:"QUATERNA", 5:"CINQUINA", 15:"TOMBOLA"}
                txt_obj = nomi_p.get(curr_obj, "FINE")
                val_corr = vals.get(curr_obj, 0)
                st.info(f"👮 PANNELLO BANCO - Si gioca per: **{txt_obj}** (Valore: {val_corr} gettoni)")
                
                col_auto, col_man = st.columns(2)
                
                def estrai():
                    if len(dati["numeri_tabellone"]) > 0 and not dati.get("gioco_finito"):
                        n = dati["numeri_tabellone"].pop(0)
                        dati["numeri_estratti"].append(n)
                        dati["ultimo_numero"] = n
                        smorfia = get_smorfia_text(n)
                        dati["messaggio_audio"] = f"{n} || {smorfia}"
                        dati["messaggio_toast"] = ""
                        d_agg, win = controlla_vincite(dati)
                        save_stanza_db(stanza, d_agg)
                        return True, win
                    return False, False

                # LOGICA TOGGLE AUDIO
                audio_on = st.toggle("Audio Vocale 🔊", value=dati.get("audio_attivo", True))
                if audio_on != dati.get("audio_attivo", True):
                    dati["audio_attivo"] = audio_on
                    save_stanza_db(stanza, dati)
                    st.rerun()

                if "stato_autoplay" not in st.session_state:
                    st.session_state.stato_autoplay = False

                def callback_autoplay():
                    st.session_state.stato_autoplay = st.session_state.toggle_widget_key

                with col_auto:
                    usa_auto = st.toggle("Auto-Play 🚀", 
                                       value=st.session_state.stato_autoplay,
                                       key="toggle_widget_key",
                                       on_change=callback_autoplay)
                    tempo = st.slider("Secondi", 3, 20, 6)
                    p_bar = st.progress(0); stat = st.empty()
                
                with col_man:
                    if st.button("🎱 ESTRAI MANUALE", type="primary", disabled=usa_auto): 
                        succ, win = estrai()
                        if succ: st.rerun()

                # LOGICA AUTO-PLAY
                if usa_auto and not dati.get("gioco_finito"):
                    if len(dati["numeri_tabellone"]) > 0:
                        stat.write(f"⏳ Estrazione tra {tempo} secondi...")
                        my_bar = st.progress(0)
                        for percent_complete in range(100):
                            time.sleep(tempo / 100)
                            my_bar.progress(percent_complete + 1)
                        
                        esito, vinta = estrai()
                        if esito:
                            if vinta: st.session_state.stato_autoplay = False
                            st.rerun()
                    else: st.warning("Fine numeri.")

            # TABELLONE E CARTELLE
            with st.expander("Tabellone", expanded=True):
                st.markdown("""<style>.g{display:grid;grid-template-columns:repeat(10,1fr);gap:2px}.c{border:1px solid #ccc;text-align:center;padding:5px;font-size:12px;background:#eee}.Ex{background:#e74c3c;color:white;font-weight:bold}</style>""", unsafe_allow_html=True)
                h = '<div class="g">'
                for i in range(1, 91): h+=f'<div class="c {"Ex" if i in estratti else ""}">{i}</div>'
                st.markdown(h+'</div>', unsafe_allow_html=True)

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
