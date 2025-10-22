import streamlit as st
import requests
import json
from datetime import datetime, date

# Configuración de la página
st.set_page_config(
    page_title="Disponibilidad de Dispositivos",
    page_icon="📅",
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
    
    # Extraer Tags
    try:
        if props.get("Tags") and props["Tags"].get("select"):
            device_data["Tags"] = props["Tags"]["select"]["name"]
        else:
            device_data["Tags"] = "Sin tags"
    except:
        device_data["Tags"] = "Sin tags"
    
    # Extraer Locations_demo
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
    
    # Extraer Location Type
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
    """
    Verifica si un dispositivo está disponible en el rango de fechas solicitado.
    
    Reglas:
    1. Si el device NO tiene ubicación → DISPONIBLE
    2. Si el device tiene ubicación pero NO tiene fechas → NO DISPONIBLE (ocupado indefinidamente)
    3. Si el device tiene fechas:
       - DISPONIBLE si NO hay conflicto de fechas
       - NO DISPONIBLE si hay solapamiento
    """
    
    # Regla 1: Sin ubicación = disponible
    if device["Locations_demo_count"] == 0:
        return True, "Sin ubicación asignada"
    
    # El device tiene ubicación, verificar fechas
    device_start = device["Start Date"]
    device_end = device["End Date"]
    
    # Regla 2: Tiene ubicación pero sin fechas = ocupado indefinidamente
    if device_start is None and device_end is None:
        return False, "Ocupado (sin fechas definidas)"
    
    # Convertir strings a objetos date para comparar
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
        return False, "Error al procesar fechas"
    
    # Regla 3: Verificar solapamiento de fechas
    # Hay conflicto si:
    # - El inicio solicitado está entre las fechas del device
    # - El fin solicitado está entre las fechas del device
    # - El periodo solicitado contiene completamente el periodo del device
    
    if device_start_date and device_end_date:
        # Caso: El device tiene inicio y fin
        # NO disponible si hay cualquier solapamiento
        if (start_date <= device_end_date and end_date >= device_start_date):
            return False, f"Ocupado del {device_start} al {device_end}"
        else:
            return True, f"Disponible (ocupado del {device_start} al {device_end})"
    
    elif device_start_date and not device_end_date:
        # Caso: Solo tiene fecha de inicio (ocupado desde esa fecha en adelante)
        if end_date >= device_start_date:
            return False, f"Ocupado desde {device_start}"
        else:
            return True, f"Disponible (se ocupará desde {device_start})"
    
    elif device_end_date and not device_start_date:
        # Caso: Solo tiene fecha de fin (ocupado hasta esa fecha)
        if start_date <= device_end_date:
            return False, f"Ocupado hasta {device_end}"
        else:
            return True, f"Disponible (estuvo ocupado hasta {device_end})"
    
    return True, "Disponible"


# ============================================
# INTERFAZ DE STREAMLIT
# ============================================

st.title("Buscador de equipos disponibles")
st.markdown("Selecciona un rango de fechas para ver qué dispositivos están disponibles para alquiler")
st.markdown("---")

# Sección de selección de fechas
st.header("🗓️ Seleccione fechas del evento")

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "Fecha de Inicio",
        value=date.today(),
        help="Fecha en la que comenzará el alquiler"
    )

with col2:
    end_date = st.date_input(
        "Fecha de Fin",
        value=date.today(),
        help="Fecha en la que terminará el alquiler"
    )

# Validar que la fecha de fin sea posterior a la de inicio
if end_date < start_date:
    st.error("⚠️ La fecha de fin debe ser posterior a la fecha de inicio")
    st.stop()

# Mostrar el rango seleccionado
days_duration = (end_date - start_date).days + 1
st.info(f"📊 Duración del alquiler: **{days_duration} días**")

st.markdown("---")

# Botón para buscar dispositivos
if st.button("🔍 Buscar Dispositivos Disponibles", type="primary"):
    with st.spinner("Consultando disponibilidad en Notion..."):
        # Obtener todos los dispositivos
        pages = get_pages(DEVICES_ID)
        all_devices = []
        
        for page in pages:
            device_data = extract_device_data(page)
            
            # Verificar disponibilidad
            is_available, reason = check_availability(device_data, start_date, end_date)
            device_data["is_available"] = is_available
            device_data["availability_reason"] = reason
            
            all_devices.append(device_data)
        
        # Guardar en session_state
        st.session_state.devices = all_devices
        st.session_state.start_date = start_date
        st.session_state.end_date = end_date
        
        st.success(f"✅ Análisis completado: {len(all_devices)} dispositivos procesados")

# Mostrar resultados si existen
if "devices" in st.session_state:
    devices = st.session_state.devices
    start_date = st.session_state.start_date
    end_date = st.session_state.end_date
    
    # Separar disponibles y no disponibles
    available_devices = [d for d in devices if d["is_available"]]
    unavailable_devices = [d for d in devices if not d["is_available"]]
    
    # Estadísticas
    st.header("Resultados")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Dispositivos", len(devices))
    
    with col2:
        st.metric("✅ Disponibles", len(available_devices), delta=f"{round(len(available_devices)/len(devices)*100)}%")
    
    with col3:
        st.metric("❌ No Disponibles", len(unavailable_devices), delta=f"{round(len(unavailable_devices)/len(devices)*100)}%")
    
    st.markdown("---")
    
    # Filtros
    st.header("🔍 Filtros")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtro por disponibilidad
        availability_filter = st.radio(
            "Mostrar:",
            ["Todos", "Solo Disponibles", "Solo No Disponibles"],
            horizontal=True
        )
    
    with col2:
        # Filtro por Tags
        all_tags = list(set([d['Tags'] for d in devices if d['Tags'] != "Sin tags"]))
        all_tags.sort()
        selected_tags = st.multiselect(
            "Filtrar por Tags",
            all_tags,
            help="Puedes seleccionar múltiples tags"
        )
    
    # Aplicar filtros
    filtered_devices = devices.copy()
    
    # Filtro de disponibilidad
    if availability_filter == "Solo Disponibles":
        filtered_devices = [d for d in filtered_devices if d["is_available"]]
    elif availability_filter == "Solo No Disponibles":
        filtered_devices = [d for d in filtered_devices if not d["is_available"]]
    
    # Filtro de tags
    if selected_tags:
        filtered_devices = [d for d in filtered_devices if d["Tags"] in selected_tags]
    
    st.info(f"📋 Mostrando {len(filtered_devices)} de {len(devices)} dispositivos")
    
    st.markdown("---")
    
    # Mostrar dispositivos DISPONIBLES
    if any(d["is_available"] for d in filtered_devices):
        st.header("✅ Dispositivos Disponibles")
        
        available_filtered = [d for d in filtered_devices if d["is_available"]]
        
        for device in available_filtered:
            with st.expander(f"✅ {device['Name']} - {device['Tags']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Información:**")
                    st.write(f"• **Name:** {device['Name']}")
                    st.write(f"• **Tags:** {device['Tags']}")
                    st.write(f"• **Estado:** ✅ {device['availability_reason']}")
                
                with col2:
                    st.write("**Ocupación Actual:**")
                    if device['Start Date']:
                        st.write(f"• **Start Date:** {device['Start Date']}")
                    else:
                        st.write(f"• **Start Date:** Sin fecha")
                    
                    if device['End Date']:
                        st.write(f"• **End Date:** {device['End Date']}")
                    else:
                        st.write(f"• **End Date:** Sin fecha")
                    
                    st.write(f"• **Location Type:** {device['Location Type']}")
        
        st.markdown("---")
    
    # Mostrar dispositivos NO DISPONIBLES
    if any(not d["is_available"] for d in filtered_devices):
        st.header("❌ Dispositivos No Disponibles")
        
        unavailable_filtered = [d for d in filtered_devices if not d["is_available"]]
        
        for device in unavailable_filtered:
            with st.expander(f"❌ {device['Name']} - {device['Tags']}", expanded=False):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.write("**Información:**")
                    st.write(f"• **Name:** {device['Name']}")
                    st.write(f"• **Tags:** {device['Tags']}")
                    st.write(f"• **Estado:** ❌ {device['availability_reason']}")
                
                with col2:
                    st.write("**Ocupación Actual:**")
                    if device['Start Date']:
                        st.write(f"• **Start Date:** {device['Start Date']}")
                    else:
                        st.write(f"• **Start Date:** Sin fecha")
                    
                    if device['End Date']:
                        st.write(f"• **End Date:** {device['End Date']}")
                    else:
                        st.write(f"• **End Date:** Sin fecha")
                    
                    st.write(f"• **Location Type:** {device['Location Type']}")
    
    # Botón de descarga
    st.markdown("---")
    st.header("💾 Exportar Resultados")
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Descargar solo disponibles
        available_json = json.dumps(available_filtered if 'available_filtered' in locals() else available_devices, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Descargar Disponibles (JSON)",
            data=available_json,
            file_name=f"disponibles_{start_date}_{end_date}.json",
            mime="application/json"
        )
    
    with col2:
        # Descargar todos los resultados
        all_json = json.dumps(filtered_devices, indent=2, ensure_ascii=False)
        st.download_button(
            label="📥 Descargar Todos (JSON)",
            data=all_json,
            file_name=f"dispositivos_{start_date}_{end_date}.json",
            mime="application/json"
        )

else:
    st.info("👆 Selecciona las fechas y haz clic en 'Buscar Dispositivos Disponibles' para comenzar")