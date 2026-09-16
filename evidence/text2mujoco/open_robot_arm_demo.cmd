@echo off
setlocal
cd /d "%~dp0"
powershell.exe -NoExit -ExecutionPolicy Bypass -File "%~dp0open_robot_arm_demo.ps1"
