param(
    [string]$Version = "",
    [switch]$SkipBuild
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VersionFile = Join-Path $ProjectRoot "app_version.py"
$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$PythonCandidate = $null

function Test-PythonCommand {
    param(
        [object]$Candidate
    )
    try {
        Invoke-PythonCandidate $Candidate @("--version") | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Test-PyInstaller {
    param(
        [object]$Candidate
    )
    try {
        Invoke-PythonCandidate $Candidate @("-m", "PyInstaller", "--version") | Out-Null
        return $LASTEXITCODE -eq 0
    }
    catch {
        return $false
    }
}

function Invoke-PythonCandidate {
    param(
        [object]$Candidate,
        [string[]]$Arguments
    )
    if ($Candidate.UseLauncher) {
        & $Candidate.Command -3 @Arguments
    }
    else {
        & $Candidate.Command @Arguments
    }
}

$PythonCandidates = @()
if (Test-Path $VenvPython) {
    $PythonCandidates += [pscustomobject]@{ Command = $VenvPython; UseLauncher = $false }
}
if (Get-Command python -ErrorAction SilentlyContinue) {
    $PythonCandidates += [pscustomobject]@{ Command = "python"; UseLauncher = $false }
}
if (Get-Command py -ErrorAction SilentlyContinue) {
    $PythonCandidates += [pscustomobject]@{ Command = "py"; UseLauncher = $true }
}

foreach ($candidate in $PythonCandidates) {
    if ((Test-PythonCommand $candidate) -and ($SkipBuild -or (Test-PyInstaller $candidate))) {
        $PythonCandidate = $candidate
        break
    }
}

if ($null -eq $PythonCandidate) {
    if ($SkipBuild) {
        throw "Python was not found. Install Python or create .venv first."
    }
    throw "PyInstaller was not found in any available Python. Run: python -m pip install -r requirements.txt"
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
$DistRoot = Join-Path $ProjectRoot "dist"
$DistAppDir = ""
$PackageAppDir = ""

New-Item -ItemType Directory -Force -Path $ReleaseRoot | Out-Null

if (-not $SkipBuild) {
    Push-Location $ProjectRoot
    try {
        Invoke-PythonCandidate $PythonCandidate @("-m", "PyInstaller", "main.spec", "--noconfirm")
    }
    finally {
        Pop-Location
    }
}

if (Test-Path $DistRoot) {
    $distDirs = Get-ChildItem -LiteralPath $DistRoot -Directory
    foreach ($dir in $distDirs) {
        $exePath = Join-Path $dir.FullName ($dir.Name + ".exe")
        if (Test-Path $exePath) {
            $DistAppDir = $dir.FullName
            $PackageAppDir = Join-Path $StageDir $dir.Name
            break
        }
    }
}

if ((-not $DistAppDir) -or (-not (Test-Path -LiteralPath $DistAppDir))) {
    throw "Build output folder was not found under dist."
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
