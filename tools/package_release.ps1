param(
    [string]$Version = "",
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VersionFile = Join-Path $ProjectRoot "app_version.py"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"

if (Test-Path $VenvPython) {
    $PythonCommand = $VenvPython
}
elseif (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCommand = "python"
}
elseif (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCommand = "py"
}
else {
    throw "Python was not found. Install Python or create .venv first."
}

if (-not $Version) {
    $versionLine = Select-String -Path $VersionFile -Pattern '^APP_VERSION\s*=\s*"([^"]+)"' | Select-Object -First 1
    if (-not $versionLine) {
        throw "Could not read APP_VERSION from app_version.py"
    }
    $Version = $versionLine.Matches[0].Groups[1].Value
}

$PackageName = "Linglan_Dict-v$Version-windows-x64"
$ReleaseRoot = Join-Path $ProjectRoot "release"
$StageDir = Join-Path $ReleaseRoot $PackageName
$ZipPath = Join-Path $ReleaseRoot "$PackageName.zip"
$DistAppDir = Join-Path $ProjectRoot "dist\铃兰词典"
$PackageAppDir = Join-Path $StageDir "铃兰词典"

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

if (-not $SkipBuild) {
    Push-Location $ProjectRoot
    try {
        if ($PythonCommand -eq "py") {
            & $PythonCommand -3 -m PyInstaller main.spec --noconfirm
        }
        else {
            & $PythonCommand -m PyInstaller main.spec --noconfirm
        }
    }
    finally {
        Pop-Location
    }
}

if (-not (Test-Path $DistAppDir)) {
    throw "Build output not found: $DistAppDir"
}

if (Test-Path $StageDir) {
    Remove-Item -LiteralPath $StageDir -Recurse -Force
}
if (Test-Path $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

New-Item -ItemType Directory -Force -Path $StageDir | Out-Null
Copy-Item -LiteralPath $DistAppDir -Destination $PackageAppDir -Recurse

$runtimeAssets = @(
    "vocabulary.db",
    "offline_assets"
)

foreach ($asset in $runtimeAssets) {
    $source = Join-Path $ProjectRoot $asset
    if (Test-Path $source) {
        Copy-Item -LiteralPath $source -Destination (Join-Path $PackageAppDir $asset) -Recurse
    }
}

$readmePath = Join-Path $ProjectRoot "README.md"
if (Test-Path $readmePath) {
    Copy-Item -LiteralPath $readmePath -Destination (Join-Path $StageDir "README.md")
}

Compress-Archive -Path (Join-Path $StageDir "*") -DestinationPath $ZipPath -Force

Write-Host "Release package created:"
Write-Host $ZipPath
