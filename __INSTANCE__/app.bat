@ECHO OFF 

TITLE Video Generator of %id%

:Start
ECHO Video Generator of %id%
python app.py
TIMEOUT /T 1
GOTO:Start

PAUSE