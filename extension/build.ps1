# yōmu! Extension Builder for Windows (PowerShell)
param (
    [Parameter(Mandatory=$false, Position=0)]
    [string]$Browser
)

# Determine the extension directory path
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
if ($ScriptDir -eq $null -or $ScriptDir -eq "") { $ScriptDir = "." }

if ([string]::IsNullOrEmpty($Browser)) {
    Write-Host "❌ Usage: .\build.ps1 [chrome|firefox]" -ForegroundColor Red
    exit 1
}

$ManifestSource = ""
$TargetManifest = Join-Path $ScriptDir "manifest.json"

switch ($Browser.ToLower()) {
    "chrome" {
        $ManifestSource = Join-Path $ScriptDir "manifest.chrome.json"
        Write-Host " preparando manifest for Chrome..." -ForegroundColor Cyan
    }
    "firefox" {
        $ManifestSource = Join-Path $ScriptDir "manifest.firefox.json"
        Write-Host " preparando manifest for Firefox..." -ForegroundColor Cyan
    }
    default {
        Write-Host "❌ Unknown browser: $Browser" -ForegroundColor Red
        exit 1
    }
}

if (Test-Path $ManifestSource) {
    Copy-Item -Path $ManifestSource -Destination $TargetManifest -Force
    Write-Host "✅ Prepared manifest.json for $Browser" -ForegroundColor Green
} else {
    Write-Host "❌ Source manifest not found: $ManifestSource" -ForegroundColor Red
    exit 1
}
