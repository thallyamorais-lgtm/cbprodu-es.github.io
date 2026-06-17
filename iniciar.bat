@echo off
title CB Engenharia — Sistema de Producao
cd /d "%~dp0"
echo.
echo  ============================================
echo   CB Engenharia — Sistema de Producao
echo   Loteamento Jose Bernardino I e II
echo  ============================================
echo.
echo   Dashboard: http://localhost:5000/dashboard
echo.
echo   Frentes de servico:
echo   /contencao     /inst_radier   /lona_malha
echo   /conc_radier   /inst_reg      /graute_inf
echo   /graute_sup    /telhado       /inst_hidro
echo   /alvenaria     /acabamento    /gesso
   /contrapiso
echo   /caixinha      /peitoril      /esquadrias
echo   /cabeamento    /impermea      /ceramica
echo.
echo   Deixe esta janela aberta enquanto usar.
echo  ============================================
echo.
python servidor_local.py
pause
