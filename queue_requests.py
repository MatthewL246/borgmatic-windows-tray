"""
This module contains the classes for requests that are exchanged in the queues between the systray menu and the
background backup thread.
"""

from configuration import BackupConfiguration


class StartBackup:
    """
    A request to start a backup for a backup config.
    """

    def __init__(self, config: BackupConfiguration, is_scheduled: bool = False) -> None:
        self.config = config
        self.is_scheduled = is_scheduled


class StartPostBackup:
    """
    A request to start post-backup tasks for a backup config.
    """

    def __init__(self, config: BackupConfiguration, is_scheduled: bool = False) -> None:
        self.config = config
        self.is_scheduled = is_scheduled


class CancelBackup:
    """
    A request to cancel a backup for a backup config.
    """

    def __init__(self, config: BackupConfiguration) -> None:
        self.config = config


class CancelPostBackup:
    """
    A request to cancel post-backup tasks for a backup config.
    """

    def __init__(self, config: BackupConfiguration) -> None:
        self.config = config


class EnableScheduledBackups:
    """
    A request to enable scheduled backups for a backup config.
    """

    def __init__(self, config: BackupConfiguration) -> None:
        self.config = config


class DisableScheduledBackups:
    """
    A request to disable scheduled backups for a backup config.
    """

    def __init__(self, config: BackupConfiguration) -> None:
        self.config = config


class AnalyzeLogs:
    """
    A request to analyze logs for a backup config and open them in the editor.
    """

    def __init__(self, config: BackupConfiguration, editor: str) -> None:
        self.config = config
        self.editor = editor


class DiffLastBackups:
    """
    A request to compare the 2 most recent backups for a backup config.
    """

    def __init__(self, config: BackupConfiguration, editor: str) -> None:
        self.config = config
        self.editor = editor


class UpdateSystray:
    """
    A request to update the systray icon hover text and/or icon.
    """

    def __init__(self, hover_text: str | None = None, icon: str | None = None) -> None:
        self.hover_text = hover_text
        self.icon = icon


class Exit:
    """
    A request to exit the thread.
    """
