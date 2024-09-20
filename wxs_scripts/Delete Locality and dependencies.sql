USE [W_ACCESS]
GO

DECLARE @ReaderID int
DECLARE @intError smallint
DECLARE @strError nvarchar(255)
DECLARE @LocalControllerID int
DECLARE @ControllerID int

--------- Preencher ----------
DECLARE @LocalityID int = 29
------------------------------


----- DELETE ALL READERS -----
DECLARE readers_cursor CURSOR FOR

---- Script de Select---
SELECT 
	ReaderID
FROM CfgHWLocalControllers lc
JOIN CfgHWReaders r ON r.LocalControllerID = lc.LocalControllerID
WHERE LocalityID = @LocalityID;
-------------------------

OPEN readers_cursor;
FETCH NEXT FROM readers_cursor INTO @ReaderID;

WHILE @@FETCH_STATUS = 0
BEGIN
    -- Aqui você pode realizar operações com os dados de cada linha
    EXECUTE [wsp_DeleteReader] @ReaderID, @LanguageID = 2, @intError = @intError OUTPUT, @strError = @strError OUTPUT
	
	------------------------------------------------------------------
    FETCH NEXT FROM readers_cursor INTO @ReaderID;
END;

CLOSE readers_cursor;
DEALLOCATE readers_cursor;


--- DELETE ALL LocalControllers
DECLARE localcontrollers_cursor CURSOR FOR

---- Script de Select---
SELECT LocalControllerID
FROM CfgHWLocalControllers
WHERE LocalityID = @LocalityID;

OPEN localcontrollers_cursor;
FETCH NEXT FROM localcontrollers_cursor INTO @LocalControllerID;

WHILE @@FETCH_STATUS = 0
BEGIN
    -- Aqui você pode realizar operações com os dados de cada linha
    EXECUTE [wsp_DeleteLocalControllerDependents] @LocalControllerID = @LocalControllerID, @LanguageID = 2, @ProfileID = 0, @intError = @intError OUTPUT, @strError = @strError OUTPUT
	
	DELETE FROM CfgHWLocalControllers WHERE LocalControllerID = @LocalControllerID

    ----------------------------------------------------------------------
	FETCH NEXT FROM localcontrollers_cursor INTO @LocalControllerID;
END;

CLOSE localcontrollers_cursor;
DEALLOCATE localcontrollers_cursor;



--- Deleta todos os Gerenciadores
DECLARE controllers_cursor CURSOR FOR

---- Script de Select---
SELECT ControllerID
FROM CfgHWControllers
WHERE LocalityID = @LocalityID;;

OPEN controllers_cursor;
FETCH NEXT FROM controllers_cursor INTO @ControllerID;

WHILE @@FETCH_STATUS = 0
BEGIN
    -- Aqui você pode realizar operações com os dados de cada linha
    EXECUTE [wsp_DeleteController] @ControllerID = @ControllerID, @LanguageID = 2, @intError = @intError OUTPUT, @strError = @strError OUTPUT

    ----------------------------------------------------------------------
	FETCH NEXT FROM controllers_cursor INTO @ControllerID;
END;

CLOSE controllers_cursor;
DEALLOCATE controllers_cursor;


---- Script de Select---
SELECT LocalityID
FROM CfgSYLocalities
WHERE LocalityID = @LocalityID;

-- Aqui você pode realizar operações com os dados de cada linha
EXECUTE [wsp_DeleteLocalityDependents] @LocalityID = @LocalityID, @LocalityIDNew = 0, @LanguageID = 2, @ProfileID = 0, @intError = @intError OUTPUT, @strError = @strError OUTPUT
EXECUTE [wsp_DeleteLocality] @LocalityID = @LocalityID, @LanguageID = 2, @intError = @intError OUTPUT, @strError = @strError OUTPUT
   