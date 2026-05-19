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
    
    # Bundle into a ZIP file
    $ZipName = "yomu-release-$Browser.zip"
    $ZipPath = Join-Path $ScriptDir $ZipName
    
    # Remove old zip if it exists
    if (Test-Path $ZipPath) {
        Remove-Item -Path $ZipPath -Force
    }

    Write-Host "📦 Bundling files into $ZipName using Python (to resolve Windows backslash separator bugs)..." -ForegroundColor Cyan
    python312 -c @"
import zipfile, os
zip_path = r'$ZipPath'
script_dir = r'$ScriptDir'
files = ['manifest.json', 'background.js', 'content.js', 'styles.css', 'popup.html', 'popup.js']
with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
    for f in files:
        fpath = os.path.join(script_dir, f)
        if os.path.exists(fpath):
            zipf.write(fpath, f)
    icons_dir = os.path.join(script_dir, 'icons')
    if os.path.exists(icons_dir):
        for root, _, filenames in os.walk(icons_dir):
            for filename in filenames:
                fpath = os.path.join(root, filename)
                rel = os.path.relpath(fpath, script_dir)
                zipf.write(fpath, rel.replace('\\', '/'))
"@
    
    Write-Host "🎉 Done! $ZipName is ready for upload." -ForegroundColor Green
} else {
    Write-Host "❌ Source manifest not found: $ManifestSource" -ForegroundColor Red
    exit 1
}
