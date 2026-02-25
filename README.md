# IAC-Netbox: Network Automation with NetBox SoT

![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)
![Ansible](https://img.shields.io/badge/Ansible-2.10+-red.svg)
![NetBox](https://img.shields.io/badge/NetBox-3.0+-green.svg)

IAC-Netbox is a powerful automation framework designed to treat **NetBox** as the absolute Source of Truth for your network infrastructure. It combines Python scripting, Ansible playbooks, and Semaphore to provide a seamless onboarding and synchronization experience for Cisco and Fortinet environments.

## 🚀 Key Features

- **Interactive Dashboard**: A Python-based CLI (`control.py`) to manage all automation tasks.
- **Brownfield Discovery**: Automated scanning of network prefixes to find and onboard existing devices.
- **Multi-Vendor Support**: Specialized onboarding for Cisco IOS switches and FortiGate HA clusters.
- **Real-time Sync**: Automated cable (topology) and VLAN synchronization between the live network and NetBox.
- **Semaphore Integration**: Centralized task execution, logging, and secret management.

## 📁 Project Structure

```text
IAC-Netbox/
├── control.py              # Main CLI Dashboard
├── ARCHITECTURE.md         # Technical Deep Dive
├── USAGE.md                # User Guide
├── Inventory/
│   └── netbox_inv.yml      # Ansible Dynamic Inventory for NetBox
├── Sync/                   # Topology and Config Sync Playbooks
│   ├── sync_cables.yml     # CDP-based cable discovery
│   └── sync_switch_vlans.yml
├── onboard/                # Device Onboarding Playbooks
│   ├── onboard_devices.yml # Standard onboarding
│   ├── onboard_Switch.yml  # Cisco-specific logic
│   └── onboard_fortigate.yml# FortiGate HA logic
└── requirements.yml        # Ansible collections
```

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/madsdude/IAC-Netbox.git
   cd IAC-Netbox
   ```

2. **Install Dependencies**:
   ```bash
   pip install requests urllib3
   ansible-galaxy collection install -r requirements.yml
   ```

3. **Configure API Tokens**:
   Edit `control.py` and set your `NETBOX_TOKEN` and `SEMAPHORE_TOKEN`.

## 📖 Documentation

- [**Architecture**](file:///c:/Users/madsc/Code/IAC-Netbox/ARCHITECTURE.md): Understand how the system works.
- [**Usage Guide**](file:///c:/Users/madsc/Code/IAC-Netbox/USAGE.md): Learn how to run scans and onboarding.

## 🤝 Contributing
Feel free to open issues or submit pull requests for new features or bug fixes.
