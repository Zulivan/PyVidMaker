@ECHO OFF 

TITLE tester

:Start
ECHO Run
python core/image_utils.py
TIMEOUT /T 10
GOTO:Start

PAUSE