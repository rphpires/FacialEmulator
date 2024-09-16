import sqlite3
import time
import os
import shutil
import subprocess

from scripts.GlobalFunctions import *
from scripts.WxsDbConnection import DatabaseReader


sql = DatabaseReader()

base_path = r"/mnt/c/Program Files (x86)/Invenzi/Invenzi W-Access/Services/SiteControllers/Virtual SiteControllers"

def copy_db(controller_id):
    file = f"SiteController_{controller_id}/data/database.db"
    # new_file = f"running/8010/controller.db"
    new_file = f"SiteController_{controller_id}/data/copy_database.db"

    try:
        if os.path.exists(os.path.join(base_path, new_file)):
            os.remove(os.path.join(base_path, new_file))
    except Exception as ex:
        report_exception(ex)
    
   
    if os.path.exists(os.path.join(base_path, new_file)):
        os.remove(os.path.join(base_path, new_file))

    shutil.copy2(
        os.path.join(base_path, file), # Source DB file
        os.path.join(base_path, new_file)  # New DB file
    )

def check_if_service_is_running():
    service_name = 'WXSVirtualControllers'
    try:
        # Comando para verificar o status do serviço via PowerShell
        command = ['powershell.exe', '-Command', f"Get-Service -Name {service_name} | Select-Object -ExpandProperty Status"]

        # Executa o comando no WSL e captura a saída
        result = subprocess.run(command, capture_output=True, text=True)

        # Remove quebras de linha e espaços extras da saída
        service_status = result.stdout.strip()

        # Retorna o status do serviço
        if service_status == "Running":
            print(f"O serviço {service_name} está em execução.")
            return True
        elif service_status == "Stopped":
            print(f"O serviço {service_name} está parado.")
            return False
        else:
            print(f"Status desconhecido para o serviço {service_name}: {service_status}")
            return True
    except Exception as e:
        print(f"Erro ao verificar o status do serviço {service_name}: {str(e)}")
        return True


def get_chids_by_local_controller_in_sitecontroller_db(controller_id):
    print(f"Processing ControllerID= {controller_id}")
    # Cria uma copia do DB do gerencaidor para ser possível acessá-lo.
    # copy_db(controller_id)

    if check_if_service_is_running():
        return []

    # Define the database file path
    file = f"SiteController_{controller_id}/data/database.db"
    
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
    # os.remove(os.path.join(base_path, file))

    return rows

def get_chids_by_emulator_in_sitecontroller(cur):
    script = """
SELECT 
    lc.LocalControllerID,
    lc.BaseCommPort,
    COALESCE(COUNT(a.CHID), 0) AS TotalUsers
FROM 
    LocalControllers lc
LEFT JOIN 
    Readers r ON lc.LocalControllerID = r.ReaderLocalControllerID
LEFT JOIN 
    AccessLevelsContents alc ON r.ReaderID = alc.ReaderID
LEFT JOIN 
    CHAccessLevels a ON alc.AccessLevelID = a.AccessLevelID
GROUP BY 
    lc.LocalControllerID, lc.BaseCommPort;
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
            result_content[controller_id][comm_port] = 9999
        else:
            result_content[controller_id] = {}
            result_content[controller_id][comm_port] = 9999

    for lc_id in result_content.keys():
        try:
            if not (contagem := get_chids_by_local_controller_in_sitecontroller_db(lc_id)):
                continue
            for _, port, total in contagem:
                result_content[lc_id][port] = total
        except Exception as ex:
            report_exception(ex)

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
    CfgHWLocalControllers lc
LEFT JOIN 
    CfgHWReaders rdr ON lc.LocalControllerID = rdr.LocalControllerID
LEFT JOIN 
    CfgACAccessLevelsContents al_cont ON rdr.ReaderID = al_cont.ReaderID
LEFT JOIN 
    CHAccessLevels ca ON al_cont.AccessLevelID = ca.AccessLevelID
    AND ca.CHID IN (
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

