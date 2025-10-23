import requests
import json
import os


# Configuración de Notion
NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_VERSION = "2022-06-28"
DEVICES_ID = "28d58a35e41180dd8080d1953c15ac23"

headers = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION,
}

print("=" * 80)
print("DIAGNÓSTICO DE TAGS EN NOTION")
print("=" * 80)
print()

# Obtener páginas
url = f"https://api.notion.com/v1/databases/{DEVICES_ID}/query"
payload = {"page_size": 5}  # Solo los primeros 5 para ver

response = requests.post(url, json=payload, headers=headers)
data = response.json()

if response.status_code != 200:
    print(f"❌ ERROR: {response.status_code}")
    print(json.dumps(data, indent=2))
else:
    print(f"✅ Conexión exitosa. Se encontraron {len(data.get('results', []))} dispositivos")
    print()
    
    for i, page in enumerate(data.get("results", []), 1):
        props = page["properties"]
        
        print(f"{'=' * 80}")
        print(f"DISPOSITIVO {i}")
        print(f"{'=' * 80}")
        
        # Nombre
        try:
            if props.get("Name") and props["Name"]["title"]:
                name = props["Name"]["title"][0]["text"]["content"]
            else:
                name = "Sin nombre"
        except:
            name = "Error al leer nombre"
        
        print(f"📱 Nombre: {name}")
        print()
        
        # Ver TODOS los campos disponibles
        print("📋 CAMPOS DISPONIBLES EN NOTION:")
        for field_name in props.keys():
            print(f"   - {field_name}")
        print()
        
        # Intentar leer Tags de diferentes formas
        print("🔍 INTENTANDO LEER TAGS:")
        print()
        
        # Intento 1: Campo "Tags"
        if "Tags" in props:
            print("   ✅ Campo 'Tags' existe")
            print(f"   Tipo de campo: {props['Tags']['type']}")
            print(f"   Contenido completo:")
            print(json.dumps(props["Tags"], indent=6))
            
            # Intentar extraer según el tipo
            if props["Tags"]["type"] == "multi_select":
                if props["Tags"]["multi_select"]:
                    tags = [tag["name"] for tag in props["Tags"]["multi_select"]]
                    print(f"   ✅ Tags extraídos: {tags}")
                else:
                    print("   ⚠️  El campo Tags está vacío")
            else:
                print(f"   ⚠️  El campo Tags no es 'multi_select', es: {props['Tags']['type']}")
        else:
            print("   ❌ No existe un campo llamado 'Tags'")
            print()
            print("   🔍 Buscando campos similares que puedan ser tags...")
            
            # Buscar campos que puedan contener tags
            possible_tag_fields = []
            for field_name, field_data in props.items():
                if field_data.get("type") == "multi_select":
                    possible_tag_fields.append(field_name)
                    print(f"      - '{field_name}' (tipo: multi_select)")
                    if field_data.get("multi_select"):
                        values = [tag["name"] for tag in field_data["multi_select"]]
                        print(f"        Valores: {values}")
            
            if not possible_tag_fields:
                print("      ❌ No se encontraron campos de tipo 'multi_select'")
        
        print()

print()
print("=" * 80)
print("DIAGNÓSTICO COMPLETADO")
print("=" * 80)
print()
print("💡 SIGUIENTE PASO:")
print("   1. Revisa el nombre exacto del campo que contiene los tags en Notion")
print("   2. Verifica que el tipo de campo sea 'multi_select'")
print("   3. Asegúrate de que los dispositivos tengan tags asignados ('Ultra' y 'Neo 4')")