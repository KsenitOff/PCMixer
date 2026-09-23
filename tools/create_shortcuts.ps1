param([Parameter(Mandatory=$true)][string]$Root)

$ErrorActionPreference = 'Stop'

$Root = $Root.TrimEnd('\')
$Desktop = [Environment]::GetFolderPath('Desktop')
$Shell = New-Object -ComObject WScript.Shell

$PythonW = Join-Path $Root '.venv\Scripts\pythonw.exe'
$Launcher = Join-Path $Root 'launcher.pyw'
$Stopper = Join-Path $Root 'stop_mixer.pyw'
$Icon = Join-Path $Root 'PCMixer.ico'

foreach ($Destination in @($Desktop, $Root)) {
    $Shortcut = $Shell.CreateShortcut((Join-Path $Destination 'PC Mixer.lnk'))
    $Shortcut.TargetPath = $PythonW
    $Shortcut.Arguments = '"' + $Launcher + '"'
    $Shortcut.WorkingDirectory = $Root
    $Shortcut.Description = 'Start PC Mixer'
    $Shortcut.IconLocation = $Icon + ',0'
    $Shortcut.Save()

    $StopShortcut = $Shell.CreateShortcut((Join-Path $Destination 'Stop PC Mixer.lnk'))
    $StopShortcut.TargetPath = $PythonW
    $StopShortcut.Arguments = '"' + $Stopper + '"'
    $StopShortcut.WorkingDirectory = $Root
    $StopShortcut.Description = 'Stop PC Mixer'
    $StopShortcut.IconLocation = $Icon + ',0'
    $StopShortcut.Save()
}
