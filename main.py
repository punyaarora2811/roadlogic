import math
import threading
import time
import json
import random
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate

from traffic_light import TrafficLightAgent
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI
from animal_obstacle import AnimalObstacle
from groq_rate_limiter import rate_limiter

load_dotenv()


def run_simulation():
    broker = V2XBroker()
    ui = SimulationUI()

    traffic_light_agent = TrafficLightAgent(broker)
    traffic_light_agent.start()

    deer = AnimalObstacle(1350, 610)

    def trigger_animal():
        deer.trigger()

    broker.trigger_animal_event = trigger_animal

    # DYNAMIC AI SPAWN LOGIC (Traffic Director)
    model_name = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    llm_spawn = ChatGroq(
        temperature=0.8,
        model_name=model_name,
        max_tokens=150,
        reasoning_effort="low",
    )

    spawn_prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                """You are the 'AI Traffic Director' of a smart city. Your role is to add a new vehicle on a FREE street, ensuring DIVERSE and FLUID traffic.
    
    AVAILABLE VALID ROUTES (Choose STRICTLY one of the combinations below):
    - W_START (West) -> E_END, S2_END, or NW_END
    - E_START (East) -> W_END, S1_END, or NW_END
    - S1_START (South 1) -> NW_END or E_END
    - S2_START (South 2) -> W_END or NW_END
    - NW_START (North-West) -> S1_END, E_END, or S2_END
    - NE_ONEWAY_START (North-East) -> S2_END, W_END, or S1_END

    STRICT RULES:
    1. NO U-TURN! Never send a car to the same exit it started from (e.g., W_START -> W_END forbidden). Choose ONLY from the routes above.
    2. BE UNPREDICTABLE: Choose different starting points compared to existing cars. Spread traffic across the map!
    3. Choose a realistic speed between 55.0 and 75.0.
    4. Choose type: 'Normal' (90% of cases) or 'Ambulance' (10%).
    5. If a route is too crowded, avoid it and choose a free one.
    
    ANSWER STRICTLY WITH A VALID JSON, no other text, exactly in this format:
    {{"start_node": "...", "target_node": "...", "speed": 65.5, "v_type": "Normal"}}
    """,
            ),
            (
                "human",
                "Current traffic on map:\n{traffic_info}\n(Diversity dice: {rand_val})\nPlease analyze and send a new vehicle on a logical and free route!",
            ),
        ]
    )

    spawn_chain = spawn_prompt | llm_spawn

    car_counter = 0

    def ai_spawn_car():
        def task():
            nonlocal car_counter
            print("[Traffic Director] Scanning streets and calculating optimal route...")

            active_cars = []
            for a_id, a in list(agents.items()):
                if hasattr(a, "position_x") and hasattr(a, "position_y"):
                    active_cars.append(
                        f"{a_id} at (X:{a.position_x:.0f}, Y:{a.position_y:.0f}) heading towards {a.heading}"
                    )

            traffic_info = "\n".join(active_cars)
            if not traffic_info:
                traffic_info = "No cars on the map. The city is completely empty."

            def apply_fallback():
                nonlocal car_counter
                fallback_routes = [
                    ("W_START", "E_END"),
                    ("NW_START", "S1_END"),
                    ("S2_START", "W_END"),
                    ("E_START", "W_END"),
                    ("S1_START", "NW_END"),
                    ("NE_ONEWAY_START", "S2_END"),
                ]
                sn, tn = random.choice(fallback_routes)
                car_counter += 1
                fid = f"AI_Car_{car_counter}_{random.randint(10, 99)}"
                agent_fallback = VehicleAgent(fid, sn, tn, 60.0)

                with broker.lock:
                    is_safe = True
                    for a in list(agents.values()):
                        if not getattr(a, "is_crashed", False):
                            distance = math.sqrt(
                                (a.position_x - agent_fallback.position_x) ** 2
                                + (a.position_y - agent_fallback.position_y) ** 2
                            )
                            if distance < 60.0:
                                is_safe = False
                                break
                    if is_safe:
                        agents[fid] = agent_fallback
                        print(f"[Traffic Director] Spawning {fid} at {sn} -> {tn}")

            rand_val = random.randint(1, 10000)

            # Check rate limiter to stay safely under Groq TPM limit
            if not rate_limiter.acquire(timeout=0.8):
                apply_fallback()
                return

            try:
                response = spawn_chain.invoke(
                    {"traffic_info": traffic_info, "rand_val": rand_val}
                )

                raw_content = response.content.strip()
                if "{" in raw_content and "}" in raw_content:
                    raw_content = raw_content[raw_content.find("{") : raw_content.rfind("}") + 1]
                data = json.loads(raw_content)

                start_n = data.get("start_node", "W_START")
                target_n = data.get("target_node", "E_END")
                speed = float(data.get("speed", 60.0))
                v_type = data.get("v_type", "Normal")

                car_counter += 1
                new_id = f"AI_Car_{car_counter}_{random.randint(10, 99)}"
                d_style = "Aggressive" if v_type == "Ambulance" else "Cautious"

                new_agent = VehicleAgent(
                    agent_id=new_id,
                    start_node=start_n,
                    target_node=target_n,
                    desired_speed=speed,
                    vehicle_type=v_type,
                    driving_style=d_style,
                )

                # --- Anti-overlap check at spawn ---
                with broker.lock:
                    is_safe = True
                    for a in list(agents.values()):
                        if not getattr(a, "is_crashed", False):
                            distance = math.sqrt(
                                (a.position_x - new_agent.position_x) ** 2
                                + (a.position_y - new_agent.position_y) ** 2
                            )
                            if distance < 60.0:
                                is_safe = False
                                break

                    if is_safe:
                        agents[new_id] = new_agent
                        print(
                            f"[Traffic Director] Created {new_id} ({v_type}) at {start_n} -> {target_n}"
                        )

            except Exception as e:
                if "429" in str(e):
                    rate_limiter.report_429(backoff_seconds=5.0)
                apply_fallback()

        threading.Thread(target=task, daemon=True).start()

    broker.trigger_spawn_car = ai_spawn_car

    def manual_spawn_ambulance():
        def task():
            nonlocal car_counter
            valid_routes = [
                ("W_START", "E_END"),
                ("NW_START", "S1_END"),
                ("S2_START", "W_END"),
                ("E_START", "W_END"),
                ("S1_START", "NW_END"),
                ("NE_ONEWAY_START", "S2_END"),
            ]
            sn, tn = random.choice(valid_routes)
            car_counter += 1
            new_id = f"Ambulance_VIP_{car_counter}_{random.randint(10, 99)}"
            amb_agent = VehicleAgent(
                new_id,
                sn,
                tn,
                75.0,
                vehicle_type="Ambulance",
                driving_style="Aggressive",
            )

            with broker.lock:
                is_safe = True
                for a in list(agents.values()):
                    if not getattr(a, "is_crashed", False):
                        distance = math.sqrt(
                            (a.position_x - amb_agent.position_x) ** 2
                            + (a.position_y - amb_agent.position_y) ** 2
                        )
                        if distance < 60.0:
                            is_safe = False
                            break
                if is_safe:
                    agents[new_id] = amb_agent
                    print(f"[Manual Spawn] Ambulance {new_id} spawned at {sn}!")
                else:
                    print(
                        f"[Manual Spawn] Location {sn} is blocked. Try again!"
                    )

        threading.Thread(target=task, daemon=True).start()

    broker.trigger_spawn_ambulance = manual_spawn_ambulance

    # AUTOMATED BACKGROUND SPAWNER (Lively Smart City Traffic)
    def auto_spawner_loop():
        """Autonomously maintain a steady, continuous stream of vehicles."""
        time.sleep(3.0)  # Initial warm-up for simulation startup
        while True:
            try:
                time.sleep(random.uniform(8.0, 12.0))
                if not getattr(broker, "auto_spawn_enabled", True):
                    continue
                if not getattr(broker, "infrastructure_active", True):
                    continue

                active_count = 0
                with broker.lock:
                    active_count = len([
                        a for a in agents.values()
                        if not getattr(a, "is_crashed", False)
                    ])

                # Keep traffic between 4 and 8 vehicles so roads stay active
                if active_count < 8:
                    if random.random() < 0.15:
                        manual_spawn_ambulance()
                    else:
                        ai_spawn_car()
            except Exception as e:
                print(f"[Auto-Spawner] Notice: {e}")

    threading.Thread(target=auto_spawner_loop, daemon=True).start()

    # PREDEFINED TEST SCENARIOS (Controlled Chaos)

    # ACC (Braking for car in front) ---
    leader_agent = VehicleAgent(
        agent_id="Leader_Car",
        start_node="W_START",
        target_node="E_END",
        desired_speed=44.0,  # Goes slow
    )

    follower_agent = VehicleAgent(
        agent_id="Follower_Car",
        start_node="W_START",
        target_node="E_END",
        desired_speed=85.0,  # Comes speeding from behind
        driving_style="Aggressive",
    )

    follower_agent.position_x -= 250
    follower_agent.base_x -= 250

    # Right-of-Way Priority
    agent_s1 = VehicleAgent(
        agent_id="South1_Car",
        start_node="S1_START",
        target_node="NW_END",
        desired_speed=55.0,
    )
    agent_s1.position_y += 80

    # Comes from Right to Left (EAST -> WEST).
    agent_east = VehicleAgent(
        agent_id="East_Car",
        start_node="E_START",
        target_node="W_END",
        desired_speed=65.0,
    )

    # Comes from bottom to top (SOUTH -> NORTH) at I2.
    agent_s2 = VehicleAgent(
        agent_id="South2_Car",
        start_node="S2_START",
        target_node="NW_END",
        desired_speed=60.0,
    )

    # Comes from top to bottom (NORTH -> SOUTH).
    agent_north = VehicleAgent(
        agent_id="North_Car",
        start_node="NW_START",
        target_node="S1_END",
        desired_speed=60.0,
    )

    # Ambulance on merge (Zipper Merge) to test V2X filter
    amb_agent = VehicleAgent(
        agent_id="Ambulance_VIP",
        start_node="NE_ONEWAY_START",
        target_node="S2_END",
        desired_speed=75.0,
        vehicle_type="Ambulance",
    )

    agents = {
        "Leader_Car": leader_agent,
        "Follower_Car": follower_agent,
        "South1_Car": agent_s1,
        "East_Car": agent_east,
        "South2_Car": agent_s2,
        "North_Car": agent_north,
        "Ambulance_VIP": amb_agent,
    }

    seen_on_screen = set()

    def is_outside_screen(agent):
        return (
            agent.position_x < -50
            or agent.position_x > 1550
            or agent.position_y < -50
            or agent.position_y > 850
        )

    def background_task():
        dt = 0.05

        intersections = [
            (380, 650),
            (1100, 650),
            (380, 320),
            (800, 435),
        ]

        while True:

            deer.update(dt)
            status_deer = deer.get_status()

            if status_deer is not None:
                broker.publish(deer.agent_id, status_deer)
            else:
                with broker.lock:
                    broker.vehicles_status.pop(deer.agent_id, None)

            # ACCIDENT DETECTION
            agent_ids = list(agents.keys())
            for i in range(len(agent_ids)):
                a1 = agents[agent_ids[i]]

                # Collision with DEER
                if status_deer is not None and not getattr(
                    a1, "is_crashed", False
                ):
                    animal_dist = math.sqrt(
                        (a1.position_x - deer.position_x) ** 2
                        + (a1.position_y - deer.position_y) ** 2
                    )

                    if animal_dist < 25 and not getattr(broker, "ai_enabled", True):
                        a1.is_crashed = True
                        deer.state = "CRASHED"  # NEW: Kill the deer too!
                        print(f" ACCIDENT: {a1.agent_id} hit the deer!")

                # Collision between cars
                for j in range(i + 1, len(agent_ids)):
                    a2 = agents[agent_ids[j]]

                    if getattr(a1, "is_crashed", False) and getattr(
                        a2, "is_crashed", False
                    ):
                        continue

                    dist = math.sqrt(
                        (a1.position_x - a2.position_x) ** 2
                        + (a1.position_y - a2.position_y) ** 2
                    )

                    if dist < 16 and not getattr(broker, "ai_enabled", True):
                        a1.is_crashed = True
                        a2.is_crashed = True
                        print(
                            f"FATAL ACCIDENT: {a1.agent_id} violently crashed into {a2.agent_id}!"
                        )

            for a_id, agent in list(agents.items()):

                agent.memory.clear()

                # 1. V2X
                traffic = broker.receive(a_id)
                for o_id, o_data in traffic.items():
                    agent.receive_v2x_message(o_data)

                # 2. Choose intersection BASED ON ROUTE
                target_int = (agent.position_x, agent.position_y)  # Fallback

                for idx in range(agent.current_node_index + 1, len(agent.route)):
                    n = agent.route[idx]
                    if "I1" in n:
                        target_int = (400, 650)
                        break
                    elif "I2" in n:
                        target_int = (1100, 650)
                        break
                    elif "I3" in n:
                        target_int = (400, 300)
                        break
                    elif "MERGE" in n or "I4" in n:
                        target_int = (770, 455)
                        break

                ai_is_on = getattr(broker, "ai_enabled", True)
                agent.decide_action(
                    target_int[0], target_int[1], ai_global_enabled=ai_is_on
                )

                agent.update_position(dt)

                if not is_outside_screen(agent):
                    seen_on_screen.add(a_id)

                if (
                    a_id in seen_on_screen
                    and is_outside_screen(agent)
                    and not getattr(agent, "is_crashed", False)
                ):
                    with broker.lock:
                        broker.vehicles_status.pop(a_id, None)
                    del agents[a_id]
                    seen_on_screen.discard(a_id)
                    continue

                broker.publish(a_id, agent.get_emergency_status())
            time.sleep(dt)

    threading.Thread(target=background_task, daemon=True).start()

    ui.start(broker)


if __name__ == "__main__":
    run_simulation()
