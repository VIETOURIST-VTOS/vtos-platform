@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ================================================
echo  CUA HEP TREN MAY - CHI DOC - cho MOI LAN
echo ================================================
echo  Chay dung 17 tep phep thu ma viec hang-rao-gop
echo  cua CI chay, cong ruff. Chung 1-2 phut.
echo  KHONG thay bo du 251 tep.
echo ================================================
echo.
set NHANH=%1
if "%NHANH%"=="" set /p NHANH=Go ten nhanh (hoac main) roi Enter: 
if "%NHANH%"=="" goto het
set PYTHONIOENCODING=utf-8:replace
python scripts\cua-hep.py --nhanh %NHANH% > "scripts\_log-cua-hep-%NHANH%.txt" 2>&1
type "scripts\_log-cua-hep-%NHANH%.txt"
:het
echo.
pause
