param(
    [string]$SceneXml = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

if ([string]::IsNullOrWhiteSpace($SceneXml)) {
    $SceneXml = Get-ChildItem -LiteralPath (Join-Path $ProjectRoot "artifacts") -Recurse -Filter "scene.xml" |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1 -ExpandProperty FullName
}

if ([string]::IsNullOrWhiteSpace($SceneXml) -or -not (Test-Path -LiteralPath $SceneXml)) {
    Write-Host "scene.xml을 찾지 못했습니다. 먼저 다음 명령을 실행하세요:" -ForegroundColor Yellow
    Write-Host "python -m text2mujoco baseline --headless"
    Read-Host "Enter를 누르면 닫습니다"
    exit 1
}

Write-Host "MuJoCo official viewer로 MJCF를 compile해서 엽니다." -ForegroundColor Green
Write-Host "Scene XML: $SceneXml"
Write-Host ""
Write-Host "Viewer 창이 열리면 마우스 드래그로 회전, 휠로 확대/축소할 수 있습니다."
Write-Host "이 PowerShell 창은 오류 확인을 위해 열어둡니다."
Write-Host ""

python -m mujoco.viewer --mjcf "$SceneXml"

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "MuJoCo viewer 실행이 실패했습니다. 위 오류 메시지를 확인하세요." -ForegroundColor Red
}

Read-Host "Enter를 누르면 닫습니다"
