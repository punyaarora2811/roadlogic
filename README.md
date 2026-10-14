# 🚦 RoadLogic — Autonomous C-V2X Traffic Simulator with AI Decision Arbiter

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![Pygame-CE](https://img.shields.io/badge/Pygame--CE-2.5.6-green.svg)](https://pyga.me/)
[![AI-Arbiter](https://img.shields.io/badge/LLM-Decision%20Arbiter-purple.svg)]()
[![Security](https://img.shields.io/badge/Security-SHA--256%20Signed-orange.svg)]()
[![Tests](https://img.shields.io/badge/Tests-28%20Passed-brightgreen.svg)]()

A state-of-the-art autonomous traffic simulation platform demonstrating the power of **C-V2X (Cellular Vehicle-to-Everything)** networks paired with an **LLM-Powered Decision Arbiter**. The architecture combines deterministic, microsecond-level safety reflexes (ACC, GLOSA, emergency corridors, cryptographic validation) with context-aware LLM negotiation at unsignalized intersections.

---

## ✨ Core Deliverables & Features

### 1. 📡 C-V2X Communication Bus
Thread-safe message broker enabling vehicles and roadside infrastructure units to broadcast real-time telemetry, location, speed, heading, and intent packets with strict memory isolation.

### 2. 🏎️ Vehicle Kinematics & ACC
- **Adaptive Cruise Control (ACC)**: Dynamic following-distance control and throttle pacing to prevent rear-end collisions and chain-reaction braking.
- **Emergency Corridor Yielding**: Non-emergency vehicles autonomously detect approaching emergency vehicles via V2X and pull over to open an unobstructed green corridor.
- **Driving Personalities**: Differentiated agent driving styles (`Cautious` vs `Aggressive`).

### 3. 🧠 AI Decision Arbiter (LLM Negotiation)
- **Hierarchy 3B Conflict Arbiter**: Resolves contested right-of-way scenarios at unsignalized intersections through an LLM layer (`openai/gpt-oss-20b` via Groq) with structured prompts (`BRAKE` vs `PASS`).
- **AI Traffic Director**: Dynamic spawner analyzing live city traffic density to route vehicles onto uncongested corridors.
- **Thread-Safe Rate Limiter & Fallback**: Paced via `GroqRateLimiter` (`min_interval=1.5s`) to remain under TPM limits, falling back seamlessly to deterministic right-of-way rules when rate-limited.

### 4. 🐾 Hazard & Obstacle Handling
- **Wildlife Crossing Obstacle**: Dynamic animal detection simulating unexpected roadside hazards (wild deer crossing) via autonomous background timers or on-demand UI triggers.
- **Collective Safety Braking**: Vehicles immediately execute emergency stops upon detecting roadway obstacles, notifying adjacent traffic.

### 5. 🚥 Smart Infrastructure & GLOSA
- **Green Light Optimal Speed Advisory (GLOSA)**: Traffic lights continuously broadcast phase timings and countdown timers (`time_to_change`). Approaching vehicles adapt cruising speed in advance to clear intersections on green.
- **Emergency Signal Preemption**: Traffic lights detect approaching ambulances and preemptively force green corridors along their travel heading.
- **Failsafe Yellow Caution Mode**: When infrastructure is deactivated, signals fall back to amber warning flashers.

### 6. 🛡️ Security & Message Validation
- **Authenticity**: Keyed SHA-256 digital signature generation and verification on all V2X packets.
- **Schema Validation**: Mandatory telemetry schema enforcement rejecting malformed payloads.
- **Anti-Ghosting & Replay Protection**: Strict timestamp freshness checking (`MAX_MESSAGE_AGE = 2.0s`) preventing replay and ghost-vehicle exploits.

---

## 🛠️ Architecture & Modules

| Module | Description |
| :--- | :--- |
| [`main.py`](file:///c:/Code/PJT-1/main.py) | Simulation coordinator, main physics step loop, collision detection, and autonomous vehicle spawner. |
| [`vehicle_agent.py`](file:///c:/Code/PJT-1/vehicle_agent.py) | Multi-hierarchy vehicle state machine controlling ACC following, GLOSA speed adaptation, emergency yielding, and LLM intersection negotiation. |
| [`simulation_ui.py`](file:///c:/Code/PJT-1/simulation_ui.py) | Pygame-CE frontend featuring anti-aliased dark-mode rendering, vehicle trails, interactive HUD, and live network graph overlays. |
| [`groq_rate_limiter.py`](file:///c:/Code/PJT-1/groq_rate_limiter.py) | Thread-safe centralized rate limiter and token guardian preventing API 429 TPM exhaustion. |
| [`traffic_light.py`](file:///c:/Code/PJT-1/traffic_light.py) | Roadside Unit (RSU) agent broadcasting V2I phase states, GLOSA countdowns, and ambulance preemption. |
| [`v2x_network.py`](file:///c:/Code/PJT-1/v2x_network.py) | Thread-safe in-memory V2X message broker for pub/sub telemetry distribution. |
| [`v2x_security.py`](file:///c:/Code/PJT-1/v2x_security.py) | Cryptographic security manager enforcing digital signatures, schema validity, and freshness. |
| [`animal_obstacle.py`](file:///c:/Code/PJT-1/animal_obstacle.py) | Autonomous and on-demand wildlife road hazard triggering emergency collision avoidance. |
| [`navigation_system.py`](file:///c:/Code/PJT-1/navigation_system.py) | Shortest-path routing engine powered by NetworkX. |
| [`map_config.py`](file:///c:/Code/PJT-1/map_config.py) | Road network topology, intersection coordinates, spawn/exit nodes, and directed edges. |
| [`test_simulator.py`](file:///c:/Code/PJT-1/test_simulator.py) | Unit test suite covering security validation, ACC, ambulance priority, and RSU traffic lights (12 tests). |
| [`test_ai_vs_baseline.py`](file:///c:/Code/PJT-1/test_ai_vs_baseline.py) | Benchmark test suite comparing AI ON vs AI OFF across 8 scenarios, generating automated reports (16 tests). |

---

## ⚙️ Installation & Running

### 1. Clone the repository
```bash
git clone https://github.com/punyaarora2811/roadlogic.git
cd roadlogic
```

### 2. Set up virtual environment & dependencies
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Configure Environment Variables
Create or verify your `.env` file in the project root:
```env
GROQ_API_KEY=your_groq_api_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

### 4. Launch the Simulator
```bash
python main.py
```

---

## 🎮 Interactive UI Controls

| Control | Action |
| :--- | :--- |
| **`SYSTEM: ON / OFF`** | Toggles smart city infrastructure (GLOSA traffic lights vs blinking yellow caution). |
| **`AI: ON / OFF`** | Toggles LLM intersection negotiation layer (AI ON vs pure rule-based baseline). |
| **`AUTO-SPAWN: ON / OFF`** | Toggles continuous background traffic spawner (maintains 4–8 active vehicles). |
| **`SPAWN DEER`** | Manually triggers an autonomous wildlife crossing hazard on the roadway. |
| **`SPAWN AI CAR`** | Invokes the AI Traffic Director to analyze free corridors and spawn an intelligent vehicle. |
| **`SPAWN AMBULANCE`** | Spawns a high-priority emergency vehicle to demonstrate V2X green corridor yielding. |
| **`ESC`** | Gracefully exits the simulation. |

---

## 🧪 Automated Testing & AI Benchmarking

The project includes two automated test suites (**28 tests total**, all passing):

### 1. Functional & Security Unit Tests (12 Tests)
Validates cybersecurity keyed-SHA-256 signatures, anti-replay freshness, ACC car following, ambulance pull-over, and RSU traffic light compliance:
```bash
pytest test_simulator.py -v
```

### 2. AI-ON vs AI-OFF Benchmark Suite (16 Tests)
Executes 8 controlled multi-vehicle scenarios under both AI-ON and AI-OFF conditions, measuring crash reduction, deadlocks, and average speed:
```bash
pytest test_ai_vs_baseline.py -v
```

### 3. Run All Tests
```bash
pytest -v
```

### Key Benchmark Findings

| Metric | AI OFF (Baseline) | AI ON (LLM Arbiter) | Improvement |
| :--- | :---: | :---: | :---: |
| **Total Crashes (Congested Scenarios)** | **1** | **0** | **-100% collisions** (Zero crashes) |
| **Total Deadlocks** | **6** | **5** | **-16.7% deadlocks** |
| **Mean Average Speed** | **52.56 px/s** | **53.96 px/s** | **+1.40 px/s** (+2.7% flow) |
| **Safety Reflex Preservation** | 100% | 100% | 0 regressions in V2X / ACC / Animal stops |

---

## 📄 License

This project is licensed under the MIT License — see the LICENSE file for details.
