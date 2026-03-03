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

:: ── 2. Verificar se tag já existe ────────────────
git tag -l "!TAG!" | findstr /c:"!TAG!" > nul
if not errorlevel 1 (
    echo ERRO: Tag !TAG! ja existe. Escolha outra versao.
    goto :fail
)

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

:: ── 4. Atualizar versao no metadata.txt ──────────
echo.
echo Atualizando metadata.txt  ^(version=!VERSION!^)...
powershell -NoProfile -Command ^
    "(Get-Content 'metadata.txt') -replace '^version=.*', 'version=!VERSION!' | Set-Content 'metadata.txt' -Encoding UTF8"
if errorlevel 1 (
    echo ERRO: Falha ao atualizar metadata.txt
    goto :fail
)

:: Verificar se houve mudança real
git diff --quiet metadata.txt
if not errorlevel 1 (
    echo   ^(metadata.txt ja estava com version=!VERSION!, nenhum commit necessario^)
    set SKIP_COMMIT=1
) else (
    set SKIP_COMMIT=0
)

:: ── 5. Commit do metadata ─────────────────────────
if "!SKIP_COMMIT!"=="0" (
    echo Commitando metadata.txt...
    git add metadata.txt
    git commit -m "release: v!VERSION!"
    if errorlevel 1 (
        echo ERRO: Falha ao criar commit.
        goto :fail
    )
)

:: ── 6. Criar tag anotada ──────────────────────────
echo.
echo Criando tag anotada !TAG!...
git tag -a "!TAG!" -m "Release !TAG!"
if errorlevel 1 (
    echo ERRO: Falha ao criar tag.
    goto :fail
)

:: ── 7. Gerar zip via git archive ──────────────────
echo.
echo Gerando !ZIPNAME!...
git archive --prefix=StaraMaps/ -o "!ZIPNAME!" "!TAG!"
if errorlevel 1 (
    echo ERRO: Falha ao gerar zip.
    git tag -d "!TAG!" > nul 2>&1
    echo   ^(tag !TAG! removida^)
    goto :fail
)

:: ── 8. Resumo ─────────────────────────────────────
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

:fail
echo.
pause
endlocal
exit /b 1
