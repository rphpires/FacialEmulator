
import uvicorn
import requests
import shutil
import subprocess
import threading

from fastapi import FastAPI, Response, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from GlobalFunctions import *
from GlobalConstants import *
from DatabaseHandler import DatabaseHandler

import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    

class Service():
    ...

    def __init__(self):
        self.service_db = DatabaseHandler('service')
        self.service_db.start()
        self.ip = get_local_ip_address()
        self.port = 8080

        ## FastAPI config.
        self.app = FastAPI()
        # self.app.mount("/static", StaticFiles(directory="static"), name="static")
        self.templates = Jinja2Templates(directory="templates")

        ## ---------------------------------------
        ## ---------- Interface Methods ----------
        ## ---------------------------------------

        @self.app.get("/", response_class=HTMLResponse)
        async def main_page(request: Request):
            return self.templates.TemplateResponse(
                request=request, name='devices.html'
            )
        
        @self.app.get("/start", response_class=HTMLResponse)
        async def start_emulators(request: Request):
            print('>>> Starting Emulators')
            self.start_emulators()
            return self.templates.TemplateResponse(
                request=request, name='devices.html'
            )
        
        @self.app.get("/stop", response_class=HTMLResponse)
        async def stop_emulators(request: Request):
            print('>>> Stoping Emulators')
            self.stop_emulators()
            return self.templates.TemplateResponse(
                request=request, name='devices.html'
            )
        
        @self.app.get("/refresh", response_class=HTMLResponse)
        async def refresh_emulators(request: Request):
            print('>>> Refreshing database')
            self.stop_emulators()
            return self.templates.TemplateResponse(
                request=request, name='devices.html'
            )


        ## ---------------------------------
        ## ---------- API Methods ----------
        ## ---------------------------------
        @staticmethod 
        def handle_response(content, response_code = 200):
            response = Response(content=content, status_code=response_code)
            response.headers["Content-Type"] = "text/plain; charset=utf-8"
            return response          
        

        @self.app.get('/api/emulators/start')
        async def api_start_emulators():
            print('>>> Starting Emulators')
            self.start_emulators()
            return {"response": "Start Emulators command: OK"}

        @self.app.get('/api/emulators/stop')
        async def api_stop_emulators():
            print('>>> Stoping Emulators')
            self.stop_emulators()
            return {"response": "Stop Emulators command: OK"}
        
        @self.app.get('/api/emulators/refresh')
        async def api_refresh_emulators():
            print('Refreshing  Emulators')
            self.refresh_configured_devices()
            return {"response": "Stop Emulators command: OK"}


    def get_missing_keys(self, local_devices, wxs_controllers_dit):
        # Obter as chaves de ambos os dicionários
        local_keys = set(local_devices.keys())
        wxs_keys = set(wxs_controllers_dit.keys())
        
        # Encontrar as chaves que estão em local_devices mas não em wxs_controllers_dit
        missing_keys = local_keys - wxs_keys
        
        # Retornar como uma lista
        return list(missing_keys)

    def refresh_configured_devices(self):
        current_controllers = []
        wxs_controllers_dit = {}

        for ctr_types in [ DAHUA_CONTROLLER_TYPES, HIKVISION_CONTROLLER_TYPES]:
            result = sql.read_data(f"""
                SELECT 
                    LocalControllerID, 
                    LocalControllerName, 
                    IPAddress, 
                    BaseCommPort, 
                    LocalControllerEnabled,
                    LocalControllerType 
                FROM CfgHWLocalControllers
                WHERE LocalControllerType in ({', '.join(str(x) for x in ctr_types)})
                AND LocalControllerEnabled = 1;
            """)
            # print(result)
            if result:
                current_controllers += result

        for id, name, ip, port, enabled, type in current_controllers:
            wxs_controllers_dit[id] = {
                'name': name,
                'ip': ip,
                'port': port,
                'type': type,
                'enabled': 1 if enabled else 0,
                'model': 'Hikvision' if type in HIKVISION_CONTROLLER_TYPES else 'Dahua' if type in DAHUA_CONTROLLER_TYPES else ' - '
            }

        get_local_lcs = "SELECT LocalControllerID, Name, IPAddress, Port, Model, Enabled, Type FROM Main;"
        local_devices = {}

        if (ret := self.service_db.select(get_local_lcs)):
            for id, name, ip, port, model, enabled, type in ret:
                local_dev = {
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'type': type,
                    'enabled': enabled,
                    'model': model
                }
                local_devices[id] = local_dev

        for key, wxs_dev in wxs_controllers_dit.items():
            if ( dev := local_devices.get(key)):
                difference = [ field for field in local_dev.keys() if dev[field] != wxs_dev[field] ]
                if difference:
                    self.service_db.execute(
                        'update Main set Name= ?, IPAddress= ?, Port= ?, Model= ?, Enabled= ?, Type= ? Where LocalControllerID= ?;', 
                        (wxs_dev["name"], wxs_dev["ip"], wxs_dev["port"], wxs_dev["model"], wxs_dev["enabled"], wxs_dev["type"], key)
                )
            else:
                self.service_db.execute(
                    'INSERT INTO Main values (?,?,?,?,?,?,?,?,?,?)', 
                    (key, wxs_dev["name"], wxs_dev["ip"], wxs_dev["port"], wxs_dev["model"], wxs_dev["enabled"], wxs_dev["type"], 0, 0, 0)
                )

        for id in self.get_missing_keys(local_devices, wxs_controllers_dit):
            self.service_db.execute(f'delete from Main where LocalControllerID= {id};')

        print(wxs_controllers_dit)


    def check_emulator_path(self, port):
        try:
            running_path = 'running'
            emulator_folder = os.path.join(running_path, str(port))

            ## Check folder: running
            if not os.path.exists(running_path):
                os.mkdir(running_path)

            ## Check each emulator's folder
            if not os.path.exists(os.path.join(running_path, str(port))):
                print(f'Creating emulator folder, PORT: {port}')
                os.mkdir(f'./{running_path}/{port}')
            else:
                print(f'Emulator PATH already exists, PORT: {port}')

            ## Check emulator executable file
            target_file = os.path.join(
                f'./{running_path}/{port}', 
                f'{os.path.splitext(EMULATOR_BASE_FILE)[0]}_{port}{os.path.splitext(EMULATOR_BASE_FILE)[1]}'
            )
            
            if not os.path.exists(target_file):
                shutil.copy2(
                    os.path.join(EMULATOR_DIST_PATH, EMULATOR_BASE_FILE), ## Source file
                    target_file
                )
                print(f'Copied and renamed file to: {target_file}')
            else:
                print(f'Executable file already exists at: {target_file}')

            return target_file, emulator_folder
        

        except Exception as ex:
            report_exception(ex)
            return None, None

    def run_emulator_process(self, processes):
        for process, port in processes:
            try:
                stdout, stderr = process.communicate()
            except Exception as ex:
                report_exception(ex)

    def start_emulators(self, innit_ports = None):
        trace('Starting emulators process')
        processes = []
        script = "select IPAddress, Port, Model, Enabled, EventInterval from Main where Enabled = 1"
        script += f" and Port in ({','.join(str(p) for p in innit_ports)});" if innit_ports else ";"
        
        read_lc_contents = self.service_db.select(script)
        for ip, port, model, enabled, evt_interval in read_lc_contents:
            try:
                trace(f'-- Sending command: {ip}, {port}, {model}, {evt_interval}')
                executavel, emulator_folder = self.check_emulator_path(port)
                emulator_path = os.path.abspath(executavel)
                try:
                    if executavel:
                        args = [emulator_path, str(ip), str(port), model, str(evt_interval)]
                        trace(f'## ARGS: {args}')
                        process = subprocess.Popen(
                            args, 
                            cwd= emulator_folder, # Define o diretório de trabalho do processo.
                            stdout=subprocess.PIPE, 
                            stderr=subprocess.PIPE, 
                            text=True
                        )
                        processes.append((process, port))

                except Exception as ex:
                    report_exception(ex)

            except Exception as ex:
                report_exception(ex)

        threading.Thread(target= self.run_emulator_process, args=(processes,)).start()
        # trace('Starting processes end.')


    def stop_emulators(self):
        for root, dirs, files in os.walk('running'):
            try:
                for file in files:
                    try:
                        # Verifica se o arquivo é chamado "PID" (sem extensão)
                        if file == "PID":
                            file_path = os.path.join(root, file)
                            try:
                                os.remove(file_path)
                                print(f"Deleted: {file_path}")
                            except Exception as e:
                                print(f"Error deleting {file_path}: {e}")
                    
                    except Exception as ex:
                        report_exception(ex)

            except Exception as ex:
                report_exception(ex)


    def recreate_emulator_files(self):
        serv.stop_emulators()
        sleep_print(3, 'recreate_emulator_files')
        try:
            if check_os() == 'Linux':
                cmd_path = '/home/invenzi/.local/bin/pyinstaller'
            elif check_os() == 'Windows':
                cmd_path = '/home/invenzi/.local/bin/pyinstaller'
            
            result = subprocess.run(
                [cmd_path, '--onefile', 'facial_emulator.py'], 
                capture_output=True, 
                text=True
            )
            
        except Exception as ex:
            report_exception(ex)
        
        if result.returncode == 0:
            trace('New exe created successfully.')
            exe_path = os.path.join('dist', EMULATOR_BASE_FILE)
            if os.path.exists(exe_path):
                trace(f'New exe created successfully at {exe_path}.')
            else:
                trace(f'Error: .exe file not found at {exe_path}.')
                trace(f'Stderr: {result.stderr}')

        else:
            trace(f'Error creating exe: {result.stderr}')
            trace(f'Stdout: {result.stdout}')

        trace('New exe created.')

        self.delete_emulator_folder_content()
        self.start_emulators()
        
    def delete_folder_content_2(self):
        # Caminho para o script shell
        shell_script_path = "./delete_content.sh"

        # Tornar o script shell executável (opcional, caso ainda não esteja)
        subprocess.run(["chmod", "+x", shell_script_path])

        # Executar o script shell
        subprocess.run([shell_script_path], check=True)


    def delete_emulator_folder_content(self):
        directory_path = 'running'
        if not os.path.exists(directory_path):
            trace(f"O diretório {directory_path} não existe.")
            return

        if not os.path.isdir(directory_path):
            print(f"{directory_path} não é um diretório.")
            return

        try:
            for filename in os.listdir(directory_path):
                file_path = os.path.join(directory_path, filename)
                if os.path.isfile(file_path) or os.path.islink(file_path):
                    os.unlink(file_path)  # Remove arquivo ou link simbólico
                    print(f"Arquivo {file_path} removido.")
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)  # Remove diretório e seu conteúdo
                    print(f"Diretório {file_path} removido.")
        except Exception as e:
            print(f"Erro ao excluir arquivos: {e}")

    # -- Erro ao excluir arquivos: [WinError 5] Access is denied: 'running\\1080\\TraceEmulator'

    def stop(self):
        self.service_db.disconnect()
        self.service_db.join()


    # def run(self):
    #     trace('Innitializing service')
    #     # self.run_server()

    #     serv.refresh_configured_devices()

    def run_server(self):
        trace('Innitializing WebService...')
        ## WebServer innitialization...
        trace(f"Starting FastAPI webServer: IP={self.ip}, Port={self.port}")
        uvicorn.run(self.app, host=self.ip, port=self.port)


def sleep_print(tempo, msg=""):
    for t in range(tempo):
        print(f'[{msg}] Sleep: {t}')
        time.sleep(t)

__os = check_os()
print(__os)

if __name__ == '__main__':
    serv = Service()
    #serv.refresh_configured_devices()
    #serv.start_emulators()

    serv.run_server()
    # serv.refresh_configured_devices()

    # serv.start_emulators()
    # print()
    # sleep_print(20)
    # serv.stop()
    
    # serv.refresh_configured_devices()
    # try:
    #     trace('Aqui')
    #     serv.start_emulators()
    
    # except Exception as ex:
    #     print(f'*** {ex}')

    # # sleep_print(20)
    # # serv.recreate_emulator_files()

    # sleep_print(20)
    # # serv.stop_emulators()
    # serv.stop()


    # if is_admin():
    #     print('admin')
    # else:
    #     print('Sem permissão')
    #     script = sys.argv[0]
    #     params = ' '.join([script] + sys.argv[1:])
    #     ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)

    # serv.recreate_emulator_files()