import streamlit as st
import random
import time
import json
import os
from datetime import datetime
import mysql.connector
from mysql.connector import Error

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tombola Online MySQL", layout="wide", page_icon="🌍")

# --- GESTIONE DATABASE MYSQL ---

def get_connection():
    """Stabilisce la connessione al DB usando i parametri in st.secrets"""
    return mysql.connector.connect(
        host=st.secrets["mysql"]["host"],
        user=st.secrets["mysql"]["user"],
        password=st.secrets["mysql"]["password"],
        database=st.secrets["mysql"]["database"],
        port=st.secrets["mysql"].get("port", 3306)
    )

def load_stanza_db(nome_stanza):
    """Scarica i dati di UNA specifica stanza dal DB"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)
        query = "SELECT dati_partita FROM stanze_tombola WHERE nome_stanza = %s"
        cursor.execute(query, (nome_stanza,))
        result = cursor.fetchone()
        
        if result:
            # Decodifica il JSON salvato nel DB in un dizionario Python
            return json.loads(result['dati_partita'])
        return None
    except Error as e:
        st.error(f"Errore connessione DB: {e}")
        return None
    finally:
        if conn and conn.is_connected():
            conn.close()

def save_stanza_db(nome_stanza, dati_dizionario):
    """Salva o Aggiorna i dati della stanza nel DB (UPSERT)"""
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Trasforma il dizionario Python in stringa JSON per salvarlo
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
# --- FUNZIONI AUDIO AVANZATE (IT/EN) ---
def speak_dual_language(numero, testo_smorfia):
    """
    Legge il numero in Italiano.
    Legge il titolo in Inglese (Rock) o Italiano (Litfiba/Smorfia classica).
    SE C'È UNA VINCITA ("Attenzione"), FORZA L'ITALIANO.
    """
    if not testo_smorfia: return

    # 1. CONTROLLO VINCITA (Priorità Massima)
    # Se c'è una vincita, dobbiamo parlare italiano, ignorando il resto.
    if "Attenzione" in testo_smorfia or "Vincita" in testo_smorfia:
        lang_title = 'it-IT'
    
    else:
        # 2. CONTROLLO LITFIBA vs ROCK
        ids_italiani = [3, 10, 17, 25, 30, 37, 44, 49, 56, 65, 73, 83, 86, 88, 90]
        try:
            num_int = int(numero)
            lang_title = 'it-IT' if num_int in ids_italiani else 'en-US'
        except:
            lang_title = 'it-IT'
    
    text_safe = testo_smorfia.replace("'", "\\'").replace('"', '\\"')
    u_id = int(time.time() * 1000)
    
    js = f"""
        <div style="display:none" id="audio_{u_id}"></div>
        <script>
            (function() {{
                window.speechSynthesis.cancel();
                
                // Legge il NUMERO (sempre IT)
                // Solo se "numero" è un vero numero e non nullo
                if ('{numero}' !== 'None' && '{numero}' !== '') {{
                    var msgNum = new SpeechSynthesisUtterance('{numero}.');
                    msgNum.lang = 'it-IT';
                    window.speechSynthesis.speak(msgNum);
                }}
                
                // Legge il TESTO (Lingua calcolata sopra)
                var msgTitle = new SpeechSynthesisUtterance('{text_safe}');
                msgTitle.lang = '{lang_title}';
                msgTitle.rate = 0.9; 
                window.speechSynthesis.speak(msgTitle);
            }})();
        </script>
    """
    st.components.v1.html(js, height=0, width=0)
# --- CLASSE GENERATORE CARTELLE ---
class GeneratoreCartelle:
    @staticmethod
    def genera_matrice_3x9():
        matrice = [[0] * 9 for _ in range(3)]
        numeri_usati = set()
        range_colonne = [
            (1, 10), (10, 20), (20, 30), (30, 40), (40, 50),
            (50, 60), (60, 70), (70, 80), (80, 91)
        ]
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
            col_nums = []
            row_indices = []
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
        """Genera un set di 6 cartelle con TUTTI i numeri da 1 a 90"""
        mega_grid = [[0] * 9 for _ in range(18)]
        range_colonne = [
            list(range(1, 10)), list(range(10, 20)), list(range(20, 30)),
            list(range(30, 40)), list(range(40, 50)), list(range(50, 60)),
            list(range(60, 70)), list(range(70, 80)), list(range(80, 91))
        ]
        for c in range(9):
            numeri_col = range_colonne[c][:]
            random.shuffle(numeri_col)
            for r in range(len(numeri_col)):
                mega_grid[r][c] = numeri_col[r]
            col_values = [mega_grid[r][c] for r in range(18)]
            random.shuffle(col_values)
            for r in range(18):
                mega_grid[r][c] = col_values[r]
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
            start_row = i * 3
            end_row = start_row + 3
            sub_matrice = [r[:] for r in mega_grid[start_row:end_row]]
            for c in range(9):
                nums = []
                positions = []
                for r in range(3):
                    if sub_matrice[r][c] != 0:
                        nums.append(sub_matrice[r][c])
                        positions.append(r)
                nums.sort()
                for idx, r in enumerate(positions):
                    sub_matrice[r][c] = nums[idx]
            cartelle_finali.append(sub_matrice)
        return cartelle_finali

# --- FUNZIONE CONTROLLO VINCITE ---
def controlla_vincite(dati_stanza):
    """Controlla le vincite e aggiorna lo stato della stanza"""
    target = dati_stanza.get("obbiettivo_corrente", 2)
    estratti = set(dati_stanza["numeri_estratti"])
    
    nomi_premi = {2: "AMBO", 3: "TERNO", 4: "QUATERNA", 5: "CINQUINA", 15: "TOMBOLA"}
    nome_premio_attuale = nomi_premi.get(target, "TOMBOLA")
    
    vincitori_round = []
    
    for nome_g, cartelle in dati_stanza["giocatori"].items():
        for cartella in cartelle:
            punti_cartella_totali = 0
            win_found = False
            for riga in cartella:
                numeri_riga = [n for n in riga if n > 0]
                punti_riga = sum(1 for n in numeri_riga if n in estratti)
                punti_cartella_totali += punti_riga
                
                if target <= 5 and punti_riga >= target:
                    win_found = True
            
            if target == 15 and punti_cartella_totali == 15:
                win_found = True
                
            if win_found and nome_g not in vincitori_round:
                vincitori_round.append(nome_g)

    if vincitori_round:
        testo_vincitori = ", ".join(vincitori_round)
        msg_win = f"Attenzione! {nome_premio_attuale} per {testo_vincitori}!"
        
        dati_stanza["messaggio_audio"] += f" ... {msg_win}"
        dati_stanza["messaggio_toast"] = f"🏆 {msg_win}"
        
        if target < 5:
            dati_stanza["obbiettivo_corrente"] += 1
        elif target == 5:
            dati_stanza["obbiettivo_corrente"] = 15
        else:
            dati_stanza["messaggio_audio"] += " ... Gioco Finito!"
            dati_stanza["gioco_finito"] = True
    
    return dati_stanza

# --- INTERFACCIA: LOGIN / LOBBY ---
st.title("🌍 TOMBOLA ONLINE MULTIPLAYER (MySQL)")

menu = st.sidebar.radio("Menu", ["🏠 Home", "🆕 Crea Stanza (Banco)", "🎮 Entra in Stanza (Giocatore)"])

if menu == "🏠 Home":
    st.markdown("""
    ### Benvenuto nella Tombola Condivisa su Database!
    I dati sono salvati su un database MySQL esterno, permettendo connessioni stabili da reti diverse.
    """)

# --- CREA STANZA ---
elif menu == "🆕 Crea Stanza (Banco)":
    st.header("Impostazioni Banco")
    with st.form("crea_stanza_form"):
        nome_stanza = st.text_input("Nome Stanza (es. NATALE25)", max_chars=15).upper().strip()
        pwd_banco = st.text_input("Password Amministratore", type="password")
        usa_tombolone = st.checkbox("Il Banco gioca col Tombolone?", value=True)
        submitted = st.form_submit_button("Crea Stanza sul Server")
        
        if submitted:
            if not nome_stanza or not pwd_banco:
                st.error("Dati mancanti.")
            else:
                # Controlla se esiste già
                esistente = load_stanza_db(nome_stanza)
                if esistente:
                    st.warning("Esiste già una stanza con questo nome. Verrà sovrascritta se procedi.")
                
                numeri = list(range(1, 91))
                random.shuffle(numeri)
                
                nuovi_dati = {
                    "admin_pwd": pwd_banco,
                    "created_at": str(datetime.now()),
                    "numeri_tabellone": numeri,
                    "numeri_estratti": [],
                    "ultimo_numero": None,
                    "messaggio_audio": "",
                    "messaggio_toast": "",
                    "giocatori": {},
                    "obbiettivo_corrente": 2,
                    "gioco_finito": False
                }
                
                if usa_tombolone:
                    nuovi_dati["giocatori"]["BANCO"] = GeneratoreCartelle.genera_tombolone_completo()
                
                save_stanza_db(nome_stanza, nuovi_dati)
                
                st.success(f"Stanza '{nome_stanza}' salvata su MySQL!")
                st.session_state.ruolo = "ADMIN"
                st.session_state.stanza_corrente = nome_stanza
                st.session_state.nome_giocatore = "BANCO" if usa_tombolone else "ADMIN"
                st.rerun()

# --- ENTRA IN STANZA ---
elif menu == "🎮 Entra in Stanza (Giocatore)":
    
    if 'stanza_corrente' not in st.session_state:
        col1, col2 = st.columns(2)
        with col1:
            input_stanza = st.text_input("Nome Stanza").upper().strip()
        with col2:
            input_nome = st.text_input("Il tuo Nome").strip().upper()
        
        is_admin = st.checkbox("Sono il Banco (Admin)")
        pwd_input = ""
        if is_admin:
            pwd_input = st.text_input("Password Admin", type="password")
            
        n_cartelle = st.slider("Cartelle desiderate", 1, 6, 1)
        
        if st.button("ENTRA"):
            # Carica dal DB
            dati_stanza = load_stanza_db(input_stanza)
            
            if not dati_stanza:
                st.error("Stanza non trovata sul server.")
            else:
                if is_admin:
                    if pwd_input == dati_stanza["admin_pwd"]:
                        st.session_state.ruolo = "ADMIN"
                        st.session_state.stanza_corrente = input_stanza
                        st.session_state.nome_giocatore = "BANCO" # O admin
                        st.rerun()
                    else:
                        st.error("Password errata.")
                else:
                    # Giocatore
                    if input_nome:
                        # Se nuovo, aggiungi e salva su DB
                        if input_nome not in dati_stanza["giocatori"]:
                            if len(dati_stanza["giocatori"]) >= 15:
                                st.error("Stanza piena.")
                            else:
                                cartelle = [GeneratoreCartelle.genera_matrice_3x9() for _ in range(n_cartelle)]
                                dati_stanza["giocatori"][input_nome] = cartelle
                                save_stanza_db(input_stanza, dati_stanza)
                                
                                st.session_state.ruolo = "PLAYER"
                                st.session_state.stanza_corrente = input_stanza
                                st.session_state.nome_giocatore = input_nome
                                st.rerun()
                        else:
                            # Rientro (rejoin)
                            st.session_state.ruolo = "PLAYER"
                            st.session_state.stanza_corrente = input_stanza
                            st.session_state.nome_giocatore = input_nome
                            st.rerun()
                    else:
                        st.error("Nome mancante.")

    # --- PARTITA IN CORSO ---
    else:
        stanza_nome = st.session_state.stanza_corrente
        ruolo = st.session_state.ruolo
        mio_nome = st.session_state.nome_giocatore
        
        # Caricamento Dati Freschi dal DB
        dati = load_stanza_db(stanza_nome)
        
        if not dati:
            st.error("Errore di connessione o stanza cancellata.")
            if st.button("Esci"):
                st.session_state.clear()
                st.rerun()
            st.stop()
            
        numeri_estratti = dati["numeri_estratti"]
        ultimo = dati["ultimo_numero"]
        messaggio_audio = dati.get("messaggio_audio", "")
        messaggio_toast = dati.get("messaggio_toast", "")
        
        # Header
        c1, c2 = st.columns([3,1])
        with c1: st.markdown(f"## Stanza: **{stanza_nome}** | Utente: *{mio_nome}*")
        with c2: 
            if st.button("🚪 Esci / Logout"):
                st.session_state.clear()
                st.rerun()

        # Toast Vincita (Visualizzato una volta sola grazie al session state locale)
        if messaggio_toast:
            if 'last_toast' not in st.session_state or st.session_state.last_toast != messaggio_toast:
                st.toast(messaggio_toast, icon="🎉")
                st.session_state.last_toast = messaggio_toast
                if dati.get("gioco_finito"):
                    st.balloons()

        # --- SEZIONE ADMIN ---
        if ruolo == "ADMIN":
            st.info(f"👮 PANNELLO BANCO - Si gioca per: {dati.get('obbiettivo_corrente', '?')}")
            col_btn, col_info = st.columns([1, 2])
            with col_btn:
                remaining = len(dati["numeri_tabellone"])
                if remaining > 0 and not dati.get("gioco_finito"):
                    if st.button("🎱 ESTRAI NUMERO", type="primary", use_container_width=True):
                        # 1. Estrai
                        num = dati["numeri_tabellone"].pop(0)
                        dati["numeri_estratti"].append(num)
                        dati["ultimo_numero"] = num
                        
                        smorfia = get_smorfia_text(num)
                        dati["messaggio_audio"] = f"{num}. {smorfia}."
                        dati["messaggio_toast"] = "" # Reset toast precedente
                        
                        # 2. Controlla Vincite
                        dati = controlla_vincite(dati)
                        
                        # 3. Salva su MySQL
                        save_stanza_db(stanza_nome, dati)
                        st.rerun()
                elif dati.get("gioco_finito"):
                    st.success("PARTITA CONCLUSA!")
            with col_info:
                st.write(f"Estratti: {len(numeri_estratti)} / 90")

        # --- AUDIO PLAYER (PER TUTTI) ---
        if 'last_audio_msg' not in st.session_state:
            st.session_state.last_audio_msg = ""
            
        # Controlliamo se c'è un messaggio audio nuovo
        if messaggio_audio and messaggio_audio != st.session_state.last_audio_msg:
            # Recuperiamo i dati puliti per la pronuncia corretta
            try:
                num_corrente = dati.get("ultimo_numero")
                
                # Se il messaggio contiene "Vincita" (es. Ambo!), lo leggiamo tutto in Italiano
                if "Attenzione!" in messaggio_audio:
                     speak_dual_language(num_corrente, messaggio_audio) # Fallback tutto IT o misto
                elif num_corrente:
                    # Caso normale: Numero + Canzone
                    txt_corrente = get_smorfia_text(num_corrente)
                    speak_dual_language(num_corrente, txt_corrente)
            except Exception as e:
                # In caso di errore, non blocchiamo nulla
                print(f"Errore audio: {e}")
                
            st.session_state.last_audio_msg = messaggio_audio
        # --- DISPLAY ULTIMO NUMERO ---
        if ultimo:
            smorfia = get_smorfia_text(ultimo)
            st.markdown(f"""
            <div style="text-align: center; background-color: #2c3e50; color: white; padding: 20px; border-radius: 10px; margin-bottom: 20px;">
                <span style="font-size: 80px; font-weight: bold; color: #e74c3c;">{ultimo}</span><br>
                <span style="font-size: 24px; font-style: italic;">{smorfia}</span>
            </div>
            """, unsafe_allow_html=True)
            
            # Info Premio Corrente
            nomi_premi = {2: "AMBO", 3: "TERNO", 4: "QUATERNA", 5: "CINQUINA", 15: "TOMBOLA"}
            curr = dati.get("obbiettivo_corrente", 2)
            lbl = nomi_premi.get(curr, "FINE")
            st.info(f"Prossimo Obiettivo: **{lbl}**")
        else:
            st.info("In attesa che il Banco inizi...")

        # --- TABELLONE ---
        with st.expander("Tabellone Completo", expanded=True):
            st.markdown("""
            <style>
            .grid-tab { display: grid; grid-template-columns: repeat(10, 1fr); gap: 2px; }
            .cell-tab { border: 1px solid #ccc; text-align: center; padding: 5px; font-size: 12px; background: #eee; }
            .cell-extracted { background: #e74c3c; color: white; font-weight: bold; }
            </style>
            """, unsafe_allow_html=True)
            html = '<div class="grid-tab">'
            for i in range(1, 91):
                cls = "cell-extracted" if i in numeri_estratti else ""
                html += f'<div class="cell-tab {cls}">{i}</div>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

        # --- LE TUE CARTELLE ---
        st.divider()
        st.subheader("Le Tue Cartelle")
        
        mie_cartelle = dati["giocatori"].get(mio_nome, [])
        if not mie_cartelle:
            st.warning("Nessuna cartella trovata.")
        else:
            cols = st.columns(3)
            st.markdown("""
            <style>
            .c-table { 
                width: 100%; 
                border-collapse: collapse; 
                margin-bottom: 10px; 
                background-color: #ffffff !important; /* Forza sfondo bianco */
            }
            .c-cell { 
                border: 1px solid #333; 
                width: 11%; 
                text-align: center; 
                height: 35px; /* Un po' più alte per il dito */
                font-weight: bold; 
                font-size: 18px; /* Numeri più grandi per mobile */
                
                /* COLORI FORZATI PER EVITARE BUG DARK MODE */
                color: #000000 !important; 
                background-color: #ffffff !important;
            }
            
            /* Casella Vinta (Verde) */
            .c-hit { 
                background-color: #2ecc71 !important; 
                color: #ffffff !important; 
                border-color: #27ae60 !important;
            }
            
            /* Casella Vuota (Grigia/Pattern) */
            .c-empty { 
                background-color: #bdc3c7 !important; 
            }
            </style>
            """, unsafe_allow_html=True)
            
            for idx, matrice in enumerate(mie_cartelle):
                with cols[idx % 3]:
                    html_c = f"<b>Cartella {idx+1}</b><table class='c-table'>"
                    for riga in matrice:
                        html_c += "<tr>"
                        for val in riga:
                            if val == 0:
                                html_c += "<td class='c-cell c-empty'></td>"
                            else:
                                hit = "c-hit" if val in numeri_estratti else ""
                                html_c += f"<td class='c-cell {hit}'>{val}</td>"
                        html_c += "</tr>"
                    html_c += "</table>"
                    st.markdown(html_c, unsafe_allow_html=True)

        # --- AUTO REFRESH (Solo Giocatori) ---
        if ruolo == "PLAYER":
            time.sleep(3)
            st.rerun()
