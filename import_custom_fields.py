#!/usr/bin/env python3
import csv
import requests
import json
import urllib3

# Sluk for advarsler om manglende SSL-certifikater
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# --- KONFIGURATION ---
# ==========================================
NETBOX_URL = "https://10.36.1.80"           
NETBOX_TOKEN = "NETBOX TOKEN"       
CSV_FILE = "netbox_custom fields.csv"
# ==========================================

headers = {
    "Authorization": f"Token {NETBOX_TOKEN}",
    "Content-Type": "application/json",
    "Accept": "application/json"
}

# Mapping-ordbog der oversætter CSV 'Type' til NetBox API formater
TYPE_MAPPING = {
    "Text": "text",
    "Selection": "select",
    "Integer": "integer",
    "Boolean (true/false)": "boolean",
    "Date": "date"
}

def import_custom_fields():
    print(f"🔄 Starter import af Custom Fields fra {CSV_FILE}...")
    
    try:
        with open(CSV_FILE, mode='r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            
            for row in reader:
                name = row.get("Name", "").strip()
                if not name:
                    continue
                
                # Split object types ved komma og rens dem
                raw_objects = row.get("Object Types", "")
                object_types = [obj.strip() for obj in raw_objects.split(",") if obj.strip()]
                
                # Oversæt type
                raw_type = row.get("Type", "Text").strip()
                nb_type = TYPE_MAPPING.get(raw_type, "text") # Default til text, hvis vi ikke kender den
                
                # Boolean oversættelse for Required
                required = str(row.get("Required", "")).strip().lower() == "true"
                
                # Byg Payload
                payload = {
                    "name": name,
                    "type": nb_type,
                    "object_types": object_types,
                    "required": required
                }
                
                # Håndter valgfri felter
                label = row.get("Label", "").strip()
                if label: payload["label"] = label
                
                description = row.get("Description", "").strip()
                if description: payload["description"] = description
                
                group_name = row.get("Group name", "").strip()
                if group_name: payload["group_name"] = group_name

                # Send kald til NetBox API'et
                url = f"{NETBOX_URL}/api/extras/custom-fields/"
                response = requests.post(url, headers=headers, json=payload, verify=False)
                
                if response.status_code == 201:
                    print(f"✅ Oprettet: {name} ({nb_type}) til {object_types}")
                elif response.status_code == 400 and "already exists" in response.text.lower():
                    print(f"⚠️ Findes allerede: {name}. Springer over.")
                else:
                    print(f"❌ Fejl ved {name}: {response.status_code} - {response.text}")

    except FileNotFoundError:
        print(f"❌ Kunne ikke finde filen '{CSV_FILE}'. Sørg for at den ligger i samme mappe som scriptet.")
    except Exception as e:
        print(f"❌ En uventet fejl opstod: {e}")

if __name__ == "__main__":
    import_custom_fields()
    print("\n🎉 Import fuldført!")
