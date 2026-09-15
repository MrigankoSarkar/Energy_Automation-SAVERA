# EnergyAutomation — User Guide: Plant Map & Meter Analysis

## 1. Plant Energy Topology Map
EnergyAutomation provides an interactive **Plant Energy Topology Map** inspired by industrial control centers and Google Maps spatial cards.

The map models the physical production facilities of **Savera MS** and groups all 18 facility meters into distinct operational zones.

### Savera MS Production Zones:
1. **Surface Treatment & Plating Plant (Shop Floor A)**:
   - *Equipment*: Chiller Plating Plant, New Plating Plant, Old Plating Plant, DIPP_PT_PANEL.
   - *Nominal Baseline*: ~160 kWh.
2. **Finishing & Powder Coating Plant (Shop Floor B)**:
   - *Equipment*: Powder Coating conveyorized booth and infrared curing oven.
   - *Nominal Baseline*: ~2,100 kWh.
3. **Press & Fabrication Line (Shop Floor C)**:
   - *Equipment*: Press & Fabrication stamping lines, Rigga Line welding, Annealing Furnace, RASKOG.
   - *Nominal Baseline*: ~1,250 kWh.
4. **Compressed Air Generation Substation (Utility Block 1)**:
   - *Equipment*: Kaeser ASD 60 40HP, ELGI E18 25HP, ELGI E45 60HP.
   - *Nominal Baseline*: ~1,850 kWh.
5. **RO & DM Water Treatment Facility (Utility Block 2)**:
   - *Equipment*: Reverse Osmosis (RO) Plant, Demineralization (DM) Plant.
   - *Nominal Baseline*: ~430 kWh.
6. **Packaging & Stitching Line (Shop Floor D)**:
   - *Equipment*: Packing & Stitching Line.
   - *Nominal Baseline*: ~500 kWh.
7. **Main Power Substation & Incomer (Bldg 0)**:
   - *Equipment*: Old LT Panel Main Incomer.
   - *Nominal Baseline*: ~3,200 kWh.

### Zone Status Levels:
- 🟢 **Normal**: Zone consumption is within nominal baseline limits (<= 115%).
- 🟡 **Warning**: Zone consumption exceeds baseline by 15% to 30%.
- 🔴 **High**: Zone consumption exceeds baseline by more than 30%.
- ⚪ **Inactive**: Meter readings are N/A (equipment offline or standby).

Click **Inspect** on any card to view the exact meter readings inside that production area.

---

## 2. Meter Analysis Table
Under **Meter Analysis**, operators can inspect all 18 facility meters:
- Filter meters instantly by typing into the filter box.
- Review rated power in kW and nominal baseline in kWh.
- Inspect real-time status (`OK` vs `N/A`).
- Identify top consumers by sorting the table by active energy consumption.
