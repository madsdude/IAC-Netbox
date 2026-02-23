#!/usr/bin/env python3
import requests
import time
import os
import sys
import urllib3
import re
import json
import subprocess
import socket
import ipaddress
import concurrent.futures

# Sluk for advarsler om SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ==========================================
# --- KONFIGURATION ---
# ==========================================
SEMAPHORE_URL = "http://10.36.0.104:3000/api"
SEMAPHORE_TOKEN = "TOKEN" 
PROJECT_ID = 3
CACHE_FILE = "sites_cache.json"

# ==========================================
# --- FARVER & VÆRKTØJER ---
# ==========================================
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
BLUE = '\033[94m'
RESET = '\033[0m'
BOLD = '\033[1m'
GREY = '\033[90m'

headers_sem = {"Authorization": f"Bearer {SEMAPHORE_TOKEN}", "Content-Type": "application/json"}

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def remove_ansi_codes(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

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

# ==========================================
# --- CACHE & SITES ---
# ==========================================
def load_cached_sites():
    """Læser vores lynhurtige lokale site-database"""
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"\n{RED}[!] Filen '{CACHE_FILE}' mangler! Kør opdatering fra hovedmenuen først.{RESET}\n")
        return {}
    except Exception as e:
        print(f"\n{RED}[!] Fejl ved læsning af cache: {e}{RESET}\n")
        return {}

def choose_site_scope():
    clear_screen()
    print(f"{BOLD}{CYAN}=== VÆLG SITE (SCOPE) ==={RESET}")
    print("1) Kør på HELE Netværket (Global)")
    print("2) Vælg et specifikt Site")
    print("-" * 30)
    
    choice = input(f"{YELLOW}Valg > {RESET}")
    if choice == "1":
        return "all"
    elif choice == "2":
        sites = load_cached_sites()
        if not sites:
            time.sleep(2)
            return "all"
            
        print(f"\n{BOLD}Tilgængelige Sites:{RESET}")
        site_map = {}
        idx = 1
        
        for short_name, data in sorted(sites.items()):
            full_name = data.get('full_name', 'Ukendt')
            site_id = data.get('site_id', 'N/A')
            slug = data.get('slug')
            
            print(f"{idx:2}) {BOLD}[{short_name}]{RESET} {full_name} {GREY}(SiteID: {site_id}){RESET}")
            site_map[str(idx)] = slug
            idx += 1
            
        site_choice = input(f"\n{YELLOW}Vælg Site ID > {RESET}")
        
        if site_choice in site_map:
            selected_slug = site_map[site_choice]
            print(f"{GREEN}Valgt: {selected_slug}{RESET}")
            time.sleep(1)
            return f"site_{selected_slug}"
        else:
            print(f"{RED}Ugyldigt valg. Afbryder.{RESET}")
            time.sleep(1)
            return None
            
    return None

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
    print("Forbinder til systemer...")
    while True:
        # Hent opgaver dynamisk fra Semaphore
        sem_tasks = get_semaphore_tasks()
        
        clear_screen()
        print(f"{BOLD}{CYAN}==========================================")
        print("   NETWORK CONTROL CENTER (v2.2)")
        print(f"=========================================={RESET}")
        
        # 1) Statisk opgave til det lokale Python script
        print(f"{BOLD} 1){RESET} {GREEN}🔄 Opdater Site Database{RESET} {GREY}(Lokal cache){RESET}")
        print("-" * 42)
        
        sem_map = {}
        if sem_tasks:
            # Vi starter index fra 2
            for index, task in enumerate(sem_tasks, start=2):
                task_name_lower = task['name'].lower()
                prefix = "🛡️  " if "fortigate" in task_name_lower else "🔌 "
                print(f"{BOLD} {index}){RESET} {prefix}{task['name']}")
                sem_map[str(index)] = task

        print("-" * 42)
        print(" 0)  Afslut")
        print("-" * 42)
        
        choice = input(f"{BOLD}Vælg handling > {RESET}")
        
        if choice == "0":
            sys.exit()
            
        elif choice == "1":
            clear_screen()
            print(f"{BOLD}{CYAN}=== 🔄 OPDATERER SITES ==={RESET}\n")
            subprocess.run(["python3", "update_sites.py"])
            input(f"\n{BOLD}[Tryk ENTER for at returnere]{RESET}")
            
        elif choice in sem_map:
            task_name = sem_map[choice]['name']
            task_id = sem_map[choice]['id']
            
            # --- FORTIGATE ---
            if "fortigate" in task_name.lower():
                clear_screen()
                print(f"{BOLD}{CYAN}=== 🛡️ ONBOARD FORTIGATE ==={RESET}\n")
                fw_ip = input(f"{YELLOW}Indtast FortiGate Management IP (f.eks. 10.0.50.68) > {RESET}")
                
                if fw_ip.strip():
                    start_task(task_id, target_scope="all", extra_vars={"target_ips": fw_ip.strip()})
                else:
                    print(f"{RED}Ingen IP indtastet. Afbryder.{RESET}")
                input(f"\n{BOLD}[Tryk ENTER for at returnere]{RESET}")
                
            # --- SWITCHES / ANDRE ---
            else:
                scope = choose_site_scope()
                if not scope:
                    continue
                    
                selected_slug = scope.replace("site_", "")
                
                # Slå sitet op i cachen for at finde SiteID
                sites = load_cached_sites()
                site_id = "0"
                for data in sites.values():
                    if data.get('slug') == selected_slug:
                        site_id = str(data.get('site_id', '0'))
                        break
                
                # Den Smarte Matematik (Forslag til subnet)
                if len(site_id) == 4:
                    oktet1 = site_id[0:2]
                    oktet2 = site_id[2:4]
                    gættet_subnet = f"{oktet1}.{oktet2}.20.0/24"
                else:
                    gættet_subnet = "10.X.20.0/24"
                    
                clear_screen()
                print(f"{BOLD}{CYAN}=== 🔌 SCANNER SWITCHES PÅ SITE ==={RESET}\n")
                print(f"SiteID fundet: {site_id}")
                
                print(f"Tryk ENTER for at scanne vores gæt, eller skriv et andet subnet.")
                bruger_subnet = input(f"{YELLOW}Subnet [{gættet_subnet}] > {RESET}")
                
                target_subnet = bruger_subnet if bruger_subnet.strip() else gættet_subnet
                
                print(f"\n{BLUE}Scanner {target_subnet} for aktive switches (port 22)...{RESET}")
                
                try:
                    network = ipaddress.ip_network(target_subnet, strict=False)
                    active_ips = []
                    with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
                        results = executor.map(check_ssh_port, network.hosts())
                        for res in results:
                            if res:
                                active_ips.append(res)
                                print(f"{GREEN} [+] Fandt switch på: {res}{RESET}")
                    
                    if not active_ips:
                        print(f"\n{RED}Fandt ingen levende switches på {target_subnet}.{RESET}")
                        input(f"\n{BOLD}[Tryk ENTER for at returnere]{RESET}")
                        continue
                        
                    ip_string = ",".join(active_ips)
                    print(f"\n{BOLD}Fandt {len(active_ips)} switches. Sender til Semaphore...{RESET}")
                    start_task(task_id, scope, extra_vars={"target_ips": ip_string, "target_site": selected_slug})
                    
                except Exception as e:
                    print(f"{RED}Fejl i IP-format: {e}{RESET}")
                    
                input(f"\n{BOLD}[Tryk ENTER for at returnere]{RESET}")
                
        else:
            print(f"\n{RED}[!] Ugyldigt valg.{RESET}")
            time.sleep(1)

if __name__ == "__main__":
    try:
        main_menu()
    except KeyboardInterrupt:
        sys.exit()
