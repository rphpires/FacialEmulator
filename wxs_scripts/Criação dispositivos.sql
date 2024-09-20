--------------------------------------------------------------
-- Script to create devices entity to run facial Emulators
-- Date: 12/08/2024
-- Author: Raphael Pires
--------------------------------------------------------------
USE [W_ACCESS]
GO

--------------------------------------
-- Preencher:
DECLARE 
@DeviceModel int = 0 --- 0: Dahua, 1: Hikvision
,@DeviceQnt int = 4 -- Quantidade total de emuladores a serem criados
,@EmulatorServerIPAddress varchar(50) = '172.23.13.159' -- IP do servidor dos emuladores
,@SiteControllerIPAddress varchar(50) = '172.23.0.1'

--------------------------------------
--------------------------------------
,@InitialPort int = (Select MAX(BaseCommPort) from CfgHWLocalControllers) + 2 -- Porta incial do range
,@PortInterval int = 2  -- Intervalo das portas dos emuladores
,@SubstringName varchar(50) 

SET @SubstringName = CAST(@InitialPort AS Varchar) 
					+ ' - ' 
					+ CAST((@InitialPort + (@DeviceQnt * @PortInterval) - @PortInterval) as varchar)

-- Print @SubstringName

----------------------------
-------- Localities --------
----------------------------
DECLARE @RCLocality int
DECLARE @strLanguage varchar(50) = 'Localidade Emuladores ' + @SubstringName
DECLARE @LanguageID smallint = 2
DECLARE @PartitionID int = 0
DECLARE @TimeZoneID int = 2
DECLARE @GMTOffset smallint = -180
DECLARE @intError smallint
DECLARE @strError nvarchar(255)
DECLARE @LocalityID int


EXECUTE @RCLocality = [dbo].[wsp_AddLocality] 
   @strLanguage
  ,@strLanguage
  ,@strLanguage
  ,@strLanguage
  ,@LanguageID
  ,@PartitionID
  ,1 -- ParentID
  ,@TimeZoneID
  ,@GMTOffset
  ,@intError OUTPUT
  ,@strError OUTPUT
  ,@LocalityID OUTPUT

-- Select @LocalityID

--------------------------------
-------- SiteController --------
--------------------------------

BEGIN TRANSACTION

DECLARE @ControllerName varchar(50) = 'Gerenciador ' + @SubstringName
DECLARE @ControllerDescription varchar(100) = ''
DECLARE @BaseCommPort int
DECLARE @ControllerID int

SET @BaseCommPort = (SELECT MAX(baseCommPort) + 10 FROM CfgHWControllers)
IF @BaseCommPort IS NULL
	SET @BaseCommPort = 5500

PRINT @BaseCommPort

EXECUTE [dbo].[wsp_AddController] 
   @ControllerName
  ,@ControllerDescription
  ,@SiteControllerIPAddress
  ,@BaseCommPort
  ,@PartitionID
  ,@LocalityID
  ,@GMTOffset
  ,@LanguageID
  ,@intError OUTPUT
  ,@strError OUTPUT
  ,@ControllerID OUTPUT


-- Verifica se o @ControllerID é NULL ou 0
IF @ControllerID IS NULL OR @ControllerID = 0
BEGIN
    -- Executa o comando de exclusão antes de interromper a execução
    EXECUTE [dbo].[wsp_DeleteLocality] @LocalityID, @LanguageID, @intError OUTPUT, @strError OUTPUT;
    
    -- Reverte as alterações antes de lançar o erro
    ROLLBACK TRANSACTION;

    -- Interrompe a execução com uma mensagem de erro
    THROW 50000, 'Execução interrompida: Erro ao criar o gerenciador, verifique se a porta inicial já está em uso.', 1;
END

-- Commit da transação se tudo estiver correto
COMMIT TRANSACTION;

--------------------------------
--------- Controllers  ---------
--------------------------------

--Select * from CfgHWLocalControllers

DECLARE
	@Counter int = 0
	,@PortNo int = @InitialPort
	,@DeviceName varchar(100)
	,@LCType int
	,@ReaderName varchar(100)
	,@LocalControllerID int
	,@ReaderID int
	,@RandomValue INT
	,@DescriptionString NVARCHAR(50);


IF @DeviceModel = 0 
	BEGIN
		SET @DeviceName = 'Dahua'
		SET @LCType = 22121
	END
ELSE 
	BEGIN
		SET @DeviceName = 'Hikvision'
		SET @LCType = 21101
	END

--Select * from CfgHWLocalControllerTypes
--where LocalControllerTypeID in (21101, 22121, 22131)

-- Loop para iterar sobre a quantidade de dispositivos
WHILE @Counter < @DeviceQnt
BEGIN
	SET @RandomValue = FLOOR(RAND(CHECKSUM(NEWID())) * (200 - 20 + 1)) + 20;
	SET @DescriptionString = REPLACE('emulator_X', 'X', CAST(@RandomValue AS NVARCHAR));
    ---------------------------------------
    -- SELECT @PortNo AS PortaAtual
	INSERT INTO CfgHWLocalControllers
	VALUES (
		@DeviceName + ' ' + cast(@PortNo as Varchar), @DescriptionString, @ControllerID, @PartitionID, @LCType, @EmulatorServerIPAddress, @PortNo,  
		1, 1, NULL, NULL, @LocalityID, 'Emulator v1.0', NULL, 1, 0, NULL, NULL, NULL, NULL
	)
	SET @LocalControllerID = (
		SELECT LocalControllerID FROM CfgHWLocalControllers 
		WHERE IPAddress = @EmulatorServerIPAddress 
		AND BaseCommPort = @PortNo
	)

	-- ADD Reader
	SET @ReaderName = @DeviceName + ' ' + CAST(@PortNo as varchar)
	EXECUTE [dbo].[wsp_AddReader]  @ReaderName, '', @PartitionID, @LanguageID, @LocalControllerID, '', '', @intError OUTPUT, @strError OUTPUT, @ReaderID OUTPUT

	UPDATE CfgHWReaders
	SET ReaderHWID = 1, CardFormatID = 1
	WHERE ReaderID = @ReaderID

	---------------------------------------
    SET @PortNo = @PortNo + @PortInterval
    SET @Counter = @Counter + 1
END