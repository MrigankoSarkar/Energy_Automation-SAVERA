# -*- mode: python ; coding: utf-8 -*-
"""
EnergyAutomation — PyInstaller Debug Specification (Console Enabled)
=====================================================================
Identical to production specification, but enables console window for
real-time diagnostic logging and error inspection during testing.
"""

from pathlib import Path
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path('.').resolve()

datas = [
    ('assets', 'assets'),
    ('config/settings.template.json', 'config'),
    ('config/services.json', 'config'),
    ('ui/index.html', 'ui'),
    ('ui/styles.css', 'ui'),
    ('ui/app.js', 'ui'),
    ('templates/Sample_BI_Analysis_Report.xlsx', 'templates'),
]

hiddenimports = [
    'PySide6',
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'qfluentwidgets',
    'qframelesswindow',
    'websocket',
    'engineio.async_drivers.threading',
    'socketio',
    'engineio',
    'sqlite3',
    'openpyxl',
    'fitz',
    'pymupdf',
    'fastapi',
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'starlette',
    'pydantic',
    'googleapiclient',
    'googleapiclient.discovery',
    'google.auth',
    'google.oauth2.credentials',
    'google_auth_oauthlib.flow',
    'app.version',
    'app.paths',
    'app.bootstrap.qt_app',
    'app.bootstrap.application',
    'app.bootstrap.dependencies',
    'ui.dashboard',
    'ui.design_system',
    'ui.data_service',
    'ui.notification_service',
    'ui.dialogs.guided_tour',
    'ui.dialogs.setup_wizard',
]

hiddenimports += collect_submodules('qfluentwidgets')
hiddenimports += [
    sub for sub in collect_submodules('qframelesswindow')
    if not sub.startswith('qframelesswindow.mac') and not sub.startswith('qframelesswindow.linux')
]

excludes = [
    'pytest',
    'pytest_cov',
    'black',
    'ruff',
    'tkinter',
    'IPython',
    'notebook',
]

a = Analysis(
    ['main.py'],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=None,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None,
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EnergyAutomation_Debug',
    debug=True,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=True,  # Console enabled for debugging
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(PROJECT_ROOT / 'assets' / 'app.ico'),
    version=str(PROJECT_ROOT / 'installer' / 'file_version_info.txt'),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='EnergyAutomation_Debug',
)
