@echo off
setlocal enabledelayedexpansion
cls
REM Ok, this is how this works.  benchmarking creates a file in the dir below.  We ??? 
set "dir=.benchmarks\Windows-CPython-3.12-32bit"
dir ".benchmarks\Windows-CPython-3.12-32bit\*_1st.json"
rem pause

set "basefile=baseline_1st.json"

rem Loop through all files from 0001 to 0999
echo Processing files... please wait...
for /l %%i in (1,1,999) do (
    rem Format the number to always be 4 digits (e.g., 0001, 0002, ...)
    set "num=0000%%i"
    set "num=!num:~-4!"
    rem Check if the file exists
    if exist "!dir!\!num!_!basefile!" (
        rem Copy the latest file so far to benchmark.json
        echo Copying "!dir!\!num!_!basefile!" to "!dir!\!basefile!"
        copy /y "!dir!\!num!_!basefile!" "!dir!\!basefile!"
    )
)

rem After the loop, copy the last benchmark.json to baseline.json
rem copy /y benchmark.json baseline.json
dir "!dir!"
rem pause

del "%dir%\????_!basefile!"
dir "!dir!"

REM call ub2.bat
