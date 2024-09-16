import sqlite3

from scripts.WxsDbConnection import DatabaseReader


sql = DatabaseReader()

LOCAL_CONTROLLER_ID = 251

def get_wxs_users(local_controller_id):
    script = f"""
SELECT 
    ca.CHID, m.FirstName
FROM 
    CHAccessLevels ca
JOIN 
	CHMain m ON m.CHID = ca.CHID
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
AND lc.LocalControllerID = {local_controller_id}
"""
    # print(script)
    if not (ret := sql.read_data(script)):
        print('Nenhum usuário')
    
    return ret


def get_controller_users(local_controller_id):
    # Create a connection to the database
    conn = None
    try:
        conn = sqlite3.connect("database.db")
    except sqlite3.OperationalError as e:
        print(f'**Error: {e}')

    # Create a cursor object to execute queries
    cur = conn.cursor()
    script = f"""
SELECT 
  distinct(CHAccessLevels.CHID), CHName
FROM 
  CHAccessLevels
  JOIN Cards ON Cards.CHID = CHAccessLevels.CHID and Cards.CHUserID NOT NULL
  JOIN AccessLevelsContents ON CHAccessLevels.AccessLevelID = AccessLevelsContents.AccessLevelID
  JOIN Readers ON Readers.ReaderID = AccessLevelsContents.ReaderID
  JOIN LocalControllers lc ON lc.LocalControllerID = Readers.ReaderLocalControllerID
WHERE ReaderLocalControllerID = {local_controller_id}
"""
    users = cur.execute(script).fetchall()

    # Close the cursor and connection
    cur.close()
    conn.close()

    return users

def compare_users(local_controller_id):
    wxs_users = get_wxs_users(local_controller_id)
    sc_users = get_controller_users(local_controller_id)
    
    wxs_users_dict = {id_: nome for id_, nome in wxs_users}
    sc_users_dict = {id_: nome for id_, nome in sc_users}

    wxs_users_diff = [ (_id, _name) for _id, _name in wxs_users if _id not in sc_users_dict]
    sc_users_diff = [ (_id, _name) for _id, _name in sc_users if _id not in wxs_users_dict]

    print(f'Usuários que não estão no SQL mas estão no gerenciador: Total= {len(wxs_users_diff)} | Usuários= {wxs_users_diff}')
    print(f'Usuários que não estão no Gerenciador mas estão no SQL: Total= {len(sc_users_diff)} | Usuários= {sc_users_diff}')


compare_users(LOCAL_CONTROLLER_ID)



