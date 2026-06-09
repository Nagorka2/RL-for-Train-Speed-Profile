import pyautogui
import time
import subprocess
import psutil
import config  # local paths/ports — copy config.example.py to config.py

# 1. Start OR
def start_OR():
    """Start the Open Rails simulation (via our custom start_OR function)."""
    file_path = config.OPENRAILS_EXE
    process = subprocess.Popen([file_path])

    # 2. Wait a few seconds for OR to open
    time.sleep(5)

    # 3. Suppose you need to click "Start" or "Run" in a menu
    # NOTE: these screen coordinates are tuned to a specific 2560x1440 monitor.
    pyautogui.moveTo(1103, 745)  # coordinates of the "Start" button
    pyautogui.click()

    # 4. Wait for scenario to load
    time.sleep(20)
    pyautogui.moveTo(1103, 745)
    pyautogui.click()
    pyautogui.keyDown("escape")
    time.sleep(0.4)
    pyautogui.keyUp("escape")
    time.sleep(0.4)
    pyautogui.keyDown("P")
    time.sleep(0.4)
    pyautogui.keyUp("P")
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'ö') #Set breaks to 0
    time.sleep(0.4)
    pyautogui.keyDown("W")
    time.sleep(0.4)
    pyautogui.keyUp("W")
    


    # Now OR is running, you can continue controlling it...
start_OR()
