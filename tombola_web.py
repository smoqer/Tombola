import streamlit as st
import random
import time
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="TombolaRock", layout="wide", page_icon="🤘")

# ==========================================
# ⚙️ IMPOSTAZIONI ECONOMICHE
# ==========================================
COSTO_CARTELLA = 5  # Costo in gettoni

# Percentuali Montepremi
PERCENTUALI_PREMI = {
    2: 0.08,   # Ambo
    3: 0.12,   # Terno
    4: 0.20,   # Quaterna
    5: 0.25,   # Cinquina
    15: 0.35   # Tombola
}
# ==========================================

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

# --- LOGICA CALCOLO MONTEPREMI ---
def ricalcola_economia(dati_stanza):
    tot_cartelle = 0
    for cartelle_giocatore in dati_stanza["giocatori"].values():
        tot_cartelle += len(cartelle_giocatore)
    montepremi_totale = float(tot_cartelle * COSTO_CARTELLA)
    dati_stanza["montepremi"] = montepremi_totale
    dati_stanza["premi_valori"] = {}
    for target, perc in PERCENTUALI_PREMI.items():
        valore = round(montepremi_totale * perc, 2)
        dati_stanza["premi_valori"][str(target)] = valore
    return dati_stanza

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

    @staticmethod
    def genera_tombolone_completo():
        mega_grid = [[0] * 9 for _ in range(18)]
        range_colonne = [list(range(1, 10)), list(range(10, 20)), list(range(20, 30)), list(range(30, 40)), list(range(40, 50)), list(range(50, 60)), list(range(60, 70)), list(range(70, 80)), list(range(80, 91))]
        for c in range(9):
            numeri_col = range_colonne[c][:]
            random.shuffle(numeri_col)
            for r in range(len(numeri_col)): mega_grid[r][c] = numeri_col[r]
            col_values = [mega_grid[r][c] for r in range(18)]
            random.shuffle(col_values)
            for r in range(18): mega_grid[r][c] = col_values[r]
        while True:
            row_counts = [sum(1 for x in row if x > 0) for row in mega_grid]
            if all(c == 5 for c in row_counts): break 
            row_over = next(i for i, c in enumerate(row_counts) if c > 5)
            row_under = next(i for i, c in enumerate(row_counts) if c < 5)
            for c in range(9):
                if mega_grid[row_over][c] > 0 and mega_grid[row_under][c] == 0:
                    mega_grid[row_under][c] = mega_grid[row_over][c]
                    mega_grid[row_over][c] = 0
                    break
        cartelle_finali = []
        for i in range(6):
            start_row, end_row = i * 3, (i * 3) + 3
            sub = [r[:] for r in mega_grid[start_row:end_row]]
            for c in range(9):
                nums, pos = [], []
                for r in range(3):
                    if sub[r][c] != 0: nums.append(sub[r][c]); pos.append(r)
                nums.sort()
                for idx, r in enumerate(pos): sub[r][c] = nums[idx]
            cartelle_finali.append(sub)
        return cartelle_finali

# --- CONTROLLO VINCITE (LOGICA SPLIT) ---
def controlla_vincite(dati_stanza):
    target = dati_stanza.get("obbiettivo_corrente", 2)
    estratti = set(dati_stanza["numeri_estratti"])
    nomi_premi = {2: "AMBO", 3: "TERNO", 4: "QUATERNA", 5: "CINQUINA", 15: "TOMBOLA"}
    nome_premio = nomi_premi.get(target, "TOMBOLA")
    
    # Valore totale del premio
    valore_premio_totale = dati_stanza.get("premi_valori", {}).get(str(target), 0)
    
    # Inizializza registro vincite se manca
    if "vincite_giocatori" not in dati_stanza:
        dati_stanza["vincite_giocatori"] = {}

    vincitori_round = []
    
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
        num_vincitori = len(vincitori_round)
        # Calcolo quota pro-capite (Split)
        quota_cadauno = round(valore_premio_totale / num_vincitori, 2)
        
        # Aggiorna il portafoglio dei vincitori
        for vincitore in vincitori_round:
            vecchio_totale = dati_stanza["vincite_giocatori"].get(vincitore, 0)
            dati_stanza["vincite_giocatori"][vincitore] = vecchio_totale + quota_cadauno

        testo = ", ".join(vincitori_round)
        if num_vincitori > 1:
            msg = f"Attenzione! {nome_premio} DIVISO ({quota_cadauno} a testa) tra: {testo}!"
        else:
            msg = f"Attenzione! {nome_premio} ({valore_premio_totale}) per {testo}!"
            
        if msg not in dati_stanza.get("messaggio_audio", ""):
            dati_stanza["messaggio_audio"] += f" ... {msg}"
        dati_stanza["messaggio_toast"] = f"🏆 {msg}"
        
        if target < 5: dati_stanza["obbiettivo_corrente"] += 1
        elif target == 5: dati_stanza["obbiettivo_corrente"] = 15
        else: 
            dati_stanza["messaggio_audio"] += " ... Gioco Finito!"
            dati_stanza["gioco_finito"] = True
            
    return dati_stanza

# --- INTERFACCIA ---
menu = st.sidebar.radio("Navigazione", ["🏠 Home", "🆕 Crea Stanza", "🎮 Entra in Stanza"])

if menu == "🏠 Home":
    st.markdown("""
    <style>
    .rock-title { font-family: 'Courier New', monospace; text-align: center; color: #d63031; text-shadow: 2px 2px 0px #2d3436; margin-bottom: 30px; }
    .rock-hand { font-size: 80px; vertical-align: middle; }
    .rock-text { font-size: 80px; font-weight: 900; vertical-align: middle; padding: 0 20px; }
    .rules-card { background-color: #f1f2f6; padding: 20px; border-radius: 10px; border-left: 5px solid #d63031; margin-bottom: 10px; }
    </style>
    <div class="rock-title"><span class="rock-hand">🤘</span><span class="rock-text">TombolaRock</span><span class="rock-hand">🤘</span></div>
    """, unsafe_allow_html=True)
    
    st.header("📜 Regolamento Ufficiale")
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown(f"""
        <div class="rules-card">
        <h4>1. Iscrizione</h4>
        <ul>
            <li>Ogni cartella costa <b>{COSTO_CARTELLA} Gettoni</b>.</li>
            <li>Puoi acquistare massimo 6 cartelle.</li>
            <li>Il costo delle cartelle forma il <b>Montepremi Totale</b>.</li>
        </ul>
        </div>
        
        <div class="rules-card">
        <h4>2. Premi e Vincite</h4>
        <p>Il Montepremi viene diviso automaticamente:</p>
        <ul>
            <li><b>Ambo (2 su una riga):</b> 8%</li>
            <li><b>Terno (3 su una riga):</b> 12%</li>
            <li><b>Quaterna (4 su una riga):</b> 20%</li>
            <li><b>Cinquina (5 su una riga):</b> 25%</li>
            <li><b>Tombola (Tutti i numeri):</b> 35%</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)
        
    with c2:
        st.markdown("""
        <div class="rules-card">
        <h4>3. Regola dell'Ex Aequo (Split) ⚖️</h4>
        <p>Se più giocatori realizzano la stessa vincita contemporaneamente (es. due persone fanno Ambo con lo stesso numero estratto):</p>
        <ul>
            <li>Il premio <b>NON</b> viene assegnato interamente a entrambi.</li>
            <li>Il valore del premio viene <b>DIVISO EQUAMENTE</b> tra i vincitori.</li>
            <li><i>Esempio: Premio 10 gettoni, 2 vincitori = 5 gettoni a testa.</i></li>
        </ul>
        </div>
        
        <div class="rules-card">
        <h4>4. Svolgimento</h4>
        <p>Il Banco (Admin) estrae i numeri. Il sistema controlla automaticamente le vincite e aggiorna i portafogli dei giocatori in tempo reale.</p>
        </div>
        """, unsafe_allow_html=True)

elif menu == "🆕 Crea Stanza":
    st.header("Impostazioni Banco")
    with st.form("crea"):
        nome = st.text_input("Nome Stanza", max_chars=15).upper().strip()
        pwd = st.text_input("Password Admin", type="password")
        banco_play = st.checkbox(f"Il Banco gioca (paga {6*COSTO_CARTELLA} gettoni)?", True)
        if st.form_submit_button("Crea Stanza"):
            if not nome or not pwd: st.error("Dati mancanti.")
            else:
                exist = load_stanza_db(nome)
                if exist: st.warning("Sovrascritta.")
                numeri = list(range(1, 91)); random.shuffle(numeri)
                dati = {
                    "admin_pwd": pwd, "created_at": str(datetime.now()),
                    "numeri_tabellone": numeri, "numeri_estratti": [],
                    "ultimo_numero": None, "messaggio_audio": "", "messaggio_toast": "",
                    "giocatori": {}, "obbiettivo_corrente": 2, "gioco_finito": False,
                    "montepremi": 0, "premi_valori": {},
                    "vincite_giocatori": {} # Dizionario {nome: totale_vinto}
                }
                if banco_play:
                    dati["giocatori"]["BANCO"] = GeneratoreCartelle.genera_tombolone_completo()
                    dati = ricalcola_economia(dati)
                save_stanza_db(nome, dati)
                st.session_state.ruolo = "ADMIN"
                st.session_state.stanza_corrente = nome
                st.session_state.nome_giocatore = "BANCO" if banco_play else "ADMIN"
                st.rerun()

elif menu == "🎮 Entra in Stanza":
    if 'stanza_corrente' not in st.session_state:
        st.markdown("## Join the Party 🎸")
        c1, c2 = st.columns(2)
        inp_stanza = c1.text_input("Nome Stanza").upper().strip()
        inp_nome = c2.text_input("Il tuo Nome").strip().upper()
        is_admin = st.checkbox("Sono Admin")
        pwd_in = st.text_input("Password", type="password") if is_admin else ""
        n_cart = st.slider(f"Cartelle ({COSTO_CARTELLA} gettoni cad.)", 1, 6, 1)
        
        if st.button(f"PAGA {n_cart*COSTO_CARTELLA} E ENTRA"):
            d = load_stanza_db(inp_stanza)
            if not d: st.error("Stanza non trovata.")
            else:
                if is_admin:
                    if pwd_in == d["admin_pwd"]:
                        st.session_state.ruolo = "ADMIN"
                        st.session_state.stanza_corrente = inp_stanza
                        st.session_state.nome_giocatore = "BANCO"
                        st.rerun()
                    else: st.error("Password errata.")
                else:
                    if inp_nome:
                        if inp_nome not in d["giocatori"]:
                            if len(d["giocatori"]) >= 20: st.error("Piena.")
                            else:
                                d["giocatori"][inp_nome] = [GeneratoreCartelle.genera_matrice_3x9() for _ in range(n_cart)]
                                d = ricalcola_economia(d)
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
        if not dati: st.error("Errore."); st.stop()

        # Inizializza vincite se manca (retrocompatibilità)
        if "vincite_giocatori" not in dati: dati["vincite_giocatori"] = {}

        with st.sidebar:
            st.divider()
            st.markdown(f"## 💰 JackPot: {dati.get('montepremi', 0)}")
            nomi_target = { "2": "Ambo", "3": "Terno", "4": "Quaterna", "5": "Cinquina", "15": "Tombola" }
            curr_target = str(dati.get("obbiettivo_corrente", 15))
            for k, val in dati.get("premi_valori", {}).items():
                nome = nomi_target.get(k, k)
                if k == curr_target and not dati.get("gioco_finito"): st.markdown(f"👉 **{nome}: {val}**")
                elif float(k) < float(curr_target): st.markdown(f"~~{nome}: {val}~~ ✅")
                else: st.markdown(f"{nome}: {val}")
            
            st.divider()
            st.markdown(f"### 👥 Rockers ({len(dati['giocatori'])})")
            
            # ORDINAMENTO: Prima Banco, poi per Vincite decrescenti, poi nome
            lista_g = list(dati["giocatori"].keys())
            def sort_key(x):
                is_banco = 0 if "BANCO" in x else 1
                vincita = dati["vincite_giocatori"].get(x, 0)
                return (is_banco, -vincita, x)
            
            for g in sorted(lista_g, key=sort_key):
                n_cart = len(dati["giocatori"][g])
                vincita_tot = dati["vincite_giocatori"].get(g, 0)
                
                icon = "🏦" if "BANCO" in g else "👤"
                soldi_str = f" | 💰 {vincita_tot:.2f}" if vincita_tot > 0 else ""
                
                style = "**" if g == mio_nome else ""
                st.markdown(f"{style}{icon} {g} ({n_cart}c){soldi_str}{style}")

        estratti = dati["numeri_estratti"]
        ultimo = dati["ultimo_numero"]
        msg_audio = dati.get("messaggio_audio", "")
        msg_toast = dati.get("messaggio_toast", "")

        c1, c2 = st.columns([3,1])
        c1.markdown(f"## Stanza: **{stanza}** | Player: *{mio_nome}*")
        if c2.button("🚪 Esci"): st.session_state.clear(); st.rerun()

        if msg_toast:
            if 'last_toast' not in st.session_state or st.session_state.last_toast != msg_toast:
                st.toast(msg_toast, icon="🎉"); st.session_state.last_toast = msg_toast
                if dati.get("gioco_finito"): st.balloons()

        tgt_code = dati.get('obbiettivo_corrente', 2)
        tgt_name = nomi_target.get(str(tgt_code), 'FINE')
        tgt_val = dati.get("premi_valori", {}).get(str(tgt_code), 0)
        
        # --- SEZIONE AUDIO ---
        if 'last_audio_msg' not in st.session_state: st.session_state.last_audio_msg = ""
        if msg_audio and msg_audio != st.session_state.last_audio_msg:
            speak_js(msg_audio); st.session_state.last_audio_msg = msg_audio

        if ultimo:
            st.markdown(f"""
            <div style="text-align: center; background-color: #2d3436; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px; border: 2px solid #d63031;">
                <span style="font-size: 80px; font-weight: bold; color: #d63031;">{ultimo}</span><br>
                <span style="font-size: 24px; font-style: italic;">{get_smorfia_text(ultimo)}</span>
            </div>
            """, unsafe_allow_html=True)
            st.info(f"Prossimo Obiettivo: **{tgt_name} ({tgt_val} gettoni)**")
        else: st.info("Waiting for the show...")

        # --- PANNELLO ADMIN ---
        if ruolo == "ADMIN":
            st.warning(f"👮 PANNELLO BANCO")
            col_auto, col_man = st.columns(2)
            
            def estrai():
                if len(dati["numeri_tabellone"]) > 0 and not dati.get("gioco_finito"):
                    n = dati["numeri_tabellone"].pop(0)
                    dati["numeri_estratti"].append(n)
                    dati["ultimo_numero"] = n
                    dati["messaggio_audio"] = f"{n}. {get_smorfia_text(n)}."
                    dati["messaggio_toast"] = ""
                    d = controlla_vincite(dati)
                    save_stanza_db(stanza, d)
                    return True
                return False

            with col_auto:
                usa_auto = st.toggle("Auto-Play")
                tempo = st.slider("Sec", 3, 20, 6)
                p_bar = st.progress(0); stat = st.empty()
            with col_man:
                if st.button("🎱 ESTRAI MANUALE", type="primary", disabled=usa_auto): 
                    if estrai(): st.rerun()

            if usa_auto and not dati.get("gioco_finito"):
                if len(dati["numeri_tabellone"]) > 0:
                    stat.write(f"⏳ Prossimo numero tra {tempo}s...")
                    for i in range(100): 
                        time.sleep(tempo/100)
                        p_bar.progress(i+1)
                    esito = estrai()
                    if esito: st.rerun()
                else: st.warning("Fine numeri.")

        with st.expander("Tabellone", expanded=True):
            st.markdown("""<style>.g{display:grid;grid-template-columns:repeat(10,1fr);gap:2px}.c{border:1px solid #ccc;text-align:center;padding:5px;font-size:12px;background:#eee}.Ex{background:#d63031;color:white;font-weight:bold;transform:scale(1.1);border:1px solid black}</style>""", unsafe_allow_html=True)
            h = '<div class="g">'
            for i in range(1, 91): h+=f'<div class="c {"Ex" if i in estratti else ""}">{i}</div>'
            st.markdown(h+'</div>', unsafe_allow_html=True)

        st.divider(); st.subheader("Le Tue Cartelle")
        mie = dati["giocatori"].get(mio_nome, [])
        cols = st.columns(3)
        st.markdown("""<style>.ct{width:100%;border-collapse:collapse;margin-bottom:10px;background:white}.cc{border:1px solid #333;width:11%;text-align:center;height:30px;font-weight:bold}.ch{background-color:#d63031;color:white}.ce{background-color:#b2bec3}</style>""", unsafe_allow_html=True)
        for idx, m in enumerate(mie):
            with cols[idx%3]:
                h = f"<b>C. {idx+1}</b><table class='ct'>"
                for r in m:
                    h+="<tr>"
                    for v in r: h+=f"<td class='cc {'ce' if v==0 else ('ch' if v in estratti else '')}'>{v if v!=0 else ''}</td>"
                    h+="</tr>"
                st.markdown(h+"</table>", unsafe_allow_html=True)

        if ruolo == "PLAYER": time.sleep(3); st.rerun()
