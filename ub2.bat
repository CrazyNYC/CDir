@echo off
::
:: This file updates the benchmark data for the project whose main dir we're in, 
::  and that every subsequent pytest run will compare to.  The latest data, if available, 
::  will be used.
::
:: - this script needs to be in the project main directory (ex. h:\Users\<user>\PycharmProjects\<projdir>)
:: - this script is only a wrapper for the main script ub_main.bat
:: - 
setlocal enabledelayedexpansion
:: enable color vars
call set_ansi_colors.bat /ON >nul

:: call main script
call ub_main.bat %~dpnx0 %*

goto :end

:end
:: disable color vars
call set_ansi_colors.bat /OFF >nul
endlocal

goto :eof  :: return from this script
