"""
Industrial Plant Energy Topology Service for Savera MS Manufacturing Plant.
Maps physical meters to production areas, calculates zone-level consumption,
and evaluates operational baselines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class PlantZone:
    zone_id: str
    name: str
    section: str
    building: str
    nominal_kwh: float
    description: str
    meters: List[str] = field(default_factory=list)


# Production areas defined for Savera MS manufacturing facility
PLANT_ZONES: Dict[str, PlantZone] = {
    "plating": PlantZone(
        zone_id="plating",
        name="Surface Treatment & Plating Plant",
        section="Shop Floor A",
        building="Bldg 1 - Chemical Processing",
        nominal_kwh=160.0,
        description="Automated and manual nickel/chrome electroplating lines with cooling chiller.",
        meters=[
            "Chiller Plating Plant",
            "New Plating Plant",
            "Old Plating Plant",
            "DIPP_PT_PANEĹ",
            "DIPP_PT_PANEL",
        ],
    ),
    "coating": PlantZone(
        zone_id="coating",
        name="Finishing & Powder Coating Plant",
        section="Shop Floor B",
        building="Bldg 2 - Finishing",
        nominal_kwh=2100.0,
        description="Continuous conveyorized powder coating booth and infrared curing oven.",
        meters=["Powder Coating"],
    ),
    "fabrication": PlantZone(
        zone_id="fabrication",
        name="Press & Fabrication Line",
        section="Shop Floor C",
        building="Bldg 3 - Metal Forming",
        nominal_kwh=1250.0,
        description="Hydraulic/mechanical stamping presses, rigga welding lines, and annealing furnace.",
        meters=[
            "Press & Fabrication",
            "Rigga Line Fabrication",
            "Annealing Furnance",
            "Annealing Furnace",
            "RASKOG",
        ],
    ),
    "compressors": PlantZone(
        zone_id="compressors",
        name="Compressed Air Generation Substation",
        section="Utility Block 1",
        building="Bldg 4 - Utilities",
        nominal_kwh=1850.0,
        description="Centralized rotary screw air compressor plant (Kaeser ASD 60, ELGI E18, ELGI E45).",
        meters=[
            "Kaeser ASD 60 40HP Air Compressor",
            "ELGI E18 25HP Air Compressor",
            "ELGI E45 60HP Air Compressor",
        ],
    ),
    "water_treatment": PlantZone(
        zone_id="water_treatment",
        name="RO & DM Water Treatment Facility",
        section="Utility Block 2",
        building="Bldg 4 - Utilities",
        nominal_kwh=430.0,
        description="Reverse Osmosis (RO) and Demineralization (DM) high-purity process water plant.",
        meters=["RO Plant", "DM Plant"],
    ),
    "packaging": PlantZone(
        zone_id="packaging",
        name="Packaging & Stitching Line",
        section="Shop Floor D",
        building="Bldg 5 - Logistics",
        nominal_kwh=500.0,
        description="Final component packaging, sealing, and automated box stitching lines.",
        meters=["Packing & Stiching Line", "Packing & Stitching Line"],
    ),
    "main_power": PlantZone(
        zone_id="main_power",
        name="Main Power Substation & Incomer",
        section="Substation",
        building="Bldg 0 - Electrical Yard",
        nominal_kwh=3200.0,
        description="Primary 415V low-tension distribution panel and main incomer.",
        meters=["Old LT Panel Main Incomer", "LT Incomer", "Main Incomer"],
    ),
}


class PlantTopologyService:
    """
    Service responsible for mapping meter readings to production zones,
    calculating aggregate metrics, and identifying status levels.
    """

    def __init__(self, zones: Optional[Dict[str, PlantZone]] = None) -> None:
        self.zones = zones or PLANT_ZONES

    def find_zone_for_meter(self, meter_name: str) -> Optional[PlantZone]:
        """Find the corresponding plant zone for a meter name using fuzzy matching."""
        name_clean = meter_name.strip().lower()
        for zone in self.zones.values():
            for m in zone.meters:
                if m.lower() in name_clean or name_clean in m.lower():
                    return zone
        return None

    def calculate_topology(
        self,
        readings: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Aggregate meter readings by production zone.
        Returns detailed zone-level metrics, status badges, and plant total.
        """
        zone_data: Dict[str, Dict[str, Any]] = {}

        # Initialize zones
        for zid, z in self.zones.items():
            zone_data[zid] = {
                "zone_id": zid,
                "name": z.name,
                "section": z.section,
                "building": z.building,
                "nominal_kwh": z.nominal_kwh,
                "description": z.description,
                "total_energy": 0.0,
                "active_meters_count": 0,
                "inactive_meters_count": 0,
                "meters": [],
                "status": "NORMAL",
                "percentage_of_total": 0.0,
            }

        unassigned_meters = []
        plant_total = 0.0

        for r in readings:
            m_name = str(r.get("meter_name", ""))
            val_raw = r.get("value") if "value" in r else r.get("active_energy")
            status_str = str(r.get("status", "OK")).upper()

            is_na = status_str in {"N/A", "NA"} or val_raw is None
            val = 0.0 if is_na else float(val_raw)

            if not is_na:
                plant_total += val

            zone = self.find_zone_for_meter(m_name)
            meter_entry = {
                "meter_name": m_name,
                "active_energy": None if is_na else round(val, 2),
                "status": "N/A" if is_na else "OK",
            }

            if zone:
                z_dict = zone_data[zone.zone_id]
                z_dict["meters"].append(meter_entry)
                if is_na:
                    z_dict["inactive_meters_count"] += 1
                else:
                    z_dict["active_meters_count"] += 1
                    z_dict["total_energy"] += val
            else:
                unassigned_meters.append(meter_entry)

        # Round values and evaluate statuses
        for z_dict in zone_data.values():
            tot = round(z_dict["total_energy"], 2)
            z_dict["total_energy"] = tot
            nominal = z_dict["nominal_kwh"]

            if plant_total > 0:
                z_dict["percentage_of_total"] = round((tot / plant_total) * 100, 1)

            if z_dict["active_meters_count"] == 0 and z_dict["inactive_meters_count"] > 0:
                z_dict["status"] = "INACTIVE"
            elif tot > nominal * 1.30:
                z_dict["status"] = "HIGH"
            elif tot > nominal * 1.15:
                z_dict["status"] = "WARNING"
            else:
                z_dict["status"] = "NORMAL"

        return {
            "plant_name": "Savera MS Manufacturing Facility",
            "plant_total_kwh": round(plant_total, 2),
            "zones": list(zone_data.values()),
            "unassigned_meters": unassigned_meters,
        }
