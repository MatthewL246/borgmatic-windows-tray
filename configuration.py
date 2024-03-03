"""
This module contains classes for backup system configuration.
"""

from pathlib import Path


class BackupConfiguration:
    """
    Configuration for a single backup.

    Instance variables:
        name (str): The name of the configuration shown in the systray menu.
        icon (str): The filename of the icon in the icons directory that represents this configuration.
        config_file (Path): The configuration file passed to borgmatic.
        wsl_distro (str): The WSL distro to run the backup in (if you are backing up Windows files using /mnt/...\
            paths, using a WSL1 distro will be faster).
        backup_schedule_hours (int): Automatically schedule a backup every x hours.
        log_file (Path): The log file for borgmatic verbose output.
        report_files (Path): The file timing reports for the "Analyze logs" option.
        report_paths (Path): The path timing reports.
        report_excluded (Path): The excluded paths reports.
        report_errors (Path): The error reports.
        diff_file (Path): A diff between the 2 most-recent backups.
        post_backup_script (Path): The script to run after the backup.
        post_backup_wsl_distro (str): The WSL distro to run the post-backup script in (again, WSL1 is faster for\
            /mnt/... paths).
        post_backup_schedule_hours (int): Automatically schedule post-backup tasks every x hours.
        backup_line_count_file (Path): The path to store the number of lines that were in the last backup's logging\
            output, used to estimate backup progress.
    """

    def __init__(
        self,
        name: str,
        icon: str,
        config_file: Path,
        wsl_distro: str,
        backup_schedule_hours: int,
        log_file: Path,
        report_files: Path,
        report_paths: Path,
        report_excluded: Path,
        report_errors: Path,
        diff_file: Path,
        post_backup_script: Path,
        post_backup_wsl_distro: str,
        post_backup_schedule_hours: int,
        backup_line_count_file: Path,
    ) -> None:
        self.name = name
        self.icon = icon
        self.config_file = config_file
        self.wsl_distro = wsl_distro
        self.backup_schedule_hours = backup_schedule_hours
        self.log_file = log_file
        self.report_files = report_files
        self.report_paths = report_paths
        self.report_excluded = report_excluded
        self.report_errors = report_errors
        self.diff_file = diff_file
        self.post_backup_script = post_backup_script
        self.post_backup_wsl_distro = post_backup_wsl_distro
        self.post_backup_schedule_hours = post_backup_schedule_hours
        self.backup_line_count_file = backup_line_count_file


class BasicBackupConfiguration:
    """
    Basic configuration for a single backup (like BackupConfiguration without file paths).

    Instance variables:
        name (str): The name of the configuration shown in the systray menu.
        icon (str): The filename of the icon in the icons directory that represents this configuration.
        wsl_distro (str): The WSL distro to run the backup in (if you are backing up Windows files using /mnt/...
            paths, using a WSL1 distro will be faster).
        backup_schedule_hours (int): Automatically schedule a backup every x hours.
        post_backup_wsl_distro (str): The WSL distro to run the post-backup script in (again, WSL1 is faster for
            /mnt/... paths).
        post_backup_schedule_hours (int): Automatically schedule post-backup tasks every x hours.
    """

    def __init__(
        self,
        name: str,
        icon: str,
        wsl_distro: str,
        backup_schedule_hours: int,
        post_backup_wsl_distro: str,
        post_backup_schedule_hours: int,
    ) -> None:
        self.name = name
        self.icon = icon
        self.wsl_distro = wsl_distro
        self.backup_schedule_hours = backup_schedule_hours
        self.post_backup_wsl_distro = post_backup_wsl_distro
        self.post_backup_schedule_hours = post_backup_schedule_hours


class Configuration:
    """
    Configuration for the backup system.

    Instance variables:
        editor (str): The editor to open reports with.
        config_dir (Path): The directory that stores Borgmatic configuration files.
        logs_dir (Path): The directory to store Borgmatic logs in.
        reports_dir (Path): The directory to store log analysis reports in.
        log_file (Path): The main log file for backup thread output and Python errors.
        backup_configurations (list[BackupConfiguration]): A list of backup configurations to use, each will be shown in
            the systray menu and run on a schedule.
    """

    def __init__(
        self,
        editor: str,
        config_dir: Path,
        logs_dir: Path,
        reports_dir: Path,
        log_file: Path,
        backup_configurations: list[BackupConfiguration | BasicBackupConfiguration],
    ) -> None:
        self.editor = editor
        self.config_dir = config_dir
        self.logs_dir = logs_dir
        self.reports_dir = reports_dir
        self.log_file = log_file

        self.backup_configurations: list[BackupConfiguration] = []
        for configuration in backup_configurations:
            if isinstance(configuration, BackupConfiguration):
                self.backup_configurations.append(configuration)
                continue

            # Use BasicBackupConfiguration to create a BackupConfiguration with generated file paths
            name = configuration.name.lower()
            full_backup_configuration = BackupConfiguration(
                configuration.name,
                configuration.icon,
                config_dir / f"borgmatic-{name}.yml",
                configuration.wsl_distro,
                configuration.backup_schedule_hours,
                logs_dir / f"borgmatic-{name}.log",
                reports_dir / f"{name}-files.txt",
                reports_dir / f"{name}-paths.txt",
                reports_dir / f"{name}-excluded.txt",
                reports_dir / f"{name}-errors.txt",
                reports_dir / f"{name}-diff.txt",
                config_dir / f"post-backup-{name}.sh",
                configuration.post_backup_wsl_distro,
                configuration.post_backup_schedule_hours,
                logs_dir / f"lines-{name}.txt",
            )
            self.backup_configurations.append(full_backup_configuration)
