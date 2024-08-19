
import uvicorn
import asyncio
import json
import requests
import base64

from fastapi import FastAPI, Response, WebSocket, Request, Body, Query, UploadFile, File, Form
from fastapi.responses import JSONResponse
from starlette.responses import PlainTextResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from pydantic import BaseModel
from typing import Any
from datetime import datetime, timezone, timedelta

from GlobalFunctions import *
from FakeEventImage import photo_img

class HikvisionHandler():
    def __init__(self, db_handler) -> None:
        self.db_handler = db_handler

        self.delete_in_progress = False

    @staticmethod
    async def heartbeat(interval, websocket: WebSocket):
        while True:
            await asyncio.sleep(10)
            await websocket.send_text("Heartbeat")

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

    def count_items(self):
        return self.db_handler.select("""
SELECT 
	(SELECT COUNT(*) FROM HikvisionUser) AS Users, 
	(SELECT COUNT(*) FROM HikvisionCard) AS Cards,
	(SELECT COUNT(*) FROM HikvisionFace) AS Faces,
	(SELECT COUNT(*) FROM HikvisionFinger) AS Fingerprints
""")[0]    
    
    # -- Users --
    def add_user(self, user_dict):
        try:
            trace(f'Insert Hikvision User: {user_dict}')

            if self.check_if_user_exists(user_dict["employeeNo"]):
                script = """ 
                    INSERT INTO HikvisionUser 
                    VALUES (?,?,?,?,?,?) """
                self.db_handler.execute(
                    script, 
                    (
                        user_dict["employeeNo"], 
                        user_dict["name"], 
                        user_dict["password"], 
                        user_dict["localUIRight"], 
                        user_dict["Valid"]["beginTime"], 
                        user_dict["Valid"]["endTime"]
                    )
                )            
                return 1
            else:
                return 6
        
        except Exception as ex:
            report_exception(ex)

    def update_user(self, user_dict):
        script = """ 
            UPDATE HikvisionUser 
            SET name= ?,password= ?,localUIRight= ?,beginTime= ?,endTime= ?
            WHERE employeeNo= ?;"""
        self.db_handler.execute(
            script, 
            (
                user_dict["name"],
                user_dict["password"],
                user_dict["localUIRight"], 
                user_dict["Valid"]["beginTime"], 
                user_dict["Valid"]["endTime"],
                user_dict["employeeNo"]
            )
        )            

    def delete_user(self, employee_list):
        self.delete_in_progress = True
        trace(f'remove_user: {employee_list = }')
        try:
            for employee in employee_list:
                try:
                    trace(f"Deleting user with EmployeeNo= {employee['employeeNo']}")
                    self.db_handler.execute(f"Delete from HikvisionUser where employeeNo= {employee['employeeNo']};")
                    self.db_handler.execute(f"Delete from HikvisionCard where employeeNo= {employee['employeeNo']};")
                    self.db_handler.execute(f"Delete from HikvisionFace where UserID= {employee['employeeNo']};")
                    self.db_handler.execute(f"Delete from HikvisionFinger where CHID= {employee['employeeNo']};")

                except Exception as ex:
                    report_exception(ex)

        except Exception as ex:
            report_exception(ex)
        self.delete_in_progress = False

    def get_remote_users(self, count, offset):
        users_count, _, _, _ = self.count_items()
        ret_users_info = []
        no_of_matches = 0

        scp = self.db_handler.select(f"SELECT * FROM HikvisionUser LIMIT ? OFFSET ?", (count, offset))
        if scp:
            for employeeNo, name, password, localUIRight, beginTime, endTime  in scp:
                ret_users_info.append({
                    "employeeNo": str(employeeNo),
                    "name":	name,
                    "userType":	"normal",
                    "sortByNamePosition":	0,
                    "sortByNameFlag": "#",
                    "closeDelayEnabled": False,
                    "Valid": {
                        "enable":	True,
                        "beginTime": beginTime,
                        "endTime": endTime,
                        "timeType":	"local"
                    },
                    "belongGroup":	"",
                    "password":	"" if not password else str(password),
                    "doorRight": "1",
                    "RightPlan": [{
                            "doorNo":	1,
                            "planTemplateNo":	"1"
                        }],
                    "maxOpenDoorTime":	0,
                    "openDoorTime":	0,
                    "roomNumber":	0,
                    "floorNumber":	0,
                    "localUIRight":	False if not localUIRight else True,
                    "gender": "unknown",
                    "numOfCard": 1,
                    "numOfRemoteControl": 0,
                    "numOfFP":	0,
                    "numOfFace":	0,
                    "PersonInfoExtends": [{ "value": "" }]
                })
                no_of_matches += 1
        
        trace(f'Users founded in database: Current select= {no_of_matches} Total= {users_count}')
        return {
            "UserInfoSearch": {
                "searchID":	"1",
                "responseStatusStrg": "MORE",
                "numOfMatches":	no_of_matches,
                "totalMatches":	int(users_count),
                "UserInfo":	ret_users_info
            }
        }
    
    def check_if_user_exists(self, employeeNo):
        scp = self.db_handler.select("SELECT * FROM HikvisionUser WHERE employeeNo = ?", (employeeNo,))
        if not scp:
            return True
        error(f'Hikvision Card: {employeeNo = } already exists in database')
        return False
    
    # -- Cards --
    def add_card(self, EmployeeNo, CardNo):
        try:
            trace(f'Insert Hikvision Card: {EmployeeNo = }, {CardNo = }')
            if self.check_if_card_exists(EmployeeNo, CardNo):
                script = """ 
                    INSERT INTO HikvisionCard 
                    VALUES (?,?) """
                self.db_handler.execute(script, (EmployeeNo, CardNo))            

                return 1
            return 6
        
        except Exception as ex:
            report_exception(ex)

    def delete_card(self, recno):
        self.db_handler.execute("DELETE FROM HikvisionCard WHERE RecNo = ?", (recno,))

    def add_face(self, UserID: int, PhotoID: str = None):
        try:
            self.db_handler.execute("INSERT INTO HikvisionFace VALUES (?,?)", (UserID, PhotoID))
            return 1
        except Exception as ex:
            error(f"UserID={UserID} already exists on database")
            return 6
    
    def get_remote_cards(self, count, offset):
        _, cards_count, _, _ = self.count_items()
        ret_cards_info = []
        no_of_matches = 0

        scp = self.db_handler.select(f"SELECT * FROM HikvisionCard LIMIT ? OFFSET ?", (count, offset))
        if scp:
            for employeeNo, CardNo in scp:
                ret_cards_info.append({
                    "employeeNo": str(employeeNo),
                    "cardNo": str(CardNo),
                    "isCardAsRemoteControlBtn":	False,
                    "leaderCard": "",
                    "cardType":	"normalCard"
                })
                no_of_matches += 1
        
        trace(f'Cards founded in database: Current select= {no_of_matches} Total= {cards_count}')
        return {
            "CardInfoSearch": {
                "searchID":	"1",
                "responseStatusStrg": "MORE",
                "numOfMatches":	no_of_matches,
                "totalMatches":	int(cards_count),
                "CardInfo":	ret_cards_info
            }
        }
    
    def check_if_card_exists(self, EmployeeNo, CardNo):
        scp = self.db_handler.select("SELECT * FROM hikvisionCard WHERE EmployeeNo = ? OR CardNo = ?", (EmployeeNo, CardNo))
        if not scp:
            return True
        error(f'Hikvision Card: {EmployeeNo = } or {CardNo = } already exists in database')
        return False
    
    def find_card(self, user_id):
        scp = self.db_handler.select("SELECT * FROM HikvisionCard WHERE UserId = ?", (user_id, ))
        if not scp:
            return "found=0"
        else:
            return f"found=1\n{self.format_card_to_response(scp)}"
        
    # -- Faces --
    def update_face(self, UserID, PhotoID):
        try:
            self.db_handler.execute("UPDATE HikvisionFace SET PhotoID=? where UserID=?)", (PhotoID, UserID))
            return 1
        except Exception as ex:
            report_exception(ex)
            return 77

    def delete_face(self, user_id):
        self.db_handler.execute("DELETE FROM HikvisionFace WHERE UserId = ?", (user_id,))

    def get_remote_faces(self, count, offset, device_url):
        _, _, faces_count, _ = self.count_items()
        ret_faces_info = []
        no_of_matches = 0

        scp = self.db_handler.select(f"SELECT * FROM HikvisionFace LIMIT ? OFFSET ?", (count, offset))
        if scp:
            for UserID, PhotoData in scp:
                ret_faces_info.append({
                    "FPID": str(UserID),
                    "faceURL": device_url + f"/{UserID}",
                    "modelData": ""
                })
                no_of_matches += 1
        
        trace(f'Faces founded in database: Current select= {no_of_matches} Total= {faces_count}')
        return {
            "searchID":	"1",
            "responseStatusStrg": "MORE",
            "numOfMatches":	no_of_matches,
            "totalMatches":	int(faces_count),
            "MatchList": ret_faces_info
        }

    def get_face(self, userID):
        scp = self.db_handler.select("SELECT PhotoData FROM HikvisionFace WHERE UserId = ?", (userID, ))
        if not scp:
            return ""
        else:
            return scp[0][0]
    
    
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

    def generate_random_event(self, emulator):
        evt = self.db_handler.select("""
SELECT name, cardNo, u.employeeNo from hikvisionUser u
JOIN HikvisionCard c ON c.employeeNo = u.employeeNo
ORDER BY RANDOM() LIMIT 1;""")
        
        if not evt:
            trace(f'generate_random_event: Nenhum evento no banco de dados.')
            return False
        
        (Name, CardNo, EmployeeNo) = evt[0]

        current_datetime = datetime.datetime.now()
        hora_atual_fuso = current_datetime.astimezone(timezone(timedelta(hours=-3)))

        gen_evt = {
            "ipAddress": emulator.ip,
            "ipv6Address": "fe80::be5e:33ff:fe57:a5cb",
            "portNo": emulator.port,
            "protocol": "HTTP",
            "macAddress": emulator.mac_address,
            "channelID": 1,
            "dateTime": hora_atual_fuso.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "activePostCount": 1,
            "eventType": "AccessControllerEvent",
            "eventState": "active",
            "eventDescription": "Access Controller Event",
            "AccessControllerEvent": {
                "deviceName": "subdoorOne",
                "majorEventType": 5,
                "subEventType": 75,
                "cardNo": CardNo,
                "cardType": 1,
                "name": Name,
                "cardReaderKind": 1,
                "cardReaderNo": 1,
                "verifyNo": 189,
                "employeeNoString": str(EmployeeNo),
                "serialNo": 4435,
                "userType": "normal",
                "currentVerifyMode": "faceOrFpOrCardOrPw",
                "currentEvent": True,
                "frontSerialNo": 4434,
                "attendanceStatus": "undefined",
                "label": "",
                "statusValue": 0,
                "mask": "no",
                "helmet": "unknown",
                "picturesNumber": 1,
                "purePwdVerifyEnable": True,
                "FaceRect": {
                    "height": 0.268,
                    "width": 0.477,
                    "x": 0.286,
                    "y": 0.354
                },
                "unlockRoomNo": "3723243075"
            }
        }
        content_length = f'''{json.dumps(gen_evt, indent=2)}'''

        evt_package = f"""\r
--MIME_boundary\r
Content-Type: application/json; charset="UTF-8"\r
Content-Length: {len(content_length)}\r
\r
""" 
        evt_package += f'''{json.dumps(gen_evt, indent=2)}'''
        image_content = base64.b64decode(photo_img)
                
        data_photo = f"""\r
--MIME_boundary\r
Content-Disposition: form-data; name="Picture"; filename="Picture.jpg"\r
Content-Type: image/jpeg\r
Content-Length: {len(image_content)}\r
Content-ID: pictureImage\r
\r""".encode('utf-8')
        
        return evt_package.encode('utf-8') + data_photo + image_content

    def generate_online_event(self, mac_address):
        trace(f"generate_online_event: {mac_address = }")
        
        try:
            current_datetime = datetime.utcnow()
            evt = self.db_handler.select("SELECT UserID, CardName, CardNo FROM HikvisionCard ORDER BY RANDOM() LIMIT 1;")
            if not evt:
                return False
            
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

    def get_door_event(self, status, mac_address):
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


class AcsCfg(BaseModel):
    remoteCheckDoorEnabled: bool
    checkChannelType: str | None = ""

class HikvisionEmulator(threading.Thread):
    def __init__(self, ip, port, db_handler, event_freq) -> None:
        threading.Thread.__init__(self)
        trace(f'Innitializing emulator model: "Hikivision".')
        self.ip = ip
        self.port = port
        self.db_handler = db_handler
        
        self.hikvision = HikvisionHandler(db_handler)
        self.app = FastAPI()
        active_connections = set()

        self.generated_event_frequency = event_freq
        self.generated_event = True if event_freq >= 1 else False

        self.mac_address = generate_mac_address()

        @staticmethod 
        def handle_response(content, response_code = 200, latency_sleep=50):
            response = Response(content=content, status_code=response_code)
            response.headers["Content-Type"] = "application/json"
            # trace('---- Start sleep ----')
            time.sleep(latency_sleep / 1000)
            # trace('---- End sleep ----')
            return response  
        
        @staticmethod 
        # def default_response(status_code, status_string, sub_status_code, error_code = None, error_msg= None):
        def default_response(response_code=200, **kwargs):
            ## "statusCode": 6, "statusString": "Invalid Content", "subStatusCode": "employeeNoAlreadyExist", "errorCode": 1610637344, "errorMsg": "checkUser"           }
            ret = {key: value for key, value in kwargs.items() if value is not None}
            return Response(content=json.dumps(ret, indent=2), status_code=response_code, media_type="application/json")
            #return JSONResponse(content=json.dumps(ret, indent=2), status_code=response_code, media_type="application/json")


        ## Custom endpoint to check emulator status
        @self.app.get('/emulator/get-status')
        async def get_device_status(request: Request):
            try:
                trace("/emulator/get-status: connect")
                current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                return {"CurrentDatetime": current_time}

            except Exception as ex:
                report_exception()

        ## ---------------------------------------------------------------
        ## ------------------------ AccessControl ------------------------
        ## ---------------------------------------------------------------
        ac_url = "/ISAPI/AccessControl"

        @self.app.get(ac_url + "/AcsCfg") # OK
        async def get_acs_cfg():
            return {
                "AcsCfg": {
                    "uploadCapPic": True,
                    "saveCapPic": True,
                    "protocol": "Private",
                    "voicePrompt": False,
                    "showPicture": False,
                    "showEmployeeNo": False,
                    "showName": True,
                    "desensitiseEmployeeNo": True,
                    "desensitiseName": True,
                    "uploadVerificationPic": True,
                    "saveVerificationPic": True,
                    "saveFacePic": False,
                    "remoteCheckDoorEnabled": True,
                    "remoteStandaloneEnabled": True,
                    "remoteCheckSet": 0,
                    "checkChannelType": "ISAPIListen",
                    "externalCardReaderEnabled": False,
                    "combinationAuthenticationTimeout": 5,
                    "combinationAuthenticationLimitOrder": True
                }
            }

        @self.app.put(ac_url + "/AcsCfg") ## Set Online/Local Authentication
        async def put_acs_cgf(payload: dict):
            try:
                body = payload["AcsCfg"]
                trace(f'Setting online mode: {body["remoteCheckDoorEnabled"]}')
                local_authentication_value = "0" if body["remoteCheckDoorEnabled"] else "1"
                self.hikvision.set_settings("LocalAuthentication", local_authentication_value)
                xml_content = """
<?xml version="1.0" encoding="UTF-8"?>
<ResponseStatus version="1.0" xmlns="http://www.hikvision.com/ver10/XMLSchema">
    <requestURL></requestURL>
    <statusCode>1</statusCode>
    <statusString>OK</statusString>
    <subStatusCode>ok</subStatusCode>
</ResponseStatus>
"""         
                return Response(content=xml_content, media_type="application/xml")
            
            except Exception as ex:
                report_exception(ex)
                return Response(content=ex, status_code=500, media_type="application/xml")

        @self.app.put(ac_url + "/AcsEvent/StorageCfg") # OK
        async def put_storage_cfg():
            return default_response(statusCode=	1, statusString= "OK", subStatusCode= "ok")

        @self.app.put(ac_url + "/Door/param/1") ## TODO: Test
        async def set_door_parameters():
            xml_response_content = """
<?xml version="1.0" encoding="UTF-8"?>
<ResponseStatus version="1.0" xmlns="http://www.hikvision.com/ver10/XMLSchema">
    <requestURL></requestURL>
    <statusCode>1</statusCode>
    <statusString>OK</statusString>
    <subStatusCode>ok</subStatusCode>
</ResponseStatus>
"""
            return Response(content=xml_response_content, media_type="application/xml")

        @self.app.put(ac_url + "/RemoteControl/door/{output_id}") ## TODO: Test
        async def command_door(output_id: int, item: dict):
            trace(f'New command received to output= {output_id}')
            xml_response_content = """
<?xml version="1.0" encoding="UTF-8"?>
<ResponseStatus version="1.0" xmlns="http://www.hikvision.com/ver10/XMLSchema">
    <requestURL></requestURL>
    <statusCode>1</statusCode>
    <statusString>OK</statusString>
    <subStatusCode>ok</subStatusCode>
</ResponseStatus>
"""
            return Response(content=xml_response_content, media_type="application/xml")

        ## ---- UserInfo ----
        @self.app.get(ac_url + "/UserInfo/Count") ## OK
        async def get_user_count():
            users_count, cards_count, faces_count, fingerprints_count = self.hikvision.count_items()
            return {
                "UserInfoCount": {
                    "userNumber": int(users_count),
                    "bindFaceUserNumber": int(faces_count),
                    "bindFingerprintUserNumber": int(fingerprints_count),
                    "bindCardUserNumber": int(cards_count),
                    "bindRemoteControlNumber": 0
                }
            }
        
        @self.app.post(ac_url + "/UserInfo/Search") ## TODO: Test
        async def post_user_search(user_info: dict):
            cond = user_info["UserInfoSearchCond"]
            return self.hikvision.get_remote_users(cond["maxResults"], cond["searchResultPosition"])
        
        @self.app.post(ac_url + "/UserInfo/Record") ## OK
        async def post_user_record(user: dict):
            ret_status = self.hikvision.add_user(user["UserInfo"])

            match ret_status:
                case 1: ## OK
                    return default_response(statusCode=1, statusString="OK", subStatusCode="ok")
                
                case 6: ## employeeNoAlreadyExist
                    return default_response(
                        statusCode=6, 
                        response_code=400, 
                        statusString="Invalid Content", 
                        subStatusCode="employeeNoAlreadyExist", 
                        errorCode= 1610637344, 
                        errorMsg="checkUser"
                    ) 
                    
        @self.app.put(ac_url + "/UserInfo/Modify") ## TODO: Test
        async def put_user_modify(user: dict):
            self.hikvision.update_user(user["UserInfo"])

            return default_response(statusCode=1, statusString="OK", subStatusCode="ok")
        
        ## ---- UserInfoDetail ----
        @self.app.get(ac_url + "/UserInfoDetail/DeleteProcess") ## TODO: Test
        async def get_user_delete_process():
            # asyncio.sleep(0.01)
            if not self.hikvision.delete_in_progress:
                status = "success"
            else:
                status = "inProgress" ## TODO: Check correct reply message
                
            return {"UserInfoDetailDeleteProcess": {"status": status}}      

        @self.app.put(ac_url + "/UserInfoDetail/Delete") ## TODO: Test
        async def put_user_delete(user: dict):
            user_to_delete = user["UserInfoDetail"]
            match user_to_delete["mode"]:
                case "byEmployeeNo":
                    self.hikvision.delete_user(user_to_delete["EmployeeNoList"])
                    return default_response(statusCode=1, statusString="OK", subStatusCode="ok")
                case _:
                    return default_response(statusCode=77, statusString="Error", subStatusCode="Emulator Invalid Mode")

        ## ---- CardInfo ----
        @self.app.get(ac_url + "/CardInfo/Count") ## TODO: Test
        async def get_card_count():
            _, cards_count, _, _ = self.hikvision.count_items()
            return {"CardInfoCount": {"cardNumber": int(cards_count)}}
        
        @self.app.post(ac_url + "/CardInfo/Search") ## TODO: Test
        async def post_card_search(item: dict):
            cond = item["CardInfoSearchCond"]
            return self.hikvision.get_remote_cards(cond["maxResults"], cond["searchResultPosition"])

        @self.app.post(ac_url + "/CardInfo/Record") ## TODO: Test
        async def post_card_record(card: dict):
            card_info = card["CardInfo"]
            trace(f'[POST] /CardInfo/Record: content= {card_info}')
            status_code = self.hikvision.add_card(card_info["employeeNo"], card_info["cardNo"])
            match status_code:
                case 1:
                    return default_response(statusCode=1, statusString="OK", subStatusCode="ok")
                case 6:
                    return default_response(
                        statusCode=6, 
                        response_code=400, 
                        statusString="Invalid Content", 
                        subStatusCode="cardNoAlreadyExist", 
                        errorCode= 1610637363, 
                        errorMsg="checkEmployeeNo"
                    )
                case _:
                    return default_response(status_code=77, statusString="Error", subStatusCode="Emulator Invalid Content")

        # @self.app.put(ac_url + "/CardInfo/Delete")
        # async def put_card_record(card: dict):
        #     return "/CardInfo/Delete"
       

        ## ---- FingerPrint ----
        # @self.app.put(ac_url + "/FingerPrint/Delete")
        # async def put_fp_delete(item: dict):
        #     pass
        
        @self.app.post(ac_url + "/FingerPrint/SetUp") ## TODO: Implement Function
        async def post_fingerprint_setup(item: dict):
            return "GetAcsCfg"
        
        @self.app.post(ac_url + "/FingerPrintUploadAll") ## TODO: Implement Function
        async def post_fingerprint_uploader():
            _, _, _, fp_count = self.hikvision.count_items()
            return {
                "statusCode":	1,
                "statusString":	"OK",
                "subStatusCode":	"ok",
                "FDRecordDataInfo":	[{
                        "FDID":	"1",
                        "faceLibType":	"blackFD",
                        "name":	"",
                        "recordDataNumber":	int(fp_count)
                    }, {
                        "FDID":	"2",
                        "faceLibType":	"infraredFD",
                        "name":	"",
                        "recordDataNumber":	0
                    }]
            }
            return "GetAcsCfg"
       
        ## ---------------------------------------------------------------
        ## ------------------------- Intelligent -------------------------
        ## ---------------------------------------------------------------
        intelli_url = "/ISAPI/Intelligent/FDLib"

        @self.app.get(intelli_url + "/Count") ## TODO: Test
        async def get_fdlib_count():
            _, _, faces_count, _ = self.hikvision.count_items()
            return {
                "statusCode":	1,
                "statusString":	"OK",
                "subStatusCode":	"ok",
                "FDRecordDataInfo":	[{
                        "FDID":	"1",
                        "faceLibType":	"blackFD",
                        "name":	"",
                        "recordDataNumber":	int(faces_count)
                    }, {
                        "FDID":	"2",
                        "faceLibType":	"infraredFD",
                        "name":	"",
                        "recordDataNumber":	0
                    }]
            }
        
        @self.app.post(intelli_url + "/FDSearch") ## TODO: Implement Function
        async def post_fingerprint_search(face_info: dict):
            return self.hikvision.get_remote_faces(face_info["maxResults"], face_info["searchResultPosition"], f"http://{self.ip}:{self.port}/LOCALS/pic/enrlFace")

        @self.app.get(intelli_url + "/LOCALS/pic/enrlFace/{user_id}")
        async def get_remote_face(user_id: str):
            return self.hikvision.get_face(user_id)
            
        
        @self.app.put(intelli_url + "/FDSearch/Delete") ## TODO: Test
        async def put_fingerprint_uploader(item: dict):
            try:
                self.hikvision.delete_face(item["FPID"][0]["value"])
                return "OK"
            
            except Exception as ex:
                report_exception(ex)
                return default_response(status_code=77, statusString="Error", subStatusCode="Emulator Invalid Content")

        @self.app.post(intelli_url + "/FaceDataRecord") ## TODO: Test
        async def upload_face_data(FaceDataRecord: str = Form(...), FaceImage: UploadFile = File(...)):
            try:
                face_data = json.loads(FaceDataRecord)
                trace(f"Face Data Record: {face_data}")

                image_data = await FaceImage.read()
                base64_image = base64.b64encode(image_data).decode()

                ret = self.hikvision.add_face(face_data["FPID"], base64_image)
                
                match ret:
                    case 1:
                        return default_response(statusCode=1, statusString="OK", subStatusCode="ok")
                    case 6:
                        default_response(
                            statusCode=6, 
                            response_code=400, 
                            statusString="Invalid Content", 
                            subStatusCode="cardNoAlreadyExist", 
                            errorCode= 1610637363, 
                            errorMsg="checkEmployeeNo"
                        )
                    case _:
                        return default_response(status_code=77, statusString="Error", subStatusCode="Emulator Invalid Content")
                        
            except Exception as ex:
                report_exception(ex)

        @self.app.put(intelli_url + "/FDSetUp") ## TODO: Test
        async def upload_face_data(FaceDataRecord: str = Form(...), FaceImage: UploadFile = File(...)):
            try:
                face_data = json.loads(FaceDataRecord)
                trace(f"Face Data Record: {face_data}")

                image_data = await FaceImage.read()
                base64_image = base64.b64encode(image_data).decode()

                ret = self.hikvision.update_face(face_data["FPID"], base64_image)
                match ret:
                    case 1:
                        return default_response(statusCode=1, statusString="OK", subStatusCode="ok")
                    case _:
                        return default_response(status_code=77, statusString="Error", subStatusCode="Emulator Invalid Content")
                        
            except Exception as ex:
                report_exception(ex)

        ## ---------------------------------------------------------------
        ## --------------------------- System ----------------------------
        ## ---------------------------------------------------------------
        system_url = "/ISAPI/System"

        @self.app.get(system_url + "/time") # OK
        async def get_datetime():
            return "OK"
        
        @self.app.put(system_url + "/time") # OK
        async def set_datetime():
            ## Body in XML
            return "OK"
        
        @self.app.get(system_url + "/deviceInfo") # OK
        async def get_device_info():
            xml_content = f"""
<?xml version="1.0" encoding="UTF-8"?>
<DeviceInfo version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <deviceName>subdoorOne</deviceName>
    <deviceID>255</deviceID>
    <model>DS-K1T673DX-BR</model>
    <serialNumber>DS-K1T673DX-BR20240206V031800ENAA8066966</serialNumber>
    <macAddress>{self.mac_address}</macAddress>
    <firmwareVersion>V3.18.0</firmwareVersion>
    <firmwareReleasedDate>build 240206</firmwareReleasedDate>
    <encoderVersion>V2.7</encoderVersion>
    <encoderReleasedDate>build 240122</encoderReleasedDate>
    <deviceType>ACS</deviceType>
    <subDeviceType>accessControlTerminal</subDeviceType>
    <telecontrolID>1</telecontrolID>
    <localZoneNum>2</localZoneNum>
    <alarmOutNum>1</alarmOutNum>
    <relayNum>2</relayNum>
    <electroLockNum>1</electroLockNum>
    <RS485Num>1</RS485Num>
    <manufacturer>Raphael Pires</manufacturer>
    <OEMCode>1</OEMCode>
    <customizedInfo>DZP20240116048</customizedInfo>
    <bspVersion>V1.17.0.642101 build 2023-11-29</bspVersion>
    <dspVersion>V2.7</dspVersion>
    <marketType>2</marketType>
    <productionDate>2023-04-28</productionDate>
</DeviceInfo>
"""
            return Response(content=xml_content, media_type="application/xml")
        
        @self.app.put(system_url + "/IO/outputs/{output_id}/trigger") ## TODO: Implement Function
        async def command_output(output_id: int, item: dict):
            trace(f'Receiving command: ')
            return

        ## ---------------------------------------------------------------
        ## --------------------------- Events ----------------------------
        ## ---------------------------------------------------------------
        system_url = "/ISAPI/Event/notification"

        @self.app.get(system_url + "/httpHosts") ## TODO: Implement Function
        async def get_device_info():
            trace('Getting Info httpHosts')
            xml_content = f"""
<?xml version="1.0" encoding="UTF-8"?>
<HttpHostNotificationList version="2.0" xmlns="http://www.isapi.org/ver20/XMLSchema">
    <HttpHostNotification>
        <id>1</id>
        <url>/w-access</url>
        <protocolType>HTTP</protocolType>
        <parameterFormatType>XML</parameterFormatType>
        <addressingFormatType>ipaddress</addressingFormatType>
        <ipAddress>172.16.17.20</ipAddress>
        <portNo>15501</portNo>
        <httpAuthenticationMethod>none</httpAuthenticationMethod>
        <SubscribeEvent>
            <heartbeat>30</heartbeat>
            <eventMode>all</eventMode>
        </SubscribeEvent>
    </HttpHostNotification>
    <HttpHostNotification>
        <id>2</id>
        <url></url>
        <protocolType>EHome</protocolType>
        <parameterFormatType>XML</parameterFormatType>
        <addressingFormatType>ipaddress</addressingFormatType>
        <ipAddress>0.0.0.0</ipAddress>
        <portNo>0</portNo>
        <httpAuthenticationMethod>none</httpAuthenticationMethod>
    </HttpHostNotification>
</HttpHostNotificationList>
"""
            return Response(content=xml_content, media_type="application/xml")

        @self.app.put(system_url + "/httpHosts") ## TODO: Implement Function
        async def set_device_info(item: dict):
            ## Body in XML
            return "OK"
        


        class AsyncGeneratorResponse(StreamingResponse):
            def __init__(self, agen):
                self.agen = agen
                super().__init__(self.iter_content(), media_type="text/event-stream")

            async def iter_content(self):
                async for chunk in self.agen:
                    yield chunk

        @self.app.get(system_url + "/alertStream") ## TODO: Implement Function
        async def GetAlertStream():
            trace(f"[GET] system_url + /alertStream")
            return AsyncGeneratorResponse(self.generate_heartbeat())
        
        # @self.app.get("/cgi-bin/snapManager.cgi")
        # async def heartbeat(request: Request):
        #     trace("[GET] /cgi-bin/snapManager.cgi")
        #     return AsyncGeneratorResponse(self.generate_heartbeat())

    async def generate_heartbeat(self):
        heartbeat_counter = time.time()
        self.genereted_event_counter = time.time()

        while True:
            now = time.time()
            if self.generated_event and (now - self.genereted_event_counter >= self.generated_event_frequency):
                trace(f'>> Sending Generated Fake Event <<')
                self.genereted_event_counter= time.time()
                evt_package = self.hikvision.generate_random_event(self)

                if evt_package and self.hikvision.get_settings("LocalAuthentication") == '1':
                    yield evt_package

            if now - heartbeat_counter >= 10:
                trace('>> Sending Heartbeat <<')
                heartbeat_counter = now
                yield self.get_heartbeat_msg()
            
            # if self.hikvision.get_settings("LocalAuthentication") == '0':
            #     break

            await asyncio.sleep(2)
    
    def get_heartbeat_msg(self): 
        hearbeat = {
            "ipAddress": self.ip,
            "portNo": self.port,
            "protocol":	"HTTP",
            "macAddress": self.mac_address,
            "channelID": 1,
            "dateTime":	"2024-04-27T15:26:41-03:00",
            "activePostCount": 1,
            "eventType": "videoloss",
            "eventState": "inactive", 
            "eventDescription": "videoloss alarm"
        }
        content_length = f'''{json.dumps(hearbeat, indent=2)}'''

        heartbeat_boundary = f"""\r
--MIME_boundary\r
Content-Type: application/json; charset="UTF-8"\r
Content-Length: {len(content_length)}\r
\r
"""     
        return f'''{heartbeat_boundary + json.dumps(hearbeat, indent=2)}\r'''


    ### ------------------------------------------------------------------
    ### ------------------------ Online events ---------------------------
    ### ------------------------------------------------------------------
    def generate_online_event(self):
        trace('Generating online event.')
        evt_package, event_reply = self.dahua.generate_online_event(self.mac_address)
        if evt_package and self.dahua.get_settings("LocalAuthentication") == '0':
            try:
                trace("Sending first online event")
                gen_evt = requests.post(self.remote_server_url + '/notification', data=evt_package, timeout=5)
                trace(f'First generated online event reply: {gen_evt.content}')
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

    # def schedule_task(self):
    #     self.scheduler.every(self.generated_event_frequency).seconds.do(self.generate_online_event)

    # def scheduler(self):
    #     schedule.every(self.generated_event_frequency).seconds.do(self.generate_online_event)
    #     while True:
    #         schedule.run_pending()   
    #         time.sleep(1)

    ### ------------------------------------------------------------------
    ### ------------------------ Online events ---------------------------
    ### ------------------------------------------------------------------
    
    def run(self):
        # threading.Thread(target=self.scheduler).start()
        ## WebServer innitialization...
        trace(f"Starting FastAPI webServer: IP={self.ip}, Port={self.port}")
        uvicorn.run(self.app, host=self.ip, port=self.port)

if __name__ == "__main__":
    port=8000
    d = HikvisionEmulator(port)
    uvicorn.run(d.app, host="192.168.0.81", port=port)