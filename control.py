#!/usr/bin/env python3
import requests
import time
import os
import sys
import urllib3
import re
import json
import socket
import ipaddress
import concurrent.futures

# Sluk for advarsler
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# --- KONFIGURATION ---
# ==========================================

SEMAPHORE_URL = "http://10.36.0.104:3000/api"
SEMAPHORE_TOKEN = "TOKEN" 
PROJECT_ID = 3

NETBOX_URL = "https://10.36.1.80"           
NETBOX_TOKEN = "TOKEN"       
SSH_USER = "ansible"                        

# ==========================================

# Farver
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'
GREY = '\033[90m'

headers_sem = {"Authorization": f"Bearer {SEMAPHORE_TOKEN}", "Content-Type": "application/json"}
headers_nb = {"Authorization": f"Token {NETBOX_TOKEN}", "Content-Type": "application/json", "Accept": "application/json"}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def remove_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

# ==========================================
# --- NETBOX OPSLAG ---
# ==========================================

def get_netbox_sites():
    try:
        url = f"{NETBOX_URL}/api/dcim/sites/?status=active"
        response = requests.get(url, headers=headers_nb, timeout=5, verify=False)
        return response.json()['results'] if response.status_code == 200 else []
    except:
        return []

def get_netbox_prefixes():
    try:
        url = f"{NETBOX_URL}/api/ipam/prefixes/"
        response = requests.get(url, headers=headers_nb, timeout=5, verify=False)
        return response.json()['results'] if response.status_code == 200 else []
    except:
        return []

def choose_site_scope():
    clear_screen()
    print(f"{BOLD}{CYAN}=== VÆLG OMFANG (SCOPE) ==={RESET}")
    print("1) Kør på HELE Netværket (Global)")
    print("2) Vælg et specifikt Site")
    print("-" * 30)
    
    choice = input(f"{YELLOW}Valg > {RESET}")
    if choice == "1":
        return "all"
    elif choice == "2":
        sites = get_netbox_sites()
        if not sites:
            print(f"{RED}Ingen sites fundet i NetBox!{RESET}")
            time.sleep(2)
            return "all"
            
        print(f"\n{BOLD}Tilgængelige Sites:{RESET}")
        site_map = {}
        for idx, site in enumerate(sites, start=1):
            print(f"{idx}) {site['name']} ({site['slug']})")
            site_map[str(idx)] = site['slug']
            
        site_choice = input(f"\n{YELLOW}Vælg Site ID > {RESET}")
        
        if site_choice in site_map:
            selected_slug = site_map[site_choice]
            print(f"{GREEN}Valgt: {selected_slug}{RESET}")
            time.sleep(1)
            return f"site_{selected_slug}"
        else:
            print(f"{RED}Ugyldigt valg. Kører på alt.{RESET}")
            time.sleep(1)
            return "all"
            
    return "all"

# ==========================================
# --- BROWNFIELD SCANNER ---
# ==========================================

def check_ssh_port(ip):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        result = sock.connect_ex((str(ip), 22))
        sock.close()
        if result == 0:
            return str(ip)
    except:
        pass
    return None

def run_brownfield_discovery(sem_tasks):
    clear_screen()
    print(f"{BOLD}{CYAN}=== 🕵️‍♂️ BROWNFIELD DISCOVERY (SCANNER) ==={RESET}")
    prefixes = get_netbox_prefixes()
    
    if not prefixes:
        print(f"{RED}[!] Fandt ingen subnets i NetBox.{RESET}")
        input("\n[Tryk ENTER]")
        return

    print(f"Viser kun subnets med formatet {YELLOW}10.XX.20.XX{RESET}:\n")
    prefix_map = {}
    display_idx = 1
    
    for p in prefixes:
        octets = p['prefix'].split('.')
        if len(octets) >= 3 and octets[0] == "10" and octets[2] == "20":
            site_name = "Intet Site"
            site_slug = ""
       
            if p.get('site') and p['site'] is not None:
                site_name = p['site'].get('name', 'Intet Site')
                site_slug = p['site'].get('slug', '')
            elif p.get('scope') and p.get('scope_type') == 'dcim.site' and p['scope'] is not None:
                site_name = p['scope'].get('name', 'Intet Site')
                site_slug = p['scope'].get('slug', '')

            print(f"{display_idx:2}) {p['prefix']:18} (Site: {site_name})")
            p['extracted_site_slug'] = site_slug
            prefix_map[str(display_idx)] = p
            display_idx += 1

    if not prefix_map:
        print(f"{RED}Ingen subnets matcher filteret 10.XX.20.XX.{RESET}")
        input("\n[Tryk ENTER]")
        return

    choice = input(f"\n{YELLOW}Vælg ID > {RESET}")
    if choice not in prefix_map: return

    selected_prefix = prefix_map[choice]['prefix']
    target_site_slug = prefix_map[choice]['extracted_site_slug']
    
    if not target_site_slug:
        print(f"{RED}Fejl: Subnettet mangler at blive tildelt et Site i NetBox (Scope).{RESET}")
        input("\n[Tryk ENTER]")
        return

    print(f"\n{BLUE}Scanner {selected_prefix} på port 22 (SSH)...{RESET}")
    network = ipaddress.ip_network(selected_prefix, strict=False)
    active_ips = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
        results = executor.map(check_ssh_port, network.hosts())
        for res in results:
            if res:
                active_ips.append(res)
                print(f"{GREEN} [+] Fandt enhed med SSH åben på: {res}{RESET}")
    
    if not active_ips:
        print(f"\n{RED}Ingen aktive enheder fundet på subnet {selected_prefix}.{RESET}")
        input("\n[Tryk ENTER]")
        return
        
    print(f"\n{BOLD}Fandt {len(active_ips)} enheder!{RESET}")
    print("Vil du sende disse IP'er til Ansible for onboarding i NetBox?")
    ans = input(f"{YELLOW}(j/n) > {RESET}").lower()
    
    if ans == 'j':
        import_task_id = None
        for t in sem_tasks:
            if "Brownfield Onboarding" in t['name']:
                import_task_id = t['id']
                break
                
        if import_task_id:
            ip_string = ",".join(active_ips)
            print(f"\n{BLUE}Starter import proces...{RESET}")
            start_task(import_task_id, f"site_{target_site_slug}", extra_vars={"target_ips": ip_string, "target_site": target_site_slug})
        else:
            print(f"{RED}Kunne ikke finde en opgave i Semaphore der hedder 'Brownfield Onboarding'.{RESET}")
    
    input("\n[Tryk ENTER]")

# ==========================================
# --- SEMAPHORE MOTOR ---
# ==========================================

def get_semaphore_tasks():
    try:
        url = f"{SEMAPHORE_URL}/project/{PROJECT_ID}/templates"
        response = requests.get(url, headers=headers_sem, timeout=3)
        if response.status_code == 200:
            return sorted(response.json(), key=lambda x: x['id'])
        return []
    except:
        return []

def monitor_task(task_id):
    print(f"\n{BLUE}Starter kørsel...{RESET}\n")
    seen_lines = 0
    running = True
    noise_filter = ["Task added", "Started:", "Preparing:", "Updating Repository", "From https", "branch", "Already up to date", "commit hash", "cloning", "requirements.yml", "Skip galaxy", "falling back to paramiko", "Run TaskRunner", "PLAY RECAP", "gathering facts", "Get current commit", "Using module file", "skipping:"]
    
    while running:
        try:
            status_resp = requests.get(f"{SEMAPHORE_URL}/project/{PROJECT_ID}/tasks/{task_id}", headers=headers_sem, timeout=5)
            if status_resp.status_code != 200: break
            status = status_resp.json().get('status')

            log_resp = requests.get(f"{SEMAPHORE_URL}/project/{PROJECT_ID}/tasks/{task_id}/output", headers=headers_sem, timeout=5)
            if log_resp.status_code == 200:
                logs = log_resp.json()
                if len(logs) > seen_lines:
                    for line in logs[seen_lines:]:
                        clean_output = remove_ansi_codes(line.get('output', '')).strip()
                        if not clean_output or any(x in clean_output for x in noise_filter): continue

                        if "TASK [" in clean_output:
                            print(f"\n{BOLD}{CYAN}>>> {clean_output.split('[')[1].split(']')[0]}{RESET}")
                            continue

                        match = re.search(r'(ok|changed|failed): \[(.*?)\]', clean_output)
                        if match:
                            s, h = match.groups()
                            col, txt = (RED, "[FEJL]") if s == "failed" else (YELLOW, "[ÆNDRET]") if s == "changed" else (GREEN, "[OK]")
                            msg = ""
                            m2 = re.search(r'"msg": "(.*?)"', clean_output)
                            if m2: msg = f"- {m2.group(1)}"
                            print(f"   {col}{txt:<10} {h:<15}{RESET} {msg}")

                        elif '"msg":' in clean_output:
                            clean_msg = clean_output.replace('"msg":', '').replace('"', '').replace(',', '').strip()
                            if clean_msg != "All assertions passed":
                                print(f"      {GREY}Details: {clean_msg}{RESET}")
                        elif "fatal:" in clean_output or "error" in clean_output.lower():
                             print(f"   {RED}!!! KRITISK: {clean_output}{RESET}")

                    seen_lines = len(logs)

            if status in ['success', 'error', 'stop']:
                print("\n" + "-"*40)
                print(f"{GREEN}Kørsel fuldført.{RESET}" if status == 'success' else f"{RED}Kørsel fejlede.{RESET}")
                break
            time.sleep(1)
        except: break

def start_task(template_id, target_scope="all", extra_vars=None):
    print(f"\n{YELLOW}[System] Sender ordre til Semaphore...{RESET}")
    print(f"{GREY}Target Scope: {target_scope}{RESET}")
    
    try:
        url = f"{SEMAPHORE_URL}/project/{PROJECT_ID}/tasks"
        env_vars = {"target": target_scope}
        
        if extra_vars:
            env_vars.update(extra_vars)
            
        data = {"template_id": template_id, "environment": json.dumps(env_vars)}
        response = requests.post(url, json=data, headers=headers_sem, timeout=3)
        
        if response.status_code == 201:
            monitor_task(response.json().get('id'))
        else:
            print(f"{RED}[FEJL] Server kode: {response.status_code}\n{response.text}{RESET}")
            
    except Exception as e:
        print(f"{RED}[FEJL] {e}{RESET}")

# ==========================================
# --- HOVED MENU ---
# ==========================================

def main_menu():
    print("Forbinder...")
    while True:
        sem_tasks = get_semaphore_tasks()
        clear_screen()
        print(f"{BOLD}{CYAN}==========================================")
        print("   NETWORK CONTROL CENTER (MULTI-SITE)")
        print(f"=========================================={RESET}")
        
        sem_map = {}
        if sem_tasks:
            for index, task in enumerate(sem_tasks, start=1):
                # Gør FortiGate-opgaven lidt pænere i menuen med et skjold
                prefix = "🛡️  " if "FortiGate" in task['name'] else ""
                print(f"{BOLD}{index}){RESET} {prefix}{task['name']}")
                sem_map[str(index)] = task

        print("-" * 42)
        print(f"{BOLD}77){RESET} {GREEN}🕵️‍♂️ Onboard nye enheder (Brownfield Scanner){RESET}")
        print(f"{BOLD}88){RESET} {YELLOW}SSH Connect{RESET}")
        print(f"{BOLD}99){RESET} {YELLOW}Admin Terminal{RESET}")
        print("0)  Log ud")
        print("------------------------------------------")
        
        choice = input(f"{BOLD}Vælg handling > {RESET}")
        
        if choice == "0": sys.exit()
        elif choice == "99": os.system("SKIP_MENU=1 /bin/bash")
        elif choice == "88": pass
        elif choice == "77":
            run_brownfield_discovery(sem_tasks)
        elif choice in sem_map:
            task_name = sem_map[choice]['name']
            task_id = sem_map[choice]['id']
            
            # --- MAGIEN TIL FORTIGATE ER HER! ---
            if "FortiGate" in task_name or "fortigate" in task_name.lower():
                clear_screen()
                print(f"{BOLD}{CYAN}=== 🛡️ ONBOARD FORTIGATE ==={RESET}")
                fw_ip = input(f"{YELLOW}Indtast FortiGate Management IP (f.eks. 10.0.50.68) > {RESET}")
                
                if fw_ip.strip():
                    # Vi sender bare "all" som scope, for scriptet regner det selv ud!
                    start_task(task_id, target_scope="all", extra_vars={"target_ips": fw_ip.strip()})
                else:
                    print(f"{RED}Ingen IP indtastet. Afbryder.{RESET}")
            else:
                # Standard kørsel for alle andre opgaver (Cisco switches osv.)
                scope = choose_site_scope()
                start_task(task_id, scope)
                
            input(f"\n{BOLD}[Tryk ENTER for at fortsætte]{RESET}")

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        sys.exit()
