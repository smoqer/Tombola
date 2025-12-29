import streamlit as st
import random
import time
import base64
from gtts import gTTS
from io import BytesIO

# --- IMPORT SMORFIA ---
try:
    from smorfia_dati import SMORFIA
except ImportError:
    SMORFIA = {}

# --- LOGICA GENERATORE CARTELLE AVANZATA ---
class GeneratoreCartelle:
    @staticmethod
    def genera_matrice_3x9():
        """Genera una cartella singola casuale (per i giocatori)"""
        matrice = [[0] * 9 for _ in range(3)]
        numeri_usati = set()
        range_colonne = [
            (1, 10), (10, 20), (20, 30), (30, 40), (40, 50),
            (50, 60), (60, 70), (70, 80), (80, 91)
        ]
        # Riempimento base
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
        # Ordinamento colonne
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
        """
        Genera un set di 6 cartelle che contengono TUTTI i numeri da 1 a 90 
        senza ripetizioni (Tombolone/Cartellone classico).
        """
        # 1. Creiamo una "mega griglia" da 18 righe (6 cartelle x 3 righe) x 9 colonne
        mega_grid = [[0] * 9 for _ in range(18)]
        
        # 2. Riempiamo le colonne con tutti i numeri 1-90
        range_colonne = [
            list(range(1, 10)),   # Col 0: 1-9 (9 num)
            list(range(10, 20)),  # Col 1: 10-19 (10 num)
            list(range(20, 30)),
            list(range(30, 40)),
            list(range(40, 50)),
            list(range(50, 60)),
            list(range(60, 70)),
            list(range(70, 80)),
            list(range(80, 91))   # Col 8: 80-90 (11 num)
        ]

        # Distribuzione iniziale dei numeri nelle colonne della mega griglia
        for c in range(9):
            numeri_col = range_colonne[c][:]
            random.shuffle(numeri_col)
            # Riempiamo le prime N righe della colonna c
            for r in range(len(numeri_col)):
                mega_grid[r][c] = numeri_col[r]
            # Mescoliamo le righe della colonna per non avere i numeri tutti in alto
            col_values = [mega_grid[r][c] for r in range(18)]
            random.shuffle(col_values)
            for r in range(18):
                mega_grid[r][c] = col_values[r]

        # 3. Bilanciamento Righe: Ogni riga deve avere ESATTAMENTE 5 numeri
        # Algoritmo di scambio: finché ci sono righe non valide, sposta numeri
        while True:
            row_counts = [sum(1 for x in row if x > 0) for row in mega_grid]
            if all(c == 5 for c in row_counts):
                break # Tutte le righe sono perfette
            
            # Trova una riga con troppi numeri e una con pochi numeri
            row_over = next(i for i, c in enumerate(row_counts) if c > 5)
            row_under = next(i for i, c in enumerate(row_counts) if c < 5)
            
            # Trova una colonna dove row_over ha un numero e row_under ha 0
            # e scambia il numero
            for c in range(9):
                if mega_grid[row_over][c] > 0 and mega_grid[row_under][c] == 0:
                    mega_grid[row_under][c] = mega_grid[row_over][c]
                    mega_grid[row_over][c] = 0
                    break
        
        # 4. Ordinamento: Ordiniamo i numeri verticalmente all'interno di ogni cartella (3 righe)
        cartelle_finali = []
        for i in range(6):
            start_row = i * 3
            end_row = start_row + 3
            # Estrai la sottomatrice
            sub_matrice = [r[:] for r in mega_grid[start_row:end_row]]
            
            # Ordina le colonne della sottomatrice
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

# --- FUNZIONI DI SUPPORTO ---
def autoplay_audio(text):
    if not text: return
    try:
        sound_file = BytesIO()
        tts = gTTS(text, lang='it')
        tts.write_to_fp(sound_file)
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

# --- INIZIALIZZAZIONE SESSIONE ---
if 'numeri_tabellone' not in st.session_state:
    nums = list(range(1, 91))
    random.shuffle(nums)
    st.session_state.numeri_tabellone = nums
    st.session_state.numeri_estratti = []
    st.session_state.ultimo_numero = None
    st.session_state.messaggio_audio = ""
    st.session_state.giocatori = [] 
    st.session_state.partita_iniziata = False

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="Tombola Web Ultimate", layout="wide", page_icon="🎄")

# --- SIDEBAR: CONFIGURAZIONE GIOCATORI ---
with st.sidebar:
    st.header("⚙️ Configurazione")
    
    if not st.session_state.partita_iniziata:
        st.info("Configura i giocatori prima di iniziare.")
        
        # Input dinamici FUORI dal form per refresh istantaneo
        n_giocatori = st.number_input("Numero Giocatori Umani", min_value=0, max_value=20, value=1)
        st.write("---")

        with st.form("setup_form"):
            st.write("Dettagli Giocatori:")
            
            dati_temp = []
            for i in range(n_giocatori):
                st.markdown(f"**Giocatore {i+1}**")
                col1, col2 = st.columns([2, 1])
                nome = col1.text_input(f"Nome", value=f"Giocatore {i+1}", key=f"n_{i}")
                n_cart = col2.number_input(f"Cartelle", min_value=1, max_value=6, value=1, key=f"c_{i}")
                dati_temp.append({'nome': nome, 'n_cartelle': n_cart})
            
            if n_giocatori > 0:
                st.markdown("---")
            
            st.write("Opzioni Banco:")
            banco_si = st.checkbox("Aggiungi TOMBOLONE (Copre tutti i 90 numeri)", value=True)
            
            submitted = st.form_submit_button("✅ INIZIA PARTITA", type="primary")
            
            if submitted:
                if n_giocatori == 0 and not banco_si:
                    st.error("Devi avere almeno un giocatore o attivare il Banco!")
                else:
                    st.session_state.giocatori = []
                    
                    # 1. Aggiunta Banco (Usa il NUOVO generatore Tombolone)
                    if banco_si:
                        # Qui chiamiamo la funzione speciale che genera 6 cartelle complementari
                        cartelle_banco = GeneratoreCartelle.genera_tombolone_completo()
                        st.session_state.giocatori.append({'nome': '🏦 TOMBOLONE', 'cartelle': cartelle_banco})
                    
                    # 2. Aggiunta Giocatori Umani (Usa il generatore casuale standard)
                    for d in dati_temp:
                        cartelle = [GeneratoreCartelle.genera_matrice_3x9() for _ in range(d['n_cartelle'])]
                        st.session_state.giocatori.append({'nome': d['nome'], 'cartelle': cartelle})
                    
                    st.session_state.partita_iniziata = True
                    st.rerun()
    else:
        st.success("Partita in corso!")
        if st.button("❌ Resetta Tutto"):
            st.session_state.clear()
            st.rerun()
        
        st.write("---")
        st.write("### Riepilogo")
        for g in st.session_state.giocatori:
            tipo = "Set Completo (1-90)" if g['nome'] == '🏦 TOMBOLONE' else "Casuali"
            st.write(f"- **{g['nome']}**: {len(g['cartelle'])} cartelle ({tipo})")

# --- INTERFACCIA PRINCIPALE ---

st.markdown("<h1 style='text-align: center; color: #c0392b;'>🎄 TOMBOLA DI NATALE 🎄</h1>", unsafe_allow_html=True)

if not st.session_state.partita_iniziata:
    st.warning("👈 Usa la barra laterale a sinistra per configurare i giocatori e iniziare!")
else:
    # --- AREA DI GIOCO ---
    col_comandi, col_tabellone = st.columns([1, 2])

    with col_comandi:
        st.subheader("Estrazione")
        
        remaining = len(st.session_state.numeri_tabellone)
        
        if remaining > 0:
            if st.button("🎱 ESTRAI NUMERO", type="primary", use_container_width=True):
                num = st.session_state.numeri_tabellone.pop(0)
                st.session_state.numeri_estratti.append(num)
                st.session_state.ultimo_numero = num
                
                smorfia = get_smorfia_text(num)
                st.session_state.messaggio_audio = f"{num}. {smorfia}"
                st.rerun()
        else:
            st.success("Tabellone Completato!")

        if st.session_state.ultimo_numero:
            num = st.session_state.ultimo_numero
            smorfia = get_smorfia_text(num)
            
            st.markdown(f"""
            <div style="text-align: center; background-color: #f1f2f6; padding: 20px; border-radius: 15px; border: 3px solid #e74c3c; margin-top: 20px;">
                <div style="font-size: 90px; font-weight: bold; color: #c0392b; line-height: 1;">{num}</div>
                <div style="font-size: 22px; color: #2980b9; margin-top: 10px; font-style: italic;">"{smorfia}"</div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.messaggio_audio:
                autoplay_audio(st.session_state.messaggio_audio)
                st.session_state.messaggio_audio = ""

    with col_tabellone:
        st.subheader("Tabellone")
        st.markdown("""
        <style>
        .grid-tab { display: grid; grid-template-columns: repeat(10, 1fr); gap: 3px; }
        .cell-tab {
            border: 1px solid #bdc3c7; border-radius: 4px; text-align: center; 
            padding: 5px 0; font-weight: bold; font-size: 14px; color: #ecf0f1; background-color: #95a5a6;
        }
        .cell-tab.active { background-color: #e74c3c; color: white; transform: scale(1.1); border-color: #c0392b; z-index: 10;}
        </style>
        """, unsafe_allow_html=True)

        html = '<div class="grid-tab">'
        for i in range(1, 91):
            cls = "active" if i in st.session_state.numeri_estratti else ""
            html += f'<div class="cell-tab {cls}">{i}</div>'
        html += '</div>'
        st.markdown(html, unsafe_allow_html=True)

    # --- VISUALIZZAZIONE CARTELLE GIOCATORI ---
    st.divider()
    st.subheader("🏆 Situazione Giocatori")
    
    st.markdown("""
    <style>
    .p-card { border: 2px solid #34495e; border-radius: 5px; margin-bottom: 10px; background: #fff; }
    .p-name { background: #34495e; color: white; padding: 5px; text-align: center; font-weight: bold; }
    .p-table { width: 100%; border-collapse: collapse; }
    .p-cell { 
        border: 1px solid #bdc3c7; height: 30px; width: 11%; text-align: center; font-weight: bold; color: #2c3e50;
    }
    .p-empty { background-image: linear-gradient(45deg, #eee 25%, white 25%, white 50%, #eee 50%, #eee 75%, white 75%, white 100%); background-size: 10px 10px; }
    .p-hit { background-color: #2ecc71 !important; color: white !important; }
    </style>
    """, unsafe_allow_html=True)

    if st.session_state.giocatori:
        nomi_tabs = [g['nome'] for g in st.session_state.giocatori]
        tabs = st.tabs(nomi_tabs)
        
        for i, tab in enumerate(tabs):
            giocatore = st.session_state.giocatori[i]
            with tab:
                cols = st.columns(3) 
                for idx_c, matrice in enumerate(giocatore['cartelle']):
                    with cols[idx_c % 3]:
                        html_c = f"""
                        <div class="p-card">
                            <div class="p-name">Cartella {idx_c + 1}</div>
                            <table class="p-table">
                        """
                        for riga in matrice:
                            html_c += "<tr>"
                            for val in riga:
                                if val == 0:
                                    html_c += '<td class="p-cell p-empty"></td>'
                                else:
                                    classe_extra = "p-hit" if val in st.session_state.numeri_estratti else ""
                                    html_c += f'<td class="p-cell {classe_extra}">{val}</td>'
                            html_c += "</tr>"
                        html_c += "</table></div>"
                        st.markdown(html_c, unsafe_allow_html=True)
