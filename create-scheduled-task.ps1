# Create the scheduled task
$currentDirectory = (Get-Location).Path

$taskName = "Borgmatic Windows Tray"
$taskCommand = "C:\WINDOWS\pyw.exe"
$taskDescription = "This task starts the Borgmatic Windows Tray program at login."
$taskArguments = "`"$currentDirectory\main.pyw`""
$taskUserId = whoami.exe

$taskAction = New-ScheduledTaskAction -Execute $taskCommand -Argument $taskArguments -WorkingDirectory $currentDirectory
$taskTrigger = New-ScheduledTaskTrigger -AtLogOn -User $taskUserId
$taskPrincipal = New-ScheduledTaskPrincipal -UserId $taskUserId -LogonType Interactive -RunLevel Highest
$taskSettings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit 0

Register-ScheduledTask -TaskName $taskName -Action $taskAction -Trigger $taskTrigger -Principal $taskPrincipal -Settings $taskSettings -Description $taskDescription

# Create a shortcut in the Start Menu
$shell = New-Object -ComObject ("WScript.Shell")
$startMenu = $shell.SpecialFolders.Item("StartMenu") + "\Programs"
$shortcut = $shell.CreateShortcut("$startMenu\$taskName.lnk")
$shortcut.TargetPath = "C:\Windows\System32\schtasks.exe"
$shortcut.Arguments = "/run /tn `"$taskName`""
$shortcut.WorkingDirectory = $currentDirectory
$shortcut.IconLocation = "$currentDirectory\icons\drive.ico"
$shortcut.Save()
