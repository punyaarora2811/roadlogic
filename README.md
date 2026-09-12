# 🚦 RoadLogic — Smart City C-V2X Simulator

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Pygame](https://img.shields.io/badge/Pygame-2.5.6-green.svg)](https://www.pygame.org/)
[![Deterministic](https://img.shields.io/badge/Core-Deterministic-blue.svg)]()
[![CI Tests](https://github.com/pterodactylstfw/V2X-Intersection-Safety-Agent/actions/workflows/tests.yml/badge.svg)](https://github.com/pterodactylstfw/V2X-Intersection-Safety-Agent/actions)

A state-of-the-art autonomous traffic simulator demonstrating the power of **RoadLogic V2X (Vehicle-to-Everything)** networks in a Smart City. The project uses a fully deterministic control hierarchy — traffic lights, Adaptive Cruise Control, and right-of-way rules — over a digitally-secured V2X network, with no LLM dependencies.

---

## ✨ Key Features

- 🧠 **Autonomous V2V Brain**: Vehicles communicate with each other using digitally signed, encrypted packets. They obey traffic lights, apply right-of-way rules at unsignalized intersections, and prevent collisions via Adaptive Cruise Control (ACC).
- 🛡️ **Test-Driven Safety (CI/CD)**: Complete automated test suite using `pytest` and `GitHub Actions` to validate V2X logic, cybersecurity, and emergency braking.
- 🚥 **Smart Infrastructure (V2I - GLOSA)**: Traffic lights broadcast the remaining time until color changes. Vehicles adjust their speed in advance to catch the "green wave," reducing carbon emissions and harsh braking.
-  **Emergency Corridor & Bypass**: Ambulances intelligently bypass traffic via the oncoming lane. Regular vehicles detect V2X emergency packets and autonomously pull over to the side of the road to yield.
- 📏 **Advanced ACC (Adaptive Cruise Control)**: Vehicles maintain realistic following distances, dynamically adapting their braking force depending on their driving style to prevent the "yo-yo" traffic effect.
- 🦌 **Wildlife Detection**: The system reacts instantly to unpredictable physical obstacles (e.g., deer on the road), executing emergency braking to stop vehicles safely.
- 📊 **C-V2X Command Center (Live HUD)**: A transparent dashboard displaying real-time telemetry: active vehicle count, average speed, packet rate (ping), and active braking interventions.
- 🎭 **Driving Styles**: Support for both "Cautious" and "Aggressive" drivers (e.g., Ambulances), featuring different reaction times and priority forcing.

---

## 🛠️ Architecture & Technologies

- **Graphical Interface**: Pygame (Glassmorphism UI, anti-aliased rendering).
- **Routing & Graphs**: Dijkstra's algorithm via the NetworkX library for map navigation.
- **Intersection Control**: Fully deterministic hierarchy — traffic light obedience (GLOSA), ambulance priority, right-of-way reflex, zipper merge, and ACC. No LLM dependencies.
- **V2X Security**: Data packets are hashed using SHA-256 to prevent spoofing, featuring strict anti-ghosting mechanisms (timestamp validation).
- **Automated Testing**: `pytest` for unit/integration tests and `GitHub Actions` for continuous integration workflows.

---

## ⚙️ Installation & Running
1. **Clone the repository:**
   ```bash
   git clone https://github.com/pterodactylstfw/V2X-Intersection-Safety-Agent.git
   cd RoadLogic
   ```

2. **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Or, on Windows: venv\Scripts\activate
    pip install -r requirements.txt
    ```
    (Main dependencies: pygame-ce, networkx, requests, python-dotenv)

3. **Start the Simulator:**
    ```bash
    python main.py
    ```


🎮 **UI Controls**
- SYSTEM ON/OFF: Shuts down the city infrastructure (traffic lights switch to flashing yellow).

- SPAWN DEER: Spawns a wild animal on the road to test the emergency braking systems.

- SPAWN CAR: Spawns a new vehicle on a random valid route.

- SPAWN AMBULANCE: Spawns a priority emergency vehicle that triggers green corridors.
