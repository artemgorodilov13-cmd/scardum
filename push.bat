@echo off
chcp 65001 >nul
echo === Подготовка файлов ===
git add .
echo.
set /p msg="Введи сообщение коммита (что изменил?): "
if "%msg%"=="" set msg="Автоматическое обновление"
echo.
echo === Отправка на GitHub ===
git commit -m "%msg%"
git push
echo.
echo === Готово! ===
pause