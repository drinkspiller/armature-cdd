@echo off
setlocal EnableDelayedExpansion
:: =============================================================================
:: Armature (OSS) Skills & Rules Installer (Windows)
:: =============================================================================

set "VERSION=0.22.2"
set "FLAGS_dry_run=0"
set "FLAGS_force=0"
set "FLAGS_uninstall=0"
set "FLAGS_update=0"

:: Parse arguments
:parse_args
if "%~1"=="" goto :args_done
if /i "%~1"=="--dry_run" ( set "FLAGS_dry_run=1" & shift & goto :parse_args )
if /i "%~1"=="--force" ( set "FLAGS_force=1" & shift & goto :parse_args )
if /i "%~1"=="--uninstall" ( set "FLAGS_uninstall=1" & shift & goto :parse_args )
if /i "%~1"=="--update" ( set "FLAGS_update=1" & shift & goto :parse_args )
if /i "%~1"=="--help" ( goto :show_help )
if /i "%~1"=="-h" ( goto :show_help )
echo Unknown argument: %~1
exit /b 1

:show_help
echo Usage: install.bat [OPTIONS]
echo   --dry_run    Preview changes without writing files
echo   --force      Overwrite existing files without backup
echo   --update     Update to the latest version (implies --force)
echo   --uninstall  Remove all installed files
echo   --help, -h   Show this help message
exit /b 0

:args_done

set "SCRIPT_DIR=%~dp0"
if "%SCRIPT_DIR:~-1%"=="\" set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

set "SOURCE_ASSETS_DIR=%SCRIPT_DIR%\skills\arm-setup\assets"
set "SOURCE_RULES_DIR=%SCRIPT_DIR%\rules"

set "TARGET_PLUGIN_DIR=%USERPROFILE%\.gemini\config\plugins\armature-cdd"
set "TARGET_SKILLS_ROOT=%TARGET_PLUGIN_DIR%\skills"
set "TARGET_RULES_ROOT=%TARGET_PLUGIN_DIR%\rules"
set "TARGET_ASSETS_DIR=%TARGET_SKILLS_ROOT%\arm-setup\assets"
set "TARGET_MANIFEST_ROOT=%TARGET_PLUGIN_DIR%"

echo.
echo   ==================================================
echo     Armature (OSS) Installer (Windows) v%VERSION%
echo   ==================================================
echo.

if "%FLAGS_update%"=="1" (
    set "FLAGS_force=1"
    if exist "%TARGET_SKILLS_ROOT%\arm-setup\.armature_version" (
        set /p INSTALLED_VERSION= < "%TARGET_SKILLS_ROOT%\arm-setup\.armature_version"
        if "!INSTALLED_VERSION!"=="%VERSION%" (
            echo Already up to date (v%VERSION%^)
            exit /b 0
        )
        echo   Installed: v!INSTALLED_VERSION! -^> v%VERSION%
    ) else (
        echo   No existing installation found. Performing fresh install.
    )
    echo.
)

if "%FLAGS_uninstall%"=="1" goto :do_uninstall

:: Validate sources
if not exist "%SOURCE_ASSETS_DIR%\workflow_template.md" ( echo [ERROR] Missing %SOURCE_ASSETS_DIR%\workflow_template.md & exit /b 1 )
if not exist "%SOURCE_ASSETS_DIR%\adr_template.md" ( echo [ERROR] Missing %SOURCE_ASSETS_DIR%\adr_template.md & exit /b 1 )
if not exist "%SOURCE_ASSETS_DIR%\manual_testing_template.md" ( echo [ERROR] Missing %SOURCE_ASSETS_DIR%\manual_testing_template.md & exit /b 1 )
for %%S in (arm-setup arm-new-track arm-implement arm-status arm-review arm-revert arm-drift arm-chat arm-new-bug-bash arm-bash arm-bug-bash-triage) do (
    if not exist "%SCRIPT_DIR%\skills\%%S\SKILL.md" ( echo [ERROR] Missing %SCRIPT_DIR%\skills\%%S\SKILL.md & exit /b 1 )
)

if "%FLAGS_dry_run%"=="1" echo   [DRY RUN MODE - no files will be written]

:: Cleanup deprecated sub-skills & legacy conductor plugin directories
for %%O in (conductor-setup conductor-new-track conductor-implement conductor-status conductor-review conductor-revert conductor-drift conductor-chat conductor) do (
    if exist "%USERPROFILE%\.gemini\antigravity\skills\%%O" (
        if "%FLAGS_dry_run%"=="1" (
            echo Would remove legacy directory: %USERPROFILE%\.gemini\antigravity\skills\%%O
        ) else (
            rmdir /s /q "%USERPROFILE%\.gemini\antigravity\skills\%%O"
            echo Removed legacy directory: %USERPROFILE%\.gemini\antigravity\skills\%%O
        )
    )
)

:: Assets
echo.
echo --- Installing Armature Assets ---
call :install_file "%SOURCE_ASSETS_DIR%\workflow_template.md" "%TARGET_ASSETS_DIR%\workflow_template.md"
call :install_file "%SOURCE_ASSETS_DIR%\adr_template.md" "%TARGET_ASSETS_DIR%\adr_template.md"
call :install_file "%SOURCE_ASSETS_DIR%\manual_testing_template.md" "%TARGET_ASSETS_DIR%\manual_testing_template.md"

:: Version Stamp
if "%FLAGS_dry_run%"=="1" (
    echo Would write version file: .armature_version
) else (
    if not exist "%TARGET_SKILLS_ROOT%\arm-setup" mkdir "%TARGET_SKILLS_ROOT%\arm-setup"
    echo %VERSION%> "%TARGET_SKILLS_ROOT%\arm-setup\.armature_version"
    echo %VERSION%> "%TARGET_PLUGIN_DIR%\.armature_version"
    echo Wrote version stamp: v%VERSION%
)

:: Manifests
echo.
echo --- Installing Armature Plugin Manifests ---
if exist "%SCRIPT_DIR%\plugin.json" call :install_file "%SCRIPT_DIR%\plugin.json" "%TARGET_MANIFEST_ROOT%\plugin.json"
if exist "%SCRIPT_DIR%\README.md" call :install_file "%SCRIPT_DIR%\README.md" "%TARGET_MANIFEST_ROOT%\README.md"
if exist "%SCRIPT_DIR%\CHANGELOG.md" call :install_file "%SCRIPT_DIR%\CHANGELOG.md" "%TARGET_MANIFEST_ROOT%\CHANGELOG.md"
if exist "%SCRIPT_DIR%\.claude-plugin\marketplace.json" call :install_file "%SCRIPT_DIR%\.claude-plugin\marketplace.json" "%TARGET_MANIFEST_ROOT%\.claude-plugin\marketplace.json"

:: Sub-Skills
echo.
echo --- Installing Armature Command Skills ---
for %%S in (arm-setup arm-new-track arm-implement arm-status arm-review arm-revert arm-drift arm-chat arm-new-bug-bash arm-bash arm-bug-bash-triage) do (
    call :install_file "%SCRIPT_DIR%\skills\%%S\SKILL.md" "%TARGET_SKILLS_ROOT%\%%S\SKILL.md"
)

:: Rules
echo.
echo --- Installing Armature Rules ---
for %%R in (armature_protocol.md armature_antigravity.md armature_adr_preflight.md armature_cdd_protocols.md) do (
    call :install_file "%SOURCE_RULES_DIR%\%%R" "%TARGET_RULES_ROOT%\%%R"
)

echo.
echo --- Summary ---
echo   Target:       armature-cdd
echo   Skills root:  %TARGET_SKILLS_ROOT%\arm-*\
echo   Rules dir:    %TARGET_RULES_ROOT%
if "%FLAGS_dry_run%"=="1" ( echo   Dry run complete. ) else ( echo   Installation complete! )
call :check_for_updates
exit /b 0

:do_uninstall
echo --- Uninstalling Armature ---
if exist "%TARGET_PLUGIN_DIR%" (
    if "%FLAGS_dry_run%"=="1" (
        echo Would remove: %TARGET_PLUGIN_DIR%
    ) else (
        rmdir /s /q "%TARGET_PLUGIN_DIR%"
        echo Removed: %TARGET_PLUGIN_DIR%
    )
)
echo Uninstall complete.
exit /b 0

:check_for_updates
echo.
if exist "%TARGET_SKILLS_ROOT%\arm-setup\.armature_version" (
    set /p INSTALLED_VERSION= < "%TARGET_SKILLS_ROOT%\arm-setup\.armature_version"
    if "!INSTALLED_VERSION!"=="%VERSION%" (
        echo   [OK] armature-cdd: Up to date (v!INSTALLED_VERSION!^)
    ) else (
        echo   [NEW] armature-cdd: Update available - v!INSTALLED_VERSION! -^> v%VERSION%
        echo   To update, run: install.bat --update
    )
) else (
    echo   No existing Armature installations found.
    echo   Run install.bat to install.
)
exit /b 0

:install_file
set "source=%~1"
set "target=%~2"

for %%F in ("%target%") do set "target_dir=%%~dpF"
for %%F in ("%target%") do set "base_name=%%~nxF"

if not exist "%target_dir%" (
    if "%FLAGS_dry_run%"=="1" (
        echo Would create directory: %target_dir%
    ) else (
        mkdir "%target_dir%"
        echo Created directory: %target_dir%
    )
)

if exist "%target%" (
    fc "%source%" "%target%" >nul
    if not errorlevel 1 (
        echo %base_name% (already up-to-date)
        exit /b 0
    )
    if "%FLAGS_force%"=="0" (
        if "%FLAGS_dry_run%"=="1" (
            echo Would backup: %target% -^> %target%.bak
        ) else (
            copy /y "%target%" "%target%.bak" >nul
            echo Backed up: %base_name% -^> %base_name%.bak
        )
    )
)

if "%FLAGS_dry_run%"=="1" (
    echo Would install: %base_name%
) else (
    copy /y "%source%" "%target%" >nul
    echo Installed: %base_name%
)
exit /b 0

