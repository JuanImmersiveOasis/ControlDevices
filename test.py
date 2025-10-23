import os
from dotenv import load_dotenv

load_dotenv()  # Solo si quieres recargar manualmente
print(os.getenv("NOTION_TOKEN"))
