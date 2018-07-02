import sys

import logging

# sys.path.append('C:\\Dimatica\\onLine\\src\\innovapos')
from innovapos.worker.worker import HardwareWorker

worker: HardwareWorker = HardwareWorker()

import sys
import psutil
import subprocess
import time
import os


def startProcess():
    # return
    # verificamos Procesos que se estan ejecutando
    time.sleep(0.5)
    for i in psutil.pids():
        process = psutil.Process(i)
        if process.name() == '3001' or process.name() == 'CCM' or process.name() == 'Sockmon' or process.name() == 'Sockserver':
            process.kill()
            print(f'Matando proceso: {process.name()}')

    # EJECUTAMOS LOS PROCESOS


    time.sleep(2)
    path3001 = f'/home/pi/AppInnova/Eject/3001'
    pathCCM = f'/home/pi/AppInnova/Eject/CCM'
    pathSockserver = f'/home/pi/AppInnova/Eject/Sockserver'
    pathSockmon = f'/home/pi/AppInnova/Eject/Sockmon'
    print('HMS: Ejecutando 3001')
    status3001 = subprocess.Popen([path3001])
    time.sleep(1)
    print('HMS: Ejecutando CCM')
    statusCCM = subprocess.Popen([pathCCM])
    time.sleep(1)
    print('HMS: Ejecutando Sockserver')
    statusSockserver = subprocess.Popen([pathSockserver])
    time.sleep(1)
    print('HMS: Ejecutando Sockmon')
    # statusSockmon = subprocess.Popen([pathSockmon])


if __name__ == "__main__":
    time.sleep(2)
    # TODO: Solo linux
    #os.system("fuser -k 3000/tcp")
    #os.system("fuser -k 3001/tcp")
    config_path = "configs/innovapos_worker+simulator.config"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]
    logging.info("Hello")
    worker.configure_from_config_file(config_path)
    import innovapos.worker.tasks.interaction
    import innovapos.worker.tasks.selling
    import innovapos.worker.tasks.debug

    # TODO: Solo linux
    #startProcess()
    worker.run_with_autorecover()
