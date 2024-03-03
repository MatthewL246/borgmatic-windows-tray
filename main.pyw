"""
This module contains the main entry point for the backup system.
"""

import os
import sys
from pathlib import Path
from queue import Queue

from backups import BackgroundBackupThread
from configuration import BasicBackupConfiguration, Configuration
from systray import BorgmaticSystray


def main() -> None:
    """
    The main entry point for the backup system. It sets up the configuration and queues, and it starts the systray icon
    and background backup thread.
    """

    # Set up backup system configuration
    appdata_path = os.getenv("APPDATA")
    if not appdata_path:
        raise EnvironmentError("APPDATA environment variable is not defined")

    data_dir = Path(appdata_path) / "borgmatic-windows-tray"
    config_dir = data_dir / "config"
    logs_dir = data_dir / "logs"
    reports_dir = data_dir / "reports"

    config_dir.mkdir(parents=True, exist_ok=True)
    logs_dir.mkdir(parents=True, exist_ok=True)
    reports_dir.mkdir(parents=True, exist_ok=True)

    main_log_file = logs_dir / "borgmatic-windows-tray.log"

    # Edit the following lines to edit the backup configurations
    wsl_backups = BasicBackupConfiguration("WSL", "wsl.ico", "Ubuntu", 2, "Ubuntu-WSL1", 6)
    windows_backups = BasicBackupConfiguration("Windows", "windows.ico", "Ubuntu-WSL1", 2, "Ubuntu-WSL1", 6)
    main_configuration = Configuration(
        "notepad.exe", config_dir, logs_dir, reports_dir, main_log_file, [wsl_backups, windows_backups]
    )

    # If the script is running without a console by using pythonw.exe, sys.stdout is None
    if sys.stdout is None:
        sys.stdout = open(main_log_file, "a", encoding="utf-8")
        sys.stderr = sys.stdout

    systray_to_backups = Queue()
    backups_to_systray = Queue()
    backup_thread = BackgroundBackupThread(systray_to_backups, backups_to_systray)
    systray = BorgmaticSystray(main_configuration, backups_to_systray, systray_to_backups)

    backup_thread.start()
    systray.start()

    backup_thread.join()


main()
