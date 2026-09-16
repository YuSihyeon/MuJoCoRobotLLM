param(
    [string]$Spec = "",
    [double]$Speed = 0.2
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location -LiteralPath $ProjectRoot

Write-Host "움직이는 MuJoCo push demo를 실행합니다." -ForegroundColor Green
Write-Host "행동: 파란 pusher가 빨간 box 뒤로 이동한 뒤 초록 target 방향으로 box를 밉니다."
Write-Host "속도: $Speed 배속. 기본값 0.2는 실제보다 5배 느리게 보여줍니다."
Write-Host ""

if ([string]::IsNullOrWhiteSpace($Spec)) {
    python -m text2mujoco.demo_viewer --speed $Speed
} else {
    python -m text2mujoco.demo_viewer --spec "$Spec" --speed $Speed
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "demo viewer 실행이 실패했습니다. 위 오류 메시지를 확인하세요." -ForegroundColor Red
}

Read-Host "Enter를 누르면 닫습니다"
