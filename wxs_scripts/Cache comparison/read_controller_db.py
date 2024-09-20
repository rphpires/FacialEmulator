import sqlite3
import time
import os
import shutil


from WxsDbConnection import DatabaseReader


wxs_sql = DatabaseReader()

base_path = 'C:\\Program Files (x86)\\Invenzi\\Invenzi W-Access\\Services\\SiteControllers\\Virtual SiteControllers'


def copy_db(controller_id):
    file = f"SiteController_{controller_id}\\data\\database.db"
    new_file = f"SiteController_{controller_id}\\data\\copy_database.db"

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
    file = f"SiteController_{controller_id}\\data\\copy_database.db"
    
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
    return cur.execute(script).fetchall()


def get_sitecontrollers():
    script = """
SELECT 
    lc.BaseCommPort, ControllerID
FROM CfgHWLocalControllers lc
    JOIN CfgHWControllers cont ON cont.ControllerID = lc.SiteControllerID
"""
    ret = wxs_sql.read_data(script)
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
        # print(contagem)
        for _, port, total in contagem:
            result_content[lc_id][port] = total
        
    print(result_content)


def wxs_count_chids_by_local_controller():
    ret = wxs_sql.read_data("""
SELECT 
    lc.LocalControllerID, 
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
    lc.LocalControllerID;

""")
    if not ret:
        print("Nenhum usuário")
    
    for lc_id, total in ret:
        print(f"[{lc_id}] => Total: {total}")


# wxs_count_chids_by_local_controller()

get_sitecontrollers()
