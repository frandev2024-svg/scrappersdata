@echo off
REM Script para automatizar la ejecución periódica de todos los scrapers
cd /d %~dp0
python run_all_scrapers.py
