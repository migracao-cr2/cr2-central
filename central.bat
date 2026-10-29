@echo off
rem ============================================================
rem  Central de Automacoes CR2
rem
rem  Dois cliques aqui abre a janela.
rem
rem  A janela nova e em Qt (src\app_qt.py, precisa do PySide6).
rem  Sem o PySide6, abre a janela em Tkinter (src\app.py), que
rem  faz exatamente o mesmo - a Central nunca deixa de abrir por
rem  falta de biblioteca. O PySide6 chega sozinho quando a pessoa
rem  abre um programa do catalogo que usa Qt (o .bat dele instala).
rem
rem  Nao usamos o dist\Central CR2.exe aqui de proposito: o .exe e
rem  uma copia congelada, e o "Atualizar a Central" atualiza o
rem  codigo do git, nao o .exe - ele continuaria na versao velha.
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

rem `pyw` abre sem o console preto atras da janela
set "PYW=%PY%"
where pyw >nul 2>&1 && set "PYW=pyw -3"

%PY% -c "import PySide6" >nul 2>&1
if not errorlevel 1 (
    start "" %PYW% "src\app_qt.py" %*
    exit /b 0
)

%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :sem_tk
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
