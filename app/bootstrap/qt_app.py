"""
Qt application bootstrap for EnergyAutomation.

This module is responsible only for creating and starting the
desktop Qt application.

The actual application/window implementation belongs to the
Application class.
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from app.bootstrap.application import Application


def run_application() -> int:
    """
    Create and run the EnergyAutomation desktop application.

    Returns
    -------
    int
        Qt application exit code.
    """

    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    app.setApplicationName("EnergyAutomation")
    app.setOrganizationName("Savera MS")
    app.setApplicationDisplayName("EnergyAutomation")

    application = Application()

    # Keep a reference so Python does not garbage-collect
    # the application object while Qt's event loop is running.
    app._energy_automation_application = application

    if hasattr(application, "start"):
        application.start()

    elif hasattr(application, "show"):
        application.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(run_application())