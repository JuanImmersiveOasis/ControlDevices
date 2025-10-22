import streamlit as st
import requests
from datetime import datetime, date


# ============================================
# CONFIGURACIÓN DE LA PÁGINA
# ============================================

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


# ============================================
# CONFIGURACIÓN DE NOTION
# ============================================

NOTION_TOKEN = "***REMOVED***2f"
NOTION_VERSION = "2022-06-28"
DEVICES_ID = "28d58a35e41180dd8080d1953c15ac23"
LOCATIONS_ID = "28d58a35e41180f78235ec7f5132e6d7"

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
    - database_id: ID de la base de datos en Notion
    
    Retorna:
    - Lista con todas las páginas encontradas
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
    - page: Una página individual de Notion (un dispositivo)
    
    Retorna:
    - Diccionario con los datos del dispositivo
    """
    props = page["properties"]
    device_data = {}
    
    # Extraer ID de la página
    device_data["id"] = page["id"]
    
    # Extraer Name (nombre del dispositivo)
    try:
        if props.get("Name") and props["Name"]["title"]:
            device_data["Name"] = props["Name"]["title"][0]["text"]["content"]
        else:
            device_data["Name"] = "Sin nombre"
    except:
        device_data["Name"] = "Sin nombre"
    
    # 🆕 NUEVO: Extraer Tags (tipo de dispositivo)
    # Este campo nos permitirá filtrar por tipo
    try:
        if props.get("Tags") and props["Tags"].get("select"):
            device_data["Tags"] = props["Tags"]["select"]["name"]
        else:
            device_data["Tags"] = "Sin categoría"
    except:
        device_data["Tags"] = "Sin categoría"
    
    # Extraer Locations_demo (ubicaciones relacionadas)
    try:
        if props.get("📍 Locations_demo") and props["📍 Locations_demo"]["relation"]:
            location_ids = [rel["id"] for rel in props["📍 Locations_demo"]["relation"]]
            device_data["Locations_demo_count"] = len(location_ids)
        else:
            device_data["Locations_demo_count"] = 0
    except:
        device_data["Locations_demo_count"] = 0
    
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
                    device_data["Start Date"] = None
            else:
                device_data["Start Date"] = None
        else:
            device_data["Start Date"] = None
    except:
        device_data["Start Date"] = None
    
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
    Verifica si un dispositivo está disponible en el rango de fechas
    
    Parámetros:
    - device: Diccionario con los datos del dispositivo
    - start_date: Fecha de inicio del alquiler (objeto date)
    - end_date: Fecha de fin del alquiler (objeto date)
    
    Retorna:
    - True si está disponible, False si está ocupado
    """
    
    # Sin ubicación = disponible
    if device["Locations_demo_count"] == 0:
        return True
    
    # Tiene ubicación, verificar fechas
    device_start = device["Start Date"]
    device_end = device["End Date"]
    
    # Con ubicación pero sin fechas = ocupado indefinidamente
    if device_start is None and device_end is None:
        return False
    
    # Convertir strings a objetos date para poder compararlos
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
    
    # Verificar solapamiento de fechas
    # Si las fechas se solapan, el dispositivo NO está disponible
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
    """
    Obtiene locations de tipo In House con contador de devices desde campo Units
    
    Retorna:
    - Lista de diccionarios con las ubicaciones In House
    """
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
        
        # Extraer device count del campo Units
        try:
            if props.get("Units") and props["Units"]["number"] is not None:
                device_count = props["Units"]["number"]
            else:
                device_count = 0
        except:
            device_count = 0
        
        locations.append({
            "id": page["id"],
            "name": name,
            "device_count": device_count
        })
    
    return locations


def create_location(name, location_type, start_date, end_date=None):
    """
    Crea una nueva ubicación en Notion
    
    Parámetros:
    - name: Nombre de la ubicación
    - location_type: Tipo de ubicación ("Client" o "In House")
    - start_date: Fecha de inicio
    - end_date: Fecha de fin (opcional)
    
    Retorna:
    - ID de la ubicación creada o None si hay error
    """
    url = "https://api.notion.com/v1/pages"
    
    # Preparar las propiedades básicas
    properties = {
        "Name": {
            "title": [
                {
                    "text": {
                        "content": name
                    }
                }
            ]
        },
        "Type": {
            "select": {
                "name": location_type
            }
        },
        "Start": {
            "date": {
                "start": start_date.isoformat()
            }
        }
    }
    
    # Añadir End date si existe
    if end_date:
        properties["End"] = {
            "date": {
                "start": end_date.isoformat()
            }
        }
    
    payload = {
        "parent": {
            "database_id": LOCATIONS_ID
        },
        "properties": properties
    }
    
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return response.json()["id"]
    else:
        st.error(f"Error al crear ubicación: {response.text}")
        return None


def create_in_house_location(name, start_date):
    """
    Crea una ubicación In House (sin fecha de fin)
    
    Parámetros:
    - name: Nombre de la ubicación
    - start_date: Fecha de inicio
    
    Retorna:
    - ID de la ubicación creada
    """
    return create_location(name, "In House", start_date, end_date=None)


def update_device_location(device_id, location_id):
    """
    Actualiza la ubicación de un dispositivo en Notion
    
    Parámetros:
    - device_id: ID del dispositivo en Notion
    - location_id: ID de la ubicación a asignar
    
    Retorna:
    - True si la actualización fue exitosa, False si hubo error
    """
    url = f"https://api.notion.com/v1/pages/{device_id}"
    
    payload = {
        "properties": {
            "📍 Locations_demo": {
                "relation": [
                    {
                        "id": location_id
                    }
                ]
            }
        }
    }
    
    response = requests.patch(url, json=payload, headers=headers)
    
    if response.status_code == 200:
        return True
    else:
        st.error(f"Error al actualizar dispositivo: {response.text}")
        return False


def assign_devices_client(device_names, client_name, start_date, end_date, available_devices):
    """
    Asigna dispositivos a un nuevo cliente
    
    Parámetros:
    - device_names: Lista de nombres de dispositivos a asignar
    - client_name: Nombre del cliente/destino
    - start_date: Fecha de inicio del alquiler
    - end_date: Fecha de fin del alquiler
    - available_devices: Lista con todos los dispositivos disponibles
    
    Retorna:
    - True si la asignación fue exitosa, False si hubo error
    """
    if not client_name or client_name.strip() == "":
        st.error("⚠️ El nombre del destino no puede estar vacío")
        return False
    
    with st.spinner("Creando ubicación y asignando dispositivos..."):
        # Crear nueva ubicación Client
        location_id = create_location(client_name, "Client", start_date, end_date)
        
        if not location_id:
            return False
        
        # Actualizar cada dispositivo
        success_count = 0
        for device_name in device_names:
            # Buscar el device_id por nombre
            device = next((d for d in available_devices if d["Name"] == device_name), None)
            
            if device:
                if update_device_location(device["id"], location_id):
                    success_count += 1
        
        if success_count == len(device_names):
            st.success(f"✅ {success_count} dispositivos asignados correctamente a '{client_name}'")
            return True
        else:
            st.warning(f"⚠️ Solo se asignaron {success_count} de {len(device_names)} dispositivos")
            return False


def assign_devices_in_house(device_names, location_id, location_name, start_date, available_devices):
    """
    Asigna dispositivos a una ubicación In House
    
    Parámetros:
    - device_names: Lista de nombres de dispositivos a asignar
    - location_id: ID de la ubicación In House
    - location_name: Nombre de la ubicación
    - start_date: Fecha de inicio
    - available_devices: Lista con todos los dispositivos disponibles
    
    Retorna:
    - True si la asignación fue exitosa, False si hubo error
    """
    with st.spinner("Asignando dispositivos..."):
        # Actualizar cada dispositivo
        success_count = 0
        for device_name in device_names:
            # Buscar el device_id por nombre
            device = next((d for d in available_devices if d["Name"] == device_name), None)
            
            if device:
                if update_device_location(device["id"], location_id):
                    success_count += 1
        
        if success_count == len(device_names):
            st.success(f"✅ {success_count} dispositivos asignados correctamente a '{location_name}'")
            return True
        else:
            st.warning(f"⚠️ Solo se asignaron {success_count} de {len(device_names)} dispositivos")
            return False


# ============================================
# INTERFAZ PRINCIPAL
# ============================================

# Inicializar session_state
if 'selected_devices' not in st.session_state:
    st.session_state.selected_devices = []

if 'search_completed' not in st.session_state:
    st.session_state.search_completed = False

if 'available_devices' not in st.session_state:
    st.session_state.available_devices = []

# 🆕 NUEVO: Inicializar filtro de tipo de dispositivo
if 'selected_type_filter' not in st.session_state:
    st.session_state.selected_type_filter = "Todos"

# Selector de fechas
st.subheader("📅 Selecciona el rango de fechas")

col1, col2 = st.columns(2)

with col1:
    start_date = st.date_input(
        "Fecha de inicio",
        value=date.today(),
        format="DD/MM/YYYY",
        key="start_date_input"
    )

with col2:
    end_date = st.date_input(
        "Fecha de fin",
        value=date.today(),
        format="DD/MM/YYYY",
        key="end_date_input"
    )

# Validar que la fecha de fin sea posterior a la de inicio
if start_date > end_date:
    st.error("⚠️ La fecha de fin debe ser posterior a la fecha de inicio")
    st.stop()

st.markdown("---")

# Botón para consultar disponibilidad
if st.button("🔍 Consultar Disponibilidad", type="primary", use_container_width=True):
    with st.spinner("Consultando dispositivos..."):
        # Obtener todos los dispositivos
        pages = get_pages(DEVICES_ID)
        
        all_devices = []
        for page in pages:
            device_data = extract_device_data(page)
            all_devices.append(device_data)
        
        # Filtrar dispositivos disponibles
        available_devices = [
            device for device in all_devices 
            if check_availability(device, start_date, end_date)
        ]
        
        # 🆕 ORDENAR ALFABÉTICAMENTE por nombre (de A a Z)
        # La función sorted() ordena la lista
        # key=lambda x: x['Name'].lower() significa: ordena por el campo 'Name' en minúsculas
        # Usamos .lower() para que "iPad" e "iphone" se ordenen correctamente
        available_devices_sorted = sorted(available_devices, key=lambda x: x['Name'].lower())
        
        # Guardar en session_state
        st.session_state.available_devices = available_devices_sorted
        st.session_state.search_completed = True
        st.session_state.query_start_date = start_date
        st.session_state.query_end_date = end_date
        st.session_state.selected_devices = []
        # 🆕 Resetear el filtro a "Todos" al hacer una nueva búsqueda
        st.session_state.selected_type_filter = "Todos"

st.markdown("---")

# Mostrar resultados si la búsqueda se ha completado
if st.session_state.search_completed:
    available_devices = st.session_state.available_devices
    
    if available_devices:
        # 🆕 NUEVO: SWITCH PARA FILTRAR POR TIPO DE DISPOSITIVO
        st.subheader("🔘 Filtrar por tipo de dispositivo")
        
        # Extraer todos los tipos (Tags) únicos que existen
        # set() elimina duplicados, sorted() los ordena alfabéticamente
        all_types = sorted(list(set([d['Tags'] for d in available_devices])))
        
        # Crear botones tipo "pills" en columnas
        # +1 para incluir el botón "Todos"
        cols = st.columns(len(all_types) + 1)
        
        # Botón "Todos"
        with cols[0]:
            # Si "Todos" está seleccionado, el botón será azul (primary)
            button_type = "primary" if st.session_state.selected_type_filter == "Todos" else "secondary"
            if st.button("🔵 Todos", use_container_width=True, type=button_type):
                st.session_state.selected_type_filter = "Todos"
                st.rerun()  # Recargar para aplicar el filtro
        
        # Botón para cada tipo
        for idx, device_type in enumerate(all_types):
            with cols[idx + 1]:
                # Si este tipo está seleccionado, el botón será azul (primary)
                button_type = "primary" if st.session_state.selected_type_filter == device_type else "secondary"
                if st.button(f"📱 {device_type}", use_container_width=True, type=button_type, key=f"type_{device_type}"):
                    st.session_state.selected_type_filter = device_type
                    st.rerun()  # Recargar para aplicar el filtro
        
        st.markdown("---")
        
        # 🆕 Aplicar el filtro de tipo si no es "Todos"
        filtered_devices = available_devices
        if st.session_state.selected_type_filter != "Todos":
            filtered_devices = [
                d for d in available_devices 
                if d['Tags'] == st.session_state.selected_type_filter
            ]
        
        # Mostrar información del resultado
        query_start = st.session_state.query_start_date
        query_end = st.session_state.query_end_date
        
        st.success(
            f"✅ **{len(filtered_devices)} dispositivos disponibles** "
            f"del {query_start.strftime('%d/%m/%Y')} al {query_end.strftime('%d/%m/%Y')}"
        )
        
        # 🆕 Mostrar información del filtro activo si no es "Todos"
        if st.session_state.selected_type_filter != "Todos":
            st.info(f"🔍 Mostrando solo: **{st.session_state.selected_type_filter}** ({len(filtered_devices)} de {len(available_devices)} dispositivos)")
        
        st.markdown("---")
        
        # Mostrar lista de dispositivos
        st.subheader("📋 Dispositivos disponibles")
        
        # Mostrar cada dispositivo con un checkbox
        for device in filtered_devices:
            device_name = device["Name"]
            device_type = device["Tags"]
            
            # Verificar si este dispositivo está seleccionado
            is_checked = device_name in st.session_state.selected_devices
            
            # Crear layout: checkbox + nombre en cajetín
            inner_col1, inner_col2 = st.columns([0.5, 9.5])
            
            with inner_col1:
                # Checkbox
                checkbox_value = st.checkbox(
                    "",
                    value=is_checked,
                    key=f"checkbox_{device_name}",
                    label_visibility="collapsed"
                )
                
                # Actualizar lista de seleccionados
                if checkbox_value and device_name not in st.session_state.selected_devices:
                    st.session_state.selected_devices.append(device_name)
                elif not checkbox_value and device_name in st.session_state.selected_devices:
                    st.session_state.selected_devices.remove(device_name)
            
            with inner_col2:
                # Nombre en cajetín con el tipo de dispositivo
                st.markdown(
                    f"""
                    <div style='padding: 8px 12px; 
                                background-color: {"#B3E5E6" if checkbox_value else "#e0e0e0"}; 
                                border-radius: 6px; 
                                margin-top: -8px;
                                border-left: 4px solid {"#00859B" if checkbox_value else "#9e9e9e"};'>
                        <p style='margin: 0; font-size: 16px; font-weight: 500; color: #333;'>
                            {device_name} <span style='color: #666; font-size: 14px;'>({device_type})</span>
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
                st.write("**📋 Nuevo Destino Cliente**")
                
                client_name = st.text_input(
                    "Nombre del Destino",
                    placeholder="Ej: Destino Barcelona 2025",
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