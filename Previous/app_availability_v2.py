import streamlit as st
import requests
from datetime import datetime, date

# Configuración de la página
st.set_page_config(
    page_title="Disponibilidad de Dispositivos",
    page_icon="",
    layout="wide"
)

# Configuración de Notion
NOTION_TOKEN = "***REMOVED***2f"
NOTION_VERSION = "2022-06-28"
DEVICES_ID = "28d58a35e41180dd8080d1953c15ac23"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}


def get_pages(database_id):
    """Obtiene todas las páginas de una base de datos de Notion"""
    url = f"https://api.notion.com/v1/databases/{database_id}/query"
    payload = {"page_size": 100}
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    return data.get("results", [])


def extract_device_data(page):
    """Extrae los campos específicos de cada dispositivo"""
    props = page["properties"]
    device_data = {}
    
    # Extraer Name
    try:
        if props.get("Name") and props["Name"]["title"]:
            device_data["Name"] = props["Name"]["title"][0]["text"]["content"]
        else:
            device_data["Name"] = "Sin nombre"
    except:
        device_data["Name"] = "Sin nombre"
    
    # Extraer Locations_demo
    try:
        if props.get("📍 Locations_demo") and props["📍 Locations_demo"]["relation"]:
            location_ids = [rel["id"] for rel in props["📍 Locations_demo"]["relation"]]
            device_data["Locations_demo_count"] = len(location_ids)
        else:
            device_data["Locations_demo_count"] = 0
    except:
        device_data["Locations_demo_count"] = 0
    
    # Extraer Start Date
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
                    device_data["Start Date"] = None
            else:
                device_data["Start Date"] = None
        else:
            device_data["Start Date"] = None
    except:
        device_data["Start Date"] = None
    
    # Extraer End Date
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
                    device_data["End Date"] = None
            else:
                device_data["End Date"] = None
        else:
            device_data["End Date"] = None
    except:
        device_data["End Date"] = None
    
    return device_data


def check_availability(device, start_date, end_date):
    """Verifica si un dispositivo está disponible en el rango de fechas"""
    
    # Sin ubicación = disponible
    if device["Locations_demo_count"] == 0:
        return True
    
    # Tiene ubicación, verificar fechas
    device_start = device["Start Date"]
    device_end = device["End Date"]
    
    # Con ubicación pero sin fechas = ocupado indefinidamente
    if device_start is None and device_end is None:
        return False
    
    # Convertir strings a objetos date
    try:
        if device_start:
            device_start_date = datetime.fromisoformat(device_start).date()
        else:
            device_start_date = None
            
        if device_end:
            device_end_date = datetime.fromisoformat(device_end).date()
        else:
            device_end_date = None
    except:
        return False
    
    # Verificar solapamiento
    if device_start_date and device_end_date:
        if (start_date <= device_end_date and end_date >= device_start_date):
            return False
        else:
            return True
    
    elif device_start_date and not device_end_date:
        if end_date >= device_start_date:
            return False
        else:
            return True
    
    elif device_end_date and not device_start_date:
        if start_date <= device_end_date:
            return False
        else:
            return True
    
    return True


# ============================================
# INTERFAZ DE STREAMLIT
# ============================================

st.title("📅 Disponibilidad de Dispositivos")
st.markdown("Consulta qué dispositivos están disponibles para alquilar en un rango de fechas")
st.markdown("---")

# Selección de fechas
col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "📅 Fecha de Inicio",
        value=date.today(),
        format="DD/MM/YYYY"
    )

with col2:
    end_date = st.date_input(
        "📅 Fecha de Fin",
        value=date.today(),
        format="DD/MM/YYYY"
    )

# Validar fechas
if end_date < start_date:
    st.error("⚠️ La fecha de fin debe ser posterior a la fecha de inicio")
    st.stop()

# Mostrar solo los días de duración
days_duration = (end_date - start_date).days + 1
st.info(f"📊 Duración: **{days_duration} días**")

st.markdown("---")

# Botón de búsqueda
if st.button("🔍 Consultar Disponibilidad", type="primary", use_container_width=True):
    with st.spinner("Consultando dispositivos en Notion..."):
        # Obtener dispositivos
        pages = get_pages(DEVICES_ID)
        all_devices = []
        
        for page in pages:
            device_data = extract_device_data(page)
            is_available = check_availability(device_data, start_date, end_date)
            
            if is_available:
                all_devices.append(device_data)
        
        # Guardar en session_state
        st.session_state.available_devices = all_devices
        st.session_state.total_devices = len(pages)
        st.session_state.search_completed = True
        
        # Inicializar selección vacía
        if "selected_devices" not in st.session_state:
            st.session_state.selected_devices = []

# Mostrar resultados
if st.session_state.get("search_completed"):
    available_devices = st.session_state.available_devices
    total_devices = st.session_state.total_devices
    
    
    
    # Resultado compacto en una línea
    st.info(f"📊 Resultado: **{len(available_devices)}/{total_devices}** dispositivos disponibles")
    
    st.markdown("---")

    # Lista de dispositivos disponibles
    if available_devices:
        # Inicializar selected_devices si no existe
        if "selected_devices" not in st.session_state:
            st.session_state.selected_devices = []
        
        # Mostrar en dos columnas
        col1, col2 = st.columns(2)
        
        for idx, device in enumerate(available_devices):
            # Alternar entre columnas
            current_col = col1 if idx % 2 == 0 else col2
            
            with current_col:
                device_name = device['Name']
                device_key = f"device_{device_name}"
                
                # Cajetín que contiene checkbox + nombre en la misma línea
                is_selected = device_name in st.session_state.selected_devices
                
                # Crear dos columnas dentro del cajetín: una para checkbox, otra para nombre
                inner_col1, inner_col2 = st.columns([0.1, 0.9])
                
                with inner_col1:
                    # Checkbox
                    checkbox_value = st.checkbox(
                        "",
                        key=device_key,
                        value=is_selected,
                        label_visibility="collapsed"
                    )
                    
                    # Actualizar selección
                    if checkbox_value and device_name not in st.session_state.selected_devices:
                        st.session_state.selected_devices.append(device_name)
                    elif not checkbox_value and device_name in st.session_state.selected_devices:
                        st.session_state.selected_devices.remove(device_name)
                
                with inner_col2:
                    # Nombre en cajetín
                    st.markdown(
                        f"""
                        <div style='padding: 8px 12px; 
                                    background-color: {"#2AD2C9" if checkbox_value else "#e0e0e0"}; 
                                    border-radius: 6px; 
                                    margin-top: -8px;
                                    border-left: 4px solid {"#2AD2C9" if checkbox_value else "#9e9e9e"};'>
                            <p style='margin: 0; font-size: 16px; font-weight: 500; color: #333;'>
                                {device_name}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Espacio entre dispositivos
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        # Mostrar dispositivos seleccionados
        if st.session_state.selected_devices:
            st.markdown("---")
            st.subheader(f"🎯 Dispositivos Seleccionados ({len(st.session_state.selected_devices)})")
            
            selected_list = ", ".join(st.session_state.selected_devices)
            st.info(f"**Seleccionados:** {selected_list}")
            
            # Botón para limpiar selección
            if st.button("🗑️ Limpiar Selección"):
                st.session_state.selected_devices = []
                st.rerun()
    
    else:
        st.warning("⚠️ No hay dispositivos disponibles en estas fechas")

else:
    st.info("👆 Selecciona las fechas y haz clic en 'Consultar Disponibilidad'")