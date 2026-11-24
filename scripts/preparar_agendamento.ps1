param(
    [string]$Destino = (Join-Path (Split-Path $PSScriptRoot -Parent) 'logs\coleta-kabum.xml'),
    [switch]$PermitirBateria,
    [switch]$AcordarComputador
)
$ErrorActionPreference = 'Stop'
$taskRaiz = (Resolve-Path (Split-Path $PSScriptRoot -Parent)).Path
$taskPython = Join-Path $taskRaiz '.venv\Scripts\pythonw.exe'
if (-not (Test-Path -LiteralPath $taskPython -PathType Leaf)) { throw 'Python da .venv não encontrado.' }
$taskUsuario = [Security.Principal.WindowsIdentity]::GetCurrent().User.Value
$taskInicio = [DateTimeOffset]::UtcNow.AddMinutes(15).ToOffset([TimeSpan]::FromHours(-4)).ToString('yyyy-MM-ddTHH:mm:sszzz')
$taskPythonXml = [Security.SecurityElement]::Escape($taskPython)
$taskRaizXml = [Security.SecurityElement]::Escape($taskRaiz)
$taskRestringirBateria = (-not $PermitirBateria).ToString().ToLowerInvariant()
$taskAcordar = $AcordarComputador.IsPresent.ToString().ToLowerInvariant()
$taskXml = @"
<?xml version="1.0" encoding="UTF-16"?>
<Task version="1.2" xmlns="http://schemas.microsoft.com/windows/2004/02/mit/task">
  <RegistrationInfo><Description>Coleta local KaBuM! a cada 15 minutos. Preparada desabilitada para revisão.</Description></RegistrationInfo>
  <Triggers><TimeTrigger><Repetition><Interval>PT15M</Interval><StopAtDurationEnd>false</StopAtDurationEnd></Repetition><StartBoundary>$taskInicio</StartBoundary><Enabled>true</Enabled></TimeTrigger></Triggers>
  <Principals><Principal id="Autor"><UserId>$taskUsuario</UserId><LogonType>InteractiveToken</LogonType><RunLevel>LeastPrivilege</RunLevel></Principal></Principals>
  <Settings><MultipleInstancesPolicy>IgnoreNew</MultipleInstancesPolicy><DisallowStartIfOnBatteries>$taskRestringirBateria</DisallowStartIfOnBatteries><StopIfGoingOnBatteries>$taskRestringirBateria</StopIfGoingOnBatteries><StartWhenAvailable>true</StartWhenAvailable><Enabled>false</Enabled><WakeToRun>$taskAcordar</WakeToRun><ExecutionTimeLimit>PT30M</ExecutionTimeLimit></Settings>
  <Actions Context="Autor"><Exec><Command>$taskPythonXml</Command><Arguments>-m scraper.agendado</Arguments><WorkingDirectory>$taskRaizXml</WorkingDirectory></Exec></Actions>
</Task>
"@
$taskCaminho = [IO.Path]::GetFullPath($Destino)
if (-not $taskCaminho.StartsWith($taskRaiz + '\', [StringComparison]::OrdinalIgnoreCase)) { throw 'O XML deve ficar dentro do projeto.' }
$taskPasta = Split-Path $taskCaminho -Parent
if (-not (Test-Path -LiteralPath $taskPasta)) { New-Item -ItemType Directory -Path $taskPasta | Out-Null }
[IO.File]::WriteAllText($taskCaminho, $taskXml, [Text.Encoding]::Unicode)
Write-Output "XML preparado em $taskCaminho. Nenhuma tarefa foi registrada, ativada ou executada."
