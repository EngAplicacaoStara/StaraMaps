@echo off
setlocal EnableDelayedExpansion
chcp 65001 > nul

:: Move para o diretório do script (raiz do plugin)
cd /d "%~dp0"

echo.
echo ================================================
echo   StaraMaps - Criar Release
echo ================================================
echo.

:: ── 1. Pedir versão ──────────────────────────────
set /p VERSION=Informe a versao (ex: 1.2.2):

if "!VERSION!"=="" (
    echo ERRO: Versao nao pode ser vazia.
    goto :fail
)

:: Validar formato x.y.z  (usa PowerShell — findstr nao suporta ancora $ confiavelmente)
powershell -NoProfile -Command "if ('!VERSION!' -notmatch '^\d+\.\d+\.\d+$') { exit 1 }" > nul 2>&1
if errorlevel 1 (
    echo ERRO: Versao deve ter formato x.y.z ^(ex: 1.2.2^)
    goto :fail
)

set TAG=v!VERSION!
set ZIPNAME=StaraMaps_!VERSION!.zip

echo.
echo  Versao : !VERSION!
echo  Tag    : !TAG!
echo  Zip    : !ZIPNAME!
echo.

:: ── 3. Alertar sobre arquivos Python nao rastreados ──
echo Verificando arquivos nao rastreados...
for /f "usebackq delims=" %%F in (`git ls-files --others --exclude-standard --full-name`) do (
    echo %%F | findstr /i "\.py$" > nul
    if not errorlevel 1 (
        echo   AVISO: arquivo Python nao rastreado sera IGNORADO no zip: %%F
        set HAS_UNTRACKED_PY=1
    )
)

if defined HAS_UNTRACKED_PY (
    echo.
    echo   Se esses arquivos fazem parte do plugin, adicione-os com:
    echo     git add arquivo.py
    echo     git commit -m "..."
    echo   antes de rodar este script.
    echo.
    set /p CONTINUE=Continuar mesmo assim? [s/N]:
    if /i not "!CONTINUE!"=="s" (
        echo Operacao cancelada.
        goto :fail
    )
)

:: ── 4. Confirmar ação ─────────────────────────────
echo.
echo ------------------------------------------------
echo  O que deseja fazer?
echo.
echo  [S] Commitar metadata.txt, criar tag !TAG! e gerar zip
echo  [N] Apenas gerar o zip ^(sem commit nem tag^)
echo ------------------------------------------------
set /p CONFIRM=Escolha [S/N]:

if /i "!CONFIRM!"=="s" goto :full_release
if /i "!CONFIRM!"=="n" goto :zip_only
echo ERRO: Opcao invalida.
goto :fail

:: ── Fluxo completo: commit + tag + zip ───────────
:full_release

:: Verificar se tag já existe (só relevante ao commitar)
git tag -l "!TAG!" | findstr /c:"!TAG!" > nul
if not errorlevel 1 (
    echo ERRO: Tag !TAG! ja existe. Escolha outra versao.
    goto :fail
)

echo.
echo Atualizando metadata.txt  ^(version=!VERSION!^)...
set _VER=!VERSION!
python -c "import re,os; v=os.environ['_VER']; c=open('metadata.txt','r',encoding='utf-8').read(); c=re.sub(r'^version=.*$',f'version={v}',c,flags=re.MULTILINE); open('metadata.txt','w',encoding='utf-8',newline='\n').write(c)"
if errorlevel 1 (
    echo ERRO: Falha ao atualizar metadata.txt
    goto :fail
)

git diff --quiet metadata.txt
if not errorlevel 1 (
    echo   ^(metadata.txt ja estava com version=!VERSION!, nenhum commit necessario^)
    set SKIP_COMMIT=1
) else (
    set SKIP_COMMIT=0
)

if "!SKIP_COMMIT!"=="0" (
    echo Commitando metadata.txt...
    git add metadata.txt
    git commit -m "release: v!VERSION!"
    if errorlevel 1 (
        echo ERRO: Falha ao criar commit.
        goto :fail
    )
)

echo.
echo Criando tag anotada !TAG!...
git tag -a "!TAG!" -m "Release !TAG!"
if errorlevel 1 (
    echo ERRO: Falha ao criar tag.
    goto :fail
)

echo.
echo Gerando !ZIPNAME!...
git archive --prefix=StaraMaps/ -o "!ZIPNAME!" "!TAG!"
if errorlevel 1 (
    echo ERRO: Falha ao gerar zip.
    git tag -d "!TAG!" > nul 2>&1
    echo   ^(tag !TAG! removida^)
    goto :fail
)

echo.
echo ================================================
echo   Release !VERSION! criada com sucesso!
echo.
echo   Arquivo : !ZIPNAME!
echo   Tag     : !TAG!
echo.
echo   Proximos passos:
echo     1. git push origin main
echo     2. git push origin !TAG!
echo     3. Publicar !ZIPNAME! em https://plugins.qgis.org
echo ================================================
echo.
pause
endlocal
exit /b 0

:: ── Apenas zip: usa HEAD sem commit nem tag ───────
:zip_only

echo.
echo Gerando !ZIPNAME! a partir do HEAD atual...
git archive --prefix=StaraMaps/ -o "!ZIPNAME!" HEAD
if errorlevel 1 (
    echo ERRO: Falha ao gerar zip.
    goto :fail
)

echo.
echo ================================================
echo   Zip gerado ^(sem commit e sem tag^)
echo.
echo   Arquivo : !ZIPNAME!
echo   Commit  : HEAD ^(nenhuma tag criada^)
echo ================================================
echo.
pause
endlocal
exit /b 0

:fail
echo.
pause
endlocal
exit /b 1
