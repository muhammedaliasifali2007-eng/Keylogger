# Keylogger
This script logs confirmed system-wide keystrokes to a local text file until Esc, or saves running processes and network connections to a CSV. It needs pynput and psutil. It does not upload data, but typing mode can capture passwords and private messages.

Download and install Python for Windows (choose 64-bit and tick Add Python to PATH).

Then open PowerShell in the script folder and run:

py -m pip install pynput psutil

py keylogger.py typing

Use audit instead of typing for the process/network report. pynput supports keyboard monitoring and psutil provides process/network information. pynput · psutil
