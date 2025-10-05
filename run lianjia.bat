@echo off

echo [%DATE% %TIME%] Starting lianjia spider... >> "D:\pythonlianjia\script_log.log"
"C:\ProgramData\Anaconda3\python.exe" "D:\pythonlianjia\lianjia spider4 crawler.py" >> "D:\pythonlianjia\script_log.log" 2>&1
echo [%DATE% %TIME%] Spider finished. >> "D:\pythonlianjia\script_log.log"

echo [%DATE% %TIME%] Starting email sender... >> "D:\pythonlianjia\script_log.log"
"C:\ProgramData\Anaconda3\python.exe" "D:\pythonlianjia\lianjia sendmail.py" >> "D:\pythonlianjia\script_log.log" 2>&1
echo [%DATE% %TIME%] Email sent. >> "D:\pythonlianjia\script_log.log"

echo All tasks completed. Log saved to D:\pythonlianjia\script_log.log
pause