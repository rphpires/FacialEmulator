

from GlobalFunctions import *

import uvicorn
import hashlib, base64
import time
import asyncio
# import io
import requests
import schedule
import json

from FakeEventImage import photo_img

from fastapi import FastAPI, Response, WebSocket, Request, Body, Query
from starlette.responses import StreamingResponse # PlainTextResponse
from pydantic import BaseModel
from datetime import datetime
from random import randint


class DahuaFace(BaseModel):
    name: str

class DahuaCard(BaseModel):
    name: str
    password: str | None = None

## 29 requests.


class DahuaHandler():
    def __init__(self, db_handler) -> None:
        self.db_handler = db_handler
        trace('Starting DahuaHandler class...')

    def get_settings(self, cfg_id):
        ret = self.db_handler.select(f"select value from DeviceSettings where CfgId = '{cfg_id}';")
        if not ret:
            return None
        
        value = ret[0][0]
        trace(f'Value readed from deviceSettings, CfgID={cfg_id} {value= }')
        return value

    def set_settings(self, cfg_id, value):
        trace(f"Update Device settings, set {cfg_id} = {value}")
        self.db_handler.execute(f"UPDATE DeviceSettings SET value = '{value}' WHERE CfgID = '{cfg_id}'")

    def add_card(self, CardName, UserID, CardNo, ValidDateStart, ValidDateEnd):
        try:
            trace(f'Insert Dahua Card: {CardName}, {UserID}, {CardNo}, {ValidDateStart}, {ValidDateEnd}')

            ## TODO: Check CardNo and UserID before ADD
            rec_no = self.db_handler.select(
                """
                SELECT MIN(t1.RecNo + 1) FROM DahuaCard AS t1
                LEFT JOIN DahuaCard AS t2 ON t1.RecNo + 1 = t2.RecNo
                WHERE t2.RecNo IS NULL
                """)[0][0]
            
            rec_no = int(rec_no) if rec_no is not None else 1                
            trace(f"RecNo= {rec_no}")

            if self.check_if_card_exists(CardNo, UserID):
                script = """ 
                    INSERT INTO DahuaCard 
                    VALUES (?,?,?,?,?,?) """
                self.db_handler.execute(script, (rec_no, CardName, UserID, CardNo, ValidDateStart, ValidDateEnd))            

                return True, f'RecNo={rec_no}'

            return False, ""
        
        except Exception as ex:
            report_exception(ex)

    def remove_card(self, recno):
        self.db_handler.execute("DELETE FROM DahuaCard WHERE RecNo = ?", (recno,))

    def add_face(self, UserID: int, md5: str = None):
        self.db_handler.execute("INSERT INTO DahuaFace VALUES (?,?)", (UserID, md5))
    
    def remove_face(self, user_id):
        self.db_handler.execute("DELETE FROM DahuaFace WHERE UserId = ?", (user_id,))

    def find_remote_faces(self):
        cnt = self.db_handler.select("SELECT COUNT(*) FROM DahuaFace")[0][0]
        return {
            "Token" : randint(1, 30),
            "Total" : int(cnt)
        }
    
    def get_remote_faces(self, count, offset):
        info = {"Info" : []}
        scp = self.db_handler.select(f"SELECT * FROM DahuaFace LIMIT ? OFFSET ?", (count, offset))
        if not scp:
            return info
        
        info["Info"] = [ {"MD5": y, "UserID": x} for x,y in scp ]
        return info

      
    def find_card(self, user_id):
        scp = self.db_handler.select("SELECT * FROM DahuaCard WHERE UserId = ?", (user_id, ))
        if not scp:
            return "found=0"
        else:
            return f"found=1\n{self.format_card_to_response(scp)}"
    
    def get_remote_cards(self, count, offset):
        scp = self.db_handler.select(f"SELECT * FROM DahuaCard LIMIT ? OFFSET ?", (count, offset))
        if not scp:
            return "found=0"
        
        return f"found={len(scp)}\n{self.format_card_to_response(scp)}" 


    def check_if_card_exists(self, cardNo, userId):
        scp = self.db_handler.select("SELECT * FROM DahuaCard WHERE CardNo = ? OR UserId = ?", (cardNo, userId))
        if not scp:
            return True
        error(f'Dahua Card: {userId = } or {cardNo = } already exists in database')
        return False
    
    def format_card_to_response(self, cards):
        i = 0
        record = ""
        for card in cards:
            RecNo, CardName, UserID, CardNo, ValidDateStart, ValidDateEnd = card
            rec = f"""records[{i}].CardName={CardName}
records[{i}].CardNo={CardNo}
records[{i}].CardStatus=0
records[{i}].CardType=0
records[{i}].CitizenIDNo=
records[{i}].Doors[0]=0
records[{i}].DynamicCheckCode=
records[{i}].FirstEnter=false
records[{i}].Handicap=false
records[{i}].IsValid=false
records[{i}].Password=
records[{i}].RecNo={RecNo}
records[{i}].RepeatEnterRouteTimeout=4294967295
records[{i}].TimeSections[0]=1
records[{i}].UseTime=200
records[{i}].UserID={UserID}
records[{i}].UserType=0
records[{i}].VTOPosition=
records[{i}].ValidDateEnd={ValidDateEnd}
records[{i}].ValidDateStart={ValidDateStart}
"""
            record = record + rec
            i += 1

        return record

    def generate_random_event(self):
        trace('generate_local_event')
        evt = self.db_handler.select("SELECT CardName, CardNo FROM DahuaCard ORDER BY RANDOM() LIMIT 1;")
        if not evt:
            return False
        
        (CardName, CardNo) = evt[0]

        gen_evt = f"""Events[0].Alive=100\r
Events[0].CardName={CardName}\r
Events[0].CardNo={CardNo}\r
Events[0].CardType=0\r
Events[0].CreateTime=1711203293\r
Events[0].Door=0\r
Events[0].ErrorCode=0\r
Events[0].EventBaseInfo.Action=Pulse\r
Events[0].EventBaseInfo.Code=AccessControl\r
Events[0].EventBaseInfo.Index=0\r
Events[0].FaceIndex=0\r
Events[0].ImageInfo[0].Height=384\r
Events[0].ImageInfo[0].Length=15225\r
Events[0].ImageInfo[0].Offset=0\r
Events[0].ImageInfo[0].Type=1\r
Events[0].ImageInfo[0].Width=640\r
Events[0].ImageInfo[1].Height=420\r
Events[0].ImageInfo[1].Length=21710\r
Events[0].ImageInfo[1].Offset=15225\r
Events[0].ImageInfo[1].Type=0\r
Events[0].ImageInfo[1].Width=360\r
Events[0].ImageInfo[2].Height=608\r
Events[0].ImageInfo[2].Length=22531\r
Events[0].ImageInfo[2].Offset=36935\r
Events[0].ImageInfo[2].Type=2\r
Events[0].ImageInfo[2].Width=480\r
Events[0].Method=15\r
Events[0].ReaderID=1\r
Events[0].RealUTC=1711203293\r
Events[0].Similarity=99\r
Events[0].SnapPath=/var/tmp/white_part5.jpg\r
Events[0].Status=1\r
Events[0].Type=Entry\r
Events[0].UTC=1711203293\r
Events[0].UserID=29559\r
Events[0].UserType=0\r
"""
        evt_package = f"""\r
\r
\r
--myboundary\r
Content-Type: text/plain\r
Content-Length: {len(gen_evt)}\r
\r
""" 
        evt_package += gen_evt
        image_content = base64.b64decode(photo_img)
                
        data_photo = f"\r\n--myboundary\r\nContent-Type: image/jpeg\r\nContent-Length: {len(image_content)}\r\n\r\n".encode('utf-8')
        return evt_package.encode('utf-8') + data_photo + image_content

    def generate_online_event(self, mac_address):
        trace(f"generate_online_event: {mac_address = }")
        
        try:
            current_datetime = datetime.utcnow()
            evt = self.db_handler.select("SELECT UserID, CardName, CardNo FROM DahuaCard ORDER BY RANDOM() LIMIT 1;")
            if not evt:
                trace(f"Event won't be generated because the database is empty.")
                return None, None
            
            (UserID, CardName, CardNo) = evt[0]

            online_event_boundary = """\r
--myboundary\r
Content-Type: text/plain\r
Content-Disposition: form-data; name="info"\r
\r
"""
            online_event = {
                "Events" : [
                    {
                        "Action" : "Pulse",
                        "Code" : "AccessControl",
                        "Data" : {
                            "CardStatus" : 0,
                            "CardType" : 0,
                            "Door" : 0,
                            "ErrorCode" : 96,
                            "EventGroupID" : 0,
                            "Method" : 15,
                            "ReadID" : "1",
                            "Status" : 0,
                            "Type" : "Entry",
                            "UTC" : int(time.time()),
                            "UserID" : UserID,
                            "UserType" : 0
                        },
                        "Index" : 0,
                        "PhysicalAddress" : mac_address
                    }
                ],
                "Time" : current_datetime.strftime("%d-%m-%Y %H:%M:%S")
                }
        
            online_event_boundary_end = """\r
--myboundary--\r
\r
"""     
            event = f'''{online_event_boundary + json.dumps(online_event, indent=2) + online_event_boundary_end}'''

            online_event["Events"][0]["Data"]["ImageInfo"] = [
                {
                    "Height" : 640,
                    "Length" : 14088,
                    "Offset" : 0,
                    "Type" : 1,
                    "Width" : 360
                }
            ]
            online_event["Channel"] = 0
            online_event["Events"][0]["Data"]["Method"] = 4
            online_event["FilePath"] = "\\/mnt\\/appdata1\\/userpic\\/SnapShot\\/2024-04-16\\/21\\/07\\/20240416210702098.jpg"

            image_content = base64.b64decode(photo_img)
            image_boundary = """\r
--myboundary\r
Content-Type: image/jpeg\r
Content-Disposition: form-data; name="file"\r
\r
"""
            _event_reply = f'''{online_event_boundary + json.dumps(online_event, indent=2) + image_boundary}''' 
            event_reply = _event_reply.encode('utf-8') + image_content + b"\r\n--myboundary--\r\n\r\n"
            
            trace(f"Returning online generated event: ")
            return event, event_reply
        
        except Exception as ex:
            report_exception(ex)
            return None, None
        

    def get_door_event(self, status, mac_address):
        try:
            current_datetime = datetime.utcnow()
            online_event_boundary = """\r
--myboundary\r
Content-Type: text/plain\r
Content-Disposition: form-data; name="info"\r
\r
"""
            door_event = {
                "Events" : [
                    {
                        "Action" : "Pulse",
                        "Code" : "DoorStatus",
                        "Data" : {
                            "Status" : status,
                            "UTC" : int(time.time())
                        },
                        "Index" : 0,
                        "PhysicalAddress" : mac_address
                    }
                ],
                "Time" : current_datetime.strftime("%d-%m-%Y %H:%M:%S")
            }
            return f'''{online_event_boundary + json.dumps(door_event, indent=2)}\r\n--myboundary--\r\n\r\n''' 
        
        except Exception as ex:
            report_exception(ex)
            

class DahuaEmulator(threading.Thread):
    def __init__(self, ip, port, db_handler, event_freq) -> None:
        threading.Thread.__init__(self)
        trace(f'Innitializing emulator model: "Dahua" v1.1')
        self.ip = ip
        self.port = port
        self.generated_event_frequency = event_freq

        self.dahua = DahuaHandler(db_handler)
        self.app = FastAPI()
        
        base_url = f'/cgi-bin/getUser.cgi'

        self.remote_server = self.dahua.get_settings("RemoteServer") 
        self.remote_port = self.dahua.get_settings("RemotePort") 
        self.remote_server_url = f'http://{self.remote_server}:{self.remote_port}'
        trace(f'Starting server URL from database: {self.remote_server_url}')

        self.mac_address = generate_mac_address()
        trace(f'Settings Mac-Adress= {self.mac_address}')

        self.generated_event = True if event_freq >= 1 else False
        trace(f'Generate event? {self.generated_event}')

        # Criando uma instância do FastAPI

        @staticmethod 
        def handle_response(content, response_code = 200, latency_sleep=50):
            try:
                response = Response(content=content, status_code=response_code)
                response.headers["Content-Type"] = "text/plain; charset=utf-8"
                # trace('---- Start sleep ----')
                time.sleep(latency_sleep / 1000)
                # trace('---- End sleep ----')
                return response

            except Exception as ex:
                report_exception(ex)
                return Response(content='Emulator Error', status_code=response_code)


        ## Custom endpoint to check emulator status
        @self.app.get('/emulator/get-status')
        async def get_device_status(request: Request):
            try:
                trace("/emulator/get-status: connect")
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return {"CurrentDatetime": current_time}

            except Exception as ex:
                report_exception(ex)
            
        ### -------------------------------  Global -----------------------------
        @self.app.get('/cgi-bin/global.cgi')
        async def GetGobal(action: str=None, time: str=None):
            try:
                trace(f"New [GET] Request at: '/cgi-bin/global.cgi' | {action = } | {time = }")
                match action:
                    case "getCurrentTime": ## OK
                        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        return handle_response(f"result={current_time}")

                    case "setCurrentTime": ## OK
                        return handle_response("OK") 
                    
                    case "setConfig":
                        return handle_response("OK") 
            
            except Exception as ex:
                report_exception(ex)


        ### -------------------------------  MagicBox -----------------------------
        @self.app.get('/cgi-bin/magicBox.cgi')
        async def GetConfigManager(request: Request):
            try:
                action = request.query_params["action"]
                match action:
                    case 'getSoftwareVersion':
                        trace('Get Software Version: emulator v1.0')
                        return handle_response("version=Emulator v1.0", latency_sleep=80) 


            except Exception as ex:
                report_exception(ex)    

        ### -------------------------------  configManager -----------------------------
        @self.app.get('/cgi-bin/configManager.cgi')
        async def GetConfigManager(request: Request):
            try:
                action = request.query_params["action"]
                match action:
                    case "getConfig":
                        name = request.query_params["name"]
                        if name.upper() == 'NETWORK':
                            device_return = f"""
table.Network.eth0.PhysicalAddress={self.mac_address}\r
table.Network.eth0.SubnetMask=255.255.248.0 
                            """
                            response = Response(content=device_return)
                            response.headers["Content-Type"] = "text/plain; charset=utf-8"
                            asyncio.sleep(0.450)
                            return response
                        
                    case "setConfig":
                        trace(f'SetConfig: {request.query_params}')
                        self.remote_server = request.query_params["PictureHttpUpload.UploadServerList[0].Address"]
                        self.dahua.set_settings("RemoteServer", self.remote_server)

                        self.remote_port = request.query_params["PictureHttpUpload.UploadServerList[0].Port"]
                        self.dahua.set_settings("RemotePort", self.remote_port)

                        self.remote_server_url = f'http://{self.remote_server}:{self.remote_port}'
                        
                        trace(f'Set LocalAuthentication: PictureHttpUpload.Enable= {request.query_params["PictureHttpUpload.Enable"]}')
                        local_authentication_value = "0" if request.query_params["PictureHttpUpload.Enable"] == "True" else "1" ## Set LocalAuthentication
                        ## IF "PictureHttpUpload.Enable" == True => Online Authentication
                        self.dahua.set_settings("LocalAuthentication", local_authentication_value)
                        
                        return handle_response("OK")

            except Exception as ex:
                print(ex)

        ### ------------------------------- Access Control -----------------------------
        @self.app.get('/cgi-bin/accessControl.cgi')
        async def GetAccessControl(action: str=None, channel: str=None):
            try:
                match action: 
                    case "openDoor": ## OK
                        ## Cmd time: 100ms
                        trace(f'Command openDoor output: {channel}')
                        
                        return handle_response("OK", latency_sleep=80) 
                    
                    case "closeDoor": ## OK
                        trace(f'Command closeDoor output: {channel}')
                        return handle_response("OK", latency_sleep=80)  

            except Exception as ex:
                print(ex)

        ### ------------------------------- FaceInfoManager -----------------------------
        @self.app.get('/cgi-bin/FaceInfoManager.cgi')
        async def GetFaceInfoManager(request: Request):
            # {"action": "doFind", "Token": token, "Offset": offset, "Count": slice_size }
            action = request.query_params["action"]
            try:
                match action:
                    case "startFind":
                        time.sleep(0.5)
                        return self.dahua.find_remote_faces() ## Response as JSON
                        ## time/users: 5 = 562ms | 500 = x | 5000 = x
                                            
                    case "doFind":
                        time.sleep(0.05)
                        return self.dahua.get_remote_faces(request.query_params["Count"], request.query_params["Offset"]) ## Response as JSON
                        ## time/users: 5 = 62ms | 500 = x | 5000 = x
                        
                    case "stopFind":
                        return handle_response("OK")
                        ## time/users: 5 = 62ms | 500 = x | 5000 = x
                                            
                    case "remove":
                        ## Remove: 1 user= 60ms
                        time.sleep(0.05)
                        return self.dahua.remove_face(request.query_params["UserID"])
                    
                    case _:
                        return "Invalid action" 
                    
            except Exception as ex:
                print(ex)

        @self.app.post("/cgi-bin/FaceInfoManager.cgi")
        #async def PostFaceInfoManager(action: dict, body: str = Body(...)):
        async def PostFaceInfoManager(request: Request, str = Body(...)):
            action = request.query_params["action"]
            UserID = str["UserID"]
            _photo = str["Info"].get("PhotoData", [""])
            print(type(_photo), type(_photo[0]))
            PhotoData = _photo[0]
            try:
                match action:
                    case "add":
                        ## ADD 1 user: 800ms
                        try:
                            md5 = hashlib.md5(base64.b64decode(PhotoData)).hexdigest().upper()
                            PhotoData = None
                        except Exception as ex:
                            trace(PhotoData)

                        trace(f'Add Face: {UserID = }, {md5 = }')
                        self.dahua.add_face(UserID, md5)

                        return handle_response("OK", latency_sleep=550)
                    
                    case "update":
                        md5 = hashlib.md5(base64.b64decode(PhotoData)).hexdigest().upper()
                        PhotoData = None

                        trace(f'Update Face: {UserID = }, {md5 = }')

                        self.dahua.remove_face(UserID)
                        self.dahua.add_face(UserID, md5)
                        
                        return handle_response("OK", latency_sleep=600)
                    
            except Exception as ex:
                print(ex)


        ### ------------------------------- recordFinder -----------------------------
        @self.app.get('/cgi-bin/recordFinder.cgi')
        async def GetRecordFinder(
            action: str, 
            name: str, 
            offset: str = None, 
            count: int = 0, 
            UserID: str = Query(None, alias="condition.UserID")
            ):

            try:
                match action:
                    case "find":
                        ## 1 usuário: 60ms
                        return handle_response(self.dahua.find_card(UserID))
                    
                    case "doSeekFind":
                        ## time/users: 5 = 545ms | 100 =  : Qnt maxima
                        return handle_response(self.dahua.get_remote_cards(count, offset), latency_sleep= 350)
    

            except Exception as ex:
                print(ex)


        ### ------------------------------- recordUpdater -----------------------------
        @self.app.get('/cgi-bin/recordUpdater.cgi')
        async def GetRecordUpdater(request: Request):
            try:
                trace(f'[GET] /recordUpdater.cgi: {request.query_params}')
                action = request.query_params["action"]
                match action:
                    case "remove":
                        ## Sempre 1 usuario: 570ms
                        self.dahua.remove_card(request.query_params["recno"])
                        return handle_response("OK", latency_sleep=350)

                    case "insert":
                        trace(f'recordUpdater..insert: {request.query_params}')
                        _inserted, msg = self.dahua.add_card(
                            request.query_params["CardName"], 
                            request.query_params["UserID"], 
                            request.query_params["CardNo"], 
                            request.query_params["ValidDateStart"], 
                            request.query_params["ValidDateEnd"]
                            )                        
                        if _inserted:
                            return handle_response(msg, latency_sleep=100)
                        else:
                            return handle_response("Error\nBad Request!", 400)


            except Exception as ex:
                print(ex)

        @self.app.post("/cgi-bin/recordUpdater.cgi")
        async def PostRecordUpdater(request: Request):
            trace(f'/recordUpdater.cgi: {request.query_params}')
            action = request.query_params["action"]
            try:                
                match action:
                    case "insert":
                        trace(f'recordUpdater..insert: {request.query_params}')
                        _inserted, msg = self.dahua.add_card(
                            request.query_params["CardName"], 
                            request.query_params["UserID"], 
                            request.query_params["CardNo"], 
                            request.query_params["ValidDateStart"], 
                            request.query_params["ValidDateEnd"]
                            )                        
                        if _inserted:
                            return handle_response(msg, latency_sleep=100)
                        else:
                            return handle_response("Error\nBad Request!", 400)


            except Exception as ex:
                print(ex)
    
        ### ------------------------------- SnapManager -----------------------------

        class AsyncGeneratorResponse(StreamingResponse):
            def __init__(self, agen):
                self.agen = agen
                super().__init__(self.iter_content(), media_type="text/event-stream")

            async def iter_content(self):
                try:
                    async for chunk in self.agen:
                        yield chunk

                except Exception as ex:
                        report_exception(ex)


        @self.app.get("/cgi-bin/snapManager.cgi")
        async def heartbeat(request: Request):
            try:
                trace("[GET] /cgi-bin/snapManager.cgi")
                return AsyncGeneratorResponse(self.generate_heartbeat())

            except Exception as ex:
                        report_exception(ex)


    async def generate_heartbeat(self):
        heartbeat_counter = time.time()
        self.genereted_event_counter = time.time()

        while True:
            try:
                trace(f'## StandAlone heartbeat and event')
                now = time.time()
                if self.generated_event and (now - self.genereted_event_counter >= self.generated_event_frequency):
                    trace(f'>> Sending Generated Fake Event <<')
                    try:
                        self.genereted_event_counter= time.time()
                        evt_package = self.dahua.generate_random_event()

                        if evt_package and self.dahua.get_settings("LocalAuthentication") == '1':
                            trace('## yield event')
                            yield evt_package
                    
                    except Exception as ex:
                        report_exception(ex)

                if now - heartbeat_counter >= 10:
                    trace('>> Sending Heartbeat <<')
                    try:
                        heartbeat_counter = now
                        yield b'\r\n\r\n\r\n--myboundary\r\nContent-Type: text/plain\r\nContent-Length:9\r\n\r\nHeartbeat'
                    
                    except Exception as ex:
                        report_exception(ex)


                if self.dahua.get_settings("LocalAuthentication") == '0':
                    break

                await asyncio.sleep(2)

            except Exception as ex:
                report_exception(ex)


    ### ------------------------------------------------------------------
    ### ------------------------ Online events ---------------------------
    ### ------------------------------------------------------------------
    def generate_online_event(self):
        trace('Generating online event.')
        try:
            evt_package, event_reply = self.dahua.generate_online_event(self.mac_address)
        except Exception as ex:
            report_exception(ex)
            return False
        
        if evt_package and self.dahua.get_settings("LocalAuthentication") == '0':
            try:
                trace(f"Sending online event to server: {self.remote_server_url}/notification")
                gen_evt = requests.post(self.remote_server_url + '/notification', data=evt_package, timeout=5)
                trace(f'Generated online event reply: {gen_evt.content}')
                if gen_evt.status_code:
                    trace('Sending image event.')
                    sec_event = requests.post(self.remote_server_url + '/notification', data=event_reply, timeout=5)
                    trace(f'Image generated online event reply: {sec_event.content}')
                    
                    if random_access_not_done():
                        trace('Sending Door sensor event to complete access')
                        ## Random chance [20%] to generate "Access Not Done" event. 
                        time.sleep(2) ## Sleep to reproduce real time to access
                        door_open_event = self.dahua.get_door_event("Open", self.mac_address)
                        requests.post(self.remote_server_url + '/notification', data=door_open_event, timeout=5)

                    
                        time.sleep(3) ## Sleep to reproduce real time to access
                        door_close_event = self.dahua.get_door_event("Close", self.mac_address)
                        requests.post(self.remote_server_url + '/notification', data=door_close_event, timeout=5)


            except Exception as ex:
                report_exception(ex)



    def scheduler(self):
        schedule.every(self.generated_event_frequency).seconds.do(self.generate_online_event)
        schedule.every(5).minutes.do(still_running_trace)

        while True:
            try:
                schedule.run_pending()   
                time.sleep(1)
            except Exception as ex:
                report_exception(ex)


    ### ------------------------------------------------------------------
    ### ------------------------ Online events ---------------------------
    ### ------------------------------------------------------------------
    
    def run(self):
        try:
            threading.Thread(target=self.scheduler).start()
        except Exception as ex:
            report_exception(ex)

        try:
            ## WebServer innitialization...
            trace(f"Starting FastAPI webServer: IP={self.ip}, Port={self.port}")
            uvicorn.run(self.app, host=self.ip, port=self.port)
        except Exception as ex:
            report_exception(ex)

        
def still_running_trace():
    trace('Emulator is still running')


if __name__ == "__main__":
    port=77
    d = DahuaEmulator(port)
    uvicorn.run(d.app, host="localhost", port=port)