import streamlit as st
import pandas as pd
import streamlit.components.v1 as components
from pyvis.network import Network
import os
import json

# --- НАСТРОЙКИ СТРАНИЦЫ ---
st.set_page_config(layout="wide", page_title="БИГ СИТИ: Редактор Вселенной")
st.title("🌐 БИГ СИТИ: Интерактивный редактор лора и связей")

# --- ФАЙЛЫ ДАННЫХ ---
NODES_FILE = 'nodes_db.csv'
EDGES_FILE = 'edges_db.csv'
CONFIG_FILE = 'universe_config.json'
EXCEL_IMPORT = 'character-roster_2_2.xlsx'

PALETTE = ["#ff4d4d", "#4da6ff", "#9933ff", "#33cc33", "#ffcc00", "#ff66b2", "#339999", "#ff9933", "#996633", "#6699ff"]

# --- ИНИЦИАЛИЗАЦИЯ ДАННЫХ И КОНФИГА ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"colors": {}, "options": {}}

def save_config():
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(st.session_state['config'], f, ensure_ascii=False, indent=4)

@st.cache_data(show_spinner=False)
def load_initial_data():
    if os.path.exists(NODES_FILE) and os.path.exists(EDGES_FILE):
        nodes = pd.read_csv(NODES_FILE)
        edges = pd.read_csv(EDGES_FILE)
    else:
        try:
            df_temp = pd.read_excel(EXCEL_IMPORT, sheet_name='🎬 Распределение по планам', header=None)
            header_idx = df_temp[df_temp.eq('Имя / Название персонажа').any(axis=1)].index[0]
            nodes = pd.read_excel(EXCEL_IMPORT, sheet_name='🎬 Распределение по планам', skiprows=header_idx)
            nodes = nodes.dropna(subset=['Имя / Название персонажа'])[['Имя / Название персонажа', 'Категория плана', 'Пол']]
            edges = pd.read_excel(EXCEL_IMPORT, sheet_name='Связи')
            edges = edges.dropna(subset=['Source', 'Target'])
        except Exception:
            nodes = pd.DataFrame(columns=['Имя / Название персонажа', 'Категория плана', 'Пол'])
            edges = pd.DataFrame(columns=['Source', 'Target', 'Weight', 'Type'])

    if 'Группировка' not in nodes.columns:
        nodes['Группировка'] = 'Не указано'
    if 'Амплуа' not in nodes.columns:
        nodes['Амплуа'] = 'Не указано'
    if 'Заметки' not in nodes.columns:
        nodes['Заметки'] = ''
    if 'Weight' not in edges.columns:
        edges['Weight'] = 1
    if 'Type' not in edges.columns:
        edges['Type'] = 'Связь'

    nodes = nodes.fillna('Не указано')
    nodes.to_csv(NODES_FILE, index=False)
    edges.to_csv(EDGES_FILE, index=False)
    return nodes, edges

if 'nodes' not in st.session_state:
    st.session_state['nodes'], st.session_state['edges'] = load_initial_data()
if 'config' not in st.session_state:
    st.session_state['config'] = load_config()

# --- ВКЛАДКИ ИНТЕРФЕЙСА ---
tab_graph, tab_chars, tab_edges = st.tabs(["🕸 Интерактивный Граф", "👤 Редактор Персонажей", "🔗 Редактор Связей"])

# --- ВКЛАДКА 2: РЕДАКТОР ПЕРСОНАЖЕЙ ---
with tab_chars:
    st.subheader("Управление Базой Данных")
    
    col_menu1, col_menu2 = st.columns(2)
    # Защищенные колонки (нельзя удалить или переименовать)
    protected_cols = ["Имя / Название персонажа", "Заметки"]
    custom_cols = [c for c in st.session_state['nodes'].columns if c not in protected_cols]

    # --- ПАНЕЛЬ 1: УПРАВЛЕНИЕ СТОЛБЦАМИ ---
    with col_menu1:
        with st.expander("⚙️ Управление столбцами (Создать / Изменить / Удалить)"):
            # Создание
            new_col = st.text_input("Создать новый столбец (напр. Оружие, Раса):").strip()
            if st.button("➕ Создать"):
                if new_col and new_col not in st.session_state['nodes'].columns:
                    st.session_state['nodes'][new_col] = "Не указано"
                    st.session_state['nodes'].to_csv(NODES_FILE, index=False)
                    st.success(f"Столбец '{new_col}' создан!")
                    st.rerun()

            st.write("---")
            # Переименование и удаление
            if custom_cols:
                edit_col = st.selectbox("Выберите существующий столбец:", custom_cols)
                c_ren, c_del = st.columns(2)
                with c_ren:
                    new_name = st.text_input("Новое название:").strip()
                    if st.button("✏️ Переименовать") and new_name:
                        st.session_state['nodes'] = st.session_state['nodes'].rename(columns={edit_col: new_name})
                        # Переносим конфиги цвета
                        if edit_col in st.session_state['config']['colors']:
                            st.session_state['config']['colors'][new_name] = st.session_state['config']['colors'].pop(edit_col)
                        if edit_col in st.session_state['config']['options']:
                            st.session_state['config']['options'][new_name] = st.session_state['config']['options'].pop(edit_col)
                        
                        st.session_state['nodes'].to_csv(NODES_FILE, index=False)
                        save_config()
                        st.success("Переименовано!")
                        st.rerun()
                with c_del:
                    st.write("") # отступ
                    st.write("")
                    if st.button("🗑 Удалить столбец"):
                        st.session_state['nodes'] = st.session_state['nodes'].drop(columns=[edit_col])
                        st.session_state['nodes'].to_csv(NODES_FILE, index=False)
                        st.success("Удалено!")
                        st.rerun()

    # --- ПАНЕЛЬ 2: УПРАВЛЕНИЕ ВАРИАНТАМИ И ЦВЕТАМИ ---
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
                            # Сохраняем цвет
                            if color_col not in st.session_state['config']['colors']:
                                st.session_state['config']['colors'][color_col] = {}
                            st.session_state['config']['colors'][color_col][nv_name] = nv_color
                            
                            # Сохраняем в список опций
                            if color_col not in st.session_state['config']['options']:
                                st.session_state['config']['options'][color_col] = []
                            if nv_name not in st.session_state['config']['options'][color_col]:
                                st.session_state['config']['options'][color_col].append(nv_name)
                                
                            save_config()
                            st.success(f"'{nv_name}' добавлен!")
                            st.rerun()

    st.write("---")
    st.markdown("**Таблица Персонажей:** Дважды кликайте по ячейкам для редактирования.")
    
    # Генерация конфига для таблицы (все столбцы, кроме имени и заметок = выпадающие списки)
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
    
    if st.button("💾 Сохранить изменения в таблице", type="primary"):
        st.session_state['nodes'] = edited_nodes.dropna(subset=['Имя / Название персонажа']).fillna("Не указано")
        st.session_state['nodes'].to_csv(NODES_FILE, index=False)
        st.success("База успешно сохранена!")
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
    if st.button("💾 Сохранить изменения связей", type="primary"):
        st.session_state['edges'] = edited_edges.dropna(subset=['Source', 'Target'])
        st.session_state['edges'].to_csv(EDGES_FILE, index=False)
        st.success("Связи успешно сохранены!")
        st.rerun()

# --- ВКЛАДКА 1: ВИЗУАЛИЗАЦИЯ ГРАФА ---
with tab_graph:
    st.sidebar.header("Настройки Карты")
    
    # 🎨 Выбор того, как раскрашивать персонажей
    color_options = [c for c in st.session_state['nodes'].columns if c not in ["Имя / Название персонажа", "Заметки"]]
    color_by = st.sidebar.selectbox("🎨 Раскрашивать персонажей по:", color_options)
    
    st.sidebar.markdown("---")
    st.sidebar.subheader("Фильтры отображения")
    
    # Автогенерация фильтров для всех колонок
    active_filters = {}
    for col in color_options:
        unique_vals = st.session_state['nodes'][col].dropna().unique().tolist()
        active_filters[col] = st.sidebar.multiselect(f"Фильтр: {col}", unique_vals, default=unique_vals)

    # Применение фильтров
    df_n = st.session_state['nodes'].copy()
    for col, selected_vals in active_filters.items():
        df_n = df_n[df_n[col].isin(selected_vals)]
        
    valid_names = df_n['Имя / Название персонажа'].tolist()
    df_e = st.session_state['edges']
    filtered_edges = df_e[(df_e['Source'].isin(valid_names)) & (df_e['Target'].isin(valid_names))]

    # Настройка сети
    net = Network(height='750px', width='100%', bgcolor='#222222', font_color='white')
    net.force_atlas_2based(gravity=-35)

    # Рисуем узлы
    unique_color_targets = df_n[color_by].dropna().unique().tolist()
    for _, row in df_n.iterrows():
        name = str(row['Имя / Название персонажа']).strip()
        plan = str(row.get('Категория плана', '3 план'))
        val = str(row.get(color_by, 'Не указано'))
        
        # Получаем цвет из сохраненных (вкладка 2), если его нет - берем дефолтный из палитры
        saved_color = st.session_state['config']['colors'].get(color_by, {}).get(val)
        if not saved_color:
            color_idx = unique_color_targets.index(val) if val in unique_color_targets else 0
            saved_color = PALETTE[color_idx % len(PALETTE)]
            if val == "Не указано": saved_color = "#ffffff"
        
        size = 25 if '1' in plan else (15 if '2' in plan else 10)
        
        # Всплывающая подсказка
        hover_text = f"👤 {name}\n"
        for c in color_options:
            hover_text += f"▪ {c}: {row.get(c, 'Не указано')}\n"
            
        net.add_node(name, label=name, size=size, color=saved_color, title=hover_text.strip())

    # Рисуем линии
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