"""
Interactive Plant Energy Topology Widget for Savera MS Manufacturing Plant.
Provides a Google Maps / industrial dashboard inspired visualization of plant areas,
consumption heat levels, and meter breakdowns.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


class ZoneDetailDialog(QDialog):
    """Detail drill-down dialog for an inspected production area."""

    def __init__(self, zone_info: Dict[str, Any], parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(f"Area Inspection — {zone_info.get('name')}")
        self.resize(600, 420)
        self._build_ui(zone_info)

    def _build_ui(self, z: Dict[str, Any]):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Info
        hdr_frame = QFrame()
        hdr_frame.setStyleSheet("background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px;")
        hdr_layout = QVBoxLayout(hdr_frame)

        title = QLabel(z.get("name", "Zone"))
        title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #0f172a;")
        hdr_layout.addWidget(title)

        loc = QLabel(f"Location: {z.get('section', '')} • {z.get('building', '')}")
        loc.setStyleSheet("color: #64748b; font-size: 9.5pt;")
        hdr_layout.addWidget(loc)

        desc = QLabel(z.get("description", ""))
        desc.setStyleSheet("color: #334155; font-size: 9pt; margin-top: 4px;")
        desc.setWordWrap(True)
        hdr_layout.addWidget(desc)

        layout.addWidget(hdr_frame)

        # Metrics row
        metrics_box = QHBoxLayout()
        tot_lbl = QLabel(f"Active Consumption: <b>{z.get('total_energy', 0.0):,.2f} kWh</b> ({z.get('percentage_of_total', 0.0)}% of plant)")
        metrics_box.addWidget(tot_lbl)
        metrics_box.addStretch()

        stat_badge = QLabel(f"Status: {z.get('status', 'NORMAL')}")
        color = "#16a34a" if z.get("status") == "NORMAL" else ("#d97706" if z.get("status") == "WARNING" else "#dc2626")
        stat_badge.setStyleSheet(f"background: {color}; color: white; padding: 4px 10px; border-radius: 12px; font-weight: 700;")
        metrics_box.addWidget(stat_badge)
        layout.addLayout(metrics_box)

        # Meters table
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(["Meter Name", "Active Energy (kWh)", "Status"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.setAlternatingRowColors(True)

        meters = z.get("meters", [])
        table.setRowCount(len(meters))
        for idx, m in enumerate(meters):
            table.setItem(idx, 0, QTableWidgetItem(m.get("meter_name", "")))
            val = m.get("active_energy")
            val_str = f"{val:,.2f}" if val is not None else "N/A"
            table.setItem(idx, 1, QTableWidgetItem(val_str))
            status_item = QTableWidgetItem(m.get("status", "OK"))
            if m.get("status") == "N/A":
                status_item.setForeground(Qt.gray)
            table.setItem(idx, 2, status_item)

        layout.addWidget(table)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close, alignment=Qt.AlignRight)


class PlantMapWidget(QWidget):
    """
    Industrial plant energy topology map showing all production areas
    with color-coded operational heatmaps and click-to-drill-down.
    """

    zone_selected = Signal(dict)

    def __init__(self, topology_service: Any = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.topology_service = topology_service
        self._last_topology_data: Dict[str, Any] = {}
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # Header toolbar
        toolbar = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("Savera MS — Plant Energy Topology Map")
        title.setStyleSheet("font-size: 13pt; font-weight: 700; color: #0f172a;")
        sub = QLabel("Abstract plant layout & production area energy distribution • Click any zone to inspect")
        sub.setStyleSheet("font-size: 9.5pt; color: #64748b;")
        title_box.addWidget(title)
        title_box.addWidget(sub)
        toolbar.addLayout(title_box)
        toolbar.addStretch()

        self.total_plant_label = QLabel("Plant Total: — kWh")
        self.total_plant_label.setStyleSheet("font-size: 11pt; font-weight: 700; color: #1e40af; background: #eff6ff; padding: 6px 14px; border-radius: 8px; border: 1px solid #bfdbfe;")
        toolbar.addWidget(self.total_plant_label)

        btn_refresh = QPushButton("Refresh Topology")
        btn_refresh.clicked.connect(self.refresh_view)
        toolbar.addWidget(btn_refresh)
        root.addLayout(toolbar)

        # Legend
        legend = QHBoxLayout()
        legend.addWidget(QLabel("Zone Status:"))
        legend.addWidget(self._create_legend_dot("#16a34a", "🟢 Normal (<= Baseline)"))
        legend.addWidget(self._create_legend_dot("#d97706", "🟡 Warning (> 115% Baseline)"))
        legend.addWidget(self._create_legend_dot("#dc2626", "🔴 High Consumption (> 130%)"))
        legend.addWidget(self._create_legend_dot("#94a3b8", "⚪ Inactive / Standby"))
        legend.addStretch()
        root.addLayout(legend)

        # Scrollable area for zone cards grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.grid = QGridLayout(container)
        self.grid.setSpacing(14)
        scroll.setWidget(container)

        root.addWidget(scroll, 1)

    @staticmethod
    def _create_legend_dot(color: str, label: str) -> QLabel:
        lbl = QLabel(label)
        lbl.setStyleSheet("font-size: 9pt; color: #475569; margin-right: 12px;")
        return lbl

    def update_data(self, readings: List[Dict[str, Any]]):
        """Update plant topology visualization from real meter readings."""
        if not self.topology_service:
            from app.services.analytics.plant_topology import PlantTopologyService
            self.topology_service = PlantTopologyService()

        self._last_topology_data = self.topology_service.calculate_topology(readings)
        self.render_topology(self._last_topology_data)

    def refresh_view(self):
        """Re-render current topology data."""
        if self._last_topology_data:
            self.render_topology(self._last_topology_data)

    def render_topology(self, topo: Dict[str, Any]):
        """Render all zone cards in the responsive grid."""
        # Clear existing cards
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        tot_kwh = topo.get("plant_total_kwh", 0.0)
        self.total_plant_label.setText(f"Plant Total: {tot_kwh:,.2f} kWh")

        zones = topo.get("zones", [])
        columns = 3

        for idx, z in enumerate(zones):
            card = self._create_zone_card(z)
            row = idx // columns
            col = idx % columns
            self.grid.addWidget(card, row, col)

    def _create_zone_card(self, z: Dict[str, Any]) -> QFrame:
        card = QFrame()
        card.setCursor(Qt.PointingHandCursor)
        stat = z.get("status", "NORMAL")

        border_color = (
            "#16a34a"
            if stat == "NORMAL"
            else (
                "#d97706"
                if stat == "WARNING"
                else ("#dc2626" if stat == "HIGH" else "#cbd5e1")
            )
        )
        bg_tint = (
            "#f0fdf4"
            if stat == "NORMAL"
            else (
                "#fffbeb"
                if stat == "WARNING"
                else ("#fef2f2" if stat == "HIGH" else "#f8fafc")
            )
        )

        card.setStyleSheet(f"""
            QFrame {{
                background: white;
                border: 1px solid #e2e8f0;
                border-left: 5px solid {border_color};
                border-radius: 10px;
                padding: 14px;
            }}
            QFrame:hover {{
                border-color: #2563eb;
                background: {bg_tint};
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(8)

        # Header with Name & Status Badge
        top_row = QHBoxLayout()
        name_lbl = QLabel(z.get("name", "Zone"))
        name_lbl.setStyleSheet("font-size: 10.5pt; font-weight: 700; color: #0f172a;")
        top_row.addWidget(name_lbl)
        top_row.addStretch()

        badge = QLabel(stat)
        badge.setStyleSheet(f"background: {border_color}; color: white; padding: 2px 8px; border-radius: 10px; font-size: 8pt; font-weight: 700;")
        top_row.addWidget(badge)
        layout.addLayout(top_row)

        loc_lbl = QLabel(f"{z.get('section')} • {z.get('building')}")
        loc_lbl.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        layout.addWidget(loc_lbl)

        # Consumption metric
        val_box = QHBoxLayout()
        kwh_lbl = QLabel(f"{z.get('total_energy', 0.0):,.2f} kWh")
        kwh_lbl.setStyleSheet("font-size: 15pt; font-weight: 700; color: #1e293b;")
        val_box.addWidget(kwh_lbl)
        val_box.addStretch()

        pct = z.get("percentage_of_total", 0.0)
        pct_lbl = QLabel(f"{pct}% of plant")
        pct_lbl.setStyleSheet("color: #2563eb; font-weight: 600; font-size: 9.5pt;")
        val_box.addWidget(pct_lbl)
        layout.addLayout(val_box)

        # Progress bar representing percentage of total
        progress = QProgressBar()
        progress.setRange(0, 100)
        progress.setValue(min(100, int(pct)))
        progress.setTextVisible(False)
        progress.setFixedHeight(6)
        progress.setStyleSheet(f"""
            QProgressBar {{ background: #f1f5f9; border-radius: 3px; border: none; }}
            QProgressBar::chunk {{ background: {border_color}; border-radius: 3px; }}
        """)
        layout.addWidget(progress)

        # Meters summary & inspect button
        bottom_row = QHBoxLayout()
        active_m = z.get("active_meters_count", 0)
        tot_m = len(z.get("meters", []))
        m_lbl = QLabel(f"{active_m}/{tot_m} active meters")
        m_lbl.setStyleSheet("color: #64748b; font-size: 8.5pt;")
        bottom_row.addWidget(m_lbl)
        bottom_row.addStretch()

        btn_inspect = QPushButton("Inspect")
        btn_inspect.setStyleSheet("padding: 2px 10px; font-size: 8.5pt; min-height: 24px;")
        btn_inspect.clicked.connect(lambda _, zone_dict=z: self._open_detail(zone_dict))
        bottom_row.addWidget(btn_inspect)
        layout.addLayout(bottom_row)

        return card

    def _open_detail(self, zone_info: Dict[str, Any]):
        dlg = ZoneDetailDialog(zone_info, self)
        dlg.exec()
