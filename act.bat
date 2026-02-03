REM @echo off
call h:\Users\emues\util\py_activate.bat %0 %*
REM %~dp0\.venv\Scripts\activate.bat

if defined DEBUG (
	echo VIRTUAL_ENV=%VIRTUAL_ENV%
	echo _OLD_CODEPAGE%_OLD_CODEPAGE% 
	echo _OLD_VIRTUAL_PROMPT=%_OLD_VIRTUAL_PROMPT% 
	echo _OLD_VIRTUAL_PYTHONHOME=%_OLD_VIRTUAL_PYTHONHOME%
	echo PYTHONHOME=%PYTHONHOME%
	echo PATH=%PATH%
	echo %%
	echo %%
	echo %%
)
