"""
Page views for EnergyAutomation Streamlit BI Dashboard.
"""

from streamlit_app.pages_views.executive_view import render_executive_view
from streamlit_app.pages_views.energy_trends import render_energy_trends_view
from streamlit_app.pages_views.meter_analysis import render_meter_analysis_view
from streamlit_app.pages_views.plant_areas import render_plant_areas_view
from streamlit_app.pages_views.data_quality import render_data_quality_view
from streamlit_app.pages_views.engineering_view import render_engineering_view
from streamlit_app.pages_views.about_view import render_about_view

__all__ = [
    "render_executive_view",
    "render_energy_trends_view",
    "render_meter_analysis_view",
    "render_plant_areas_view",
    "render_data_quality_view",
    "render_engineering_view",
    "render_about_view",
]
