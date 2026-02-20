import os
import json
import pynetbox
import urllib3

# Sluk for SSL-advarsler, hvis I bruger selvsignerede certifikater internt
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 1. Hent opsætning fra miljøvariabler (så vi ikke hardkoder tokens)
NETBOX_URL = os.environ.get("NETBOX_URL")
NETBOX_TOKEN = os.environ.get("NETBOX_TOKEN")

def fetch_active_sites():
    """Forbinder til NetBox og henter en liste over alle aktive sites."""
    print(f"Forbinder til NetBox på {NETBOX_URL}...")
    
    # Opret forbindelse
    nb = pynetbox.api(NETBOX_URL, token=NETBOX_TOKEN)
    nb.http_session.verify = False # Ignorer SSL validering
    
    try:
        # Hent kun sites med status 'active'
        sites = nb.dcim.sites.filter(status="active")
        
        site_list = []
        for site in sites:
            site_list.append({
                "id": site.id,
                "name": site.name,
                "slug": site.slug
            })
            
        return site_list
    except Exception as e:
        print(f"Fejl ved hentning af sites: {e}")
        return []

def save_sites_to_log(sites, filename="site_list_log.json"):
    """Gemmer listen af sites i en JSON fil til brug for onboarding."""
    if not sites:
        print("Ingen sites fundet. Filen bliver ikke oprettet.")
        return
        
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(sites, f, indent=4)
        
    print(f"Succes! {len(sites)} sites er gemt i '{filename}'.")

if __name__ == "__main__":
    # Sikkerhedstjek: Er variablerne sat?
    if not NETBOX_URL or not NETBOX_TOKEN:
        print("FEJL: Mangler NETBOX_URL eller NETBOX_TOKEN i miljøvariablerne.")
    else:
        active_sites = fetch_active_sites()
        save_sites_to_log(active_sites)
