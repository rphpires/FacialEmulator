#!/usr/bin/env python
# -*- coding: utf-8 -*- 

import sys
import signal
import os
import pathlib
# from PyInstaller.utils.hooks import collect_all

from DatabaseHandler import DatabaseHandler
from GlobalFunctions import *

from EmulatorDahua import DahuaEmulator
from EmulatorHikvision import HikvisionEmulator

# datas, binaries, hiddenimports = collect_all('pyarmor')

if __name__ == "__main__":
    try:
        trace('## Starting Emulator process: v1.0')
        trace(f'Args: {sys.argv}')
        # cwd = pathlib.Path(__file__).parent.resolve()

        if len(sys.argv) == 1: ## Debug Mode
            print("Required: python facial_emulator.py <IP Address> <port> <Device Type>")
            ip = '172.16.17.47'
            port = 8030
            device_type = 'Dahua'
            event_freq = 10 ## Seconds
            log_init_file = '.log.ini'
        else:
            ip = sys.argv[1]
            port = int(sys.argv[2])
            device_type = sys.argv[3]
            if len(sys.argv) == 5:
                trace('Setting interval to generate fake events')
                event_freq = int(sys.argv[4]) ## Seconds 
            else:
                event_freq = 0
            log_init_file = '../../.log.ini'
    
        # innitialize_tracer(port)   
        trace(f'Innitializing emulator with parameters: Device Type= {device_type}, IP= {ip} and Port= {port}') 

    except Exception as ex:
        report_exception(ex)

    try:
        db_handler = DatabaseHandler('emulator')
        db_handler.start()

    except Exception as ex:
        report_exception(ex)
    
    
    match device_type.upper():
        case "DAHUA":
            d = DahuaEmulator(ip, port, db_handler, event_freq, log_init_file)
            d.start()
            active_emulator = d

        case "HIKVISION":
            h = HikvisionEmulator(ip, port, db_handler, event_freq, log_init_file)
            h.start()
            active_emulator = h            
        
        case _:
            trace('Nenhum device identificado com este nome, opções possíveis: Dahua e Hikvision.')

    def turn_off(*arg):
        trace('Killing Emulator process...')
        time.sleep(2)
        if os.path.exists("PID"):
            os.remove("PID")
        os.kill(_pid, signal.SIGTERM)
    
    f = open('PID', 'w')
    _pid = os.getpid()
    f.write(str(_pid))
    f.close()

    while True:
        time.sleep(2)
        ## Caso o arquivo com o PID (Process ID do windows) seja excluído, encerrar o processo do Emulador.
        if not os.path.exists("PID"):
            turn_off()

        ## Quando o programa é executado no prompt ou no IDE, encerrar o processo no comando "Crtl+C"
        signal.signal(signal.SIGINT, turn_off) 
