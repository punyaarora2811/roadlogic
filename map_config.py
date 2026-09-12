# map_config.py
# Resolution: 1500x800
# Logic: 4 nodes per intersection (Corners: NW, NE, SE, SW) with perpendicular turns.

nodes = {
    # --- EDGES (Spawn / Exit Points) ---
    "W_START": (0, 675),
    "W_END": (0, 635),
    "E_START": (1500, 635),
    "E_END": (1500, 675),
    "S1_START": (420, 800),
    "S1_END": (380, 800),
    "S2_START": (1140, 800),
    "S2_END": (1100, 800),
    "NW_START": (0, 100),
    "NW_END": (0, 70),
    "NE_ONEWAY_START": (1000, 0),
    # --- INTERSECTION 1 (4 central nodes) ---
    "I1_NW": (380, 635),
    "I1_NE": (420, 635),
    "I1_SE": (420, 675),
    "I1_SW": (380, 675),
    # --- INTERSECTION 2 (4 central nodes) ---
    "I2_NW": (1090, 635),
    "I2_NE": (1150, 635),
    "I2_SE": (1140, 675),
    "I2_SW": (1100, 675),
    # --- INTERSECTION 3 (4 central nodes) ---
    "I3_NW": (380, 290),
    "I3_NE": (420, 280),
    "I3_SE": (420, 310),
    "I3_SW": (380, 320),
    # --- INTERSECTION 4 (Merge Points - remains as simple) ---
    "MERGE_UP": (770, 455),  
    "MERGE_DOWN": (760, 475),
}

edges = [
    # --- 1. ENTRANCE / EXIT TO EDGES ---
    # West
    ("W_START", "I1_SW", 1),
    ("I1_NW", "W_END", 1),
    # East
    ("E_START", "I2_NE", 1),
    ("I2_SE", "E_END", 1),
    # South 1
    ("S1_START", "I1_SE", 1),
    ("I1_SW", "S1_END", 1),
    # South 2
    ("S2_START", "I2_SE", 1),
    ("I2_SW", "S2_END", 1),
    # North-West
    ("NW_START", "I3_NW", 1),
    ("I3_NE", "NW_END", 1),
    # --- 2. CONNECTING ROADS BETWEEN INTERSECTIONS ---
    # I1 <-> I2 (Bottom Horizontal)
    ("I1_SE", "I2_SW", 1),  # To East
    ("I2_NW", "I1_NE", 1),  # To West
    # I1 <-> I3 (Left Vertical)
    ("I1_NE", "I3_SE", 1),  # To North
    ("I3_SW", "I1_NW", 1),  # To South
    # I2 <-> I3 (Main Diagonal) - Passes through Merge Points
    ("I3_SE", "MERGE_DOWN", 1),  # From I3 goes down to I2
    ("MERGE_DOWN", "I2_NW", 1),
    ("I2_NE", "MERGE_UP", 1),  # From I2 goes up to I3
    ("MERGE_UP", "I3_NE", 1),
    # --- 3. ONE WAY I4 ---
    ("NE_ONEWAY_START", "MERGE_UP", 1),
    ("NE_ONEWAY_START", "MERGE_DOWN", 1),  # Spills to I2
    # --- 4. INTERNAL CONNECTION OF INTERSECTIONS ---
    # Cars drive Counter-Clockwise inside (right-of-way rule)
    # I1
    ("I1_NW", "I1_SW", 1),
    ("I1_SW", "I1_SE", 1),
    ("I1_SE", "I1_NE", 1),
    ("I1_NE", "I1_NW", 1),
    # I2
    ("I2_NW", "I2_SW", 1),
    ("I2_SW", "I2_SE", 1),
    ("I2_SE", "I2_NE", 1),
    ("I2_NE", "I2_NW", 1),
    # I3
    ("I3_NW", "I3_SW", 1),
    ("I3_SW", "I3_SE", 1),
    ("I3_SE", "I3_NE", 1),
    ("I3_NE", "I3_NW", 1),
]
