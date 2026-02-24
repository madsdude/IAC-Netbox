# Usage Guide - IAC-Netbox

This guide explains how to use the IAC-Netbox automation tools, specifically the `control.py` interactive dashboard.

## Prerequisites

Before using the tools, ensure you have:
- Python 3.x installed.
- Access to the NetBox instance.
- Access to the Semaphore instance.
- Valid API tokens for both NetBox and Semaphore (configured in `control.py`).

## Getting Started

1. Navigate to the project directory.
2. Run the control script:
   ```bash
   python control.py
   ```

## The Main Menu

The dashboard provides several options to manage your network:

1. **Ansible Playbooks**: Select from available Semaphore templates (e.g., Onboard Switch, Sync Cables).
2. **77) Brownfield Scanner**: Discover and onboard new devices.
3. **88) SSH Connect**: (Utility for quick SSH access).
4. **99) Admin Terminal**: Opens a shell for advanced maintenance.
5. **0) Logout**: Exit the dashboard.

## Core Operations

### 1. Onboarding FortiGate Firewalls
When selecting the FortiGate Onboarding task:
1. Enter the management IP of the FortiGate cluster.
2. The automation will:
   - Connect via REST API.
   - Gather HA status and hostnames.
   - Sync all interfaces, VLANs, and IP addresses to NetBox.
   - Create a Virtual Chassis (HA Cluster) in NetBox.

### 2. Brownfield Discovery (Scanner)
Use this tool to find devices that are not yet in NetBox:
1. Select a subnet prefix fetched directly from NetBox.
2. The script scans for active SSH (port 22) listeners.
3. Review the found IPs.
4. Send the IPs to Ansible for automatic onboarding.

### 3. Topology & VLAN Sync
Sync tasks ensure NetBox matches the real world:
- **Cables**: Uses CDP to map physical connections between devices.
- **VLANs**: Syncs VLAN definitions and assignments.

## Monitoring Tasks

When a task is triggered, `control.py` provides real-time feedback:
- `[OK]`: Task completed with no changes.
- `[ÆNDRET]`: NetBox was updated with new data.
- `[FEJL]`: Something went wrong (check the details provided).

> [!TIP]
> Use the **Scope** selection to run tasks on a specific site rather than the entire network to save time and reduce risk.
