import math
import threading
import time
import random

from traffic_light import TrafficLightAgent
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent
from simulation_ui import SimulationUI
from animal_obstacle import AnimalObstacle

def run_simulation():
    broker = V2XBroker()
    ui = SimulationUI()
    traffic_light_agent = TrafficLightAgent(broker)
    traffic_light_agent.start()
    deer = AnimalObstacle(1350, 610)
    # Auto-spawner constants
    MAX_CONCURRENT_VEHICLES = 10   # hard cap: stops spawning when reaching 10 cars
    VALID_ROUTES = [
        ("W_START",          "E_END"),
        ("W_START",          "NW_END"),
        ("NW_START",         "S1_END"),
        ("NW_START",         "E_END"),
        ("S2_START",         "W_END"),
        ("S2_START",         "NW_END"),
        ("E_START",          "W_END"),
        ("E_START",          "S1_END"),
        ("S1_START",         "NW_END"),
        ("S1_START",         "E_END"),
        ("NE_ONEWAY_START",  "S2_END"),
        ("NE_ONEWAY_START",  "W_END"),
    ]
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

    def auto_spawner():
        """Background thread: periodically spawns vehicles while SYSTEM is ON.
        Spawning probability is at MAX (100%) when at 0 cars, decreasing as
        the car count increases, and stops completely at 10 cars.
        """
        while True:
            # Respect SYSTEM ON/OFF
            if not broker.infrastructure_active:
                time.sleep(1.0)
                continue
            with broker.lock:
                live_count = len(agents)
            # At 10 cars, stop spawning completely
            if live_count >= MAX_CONCURRENT_VEHICLES:
                time.sleep(1.0)
                continue
            # Probability: 1.0 (100% max) at 0 cars, down to 0.0 at 10 cars
            spawn_prob = max(0.0, 1.0 - (live_count / MAX_CONCURRENT_VEHICLES))
            # Adaptive delay: very fast when empty (0.8s), gradually spacing out as count grows
            delay = 0.8 + (live_count / MAX_CONCURRENT_VEHICLES) * 2.2
            time.sleep(random.uniform(delay * 0.85, delay * 1.15))
            if not broker.infrastructure_active:
                continue
            with broker.lock:
                live_count = len(agents)
                if live_count >= MAX_CONCURRENT_VEHICLES:
                    continue
            # Roll against dynamic spawn probability
            if random.random() > spawn_prob:
                continue
            sn, tn = random.choice(VALID_ROUTES)
            speed = random.uniform(55.0, 75.0)
            # 10 % chance of spawning an ambulance for variety
            if random.random() < 0.10:
                new_id = f"Ambulance_{random.randint(100, 999)}"
                new_agent = VehicleAgent(new_id, sn, tn, 75.0,
                                         vehicle_type="Ambulance",
                                         driving_style="Aggressive")
            else:
                new_id = f"Car_{random.randint(100, 999)}"
                new_agent = VehicleAgent(new_id, sn, tn, speed)
            with broker.lock:
                is_safe = True
                for a in list(agents.values()):
                    if not getattr(a, "is_crashed", False):
                        dist = math.sqrt(
                            (a.position_x - new_agent.position_x) ** 2
                            + (a.position_y - new_agent.position_y) ** 2
                        )
                        if dist < 60.0:
                            is_safe = False
                            break
                if is_safe:
                    agents[new_id] = new_agent
                    print(f"[AutoSpawner] {new_id} → {sn} -> {tn} (total: {len(agents)}/{MAX_CONCURRENT_VEHICLES}, prob: {spawn_prob*100:.0f}%)")
                else:
                    print(f"[AutoSpawner] Spawn point {sn} crowded, retrying.")
    threading.Thread(target=auto_spawner, daemon=True).start()

    def background_task():
        dt = 0.05
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
                    if animal_dist < 25:
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
                    if dist < 16:
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
                agent.decide_action(target_int[0], target_int[1])
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
