"""
This module contains the systray GUI for the backup system.
"""

import subprocess
import sys
from queue import Empty, Queue
from threading import Thread
from traceback import format_exc

from infi.systray import SysTrayIcon

import queue_requests as q_req
from configuration import Configuration


class BorgmaticSystray(SysTrayIcon):
    """
    The systray GUI frontend for the backup system. It communicates with the background backup thread using input and
    output queues.
    """

    def __init__(self, config: Configuration, input_queue: Queue, output_queue: Queue) -> None:
        self.config = config
        self.input_queue = input_queue
        self.output_queue = output_queue

        menu_options = []
        vorta_index = 0

        for backup_config in config.backup_configurations:
            menu_option = (
                f"{backup_config.name} backups",
                f"./icons/{backup_config.icon}",
                (
                    (
                        "Run backup now",
                        "./icons/backup.ico",
                        # lambda _ is used here because the systray instance is always the first argument of the menu
                        # option, which is unnecessary here
                        lambda _, config=backup_config: self.output_queue.put(q_req.StartBackup(config)),
                    ),
                    (
                        "Cancel backup",
                        None,
                        lambda _, config=backup_config: self.output_queue.put(q_req.CancelBackup(config)),
                    ),
                    (
                        "Run post-backup tasks",
                        "./icons/post-backup.ico",
                        lambda _, config=backup_config: self.output_queue.put(q_req.StartPostBackup(config)),
                    ),
                    (
                        "Cancel post-backup tasks",
                        None,
                        lambda _, config=backup_config: self.output_queue.put(q_req.CancelPostBackup(config)),
                    ),
                    (
                        "Enable scheduled backups",
                        "./icons/success.ico",
                        lambda _, config=backup_config: self.output_queue.put(q_req.EnableScheduledBackups(config)),
                    ),
                    (
                        "Disable scheduled backups",
                        "./icons/error.ico",
                        lambda _, config=backup_config: self.output_queue.put(q_req.DisableScheduledBackups(config)),
                    ),
                    (
                        "Edit backup config",
                        "./icons/logs.ico",
                        lambda _, config=backup_config: subprocess.Popen([self.config.editor, config.config_file]),
                    ),
                    (
                        "Analyze logs",
                        "./icons/analyze.ico",
                        lambda _, config=backup_config: self.output_queue.put(
                            q_req.AnalyzeLogs(config, self.config.editor)
                        ),
                    ),
                    (
                        "Diff the last 2 backups",
                        "./icons/logs.ico",
                        lambda _, config=backup_config: self.output_queue.put(
                            q_req.DiffLastBackups(config, self.config.editor)
                        ),
                    ),
                ),
            )
            menu_options.append(menu_option)
            vorta_index += len(menu_option[2]) + 1

        menu_options.extend(
            [
                (
                    "Open Vorta",
                    "./icons/drive.ico",
                    lambda _: subprocess.Popen(["wsl.exe", "PATH=~/.local/bin:$PATH", "vorta"]),
                ),
                (
                    "Open logs directory",
                    "./icons/explorer.ico",
                    lambda _: subprocess.Popen(["explorer.exe", self.config.logs_dir]),
                ),
                (
                    "Open terminal",
                    "./icons/terminal.ico",
                    lambda _: subprocess.Popen(
                        [
                            "wt.exe",
                            "-w",
                            "0",
                            "-d",
                            str(self.config.config_dir),
                            "wsl.exe",
                        ]
                    ),
                ),
                (
                    "View logs",
                    "./icons/logs.ico",
                    lambda _: subprocess.Popen([self.config.editor, self.config.log_file]),
                ),
            ]
        )

        super().__init__(
            "./icons/drive.ico",
            "Borgmatic backup (not yet run)",
            tuple(menu_options),
            default_menu_index=vorta_index,
            on_quit=lambda _: self.queue_exit(),
        )

    def queue_exit(self) -> None:
        """
        Request both the systray and background backup threads to exit.
        """

        self.input_queue.put(q_req.Exit())
        self.output_queue.put(q_req.Exit())

    def systray_update_thread(self) -> None:
        """
        Run in a loop in a separate thread and listens for requests to update the systray icon and hover text from the
        input queue.
        """

        while True:
            try:
                try:
                    queue_item = self.input_queue.get(timeout=1)
                except Empty:
                    continue

                match queue_item:
                    case q_req.UpdateSystray():
                        self.update(queue_item.icon, queue_item.hover_text)
                    case q_req.Exit():
                        self.queue_exit()
                        break
                    case _:
                        raise TypeError(f"Systray got unknown type in input queue: {type(queue_item)}")

            except Exception as ex:
                message = f"Error in systray: {ex}\n{format_exc()}"
                print(message)
                sys.stdout.flush()
                self.update("./icons/error.ico", message)

    def start(self) -> None:
        """
        Create the systray update thread and then starts displaying the systray icon.
        """

        systray_update_thread = Thread(target=self.systray_update_thread)
        systray_update_thread.start()

        # Enable scheduled backups by default
        for config in self.config.backup_configurations:
            self.output_queue.put(q_req.EnableScheduledBackups(config))

        super().start()
