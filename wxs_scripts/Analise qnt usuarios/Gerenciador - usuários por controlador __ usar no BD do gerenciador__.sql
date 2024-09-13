SELECT 
  distinct(CHAccessLevels.CHID), CHName
FROM 
  CHAccessLevels
  JOIN Cards ON Cards.CHID = CHAccessLevels.CHID and Cards.CHUserID NOT NULL
  JOIN AccessLevelsContents ON CHAccessLevels.AccessLevelID = AccessLevelsContents.AccessLevelID
  JOIN Readers ON Readers.ReaderID = AccessLevelsContents.ReaderID
  JOIN LocalControllers lc ON lc.LocalControllerID = Readers.ReaderLocalControllerID
WHERE ReaderLocalControllerID = {ID}