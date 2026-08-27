@echo off
rem ============================================================
rem  Instalador da Central de Automacoes CR2
rem
rem  Dois cliques aqui e pronto: instala o que falta, baixa a
rem  Central, cria o atalho na area de trabalho e abre a janela.
rem
rem  Rodar de novo nao estraga nada: quando a Central ja esta
rem  instalada, ele so atualiza e abre.
rem
rem  POR QUE UM .BAT E NAO UM INSTALADOR DE VERDADE
rem  O Windows 11 ja traz o winget, que instala Python e Git
rem  sozinho. Um .msi exigiria build e assinatura de codigo, e
rem  sem assinar o SmartScreen assusta mais gente do que o
rem  instalador ajudaria.
rem
rem  Este arquivo precisa ficar em ASCII com quebra CRLF: o
rem  cmd.exe nao le .bat com quebra de linha LF.
rem ============================================================
setlocal EnableExtensions
title Instalador da Central de Automacoes CR2

set "REPO=https://github.com/migracao-cr2/cr2-central.git"
set "DEST=%LOCALAPPDATA%\CR2\cr2-central"

rem Um repositorio privado qualquer, so para fazer o login do
rem GitHub AQUI, num terminal de verdade. Ver a secao do login.
set "REPO_PRIVADO=https://github.com/migracao-cr2/gestor-licitacoes.git"

echo.
echo  ========================================================
echo    CENTRAL DE AUTOMACOES CR2 - instalacao
echo  ========================================================
echo.
echo    Vou conferir quatro coisas e instalar o que faltar:
echo.
echo      1. Git para Windows
echo      2. Python com Tkinter
echo      3. a propria Central
echo      4. o atalho na area de trabalho
echo.

rem ------------------------------------------------------------
rem  1. Git
rem ------------------------------------------------------------
echo  [1/4] Git...
call :achar_git
if defined GIT goto :git_pronto

echo        nao encontrei. Instalando pelo winget, aguarde...
call :achar_winget
if not defined WINGET goto :git_manual
winget install --id Git.Git --exact --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
rem "%ERRORLEVEL%"=="0" e nao `if not errorlevel 1`: os codigos de erro
rem do winget sao negativos, e `if errorlevel 1` significa ">= 1" - um
rem codigo negativo passaria pelo teste como se tivesse dado certo.
set "FEZ="
if "%ERRORLEVEL%"=="0" set "FEZ=1"
call :achar_git
if defined GIT goto :git_instalado
if defined FEZ goto :reabrir
goto :git_manual

:git_instalado
echo        instalado.

:git_pronto
echo        ok.
echo.

rem ------------------------------------------------------------
rem  2. Python com Tkinter
rem
rem  PrependPath=1 NAO e opcional. A Central sobrevive sem PATH
rem  (o central.bat procura o launcher `py` primeiro, e o `py`
rem  vai para C:\Windows sempre), mas os .bat das automacoes
rem  chamam `python` puro - inclusive o `python -m pip install`
rem  que instala as dependencias delas. Sem PATH, a Central abre
rem  bonita e nenhuma automacao roda.
rem
rem  Include_tcltk=1 e o Tkinter, sem o qual a janela nao abre.
rem  O instalador do python.org deixa as duas coisas DESMARCADAS
rem  por padrao, e o winget em modo silencioso nao as marca.
rem ------------------------------------------------------------
echo  [2/4] Python...
call :achar_python
if defined PY goto :python_achado

echo        nao encontrei. Instalando pelo winget, aguarde...
echo        (uns minutos: ele baixa cerca de 30 MB)
call :achar_winget
if not defined WINGET goto :python_manual
winget install --id Python.Python.3.13 --exact --silent --accept-source-agreements --accept-package-agreements --custom "PrependPath=1 Include_tcltk=1 Include_pip=1 Include_launcher=1" >nul 2>&1
set "FEZ="
if "%ERRORLEVEL%"=="0" set "FEZ=1"
call :achar_python
if defined PY goto :python_instalado
if defined FEZ goto :reabrir
goto :python_manual

:python_instalado
echo        instalado.

:python_achado
%PY% -c "import tkinter" >nul 2>&1
if errorlevel 1 goto :sem_tkinter
echo        ok, com Tkinter.
echo.

rem ------------------------------------------------------------
rem  3. A Central
rem ------------------------------------------------------------
echo  [3/4] Central...
if exist "%DEST%\.git" goto :atualizar
rem Pasta que existe com qualquer coisa dentro e assunto da pessoa,
rem nao meu: o clone falharia de qualquer forma, e com uma mensagem
rem que nao explicaria o motivo.
dir /b "%DEST%" 2>nul | findstr "." >nul && goto :pasta_ocupada

echo        baixando do GitHub...
if not exist "%LOCALAPPDATA%\CR2" md "%LOCALAPPDATA%\CR2"
git clone --quiet "%REPO%" "%DEST%"
if errorlevel 1 goto :falhou_clone
echo        instalada em %DEST%
goto :central_pronta

:atualizar
echo        ja esta instalada. Buscando novidades...
git -C "%DEST%" pull --ff-only --quiet
if errorlevel 1 echo        (nao deu para atualizar agora; segue com a versao que ja esta aqui)
echo        ok.

:central_pronta
echo.

rem ------------------------------------------------------------
rem  4. Atalho
rem
rem  O caminho da area de trabalho sai do PowerShell, e nao de
rem  %USERPROFILE%\Desktop: com o OneDrive ligado ela fica
rem  redirecionada, e o atalho iria para uma pasta que ninguem ve.
rem ------------------------------------------------------------
echo  [4/4] Atalho...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$d=[Environment]::GetFolderPath('Desktop'); $w=New-Object -ComObject WScript.Shell; $s=$w.CreateShortcut((Join-Path $d 'Central CR2.lnk')); $s.TargetPath=$env:DEST+'\central.bat'; $s.WorkingDirectory=$env:DEST; $s.Description='Central de Automacoes CR2'; $s.Save()" >nul 2>&1
if errorlevel 1 goto :sem_atalho
echo        "Central CR2" esta na area de trabalho.
goto :login

:sem_atalho
echo        nao deu para criar o atalho. O central.bat na pasta
echo        da Central funciona igual.

rem ------------------------------------------------------------
rem  O login do GitHub acontece AQUI, e nao la dentro
rem
rem  As automacoes estao em repositorios privados. Este login
rem  poderia acontecer no primeiro clique em "Instalar", mas ali
rem  a Central roda o git com CREATE_NO_WINDOW: se o Credential
rem  Manager resolvesse pedir a senha no terminal em vez de abrir
rem  janela, o pedido ficaria invisivel e a Central pareceria
rem  travada. Aqui estamos num console de verdade, que e o lugar
rem  certo para isso. Se falhar, nao interrompe a instalacao.
rem ------------------------------------------------------------
:login
echo.
echo  Login do GitHub (uma vez por maquina, para as automacoes)...
git ls-remote --heads "%REPO_PRIVADO%" >nul 2>&1
if errorlevel 1 goto :login_falhou
echo        ok, a credencial ficou guardada pelo Windows.
goto :abrir

:login_falhou
echo.
echo        Nao consegui confirmar o acesso agora, e nao ha
echo        problema nisso: a Central abre, e o primeiro clique
echo        em "Instalar" vai pedir o login. Se ele nao aparecer,
echo        rode isto uma vez num Prompt de Comando:
echo.
echo            git ls-remote %REPO_PRIVADO%
echo.

:abrir
echo.
echo  ========================================================
echo    Pronto. Abrindo a Central...
echo  ========================================================
echo.
start "" "%DEST%\central.bat"
timeout /t 3 >nul
exit /b 0


rem ============================================================
rem  Sub-rotinas
rem ============================================================

:achar_git
rem Procura no PATH e, se nao achar, nos lugares onde o
rem instalador costuma pousar. Depois de um `winget install` o
rem PATH DESTA janela ainda e o antigo, e e so por isso que a
rem segunda busca existe.
set "GIT="
where git >nul 2>&1
if not errorlevel 1 set "GIT=git"
if defined GIT goto :eof
for %%d in ("%ProgramFiles%\Git\cmd" "%ProgramFiles(x86)%\Git\cmd" "%LOCALAPPDATA%\Programs\Git\cmd") do if exist "%%~d\git.exe" call :usar_git "%%~d"
goto :eof

:achar_python
rem O launcher `py` vem primeiro de proposito: um `python` solto
rem no PATH pode ser o embutido de outro programa. O do
rem LibreOffice, por exemplo, nao tem Tkinter; a janela nao
rem abriria e o erro nao explicaria por que.
set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if defined PY goto :eof
where python >nul 2>&1
if not errorlevel 1 set "PY=python"
if defined PY goto :eof

rem Fora do PATH. Os quatro lugares abaixo cobrem o launcher para
rem todos os usuarios, o launcher so para este usuario, e a
rem instalacao do python.org nas duas formas. Nesta maquina, por
rem exemplo, C:\Windows\py.exe nao existe - o Python veio da
rem Microsoft Store, cujos atalhos ficam em WindowsApps. Por isso a
rem lista, e nao um caminho unico.
if exist "%WINDIR%\py.exe" set "PY=%WINDIR%\py.exe -3"
if defined PY goto :eof
if exist "%LOCALAPPDATA%\Programs\Python\Launcher\py.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Launcher\py.exe -3"
if defined PY goto :eof
for /d %%d in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%~d\python.exe" call :usar_python "%%~d"
if defined PY goto :eof
for /d %%d in ("%ProgramFiles%\Python3*") do if exist "%%~d\python.exe" call :usar_python "%%~d"
goto :eof

:usar_git
rem Poe a pasta do git no PATH desta janela.
set "PATH=%~1;%PATH%"
set "GIT=git"
goto :eof

:usar_python
set "PATH=%~1;%~1\Scripts;%PATH%"
set "PY=python"
goto :eof

:achar_winget
set "WINGET="
where winget >nul 2>&1
if not errorlevel 1 set "WINGET=1"
goto :eof


rem ============================================================
rem  Saidas com explicacao
rem ============================================================

:reabrir
rem O winget instalou, mas o PATH desta janela e o de antes: o cmd
rem le o PATH uma vez, ao abrir. Procurei nos lugares de sempre e
rem nao achei - em vez de chutar mais caminhos, a resposta honesta
rem e pedir para abrir de novo, o que sempre funciona.
echo.
echo   ========================================================
echo     Instalei o que faltava. Falta um passo bobo:
echo.
echo     FECHE esta janela e rode o INSTALAR.bat de novo.
echo.
echo     Motivo: o Windows so avisa os programas ja abertos sobre
echo     um programa novo quando eles reabrem. Na segunda vez ele
echo     acha tudo e vai direto ao fim.
echo   ========================================================
echo.
pause
exit /b 0

:git_manual
echo.
echo   Nao consegui instalar o Git sozinho.
echo.
echo   Baixe em  https://git-scm.com/download/win
echo   e instale clicando "Next" em tudo: o padrao serve.
echo   Depois rode este arquivo de novo.
echo.
start "" "https://git-scm.com/download/win"
pause
exit /b 1

:python_manual
echo.
echo   Nao consegui instalar o Python sozinho.
echo.
echo   Baixe em  https://www.python.org/downloads/
echo   e na PRIMEIRA tela do instalador marque as duas caixas:
echo.
echo       [x] Add python.exe to PATH
echo       [x] tcl/tk and IDLE
echo.
echo   As duas vem desmarcadas, e sem elas nada funciona.
echo   Depois rode este arquivo de novo.
echo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:sem_tkinter
echo.
echo   Este Python nao tem Tkinter, entao a janela nao abre.
echo.
echo   Reinstale o Python marcando "tcl/tk and IDLE" e rode
echo   este arquivo de novo.
echo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:pasta_ocupada
echo.
echo   Ja existe uma pasta aqui, e ela nao e um clone do git:
echo.
echo       %DEST%
echo.
echo   Nao vou mexer nela. Apague-a e rode este arquivo de novo.
echo.
pause
exit /b 1

:falhou_clone
echo.
echo   Nao consegui baixar a Central de:
echo.
echo       %REPO%
echo.
echo   Ou falta conexao, ou o GitHub recusou o acesso. Se ele
echo   pediu o login e a janela foi fechada, rode este arquivo
echo   de novo e faca o login.
echo.
pause
exit /b 1
