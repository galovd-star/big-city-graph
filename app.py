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

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(layout="wide", page_title="БИГ СИТИ: Экосистема Вселенной", initial_sidebar_state="expanded")

# 🔗 ВСТАВЬТЕ СЮДА ССЫЛКУ НА ВАШУ GOOGLE ТАБЛИЦУ (внутри кавычек)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MyQ3vqstgSAarY9NtsAl1f1tnlbgmi-2iljHMf97zBM/edit?gid=0#gid=0"

if SHEET_URL == "ВСТАВЬТЕ_ССЫЛКУ_СЮДА":
    st.error("⚠️ Откройте код app.py на GitHub и вставьте настоящую ссылку на вашу Google Таблицу в переменную SHEET_URL (строка 18).")
    st.stop()

# --- КАСТОМНЫЙ ДИЗАЙН И СТИЛИ ДЛЯ СКРЫТЫХ ЗАГОЛОВКОВ ---
st.markdown("""
<style>
    [data-testid="stAppViewContainer"] { background-color: #121212; }
    [data-testid="stSidebar"] { background-color: #1a1a24 !important; border-right: 1px solid #333344; }
    [data-testid="stHeader"] { background-color: rgba(0,0,0,0) !important; }
    h1, h2, h3 { color: #00d4ff !important; font-family: 'Courier New', Courier, monospace; }
    .stMarkdown p, .stText { color: #dcdcdc !important; font-size: 16px; }
    
    /* Стили для карточек галереи */
    .game-card {
        background-color: #1e1e2a;
        border: 1px solid #33334d;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        box-shadow: 0 4px 10px rgba(0,0,0,0.4);
    }
    .game-card-title { color: #00d4ff; font-size: 20px; font-weight: bold; margin-bottom: 5px; }
    .game-card-faction { color: #ffcc00; font-size: 13px; text-transform: uppercase; margin-bottom: 8px; }
    .game-card-stats { background-color: #2b2b3d; padding: 6px 10px; border-radius: 6px; font-size: 13px; color: #ffffff; margin-bottom: 10px; font-family: monospace; }
    
    /* Стили для скрытых заголовков и подзаголовков в Сценариях */
    details.lvl1 {
        background-color: #1b1b26;
        border-left: 4px solid #00d4ff;
        border-radius: 6px;
        padding: 10px 15px;
        margin: 12px 0;
    }
    details.lvl1 > summary {
        font-size: 20px;
        font-weight: bold;
        color: #00d4ff;
        cursor: pointer;
        outline: none;
    }
    details.lvl2 {
        background-color: #232332;
        border-left: 3px solid #ffcc00;
        border-radius: 6px;
        padding: 8px 14px;
        margin: 10px 0 10px 15px;
    }
    details.lvl2 > summary {
        font-size: 17px;
        font-weight: bold;
        color: #ffcc00;
        cursor: pointer;
        outline: none;
    }
    details.lvl3 {
        background-color: #2b2b3c;
        border-left: 3px solid #ff66b2;
        border-radius: 6px;
        padding: 6px 12px;
        margin: 8px 0 8px 25px;
    }
    details.lvl3 > summary {
        font-size: 15px;
        font-weight: bold;
        color: #ff66b2;
        cursor: pointer;
        outline: none;
    }
    .script-body {
        padding-top: 8px;
        color: #e0e0e0;
        line-height: 1.6;
        white-space: pre-wrap;
    }
</style>
""", unsafe_allow_html=True)

PALETTE = ["#ff4d4d", "#4da6ff", "#9933ff", "#33cc33", "#ffcc00", "#ff66b2", "#339999", "#ff9933", "#996633", "#6699ff"]

# --- ПОДКЛЮЧЕНИЕ К GOOGLE SHEETS ---
conn = st.connection("gsheets", type=GSheetsConnection)

def safe_read_sheet(worksheet_name, default_cols):
    try:
        df = conn.read(spreadsheet=SHEET_URL, worksheet=worksheet_name)
        df = df.dropna(how='all')
        if df.empty or len(df.columns) == 0:
            return pd.DataFrame(columns=default_cols)
        for col in default_cols:
            if col not in df.columns:
                df[col] = "Не указано" if col not in ["Content", "Image_Data", "Заметки"] else ""
        return df.fillna("")
    except Exception:
        return pd.DataFrame(columns=default_cols)

@st.cache_data(ttl=5)
def load_all_data():
    nodes = safe_read_sheet("Nodes", ['Имя / Название персонажа', 'Категория плана', 'Пол', 'Группировка', 'Заметки'])
    nodes = nodes.replace("", "Не указано")
    edges = safe_read_sheet("Edges", ['Source', 'Target', 'Weight', 'Type'])
    archives = safe_read_sheet("Archives", ['Title', 'Category', 'Content'])
    cards = safe_read_sheet("Cards", ['Name', 'Faction', 'Stats', 'Description', 'Image_Data'])
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
        st.error(f"⚠️ Ошибка сохранения в лист '{worksheet_name}'. Убедитесь, что вы создали лист с таким названием внизу Google Таблицы! Детали: {e}")

def save_config_to_cloud(config_dict):
    df = pd.DataFrame({"Settings": [json.dumps(config_dict, ensure_ascii=False)]})
    save_sheet("Config", df)

# --- ФУНКЦИЯ СЖАТИЯ ФОТО КАРТОЧЕК (ДЛЯ ХРАНЕНИЯ В ОБЛАКЕ) ---
def compress_uploaded_image(uploaded_file):
    img = Image.open(uploaded_file)
    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")
    img.thumbnail((420, 580)) # Оптимальный размер карточки
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=72, optimize=True)
    b64_str = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return f"data:image/jpeg;base64,{b64_str}"

# --- ФУНКЦИЯ ПАРСИНГА СКРЫТЫХ ЗАГОЛОВКОВ И ПОДЗАГОЛОВКОВ ---
def render_script_with_spoilers(raw_text):
    lines = raw_text.split('\n')
    html_out = []
    open_levels = [] # стек открытых уровней [1, 2, 3]

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
            safe_line = html.escape(line)
            html_out.append(safe_line + "<br>")

    close_until(1)
    return "".join(html_out)

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
        "📚 Архивы и Лор",
        "🃏 Галерея Карточек",
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
# МОДУЛЬ 1: ПЕРСОНАЖИ, ГРАФ И СТАТИСТИКА
# ==============================================================================
if app_mode == "🌐 Персонажи и Граф":
    st.title("🌐 База Персонажей и Карта Связей")
    tab_graph, tab_chars, tab_edges, tab_stats = st.tabs([
        "🕸 Интерактивный Граф", "👤 Персонажи", "🔗 Связи", "📊 Статистика"
    ])

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

        with st.expander("🔄 Умное переименование персонажа (С сохранением связей)"):
            all_chars = st.session_state['nodes']['Имя / Название персонажа'].dropna().unique().tolist()
            old_name = st.selectbox("Выберите персонажа:", all_chars) if all_chars else None
            new_char_name = st.text_input("Новое имя:").strip()
            if st.button("Применить новое имя") and old_name:
                if new_char_name and new_char_name != old_name and new_char_name not in all_chars:
                    st.session_state['nodes']['Имя / Название персонажа'] = st.session_state['nodes']['Имя / Название персонажа'].replace(old_name, new_char_name)
                    st.session_state['edges']['Source'] = st.session_state['edges']['Source'].replace(old_name, new_char_name)
                    st.session_state['edges']['Target'] = st.session_state['edges']['Target'].replace(old_name, new_char_name)
                    save_sheet("Nodes", st.session_state['nodes'])
                    save_sheet("Edges", st.session_state['edges'])
                    st.success("Имя обновлено везде!")
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

            net = Network(height='700px', width='100%', bgcolor='#181820', font_color='white')
            net.force_atlas_2based(gravity=-35)

            unique_color_targets = df_n[color_by].dropna().unique().tolist()
            for _, row in df_n.iterrows():
                name = str(row['Имя / Название персонажа']).strip()
                plan = str(row.get('Категория плана', '3 план'))
                val = str(row.get(color_by, 'Не указано'))
                saved_color = st.session_state['config']['colors'].get(color_by, {}).get(val)
                if not saved_color:
                    color_idx = unique_color_targets.index(val) if val in unique_color_targets else 0
                    saved_color = PALETTE[color_idx % len(PALETTE)]
                    if val == "Не указано": saved_color = "#ffffff"
                size = 25 if '1' in plan else (15 if '2' in plan else 10)
                hover_text = f"👤 {name}\n" + "\n".join([f"▪ {c}: {row.get(c, 'Не указано')}" for c in color_options])
                net.add_node(name, label=name, size=size, color=saved_color, title=hover_text)

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
                components.html(f.read(), height=730)


# ==============================================================================
# МОДУЛЬ 2: АРХИВЫ И ЛОР (БИБЛИОТЕКА ДОКУМЕНТОВ)
# ==============================================================================
elif app_mode == "📚 Архивы и Лор":
    st.title("📚 Архивы БИГ СИТИ")
    df_arch = st.session_state['archives']

    col_left, col_right = st.columns([1, 2.5])

    with col_left:
        st.subheader("🗂 Оглавление")
        if st.button("➕ Создать новый документ", use_container_width=True, type="primary"):
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
            new_title = st.text_input("Название документа (например: История Синдиката):")
            new_cat = st.text_input("Раздел / Том (например: Лор, Правила, Локации):", value="Общий Лор")
            new_content = st.text_area("Текст документа (поддерживается Markdown):", height=400)
            
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

            mode_read, mode_edit = st.tabs(["📖 Чтение", "✏️ Редактировать"])
            with mode_read:
                st.caption(f"Раздел: **{doc_row['Category']}**")
                st.markdown(f"## {doc_row['Title']}")
                st.write("---")
                st.markdown(doc_row['Content'])

            with mode_edit:
                ed_title = st.text_input("Название:", value=doc_row['Title'])
                ed_cat = st.text_input("Раздел:", value=doc_row['Category'])
                ed_content = st.text_area("Содержание:", value=doc_row['Content'], height=420)
                
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
# МОДУЛЬ 3: ГАЛЕРЕЯ КАРТОЧЕК (ЗАГРУЗКА ФОТО И СЕТКА)
# ==============================================================================
elif app_mode == "🃏 Галерея Карточек":
    st.title("🃏 Галерея Игровых Карточек")
    df_cards = st.session_state['cards']

    with st.expander("➕ Добавить или отредактировать карточку", expanded=df_cards.empty):
        edit_mode = st.selectbox("Режим:", ["Создать новую карточку"] + df_cards['Name'].tolist())
        
        if edit_mode == "Создать новую карточку":
            c_name_val, c_fac_val, c_stat_val, c_desc_val, c_img_val = "", "", "", "", ""
        else:
            row_c = df_cards[df_cards['Name'] == edit_mode].iloc[0]
            c_name_val = row_c['Name']
            c_fac_val = row_c['Faction']
            c_stat_val = row_c['Stats']
            c_desc_val = row_c['Description']
            c_img_val = row_c['Image_Data']

        col_f1, col_f2 = st.columns(2)
        with col_f1:
            c_name = st.text_input("Название карточки / Персонаж:", value=c_name_val)
            c_fac = st.text_input("Фракция / Колода (напр. Синдикат, Атака, Уловка):", value=c_fac_val)
            c_stat = st.text_input("Характеристики (напр. Урон: 4 | Защита: 2):", value=c_stat_val)
        with col_f2:
            uploaded_img = st.file_uploader("📸 Загрузить фото карточки (с телефона или ПК):", type=["png", "jpg", "jpeg", "webp"])
            c_url = st.text_input("ИЛИ вставить прямую ссылку на картинку:", value="" if c_img_val.startswith("data:image") else c_img_val)

        c_desc = st.text_area("Описание эффекта / Лор карточки:", value=c_desc_val, height=100)

        btn_c1, btn_c2 = st.columns([3, 1])
        with btn_c1:
            if st.button("💾 Сохранить карточку в облако", type="primary", use_container_width=True):
                if c_name.strip():
                    final_img = c_img_val
                    if uploaded_img is not None:
                        final_img = compress_uploaded_image(uploaded_img)
                    elif c_url.strip():
                        final_img = c_url.strip()

                    new_card_data = {
                        "Name": c_name.strip(),
                        "Faction": c_fac.strip() or "Общие",
                        "Stats": c_stat.strip(),
                        "Description": c_desc.strip(),
                        "Image_Data": final_img
                    }

                    if edit_mode == "Создать новую карточку":
                        st.session_state['cards'] = pd.concat([df_cards, pd.DataFrame([new_card_data])], ignore_index=True)
                    else:
                        idx = df_cards[df_cards['Name'] == edit_mode].index[0]
                        for k, v in new_card_data.items():
                            st.session_state['cards'].at[idx, k] = v

                    save_sheet("Cards", st.session_state['cards'])
                    st.success("Карточка успешно сохранена!")
                    st.rerun()
                else:
                    st.warning("Укажите название карточки!")
        with btn_c2:
            if edit_mode != "Создать новую карточку":
                if st.button("🗑 Удалить карточку", use_container_width=True):
                    st.session_state['cards'] = df_cards[df_cards['Name'] != edit_mode].reset_index(drop=True)
                    save_sheet("Cards", st.session_state['cards'])
                    st.rerun()

    st.write("---")

    if not df_cards.empty:
        f_col1, f_col2 = st.columns([1, 2])
        with f_col1:
            factions = ["Все"] + sorted([f for f in df_cards['Faction'].unique().tolist() if f])
            sel_fac = st.selectbox("Фильтр по фракции/колоде:", factions)
        with f_col2:
            search_q = st.text_input("🔍 Поиск карточки по названию или эффекту:")

        view_cards = df_cards.copy()
        if sel_fac != "Все":
            view_cards = view_cards[view_cards['Faction'] == sel_fac]
        if search_q.strip():
            q = search_q.strip().lower()
            view_cards = view_cards[view_cards['Name'].str.lower().str.contains(q) | view_cards['Description'].str.lower().str.contains(q)]

        cols = st.columns(3)
        for i, (_, card) in enumerate(view_cards.iterrows()):
            with cols[i % 3]:
                st.markdown(f"""
                <div class="game-card">
                    <div class="game-card-faction">{html.escape(str(card['Faction']))}</div>
                    <div class="game-card-title">{html.escape(str(card['Name']))}</div>
                </div>
                """, unsafe_allow_html=True)
                if card['Image_Data']:
                    st.image(card['Image_Data'], use_container_width=True)
                if card['Stats']:
                    st.markdown(f"<div class='game-card-stats'>⚡ {html.escape(str(card['Stats']))}</div>", unsafe_allow_html=True)
                if card['Description']:
                    st.write(card['Description'])
                st.write("---")
    else:
        st.info("Галерея пока пуста. Откройте вкладку выше и загрузите свою первую карточку!")


# ==============================================================================
# МОДУЛЬ 4: СЦЕНАРИИ И СЮЖЕТ (СКРЫТЫЕ ЗАГОЛОВКИ И ПОДЗАГОЛОВКИ)
# ==============================================================================
elif app_mode == "🎬 Сценарии и Сюжет":
    st.title("🎬 Сценарии и Сюжетные Линии")
    df_scr = st.session_state['scripts']

    col_s_left, col_s_right = st.columns([1, 2.5])

    with col_s_left:
        st.subheader("📑 Сюжетные ветки")
        if st.button("➕ Новый сценарий / Акт", use_container_width=True, type="primary"):
            st.session_state['selected_script'] = "__NEW_SCRIPT__"

        scr_titles = df_scr['Title'].tolist()
        if scr_titles:
            chosen_scr = st.radio("Выберите сценарий:", scr_titles)
            if st.session_state.get('selected_script') != "__NEW_SCRIPT__":
                st.session_state['selected_script'] = chosen_scr
        else:
            st.info("Сценариев пока нет.")

        with st.expander("💡 Как делать скрытые заголовки?"):
            st.markdown("""
            В тексте сценария используйте решетки в начале строки:
            * `# Заголовок` — создаст **главный скрытый блок** (1 уровень).
            * `## Подзаголовок` — создаст **вложенный скрытый подзаголовок** (2 уровень) внутри первого.
            * `### Деталь` — создаст **глубокий спойлер** (3 уровень).
            """)

    with col_s_right:
        default_template = (
            "Вступление к сценарию (видно сразу).\n\n"
            "# Акт 1. Тень над Городом\n"
            "Общее описание первого акта.\n\n"
            "## Сцена 1. Встреча в порту\n"
            "Диалог героев у старого склада.\n\n"
            "### Секретная улика (Спойлер)\n"
            "Если игроки обыщут ящик, они найдут медальон.\n\n"
            "## Сцена 2. Погоня\n"
            "Динамическая сцена на крышах.\n\n"
            "# Акт 2. Финальная битва\n"
            "Описание развязки."
        )

        if st.session_state.get('selected_script') == "__NEW_SCRIPT__" or df_scr.empty:
            st.subheader("✍️ Создание нового сценария")
            s_title = st.text_input("Название сценария / Главы:")
            c_a1, c_a2 = st.columns(2)
            with c_a1:
                s_act = st.text_input("Акт / Сюжетная арка:", value="Основной сюжет")
            with c_a2:
                s_status = st.selectbox("Статус готовности:", ["💡 Идея", "✍️ В работе", "✅ Готово"])
            
            s_content = st.text_area("Текст сценария (используйте #, ##, ### для скрытых блоков):", value=default_template, height=400)

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

            tab_s_read, tab_s_edit = st.tabs(["🎭 Интерактивное чтение (Со спойлерами)", "✏️ Редактировать сценарий"])

            with tab_s_read:
                st.caption(f"Арка: **{s_row['Act']}** | Статус: **{s_row['Status']}**")
                st.markdown(f"## {s_row['Title']}")
                st.caption("👆 Нажимайте на цветные блоки ниже, чтобы раскрывать заголовки и вложенные подзаголовки:")
                rendered_html = render_script_with_spoilers(str(s_row['Content']))
                st.markdown(rendered_html, unsafe_allow_html=True)

            with tab_s_edit:
                ed_s_title = st.text_input("Название:", value=s_row['Title'])
                ec1, ec2 = st.columns(2)
                with ec1:
                    ed_s_act = st.text_input("Арка / Акт:", value=s_row['Act'])
                with ec2:
                    statuses = ["💡 Идея", "✍️ В работе", "✅ Готово"]
                    curr_st_idx = statuses.index(s_row['Status']) if s_row['Status'] in statuses else 0
                    ed_s_status = st.selectbox("Статус:", statuses, index=curr_st_idx)

                ed_s_content = st.text_area("Текст сценария (# - Заголовок, ## - Подзаголовок, ### - Секрет):", value=s_row['Content'], height=420)

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
