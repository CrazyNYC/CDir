@echo off
del cdir_out.txt

echo ======================================================= >> cdir_out.txt
call cdir.bat %SYSTEMROOT%\system32\*.ini /s >> cdir_out.txt
echo ======================================================= >> cdir_out.txt
call cdir.bat %SYSTEMROOT%\system32\*.txt /s >> cdir_out.txt
echo ======================================================= >> cdir_out.txt
call cdir.bat %SYSTEMROOT%\system32\*.log /s >> cdir_out.txt
echo ======================================================= >> cdir_out.txt
call cdir.bat %SYSTEMROOT%\system32\*.exe /s >> cdir_out.txt
echo ======================================================= >> cdir_out.txt
call cdir.bat %SYSTEMROOT%\system32\*.dll /s >> cdir_out.txt
echo ======================================================= >> cdir_out.txt

type cdir_out.txt
