# Descrição: Arquivo base para conexão com o banco de dados
# Desenvolvido por: Raphael Pires
# Última Revisão: 09/08/2023

import threading
import sqlite3
import os
import datetime
import time
import sys
import queue

from threading import Thread
from scripts.GlobalFunctions import *


class DatabaseHandler(Thread):
    def __init__(self, database_type):
        super(DatabaseHandler, self).__init__()

        self.db_cursor = None
        self.file_connection = None        
        self.db_initialized = False
        self.do_stop = False
        self.requisitions = queue.Queue()

        self.db_type = database_type

        self.set_db_parameters()
        

    def create_db_connection(self):
        try:
            file_connection = sqlite3.connect(self.database_path)
            file_connection.text_factory = lambda x: str(x, "utf-8", "ignore")
            db_cursor = file_connection.cursor()
            db_cursor.execute("PRAGMA synchronous=OFF")
            db_cursor.execute("PRAGMA JOURNAL_MODE=MEMORY")
            db_cursor.execute("PRAGMA TEMP_STORE=MEMORY")
            db_cursor.execute("PRAGMA LOCKING_MODE=EXCLUSIVE")
            return file_connection, db_cursor
        except sqlite3.DatabaseError as ex:
            trace(ex)
    
    def assert_connection(self):
        if not self.db_cursor or not self.file_connection:
            ret = True
            for _ in range(2):
                try:
                    print("Opening %s file" % (self.database_path))
                    self.file_connection, self.db_cursor = self.create_db_connection()
                    return True
                except sqlite3.DatabaseError:
                    try:
                        if os.path.exists(self.database_path):
                            os.remove(self.database_path)
                        
                    except OSError as s:
                        print(str(s))
                    except Exception as e:
                        print("Error on database remove" + str(e))
                    ret = False
            return ret
        else:
            return True

    def execute(self, query, args=None, commit=True):
        if not query:
            return
        self.requisitions.put((query, args, False, commit, None))

    def executemany(self, query, args, commit=True):
        if not query:
            return
        self.requisitions.put((query, args, True, commit, None))

    def select(self, query, args=None):
        if not query:
            return []

        res = queue.Queue()

        try:
            t = "{}".format(type(threading.currentThread())).split("'")[1].split(".")[1]
        except IndexError:
            t = ""
        if t == "DatabaseHandler":
            self.execute_query(query, args, False, False, res)
        else:
            self.requisitions.put((query, args, False, True, res))

        ret = []
        # while not self.do_stop:
        rec = res.get()
        # if rec == '--no more--':
        # 	break
        if rec == "--error--":
            return None
        if rec == "--ok--":
            return []
        # ret.append(rec)
        ret = rec
        return ret
    
    def execute_query(self, query, args, execute_many, commit, result):
        for _ in range(3):
            some_error = False
            self.assert_connection()
            try:
                if query:
                    if execute_many:
                        self.db_cursor.executemany(query, args)
                    else:
                        if args:
                            self.db_cursor.execute(query, args)
                        else:
                            self.db_cursor.execute(query)
                if commit:
                    self.file_connection.commit()
            except Exception as e:
                print("SQL: '%s' %s (%s)" % (query, args, e))
                self.close_connection()
                time.sleep(1)
                some_error = True

            if some_error:
                continue

            if result:
                x = self.db_cursor.fetchall()
                result.put(x)
                return len(x)
            return

        if result:
            result.put("--error--")

    def close_connection(self):
        print("close_connection")
        if self.file_connection:
            try:
                self.file_connection.close()
            except Exception:
                pass
        self.file_connection = None
        self.db_cursor = None
        
    def disconnect(self):
        trace('Disconnecting...')
        self.close_connection()
        self.do_stop = True
        self.requisitions.put(None)


    def run(self):
        try:
            trace('Starting Database...')
            self.assert_connection()
            self.create_db()
            self.db_initialized = True
        except Exception as ex:
            print(ex)

        while not self.do_stop:
            try:
                try:
                    if not ( new_requisition := self.requisitions.get()):
                        continue

                    query, args, execute_many, commit, result = new_requisition

                except queue.Empty:
                    continue

                b = datetime.datetime.utcnow()
                result_count = self.execute_query(query, args, execute_many, commit, result)

                if not self.requisitions.empty():
                    print("Queries queue still has %s items" % (self.requisitions.qsize()))
            
            except Exception as ex:
                print(ex)
        
        
    def set_db_parameters(self):
        match self.db_type:
            case 'emulator':
                self.db_creation_string = EMULATOR_DB_CREATION_STRING
                self.test_query = "SELECT RecNo FROM DahuaCard LIMIT 1;"
                self.database_path = 'database.db'
                
            case 'service':
                self.db_creation_string = SERVICE_DB_CREATION_STRING
                self.test_query = "SELECT LocalControllerID FROM Main LIMIT 1;"
                self.database_path = r'data/database.db'
                

    def create_db(self):
        trace('Create DB')
        try:
            self.db_cursor.execute(self.test_query)
        
        except sqlite3.OperationalError:
            self.close_connection()
            commands = self.db_creation_string

            for cmd in commands.split(";"):
                trace(cmd)
                self.assert_connection()
                self.db_cursor.execute(cmd)
                self.file_connection.commit()

        # TODO: Check database
        trace("init_database done")

EMULATOR_DB_CREATION_STRING = """
-- Device Settings --
CREATE TABLE IF NOT EXISTS DeviceSettings(
[CfgID] TEXT,
[Value] TEXT
);

----------------------------  DAHUA ----------------------------
-- Dahua Card --
CREATE TABLE IF NOT EXISTS DahuaCard(
[RecNo] INTEGER PRIMARY KEY AUTOINCREMENT,
[CardName] TEXT,
[UserID] INTEGER UNIQUE,
[CardNo] TEXT UNIQUE,
[ValidDateStart] DATETIME,
[ValidDateEnd] DATETIME
);

DROP INDEX IF EXISTS [IX_DahuaCard_RecNo_UserID];
CREATE UNIQUE INDEX [IX_DahuaCard_RecNo_UserID]
ON [DahuaCard]([RecNo] ASC, [UserID] ASC);

-- Dahua Face --
CREATE TABLE IF NOT EXISTS DahuaFace(
[UserID] INTEGER PRIMARY KEY,
[MD5] TEXT
);

----------------------------  HIKVISION ----------------------------
-- Hikvision User --
CREATE TABLE IF NOT EXISTS HikvisionUser(
[employeeNo] TEXT PRIMARY KEY,
[name] TEXT,
[password] TEXT,
[localUIRight] TEXT,
[beginTime] DATETIME,
[endTime] DATETIME
);

-- Hikvision Card --
CREATE TABLE IF NOT EXISTS HikvisionCard(
[employeeNo] TEXT PRIMARY KEY,
[cardNo] TEXT
);

DROP INDEX IF EXISTS [IX_HikvisionCard_employeeNo_cardNo];
CREATE UNIQUE INDEX [IX_HikvisionCard_employeeNo_cardNo]
ON [HikvisionCard]([employeeNo] ASC, [cardNo] ASC);

-- Hikvision Face --
CREATE TABLE IF NOT EXISTS HikvisionFace(
[UserID] INTEGER PRIMARY KEY,
[PhotoData] TEXT
);

-- Hikvision FingerPrint --
CREATE TABLE IF NOT EXISTS HikvisionFinger(
[CHID] INTEGER PRIMARY KEY,
[DataIndex] INTEGER,
[Template] TEXT
);

DROP INDEX IF EXISTS [IX_HikvisionFinger_CHID_DataIndex];
CREATE UNIQUE INDEX [IX_HikvisionFinger_CHID_DataIndex]
ON [HikvisionFinger]([CHID] ASC, [DataIndex] ASC);


----------------------------  INSERTING DEFAULT SETTINGS ----------------------------

INSERT INTO DeviceSettings VALUES ('LocalAuthentication', '1');
INSERT INTO DeviceSettings VALUES ('RemoteServer', '127.0.0.1');
INSERT INTO DeviceSettings VALUES ('RemotePort', 15502);
""" 

SERVICE_DB_CREATION_STRING = """
-- Service Main --
CREATE TABLE IF NOT EXISTS Main(
[LocalControllerID] INTEGER PRIMARY KEY,
[Name] TEXT,
[IPAddress] TEXT,
[Port] INTEGER,
[Model] TEXT,
[Enabled] INTEGER,
[Type] INTEGER,
[Status] TEXT,
[EventInterval] INTEGER,
[TotalUsers] INTEGER
);

-- WXS Users to be Compared --
CREATE TABLE IF NOT EXISTS UsersCount (
[SiteControllerID] INTEGER,
[LocalControllerID] INTEGER,
[BaseCommPort] INTEGER,
[WxsCount] INTEGER,
[SiteControllerCount] INTEGER
);
"""

if __name__ == "__main__":
    port = 8001
    path = f'{port}'
    if not os.path.exists(path):
        try:
            # Tenta criar o diretório
            os.makedirs(path)
            print(f"Pasta '{path}' criada com sucesso!")
        except OSError as e:
            # Se ocorrer um erro ao criar o diretório, mostra uma mensagem de erro
            print(f"Erro ao criar pasta '{path}': {e}")
            
    db = DatabaseHandler(port)
    db.start()