import streamlit as st
import requests
from datetime import datetime, date


# Configuración de la página
st.set_page_config(
    page_title="Disponibilidad de dispositivos",
    page_icon="",
    layout="centered"
)

# Logo + título en la misma línea (alineados a la izquierda)
logo_col, title_col = st.columns([1, 9])

with logo_col:
    st.markdown("<div style='margin-top: 30px;'></div>", unsafe_allow_html=True)
    st.image("img/icono.png", width=80)

with title_col:
    st.markdown("<h1 style='margin-top: 20px;'>Disponibilidad de dispositivos</h1>", unsafe_allow_html=True)

st.markdown("Consulta qué dispositivos están disponibles para alquilar en un rango de fechas")
st.markdown("---")

# Configuración de Notion - IDs DE PRODUCCIÓN
NOTION_TOKEN = "***REMOVED***2f"
NOTION_VERSION = "2022-06-28"
DEVICES_ID = "43e15b677c8c4bd599d7c602f281f1da"  # ← ID NUEVO
LOCATIONS_ID = "28758a35e4118045abe6e37534c44974"  # ← ID NUEVO

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
    
    # Extraer ID de la página
    device_data["id"] = page["id"]
    
    # Extraer Name
    try:
        if props.get("Name") and props["Name"]["title"]:
            device_data["Name"] = props["Name"]["title"][0]["text"]["content"]
        else:
            device_data["Name"] = "Sin nombre"
    except:
        device_data["Name"] = "Sin nombre"
    
    # Extraer Locations (CAMBIO: sin emoji)
    try:
        if props.get("Locations") and props["Locations"]["relation"]:
            location_ids = [rel["id"] for rel in props["Locations"]["relation"]]
            device_data["Locations_count"] = len(location_ids)
        else:
            device_data["Locations_count"] = 0
    except:
        device_data["Locations_count"] = 0
    
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
    if device["Locations_count"] == 0:
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


def get_in_house_locations():
    """Obtiene locations de tipo In House con contador de devices desde campo Units"""
    url = f"https://api.notion.com/v1/databases/{LOCATIONS_ID}/query"
    
    payload = {
        "filter": {
            "property": "Type",
            "select": {
                "equals": "In House"
            }
        },
        "page_size": 100
    }
    
    response = requests.post(url, json=payload, headers=headers)
    data = response.json()
    
    locations = []
    for page in data.get("results", []):
        props = page["properties"]
        
        # Extraer Name
        try:
            if props.get("Name") and props["Name"]["title"]:
                name = props["Name"]["title"][0]["text"]["content"]
            else:
                name = "Sin nombre"
        except:
            name = "Sin nombre"
        
        # Extraer Units (contador de devices)
        device_count = 0
        try:
            if props.get("Units"):
                # Units puede ser de tipo "rollup" o "number"
                if props["Units"].get("rollup"):
                    # Si es rollup
                    rollup = props["Units"]["rollup"]
                    if rollup["type"] == "number" and rollup.get("number") is not None:
                        device_count = int(rollup["number"])
                elif props["Units"].get("number") is not None:
                    # Si es campo numérico directo
                    device_count = int(props["Units"]["number"])
        except:
            device_count = 0
        
        locations.append({
            "id": page["id"],
            "name": name,
            "device_count": device_count
        })
    
    return locations


def create_client_location(name, start_date, end_date):
    """Crea un nuevo location tipo Client con fechas"""
    url = "https://api.notion.com/v1/pages"
    
    start_date_iso = start_date.isoformat()
    end_date_iso = end_date.isoformat()
    
    payload = {
        "parent": {"database_id": LOCATIONS_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": name}}]
            },
            "Type": {
                "select": {"name": "Client"}
            },
            "Start Date": {
                "date": {"start": start_date_iso}
            },
            "End Date": {
                "date": {"start": end_date_iso}
            }
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()["id"]
    else:
        st.error(f"Error al crear location Client: {response.status_code} - {response.text}")
        return None


def create_in_house_location(name, start_date):
    """Crea un nuevo location tipo In House solo con Start Date"""
    url = "https://api.notion.com/v1/pages"
    
    start_date_iso = start_date.isoformat()
    
    payload = {
        "parent": {"database_id": LOCATIONS_ID},
        "properties": {
            "Name": {
                "title": [{"text": {"content": name}}]
            },
            "Type": {
                "select": {"name": "In House"}
            },
            "Start Date": {
                "date": {"start": start_date_iso}
            }
            # No incluir End Date para In House
        }
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()["id"]
    else:
        st.error(f"Error al crear location In House: {response.status_code} - {response.text}")
        return None


def update_device_location(device_id, location_id):
    """Actualiza un dispositivo asignándole un location"""
    url = f"https://api.notion.com/v1/pages/{device_id}"
    
    payload = {
        "properties": {
            "Locations": {  # CAMBIO: sin emoji
                "relation": [{"id": location_id}]
            }
        }
    }
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.status_code == 200


def update_location_start_date(location_id, start_date):
    """Actualiza la Start Date de un location"""
    url = f"https://api.notion.com/v1/pages/{location_id}"
    
    start_date_iso = start_date.isoformat()
    
    payload = {
        "properties": {
            "Start Date": {
                "date": {"start": start_date_iso}
            }
        }
    }
    
    response = requests.patch(url, json=payload, headers=headers)
    return response.status_code == 200


def assign_devices_client(device_names, location_name, start_date, end_date, all_devices):
    """Asigna dispositivos a un nuevo location tipo Client"""
    
    # Validar nombre
    if not location_name or location_name.strip() == "":
        st.error("⚠️ El nombre del proyecto no puede estar vacío")
        return False
    
    # Crear nuevo location Client
    with st.spinner("Creando nuevo proyecto..."):
        location_id = create_client_location(location_name, start_date, end_date)
    
    if not location_id:
        return False
    
    # Asignar devices
    device_ids = [d["id"] for d in all_devices if d["Name"] in device_names]
    success_count = 0
    
    with st.spinner(f"Asignando {len(device_ids)} dispositivos..."):
        for device_id in device_ids:
            if update_device_location(device_id, location_id):
                success_count += 1
    
    if success_count == len(device_ids):
        st.success(f"✅ ¡Éxito! {success_count} dispositivos asignados al proyecto '{location_name}'")
        return True
    else:
        st.warning(f"⚠️ Se asignaron {success_count} de {len(device_ids)} dispositivos")
        return False


def assign_devices_in_house(device_names, location_id, location_name, start_date, all_devices):
    """Asigna dispositivos a un location In House existente y actualiza Start Date"""
    
    # Actualizar Start Date del location
    with st.spinner("Actualizando fecha de inicio..."):
        if not update_location_start_date(location_id, start_date):
            st.warning("⚠️ No se pudo actualizar la fecha de inicio del location")
    
    # Asignar devices
    device_ids = [d["id"] for d in all_devices if d["Name"] in device_names]
    success_count = 0
    
    with st.spinner(f"Asignando {len(device_ids)} dispositivos..."):
        for device_id in device_ids:
            if update_device_location(device_id, location_id):
                success_count += 1
    
    if success_count == len(device_ids):
        st.success(f"✅ ¡Éxito! {success_count} dispositivos asignados a '{location_name}'")
        return True
    else:
        st.warning(f"⚠️ Se asignaron {success_count} de {len(device_ids)} dispositivos")
        return False


# ============================================
# INTERFAZ DE STREAMLIT
# ============================================

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
        st.session_state.query_start_date = start_date
        st.session_state.query_end_date = end_date
        
        # Inicializar selección vacía
        if "selected_devices" not in st.session_state:
            st.session_state.selected_devices = []

# Mostrar resultado justo debajo del botón
if st.session_state.get("search_completed"):
    available_devices = st.session_state.available_devices
    total_devices = st.session_state.total_devices
    
    # Resultado compacto
    st.info(f"📊 Resultado: **{len(available_devices)}/{total_devices}** dispositivos disponibles")

# Línea divisoria
st.markdown("---")

# Mostrar lista de dispositivos
if st.session_state.get("search_completed"):
    available_devices = st.session_state.available_devices
    
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
                                    background-color: {"#B3E5E6" if checkbox_value else "#e0e0e0"}; 
                                    border-radius: 6px; 
                                    margin-top: -8px;
                                    border-left: 4px solid {"#00859B" if checkbox_value else "#9e9e9e"};'>
                            <p style='margin: 0; font-size: 16px; font-weight: 500; color: #333;'>
                                {device_name}
                            </p>
                        </div>
                        """,
                        unsafe_allow_html=True
                    )
                
                # Espacio entre dispositivos
                st.markdown("<div style='margin-bottom: 10px;'></div>", unsafe_allow_html=True)
        
        # Mostrar formulario de asignación si hay dispositivos seleccionados
        if st.session_state.selected_devices:
            st.markdown("---")
            st.subheader(f"🎯 Asignar ubicación ({len(st.session_state.selected_devices)} dispositivos)")
            
            # Selector de tipo de ubicación - DESPLEGABLE
            location_type = st.selectbox(
                "Tipo de Ubicación",
                ["Client", "In House"],
                index=0  # Client por defecto
            )
            
            st.markdown("---")
            
            # Información de dispositivos seleccionados
            selected_list = ", ".join(st.session_state.selected_devices)
            st.info(f"**Seleccionados:** {selected_list}")
            
            # Mostrar fechas según el tipo
            if location_type == "Client":
                query_start = st.session_state.query_start_date
                query_end = st.session_state.query_end_date
                st.info(f"📅 **Fechas:** {query_start.strftime('%d/%m/%Y')} - {query_end.strftime('%d/%m/%Y')}")
            else:  # In House
                today = date.today()
                st.info(f"📅 **Fecha de inicio:** {today.strftime('%d/%m/%Y')}")
            
            st.markdown("---")
            
            # Formulario según el tipo
            if location_type == "Client":
                # FORMULARIO CLIENT
                st.write("**📋 Nuevo Proyecto Cliente**")
                
                client_name = st.text_input(
                    "Nombre del Proyecto",
                    placeholder="Ej: Proyecto Barcelona 2025",
                    key="client_name_input"
                )
                
                if st.button("Asignar", type="primary", use_container_width=True):
                    query_start = st.session_state.query_start_date
                    query_end = st.session_state.query_end_date
                    
                    success = assign_devices_client(
                        st.session_state.selected_devices,
                        client_name,
                        query_start,
                        query_end,
                        available_devices
                    )
                    
                    if success:
                        st.session_state.selected_devices = []
                        st.session_state.search_completed = False
                        st.session_state.available_devices = []
                        st.rerun()
            
            else:
                # FORMULARIO IN HOUSE
                st.write("**🏠 Asignar a In House**")
                
                # Obtener locations In House
                with st.spinner("Cargando ubicaciones In House..."):
                    in_house_locations = get_in_house_locations()
                
                if not in_house_locations:
                    st.warning("⚠️ No hay ubicaciones In House disponibles")
                    st.info("💡 Crea una nueva ubicación In House")
                    
                    # Formulario para crear nueva
                    new_in_house_name = st.text_input(
                        "Nombre de la ubicación",
                        placeholder="Ej: Casa Juan",
                        key="new_in_house_name"
                    )
                    
                    if st.button("Crear y Asignar", type="primary", use_container_width=True):
                        if not new_in_house_name or new_in_house_name.strip() == "":
                            st.error("⚠️ El nombre no puede estar vacío")
                        else:
                            today = date.today()
                            with st.spinner("Creando ubicación..."):
                                location_id = create_in_house_location(new_in_house_name, today)
                            
                            if location_id:
                                success = assign_devices_in_house(
                                    st.session_state.selected_devices,
                                    location_id,
                                    new_in_house_name,
                                    today,
                                    available_devices
                                )
                                
                                if success:
                                    st.session_state.selected_devices = []
                                    st.session_state.search_completed = False
                                    st.session_state.available_devices = []
                                    st.rerun()
                
                else:
                    # Mostrar dropdown con locations existentes
                    location_options = {
                        f"📍 {loc['name']} ({loc['device_count']} devices)": loc['id'] 
                        for loc in in_house_locations
                    }
                    
                    selected_location_display = st.selectbox(
                        "Seleccionar ubicación existente",
                        options=list(location_options.keys())
                    )
                    
                    selected_location_id = location_options[selected_location_display]
                    selected_location_name = selected_location_display.split(" (")[0].replace("📍 ", "")
                    
                    # Opción para crear nueva
                    with st.expander("➕ O crear nueva ubicación In House"):
                        new_in_house_name = st.text_input(
                            "Nombre de la ubicación",
                            placeholder="Ej: Casa María",
                            key="new_in_house_name_alt"
                        )
                        
                        if st.button("Crear y Asignar Nueva", type="secondary", use_container_width=True):
                            if not new_in_house_name or new_in_house_name.strip() == "":
                                st.error("⚠️ El nombre no puede estar vacío")
                            else:
                                today = date.today()
                                with st.spinner("Creando ubicación..."):
                                    location_id = create_in_house_location(new_in_house_name, today)
                                
                                if location_id:
                                    success = assign_devices_in_house(
                                        st.session_state.selected_devices,
                                        location_id,
                                        new_in_house_name,
                                        today,
                                        available_devices
                                    )
                                    
                                    if success:
                                        st.session_state.selected_devices = []
                                        st.session_state.search_completed = False
                                        st.session_state.available_devices = []
                                        st.rerun()
                    
                    # Botón principal para asignar a existente
                    if st.button("Asignar", type="primary", use_container_width=True):
                        today = date.today()
                        success = assign_devices_in_house(
                            st.session_state.selected_devices,
                            selected_location_id,
                            selected_location_name,
                            today,
                            available_devices
                        )
                        
                        if success:
                            st.session_state.selected_devices = []
                            st.session_state.search_completed = False
                            st.session_state.available_devices = []
                            st.rerun()
    
    else:
        st.warning("⚠️ No hay dispositivos disponibles en estas fechas")

else:
    st.info("👆 Selecciona las fechas y haz clic en 'Consultar Disponibilidad'")