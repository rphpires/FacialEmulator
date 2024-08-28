
import uvicorn
import requests
import shutil
import subprocess
import threading
import schedule
import asyncio
import socketio
import os

from fastapi import FastAPI, Response, Request, WebSocket
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from fastapi_socketio import SocketManager

from GlobalFunctions import *
from GlobalConstants import *
from DatabaseHandler import DatabaseHandler

import ctypes

load_dotenv()

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False
    

## Teste new repository
class Service():
    ...

    def __init__(self):
        self.service_db = DatabaseHandler('service')
        self.service_db.start()
        self.ip = get_local_ip_address()
        self.port = 8080

        # self.api_server = os.getenv("WXS_API_SERVER")
        # self.api_user = os.getenv("WXS_API_USER")
        # self.api_password = os.getenv("WXS_API_PASSWORD")
        # self.api_url = 

        ## FastAPI config.
        self.app = FastAPI()
        self.sio = socketio.AsyncServer(async_mode='asgi')
        self.app.mount('/socket.io', socketio.ASGIApp(self.sio))
        self.templates = Jinja2Templates(directory="templates")


    
        self.init_devices()

        ## ---------------------------------------
        ## ---------- Interface Methods ----------
        ## ---------------------------------------
        @self.sio.on('connect')
        async def connect(sid, _):
            print('Client connected')

        @self.sio.on('disconnect')
        async def disconnect(sid):
            print('Client disconnected')


        class Devices(BaseModel):
            devices: list[str]

        @self.app.api_route("/", methods=["GET", "POST"], response_class=HTMLResponse)
        async def main_page(request: Request, page: int = 1, per_page: int = 10):
            devices = self.get_current_devices()
            # Paginação
            total_devices = len(devices)
            start = (page - 1) * per_page
            end = start + per_page
            paginated_devices = devices[start:end]

            total_pages = (total_devices + per_page - 1) // per_page  # Calcula o total de páginas

            context = {
                "request": request,
                "devices": paginated_devices,
                "page": page,
                "total_pages": total_pages,
                "per_page": per_page,
            }
            return self.templates.TemplateResponse('devices.html', context )
       
        @self.app.post("/start", response_class=HTMLResponse)
        async def start_emulators(request: Request, devices: Devices):
            print('>>> Starting Emulators')
            self.start_emulators(devices.devices)
            return RedirectResponse(url="/")

        @self.app.post("/stop", response_class=HTMLResponse)
        async def stop_emulators(request: Request, devices: Devices):
            print('>>> Stoping Emulators')
            self.stop_emulators(devices.devices)
            return RedirectResponse(url="/")
            
        @self.app.get("/refresh", response_class=HTMLResponse)
        async def refresh_emulators(request: Request):
            print('>>> Refreshing database')
            self.refresh_configured_devices()
            return RedirectResponse(url="/")

        @self.app.get("/recreate", response_class=HTMLResponse)
        async def recreate_emulators(request: Request):
            print('>>> Recreating emulator executable: BEGIN')
            self.recreate_emulator_files()
            print('>>> Recreating emulator executable: END')
            return RedirectResponse(url="/?recreate=true")
        
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

    ## -------------------------------------
    ## ---------- Class Functions ----------
    ## -------------------------------------


    def init_devices(self):
        self.devices_watchdog = {}
        for device in self.get_current_devices():
            self.devices_watchdog[device["port"]] = 0
            self.service_db.execute(f"update Main set status = 'stopped' where LocalControllerID = {device['lc_id']};")


    def get_current_devices(self):
        current_devices = []
        result = self.service_db.select(f"""
select LocalControllerID, Name, IpAddress, Port, Model, Status, Enabled, EventInterval, TotalUsers from Main;
""")
        if result:
            for lc_id, name, ip, port, model, status, enabled, interval, total in result:
                current_devices.append({
                    "lc_id": lc_id,
                    "name": name,
                    "ip_address": ip,
                    "port": port,
                    "model": model,
                    "status": status,
                    "enabled": enabled,
                    "interval": interval,
                    "total" : total
                })
                
        return current_devices
    
    def get_missing_keys(self, local_devices, wxs_controllers_dit):
        # Obter as chaves de ambos os dicionários
        local_keys = set(local_devices.keys())
        wxs_keys = set(wxs_controllers_dit.keys())
        
        # Encontrar as chaves que estão em local_devices mas não em wxs_controllers_dit
        missing_keys = local_keys - wxs_keys
        
        # Retornar como uma lista
        return list(missing_keys)

    def refresh_configured_devices(self):
        wxs_controllers_dit = {}

        result = sql.read_data(f"""
            SELECT 
                LocalControllerID, 
                LocalControllerName, 
                IPAddress, 
                BaseCommPort, 
                LocalControllerEnabled,
                LocalControllerType,
                LocalControllerDescription 
            FROM CfgHWLocalControllers
            WHERE LocalControllerDescription like 'emulator%';
        """)
        # print(result)
        if not result:
            trace("There aren't available controllers to be create as emulators.")
            return False

        for id, name, ip, port, enabled, type, description in result:
            if type not in DAHUA_CONTROLLER_TYPES + HIKVISION_CONTROLLER_TYPES:
                trace(f'Skipping LocaController "{name}", because LocalControllerType is not valid.')
                continue

            if len(description.split('_')) == 2:
                try:
                    event_interval = int(description.split('_')[1])
                except Exception as ex:
                    trace(f'Error getting event time interval, description= {description}')
                    event_interval = 0

            wxs_controllers_dit[id] = {
                'name': name,
                'ip': ip,
                'port': port,
                'type': type,
                'enabled': 1 if enabled else 0,
                'interval': event_interval,
                'model': 'Hikvision' if type in HIKVISION_CONTROLLER_TYPES else 'Dahua' if type in DAHUA_CONTROLLER_TYPES else ' - '
            }


        get_local_lcs = "SELECT LocalControllerID, Name, IPAddress, Port, Model, Enabled, Type, EventInterval FROM Main;"
        local_devices = {}

        if (ret := self.service_db.select(get_local_lcs)):
            for id, name, ip, port, model, enabled, type, interval in ret:
                local_dev = {
                    'name': name,
                    'ip': ip,
                    'port': port,
                    'type': type,
                    'enabled': enabled,
                    'model': model,
                    'interval' : interval
                }
                local_devices[id] = local_dev

        for key, wxs_dev in wxs_controllers_dit.items():
            if ( dev := local_devices.get(key)):
                difference = [ field for field in local_dev.keys() if dev[field] != wxs_dev[field] ]
                if difference:
                    self.service_db.execute(
                        'update Main set Name= ?, IPAddress= ?, Port= ?, Model= ?, Enabled= ?, Type= ?, EventInterval= ? Where LocalControllerID= ?;', 
                        (wxs_dev["name"], wxs_dev["ip"], wxs_dev["port"], wxs_dev["model"], wxs_dev["enabled"], wxs_dev["type"], wxs_dev["interval"], key)
                )
            else:
                self.service_db.execute(
                    'INSERT INTO Main values (?,?,?,?,?,?,?,?,?,?)', 
                    (key, wxs_dev["name"], wxs_dev["ip"], wxs_dev["port"], wxs_dev["model"], wxs_dev["enabled"], wxs_dev["type"], 'stopped', wxs_dev["interval"], 0)
                )

        for id in self.get_missing_keys(local_devices, wxs_controllers_dit):
            self.service_db.execute(f'delete from Main where LocalControllerID= {id};')

        print(wxs_controllers_dit)
        self.init_devices()

    def get_wxs_local_controllers(self):
        print('get controllers')
        get_lcs = requests.get(f"http://{self.api_server}")
        return False


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
                f'{os.path.splitext(EMULATOR_BASE_FILE)[0]}_{port}{os.path.splitext(EMULATOR_BASE_FILE)[1]}'.replace('_unix', '').replace('_win', '')
            )

            if not os.path.exists(os.path.join(EMULATOR_DIST_PATH, EMULATOR_BASE_FILE)):
                self.recreate_emulator_files()

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

    def start_emulators(self, devices = None): ## TODO: verificar se o processo já está em execução, se estiver não iniciar 
        trace(f'Starting emulators process: {devices}')
        try:
            processes = []
            script = "select IPAddress, Port, Model, Enabled, EventInterval from Main where Enabled = 1"
            if 'all' in devices:
                script += ";"
            else:
                script += f" and Port in ({','.join(str(p) for p in devices)});"

            trace(script)
        
        except Exception as ex:
            report_exception(ex)

        read_lc_contents = self.service_db.select(script)
        for ip, port, model, enabled, evt_interval in read_lc_contents:
            try:
                trace(f'-- Sending command: {ip}, {port}, {model}, {evt_interval}')
                executavel, emulator_folder = self.check_emulator_path(port)
                emulator_path = os.path.abspath(executavel)
                try:
                    if executavel:
                        args = [emulator_path, str(ip), str(port), model, str(evt_interval)]
                        if self.get_pids_of_running_process(port) == ['']:
                            trace(f'## ARGS: {args}')
                            process = subprocess.Popen(
                                args, 
                                cwd= emulator_folder, # Define o diretório de trabalho do processo.
                                stdout=subprocess.PIPE, 
                                stderr=subprocess.PIPE, 
                                text=True
                            )
                            processes.append((process, port))
                        else:
                            trace(f'Port: {port}, process is already running.')

                except Exception as ex:
                    report_exception(ex)

            except Exception as ex:
                report_exception(ex)

        threading.Thread(target= self.run_emulator_process, args=(processes,)).start()
        # trace('Starting processes end.')


    def stop_emulators(self, devices):
        for root, dirs, files in os.walk('running'):
            try:
                # print(dirs)
                for file in files:
                    try:
                        # Verifica se o arquivo é chamado "PID" (sem extensão)
                        if file == "PID":
                            if 'all' in devices or root.split('/')[1] in devices:
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
        serv.stop_emulators(['all'])
        # sleep_print(3, 'recreate_emulator_files')
        try:
            try:
                build_dir = os.path.join(os.path.dirname(__file__), 'build')
                trace(f'Before recreate executable, delete "build" path: {build_dir}')
                if os.path.exists(build_dir):
                    shutil.rmtree(build_dir)
                
            except Exception as ex:
                report_exception(ex)

            if check_os() == 'Linux':
                cmd_path = 'pyinstaller'
            elif check_os() == 'Windows':
                cmd_path = 'pyinstaller'
            
            result = subprocess.run(
                [cmd_path, '--onefile', 'facial_emulator.py', f'--name={EMULATOR_BASE_FILE}'], 
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
        #self.start_emulators()


    def delete_emulator_folder_content(self):
        directory_path = 'running'
        if not os.path.exists(directory_path):
            trace(f"O diretório {directory_path} não existe.")
            return

        if not os.path.isdir(directory_path):
            print(f"{directory_path} não é um diretório.")
            return

        try:
            root_dir = os.path.join(os.path.dirname(__file__), 'running')
            for subdir, _, files in os.walk(root_dir):
                for file in files:
                    if 'facial_emulator' in file:
                        file_path = os.path.join(subdir, file)
                        try:
                            os.remove(file_path)
                        except Exception as ex:
                            report_exception(ex)

        except Exception as e:
            print(f"Erro ao excluir arquivos: {e}")

    def stop(self):
        self.service_db.disconnect()
        self.service_db.join()

    def update_total_users(self, device, total):
        self.service_db.execute(f"update Main set TotalUsers = {total} where LocalControllerID = {device['lc_id']};")

    def check_connection(self, device):
        try:
            get_conn = requests.get(f'http://{device["ip_address"]}:{device["port"]}/emulator/get-status', timeout=2)  
            if get_conn.status_code in [200]: 
                return get_conn.json()
            else:
                print(f'Failed or offline: {device["ip_address"]}:{device["port"]} = {get_conn.status_code} | TotalUsers: {get_conn.content}')
                return False      
            
        except requests.exceptions.RequestException:
            print(f'Failed or offline: {device["ip_address"]}:{device["port"]} | Current Status= {device["status"]}')
            return False

    async def update_device_status(self, device_id: int, status: str):
        trace(f'------ Gerando update para o controlador: {device_id}')
        await self.sio.emit('update_device_status', {'device_id': device_id, 'updated_html': self.format_device_template(device_id) })

    async def refresh_device_status(self):
        for dev in self.get_current_devices():
            try:
                if (ret := self.check_connection(dev)):
                    print(f'>> {dev["ip_address"]}:{dev["port"]} = OK | Current Status= {dev["status"]} |  DeviceInfo: {ret}')
                    self.update_total_users(dev, ret["TotalUsers"])
                    self.devices_watchdog[dev['port']] = 0
                    if dev["status"] != "running":
                        self.service_db.execute(f"update Main set status = 'running' where LocalControllerID = {dev['lc_id']};")
                        await self.update_device_status(dev["lc_id"], 'running')
                    continue
                else:
                    self.emulator_watchdog(dev)
                    if dev["status"] != "stopped":
                        self.service_db.execute(f"update Main set status = 'stopped' where LocalControllerID = {dev['lc_id']};")
                        await self.update_device_status(dev["lc_id"], 'running')

            except requests.exceptions.RequestException  as ex:
                self.emulator_watchdog(dev)
                if dev["status"] != "stopped":
                    self.service_db.execute(f"update Main set status = 'stopped' where LocalControllerID = {dev['lc_id']};")
                    await self.update_device_status(dev["lc_id"], 'running')

    def get_pids_of_running_process(self, device_port):
        try:
            pgrep_cmd = f"ps aux | grep 'facial_emulator_{device_port}' | grep -v grep | awk '{{print $2}}'"
            result = subprocess.run(pgrep_cmd, shell=True, check=True, stdout=subprocess.PIPE, text=True)
            _r = result.stdout.strip().split('\n')
            trace(f"get_pids_of_running_process.port = {device_port} | return: {_r}.")
            return _r
        
        except Exception as ex:
            report_exception(ex)
            return ['']

    def emulator_watchdog(self, device):
        try:
            print(f'--- counter = {self.devices_watchdog[device["port"]]}')
            if (pids := self.get_pids_of_running_process(device["port"])) != [""]:
                print(f'--- PORT= {device["port"]} | PIDS: {pids}')
                if self.devices_watchdog[device['port']] > 3:
                    error(f'Emulator Port= {device["port"]} is not running correctly... killing process.')
                    for pid in pids:
                        try:
                            kill_cmd = f"kill -9 {pid}"
                            subprocess.run(kill_cmd, shell=True, check=True)
                            trace(f"Processo {pid} finalizado.")
                        except:
                            error(f'error killing process: {pid}')

                    threading.Thread(target=self.start_emulator_with_delay, args=(device['port'],)).start()
                    self.devices_watchdog[device['port']] = 0
                else:
                    self.devices_watchdog[device['port']] += 1

            else:
                self.devices_watchdog[device['port']] = 0
        
        except Exception as ex:
            report_exception(ex)

    def format_device_template(self, device_id):
        try:
            result = self.service_db.select(f"select Name, Port, EventInterval, Status, TotalUsers from Main where LocalControllerID = {device_id};")
            trace(f"format_device_template: {result}")
            name, port, interval, status, total = result[0]
        except Exception as ex:
            report_exception(ex)

        _template = device_template.replace("$lc_id", str(device_id))
        _template = _template.replace("$name", str(name))
        _template = _template.replace("$port", str(port))
        _template = _template.replace("$interval", str(interval))
        _template = _template.replace("$total", str(total))

        if status == 'running':
            button_start = 'btn-custom-disabled'
            button_stop = ""
            status_obj = f"""
                <td class="text-center">
                    <span class="border border-success" style="padding: 5px; border-radius: 5px; color: #117529;">{status}</span>
                </td>"""
        else:
            button_start = ""
            button_stop = "btn-custom-disabled"
            status_obj = f"""
                <td class="text-center">
                    <span class="border border-danger" style="padding: 5px; border-radius: 5px; color: #a70000;">{status}</span>
                </td>"""

        _template = _template.replace('$buttonStart', button_start)
        _template = _template.replace('$buttonStop', button_stop)
        _template = _template.replace('$statusObj', status_obj)

        return _template



    def start_emulator_with_delay(self, device_port):
        time.sleep(3)
        self.start_emulators([device_port])

    def refresh_device_status_wrapper(self):
        asyncio.run(self.refresh_device_status())

    def scheduler(self):
        schedule.every(10).seconds.do(self.refresh_device_status_wrapper)
        while True:
            schedule.run_pending()   
            time.sleep(1)

    def run_server(self):
        trace('Innitializing WebService...')

        ## Start Thread to scheduled functions
        threading.Thread(target=self.scheduler).start()

        ## WebServer innitialization...
        trace(f"Starting FastAPI webServer: IP={self.ip}, Port={self.port}")
        uvicorn.run(self.app, host=self.ip, port=self.port)

    
device_template = """
<tr id="device_$lc_id">
<td class="text-center">$lc_id</td>
<td class="text-center">$name</td>
<td class="text-center" id="port_no">$port</td>
<td class="text-center">$interval</td>
<td class="text-center">$total</td>
<td class="text-center">
<a href="#" 
    class="btn btn-outline-success btn-sm $buttonStart"
    onclick="startSingleEmulator('$port')">
    <i class="bi bi-play-fill"></i>
</a>
<a href="#" 
    class="btn btn-outline-danger btn-sm $buttonStop"
    onclick="stopSingleEmulator('$port')">
    <i class="bi bi-pause-fill"></i>
</a>
</td>
<td class="text-center">
<input type="checkbox" class="device-checkbox" />
</td>
$statusObj
</tr>
"""
if __name__ == '__main__':
    serv = Service()
    # serv.refresh_configured_devices()
    # serv.start_emulators()
    # serv.check_emulator_path(8010)
    # serv.get_wxs_local_controllers()

    serv.run_server()

    # SELECT 
    #             LocalControllerID, 
    #             LocalControllerName, 
    #             IPAddress, 
    #             BaseCommPort, 
    #             LocalControllerEnabled,
    #             LocalControllerType,
    #             LocalControllerDescription 
    #         FROM CfgHWLocalControllers
    #         WHERE LocalControllerDescription like 'emulator%';
