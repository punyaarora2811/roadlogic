import pytest
import time
from v2x_security import SecurityManager
from v2x_network import V2XBroker
from vehicle_agent import VehicleAgent

def test_security_valid_signature():
    """Test if a valid digitally signed package is accepted."""
    data = {
        "agent_id": "Test_Car",
        "position_x": 100.0,
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time(),
    }
    data["signature"] = SecurityManager.sign_data(data)
    assert SecurityManager.is_payload_valid(data, "Center_TrafficLight") == True

def test_security_tampered_payload():
    """Test if modifying data invalidates signature."""
    data = {
        "agent_id": "Test_Car",
        "position_x": 100.0,
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time(),
    }
    data["signature"] = SecurityManager.sign_data(data)
    # Attacker modifies speed after package was signed
    data["speed"] = 150.0
    assert SecurityManager.is_payload_valid(data, "Center_TrafficLight") == False

def test_security_expired_payload():
    """Test anti-ghosting: packages older than 2.0 seconds must be rejected."""
    data = {
        "agent_id": "Test_Car",
        "position_x": 100.0,
        "position_y": 200.0,
        "speed": 50.0,
        "timestamp": time.time() - 3.0,  # Generated 3 seconds ago
    }
    data["signature"] = SecurityManager.sign_data(data)
    assert SecurityManager.is_payload_valid(data, "Center_TrafficLight") == False

def test_vehicle_agent_initialization():
    """Test if a vehicle initializes correctly."""
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)
    assert agent.agent_id == "Car_1"
    assert agent.desired_speed == 60.0
    assert agent.current_state == "CRUISE"

def test_vehicle_agent_ambulance_priority(mocker):
    """Test if normal car pulls over (-20.0) when it sees ambulance behind."""
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)
    # Force values on agent to bypass cold start of navigation
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.visual_angle",
        new_callable=mocker.PropertyMock,
        return_value=0.0,
    )
    # Set position using agent setter (updates base_x)
    agent.position_x = 100.0
    agent.position_y = 675.0
    # Artificially insert ambulance into V2X memory, right behind
    agent.memory["Ambulance_VIP"] = {
        "agent_id": "Ambulance_VIP",
        "vehicle_type": "Ambulance",
        "position_x": 50.0,
        "position_y": 675.0,
        "heading": "EAST",
    }
    agent.decide_action(400, 650)
    assert agent.target_lane_offset == -20.0

def test_vehicle_agent_ambulance_opposite_priority(mocker):
    """Test if car pulls over when it sees ambulance from OPPOSITE direction."""
    agent = VehicleAgent("Car_1", "E_START", "W_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="WEST",
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.visual_angle",
        new_callable=mocker.PropertyMock,
        return_value=180.0,
    )
    agent.position_x = 200.0
    agent.position_y = 635.0
    # Inject ambulance in front of it on oncoming lane (heading East)
    agent.memory["Ambulance_VIP"] = {
        "agent_id": "Ambulance_VIP",
        "vehicle_type": "Ambulance",
        "position_x": 100.0,
        "position_y": 675.0,
        "heading": "EAST",
    }
    agent.decide_action(400, 650)
    assert agent.target_lane_offset == -20.0

def test_vehicle_agent_red_light(mocker):
    """Test if car brakes correctly at RED traffic light (V2I)."""
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.visual_angle",
        new_callable=mocker.PropertyMock,
        return_value=0.0,
    )
    # Place it quite close to intersection at X=400
    agent.position_x = 320.0
    agent.position_y = 675.0
    # Inject traffic light in memory
    agent.memory["Center_TrafficLight"] = {
        "agent_id": "Center_TrafficLight",
        "vehicle_type": "Infrastructure",
        "state_NS": "GREEN",
        "state_EW": "RED",  # Red on its direction (East-West)
        "time_to_change": 3.0,
        "position_x": 400.0,
        "position_y": 400.0,
    }
    agent.decide_action(400, 650)
    # Check if it detected traffic light and entered braking state
    assert agent.current_state == "BRAKING"

def test_vehicle_agent_acc_braking(mocker):
    """Test if safety braking (ACC) triggers when car too close to leader."""
    agent = VehicleAgent("Car_Fast", "W_START", "E_END", desired_speed=80.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    mocker.patch(
        "vehicle_agent.VehicleAgent.visual_angle",
        new_callable=mocker.PropertyMock,
        return_value=0.0,
    )
    agent.position_x = 100.0
    agent.position_y = 675.0
    # Inject slow car just 40 pixels in front of it
    agent.memory["Car_Slow"] = {
        "agent_id": "Car_Slow",
        "vehicle_type": "Normal",
        "position_x": 140.0,
        "position_y": 675.0,
        "speed": 20.0,
        "heading": "EAST",
        "visual_angle": 0.0,
    }
    agent.decide_action(400, 650)
    assert agent.current_state == "BRAKING"
    assert agent.speed < 80.0  # Speed must have automatically decreased

def test_vehicle_agent_animal_obstacle(mocker):
    """Test emergency braking upon detecting animal on road."""
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)
    mocker.patch(
        "vehicle_agent.VehicleAgent.heading",
        new_callable=mocker.PropertyMock,
        return_value="EAST",
    )
    agent.position_x = 100.0
    agent.position_y = 675.0
    # Inject deer 50 meters in front of car
    agent.memory["Deer"] = {
        "agent_id": "Deer",
        "vehicle_type": "Animal",
        "position_x": 150.0,
        "position_y": 675.0,
    }
    agent.decide_action(400, 650)
    assert agent.current_state == "BRAKING"

def test_vehicle_agent_crashed_state():
    """Test if crashed car is paralyzed correctly."""
    agent = VehicleAgent("Car_1", "W_START", "E_END", desired_speed=60.0)
    agent.is_crashed = True
    agent.decide_action(400, 650)
    assert agent.speed == 0.0
    assert agent.current_state == "CRASHED"

def test_v2x_broker_isolation():
    """Test if broker isolates packages (vehicle doesn't receive its own message)."""
    broker = V2XBroker()
    broker.publish("Car_A", {"speed": 50.0})
    broker.publish("Car_B", {"speed": 40.0})
    # Car A listens to network
    traffic_for_a = broker.receive("Car_A")
    assert "Car_A" not in traffic_for_a
    assert "Car_B" in traffic_for_a
