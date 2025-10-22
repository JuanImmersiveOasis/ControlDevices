import streamlit as st
import requests
import json
from datetime import datetime

# ============================================
# CONFIGURACIÓN INICIAL
# ============================================

# Configuración de la página de Streamlit
st.set_page_config(
    page_title="Devices Dashboard",
    page_icon="📱",
    layout="wide"
)

# Credenciales y configuración de Notion
NOTION_TOKEN = "***REMOVED***2f"
NOTION_VERSION = "2022-06-28"
DEVICES_ID = "28d58a35e41180dd8080d1953c15ac23"

# Headers necesarios para hacer peticiones a Notion
headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


# ============================================
# FUNCIONES PARA OBTENER DATOS DE NOTION
# ============================================

def get_pages(database_id):
    """
    Obtiene todas las páginas de una base de datos de Notion
    
    Parámetros:
    - database_id: El ID de la base de datos en Notion
    
    Retorna:
    - Una lista con todas las páginas (dispositivos) encontradas
    """
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"page_size": 100}
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    return data.get("results", [])


def extract_device_data(page):
    """
    Extrae los campos específicos de cada dispositivo
    
    Parámetros:
    - page: Una página individual de Notion (representa un dispositivo)
    
    Retorna:
    - Un diccionario con los datos limpios del dispositivo
    """
    props = page["properties"]
    device_data = {}
    
    # Extraer Name (nombre del dispositivo)
    try:
        if props.get("Name") and props["Name"]["title"]:
            device_data["Name"] = props["Name"]["title"][0]["text"]["content"]
        else:
            device_data["Name"] = "Sin nombre"
    except:
        device_data["Name"] = "Sin nombre"
    
    # Extraer Tags (tipo de dispositivo: móvil, tablet, etc.)
    try:
        if props.get("Tags") and props["Tags"].get("select"):
            device_data["Tags"] = props["Tags"]["select"]["name"]
        else:
            device_data["Tags"] = "Sin tags"
    except:
        device_data["Tags"] = "Sin tags"
    
    # Extraer Locations_demo (ubicaciones relacionadas)
    try:
        if props.get("📍 Locations_demo") and props["📍 Locations_demo"]["relation"]:
            location_ids = [rel["id"] for rel in props["📍 Locations_demo"]["relation"]]
            device_data["Locations_demo"] = location_ids
            device_data["Locations_demo_count"] = len(location_ids)
        else:
            device_data["Locations_demo"] = []
            device_data["Locations_demo_count"] = 0
    except:
        device_data["Locations_demo"] = []
        device_data["Locations_demo_count"] = 0
    
    # Extraer Location Type (tipo de ubicación)
    try:
        if props.get("Location Type") and props["Location Type"]["rollup"]:
            rollup = props["Location Type"]["rollup"]
            if rollup["type"] == "array" and rollup["array"]:
                first_item = rollup["array"][0]
                if first_item["type"] == "select" and first_item.get("select"):
                    device_data["Location Type"] = first_item["select"]["name"]
                else:
                    device_data["Location Type"] = "No disponible"
            else:
                device_data["Location Type"] = "No disponible"
        else:
            device_data["Location Type"] = "No disponible"
    except:
        device_data["Location Type"] = "No disponible"
    
    # Extraer Start Date (fecha de inicio)
    try:
        if props.get("Start Date") and props["Start Date"]["rollup"]:
            rollup = props["Start Date"]["rollup"]
            if rollup["type"] == "date" and rollup.get("date"):
                device_data["Start Date"] = rollup["date"]["start"]
            elif rollup["type"] == "array" and rollup["array"]:
                first_item = rollup["array"][0]
                if first_item["type"] == "date" and first_item.get("date"):
                    device_data["Start Date"] = first_item["date"]["start"]
                else:
                    device_data["Start Date"] = "No disponible"
            else:
                device_data["Start Date"] = "No disponible"
        else:
            device_data["Start Date"] = "No disponible"
    except:
        device_data["Start Date"] = "No disponible"
    
    # Extraer End Date (fecha de fin)
    try:
        if props.get("End Date") and props["End Date"]["rollup"]:
            rollup = props["End Date"]["rollup"]
            if rollup["type"] == "date" and rollup.get("date"):
                device_data["End Date"] = rollup["date"]["start"]
            elif rollup["type"] == "array" and rollup["array"]:
                first_item = rollup["array"][0]
                if first_item["type"] == "date" and first_item.get("date"):
                    device_data["End Date"] = first_item["date"]["start"]
                else:
                    device_data["End Date"] = "No disponible"
            else:
                device_data["End Date"] = "No disponible"
        else:
            device_data["End Date"] = "No disponible"
    except:
        device_data["End Date"] = "No disponible"
    
    return device_data


# ============================================
# INTERFAZ DE STREAMLIT
# ============================================

# Título principal
st.title("📱 Dashboard de Dispositivos")
st.markdown("---")

# Botón para cargar datos
if st.button("🔄 Cargar datos desde Notion", type="primary"):
    with st.spinner("Obteniendo datos de Notion..."):
        # Obtener páginas desde Notion
        pages = get_pages(DEVICES_ID)
        
        # Procesar cada dispositivo
        all_devices = []
        for page in pages:
            device_data = extract_device_data(page)
            all_devices.append(device_data)
        
        # 🆕 ORDENAR ALFABÉTICAMENTE por el campo "Name"
        # La función sorted() ordena la lista
        # key=lambda x: x['Name'].lower() significa: ordena por el Name, en minúsculas
        all_devices_sorted = sorted(all_devices, key=lambda x: x['Name'].lower())
        
        # Guardar en session_state para mantener los datos entre recargas
        st.session_state.devices = all_devices_sorted
        st.success(f"✅ Se cargaron {len(all_devices_sorted)} dispositivos (ordenados alfabéticamente)")

# Mostrar datos si existen
if "devices" in st.session_state and st.session_state.devices:
    devices = st.session_state.devices
    
    # Estadísticas generales
    st.header("📊 Estadísticas Generales")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Dispositivos", len(devices))
    
    with col2:
        devices_with_location = sum(1 for d in devices if d['Locations_demo_count'] > 0)
        st.metric("Con Ubicación", devices_with_location)
    
    with col3:
        devices_without_location = sum(1 for d in devices if d['Locations_demo_count'] == 0)
        st.metric("Sin Ubicación", devices_without_location)
    
    with col4:
        devices_with_tags = sum(1 for d in devices if d['Tags'] != "Sin tags")
        st.metric("Con Tags", devices_with_tags)
    
    st.markdown("---")
    
    # 🆕 NUEVO: SWITCH PARA FILTRAR POR TYPE (TAGS)
    st.header("🔘 Filtrar por Tipo de Dispositivo")
    
    # Extraer todos los tags únicos que existen
    # set() elimina duplicados, sorted() los ordena alfabéticamente
    all_tags = sorted(list(set([d['Tags'] for d in devices])))
    
    # Inicializar el filtro seleccionado en session_state
    # Esto permite que el filtro se mantenga entre recargas
    if 'selected_type_filter' not in st.session_state:
        st.session_state.selected_type_filter = "Todos"
    
    # Crear los botones tipo "pills"
    # Creamos columnas: una para "Todos" y una para cada tag
    cols = st.columns(len(all_tags) + 1)
    
    # Botón "Todos"
    with cols[0]:
        if st.button("🔵 Todos", use_container_width=True, 
                     type="primary" if st.session_state.selected_type_filter == "Todos" else "secondary"):
            st.session_state.selected_type_filter = "Todos"
            st.rerun()  # Recargar la página para aplicar el filtro
    
    # Botón para cada tag
    for idx, tag in enumerate(all_tags):
        with cols[idx + 1]:
            # Si este tag está seleccionado, el botón será "primary" (azul)
            button_type = "primary" if st.session_state.selected_type_filter == tag else "secondary"
            if st.button(f"📱 {tag}", use_container_width=True, type=button_type, key=f"tag_{tag}"):
                st.session_state.selected_type_filter = tag
                st.rerun()  # Recargar la página para aplicar el filtro
    
    st.markdown("---")
    
    # Filtros adicionales
    st.header("🔍 Filtros Adicionales")
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro por location type
        all_location_types = list(set([d['Location Type'] for d in devices]))
        selected_location_type = st.selectbox("Filtrar por Location Type", ["Todos"] + all_location_types)
    
    with col2:
        # Filtro por ubicación
        has_location_filter = st.selectbox("Tiene Ubicación", ["Todos", "Sí", "No"])
    
    # Aplicar TODOS los filtros
    filtered_devices = devices.copy()
    
    # 🆕 Aplicar filtro del switch de Types
    if st.session_state.selected_type_filter != "Todos":
        filtered_devices = [d for d in filtered_devices if d['Tags'] == st.session_state.selected_type_filter]
    
    # Aplicar filtro de Location Type
    if selected_location_type != "Todos":
        filtered_devices = [d for d in filtered_devices if d['Location Type'] == selected_location_type]
    
    # Aplicar filtro de tiene/no tiene ubicación
    if has_location_filter == "Sí":
        filtered_devices = [d for d in filtered_devices if d['Locations_demo_count'] > 0]
    elif has_location_filter == "No":
        filtered_devices = [d for d in filtered_devices if d['Locations_demo_count'] == 0]
    
    st.info(f"Mostrando {len(filtered_devices)} de {len(devices)} dispositivos")
    
    st.markdown("---")
    
    # Tabla de dispositivos
    st.header("📋 Lista de Dispositivos")
    
    # Mostrar cada dispositivo en un expander
    for i, device in enumerate(filtered_devices):
        with st.expander(f"📱 {device['Name']} - {device['Tags']}"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.write("**Información Básica:**")
                st.write(f"• **Name:** {device['Name']}")
                st.write(f"• **Tags:** {device['Tags']}")
                st.write(f"• **Location Type:** {device['Location Type']}")
            
            with col2:
                st.write("**Fechas:**")
                st.write(f"• **Start Date:** {device['Start Date']}")
                st.write(f"• **End Date:** {device['End Date']}")
                st.write(f"• **Ubicaciones:** {device['Locations_demo_count']}")
            
            if device['Locations_demo']:
                st.write("**Location IDs:**")
                for loc_id in device['Locations_demo']:
                    st.code(loc_id, language=None)
    
    # Botón para descargar JSON
    st.markdown("---")
    st.header("💾 Descargar Datos")
    
    json_str = json.dumps(filtered_devices, indent=2, ensure_ascii=False)
    st.download_button(
        label="📥 Descargar como JSON",
        data=json_str,
        file_name="devices_filtered.json",
        mime="application/json"
    )

else:
    st.info("👆 Haz clic en el botón 'Cargar datos desde Notion' para comenzar")