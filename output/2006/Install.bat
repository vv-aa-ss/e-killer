@echo off
set SERVICE_NAME=BITSKiller
set BINARY_PATH="C:\Program Files\EKiller\Killer_Client.exe"
set TOOL_PATH=C:\nssm-2.24\win64

echo Installing service %SERVICE_NAME%...
%TOOL_PATH% install %SERVICE_NAME% %BINARY_PATH% >nul 2>&1

echo Setting service description...
%TOOL_PATH% set %SERVICE_NAME% Description "Завершает указанный процесс во всех сеансах"

echo Setting service to auto-start...
%TOOL_PATH% set %SERVICE_NAME% Start SERVICE_AUTO_START

echo Setting logon account...
%TOOL_PATH% set %SERVICE_NAME% ObjectName LocalSystem

echo Setting display name...
%TOOL_PATH% set %SERVICE_NAME% DisplayName "BITSKiller"

echo Done.
echo Starting service...
net start %SERVICE_NAME%

pause