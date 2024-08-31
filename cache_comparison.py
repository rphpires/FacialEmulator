import sqlite3
import time
import os
import shutil

from GlobalFunctions import *
from WxsDbConnection import DatabaseReader


sql = DatabaseReader()

base_path = r"/mnt/c/Program Files (x86)/Invenzi/Invenzi W-Access/Services/SiteControllers/Virtual SiteControllers"

def copy_db(controller_id):
    file = f"SiteController_{controller_id}/data/database.db"
    new_file = f"SiteController_{controller_id}/data/copy_database.db"

    if os.path.exists(os.path.join(base_path, new_file)):
        os.remove(os.path.join(base_path, new_file))

    shutil.copyfile(
        os.path.join(base_path, file), # Source DB file
        os.path.join(base_path, new_file)  # New DB file
    )

def get_chids_by_local_controller_in_sitecontroller_db(controller_id):
    print(f"Processing ControllerID= {controller_id}")
    # Cria uma copia do DB do gerencaidor para ser possível acessá-lo.
    copy_db(controller_id)

    # Define the database file path
    file = f"SiteController_{controller_id}/data/copy_database.db"
    
    # Define the timeout value (in seconds) to wait for the database to be available
    timeout = 30

    # Define the number of retries to attempt before giving up
    retries = 5

    # Create a connection to the database
    conn = None
    for attempt in range(retries):
        try:
            conn = sqlite3.connect(os.path.join(base_path, file), timeout=timeout)
            break
        except sqlite3.OperationalError as e:
            if attempt < retries - 1:
                print(f"Attempt {attempt+1} failed: {e}. Retrying...")
                time.sleep(timeout)
            else:
                raise

    # Create a cursor object to execute queries
    cur = conn.cursor()
    rows = get_chids_by_emulator_in_sitecontroller(cur)

    # Close the cursor and connection
    cur.close()
    conn.close()

    # Deleta o DB criado após sua leitura
    os.remove(os.path.join(base_path, file))

    return rows

def get_chids_by_emulator_in_sitecontroller(cur):
    script = """
WITH AgrupedCHIDs AS (
	SELECT 
	  ReaderLocalControllerID, 
	  BaseCommPort,
	  CHID
	FROM 
	  CHAccessLevels
	  JOIN AccessLevelsContents ON CHAccessLevels.AccessLevelID = AccessLevelsContents.AccessLevelID
	  JOIN Readers ON Readers.ReaderID = AccessLevelsContents.ReaderID
	  JOIN LocalControllers lc ON lc.LocalControllerID = Readers.ReaderLocalControllerID
	--WHERE ReaderLocalControllerID = 251
	GROUP BY ReaderLocalControllerID, BaseCommPort, CHID
)
Select 
	ReaderLocalControllerID,
	BaseCommPort,
	count(CHID) as TotalUsers
from AgrupedCHIDs
GROUP BY ReaderLocalControllerID, BaseCommPort
"""
    # time.sleep()
    return cur.execute(script).fetchall()

def count_users_in_sitecontroller_db(wxs_conn):
    script = """
SELECT 
    lc.BaseCommPort, ControllerID
FROM CfgHWLocalControllers lc
    JOIN CfgHWControllers cont ON cont.ControllerID = lc.SiteControllerID
"""
    ret = wxs_conn.read_data(script)
    if not ret:
        print('Nenhum gerenciador')
        return
    
    result_content = {}
    for comm_port, controller_id in ret:
        if result_content.get(controller_id):
            result_content[controller_id][comm_port] = 0
        else:
            result_content[controller_id] = {}
            result_content[controller_id][comm_port] = 0

    for lc_id in result_content.keys():
        contagem = get_chids_by_local_controller_in_sitecontroller_db(lc_id)
        for _, port, total in contagem:
            result_content[lc_id][port] = total
        
    print("result_content= ", result_content)
    return result_content

def wxs_count_chids_by_local_controller(wxs_conn):
    ret = wxs_conn.read_data("""
SELECT 
	lc.SiteControllerID,
    lc.LocalControllerID, 
    lc.BaseCommPort,
    COUNT(DISTINCT ca.CHID) AS CHID_Count
FROM 
    CHAccessLevels ca
JOIN 
    CfgACAccessLevelsContents al_cont ON ca.AccessLevelID = al_cont.AccessLevelID
JOIN 
    CfgHWReaders rdr ON al_cont.ReaderID = rdr.ReaderID
JOIN 
    CfgHWLocalControllers lc ON rdr.LocalControllerID = lc.LocalControllerID
WHERE 
    ca.CHID IN (
        SELECT CHID 
        FROM CHCards
        WHERE IPRdrUserID IS NOT NULL
    )
GROUP BY 
    lc.LocalControllerID, lc.SiteControllerID, lc.BaseCommPort;
""")
    if not ret:
        print("Nenhum usuário")
    
    wxs_count = {}
    for site_controller_id, lc_id, port, total in ret:
        try:
            print(f"[{lc_id}] => Total: {total}")
            if not wxs_count.get(site_controller_id):
                wxs_count[site_controller_id] = {}
               
            wxs_count[site_controller_id][lc_id] = (port, total)
        
        except Exception as ex:
            report_exception(ex)

    return wxs_count

# ret = wxs_count_chids_by_local_controller(sql)
# for site_controller_id, lcs in ret.items():
#     for lc_id, total in lcs.items():
#         print(f"Gerenciador: {site_controller_id}, LocalControllerID= {lc_id} | Total= {total}")

# count_users_in_sitecontroller_db(sql)


def list_items_in_path():
    # Get the list of all files in a directory
    files = os.listdir(base_path)

    # Print the files
    for file in files:
        print(file)

# list_items_in_path()
