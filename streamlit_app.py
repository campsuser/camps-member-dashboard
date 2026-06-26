import re
import random
import pandas as pd
import pydeck as pdk
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Set page config
st.set_page_config(
    page_title="CAMPS Supply Chain & Capability Match Engine",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Minimalist, Professional, High-Contrast Executive Look
st.markdown("""
<style>
    /* Dark Slate Executive Theme */
    .stApp {
        background-color: #0F172A;
        color: #F8FAFC;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #1E293B !important;
        border-right: 1px solid #334155;
    }
    
    section[data-testid="stSidebar"] h1, 
    section[data-testid="stSidebar"] h2, 
    section[data-testid="stSidebar"] h3 {
        color: #00F0FF !important;
        font-size: 1.1rem !important;
        font-weight: 700 !important;
        margin-top: 15px !important;
        margin-bottom: 10px !important;
    }
    
    section[data-testid="stSidebar"] label {
        color: #E2E8F0 !important;
        font-weight: 500;
        font-size: 0.85rem !important;
    }

    /* Cards & Containers */
    div[data-testid="stMetric"] {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-radius: 8px;
        padding: 15px 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
    }
    
    div[data-testid="stMetric"] label {
        color: #94A3B8 !important;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-size: 0.75rem !important;
    }

    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        color: #00F0FF !important;
        font-weight: 700;
        font-size: 1.8rem;
    }

    /* Custom KPI Panels */
    .kpi-card {
        background-color: #1E293B;
        border: 1px solid #334155;
        border-left: 4px solid #00F0FF;
        border-radius: 6px;
        padding: 15px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin-bottom: 10px;
    }

    .kpi-card.capacity {
        border-left: 4px solid #F59E0B; /* Gold/Yellow for Open Capacity */
    }

    .kpi-card.warning {
        border-left: 4px solid #F59E0B;
    }

    .kpi-card.danger {
        border-left: 4px solid #EF4444;
    }

    .kpi-title {
        color: #94A3B8;
        font-size: 0.75rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        font-weight: 600;
        margin-bottom: 5px;
    }

    .kpi-value {
        color: #F8FAFC;
        font-size: 1.4rem;
        font-weight: 700;
    }

    .kpi-desc {
        color: #CBD5E1;
        font-size: 0.8rem;
        margin-top: 5px;
    }

    /* Header styling */
    .dashboard-header {
        border-bottom: 1px solid #334155;
        padding-bottom: 15px;
        margin-bottom: 25px;
    }
    
    .dashboard-header h1 {
        font-size: 2.2rem;
        font-weight: 800;
        letter-spacing: -0.02em;
        margin-bottom: 5px;
        background: linear-gradient(135deg, #FFF 0%, #00F0FF 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .dashboard-header p {
        color: #94A3B8;
        font-size: 1rem;
        margin: 0;
    }

    /* Custom buttons */
    .stButton>button {
        background-color: #1E293B;
        color: #F8FAFC;
        border: 1px solid #334155;
        border-radius: 6px;
        transition: all 0.2s ease;
    }
    
    .stButton>button:hover {
        background-color: #00F0FF;
        color: #0F172A;
        border-color: #00F0FF;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        border-bottom: 1px solid #334155;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        color: #94A3B8;
        border: none;
        padding: 10px 16px;
        font-weight: 500;
        border-radius: 4px 4px 0 0;
    }

    .stTabs [data-baseweb="tab"]:hover {
        color: #00F0FF;
    }

    .stTabs [aria-selected="true"] {
        background-color: #1E293B !important;
        color: #00F0FF !important;
        border-bottom: 2px solid #00F0FF !important;
    }

    /* Highlight badge styles */
    .capacity-badge {
        background-color: rgba(245, 158, 11, 0.2);
        color: #F59E0B;
        border: 1px solid #F59E0B;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    .tech-badge {
        background-color: rgba(112, 0, 255, 0.2);
        color: #C084FC;
        border: 1px solid #7000FF;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }

    .prod-badge {
        background-color: rgba(0, 240, 255, 0.15);
        color: #00F0FF;
        border: 1px solid #00F0FF;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
</style>
""", unsafe_allow_html=True)

# ------------------ CONSTANTS & TAXONOMY ------------------
GOOGLE_SHEET_URL = "https://docs.google.com/spreadsheets/d/1ms5e9lKWEHvihC7kyirU91FwtTQAtoIQKatYzx1LySM/edit?usp=sharing"

PAIN_POINT_TAXONOMY = {
    "Assembly errors & manual defects": ["Computer Vision", "Quality AI", "Mistake-Proofing", "Digital Work Instructions"],
    "Slow operator onboarding / training bottlenecks": ["Digital Work Instructions", "Training Support Platforms"],
    "WIP visibility & inventory bottlenecks": ["MES", "RFID / RTLS Tracking", "Industrial IoT"],
    "Machine downtime & equipment failure": ["Predictive Maintenance", "Sensors & Telemetry"],
    "Process integration & system silos": ["Systems Integration", "Robotics", "PLC Programming"]
}

CITY_CLEANING = {
    "MT. VERNON": "Mount Vernon",
    "LYNWOOD": "Lynnwood",
    "SEDRO WOOLEY": "Sedro-Woolley",
    "SEDRO WOOLLEY": "Sedro-Woolley",
    "TUKWILLA": "Tukwila",
    "SULTON": "Sultan",
    "GOLENENDALE": "Goldendale",
    "WISHROM": "Wishram"
}

COORDINATES = {
    "Anacortes": (48.5126, -122.6127),
    "Arlington": (48.1986, -122.1251),
    "Auburn": (47.3073, -122.2285),
    "Bainbridge Island": (47.6262, -122.5212),
    "Belfair": (47.4523, -122.8285),
    "Bellevue": (47.6101, -122.1428),
    "Bellingham": (48.7519, -122.4787),
    "Blaine": (48.9937, -122.7471),
    "Bothell": (47.7601, -122.2057),
    "Burlington": (48.4762, -122.3324),
    "Chelan": (47.8404, -120.0162),
    "Custer": (48.9242, -122.6371),
    "Eastsound": (48.6968, -122.9090),
    "Edmonds": (47.8107, -122.3774),
    "Enumclaw": (47.2029, -121.9904),
    "Everett": (47.9790, -122.2021),
    "Ferndale": (48.8479, -122.5902),
    "Fife": (47.2343, -122.3565),
    "Gig Harbor": (47.3293, -122.5801),
    "Goldendale": (45.8210, -120.8212),
    "Granite Falls": (48.0845, -121.9682),
    "Issaquah": (47.5301, -122.0326),
    "Kennewick": (46.2112, -119.1372),
    "Kent": (47.3809, -122.2348),
    "Kirkland": (47.6786, -122.2054),
    "Lake Forest Park": (47.7512, -122.2796),
    "Lakewood": (47.1718, -122.5185),
    "Leavenworth": (47.5962, -120.6615),
    "Lowden": (46.0560, -118.5830),
    "Lynden": (48.9084, -122.4518),
    "Lynnwood": (47.8209, -122.3151),
    "Maple Valley": (47.4068, -122.0396),
    "Marysville": (48.0518, -122.1771),
    "Mercer Island": (47.5601, -122.2201),
    "Mesa": (46.5774, -119.0065),
    "Mill Creek": (47.8565, -122.2215),
    "Monroe": (47.8557, -121.9707),
    "Mount Vernon": (48.4198, -122.3340),
    "Mountlake Terrace": (47.7876, -122.3049),
    "Mukilteo": (47.9445, -122.3046),
    "Oakville": (46.8398, -123.2307),
    "Odessa": (47.3307, -118.7126),
    "Olympia": (47.0379, -122.9007),
    "Othello": (46.8226, -119.1695),
    "Port Hadlock": (48.0300, -122.7500),
    "Port Orchard": (47.5315, -122.6360),
    "Port Townsend": (48.1170, -122.7604),
    "Poulsbo": (47.7359, -122.6465),
    "Prosser": (46.2068, -119.7689),
    "Puyallup": (47.1854, -122.2929),
    "Redmond": (47.6740, -122.1215),
    "Renton": (47.4829, -122.2035),
    "Sammamish": (47.6163, -122.0356),
    "SeaTac": (47.4437, -122.2965),
    "Seattle": (47.6062, -122.3321),
    "Sedro-Woolley": (48.5039, -122.2362),
    "Shoreline": (47.7560, -122.3457),
    "Snohomish": (47.9126, -122.0982),
    "Snoqualmie Pass": (47.4204, -121.4154),
    "Spokane": (47.6588, -117.4260),
    "Sultan": (47.8623, -121.8151),
    "Sumas": (48.9996, -122.2646),
    "Sumner": (47.2029, -122.2429),
    "Sunnyside": (46.2757, -120.0117),
    "Tacoma": (47.2529, -122.4443),
    "Tel Aviv": (32.0853, 34.7818),
    "Tensed, ID": (47.1585, -116.9246),
    "Thorp": (47.0668, -120.6707),
    "Tukwila": (47.4740, -122.2610),
    "Tumwater": (47.0051, -122.9096),
    "Underwood": (45.7246, -121.5285),
    "Vancouver": (45.6387, -122.6615),
    "Vashon": (47.4479, -122.4635),
    "Walla Walla": (46.0646, -118.3430),
    "Wapato": (46.4468, -120.4204),
    "Wenatchee": (47.4235, -120.3103),
    "Wishram": (45.6593, -120.9635),
    "Woodinville": (47.7543, -122.1635),
    "Yakima": (46.6021, -120.5059)
}

# Seed Dual-Track specifications
SEED_DATA = {
    "Access Laser Company": {
        "track": "Physical Production",
        "machinery_types": ["CNC Precision Machining", "CO2 Laser Test Rig", "High-Vacuum Chamber"],
        "materials": ["Composites", "Glass", "Aluminum"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "CO2 Laser Test & Characterization Rig",
                "shift_availability": "12 hours/week",
                "description": "Available for custom laser power validation and optical wavelength testing."
            }
        ]
    },
    "Advanced Powder Coating NW, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Powder Coating Oven (8ft x 20ft)", "Media Blasting Booth"],
        "materials": ["Steel", "Aluminum", "Titanium"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "AeroGo, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Heavy Structural Welding Station", "3-Axis CNC", "Air Caster Load Test Pad"],
        "materials": ["Steel", "Aluminum"],
        "certifications": ["ISO 9001", "AS9100"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Alliance Manufacturing Group": {
        "track": "Physical Production",
        "machinery_types": ["5-Axis CNC Mill", "CNC Lathe", "Techni-Grip Workholding Assembly"],
        "materials": ["Steel", "Aluminum", "Titanium"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "American Rifle Company": {
        "track": "Physical Production",
        "machinery_types": ["3-Axis CNC", "CNC Turning Center"],
        "materials": ["Steel", "Titanium"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "BMT USA, LLC": {
        "track": "Physical Production",
        "machinery_types": ["Sheet Metal Fab", "Orbital TIG Welder", "Cleanroom Assembly Area"],
        "materials": ["Stainless Steel", "Aluminum"],
        "certifications": ["ISO 9001", "ASME Section VIII"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Buyken Metal Products": {
        "track": "Physical Production",
        "machinery_types": ["150-Ton Stamping Press", "Sheet Metal Fab", "Laser Cutter"],
        "materials": ["Steel", "Aluminum", "Stainless Steel"],
        "certifications": ["ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "150-Ton Stamping Press",
                "shift_availability": "2 shifts/week (16 hours)",
                "description": "Open window for large run metal stampings, progressive die setups."
            }
        ]
    },
    "The BoxMaker a Supply One Company": {
        "track": "Physical Production",
        "machinery_types": ["Digital Corrugated Press", "Flatbed Die Cutter"],
        "materials": ["Paperboard", "Plastics"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Cannon Machine Products, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["5-Axis CNC Mill", "3-Axis CNC", "CNC Lathe"],
        "materials": ["Titanium", "Aluminum", "Composites"],
        "certifications": ["AS9100", "ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "Matsuura 5-Axis CNC Machining Center",
                "shift_availability": "1 shift/week (8 hours)",
                "description": "Open capacity for high-precision hard metal milling (Titanium/Inconel)."
            }
        ]
    },
    "Corvus Energy USA": {
        "track": "Physical Production",
        "machinery_types": ["Automated Battery Cell Assembly", "Environmental Testing Chamber"],
        "materials": ["Lithium-Ion", "Aluminum"],
        "certifications": ["ISO 9001", "DNV-GL Marine Certification"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "EDCO Metal Fabricators": {
        "track": "Physical Production",
        "machinery_types": ["Heavy Plate Welding Station", "CNC Plasma Cutter", "10-Ton Overhead Crane"],
        "materials": ["Structural Steel", "Aluminum"],
        "certifications": ["AWS Certified Welding"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "Heavy Plate Weld & Fabrication Station",
                "shift_availability": "20 hours/week",
                "description": "Ideal for structural steel assemblies, includes 10-ton overhead crane support."
            }
        ]
    },
    "GlobalTech Plastics LLC": {
        "track": "Physical Production",
        "machinery_types": ["300-Ton Injection Molding Machine", "Plastics Extruder"],
        "materials": ["Plastics", "Composites"],
        "certifications": ["ISO 9001", "ISO 13485 (Medical)"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "300-Ton Toyo Plastic Injection Molding Press",
                "shift_availability": "2 shifts/week",
                "description": "Available for custom runs, mold testing, and cleanroom packaging."
            }
        ]
    },
    "Golden Harvest, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Sheet Metal Fab", "Heavy Welding Station"],
        "materials": ["Stainless Steel", "Aluminum"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Haley Manufacturing Inc": {
        "track": "Physical Production",
        "machinery_types": ["CNC Laser Cutter", "Press Brake", "Robotics Assembly Station"],
        "materials": ["Steel", "Aluminum"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Harbor Island Machine Works, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["5-Axis CNC Mill", "3-Axis CNC", "CNC ID/OD Grinder"],
        "materials": ["Titanium", "Aluminum", "Stainless Steel"],
        "certifications": ["AS9100", "ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "5-Axis CNC Machining Center",
                "shift_availability": "10 hours/week",
                "description": "Open space for complex geometries and aerospace component machining."
            }
        ]
    },
    "ID Integration": {
        "track": "Technology & Automation",
        "solutions": ["Digital Work Instructions", "RFID / RTLS Tracking", "Systems Integration"],
        "resolved_pain_points": ["Slow onboarding", "WIP visibility", "Inventory bottleneck"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Island Machine Inc": {
        "track": "Physical Production",
        "machinery_types": ["CNC Lathe", "3-Axis CNC", "Thread Roller"],
        "materials": ["Titanium", "Aluminum", "Inconel"],
        "certifications": ["AS9100", "ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "CNC Turning Center / Lathe",
                "shift_availability": "15 hours/week",
                "description": "Available for precision turning, thread rolling, and prototype manufacturing."
            }
        ]
    },
    "Laser Cutting Northwest": {
        "track": "Physical Production",
        "machinery_types": ["6kW Fiber Laser Cutter", "CNC Press Brake", "Deburring Machine"],
        "materials": ["Steel", "Aluminum", "Stainless Steel", "Brass"],
        "certifications": ["ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "6kW Bystronic Fiber Laser Cutter",
                "shift_availability": "1 shift/week (8 hours)",
                "description": "High speed laser cutting for thin/medium plate steels, copper, and brass."
            }
        ]
    },
    "Lightel Technologies": {
        "track": "Physical Production",
        "machinery_types": ["Fiber Optic Fusion Splicer", "Microscope Inspection System"],
        "materials": ["Glass", "Plastics"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Membrion, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Ceramic Membrane Casting Line", "Sintering Kiln"],
        "materials": ["Ceramics", "Composites"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Metal Solutions LLC": {
        "track": "Physical Production",
        "machinery_types": ["Sheet Metal Fab", "TIG/MIG Welding Booths", "Ironworker"],
        "materials": ["Steel", "Aluminum"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Mid-Mountain Materials, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["High-Temperature Coater", "Thermal Textile Loom"],
        "materials": ["Composites", "Silicones", "Glass Fiber"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Out of the Box Manufacturing": {
        "track": "Physical Production",
        "machinery_types": ["SMT Pick & Place Line", "Reflow Oven", "Automated Optical Inspection (AOI)"],
        "materials": ["FR4", "Copper", "Solder Alloys"],
        "certifications": ["AS9100", "ISO 9001", "ISO 13485 (Medical)", "ITAR"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Pacific Metalurgical Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Vacuum Heat Treat Furnace", "Induction Hardening Machine"],
        "materials": ["Steel", "Titanium", "Superalloys"],
        "certifications": ["AS9100", "Nadcap Heat Treating", "ITAR"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Pioneer Aerofab Company, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Industrial Sewing Station", "Composite Layup Table"],
        "materials": ["Composites", "Aerospace Fabrics"],
        "certifications": ["AS9100", "ISO 9001", "ITAR"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Quality Stamping & Machining, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["High-Speed Stamping Line", "3-Axis CNC", "Press Brake"],
        "materials": ["Steel", "Aluminum", "Brass"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "High-Speed Progressive Stamping Line",
                "shift_availability": "12 hours/week",
                "description": "Available for long-run stamping of small components and bracket assemblies."
            }
        ]
    },
    "Remote Control Technology": {
        "track": "Physical Production",
        "machinery_types": ["SMT Line", "RF Signal Generator"],
        "materials": ["FR4", "Plastics"],
        "certifications": ["ISO 9001", "FCC Certified Facility"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Rothenbuhler Engineering": {
        "track": "Physical Production",
        "machinery_types": ["Wave Soldering Machine", "SMT Line", "Environmental Test Chamber"],
        "materials": ["FR4", "Steel"],
        "certifications": ["ISO 9001", "MSHA Approved Production"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Rottler Manufacturing": {
        "track": "Physical Production",
        "machinery_types": ["5-Axis CNC Mill", "CNC Cylinder Hone", "Precision Lathe"],
        "materials": ["Steel", "Cast Iron", "Aluminum"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Seakamp Engineering, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Tube Bending Machine", "MIG/TIG Welder", "Maritime Assembly Bay"],
        "materials": ["Copper-Nickel", "Bronze", "Stainless Steel"],
        "certifications": ["ISO 9001", "NAVSEA Certified Welding"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Skills Inc.": {
        "track": "Physical Production",
        "machinery_types": ["AS9100 Coordinate Measuring Machine (CMM)", "3-Axis CNC", "Chemical Processing Anodizing Line"],
        "materials": ["Aluminum", "Titanium", "Stainless Steel"],
        "certifications": ["AS9100", "Nadcap Chemical Processing", "ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "AS9100 Certified Zeiss Coordinate Measuring Machine (CMM)",
                "shift_availability": "1 shift/week (8 hours)",
                "description": "Zeiss Contura CMM open for contract inspection and dimensional verification."
            }
        ]
    },
    "Steeler Inc.": {
        "track": "Physical Production",
        "machinery_types": ["Roll Forming Mill", "Sheet Metal Fab"],
        "materials": ["Steel"],
        "certifications": ["ISO 9001", "ICC-ES Approved Facility"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Sterlitech Corporation": {
        "track": "Physical Production",
        "machinery_types": ["Cleanroom Packaging Line", "Filter Slitting Machine"],
        "materials": ["Membranes", "Plastics"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Stratus Automation Corporation": {
        "track": "Technology & Automation",
        "solutions": ["Robotics", "Systems Integration", "PLC Programming"],
        "resolved_pain_points": ["Process integration", "System silo", "PLC connection"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "TNT Aerospace": {
        "track": "Physical Production",
        "machinery_types": ["5-Axis CNC Mill", "3-Axis CNC", "Coordinate Measuring Machine (CMM)"],
        "materials": ["Titanium", "Aluminum", "Superalloys"],
        "certifications": ["AS9100", "ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "Mori Seiki 5-Axis Machining Center",
                "shift_availability": "15 hours/week",
                "description": "Open shift for high speed aerospace machining."
            }
        ]
    },
    "Torklift Central Welding of Kent": {
        "track": "Physical Production",
        "machinery_types": ["Heavy Welding Station", "Tube Bender", "Plasma Cutter"],
        "materials": ["Steel", "Aluminum"],
        "certifications": ["AWS Certified Welding"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Tri-Tec Manufacturing": {
        "track": "Physical Production",
        "machinery_types": ["Valve Assembly & Test Rig", "CNC Machining Center", "Clean Room"],
        "materials": ["Stainless Steel", "Bronze", "Monel"],
        "certifications": ["MIL-SPEC Standard Facility", "ISO 9001", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "Maritime Assembly Clean Room",
                "shift_availability": "10 hours/week",
                "description": "Open for sub-assembly assembly requiring cleanroom specifications."
            }
        ]
    },
    "Triton Holdings": {
        "track": "Physical Production",
        "machinery_types": ["Composite Autoclave (6ft x 12ft)", "Composite Layup Clean Room"],
        "materials": ["Composites", "Carbon Fiber", "Fiberglass"],
        "certifications": ["AS9100", "FAA Approved Facility", "ITAR"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "Composite Autoclave (6ft x 12ft, 400F)",
                "shift_availability": "2 runs/week",
                "description": "Open cure capacity for aerospace composite layups."
            }
        ]
    },
    "Unitec": {
        "track": "Physical Production",
        "machinery_types": ["Composite Panel Press", "CNC Router"],
        "materials": ["Composites", "Honeycomb Panels"],
        "certifications": ["AS9100", "ISO 9001", "ITAR"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Warmoth Guitar Products, Inc.": {
        "track": "Physical Production",
        "machinery_types": ["CNC Router", "Guitar Finishing Spray Booth"],
        "materials": ["Wood", "Composites"],
        "certifications": ["ISO 9001"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Western Integrated Technologies, Inc.": {
        "track": "Technology & Automation",
        "solutions": ["Predictive Maintenance", "Sensors & Telemetry", "Systems Integration"],
        "resolved_pain_points": ["Machine downtime", "Equipment failure", "Maintenance scheduling"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "YST SemiConductor": {
        "track": "Physical Production",
        "machinery_types": ["Cleanroom Wire Bonder", "Wafer Probing Station"],
        "materials": ["Silicon", "Gold", "Copper"],
        "certifications": ["ISO 9001", "ITAR"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Xemelgo": {
        "track": "Technology & Automation",
        "solutions": ["MES", "RFID / RTLS Tracking", "Industrial IoT"],
        "resolved_pain_points": ["WIP visibility", "Inventory bottleneck", "Production tracking"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Retrocausal, Inc.": {
        "track": "Technology & Automation",
        "solutions": ["Computer Vision", "Quality AI", "Mistake-Proofing", "Digital Work Instructions"],
        "resolved_pain_points": ["Assembly errors", "Manual defects", "High scrap rate", "Slow onboarding", "Operator training bottlenecks"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Kanoa": {
        "track": "Technology & Automation",
        "solutions": ["MES", "Systems Integration", "Industrial Software & IoT"],
        "resolved_pain_points": ["Process integration", "System silo"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "LOOPR AI, Inc.": {
        "track": "Technology & Automation",
        "solutions": ["Computer Vision", "Quality AI", "Mistake-Proofing"],
        "resolved_pain_points": ["Assembly errors", "Manual defects", "High scrap rate"],
        "excess_capacity_flag": False,
        "shared_capacity": []
    },
    "Root Sciences": {
        "track": "Physical Production",
        "machinery_types": ["Supercritical CO2 Extraction Rig", "Short-Path Distillation Column"],
        "materials": ["Stainless Steel", "Glass"],
        "certifications": ["ISO 9001", "GMP Certified Facility"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "Supercritical CO2 Extraction Rig",
                "shift_availability": "8 hours/week",
                "description": "High pressure chemical extraction rig open for experimental runs."
            }
        ]
    },
    "Open Source Steel": {
        "track": "Physical Production",
        "machinery_types": ["TIG Welding Station", "Heavy Metal Rolling Brake"],
        "materials": ["Stainless Steel", "Carbon Steel"],
        "certifications": ["ASME Pressure Vessel Welding"],
        "excess_capacity_flag": True,
        "shared_capacity": [
            {
                "equipment": "TIG Welding Station",
                "shift_availability": "15 hours/week",
                "description": "Available for custom pressure-tight sanitary stainless steel welding."
            }
        ]
    }
}

REG_PATTERNS = {
    "AS9100": r"\bas9100\b",
    "ISO 9001": r"\biso\s*9001\b",
    "ITAR": r"\bitar\b",
    "CMMC": r"\bcmmc\b|\bnist\s*sp\s*800-171\b",
    "5-Axis CNC": r"5-axis|five-axis|5axis",
    "3-Axis CNC": r"3-axis|three-axis|cnc\s*mill|cnc\s*lathe",
    "Sheet Metal Fab": r"sheet\s*metal|press\s*brake|bending|shear",
    "Additive Manufacturing": r"3d\s*print|additive\s*manufacturing",
    "Injection Molding": r"injection\s*mold",
    "Welding": r"weld",
    "Titanium": r"titanium|ti-6al-4v",
    "Aluminum": r"aluminum|aluminium",
    "Composites": r"composite|carbon\s*fiber|fiberglass",
    "Steel": r"\bsteel\b|stainless",
    "Computer Vision": r"computer\s*vision|camera|vision\s*system",
    "MES": r"\bmes\b|manufacturing\s*execution",
    "Industrial IoT": r"\biot\b|iiot|industrial\s*internet\s*of\s*things",
    "Digital Work Instructions": r"digital\s*work\s*instructions|work\s*guide",
    "Robotics": r"robot|cobot",
    "Quality AI": r"quality\s*ai|defect\s*detection",
    "Mistake-Proofing": r"mistake-proofing|poka-yoke",
    "Assembly errors": r"assembly\s*error|assembly\s*defect",
    "Manual defects": r"manual\s*defect|human\s*error",
    "Slow onboarding": r"onboard|training\s*bottleneck",
    "WIP visibility": r"wip|work\s*in\s*progress|tracking",
    "Machine downtime": r"downtime|breakdown|maintenance"
}

# ------------------ HELPER FUNCTIONS FOR IN-MEMORY PROCESSING ------------------
def clean_company_name(name):
    name = re.sub(r"\(dba\).*$", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\*\*.*$", "", name)
    name = re.sub(r"\(OPTED OUT\)", "", name, flags=re.IGNORECASE)
    name = re.sub(r"\(BOUNCED\)", "", name, flags=re.IGNORECASE)
    return name.strip()

def clean_city_name(city):
    if not city:
        return ""
    city_upper = str(city).strip().upper()
    if city_upper in CITY_CLEANING:
        return CITY_CLEANING[city_upper]
    return str(city).strip().title()

def classify_company(company_name, section):
    """Derives tracks and parameters. Uses SEED_DATA for target firms; defaults for others."""
    matched_seed = None
    for seed_name, data in SEED_DATA.items():
        if seed_name.lower() in company_name.lower() or company_name.lower() in seed_name.lower():
            matched_seed = data
            break
            
    if matched_seed:
        return matched_seed

    # Default rule-based mapping (No live scraping since it's too slow in direct load)
    is_tech = section == "Industrial Technology" or "software" in company_name.lower() or "tech" in company_name.lower()
    track = "Technology & Automation" if is_tech else "Physical Production"
    
    if track == "Physical Production":
        return {
            "track": track,
            "machinery_types": ["3-Axis CNC"],
            "materials": ["Steel", "Aluminum"],
            "certifications": ["ISO 9001"],
            "excess_capacity_flag": False,
            "shared_capacity": []
        }
    else:
        return {
            "track": track,
            "solutions": ["Systems Integration"],
            "resolved_pain_points": ["Process integration"],
            "excess_capacity_flag": False,
            "shared_capacity": []
        }

def extract_general_capabilities(track, info):
    caps = []
    inds = []
    if track == "Physical Production":
        mach = info.get("machinery_types", [])
        certs = info.get("certifications", [])
        
        has_cnc = any("cnc" in m.lower() or "machining" in m.lower() or "mill" in m.lower() or "turning" in m.lower() or "lathe" in m.lower() for m in mach)
        if has_cnc: caps.append("CNC Precision Machining")
        
        has_fab = any("fab" in m.lower() or "weld" in m.lower() or "stamping" in m.lower() or "laser" in m.lower() or "cutter" in m.lower() or "brake" in m.lower() for m in mach)
        if has_fab: caps.append("Metal Fabrication")
        
        has_comp = any("composite" in m.lower() or "autoclave" in m.lower() or "layup" in m.lower() for m in mach)
        if has_comp: caps.append("Aerospace Composites")
        
        has_fin = any("finishing" in m.lower() or "anodizing" in m.lower() or "coating" in m.lower() or "paint" in m.lower() or "heat treat" in m.lower() for m in mach)
        if has_fin: caps.append("Heat Treating & Finishing")
        
        has_elect = any("smt" in m.lower() or "assembly" in m.lower() or "splicer" in m.lower() or "probe" in m.lower() or "solder" in m.lower() or "wire" in m.lower() for m in mach)
        if has_elect: caps.append("Electronics Assembly")
        
        if not caps: caps = ["Metal Fabrication"]
        
        if any("as9100" in c.lower() for c in certs): inds.extend(["Aerospace", "Defense"])
        if any("itar" in c.lower() for c in certs) and "Defense" not in inds: inds.append("Defense")
        if any("13485" in c.lower() for c in certs): inds.append("Medical")
        if not inds: inds = ["Commercial/Industrial"]
    else:
        sols = info.get("solutions", [])
        if any("robot" in s.lower() or "automation" in s.lower() for s in sols):
            caps.append("Robotics & Automation")
        if any("software" in s.lower() or "iot" in s.lower() or "mes" in s.lower() or "vision" in s.lower() or "analytics" in s.lower() for s in sols):
            caps.append("Industrial Software & IoT")
        if not caps: caps = ["Industrial Software & IoT"]
        
        inds = ["Aerospace", "Defense", "Medical", "Commercial/Industrial"]
        
    return caps, inds

# ------------------ IN-MEMORY INGESTION PIPELINE ------------------
@st.cache_data(ttl="15m")
def load_and_process_data():
    """Fetches raw data from Google Sheet, cleans, geocodes, and tracks parameters in memory."""
    try:
        # Create Google Sheets connection
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        # Read the raw sheet data (header=None since spreadsheet has multiple sections and empty rows)
        raw_df = conn.read(spreadsheet=GOOGLE_SHEET_URL, header=None)
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {e}")
        return pd.DataFrame()

    sections_rows = {}
    current_section = None
    
    # Iterate through rows and extract categories
    for idx, row in raw_df.iterrows():
        # Convert row values to string list, ignore None
        row_vals = [str(val).strip() for val in row.values if pd.notna(val)]
        if not row_vals:
            continue
            
        row_str = ",".join(row_vals).upper()
        if "MANUFACTURERS" in row_str and "WEBSITE" in row_str:
            current_section = "MANUFACTURERS"
            sections_rows[current_section] = []
            continue
        elif "CANNABIS" in row_str and "WEBSITE" in row_str:
            current_section = "CANNABIS"
            sections_rows[current_section] = []
            continue
        elif "ASSOCIATE" in row_str and "WEBSITE" in row_str:
            current_section = "ASSOCIATES"
            sections_rows[current_section] = []
            continue
        elif "AFFILIATE" in row_str and "WEBSITE" in row_str:
            current_section = "AFFILIATES"
            sections_rows[current_section] = []
            continue
        elif "TOTAL" in row_str:
            current_section = None
            continue
            
        if current_section:
            # Check length of raw row
            row_list = list(row.values)
            if len(row_list) > 1:
                name = str(row_list[1]).strip() if pd.notna(row_list[1]) else ""
                if name and not name.startswith("Additional") and name != "MANUFACTURERS" and name != "AFFILIATES":
                    sections_rows[current_section].append(row_list)

    all_companies = []
    
    # Process items matching target scopes
    # 1. Manufacturers
    for row in sections_rows.get("MANUFACTURERS", []):
        all_companies.append((row, "Manufacturers"))
        
    # 2. Select Associates (Tech support)
    target_associates = ["Xemelgo", "Retrocausal, Inc.", "Kanoa", "LOOPR AI, Inc."]
    for row in sections_rows.get("ASSOCIATES", []):
        raw_name = str(row[1]) if pd.notna(row[1]) else ""
        name = clean_company_name(raw_name)
        if any(target.lower() in name.lower() for target in target_associates):
            all_companies.append((row, "Industrial Technology"))
            
    # 3. Select Cannabis (Equipment / Labs)
    target_cannabis = ["Root Sciences", "Open Source Steel", "Yakima Machine", "405 Labs"]
    for row in sections_rows.get("CANNABIS", []):
        raw_name = str(row[1]) if pd.notna(row[1]) else ""
        name = clean_company_name(raw_name)
        if any(target.lower() in name.lower() for target in target_cannabis):
            all_companies.append((row, "Manufacturers"))

    processed_data = []
    random.seed(42)  # For reproducible jitter

    for row, section in all_companies:
        # Standard columns offset: Col 1 is empty, Col 2 is Name, etc.
        raw_name = str(row[1]) if pd.notna(row[1]) else ""
        company_name = clean_company_name(raw_name)
        website = str(row[3]).strip() if pd.notna(row[3]) else ""
        address = str(row[9]).strip() if pd.notna(row[9]) else ""
        city_raw = str(row[10]).strip() if pd.notna(row[10]) else ""
        zip_code = str(row[11]).strip() if pd.notna(row[11]) else ""
        
        contact_name = str(row[5]).strip() if pd.notna(row[5]) else ""
        contact_title = str(row[6]).strip() if pd.notna(row[6]) else ""
        contact_email = str(row[7]).strip() if pd.notna(row[7]) else ""
        contact_phone = str(row[8]).strip() if pd.notna(row[8]) else ""
        
        city = clean_city_name(city_raw)
        
        # Geocode lookup
        lat, lon = 0.0, 0.0
        if city in COORDINATES:
            lat, lon = COORDINATES[city]
            
        track_info = classify_company(company_name, section)
        capabilities, industries_served = extract_general_capabilities(track_info["track"], track_info)
        
        # Add slight jitter for overlapping markers in cities
        lat_jitter = lat + random.uniform(-0.006, 0.006) if lat != 0.0 else 0.0
        lon_jitter = lon + random.uniform(-0.006, 0.006) if lon != 0.0 else 0.0

        item = {
            "company_name": company_name,
            "raw_name": raw_name,
            "website": website,
            "address": address,
            "city": city,
            "zip": zip_code,
            "latitude": lat,
            "longitude": lon,
            "lat_jittered": lat_jitter,
            "lon_jittered": lon_jitter,
            "section": section,
            "track": track_info["track"],
            "capabilities": capabilities,
            "industries_served": industries_served,
            "excess_capacity_flag": track_info["excess_capacity_flag"],
            "shared_capacity": track_info["shared_capacity"],
            "contact_name": contact_name,
            "contact_title": contact_title,
            "contact_email": contact_email,
            "contact_phone": contact_phone,
            # Helper lists for easy pandas access
            "machinery": track_info.get("machinery_types", []) if track_info["track"] == "Physical Production" else [],
            "materials": track_info.get("materials", []) if track_info["track"] == "Physical Production" else [],
            "certifications": track_info.get("certifications", []) if track_info["track"] == "Physical Production" else [],
            "solutions": track_info.get("solutions", []) if track_info["track"] == "Technology & Automation" else [],
            "resolved_pain_points": track_info.get("resolved_pain_points", []) if track_info["track"] == "Technology & Automation" else []
        }
        processed_data.append(item)
        
    return pd.DataFrame(processed_data)

# Load the data dynamically from Sheets
df_raw = load_and_process_data()

if not df_raw.empty:
    # ------------------ SIDEBAR FILTERS ------------------
    st.sidebar.markdown("# Match Engine Controls")
    
    if st.sidebar.button("Clear All Filters"):
        st.rerun()

    st.sidebar.markdown("---")

    # 1. Operational Pain-Point Matcher
    st.sidebar.markdown("### 🔍 Match by Shop Floor Pain Point")
    selected_pain = st.sidebar.selectbox(
        "Select your bottleneck / pain point:",
        options=["None"] + list(PAIN_POINT_TAXONOMY.keys()),
        index=0
    )

    # 2. Track Filter
    st.sidebar.markdown("### 📊 Membership Track")
    selected_tracks = st.sidebar.multiselect(
        "Filter by classification:",
        options=["Physical Production", "Technology & Automation"],
        default=["Physical Production", "Technology & Automation"]
    )

    # 3. Capacity Filter
    st.sidebar.markdown("### ⚡ Resource Sharing")
    show_open_capacity = st.sidebar.toggle("Show Shared/Open Capacity Only", value=False)

    # 4. Track A SPECIFIC FILTERS
    st.sidebar.markdown("### 🔧 Track A (Production Filters)")
    
    # Extract unique machinery types
    all_machinery = set()
    for item in df_raw['machinery']:
        for m in item:
            all_machinery.add(m)
    selected_machinery = st.sidebar.multiselect(
        "Machinery Types",
        options=sorted(list(all_machinery)),
        default=[]
    )

    # Extract unique materials
    all_materials = set()
    for item in df_raw['materials']:
        for mat in item:
            all_materials.add(mat)
    selected_materials = st.sidebar.multiselect(
        "Material Capabilities",
        options=sorted(list(all_materials)),
        default=[]
    )

    # Extract unique certs
    all_certs = set()
    for item in df_raw['certifications']:
        for c in item:
            all_certs.add(c)
    selected_certs = st.sidebar.multiselect(
        "Compliance & Certifications",
        options=sorted(list(all_certs)),
        default=[]
    )

    # 5. Track B SPECIFIC FILTERS
    st.sidebar.markdown("### 💻 Track B (Technology Filters)")
    
    # Extract unique solutions
    all_solutions = set()
    for item in df_raw['solutions']:
        for s in item:
            all_solutions.add(s)
    selected_solutions = st.sidebar.multiselect(
        "Technology Solutions",
        options=sorted(list(all_solutions)),
        default=[]
    )

    # City filter
    all_cities = sorted(list(df_raw['city'].unique()))
    selected_cities = st.sidebar.multiselect(
        "Headquarters Cities",
        options=all_cities,
        default=[]
    )

    # ------------------ FILTER PROCESSING LOGIC ------------------
    df_filtered = df_raw.copy()

    # Apply Pain Point mapping logic
    if selected_pain != "None":
        mapped_solutions = PAIN_POINT_TAXONOMY[selected_pain]
        # Filter to Track B tech providers who solve this pain point
        df_filtered = df_filtered[
            (df_filtered['track'] == 'Technology & Automation') & 
            (df_filtered['solutions'].apply(lambda x: any(s in x for s in mapped_solutions)))
        ]

    # Apply Track Filter
    if selected_tracks and selected_pain == "None":
        df_filtered = df_filtered[df_filtered['track'].isin(selected_tracks)]

    # Apply Open Capacity Toggle
    if show_open_capacity:
        df_filtered = df_filtered[df_filtered['excess_capacity_flag'] == True]

    # Track A Multi-select Filters
    if selected_machinery:
        df_filtered = df_filtered[df_filtered['machinery'].apply(
            lambda x: any(m in x for m in selected_machinery)
        )]
    if selected_materials:
        df_filtered = df_filtered[df_filtered['materials'].apply(
            lambda x: any(mat in x for mat in selected_materials)
        )]
    if selected_certs:
        df_filtered = df_filtered[df_filtered['certifications'].apply(
            lambda x: any(c in x for c in selected_certs)
        )]

    # Track B Multi-select Filters
    if selected_solutions:
        df_filtered = df_filtered[df_filtered['solutions'].apply(
            lambda x: any(s in x for s in selected_solutions)
        )]

    # City Filter
    if selected_cities:
        df_filtered = df_filtered[df_filtered['city'].isin(selected_cities)]

    # ------------------ HEADER SECTION ------------------
    st.markdown("""
        <div class="dashboard-header">
            <h1>CAMPS Supply Chain & Capability Match Engine</h1>
            <p>Advanced dual-track dashboard mapping capital equipment capacities and aligning operational shop-floor bottlenecks with technology partners.</p>
        </div>
    """, unsafe_allow_html=True)

    # ------------------ KPI AND VALUE CARDS ------------------
    total_open_assets = df_raw[df_raw['excess_capacity_flag'] == True]['shared_capacity'].apply(len).sum()
    total_tech_providers = len(df_raw[df_raw['track'] == 'Technology & Automation'])
    total_manufacturers = len(df_raw[df_raw['track'] == 'Physical Production'])

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Matches Found", f"{len(df_filtered)} members", f"{len(df_filtered) - len(df_raw)} from pool")
    with col2:
        st.metric("Ecosystem Partners", f"{len(df_raw)} total", f"{total_manufacturers} Mfg / {total_tech_providers} Tech")
    with col3:
        st.metric("Shared Machine Assets", f"{total_open_assets} open tools", "Available for Co-use")
    with col4:
        tech_ratio = (total_tech_providers / total_manufacturers) * 100 if total_manufacturers else 0
        st.metric("Tech Support Index", f"{tech_ratio:.1f}% ratio", "Integrators to Shops")

    # ------------------ SUPPLY CHAIN GAP ANALYSIS ------------------
    df_mfg_only = df_raw[df_raw['track'] == 'Physical Production']
    capability_counts = {}
    for caps in df_mfg_only['capabilities']:
        for cap in caps:
            capability_counts[cap] = capability_counts.get(cap, 0) + 1

    total_mfg = len(df_mfg_only)
    sorted_caps = sorted(capability_counts.items(), key=lambda x: x[1])

    # Extract the lowest represented capabilities
    gaps = []
    for cap, count in sorted_caps[:3]:
        pct = (count / total_mfg) * 100 if total_mfg else 0
        gaps.append((cap, count, pct))

    st.markdown("### ⚠️ Supply Chain Vulnerability & Capacity Alerts")
    gap_cols = st.columns(3)
    for idx, (cap, count, pct) in enumerate(gaps):
        with gap_cols[idx]:
            card_class = "danger" if pct < 10 else "warning"
            st.markdown(f"""
                <div class="kpi-card {card_class}">
                    <div class="kpi-title">Critical Gap {idx+1}</div>
                    <div class="kpi-value">{cap}</div>
                    <div class="kpi-desc">Only <b>{count}</b> members ({pct:.1f}% of production track) possess this capability.</div>
                </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ------------------ WORKSPACE TABS ------------------
    tab1, tab2, tab3, tab4 = st.tabs(["🗺️ Interactive Map", "🔌 Solution & Pain Point Matrix", "♻️ Shared / Excess Capacity Directory", "🔍 Search Directory"])

    with tab1:
        st.markdown("#### Geographic Match Workspace")
        st.write("Visualizing members across Washington State. Hover over markers to see capabilities and open shifts.")

        df_map = df_filtered[df_filtered['latitude'] != 0.0].copy()

        if not df_map.empty:
            # Color code points based on capacity status and classification track
            def get_point_color(row):
                if row['excess_capacity_flag']:
                    return [245, 158, 11, 230]  # Amber/Gold
                elif row['track'] == 'Physical Production':
                    return [0, 240, 255, 180]   # Neon Cyan
                else:
                    return [112, 0, 255, 200]   # Deep Purple

            df_map['color'] = df_map.apply(get_point_color, axis=1)
            
            # Map tooltips details
            def make_tooltip_text(row):
                shared_text = ""
                if row['excess_capacity_flag']:
                    shared_text = "<br/>⚠️ <b>OPEN CAPACITY AVAILABLE:</b> " + ", ".join([item['equipment'] for item in row['shared_capacity']])
                    
                if row['track'] == 'Physical Production':
                    track_details = f"<br/><b>Machinery:</b> {', '.join(row['machinery'])}<br/><b>Certs:</b> {', '.join(row['certifications'])}"
                else:
                    track_details = f"<br/><b>Solutions:</b> {', '.join(row['solutions'])}<br/><b>Pain Points Mapped:</b> {', '.join(row['resolved_pain_points'])}"

                return f"<b>{row['company_name']}</b> ({row['city']}){shared_text}{track_details}"

            df_map['tooltip_desc'] = df_map.apply(make_tooltip_text, axis=1)

            view_state = pdk.ViewState(
                latitude=df_map['latitude'].mean(),
                longitude=df_map['longitude'].mean(),
                zoom=7.5,
                pitch=30
            )

            scatterplot_layer = pdk.Layer(
                "ScatterplotLayer",
                data=df_map,
                get_position=["lon_jittered", "lat_jittered"],
                get_color="color",
                get_radius=2000,
                pickable=True,
                auto_highlight=True
            )

            r = pdk.Deck(
                layers=[scatterplot_layer],
                initial_view_state=view_state,
                map_provider="carto",
                map_style="dark",
                tooltip={
                    "html": "{tooltip_desc}<br/><br/><b>Contact:</b> {contact_name}<br/><b>Email:</b> {contact_email}",
                    "style": {"backgroundColor": "#1E293B", "color": "#F8FAFC", "border": "1px solid #334155", "fontSize": "12px"}
                }
            )

            st.pydeck_chart(r)
            
            # Map legend
            st.markdown("""
                <div style="display: flex; gap: 20px; align-items: center; justify-content: center; background-color: #1E293B; padding: 10px; border-radius: 6px; border: 1px solid #334155;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 14px; height: 14px; background-color: #00F0FF; border-radius: 50%;"></div>
                        <span style="font-size: 0.85rem; color: #E2E8F0; font-weight: 500;">Track A (Physical Production)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 14px; height: 14px; background-color: #7000FF; border-radius: 50%;"></div>
                        <span style="font-size: 0.85rem; color: #E2E8F0; font-weight: 500;">Track B (Technology & Automation)</span>
                    </div>
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <div style="width: 14px; height: 14px; background-color: #F59E0B; border-radius: 50%;"></div>
                        <span style="font-size: 0.85rem; color: #E2E8F0; font-weight: 500;">⚠️ Open / Shared Machinery Capacity</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.warning("No companies matched the current filters.")

    with tab2:
        st.markdown("#### Solution & Pain Point Matrix")
        st.write("Mapping how Track B Technology partners resolve specific operational pain points.")

        df_tech = df_filtered[df_filtered['track'] == 'Technology & Automation']
        
        if not df_tech.empty:
            matrix_data = []
            for idx, row in df_tech.iterrows():
                row_data = {
                    "Technology Partner": row["company_name"],
                    "HQ City": row["city"],
                    "Key Solutions": ", ".join(row["solutions"])
                }
                for p in PAIN_POINT_TAXONOMY.keys():
                    resolved = False
                    for sol in PAIN_POINT_TAXONOMY[p]:
                        if sol in row["solutions"]:
                            resolved = True
                    row_data[p] = "✓ Resolves" if resolved else ""
                matrix_data.append(row_data)
                
            df_matrix = pd.DataFrame(matrix_data)
            st.dataframe(df_matrix, use_container_width=True, height=450)
        else:
            st.warning("No Technology & Automation partners match the current filters.")

    with tab3:
        st.markdown("#### ♻️ Shared & Excess Capital Equipment Directory")
        st.write("Browse specialized manufacturing equipment and testing resources shared by members to prevent redundant capital expenditures.")
        
        df_capacity = df_filtered[df_filtered['excess_capacity_flag'] == True]
        
        if not df_capacity.empty:
            for idx, row in df_capacity.iterrows():
                st.markdown(f"""
                    <div style="background-color: #1E293B; border: 1px solid #334155; border-left: 4px solid #F59E0B; padding: 15px; border-radius: 6px; margin-bottom: 15px;">
                        <div style="display: flex; justify-content: space-between; align-items: center;">
                            <span style="font-size: 1.1rem; font-weight: 700; color: #F8FAFC;">{row['company_name']}</span>
                            <span class="capacity-badge">OPEN CAPACITY ACTIVE</span>
                        </div>
                        <div style="margin-top: 5px; color: #94A3B8; font-size: 0.85rem;">City: {row['city']} | Certifications: {', '.join(row['certifications'])}</div>
                        <div style="margin-top: 10px;">
                            <b style="color: #F59E0B;">Shared Equipment / Resources:</b>
                            <table style="width: 100%; border-collapse: collapse; margin-top: 5px; font-size: 0.9rem;">
                                <tr style="border-bottom: 1px solid #334155; text-align: left; color: #E2E8F0;">
                                    <th style="padding: 5px 0;">Equipment Name</th>
                                    <th>Weekly Shift Window</th>
                                    <th>Description / Open Usage</th>
                                </tr>
                                {"".join([f'<tr style="color: #CBD5E1;"><td style="padding: 5px 0; font-weight:600;">{item["equipment"]}</td><td>{item["shift_availability"]}</td><td>{item["description"]}</td></tr>' for item in row['shared_capacity']])}
                            </table>
                        </div>
                        <div style="margin-top: 12px; border-top: 1px solid #334155; padding-top: 10px; display: flex; justify-content: space-between; font-size: 0.85rem; color: #94A3B8;">
                            <span>👤 Contact: <b>{row['contact_name']}</b> ({row['contact_title']})</span>
                            <span>✉️ {row['contact_email']} | 📞 {row['contact_phone']}</span>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No members with open machine capacity matched the current filters.")

    with tab4:
        st.markdown("#### Search Match Directory")
        
        search_query = st.text_input("Search members by name, machinery type, certification, or pain point...", value="")
        
        df_search = df_filtered.copy()
        if search_query:
            q = search_query.lower()
            df_search = df_search[df_search.apply(
                lambda row: q in row['company_name'].lower() or 
                            q in str(row['machinery']).lower() or
                            q in str(row['materials']).lower() or
                            q in str(row['certifications']).lower() or
                            q in str(row['solutions']).lower() or
                            q in str(row['resolved_pain_points']).lower(),
                axis=1
            )]
            
        st.write(f"Showing {len(df_search)} matched profiles")
        
        for idx, row in df_search.iterrows():
            badge_html = ""
            if row['excess_capacity_flag']:
                badge_html = '<span class="capacity-badge" style="margin-left: 8px;">OPEN CAPACITY</span>'
                
            track_badge = ""
            if row['track'] == 'Physical Production':
                track_badge = '<span class="prod-badge">PRODUCTION TRACK</span>'
            else:
                track_badge = '<span class="tech-badge">TECH TRACK</span>'

            with st.expander(f"{row['company_name']} — {row['city']} ({row['track']})"):
                col_left, col_right = st.columns(2)
                
                with col_left:
                    st.markdown(f"**Track Class:** {track_badge} {badge_html}", unsafe_allow_html=True)
                    st.write(f"**Website:** [{row['website']}]({row['website']})")
                    st.write(f"**Address:** {row['address']}, {row['city']}, WA {row['zip']}")
                    
                    if row['track'] == 'Physical Production':
                        st.write(f"**Machinery & Tools:** {', '.join(row['machinery'])}")
                        st.write(f"**Materials Processed:** {', '.join(row['materials'])}")
                        st.write(f"**Certifications:** {', '.join(row['certifications'])}")
                    else:
                        st.write(f"**Technology Solutions:** {', '.join(row['solutions'])}")
                        st.write(f"**Resolved Bottlenecks:** {', '.join(row['resolved_pain_points'])}")
                    
                with col_right:
                    st.markdown("**Primary Contact Details:**")
                    if row['contact_name']:
                        st.write(f"👤 {row['contact_name']} ({row['contact_title']})")
                        st.write(f"✉️ {row['contact_email']}")
                        st.write(f"📞 {row['contact_phone']}")
                    else:
                        st.write("No direct contact details registered.")
                
                if row['excess_capacity_flag']:
                    st.markdown("---")
                    st.markdown("<b style='color: #F59E0B;'>Shared Capacity Details:</b>", unsafe_allow_html=True)
                    for item in row['shared_capacity']:
                        st.write(f"• **{item['equipment']}** ({item['shift_availability']}): {item['description']}")

                st.markdown(f"""
                    <div style="font-size: 0.75rem; color: #64748B; margin-top: 10px;">
                        Data Ingestion: Google Sheets Live Sync | Source Track: {row['track']}
                    </div>
                """, unsafe_allow_html=True)

else:
    st.error("Ingestion failed. Unable to fetch and process Google Sheets data.")
