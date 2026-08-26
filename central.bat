@echo off
rem ============================================================
rem  Central de Automacoes CR2
rem
rem  Dois cliques aqui abre a janela.
rem
rem  A Central so precisa do Python com Tkinter - nada de pip.
rem  Quem instala dependencia e o .bat de cada automacao, na
rem  primeira vez que ela e aberta.
rem
rem  Este arquivo precisa ficar em ASCII com quebra CRLF:
rem  o cmd.exe nao le .bat com quebra de linha LF.
rem ============================================================
title Central CR2
cd /d "%~dp0"

rem O lancador `py` acha a instalacao real do Python. Um `python`
rem solto no PATH pode ser o embutido de outro programa (o do
rem LibreOffice, por exemplo, nao tem Tkinter e a janela nao abre).
set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY (
    where python >nul 2>&1 && set "PY=python"
)
if not defined PY goto :sem_python

%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :sem_tk

rem `pyw` abre sem o console preto atras da janela
set "PYW=%PY%"
where pyw >nul 2>&1 && set "PYW=pyw -3"
start "" %PYW% "src\app.py" %*
exit /b 0

:sem_python
echo.
echo   Python nao encontrado.
echo   Instale em https://www.python.org/downloads/ marcando
echo   "Add python.exe to PATH" e rode este arquivo de novo.
echo.
pause
exit /b 1

:sem_tk
echo.
echo   Este Python nao tem Tkinter, entao a janela nao abre.
echo   Reinstale o Python marcando "tcl/tk and IDLE".
echo.
pause
exit /b 1
