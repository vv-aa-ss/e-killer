# Запуск PowerShell в виртуальном окружении
$venvPath = Join-Path $PSScriptRoot "venv"
$activateScript = Join-Path $venvPath "Scripts\Activate.ps1"

if (Test-Path $activateScript) {
    Write-Host "Активация виртуального окружения..." -ForegroundColor Green
    & $activateScript
    Write-Host "Виртуальное окружение активировано!" -ForegroundColor Green
} else {
    Write-Host "Ошибка: Файл активации не найден по пути: $activateScript" -ForegroundColor Red
    Write-Host "Убедитесь, что виртуальное окружение создано и находится в папке 'venv'" -ForegroundColor Yellow
} 