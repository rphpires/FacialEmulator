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