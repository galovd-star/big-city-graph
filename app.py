import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from pyvis.network import Network
from streamlit_gsheets import GSheetsConnection
import plotly.express as px
import json
import base64
from io import BytesIO
from PIL import Image
import html
import docx

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(layout="wide", page_title="БИГ СИТИ: Экосистема Вселенной", initial_sidebar_state="expanded")

# 🔗 ВСТАВЬТЕ СЮДА ССЫЛКУ НА ВАШУ GOOGLE ТАБЛИЦУ (внутри кавычек)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MyQ3vqstgSAarY9NtsAl1f1tnlbgmi-2iljHMf97zBM/edit?gid=0#gid=0"

if SHEET_URL == "ВСТАВЬТЕ_ССЫЛКУ_СЮДА":
    st.error("⚠️ Откройте код app.py на GitHub и вставьте настоящую ссылку на вашу Google Таблицу в переменную SHEET_URL (строка 19).")
    st.stop()

# --- КАСТОМНЫЙ ДИЗАЙН И СТИЛИ КАРТОЧЕК ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #121212; }
    [data-testid="stSidebar"] { background-color: #1a1a24 !important; border-right: 1px solid #333344; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    h1, h2, h3 { color: #00d4ff !important; font-family: 'Courier New', Courier, monospace; }
    .stMarkdown p, .stText { color: #dcdcdc !important; font-size: 16px; }
    
    /* Стили для карточек галереи */
    .game-card {
        background-color: #1b1b26;
        border: 1px solid #33334d;
        border-radius: 12px;
        padding: 14px;
        margin-bottom: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5);
    }
    .game-card-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 6px; }
    .game-card-type { font-size: 11px; padding: 2px 8px; border-radius: 4px; background-color: #2b2b3d; color: #00d4ff; text-transform: uppercase; font-weight: bold; }
    .game-card-title { color: #ffffff; font-size: 22px; font-weight: bold; font-family: 'Courier New', monospace; letter-spacing: 1px; margin-bottom: 6px; }
    
    /* Сетка показателей С, Л, М, С */
    .stats-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 6px;
        background-color: #232334;
        padding: 8px 10px;
        border-radius: 8px;
        margin: 8px 0;
        font-family: 'Courier New', monospace;
        font-size: 14px;
        border-left: 3px solid #00d4ff;
    }
    .stat-item { color: #e0e0e0; }
    .stat-letter { color: #00d4ff; font-weight: bold; margin-right: 4px; }
    
    /* Плашка класса снизу карточки */
    .alignment-badge {
        text-align: center;
        padding: 5px;
        border-radius: 6px;
        font-weight: bold;
        font-size: 13px;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 8px;
        margin-bottom: 6px;
    }
    .align-hero { background-color: rgba(77, 166, 255, 0.2); color: #4da6ff; border: 1px solid #4da6ff; }
    .align-villain { background-color: rgba(255, 77, 77, 0.2); color: #ff4d4d; border: 1px solid #ff4d4d; }
    .align-neutral { background-color: rgba(255, 204, 0, 0.2); color: #ffcc00; border: 1px solid #ffcc00; }

    /* Плашки связей внутри карточки */
    .rel-pill {
        padding: 5px 10px;
        border-radius: 6px;
        margin-bottom: 5px;
        font-size: 13px;
        display: flex;
        justify-content: space-between;
    }
    .rel-ally { background-color: rgba(77, 166, 255, 0.15); border-left: 3px solid #4da6ff; color: #d9ecff; }
    .rel-enemy { background-color: rgba(255, 77, 77, 0.15); border-left: 3px solid #ff4d4d; color: #ffd9d9; }
    .rel-neutral { background-color: rgba(160, 160, 160, 0.15); border-left: 3px solid #999999; color: #e0e0e0; }
    
    /* Стили для скрытых заголовков и подзаголовков в Сценариях */
    details.lvl1 { background-color: #1b1b26; border-left: 4px solid #00d4ff; border-radius: 6px; padding: 10px 15px; margin: 12px 0; }
    details.lvl1 > summary { font-size: 20px; font-weight: bold; color: #00d4ff; cursor: pointer; outline: none; }
    details.lvl2 { background-color: #232332; border-left: 3px solid #ffcc00; border-radius: 6px; padding: 8px 14px; margin: 10px 0 10px 15px; }
    details.lvl2 > summary { font-size: 17px; font-weight: bold; color: #ffcc00; cursor: pointer; outline: none; }
    details.lvl3 { background-color: #2b2b3c; border-left: 3px solid #ff66b2; border-radius: 6px; padding: 6px 12px; margin: 8px 0 8px 25px; }
    details.lvl3 > summary { font-size: 15px; font-weight: bold; color: #ff66b2; cursor: pointer; outline: none; }
    .script-body { padding-top: 8px; color: #e0e0e0; line-height: 1.6; white-space: pre-wrap; }
</style>
""", unsafe_allow_html=True)

PALETTE = ["#ff4d4d", "#4da6ff", "#9933ff", "#33cc33", "#ffcc00", "#ff66b2", "#339999", "#ff9933", "#996633", "#6699ff"]

# --- ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

CARD_COLS = [
    'Name', 'Card_Type', 'Alignment', 'Faction',
    'Strength', 'Agility', 'Mastery', 'Wit',
    'Description', 'Image_Data', 'Linked_Character'
]

def safe_read_sheet(worksheet_name, default_cols):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name)
        df = df.dropna(how='all')
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=default_cols)
        for col in default_cols:
            if col not in df.columns:
                if col in ['Strength', 'Agility', 'Mastery', 'Wit']:
                    df[col] = 0
                elif col == 'Card_Type':
                    df[col] = 'Персонаж'
                elif col == 'Alignment':
                    df[col] = 'Нейтралитет'
                elif col in ["Content", "Image_Data", "Заметки", "Description", "Linked_Character"]:
                    df[col] = ""
                else:
                    df[col] = "Не указано"
        return df.fillna("")
    except Exception:
        return pd.DataFrame(columns=default_cols)

@st.cache_data(ttl=5)
def load_all_data():
    nodes = safe_read_sheet("Nodes", ['Имя / Название персонажа', 'Категория плана', 'Пол', 'Группировка', 'Заметки']).replace("", "Не указано")
    edges = safe_read_sheet("Edges", ['Source', 'Target', 'Weight', 'Type'])
    archives = safe_read_sheet("Archives", ['Title', 'Category', 'Content'])
    cards = safe_read_sheet("Cards", CARD_COLS)
    for stat_col in ['Strength', 'Agility', 'Mastery', 'Wit']:
        cards[stat_col] = pd.to_numeric(cards[stat_col], errors='coerce').fillna(0).astype(int)
    scripts = safe_read_sheet("Scripts", ['Title', 'Act', 'Status', 'Content'])
    return nodes, edges, archives, cards, scripts

@st.cache_data(ttl=5)
def load_config():
    try:
        cfg = conn.read(spreadsheet=SHEET_URL, worksheet="Config")
        if not cfg.empty and 'Settings' in cfg.columns:
            val = cfg['Settings'].iloc[0]
            if pd.notna(val) and str(val).strip() != "":
                return json.loads(val)
    except Exception:
        pass
    return {"colors": {}, "options": {}}

def save_sheet(worksheet_name, df):
    try:
        conn.update(spreadsheet=SHEET_URL, worksheet=worksheet_name, data=df)
        st.cache_data.clear()
    except Exception as e:
        st.error(f"⚠️ Ошибка сохранения в лист '{worksheet_name}'. Проверьте наличие листа в таблице! Детали: {e}")

def save_config_to_cloud(config_dict):
    df = pd.DataFrame({"Settings": [json.dumps(config_dict, ensure_ascii=False)]})
    save_sheet("Config", df)

# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ СВЯЗЕЙ И КАРТОЧЕК ---
def get_character_relations(char_name, edges_df):
    if not char_name or edges_df.empty:
        return []
    char_clean = str(char_name).strip()
    rels = []
    for _, row in edges_df.iterrows():
        src = str(row.get('Source', '')).strip()
        tgt = str(row.get('Target', '')).strip()
        rtype = str(row.get('Type', 'Связь')).strip()
        try:
            w = int(float(row.get('Weight', 1)))
        except ValueError:
            w = 1
        if src == char_clean:
            rels.append({"partner": tgt, "type": rtype, "weight": w, "dir": "→"})
        elif tgt == char_clean:
            rels.append({"partner": src, "type": rtype, "weight": w, "dir": "←"})
    return rels

def resolve_linked_character(card_row, valid_chars_list):
    explicit_link = str(card_row.get('Linked_Character', '')).strip()
    if explicit_link and explicit_link != "— Нет привязки —" and explicit_link in valid_chars_list:
        return explicit_link
    card_name = str(card_row.get('Name', '')).strip()
    for ch in valid_chars_list:
        if ch.strip().lower() == card_name.lower():
            return ch
    return None

def get_cards_for_character(char_name, cards_df):
    if cards_df.empty or not char_name:
        return pd.DataFrame(columns=CARD_COLS)
    clean_name = str(char_name).strip().lower()
    mask = (
        (cards_df['Linked_Character'].astype(str).str.strip().str.lower() == clean_name) |
        (cards_df['Name'].astype(str).str.strip().str.lower() == clean_name)
    )
    return cards_df[mask]

# --- ЧТЕНИЕ ФАЙЛОВ С КОМПЬЮТЕРА (.DOCX, .TXT, .MD) ---
def read_uploaded_document(uploaded_file):
    filename = uploaded_file.name
    base_title = filename.rsplit('.', 1)[0]
    if filename.lower().endswith('.docx'):
        doc = docx.Document(uploaded_file)
        lines = []
        for p in doc.paragraphs:
            text = p.text.strip()
            if not text:
                lines.append("")
                continue
            style_name = p.style.name.lower() if p.style else ""
            if 'heading 1' in style_name or 'заголовок 1' in style_name:
                lines.append(f"# {text}")
            elif 'heading 2' in style_name or 'заголовок 2' in style_name:
                lines.append(f"## {text}")
            elif 'heading 3' in style_name or 'заголовок 3' in style_name:
                lines.append(f"### {text}")
            else:
                lines.append(p.text)
        return base_title, "\n".join(lines)
    else:
        raw_bytes = uploaded_file.read()
        try:
            content = raw_bytes.decode('utf-8')
        except UnicodeDecodeError:
            content = raw_bytes.decode('cp1251', errors='replace')
        return base_title, content

# --- СЖАТИЕ ФОТО КАРТОЧЕК ---
def compress_uploaded_image(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((420, 580))
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=72, optimize=True)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"

# --- ПАРСИНГ СКРЫТЫХ ЗАГОЛОВКОВ И ПОДЗАГОЛОВКОВ ---
def render_script_with_spoilers(raw_text):
    lines = raw_text.split('\n')
    html_out = []
    open_levels = []

    def close_until(target_level):
        while open_levels and open_levels[-1] >= target_level:
            html_out.append("</div></details>")
            open_levels.pop()

    for line in lines:
        stripped = line.strip()
        if stripped.startswith('### '):
            close_until(3)
            title = html.escape(stripped[4:].strip())
            html_out.append(f'<details class="lvl3"><summary>🔹 {title}</summary><div class="script-body">')
            open_levels.append(3)
        elif stripped.startswith('## '):
            close_until(2)
            title = html.escape(stripped[3:].strip())
            html_out.append(f'<details class="lvl2"><summary>📂 {title}</summary><div class="script-body">')
            open_levels.append(2)
        elif stripped.startswith('# '):
            close_until(1)
            title = html.escape(stripped[2:].strip())
            html_out.append(f'<details class="lvl1"><summary>📁 {title}</summary><div class="script-body">')
            open_levels.append(1)
        else:
            html_out.append(html.escape(line) + "<br>")

    close_until(1)
    return "".join(html_out)

# --- ВСТРАИВАНИЕ ИНТЕРАКТИВНОЙ КАРТОЧКИ ПРИ НАВЕДЕНИИ В HTML ГРАФА ---
def inject_card_hover_into_graph(raw_html, node_popup_dict):
    popup_json = json.dumps(node_popup_dict, ensure_ascii=False)
    custom_injection = f"""
    <style>
        #graph-card-popup {{
            position: fixed;
            display: none;
            z-index: 99999;
            width: 265px;
            background: rgba(24, 24, 36, 0.96);
            border: 1px solid #00d4ff;
            border-radius: 12px;
            padding: 12px;
            color: #ffffff;
            font-family: 'Segoe UI', Tahoma, sans-serif;
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.85), 0 0 12px rgba(0, 212, 255, 0.25);
            pointer-events: none;
            backdrop-filter: blur(6px);
        }}
        .gcp-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 11px;
            margin-bottom: 4px;
        }}
        .gcp-faction {{ color: #ffcc00; font-weight: bold; text-transform: uppercase; }}
        .gcp-type {{ background: #2b2b3d; color: #00d4ff; padding: 2px 6px; border-radius: 4px; font-weight: bold; }}
        .gcp-title {{
            font-family: 'Courier New', monospace;
            font-size: 18px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 6px;
            border-bottom: 1px solid #33334d;
            padding-bottom: 4px;
        }}
        .gcp-img-wrap {{
            width: 100%;
            max-height: 195px;
            overflow: hidden;
            border-radius: 8px;
            margin-bottom: 8px;
            text-align: center;
            background: #12121a;
        }}
        .gcp-img-wrap img {{
            width: 100%;
            height: 195px;
            object-fit: cover;
            display: block;
        }}
        .gcp-stats {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 4px 8px;
            background: #232334;
            padding: 6px 9px;
            border-radius: 6px;
            font-family: 'Courier New', monospace;
            font-size: 13px;
            border-left: 3px solid #00d4ff;
            margin-bottom: 6px;
        }}
        .gcp-stat-let {{ color: #00d4ff; font-weight: bold; margin-right: 4px; }}
        .gcp-align {{
            text-align: center;
            padding: 4px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 11px;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 6px;
        }}
        .gcp-hero {{ background: rgba(77, 166, 255, 0.2); color: #4da6ff; border: 1px solid #4da6ff; }}
        .gcp-villain {{ background: rgba(255, 77, 77, 0.2); color: #ff4d4d; border: 1px solid #ff4d4d; }}
        .gcp-neutral {{ background: rgba(255, 204, 0, 0.2); color: #ffcc00; border: 1px solid #ffcc00; }}
        .gcp-desc {{ font-size: 12px; color: #cccccc; margin-bottom: 6px; line-height: 1.35; }}
        .gcp-bonuses {{ font-size: 11px; color: #ff99cc; margin-bottom: 6px; }}
        .gcp-lore {{
            font-size: 11px;
            color: #aaaaaa;
            border-top: 1px solid #2e2e42;
            padding-top: 5px;
            line-height: 1.4;
        }}
    </style>

    <div id="graph-card-popup"></div>

    <script type="text/javascript">
        (function() {{
            const popupData = {popup_json};
            const popupEl = document.getElementById('graph-card-popup');
            let isPinned = false;

            function escapeHtml(str) {{
                if (!str) return "";
                return String(str).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
            }}

            function buildCardHtml(nodeId) {{
                const info = popupData[nodeId];
                if (!info) return "";

                let html = "";
                if (info.has_card) {{
                    let alignClass = "gcp-neutral";
                    if (info.alignment === "Герой") alignClass = "gcp-hero";
                    else if (info.alignment === "Злодей") alignClass = "gcp-villain";

                    html += `<div class="gcp-header">
                                <span class="gcp-faction">${{escapeHtml(info.faction)}}</span>
                                <span class="gcp-type">${{escapeHtml(info.card_type)}}</span>
                             </div>`;
                    html += `<div class="gcp-title">${{escapeHtml(info.card_name)}}</div>`;
                    if (info.image) {{
                        html += `<div class="gcp-img-wrap"><img src="${{info.image}}" alt="card"/></div>`;
                    }}
                    html += `<div class="gcp-stats">
                                <div><span class="gcp-stat-let">С</span>${{info.str}}</div>
                                <div><span class="gcp-stat-let">Л</span>${{info.agi}}</div>
                                <div><span class="gcp-stat-let">М</span>${{info.mas}}</div>
                                <div><span class="gcp-stat-let">С</span>${{info.wit}}</div>
                             </div>`;
                    html += `<div class="gcp-align ${{alignClass}}">${{escapeHtml(info.alignment)}}</div>`;
                    if (info.desc) {{
                        html += `<div class="gcp-desc">${{escapeHtml(info.desc)}}</div>`;
                    }}
                    if (info.bonuses && info.bonuses.length > 0) {{
                        html += `<div class="gcp-bonuses">🎁 <b>Бонусы:</b> ${{escapeHtml(info.bonuses.join(', '))}}</div>`;
                    }}
                }} else {{
                    html += `<div class="gcp-title">👤 ${{escapeHtml(nodeId)}}</div>`;
                }}

                if (info.lore && info.lore.length > 0) {{
                    html += `<div class="gcp-lore">` + info.lore.map(item => `▪ ${{escapeHtml(item)}}`).join('<br>') + `</div>`;
                }}
                return html;
            }}

            function positionPopup(nodeId) {{
                if (typeof network === 'undefined') return;
                const pos = network.getPositions([nodeId])[nodeId];
                if (!pos) return;
                const domPos = network.canvasToDOM(pos);
                const pad = 18;
                let left = domPos.x + 24;
                let top = domPos.y - 40;

                const rect = popupEl.getBoundingClientRect();
                const w = rect.width || 275;
                const h = rect.height || 360;

                if (left + w + pad > window.innerWidth) {{
                    left = Math.max(pad, domPos.x - w - 24);
                }}
                if (top + h + pad > window.innerHeight) {{
                    top = Math.max(pad, window.innerHeight - h - pad);
                }}
                if (top < pad) top = pad;

                popupEl.style.left = left + 'px';
                popupEl.style.top = top + 'px';
            }}

            if (typeof network !== 'undefined') {{
                network.setOptions({{ interaction: {{ hover: true, tooltipDelay: 50 }} }});

                network.on("hoverNode", function(params) {{
                    if (isPinned) return;
                    const content = buildCardHtml(params.node);
                    if (content) {{
                        popupEl.innerHTML = content;
                        popupEl.style.display = 'block';
                        positionPopup(params.node);
                    }}
                }});

                network.on("blurNode", function() {{
                    if (!isPinned) {{
                        popupEl.style.display = 'none';
                    }}
                }});

                network.on("selectNode", function(params) {{
                    if (params.nodes.length > 0) {{
                        const nodeId = params.nodes[0];
                        const content = buildCardHtml(nodeId);
                        if (content) {{
                            isPinned = true;
                            popupEl.innerHTML = content;
                            popupEl.style.display = 'block';
                            positionPopup(nodeId);
                        }}
                    }}
                }});

                network.on("deselectNode", function() {{
                    isPinned = false;
                    popupEl.style.display = 'none';
                }});

                network.on("dragStart", function() {{
                    if (!isPinned) popupEl.style.display = 'none';
                }});
            }}
        }})();
    </script>
    """
    return raw_html.replace("</body>", custom_injection + "\n</body>")

# --- ИНИЦИАЛИЗАЦИЯ ДАННЫХ ---
if 'nodes' not in st.session_state:
    n, e, a, c, s = load_all_data()
    st.session_state['nodes'] = n
    st.session_state['edges'] = e
    st.session_state['archives'] = a
    st.session_state['cards'] = c
    st.session_state['scripts'] = s

if 'config' not in st.session_state:
    st.session_state['config'] = load_config()
if 'colors' not in st.session_state['config']: st.session_state['config']['colors'] = {}
if 'options' not in st.session_state['config']: st.session_state['config']['options'] = {}

# --- БОКОВОЕ МЕНЮ НАВИГАЦИИ ---
st.sidebar.title("🌆 БИГ СИТИ")
app_mode = st.sidebar.radio(
    "Навигация по экосистеме:",
    [
        "🌐 Персонажи и Граф",
        "🃏 Галерея Карточек",
        "📚 Архивы и Лор",
        "🎬 Сценарии и Сюжет"
    ]
)

st.sidebar.write("---")
if st.sidebar.button("🔄 Синхронизировать с облаком", use_container_width=True):
    st.cache_data.clear()
    n, e, a, c, s = load_all_data()
    st.session_state['nodes'], st.session_state['edges'] = n, e
    st.session_state['archives'], st.session_state['cards'], st.session_state['scripts'] = a, c, s
    st.session_state['config'] = load_config()
    st.rerun()


# ==============================================================================
# МОДУЛЬ 1: ПЕРСОНАЖИ, ГРАФ, ДОСЬЕ И СТАТИСТИКА
# ==============================================================================
if app_mode == "🌐 Персонажи и Граф":
    st.title("🌐 База Персонажей и Карта Связей")
    tab_graph, tab_dossier, tab_chars, tab_edges, tab_stats = st.tabs([
        "🕸 Интерактивный Граф", "🗂 Досье Персонажа", "👤 Таблица Персонажей", "🔗 Таблица Связей", "📊 Статистика"
    ])

    with tab_dossier:
        all_chars_list = st.session_state['nodes']['Имя / Название персонажа'].dropna().unique().tolist()
        if not all_chars_list:
            st.info("База персонажей пока пуста.")
        else:
            sel_hero = st.selectbox("🔍 Выберите персонажа для просмотра полного досье:", all_chars_list)
            hero_row = st.session_state['nodes'][st.session_state['nodes']['Имя / Название персонажа'] == sel_hero].iloc[0]
            
            d_col1, d_col2 = st.columns([1.2, 1.8])
            with d_col1:
                st.subheader(f"👤 {sel_hero}")
                for col_n in st.session_state['nodes'].columns:
                    if col_n != 'Имя / Название персонажа':
                        st.markdown(f"**{col_n}:** {hero_row.get(col_n, 'Не указано')}")
                
                st.write("---")
                st.markdown("#### 🔗 Связи на графе")
                hero_rels = get_character_relations(sel_hero, st.session_state['edges'])
                if hero_rels:
                    for r in hero_rels:
                        t_low = r['type'].lower()
                        css_c = "rel-enemy" if t_low in ['вражда', 'конфликт'] else ("rel-ally" if t_low in ['союз', 'родство', 'подчинение'] else "rel-neutral")
                        st.markdown(f"""
                        <div class="rel-pill {css_c}">
                            <span><b>{html.escape(r['partner'])}</b> ({html.escape(r['type'])})</span>
                            <span>Сила: {'⭐' * r['weight']}</span>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.caption("У этого персонажа пока нет зафиксированных связей.")

            with d_col2:
                st.subheader("🃏 Привязанные карточки и бонусы")
                linked_cards = get_cards_for_character(sel_hero, st.session_state['cards'])
                if not linked_cards.empty:
                    c_cols = st.columns(2)
                    for idx_c, (_, crd) in enumerate(linked_cards.iterrows()):
                        with c_cols[idx_c % 2]:
                            al_str = str(crd['Alignment'])
                            al_cls = "align-hero" if al_str == "Герой" else ("align-villain" if al_str == "Злодей" else "align-neutral")
                            st.markdown(f"""
                            <div class="game-card">
                                <div class="game-card-header">
                                    <span style="color:#ffcc00; font-size:12px;">{html.escape(str(crd['Faction']))}</span>
                                    <span class="game-card-type">{html.escape(str(crd['Card_Type']))}</span>
                                </div>
                                <div class="game-card-title">{html.escape(str(crd['Name']))}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            if crd['Image_Data']:
                                st.image(crd['Image_Data'], use_container_width=True)
                            st.markdown(f"""
                            <div class="stats-grid">
                                <div class="stat-item"><span class="stat-letter">С</span>{int(crd['Strength'])}</div>
                                <div class="stat-item"><span class="stat-letter">Л</span>{int(crd['Agility'])}</div>
                                <div class="stat-item"><span class="stat-letter">М</span>{int(crd['Mastery'])}</div>
                                <div class="stat-item"><span class="stat-letter">С</span>{int(crd['Wit'])}</div>
                            </div>
                            <div class="alignment-badge {al_cls}">{html.escape(al_str)}</div>
                            """, unsafe_allow_html=True)
                            if crd['Description']:
                                st.caption(crd['Description'])
                else:
                    st.info("К этому персонажу пока не привязано ни одной игровой карточки в Галерее.")

    with tab_stats:
        st.subheader("Аналитика и распределение сил")
        m1, m2, m3 = st.columns(3)
        m1.metric("👥 Всего персонажей", len(st.session_state['nodes']))
        m2.metric("🔗 Всего связей", len(st.session_state['edges']))
        color_cols = [c for c in st.session_state['nodes'].columns if c not in ["Имя / Название персонажа", "Заметки"]]
        m3.metric("🗂 Создано категорий", len(color_cols))
        st.write("---")
        
        c_stat1, c_stat2 = st.columns(2)
        with c_stat1:
            st.markdown("**Распределение по категориям**")
            stat_cat = st.selectbox("Выберите категорию:", color_cols)
            if stat_cat and not st.session_state['nodes'].empty:
                counts = st.session_state['nodes'][stat_cat].value_counts().reset_index()
                counts.columns = [stat_cat, 'Количество']
                fig_pie = px.pie(counts, values='Количество', names=stat_cat, hole=0.4, color_discrete_sequence=px.colors.qualitative.Pastel)
                fig_pie.update_traces(textposition='inside', textinfo='percent+label')
                fig_pie.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_pie, use_container_width=True)
                
        with c_stat2:
            st.markdown("**👑 Топ-10 Влиятельных фигур**")
            if not st.session_state['edges'].empty:
                all_edges = pd.concat([st.session_state['edges']['Source'], st.session_state['edges']['Target']])
                top_chars = all_edges.value_counts().head(10).reset_index()
                top_chars.columns = ['Персонаж', 'Количество связей']
                fig_bar = px.bar(top_chars, x='Количество связей', y='Персонаж', orientation='h', color='Количество связей', color_continuous_scale='Blues')
                fig_bar.update_layout(yaxis={'categoryorder':'total ascending'}, coloraxis_showscale=False, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_bar, use_container_width=True)
            else:
                st.info("Добавьте связи, чтобы увидеть лидеров.")

    with tab_chars:
        protected_cols = ["Имя / Название персонажа", "Заметки"]
        custom_cols = [c for c in st.session_state['nodes'].columns if c not in protected_cols]

        with st.expander("🔄 Умное переименование персонажа (С сохранением связей и карточек)"):
            all_chars = st.session_state['nodes']['Имя / Название персонажа'].dropna().unique().tolist()
            old_name = st.selectbox("Выберите персонажа:", all_chars) if all_chars else None
            new_char_name = st.text_input("Новое имя:").strip()
            if st.button("Применить новое имя") and old_name:
                if new_char_name and new_char_name != old_name and new_char_name not in all_chars:
                    st.session_state['nodes']['Имя / Название персонажа'] = st.session_state['nodes']['Имя / Название персонажа'].replace(old_name, new_char_name)
                    st.session_state['edges']['Source'] = st.session_state['edges']['Source'].replace(old_name, new_char_name)
                    st.session_state['edges']['Target'] = st.session_state['edges']['Target'].replace(old_name, new_char_name)
                    st.session_state['cards']['Linked_Character'] = st.session_state['cards']['Linked_Character'].replace(old_name, new_char_name)
                    save_sheet("Nodes", st.session_state['nodes'])
                    save_sheet("Edges", st.session_state['edges'])
                    save_sheet("Cards", st.session_state['cards'][CARD_COLS])
                    st.success("Имя обновлено в базе, на графе и в карточках!")
                    st.rerun()

        col_menu1, col_menu2 = st.columns(2)
        with col_menu1:
            with st.expander("⚙️ Управление столбцами"):
                new_col = st.text_input("Новый столбец (напр. Оружие, Раса):").strip()
                if st.button("➕ Создать столбец"):
                    if new_col and new_col not in st.session_state['nodes'].columns:
                        st.session_state['nodes'][new_col] = "Не указано"
                        save_sheet("Nodes", st.session_state['nodes'])
                        st.rerun()
                if custom_cols:
                    edit_col = st.selectbox("Столбец:", custom_cols)
                    c_ren, c_del = st.columns(2)
                    with c_ren:
                        new_name = st.text_input("Новое название:").strip()
                        if st.button("✏️ Переименовать") and new_name:
                            st.session_state['nodes'] = st.session_state['nodes'].rename(columns={edit_col: new_name})
                            save_sheet("Nodes", st.session_state['nodes'])
                            st.rerun()
                    with c_del:
                        st.write("")
                        if st.button("🗑 Удалить"):
                            st.session_state['nodes'] = st.session_state['nodes'].drop(columns=[edit_col])
                            save_sheet("Nodes", st.session_state['nodes'])
                            st.rerun()

        with col_menu2:
            with st.expander("🎨 Настройка вариантов и цветов"):
                if custom_cols:
                    color_col = st.selectbox("Категория:", custom_cols, key="color_col")
                    with st.form("add_variant_form"):
                        nv_name = st.text_input("Новый класс/вариант:").strip()
                        nv_color = st.color_picker("Цвет на графе:", "#4da6ff")
                        if st.form_submit_button("Сохранить вариант и цвет"):
                            if nv_name:
                                st.session_state['config']['colors'].setdefault(color_col, {})[nv_name] = nv_color
                                opts = st.session_state['config']['options'].setdefault(color_col, [])
                                if nv_name not in opts: opts.append(nv_name)
                                save_config_to_cloud(st.session_state['config'])
                                st.success(f"'{nv_name}' добавлен!")
                                st.rerun()

        col_config = {
            "Имя / Название персонажа": st.column_config.TextColumn("Имя (уникальное)", required=True),
            "Заметки": st.column_config.TextColumn("Способности / Лор")
        }
        for col in custom_cols:
            existing_opts = list(st.session_state['nodes'][col].dropna().unique())
            saved_opts = st.session_state['config']['options'].get(col, [])
            all_opts = list(set(existing_opts + saved_opts + ["Не указано"]))
            col_config[col] = st.column_config.SelectboxColumn(col, options=all_opts)

        edited_nodes = st.data_editor(st.session_state['nodes'], num_rows="dynamic", use_container_width=True, height=550, column_config=col_config)
        if st.button("💾 Сохранить персонажей", type="primary"):
            df_to_save = edited_nodes.dropna(subset=['Имя / Название персонажа']).fillna("Не указано")
            st.session_state['nodes'] = df_to_save
            save_sheet("Nodes", df_to_save)
            st.success("Персонажи сохранены!")
            st.rerun()

    with tab_edges:
        valid_chars = st.session_state['nodes']['Имя / Название персонажа'].dropna().unique().tolist()
        edited_edges = st.data_editor(
            st.session_state['edges'], num_rows="dynamic", use_container_width=True, height=500,
            column_config={
                "Source": st.column_config.SelectboxColumn("Кто (Source)", options=valid_chars, required=True),
                "Target": st.column_config.SelectboxColumn("С кем (Target)", options=valid_chars, required=True),
                "Type": st.column_config.SelectboxColumn("Тип связи", options=["Союз", "Вражда", "Родство", "Подчинение", "Нейтрально", "Конфликт"]),
                "Weight": st.column_config.NumberColumn("Сила связи (1-5)", min_value=1, max_value=5, step=1)
            }
        )
        if st.button("💾 Сохранить связи", type="primary"):
            df_edges_save = edited_edges.dropna(subset=['Source', 'Target'])
            st.session_state['edges'] = df_edges_save
            save_sheet("Edges", df_edges_save)
            st.success("Связи сохранены!")
            st.rerun()

    with tab_graph:
        color_options = [c for c in st.session_state['nodes'].columns if c not in ["Имя / Название персонажа", "Заметки"]]
        if color_options:
            color_by = st.sidebar.selectbox("🎨 Раскрашивать граф по:", color_options)
            show_card_avatars = st.sidebar.checkbox("🖼 Арт карточки внутри кружочка узла", value=True)
            
            active_filters = {}
            with st.sidebar.expander("🌪 Фильтры графа", expanded=False):
                for col in color_options:
                    unique_vals = st.session_state['nodes'][col].dropna().unique().tolist()
                    active_filters[col] = st.multiselect(f"{col}:", unique_vals, default=unique_vals)

            df_n = st.session_state['nodes'].copy()
            for col, selected_vals in active_filters.items():
                df_n = df_n[df_n[col].isin(selected_vals)]
                
            valid_names = df_n['Имя / Название персонажа'].tolist()
            df_e = st.session_state['edges']
            filtered_edges = df_e[(df_e['Source'].isin(valid_names)) & (df_e['Target'].isin(valid_names))]

            net = Network(height='720px', width='100%', bgcolor='#181820', font_color='white')
            net.force_atlas_2based(gravity=-35)

            unique_color_targets = df_n[color_by].dropna().unique().tolist()
            node_popup_dict = {}
            all_cards_df = st.session_state['cards']

            for _, row in df_n.iterrows():
                name = str(row['Имя / Название персонажа']).strip()
                plan = str(row.get('Категория плана', '3 план'))
                val = str(row.get(color_by, 'Не указано'))
                
                saved_color = st.session_state['config']['colors'].get(color_by, {}).get(val)
                if not saved_color:
                    color_idx = unique_color_targets.index(val) if val in unique_color_targets else 0
                    saved_color = PALETTE[color_idx % len(PALETTE)]
                    if val == "Не указано":
                        saved_color = "#ffffff"
                        
                size = 28 if '1' in plan else (18 if '2' in plan else 12)
                lore_lines = [f"{c}: {row.get(c, 'Не указано')}" for c in color_options if str(row.get(c, 'Не указано')) != 'Не указано']
                if str(row.get('Заметки', '')).strip() not in ['', 'Не указано']:
                    lore_lines.append(f"Лор: {row.get('Заметки')}")

                # Ищем привязанные к персонажу карточки
                char_cards = get_cards_for_character(name, all_cards_df)
                main_card = None
                bonus_names = []
                if not char_cards.empty:
                    pers_cards = char_cards[char_cards['Card_Type'] == 'Персонаж']
                    main_card = pers_cards.iloc[0] if not pers_cards.empty else char_cards.iloc[0]
                    bonus_cards = char_cards[char_cards['Card_Type'] == 'Бонус']
                    bonus_names = bonus_cards['Name'].tolist()

                if main_card is not None:
                    card_img_str = str(main_card.get('Image_Data', '')).strip()
                    node_popup_dict[name] = {
                        "has_card": True,
                        "card_name": str(main_card.get('Name', name)),
                        "card_type": str(main_card.get('Card_Type', 'Персонаж')),
                        "alignment": str(main_card.get('Alignment', 'Нейтралитет')),
                        "faction": str(main_card.get('Faction', '')),
                        "str": int(main_card.get('Strength', 0)),
                        "agi": int(main_card.get('Agility', 0)),
                        "mas": int(main_card.get('Mastery', 0)),
                        "wit": int(main_card.get('Wit', 0)),
                        "desc": str(main_card.get('Description', '')),
                        "image": card_img_str,
                        "bonuses": bonus_names,
                        "lore": lore_lines
                    }
                    if show_card_avatars and card_img_str:
                        net.add_node(
                            name,
                            label=name,
                            size=size + 6,
                            shape='circularImage',
                            image=card_img_str,
                            borderWidth=4,
                            color={'border': saved_color, 'background': '#1b1b26', 'highlight': {'border': '#00d4ff'}}
                        )
                    else:
                        net.add_node(name, label=name, size=size, color=saved_color)
                else:
                    node_popup_dict[name] = {
                        "has_card": False,
                        "lore": lore_lines
                    }
                    net.add_node(name, label=name, size=size, color=saved_color)

            added_nodes = net.get_nodes()
            for _, row in filtered_edges.iterrows():
                src, tgt = str(row['Source']).strip(), str(row['Target']).strip()
                rel_type = str(row.get('Type', 'Связь')).strip()
                try:
                    weight = float(row.get('Weight', 1.0))
                except ValueError:
                    weight = 1.0
                if src in added_nodes and tgt in added_nodes:
                    edge_color = '#ff4d4d' if rel_type.lower() in ['вражда', 'конфликт'] else ('#4da6ff' if rel_type.lower() in ['союз', 'родство', 'подчинение'] else '#888888')
                    net.add_edge(src, tgt, value=weight, color=edge_color, title=rel_type)

            net.save_graph('pyvis_graph.html')
            with open('pyvis_graph.html', 'r', encoding='utf-8') as f:
                raw_graph_html = f.read()
            enhanced_graph_html = inject_card_hover_into_graph(raw_graph_html, node_popup_dict)
            components.html(enhanced_graph_html, height=750)


# ==============================================================================
# МОДУЛЬ 2: ГАЛЕРЕЯ КАРТОЧЕК, СВЯЗИ НА ГРАФЕ И БАЛАНС КОЛОДЫ
# ==============================================================================
elif app_mode == "🃏 Галерея Карточек":
    st.title("🃏 Игровые Карточки БИГ СИТИ")
    df_cards = st.session_state['cards'].copy()
    for s_col in ['Strength', 'Agility', 'Mastery', 'Wit']:
        df_cards[s_col] = pd.to_numeric(df_cards[s_col], errors='coerce').fillna(0).astype(int)
    df_cards['Total_Power'] = df_cards['Strength'] + df_cards['Agility'] + df_cards['Mastery'] + df_cards['Wit']

    valid_graph_chars = st.session_state['nodes']['Имя / Название персонажа'].dropna().unique().tolist()

    tab_gallery, tab_card_stats = st.tabs(["🃏 Коллекция и Конструктор", "📊 Статистика и Баланс Карточек"])

    with tab_gallery:
        with st.expander("➕ Добавить или отредактировать карточку", expanded=df_cards.empty):
            edit_mode = st.selectbox("Выберите карточку для редактирования или создайте новую:", ["Создать новую карточку"] + df_cards['Name'].tolist())
            
            if edit_mode == "Создать новую карточку":
                c_name_val, c_type_val, c_align_val, c_fac_val, c_desc_val, c_img_val, c_link_val = "", "Персонаж", "Нейтралитет", "", "", "", "— Авто / По имени —"
                s_str, s_agi, s_mas, s_wit = 8000, 8000, 8000, 8000
            else:
                row_c = df_cards[df_cards['Name'] == edit_mode].iloc[0]
                c_name_val = str(row_c['Name'])
                c_type_val = str(row_c['Card_Type']) if row_c['Card_Type'] in ["Персонаж", "Бонус"] else "Персонаж"
                c_align_val = str(row_c['Alignment']) if row_c['Alignment'] in ["Герой", "Злодей", "Нейтралитет"] else "Нейтралитет"
                c_fac_val = str(row_c['Faction'])
                c_desc_val = str(row_c['Description'])
                c_img_val = str(row_c['Image_Data'])
                saved_link = str(row_c.get('Linked_Character', '')).strip()
                c_link_val = saved_link if saved_link in valid_graph_chars else "— Авто / По имени —"
                s_str, s_agi, s_mas, s_wit = int(row_c['Strength']), int(row_c['Agility']), int(row_c['Mastery']), int(row_c['Wit'])

            col_f1, col_f2 = st.columns(2)
            with col_f1:
                c_name = st.text_input("Имя / Название карточки (напр. ТЕР РОТ):", value=c_name_val)
                tc1, tc2 = st.columns(2)
                with tc1:
                    type_opts = ["Персонаж", "Бонус"]
                    c_type = st.selectbox("Категория карточки:", type_opts, index=type_opts.index(c_type_val))
                with tc2:
                    align_opts = ["Герой", "Злодей", "Нейтралитет"]
                    c_align = st.selectbox("Класс (снизу карточки):", align_opts, index=align_opts.index(c_align_val))
                
                link_options = ["— Авто / По имени —"] + valid_graph_chars
                c_link_idx = link_options.index(c_link_val) if c_link_val in link_options else 0
                c_linked_char = st.selectbox("🔗 Привязка к профилю на графе:", link_options, index=c_link_idx)
                c_fac = st.text_input("Фракция / Принадлежность:", value=c_fac_val)

            with col_f2:
                st.markdown("**Показатели карточки (или прибавка от бонуса):**")
                st1, st2 = st.columns(2)
                with st1:
                    val_str = st.number_input("💪 Сила (С):", value=s_str, step=10)
                    val_mas = st.number_input("🛠 Мастерство (М):", value=s_mas, step=10)
                with st2:
                    val_agi = st.number_input("⚡ Ловкость (Л):", value=s_agi, step=10)
                    val_wit = st.number_input("🧠 Смекалка (С):", value=s_wit, step=10)
                
                auto_add_to_graph = st.checkbox(
                    "🌐 Автоматически добавить персонажа в базу Графа (если его там ещё нет)",
                    value=(c_type == "Персонаж")
                )

            img_col1, img_col2 = st.columns(2)
            with img_col1:
                uploaded_img = st.file_uploader("📸 Загрузить фото карточки (с телефона или ПК):", type=["png", "jpg", "jpeg", "webp"])
            with img_col2:
                c_url = st.text_input("ИЛИ прямая ссылка на изображение:", value="" if c_img_val.startswith("data:image") else c_img_val)

            c_desc = st.text_area("Описание бонуса / Особое свойство / Лор:", value=c_desc_val, height=80)

            btn_c1, btn_c2 = st.columns([3, 1])
            with btn_c1:
                if st.button("💾 Сохранить карточку в базу", type="primary", use_container_width=True):
                    if c_name.strip():
                        final_img = c_img_val
                        if uploaded_img is not None:
                            final_img = compress_uploaded_image(uploaded_img)
                        elif c_url.strip():
                            final_img = c_url.strip()

                        resolved_link = c_name.strip() if c_linked_char == "— Авто / По имени —" else c_linked_char

                        new_card_data = {
                            "Name": c_name.strip(),
                            "Card_Type": c_type,
                            "Alignment": c_align,
                            "Faction": c_fac.strip() or "Общие",
                            "Strength": int(val_str),
                            "Agility": int(val_agi),
                            "Mastery": int(val_mas),
                            "Wit": int(val_wit),
                            "Description": c_desc.strip(),
                            "Image_Data": final_img,
                            "Linked_Character": resolved_link
                        }

                        base_df = st.session_state['cards'][CARD_COLS]
                        if edit_mode == "Создать новую карточку":
                            st.session_state['cards'] = pd.concat([base_df, pd.DataFrame([new_card_data])], ignore_index=True)
                        else:
                            idx = base_df[base_df['Name'] == edit_mode].index[0]
                            for k, v in new_card_data.items():
                                st.session_state['cards'].at[idx, k] = v

                        save_sheet("Cards", st.session_state['cards'][CARD_COLS])

                        if auto_add_to_graph and c_type == "Персонаж" and resolved_link not in valid_graph_chars:
                            new_node_row = {col: "Не указано" for col in st.session_state['nodes'].columns}
                            new_node_row['Имя / Название персонажа'] = resolved_link
                            new_node_row['Категория плана'] = '1 план'
                            if 'Группировка' in new_node_row:
                                new_node_row['Группировка'] = c_fac.strip() or "Не указано"
                            if 'Амплуа' in new_node_row:
                                new_node_row['Амплуа'] = c_align
                            if 'Заметки' in new_node_row:
                                new_node_row['Заметки'] = c_desc.strip()
                            st.session_state['nodes'] = pd.concat([st.session_state['nodes'], pd.DataFrame([new_node_row])], ignore_index=True)
                            save_sheet("Nodes", st.session_state['nodes'])

                        st.success(f"Карточка «{c_name.strip()}» успешно сохранена и синхронизирована с графом!")
                        st.rerun()
                    else:
                        st.warning("Укажите название карточки!")
            with btn_c2:
                if edit_mode != "Создать новую карточку":
                    if st.button("🗑 Удалить карточку", use_container_width=True):
                        st.session_state['cards'] = st.session_state['cards'][st.session_state['cards']['Name'] != edit_mode].reset_index(drop=True)
                        save_sheet("Cards", st.session_state['cards'][CARD_COLS])
                        st.rerun()

        st.write("---")

        if not df_cards.empty:
            f1, f2, f3, f4 = st.columns(4)
            with f1:
                filter_type = st.selectbox("Тип карточки:", ["Все", "Персонаж", "Бонус"])
            with f2:
                filter_align = st.selectbox("Класс:", ["Все", "Герой", "Злодей", "Нейтралитет"])
            with f3:
                factions = ["Все"] + sorted([f for f in df_cards['Faction'].unique().tolist() if f])
                filter_fac = st.selectbox("Фракция:", factions)
            with f4:
                sort_by = st.selectbox("Сортировать по:", [
                    "По порядку добавления",
                    "Общая мощь (по убыванию)",
                    "Сила (по убыванию)",
                    "Ловкость (по убыванию)",
                    "Мастерство (по убыванию)",
                    "Смекалка (по убыванию)",
                    "По алфавиту (А-Я)"
                ])

            search_q = st.text_input("🔍 Быстрый поиск по имени карточки, персонажу или тексту эффекта:")

            view_cards = df_cards.copy()
            if filter_type != "Все":
                view_cards = view_cards[view_cards['Card_Type'] == filter_type]
            if filter_align != "Все":
                view_cards = view_cards[view_cards['Alignment'] == filter_align]
            if filter_fac != "Все":
                view_cards = view_cards[view_cards['Faction'] == filter_fac]
            if search_q.strip():
                q = search_q.strip().lower()
                view_cards = view_cards[
                    view_cards['Name'].str.lower().str.contains(q) |
                    view_cards['Description'].str.lower().str.contains(q) |
                    view_cards['Linked_Character'].astype(str).str.lower().str.contains(q)
                ]

            sort_map = {
                "Общая мощь (по убыванию)": ("Total_Power", False),
                "Сила (по убыванию)": ("Strength", False),
                "Ловкость (по убыванию)": ("Agility", False),
                "Мастерство (по убыванию)": ("Mastery", False),
                "Смекалка (по убыванию)": ("Wit", False),
                "По алфавиту (А-Я)": ("Name", True)
            }
            if sort_by in sort_map:
                col_s, asc = sort_map[sort_by]
                view_cards = view_cards.sort_values(by=col_s, ascending=asc)

            st.caption(f"Найдено карточек: **{len(view_cards)}**")
            cols = st.columns(3)
            for i, (_, card) in enumerate(view_cards.iterrows()):
                with cols[i % 3]:
                    align_str = str(card['Alignment'])
                    align_class = "align-hero" if align_str == "Герой" else ("align-villain" if align_str == "Злодей" else "align-neutral")
                    
                    st.markdown(f"""
                    <div class="game-card">
                        <div class="game-card-header">
                            <span style="color:#ffcc00; font-size:12px;">{html.escape(str(card['Faction']))}</span>
                            <span class="game-card-type">{html.escape(str(card['Card_Type']))}</span>
                        </div>
                        <div class="game-card-title">{html.escape(str(card['Name']))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    if card['Image_Data']:
                        st.image(card['Image_Data'], use_container_width=True)
                        
                    st.markdown(f"""
                    <div class="stats-grid">
                        <div class="stat-item"><span class="stat-letter">С</span>{int(card['Strength'])}</div>
                        <div class="stat-item"><span class="stat-letter">Л</span>{int(card['Agility'])}</div>
                        <div class="stat-item"><span class="stat-letter">М</span>{int(card['Mastery'])}</div>
                        <div class="stat-item"><span class="stat-letter">С</span>{int(card['Wit'])}</div>
                    </div>
                    <div class="alignment-badge {align_class}">{html.escape(align_str)}</div>
                    """, unsafe_allow_html=True)

                    if card['Description']:
                        st.caption(card['Description'])

                    linked_hero = resolve_linked_character(card, valid_graph_chars)
                    if linked_hero:
                        rels = get_character_relations(linked_hero, st.session_state['edges'])
                        with st.expander(f"🔗 Связи на графе: {linked_hero} ({len(rels)})"):
                            hero_info = st.session_state['nodes'][st.session_state['nodes']['Имя / Название персонажа'] == linked_hero].iloc[0]
                            meta_parts = [f"**{c}**: {hero_info[c]}" for c in st.session_state['nodes'].columns if c not in ['Имя / Название персонажа', 'Заметки'] and str(hero_info[c]) != 'Не указано']
                            if meta_parts:
                                st.markdown(" • ".join(meta_parts))
                            if str(hero_info.get('Заметки', '')).strip() not in ['', 'Не указано']:
                                st.caption(f"📝 {hero_info['Заметки']}")

                            if rels:
                                for r in rels:
                                    t_low = r['type'].lower()
                                    css_c = "rel-enemy" if t_low in ['вражда', 'конфликт'] else ("rel-ally" if t_low in ['союз', 'родство', 'подчинение'] else "rel-neutral")
                                    icon = "⚔️" if css_c == "rel-enemy" else ("🤝" if css_c == "rel-ally" else "⚖️")
                                    st.markdown(f"""
                                    <div class="rel-pill {css_c}">
                                        <span>{icon} <b>{html.escape(r['partner'])}</b> — {html.escape(r['type'])}</span>
                                        <span>{'⭐' * r['weight']}</span>
                                    </div>
                                    """, unsafe_allow_html=True)
                            else:
                                st.caption("Связей на графе пока нет.")

                            st.markdown("---")
                            st.caption("➕ **Быстро добавить связь:**")
                            other_chars = [c for c in valid_graph_chars if c != linked_hero]
                            if other_chars:
                                qc1, qc2 = st.columns(2)
                                with qc1:
                                    q_target = st.selectbox("С кем:", other_chars, key=f"qt_{i}_{card['Name']}")
                                with qc2:
                                    q_type = st.selectbox("Тип:", ["Союз", "Вражда", "Родство", "Подчинение", "Конфликт", "Нейтрально"], key=f"qtp_{i}_{card['Name']}")
                                q_weight = st.slider("Сила связи:", 1, 5, 3, key=f"qw_{i}_{card['Name']}")
                                if st.button("Добавить связь на граф", key=f"qbtn_{i}_{card['Name']}", use_container_width=True):
                                    new_edge = pd.DataFrame([{"Source": linked_hero, "Target": q_target, "Type": q_type, "Weight": q_weight}])
                                    st.session_state['edges'] = pd.concat([st.session_state['edges'], new_edge], ignore_index=True)
                                    save_sheet("Edges", st.session_state['edges'])
                                    st.success("Связь добавлена!")
                                    st.rerun()
                    else:
                        st.caption("⚪ *Персонаж еще не привязан к графу*")

                    st.write("---")
        else:
            st.info("В базе пока нет карточек. Добавьте первую карточку через панель выше!")

    with tab_card_stats:
        if df_cards.empty:
            st.info("Добавьте карточки, чтобы увидеть статистику и баланс.")
        else:
            st.subheader("Баланс классов и статистика колоды")
            k1, k2, k3, k4 = st.columns(4)
            k1.metric("🃏 Всего карточек", len(df_cards))
            k2.metric("👤 Персонажей", len(df_cards[df_cards['Card_Type'] == 'Персонаж']))
            k3.metric("🎁 Карточек бонусов", len(df_cards[df_cards['Card_Type'] == 'Бонус']))
            char_only = df_cards[df_cards['Card_Type'] == 'Персонаж']
            avg_power = int(char_only['Total_Power'].mean()) if not char_only.empty else 0
            k4.metric("⚡ Средняя сумма статов", avg_power)

            st.write("---")
            ch1, ch2 = st.columns(2)
            with ch1:
                st.markdown("**Соотношение классов (Герой / Злодей / Нейтралитет)**")
                al_counts = df_cards['Alignment'].value_counts().reset_index()
                al_counts.columns = ['Класс', 'Количество']
                color_map_align = {"Герой": "#4da6ff", "Злодей": "#ff4d4d", "Нейтралитет": "#ffcc00"}
                fig_al = px.pie(al_counts, values='Количество', names='Класс', hole=0.45, color='Класс', color_discrete_map=color_map_align)
                fig_al.update_traces(textposition='inside', textinfo='percent+label')
                fig_al.update_layout(showlegend=False, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', font_color='white')
                st.plotly_chart(fig_al, use_container_width=True)

            with ch2:
                st.markdown("**Баланс средних показателей по классам (Персонажи)**")
                if not char_only.empty:
                    avg_stats = char_only.groupby('Alignment')[['Strength', 'Agility', 'Mastery', 'Wit']].mean().reset_index()
                    avg_melted = avg_stats.melt(id_vars='Alignment', var_name='Показатель', value_name='Среднее значение')
                    stat_ru = {'Strength': 'Сила (С)', 'Agility': 'Ловкость (Л)', 'Mastery': 'Мастерство (М)', 'Wit': 'Смекалка (С)'}
                    avg_melted['Показатель'] = avg_melted['Показатель'].map(stat_ru)
                    fig_avg = px.bar(avg_melted, x='Показатель', y='Среднее значение', color='Alignment', barmode='group', color_discrete_map=color_map_align)
                    fig_avg.update_layout(margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
                    st.plotly_chart(fig_avg, use_container_width=True)
                else:
                    st.info("Нет карточек категории «Персонаж» для расчета средних характеристик.")

            st.write("---")
            st.markdown("**🏆 Топ-10 карточек по характеристикам**")
            rank_metric = st.selectbox("Выберите показатель для рейтинга:", [
                "Суммарная мощь (С+Л+М+С)", "Сила (С)", "Ловкость (Л)", "Мастерство (М)", "Смекалка (С)"
            ])
            metric_col_map = {
                "Суммарная мощь (С+Л+М+С)": "Total_Power",
                "Сила (С)": "Strength",
                "Ловкость (Л)": "Agility",
                "Мастерство (М)": "Mastery",
                "Смекалка (С)": "Wit"
            }
            target_m = metric_col_map[rank_metric]
            top_c = df_cards.sort_values(by=target_m, ascending=False).head(10)
            fig_top = px.bar(top_c, x=target_m, y='Name', color='Alignment', orientation='h', color_discrete_map=color_map_align, text=target_m)
            fig_top.update_layout(yaxis={'categoryorder':'total ascending'}, margin=dict(t=10, b=10, l=10, r=10), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', font_color='white')
            st.plotly_chart(fig_top, use_container_width=True)


# ==============================================================================
# МОДУЛЬ 3: АРХИВЫ И ЛОР (С ЗАГРУЗКОЙ ФАЙЛОВ С ПК)
# ==============================================================================
elif app_mode == "📚 Архивы и Лор":
    st.title("📚 Архивы БИГ СИТИ")
    df_arch = st.session_state['archives']

    col_left, col_right = st.columns([1, 2.5])

    with col_left:
        st.subheader("🗂 Оглавление")
        if st.button("➕ Создать / Загрузить документ", use_container_width=True, type="primary"):
            st.session_state['selected_doc'] = "__NEW__"

        categories = ["Все"] + sorted([c for c in df_arch['Category'].unique().tolist() if c])
        filter_cat = st.selectbox("Фильтр по разделу:", categories)

        filtered_arch = df_arch if filter_cat == "Все" else df_arch[df_arch['Category'] == filter_cat]
        doc_titles = filtered_arch['Title'].tolist()

        if doc_titles:
            chosen_doc = st.radio("Выберите запись:", doc_titles)
            if st.session_state.get('selected_doc') != "__NEW__":
                st.session_state['selected_doc'] = chosen_doc
        else:
            st.info("В этом разделе пока нет записей.")

    with col_right:
        if st.session_state.get('selected_doc') == "__NEW__" or df_arch.empty:
            st.subheader("✍️ Новый архивный документ")
            
            uploaded_doc = st.file_uploader("📂 Загрузить готовый файл с компьютера (.docx, .txt, .md):", type=["docx", "txt", "md"], key="arch_upload")
            init_title, init_content = "", ""
            if uploaded_doc is not None:
                init_title, init_content = read_uploaded_document(uploaded_doc)
                st.success(f"Файл «{uploaded_doc.name}» успешно прочитан! Проверьте текст ниже и нажмите «Сохранить в Архив».")

            new_title = st.text_input("Название документа:", value=init_title)
            new_cat = st.text_input("Раздел / Том (например: Лор, Правила, Локации):", value="Общий Лор")
            new_content = st.text_area("Текст документа:", value=init_content, height=400)
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("💾 Сохранить в Архив", type="primary", use_container_width=True):
                    if new_title.strip():
                        new_row = pd.DataFrame([{"Title": new_title.strip(), "Category": new_cat.strip(), "Content": new_content}])
                        st.session_state['archives'] = pd.concat([df_arch, new_row], ignore_index=True)
                        save_sheet("Archives", st.session_state['archives'])
                        st.session_state['selected_doc'] = new_title.strip()
                        st.success("Документ сохранен!")
                        st.rerun()
                    else:
                        st.warning("Введите название документа!")
            with c2:
                if st.button("Отмена", use_container_width=True):
                    st.session_state['selected_doc'] = doc_titles[0] if doc_titles else None
                    st.rerun()

        elif st.session_state.get('selected_doc') in df_arch['Title'].values:
            curr_title = st.session_state['selected_doc']
            doc_row = df_arch[df_arch['Title'] == curr_title].iloc[0]

            mode_read, mode_edit = st.tabs(["📖 Чтение", "✏️ Редактировать / Заменить файлом"])
            with mode_read:
                st.caption(f"Раздел: **{doc_row['Category']}**")
                st.markdown(f"## {doc_row['Title']}")
                st.write("---")
                st.markdown(doc_row['Content'])

            with mode_edit:
                replace_doc = st.file_uploader("📂 Заменить текст из файла (.docx, .txt, .md):", type=["docx", "txt", "md"], key="arch_replace")
                curr_content_val = doc_row['Content']
                if replace_doc is not None:
                    _, curr_content_val = read_uploaded_document(replace_doc)
                    st.info("Текст из файла подгружен в поле ниже. Нажмите «Обновить документ», чтобы сохранить.")

                ed_title = st.text_input("Название:", value=doc_row['Title'])
                ed_cat = st.text_input("Раздел:", value=doc_row['Category'])
                ed_content = st.text_area("Содержание:", value=curr_content_val, height=420)
                
                b1, b2 = st.columns([3, 1])
                with b1:
                    if st.button("💾 Обновить документ", type="primary", use_container_width=True):
                        idx = df_arch[df_arch['Title'] == curr_title].index[0]
                        st.session_state['archives'].at[idx, 'Title'] = ed_title.strip()
                        st.session_state['archives'].at[idx, 'Category'] = ed_cat.strip()
                        st.session_state['archives'].at[idx, 'Content'] = ed_content
                        save_sheet("Archives", st.session_state['archives'])
                        st.session_state['selected_doc'] = ed_title.strip()
                        st.success("Обновлено!")
                        st.rerun()
                with b2:
                    if st.button("🗑 Удалить", use_container_width=True):
                        st.session_state['archives'] = df_arch[df_arch['Title'] != curr_title].reset_index(drop=True)
                        save_sheet("Archives", st.session_state['archives'])
                        st.session_state['selected_doc'] = None
                        st.rerun()


# ==============================================================================
# МОДУЛЬ 4: СЦЕНАРИИ И СЮЖЕТ (С ЗАГРУЗКОЙ ФАЙЛОВ И СКРЫТЫМИ ЗАГОЛОВКАМИ)
# ==============================================================================
elif app_mode == "🎬 Сценарии и Сюжет":
    st.title("🎬 Сценарии и Сюжетные Линии")
    df_scr = st.session_state['scripts']

    col_s_left, col_s_right = st.columns([1, 2.5])

    with col_s_left:
        st.subheader("📑 Сюжетные ветки")
        if st.button("➕ Новый / Загрузить сценарий", use_container_width=True, type="primary"):
            st.session_state['selected_script'] = "__NEW_SCRIPT__"

        scr_titles = df_scr['Title'].tolist()
        if scr_titles:
            chosen_scr = st.radio("Выберите сценарий:", scr_titles)
            if st.session_state.get('selected_script') != "__NEW_SCRIPT__":
                st.session_state['selected_script'] = chosen_scr
        else:
            st.info("Сценариев пока нет.")

        with st.expander("💡 Как работают скрытые заголовки?"):
            st.markdown("""
            * `# Заголовок` — **главный скрытый блок** (1 уровень).
            * `## Подзаголовок` — **вложенный подзаголовок** (2 уровень).
            * `### Деталь` — **глубокий спойлер** (3 уровень).
            * При загрузке файла `.docx` стандартные стили Word (*Заголовок 1, 2, 3*) превращаются в `#`, `##`, `###` автоматически!
            """)

    with col_s_right:
        default_template = (
            "Вступление к сценарию (видно сразу).\n\n"
            "# Акт 1. Тень над Городом\n"
            "Общее описание первого акта.\n\n"
            "## Сцена 1. Встреча в порту\n"
            "Диалог героев у старого склада.\n\n"
            "### Секретная улика (Спойлер)\n"
            "Если игроки обыщут ящик, они найдут медальон."
        )

        if st.session_state.get('selected_script') == "__NEW_SCRIPT__" or df_scr.empty:
            st.subheader("✍️ Создание или загрузка сценария")
            
            up_scr = st.file_uploader("📂 Загрузить готовый сценарий с компьютера (.docx, .txt, .md):", type=["docx", "txt", "md"], key="scr_upload")
            s_init_title, s_init_content = "", default_template
            if up_scr is not None:
                s_init_title, s_init_content = read_uploaded_document(up_scr)
                st.success(f"Сценарий «{up_scr.name}» загружен! Проверьте разметку и нажмите «Сохранить сценарий».")

            s_title = st.text_input("Название сценария / Главы:", value=s_init_title)
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                s_act = st.text_input("Акт / Сюжетная арка:", value="Основной сюжет")
            with c_a2:
                s_status = st.selectbox("Статус готовности:", ["💡 Идея", "✍️ В работе", "✅ Готово"])
            
            s_content = st.text_area("Текст сценария (используйте #, ##, ### для скрытых блоков):", value=s_init_content, height=400)

            if st.button("💾 Сохранить сценарий", type="primary", use_container_width=True):
                if s_title.strip():
                    new_s = pd.DataFrame([{"Title": s_title.strip(), "Act": s_act.strip(), "Status": s_status, "Content": s_content}])
                    st.session_state['scripts'] = pd.concat([df_scr, new_s], ignore_index=True)
                    save_sheet("Scripts", st.session_state['scripts'])
                    st.session_state['selected_script'] = s_title.strip()
                    st.success("Сценарий сохранен!")
                    st.rerun()
                else:
                    st.warning("Введите название сценария!")

        elif st.session_state.get('selected_script') in df_scr['Title'].values:
            curr_s_title = st.session_state['selected_script']
            s_row = df_scr[df_scr['Title'] == curr_s_title].iloc[0]

            tab_s_read, tab_s_edit = st.tabs(["🎭 Интерактивное чтение (Со спойлерами)", "✏️ Редактировать / Загрузить из файла"])

            with tab_s_read:
                st.caption(f"Арка: **{s_row['Act']}** | Статус: **{s_row['Status']}**")
                st.markdown(f"## {s_row['Title']}")
                st.caption("👆 Нажимайте на цветные плашки ниже, чтобы раскрывать акты, сцены и секреты:")
                rendered_html = render_script_with_spoilers(str(s_row['Content']))
                st.markdown(rendered_html, unsafe_allow_html=True)

            with tab_s_edit:
                rep_scr = st.file_uploader("📂 Обновить текст сценария из файла (.docx, .txt, .md):", type=["docx", "txt", "md"], key="scr_replace")
                s_curr_text = s_row['Content']
                if rep_scr is not None:
                    _, s_curr_text = read_uploaded_document(rep_scr)
                    st.info("Текст из файла подгружен. Нажмите «Сохранить изменения» внизу.")

                ed_s_title = st.text_input("Название:", value=s_row['Title'])
                ec1, ec2 = st.columns(2)
                with ec1:
                    ed_s_act = st.text_input("Арка / Акт:", value=s_row['Act'])
                with ec2:
                    statuses = ["💡 Идея", "✍️ В работе", "✅ Готово"]
                    curr_st_idx = statuses.index(s_row['Status']) if s_row['Status'] in statuses else 0
                    ed_s_status = st.selectbox("Статус:", statuses, index=curr_st_idx)

                ed_s_content = st.text_area("Текст сценария (# - Заголовок, ## - Подзаголовок, ### - Секрет):", value=s_curr_text, height=420)

                sb1, sb2 = st.columns([3, 1])
                with sb1:
                    if st.button("💾 Сохранить изменения", type="primary", use_container_width=True):
                        idx = df_scr[df_scr['Title'] == curr_s_title].index[0]
                        st.session_state['scripts'].at[idx, 'Title'] = ed_s_title.strip()
                        st.session_state['scripts'].at[idx, 'Act'] = ed_s_act.strip()
                        st.session_state['scripts'].at[idx, 'Status'] = ed_s_status
                        st.session_state['scripts'].at[idx, 'Content'] = ed_s_content
                        save_sheet("Scripts", st.session_state['scripts'])
                        st.session_state['selected_script'] = ed_s_title.strip()
                        st.success("Сценарий обновлен!")
                        st.rerun()
                with sb2:
                    if st.button("🗑 Удалить сценарий", use_container_width=True):
                        st.session_state['scripts'] = df_scr[df_scr['Title'] != curr_s_title].reset_index(drop=True)
                        save_sheet("Scripts", st.session_state['scripts'])
                        st.session_state['selected_script'] = None
                        st.rerun()
