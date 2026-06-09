import subprocess
import time
import os
import signal

# Tiden i sekunder (2 timmar + 10 min)
restart_interval =  3600 + 600/2


while True:
    print("Startar main.py...")
    # Starta main.py (justera kommandot om du använder en specifik Python-version eller virtuell miljö)
    process = subprocess.Popen(["python", "main.py"])
    
    start_time = time.time()
    # Vänta i små intervaller och kolla om processen avslutats i förtid
    while time.time() - start_time < restart_interval:
        time.sleep(60)  # kolla var minut
        ret = process.poll()
        if ret is not None:
            # Processen avslutades själv
            break

    # Om main.py fortfarande körs, avsluta den
    if process.poll() is None:
        print("2 timmar har passerat, startar om main.py...")
        try:
            # På Windows kan du använda process.terminate()
            process.terminate()
            process.wait(timeout=30)
        except Exception as e:
            print("Fel vid avslutning, försöker kill:", e)
            process.kill()
            process.wait()
    else:
        print("main.py avslutades själv, startar om direkt.")
    
    # Liten paus innan nästa start
    time.sleep(1)
