"""
This module contains the background backup thread that runs the backup logic.
"""

import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from enum import Enum
from pathlib import Path, PurePosixPath
from queue import Empty, Queue
from shlex import split as shlex_split
from shutil import move
from threading import Thread
from time import sleep, time
from traceback import format_exc

import schedule

import queue_requests as q_req


class BackgroundBackupThread(Thread):
    """
    A thread that runs backup tasks in the background to avoid blocking the systray GUI. It communicates with the
    systray using input and output queues.
    """

    def __init__(self, input_queue: Queue, output_queue: Queue) -> None:
        super().__init__()
        self.input_queue = input_queue
        self.output_queue = output_queue

        self.task_status: dict[str, TaskStatus] = defaultdict(lambda: TaskStatus.NOT_STARTED)
        self.last_sent_icon: str | None = None

    @staticmethod
    def to_wsl_path(path: Path) -> str:
        """
        Convert a Windows path to the corresponsing path in WSL.

        Args:
            path (Path): The Windows path to convert.

        Returns:
            str: A WSL path in /mnt/ that corresponds to the input path.
        """

        return f"/mnt/{path.drive.replace(':', '').lower()}/{PurePosixPath(*path.parts[1:])}"

    def update_systray(self, hover_text: str | None = None, icon: str | None = None) -> None:
        """
        Send a request to the systray to update the hover text and icon.

        Args:
            hover_text (str | None, optional): The hover text to show on the systray icon. Defaults to None.
            icon (str | None, optional): A path to the icon to show on the systray. Defaults to an\
                automatically-selected icon based on the current task statuses.
        """

        if icon is None:
            if TaskStatus.FAILED in self.task_status.values():
                # Failed tasks take precedence over anything else
                icon = "./icons/error.ico"
            elif TaskStatus.RUNNING in self.task_status.values():
                for [task, status] in self.task_status.items():
                    # Choose the icon based on the first running task
                    if status == TaskStatus.RUNNING:
                        if "post-backup" in task:
                            icon = "./icons/post-backup.ico"
                        elif "backup" in task:
                            icon = "./icons/backup.ico"
                        elif "analysis" in task:
                            icon = "./icons/analyze.ico"
                        elif "diff" in task:
                            icon = "./icons/logs.ico"
                        break
            elif TaskStatus.FINISHED in self.task_status.values():
                icon = "./icons/success.ico"
            else:
                icon = "./icons/drive.ico"

        if icon == self.last_sent_icon:
            # Avoid pointlessly sending the same icon to the systray multiple times
            icon = None
        else:
            self.last_sent_icon = icon

        self.output_queue.put(q_req.UpdateSystray(hover_text=hover_text, icon=icon))

    def output(self, line: str) -> None:
        """
        Log a message and automatically update the systray icon.

        Args:
            line (str): The line to log and show on the systray icon.
        """

        # Print will be redirected to the log file if the script is running without a console
        print(f"[{datetime.now()}] {line}")
        sys.stdout.flush()
        self.update_systray(line)

    def run_process_and_update_systray(self, title: str, command: str, line_count_target: int = 0) -> int:
        """
        Run a process and update the systray icon hover text every second with the process output.

        Args:
            title (str): The title of the process to show on the systray. Also used to keep track of the task's status.
            command (str): The command to run for the process.
            line_count_target (int, optional): A line count used to estimate the progress of the process based on the\
                number of lines output. It should be the number of lines that the last execution of the process output.\
                Defaults to 0.

        Raises:
            CalledProcessError: The process returned a non-zero exit code.

        Returns:
            int: The number of lines output by the process.
        """

        self.task_status[title] = TaskStatus.RUNNING
        self.output(f"Running {title}: started")

        stats_output = ""
        start_time = time()
        command_parts = shlex_split(command)

        with subprocess.Popen(
            args=command_parts,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        ) as process:
            if process.stdout is None:
                # This shouldn't happen, but the type checker complains
                raise RuntimeError()

            line_count = 0
            last_update_time = start_time
            for line in iter(process.stdout.readline, b""):
                line_count += 1

                if self.task_status[title] == TaskStatus.CANCEL_REQUESTED:
                    process.terminate()

                line = line.decode("utf-8").strip()
                # Get the borg --stats output: number of files, original size, and deduplicated size
                if "Number of files: " in line or "Original size: " in line or "Deduplicated size: " in line:
                    # Ignore the stats if they are 0 (seems to happen with the prune)
                    if not (line.endswith(" 0") or line.endswith(" 0 B")):
                        stats_output += f"\n{line}"

                if time() - last_update_time > 1:
                    elapsed_time = time() - start_time
                    minutes, seconds = divmod(int(elapsed_time), 60)
                    time_string = f"{minutes}:{seconds:02}s"

                    # Hover text will be truncated to 128 characters
                    hover_text = f"Running {title} ({time_string}"

                    if line_count_target > 0:
                        # Progress estimate based on the number of lines output
                        percentage = (line_count / line_count_target) * 100
                        hover_text += f", {percentage:.2f}%"

                    hover_text += f"):\n{line}"

                    # Logging this is redundant because it is already in the Borgmatic log
                    self.update_systray(hover_text)
                    last_update_time = time()

            # Once readline returns an empty string, the process should have finished, but wait just to be safe
            process.wait()

            elapsed_time = time() - start_time
            minutes, seconds = divmod(int(elapsed_time), 60)
            time_string = f"{minutes}:{seconds:02}s"

            if process.returncode != 0:
                self.task_status[title] = TaskStatus.FAILED
                self.output(
                    f"Failed {title} at {datetime.now().strftime('%I:%M %p')}!\n"
                    + f"Return code: {process.returncode} (in {time_string})"
                )
                raise subprocess.CalledProcessError(process.returncode, command_parts)

            hover_text = f"Finished {title} at {datetime.now().strftime('%I:%M %p')} in {time_string}:"
            if stats_output:
                hover_text += f"\n{stats_output}"
            self.task_status[title] = TaskStatus.FINISHED
            self.output(hover_text)
            return line_count

    def save_line_count(self, line_count_file: Path, line_count: int) -> None:
        """
        Save the number of lines output by a process to a file.

        Args:
            line_count_file (Path): A file to save the line count to.
            line_count (int): The number of lines output by a process.
        """

        with open(line_count_file, "w", encoding="utf-8") as file:
            file.write(str(line_count))

    def load_line_count(self, line_count_file: Path) -> int:
        """
        Load the number of lines output by a process from a file.

        Args:
            line_count_file (Path): The file to load the line count from.

        Returns:
            int: The number of lines output by a process.
        """

        if not line_count_file.exists():
            return 0

        with open(line_count_file, "r", encoding="utf-8") as file:
            return int(file.read())

    def rotate_logs(self, log_file: Path) -> None:
        """
        Rotate 10 log files based on the current log file. Add the .1 suffix to the current log, rename .1 to .2,
        etc., and delete .9.

        Args:
            log_file (Path): The current log file, without any suffix.
        """

        if (log_file.parent / f"{log_file.name}.9").exists():
            (log_file.parent / f"{log_file.name}.9").unlink()

        for i in range(8, 0, -1):
            if (log_file.parent / f"{log_file.name}.{i}").exists():
                move(str(log_file) + f".{i}", str(log_file) + f".{i + 1}")

        if log_file.exists():
            move(str(log_file), str(log_file) + ".1")

    def task_is_running(self, task_title: str) -> bool:
        """
        Check if a task is currently running based on its current status.

        Args:
            task_title (str): The title of the task to check.

        Returns:
            bool: True if the task is currently running, False if it is not.
        """

        match self.task_status[task_title]:
            case TaskStatus.RUNNING:
                return True
            case TaskStatus.CANCEL_REQUESTED:
                return True

        return False

    def run_backup(self, request: q_req.StartBackup) -> None:
        """
        Run a backup task using the config from a StartBackup request. This only starts the backup if it is not already
        running.

        Args:
            request (StartBackup): The request from the systray or schedule to start a backup.
        """

        config = request.config
        task_title = f"{config.name} backup"

        try:
            if self.task_is_running(task_title):
                self.output(f"{task_title} is already running, skipping")
                return

            self.rotate_logs(config.log_file)

            backup_lines = self.load_line_count(config.backup_line_count_file)
            backup_lines = self.run_process_and_update_systray(
                task_title,
                f"wsl.exe -d {config.wsl_distro} -- PATH=~/.local/bin:$PATH borgmatic "
                f"--config {self.to_wsl_path(config.config_file)} --verbosity 1 "
                f"--log-file {self.to_wsl_path(config.log_file)} --log-file-verbosity 2",
                backup_lines,
            )
            self.save_line_count(config.backup_line_count_file, backup_lines)

        except subprocess.CalledProcessError:
            # This error was already handled
            return
        except Exception as ex:
            self.task_status[task_title] = TaskStatus.FAILED
            self.output(f"Error running backup for {config.name}: {ex}\n{format_exc()}")

    def run_post_backup(self, request: q_req.StartPostBackup) -> None:
        """
        Run post-backup tasks using the config from a StartPostBackup request. This only starts the post-backup tasks if
        both them and the associated backup task are not already running.

        Args:
            request (q_req.StartPostBackup): The request from the systray or schedule to start post-backup tasks.
        """

        config = request.config
        task_title = f"{config.name} post-backup"

        try:
            if request.is_scheduled:
                # Make sure scheduled post-backup tasks always run after the respective backup when both are queued at
                # the same time
                sleep(10)

            if self.task_is_running(task_title):
                self.output(f"{task_title} is already running, skipping")
                return

            # Avoid running the post-backup script if the backup is still running, as there might be inconsistencies in
            # the backup repo
            backup_task_title = f"{config.name} backup"
            if self.task_is_running(backup_task_title):
                self.output(f"{backup_task_title} is still running, delaying {task_title}")
                # Wait before putting the request back into the queue to avoid log spam or running the main loop too
                # often
                sleep(30)
                self.input_queue.put(request)
                return

            self.run_process_and_update_systray(
                task_title,
                f"wsl.exe -d {config.post_backup_wsl_distro} -- PATH=~/.local/bin:$PATH "
                f"{self.to_wsl_path(config.post_backup_script)}",
            )

        except subprocess.CalledProcessError:
            # This error was already handled
            return
        except Exception as ex:
            self.task_status[task_title] = TaskStatus.FAILED
            self.output(f"Error running post-backup tasks for {config.name}: {ex}\n{format_exc()}")

    def enable_scheduled_backups(self, request: q_req.EnableScheduledBackups) -> None:
        """
        Enable scheduled backups for a config. This clears any existing scheduled tasks for the config and creates new
        ones that run the backup every 2 hours and post-backup tasks every 6 hours.

        Args:
            request (q_req.EnableScheduledBackups): The request from the systray to enable scheduled backups.
        """

        schedule.clear(request.config.name)

        schedule.every(request.config.backup_schedule_hours).hours.at(":00").do(
            lambda: self.input_queue.put(q_req.StartBackup(request.config, True))
        ).tag(request.config.name)
        # Post-backup tasks should always be queued after the backup so they can check if the backup is running
        schedule.every(request.config.post_backup_schedule_hours).hours.at(":01").do(
            lambda: self.input_queue.put(q_req.StartPostBackup(request.config, True))
        ).tag(request.config.name)

        self.output(f"Enabled scheduled backups for {request.config.name}")

    def disable_scheduled_backups(self, request: q_req.DisableScheduledBackups) -> None:
        """
        Disable scheduled backups for a config. This clears any existing scheduled tasks for the config.

        Args:
            request (q_req.DisableScheduledBackups): The request from the systray to disable scheduled backups.
        """

        schedule.clear(request.config.name)
        self.output(f"Disabled scheduled backups for {request.config.name}")

    def cancel_backup(self, request: q_req.CancelBackup) -> None:
        """
        Cancel a backup for a config if it is currently running.

        Args:
            request (q_req.CancelBackup): The request from the systray to cancel a backup.
        """

        config = request.config
        task_title = f"{config.name} backup"
        if self.task_is_running(task_title):
            self.task_status[task_title] = TaskStatus.CANCEL_REQUESTED
            self.output(f"Cancelled {config.name} backup")

    def cancel_post_backup(self, request: q_req.CancelPostBackup) -> None:
        """
        Cancel post-backup tasks for a config if they are currently running.

        Args:
            request (q_req.CancelBackup): The request from the systray to cancel post-backup tasks.
        """

        config = request.config
        task_title = f"{config.name} post-backup"
        if self.task_is_running(task_title):
            self.task_status[task_title] = TaskStatus.CANCEL_REQUESTED
            self.output(f"Cancelled {config.name} post-backup tasks")

    def write_report(self, file: Path, header: str, lines: list[str], editor: str) -> None:
        """
        Write a header and a list of lines to a file. Then, open it in an editor.

        Args:
            file (Path): The file to write the lines to.
            header (str): The header to write to the file before the lines.
            lines (list[str]): The lines to write to the file.
            editor (str): The editor to open the file with.
        """

        with open(file, "w", encoding="utf-8") as report:
            report.write(f"{header}\n\n")
            report.write("".join(lines))

        subprocess.Popen([editor, file])

    def analyze_logs(self, request: q_req.AnalyzeLogs) -> None:
        """
        Analyze logs for a config and open them in the editor. This creates reports for the average backup times of each
        file and path component of that file, as well as the latest backup's excluded files and errors.

        Args:
            request (q_req.AnalyzeLogs): The request from the systray to analyze the logs.
        """

        config = request.config
        task_title = f"{config.name} analysis"
        self.task_status[task_title] = TaskStatus.RUNNING

        try:
            file_backup_times = defaultdict(float)
            path_backup_times = defaultdict(float)
            error_lines = []
            excluded_files = []
            backup_count = 0  # Keep track of the backup count to average the times

            for i in range(0, 10):
                log_file_path = str(config.log_file)
                if i != 0:
                    # The first log file has no suffix
                    log_file_path += f".{i}"

                if not os.path.exists(log_file_path):
                    break

                with open(log_file_path, "r", encoding="utf-8") as log_file:
                    self.output(f"Analyzing {log_file_path}...")

                    previous_timestamp = None
                    previous_line = ""

                    for line in log_file:
                        parts = line.split()
                        if len(parts) < 5:
                            # Ignore lines that are not borg --list output
                            continue

                        # Borgmatic rounds the microseconds to milliseconds, so add 3 zeros to the end
                        timestamp_str = " ".join(parts[0:2])[1:-1] + "000"
                        timestamp = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S,%f")

                        if previous_timestamp is None:
                            # This is the first log line
                            previous_timestamp = timestamp

                        # parts[2] is the log level, unnecessary for this analysis
                        file_flag = parts[3]
                        log_file = " ".join(parts[4:])  # File path can contain spaces

                        # See https://borgbackup.readthedocs.io/en/latest/usage/create.html#item-flags
                        if len(file_flag) == 1:
                            backup_time = timestamp - previous_timestamp
                            backup_time = backup_time.total_seconds()
                            # If backup_time is over 10 minutes for a single file, the computer was probably just asleep
                            # during a backup
                            if backup_time < 600:
                                file_backup_times[log_file] += backup_time

                                path_components = log_file.split("/")
                                for j in range(1, len(path_components) + 1):
                                    component = "/".join(path_components[:j])
                                    path_backup_times[component] += backup_time

                        # Report errors only for the most recent backup
                        if i == 0:
                            if file_flag == "-":
                                excluded_files.append(line)
                            if file_flag == "E":
                                # The detailed error is logged on the previous line
                                error_lines.append(previous_line)
                            if "file changed while we read it!" in line:
                                error_lines.append(line)

                        previous_timestamp = timestamp
                        previous_line = line

                backup_count += 1

            if backup_count == 0:
                # There are only failed backups in the logs, avoid division by zero
                backup_count = 1

            sorted_files = sorted(file_backup_times.items(), key=lambda x: x[1], reverse=True)
            sorted_paths = sorted(path_backup_times.items(), key=lambda x: x[1], reverse=True)

            self.write_report(
                config.report_files,
                f"Average backup times for {config.name} files ({backup_count} backups analyzed):",
                [
                    (f"{backup_time / backup_count:.2f}s: {log_file_path}\n")
                    for log_file_path, backup_time in sorted_files
                ],
                request.editor,
            )
            self.write_report(
                config.report_paths,
                f"Average backup times for {config.name} paths ({backup_count} backups analyzed):",
                [(f"{backup_time / backup_count:.2f}s: {log_file}\n") for log_file, backup_time in sorted_paths],
                request.editor,
            )
            self.write_report(
                config.report_excluded,
                f"Excluded files for {config.name} (latest backup):",
                excluded_files,
                request.editor,
            )
            self.write_report(
                config.report_errors,
                f"Errors for {config.name} (latest backup):",
                error_lines,
                request.editor,
            )

            self.task_status[task_title] = TaskStatus.FINISHED
            self.output(f"Finished analyzing {config.name} logs")

        except Exception as ex:
            self.task_status[task_title] = TaskStatus.FAILED
            self.output(f"Error analyzing logs for {config.name}: {ex}\n{format_exc()}")

    def diff_last_backups(self, request: q_req.DiffLastBackups) -> None:
        config = request.config
        task_title = f"{config.name} diff"
        self.task_status[task_title] = TaskStatus.RUNNING

        try:
            self.output(f"Finding last two backups for {config.name}...")
            command_parts = shlex_split(
                f"wsl.exe -d {config.wsl_distro} -- PATH=~/.local/bin:$PATH borgmatic "
                f"--config {self.to_wsl_path(config.config_file)} borg rlist"
            )
            process = subprocess.run(
                command_parts, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            last_two_lines = process.stdout.decode("utf-8").split("\n")[-3:-1]
            last_two_backups = " ".join([line.split(" ")[0] for line in last_two_lines])

            self.output(f"Running diff for {config.name}...")
            command_parts = shlex_split(
                f"wsl.exe -d {config.wsl_distro} -- PATH=~/.local/bin:$PATH borgmatic "
                f"--config {self.to_wsl_path(config.config_file)} borg diff {last_two_backups} --content-only"
            )
            process = subprocess.run(
                command_parts, check=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW
            )
            diff_output = process.stdout.decode("utf-8")

            self.write_report(
                config.diff_file,
                f"Diff for last two {config.name} backups ({last_two_backups}):",
                [diff_output],
                request.editor,
            )

            self.task_status[task_title] = TaskStatus.FINISHED
            self.output(f"Finished diff for {config.name}")

        except Exception as ex:
            self.task_status[task_title] = TaskStatus.FAILED
            self.output(f"Error running diff for {config.name}: {ex}\n{format_exc()}")

    def queue_exit(self) -> None:
        """
        Send exit requests to the input and output queues and set all tasks to CANCEL_REQUESTED to stop them.
        """

        self.input_queue.put(q_req.Exit())
        self.output_queue.put(q_req.Exit())
        for task in self.task_status.keys():
            self.task_status[task] = TaskStatus.CANCEL_REQUESTED

    def run(self) -> None:
        """
        Run the background backup thread. This is the main loop that processes requests from the input queue and runs
        backup tasks.
        """

        self.output("Background backup thread started")
        while True:
            try:
                # This should not take too long because each scheduled task only adds an item to the input queue. If
                # scheduled tasks ran longer, it would be better to run them in a separate thread.
                schedule.run_pending()

                try:
                    queue_item = self.input_queue.get(timeout=1)
                except Empty:
                    continue

                match queue_item:
                    case q_req.StartBackup():
                        task_thread = Thread(target=self.run_backup, args=(queue_item,))
                        task_thread.start()
                    case q_req.StartPostBackup():
                        task_thread = Thread(target=self.run_post_backup, args=(queue_item,))
                        task_thread.start()
                    case q_req.CancelBackup():
                        self.cancel_backup(queue_item)
                    case q_req.CancelPostBackup():
                        self.cancel_post_backup(queue_item)
                    case q_req.EnableScheduledBackups():
                        self.enable_scheduled_backups(queue_item)
                    case q_req.DisableScheduledBackups():
                        self.disable_scheduled_backups(queue_item)
                    case q_req.AnalyzeLogs():
                        task_thread = Thread(target=self.analyze_logs, args=(queue_item,))
                        task_thread.start()
                    case q_req.DiffLastBackups():
                        task_thread = Thread(target=self.diff_last_backups, args=(queue_item,))
                        task_thread.start()
                    case q_req.Exit():
                        self.queue_exit()
                        break
                    case _:
                        raise TypeError(f"Backup thread got unknown type in input queue: {type(queue_item)}")

            except Exception as ex:
                self.output(f"Error in background backup thread: {ex}\n{format_exc()}")
                self.update_systray(icon="./icons/error.ico")

        self.output("Exiting background backup thread")


class TaskStatus(Enum):
    """
    Represents the status of a task.
    """

    NOT_STARTED = 0
    RUNNING = 1
    FINISHED = 2
    FAILED = 3
    CANCEL_REQUESTED = 4
