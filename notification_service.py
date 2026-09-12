from PySide6.QtWidgets import QSystemTrayIcon

class NotificationService:
    def __init__(self, tray):
        self.tray = tray

    def _show(self, title, message, icon):
        if (
            self.tray
            and not self.tray.icon().isNull()
            and QSystemTrayIcon.isSystemTrayAvailable()
        ):
            self.tray.showMessage(title, message, icon, 5000)

    def success(self, title, message):
        self._show(title, message, QSystemTrayIcon.Information)

    def warning(self, title, message):
        self._show(title, message, QSystemTrayIcon.Warning)

    def error(self, title, message):
        self._show(title, message, QSystemTrayIcon.Critical)
