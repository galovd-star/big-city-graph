import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from pyvis.network import Network
from streamlit_gsheets import GSheetsConnection
import json

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(layout="wide", page_title="БИГ СИТИ: Редактор Вселенной")
st.title("🌐 БИГ СИТИ: Облачный редактор лора и связей")

# 🔗 ВСТАВЬТЕ СЮДА ССЫЛКУ НА ВАШУ GOOGLE ТАБЛИЦУ (внутри кавычек)
SHEET_URL = "https://docs.google.com/spreadsheets/d/1MyQ3vqstgSAarY9NtsAl1f1tnlbgmi-2iljHMf97zBM/edit?gid=0#gid=0"

if SHEET_URL == ":
    st.error("⚠️ Откройте код app.py на GitHub и вставьте настоящую ссылку на вашу Google Таблицу в переменную SHEET_URL.")
    st.stop()

PALETTE = ["#ff4d4d", "#4da6ff", "#9933ff", "#33cc33", "#ffcc00", "#ff66b2", "#339999", "#ff9933", "#996633", "#6699ff"]

# --- ПОДКЛЮЧЕНИЕ К БАЗЕ ДАННЫХ GOOGLE ---
conn = st.connection("gsheets", type=GSheetsConnection)

@st.cache_data(ttl=5) # Кэш на 5 секунд, чтобы все соавторы видели изменения почти в реальном времени
def load_data():
    try:
        nodes = conn.read(spreadsheet=SHEET_URL, worksheet="Nodes")
        edges = conn.read(spreadsheet=SHEET_URL, worksheet="Edges")
        
        # Защита от пустых таблиц
        if nodes.empty:
            nodes = pd.DataFrame(columns=['Имя / Название персонажа', 'Категория плана', 'Пол', 'Группировка', 'Заметки'])
        if edges.empty:
            edges = pd.DataFrame(columns=['Source', 'Target', 'Weight', 'Type'])

        nodes = nodes.dropna(how='all').fillna("Не указано")
        edges = edges.dropna(how='all')
        
        return nodes, edges
    except Exception as e:
        st.error(f"❌ Ошибка связи с Google Таблицей: {e}")
        st.stop()

@st.cache_data(ttl=5)
def load_config():
    try:
        cfg = conn.read(spreadsheet=SHEET_URL, worksheet="Config")
        if not cfg.empty and 'Settings' in cfg.columns:
            val = cfg['Settings'].iloc[0]
            if pd.notna(val) and val.strip() != "":
                return json.loads(val)
    except Exception:
        pass
    return {"colors": {}, "options": {}}

# Функции для записи в облако
def save_nodes_to_cloud(df):
    conn.update(spreadsheet=SHEET_URL, worksheet="Nodes", data=df)
    st.cache_data.clear()

def save_edges_to_cloud(df):
    conn.update(spreadsheet=SHEET_URL, worksheet="Edges", data=df)
    st.cache_data.clear()

def save_config_to_cloud(config_dict):
    df = pd.DataFrame({"Settings": [json.dumps(config_dict, ensure_ascii=False)]})
    conn.update(spreadsheet=SHEET_URL, worksheet="Config", data=df)
    st.cache_data.clear()

# --- ИНИЦИАЛИЗАЦИЯ ПАМЯТИ ---
if 'nodes' not in st.session_state or 'edges' not in st.session_state:
    st.session_state['nodes'], st.session_state['edges'] = load_data()
if 'config' not in st.session_state:
    st.session_state['config'] = load_config()

# Окно синхронизации (кнопка принудительного обновления для соавторов)
col_sync1, col_sync2 = st.columns([8, 2])
with col_sync2:
    if st.button("🔄 Обновить данные из облака", use_container_width=True):
        st.cache_data.clear()
        st.session_state['nodes'], st.session_state['edges'] = load_data()
        st.session_state['config'] = load_config()
        st.rerun()

st.write("---")

# --- ВКЛАДКИ ИНТЕРФЕЙСА ---
tab_graph, tab_chars, tab_edges = st.tabs(["🕸 Интерактивный Граф", "👤 Редактор Персонажей", "🔗 Редактор Связей"])

# --- ВКЛАДКА 2: РЕДАКТОР ПЕРСОНАЖЕЙ ---
with tab_chars:
    st.subheader("Управление Облачной Базой")
    
    col_menu1, col_menu2 = st.columns(2)
    protected_cols = ["Имя / Название персонажа", "Заметки"]
    custom_cols = [c for c in st.session_state['nodes'].columns if c not in protected_cols]

    with col_menu1:
        with st.expander("⚙️ Управление столбцами (Создать / Изменить / Удалить)"):
            new_col = st.text_input("Создать новый столбец (напр. Оружие, Раса):").strip()
            if st.button("➕ Создать столбец"):
                if new_col and new_col not in st.session_state['nodes'].columns:
                    st.session_state['nodes'][new_col] = "Не указано"
                    with st.spinner("Создание столбца в облаке..."):
                        save_nodes_to_cloud(st.session_state['nodes'])
                    st.success(f"Столбец '{new_col}' создан!")
                    st.rerun()

            st.write("---")
            if custom_cols:
                edit_col = st.selectbox("Выберите существующий столбец:", custom_cols)
                c_ren, c_del = st.columns(2)
                with c_ren:
                    new_name = st.text_input("Новое название:").strip()
                    if st.button("✏️ Переименовать") and new_name:
                        st.session_state['nodes'] = st.session_state['nodes'].rename(columns={edit_col: new_name})
                        if edit_col in st.session_state['config']['colors']:
                            st.session_state['config']['colors'][new_name] = st.session_state['config']['colors'].pop(edit_col)
                        if edit_col in st.session_state['config']['options']:
                            st.session_state['config']['options'][new_name] = st.session_state['config']['options'].pop(edit_col)
                        with st.spinner("Синхронизация..."):
                            save_nodes_to_cloud(st.session_state['nodes'])
                            save_config_to_cloud(st.session_state['config'])
                        st.success("Успешно переименовано!")
                        st.rerun()
                with c_del:
                    st.write("") 
                    st.write("")
                    if st.button("🗑 Удалить столбец"):
                        st.session_state['nodes'] = st.session_state['nodes'].drop(columns=[edit_col])
                        with st.spinner("Удаление из облака..."):
                            save_nodes_to_cloud(st.session_state['nodes'])
                        st.success("Удалено!")
                        st.rerun()

    with col_menu2:
        with st.expander("🎨 Настройка вариантов и выбора цветов"):
            if custom_cols:
                color_col = st.selectbox("Выберите категорию для настройки:", custom_cols, key="color_col")
                with st.form("add_variant_form"):
                    st.write("**Добавить новый класс/вариант:**")
                    nv_name = st.text_input("Название (например: Джедай, Герой):").strip()
                    nv_color = st.color_picker("Выберите цвет для графа:", "#4da6ff")
                    if st.form_submit_button("Сохранить вариант и цвет"):
                        if nv_name:
                            if color_col not in st.session_state['config']['colors']:
                                st.session_state['config']['colors'][color_col] = {}
                            st.session_state['config']['colors'][color_col][nv_name] = nv_color
                            if color_col not in st.session_state['config']['options']:
                                st.session_state['config']['options'][color_col] = []
                            if nv_name not in st.session_state['config']['options'][color_col]:
                                st.session_state['config']['options'][color_col].append(nv_name)
                            
                            with st.spinner("Сохранение настроек в облако..."):
                                save_config_to_cloud(st.session_state['config'])
                            st.success(f"'{nv_name}' добавлен!")
                            st.rerun()

    st.write("---")
    
    col_config = {
        "Имя / Название персонажа": st.column_config.TextColumn("Имя (уникальное)", required=True),
        "Заметки": st.column_config.TextColumn("Способности / Лор")
    }
    for col in custom_cols:
        existing_opts = list(st.session_state['nodes'][col].dropna().unique())
        saved_opts = st.session_state['config']['options'].get(col, [])
        all_opts = list(set(existing_opts + saved_opts + ["Не указано"]))
        col_config[col] = st.column_config.SelectboxColumn(col, options=all_opts)

    edited_nodes = st.data_editor(
        st.session_state['nodes'],
        num_rows="dynamic",
        use_container_width=True,
        height=600,
        column_config=col_config
    )
    
    if st.button("💾 Сохранить персонажей", type="primary"):
        df_to_save = edited_nodes.dropna(subset=['Имя / Название персонажа']).fillna("Не указано")
        st.session_state['nodes'] = df_to_save
        with st.spinner("Запись в Google Таблицу..."):
            save_nodes_to_cloud(df_to_save)
        st.success("База персонажей успешно обновлена!")
        st.rerun()

# --- ВКЛАДКА 3: РЕДАКТОР СВЯЗЕЙ ---
with tab_edges:
    st.subheader("Карта отношений")
    valid_chars = st.session_state['nodes']['Имя / Название персонажа'].dropna().unique().tolist()
    
    edited_edges = st.data_editor(
        st.session_state['edges'],
        num_rows="dynamic",
        use_container_width=True,
        height=500,
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
        with st.spinner("Запись связей в Google Таблицу..."):
            save_edges_to_cloud(df_edges_save)
        st.success("Связи успешно сохранены!")
        st.rerun()

# --- ВКЛАДКА 1: ВИЗУАЛИЗАЦИЯ ГРАФА ---
with tab_graph:
    st.sidebar.header("Настройки Карты")
    
    color_options = [c for c in st.session_state['nodes'].columns if c not in ["Имя / Название персонажа", "Заметки"]]
    color_by = st.sidebar.selectbox("🎨 Раскрашивать персонажей по:", color_options)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Фильтры отображения")
    
    active_filters = {}
    for col in color_options:
        unique_vals = st.session_state['nodes'][col].dropna().unique().tolist()
        active_filters[col] = st.sidebar.multiselect(f"Фильтр: {col}", unique_vals, default=unique_vals)

    df_n = st.session_state['nodes'].copy()
    for col, selected_vals in active_filters.items():
        df_n = df_n[df_n[col].isin(selected_vals)]
        
    valid_names = df_n['Имя / Название персонажа'].tolist()
    df_e = st.session_state['edges']
    filtered_edges = df_e[(df_e['Source'].isin(valid_names)) & (df_e['Target'].isin(valid_names))]

    net = Network(height='750px', width='100%', bgcolor='#222222', font_color='white')
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
        
        hover_text = f"👤 {name}\n"
        for c in color_options:
            hover_text += f"▪ {c}: {row.get(c, 'Не указано')}\n"
            
        net.add_node(name, label=name, size=size, color=saved_color, title=hover_text.strip())

    added_nodes = net.get_nodes()
    for _, row in filtered_edges.iterrows():
        src, tgt = str(row['Source']).strip(), str(row['Target']).strip()
        rel_type = str(row.get('Type', 'Связь')).strip()
        weight = float(row.get('Weight', 1.0))
        
        if src in added_nodes and tgt in added_nodes:
            if rel_type.lower() in ['вражда', 'конфликт']:
                edge_color = '#ff4d4d'
            elif rel_type.lower() in ['союз', 'родство', 'подчинение']:
                edge_color = '#4da6ff'
            else:
                edge_color = '#888888'
                
            net.add_edge(src, tgt, value=weight, color=edge_color, title=rel_type)

    net.save_graph('pyvis_graph.html')
    with open('pyvis_graph.html', 'r', encoding='utf-8') as f:
        components.html(f.read(), height=800)
