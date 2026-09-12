# 🚦 RoadLogic — Autonomous C-V2X Traffic Simulator

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/Pygame--CE-2.5.6-green.svg)](https://pyga.me/)
[![Core](https://img.shields.io/badge/Core-Deterministic-blue.svg)]()
[![Tests](https://img.shields.io/badge/Tests-11%20Passed-brightgreen.svg)]()

A state-of-the-art autonomous traffic simulator demonstrating the power of **C-V2X (Cellular Vehicle-to-Everything)** networks in a modern smart city. The system operates on a **pure deterministic core** — utilizing V2I traffic light coordination, V2V emergency vehicle priority corridors, Adaptive Cruise Control (ACC), and cryptographically validated message exchange with zero external LLM or cloud API dependencies.

---

## ✨ Key Features

- 🧠 **Deterministic V2V & V2I Architecture**: Vehicles navigate autonomously by exchanging digitally signed V2X packets. They obey signal phases, perform GLOSA speed adjustments, yield to emergency vehicles, and maintain safe following distances.
- 🚗 **Dynamic Autonomous Auto-Spawner**: Spawns cars and priority ambulances automatically in a background daemon thread. The spawn probability scales dynamically based on real-time traffic density:
  - **At 0 cars**: Maximum spawn probability (100%) with minimal delay (~0.8s) to rapidly populate roads.
  - **1 to 9 cars**: Probability scales down linearly ($90\% \to 80\% \dots \to 10\%$) with gradually spaced intervals.
  - **At 10 cars**: Spawning halts completely until vehicles exit the road network.
- 🚑 **Emergency Corridor & Yielding**: Ambulances broadcast high-priority emergency packets. Oncoming and preceding vehicles detect the priority transmission via V2X and autonomously pull over or yield the right of way.
- 🚥 **Smart Infrastructure (V2I - GLOSA)**: Traffic lights broadcast phase states and time-to-change. Approaching vehicles adjust cruise speed in advance to hit the green light window, minimizing stop-and-go energy loss. When the city system is turned OFF, signals fall back to amber warning flashers.
- 📏 **Adaptive Cruise Control (ACC)**: Front-distance-based following logic dynamically regulates throttle and braking against vehicles ahead on the route to prevent chain-reaction decelerations.
- 🦌 **Autonomous Wildlife Crossing**: A background timer autonomously triggers wildlife (deer) road crossing events on random intervals (every 20–40 seconds), challenging vehicle emergency braking and collision avoidance reflex systems.
- 🗺️ **Integrated Navigation Graph Overlay**: Permanent real-time visual overlay of the underlying navigation graph directly over the asphalt layer:
  - Directed edges rendered as crisp lines with travel-direction arrowheads.
  - Nodes rendered as distinct labeled coordinate points on frosted glass pill badges.
- 📊 **Glassmorphism C-V2X Command Center**: Real-time HUD telemetry dashboard displaying live vehicle count, network packets per second (ping rate), average speed, and braking interventions.
- 🛡️ **Cryptographic V2X Security**: In-memory V2X broker with SHA-256 digital signature generation and verification, plus strict anti-ghosting replay protection (payload timestamp verification).

---

## 🛠️ Architecture & Modules

| Module | Description |
| :--- | :--- |
| [`main.py`](file:///c:/Code/PJT-1/main.py) | Simulation coordinator, physics step loop, collision detection, and dynamic vehicle auto-spawner thread. |
| [`simulation_ui.py`](file:///c:/Code/PJT-1/simulation_ui.py) | Pygame-CE frontend featuring anti-aliased dark-mode road rendering, vehicle heading rotation, soft trails, and navigation graph overlay. |
| [`vehicle_agent.py`](file:///c:/Code/PJT-1/vehicle_agent.py) | Vehicle state machine controlling ACC following, GLOSA braking/speed adaptation, and emergency vehicle yielding. |
| [`v2x_network.py`](file:///c:/Code/PJT-1/v2x_network.py) | Thread-safe in-memory V2X message broker for pub/sub communication between vehicles and roadside units. |
| [`v2x_security.py`](file:///c:/Code/PJT-1/v2x_security.py) | Security manager handling SHA-256 payload signing, signature validation, and replay packet rejection. |
| [`traffic_light.py`](file:///c:/Code/PJT-1/traffic_light.py) | Traffic light controller broadcasting V2I signal timing and phase states. |
| [`animal_obstacle.py`](file:///c:/Code/PJT-1/animal_obstacle.py) | Autonomous animal obstacle with scheduled state transitions (`HIDDEN` → `CROSSING` → `CROSSED`). |
| [`map_config.py`](file:///c:/Code/PJT-1/map_config.py) | Road network topology, intersection coordinates, spawn/exit nodes, and directed edge connections. |
| [`navigation_system.py`](file:///c:/Code/PJT-1/navigation_system.py) | Shortest-path routing engine powered by NetworkX. |

---

## ⚙️ Installation & Running

### 1. Clone the repository
```bash
git clone https://github.com/punyaarora2811/roadlogic.git
cd roadlogic
```

### 2. Create a virtual environment & install dependencies
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Launch the Simulator
```bash
python main.py
```

---

## 🎮 UI Controls

- **`SYSTEM: ON / OFF` (Top-Left Button)**:
  - **ON**: Standard smart city operation. Traffic signals cycle normally, vehicles utilize V2X routing, and the auto-spawner introduces traffic.
  - **OFF**: Infrastructure emergency mode. Traffic lights switch to blinking yellow caution mode and autonomous vehicle spawning pauses.
- **`ESC`**: Exit the simulation window.

---

## 🧪 Automated Testing

Run the automated test suite covering cybersecurity signature verification, anti-ghosting expiry, ambulance green corridor yielding, ACC braking, and animal obstacle detection:

```bash
pytest test_simulator.py -v
```

All 11 unit & integration tests run deterministically in `< 1.0s`.
