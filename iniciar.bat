@echo off
title CB Engenharia — Servidor de Producao
cd /d "%~dp0"
echo.
echo  Iniciando servidor...
echo  O sistema abrira automaticamente no seu browser.
echo  Mantenha esta janela aberta enquanto usar o sistema.
echo  Feche esta janela para encerrar.
echo.
python servidor_local.py
pause
