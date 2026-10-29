@echo off
setlocal
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && py -3 -c "import sys" >nul 2>&1 && set "PY=py -3"
if not defined PY (
    for /f "delims=" %%D in ('dir /b /ad /o-n "%LocalAppData%\Programs\Python\Python3*" 2^>nul') do if not defined PY set "PY=%LocalAppData%\Programs\Python\%%D\python.exe"
)
if not defined PY goto :sem_python

%PY% -c "import PySide6" >nul 2>&1 || (
    echo Instalando a interface desktop Qt...
    %PY% -m pip install PySide6 || goto :erro
)

%PY% -m PyInstaller --version >nul 2>&1 || (
    echo Instalando a ferramenta de empacotamento...
    %PY% -m pip install pyinstaller || goto :erro
)

echo Gerando o executavel da Central CR2...
%PY% -m PyInstaller --noconfirm --clean "Central CR2.spec" || goto :erro
echo.
echo Pronto: dist\Central CR2.exe
exit /b 0

:sem_python
echo Python nao encontrado. Instale o Python 3 e tente novamente.
exit /b 1

:erro
echo Nao foi possivel gerar o executavel.
exit /b 1
