[CmdletBinding()]
param()
Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"
$ProgressPreference = "SilentlyContinue"
function Stop-Launcher {
    param([Parameter(Mandatory = $true)][string]$Message)
    [Console]::Error.WriteLine("PreToolUse Windows launcher: " + $Message)
    exit 2
}
try {
    $cwd = (Get-Location).Path
    $rootOutput = @(& git.exe -C $cwd rev-parse --show-toplevel 2>$null)
    $gitExit = $LASTEXITCODE
    if ($gitExit -ne 0 -or $rootOutput.Count -eq 0 -or [string]::IsNullOrWhiteSpace([string]$rootOutput[0])) { Stop-Launcher "unable to resolve repository root from cwd" }
    $repoRoot = [System.IO.Path]::GetFullPath(([string]$rootOutput[0]).Trim())
    $hookPath = Join-Path $repoRoot ".codex\hooks\pre_tool_use_policy.mjs"
    if (-not (Test-Path -LiteralPath $hookPath -PathType Leaf)) { Stop-Launcher "Node Hook file not found" }
    $nodeCommand = Get-Command node.exe -ErrorAction SilentlyContinue
    if ($null -eq $nodeCommand -or [string]::IsNullOrWhiteSpace($nodeCommand.Source)) { Stop-Launcher "Node executable was not found on PATH" }
    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $nodeCommand.Source
    $startInfo.Arguments = '"' + $hookPath + '"'
    $startInfo.WorkingDirectory = $cwd
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.RedirectStandardInput = $true
    $startInfo.RedirectStandardOutput = $true
    $startInfo.RedirectStandardError = $true
    $process = New-Object System.Diagnostics.Process
    $process.StartInfo = $startInfo
    [void]$process.Start()
    $stdoutTask = $process.StandardOutput.BaseStream.CopyToAsync([Console]::OpenStandardOutput())
    $stderrTask = $process.StandardError.BaseStream.CopyToAsync([Console]::OpenStandardError())
    [Console]::OpenStandardInput().CopyTo($process.StandardInput.BaseStream)
    $process.StandardInput.Close()
    if (-not $process.WaitForExit(12000)) {
        if (-not $process.HasExited) { $process.Kill() }
        $process.WaitForExit()
        Stop-Launcher "Node Hook timed out"
    }
    [void]$stdoutTask.GetAwaiter().GetResult()
    [void]$stderrTask.GetAwaiter().GetResult()
    exit $process.ExitCode
}
catch { Stop-Launcher $_.Exception.Message }