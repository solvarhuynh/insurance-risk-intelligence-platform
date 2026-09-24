-- V9: isolated CDC engineering demonstration for P1-INC-02.
-- This never enables CDC on canonical staging or fact tables.

USE [DWH_Insurance];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET XACT_ABORT ON;
GO

IF (SELECT is_cdc_enabled FROM sys.databases WHERE name = DB_NAME()) = 0
BEGIN
    EXEC sys.sp_cdc_enable_db;
END;
GO

IF OBJECT_ID(N'meta.CdcDemoOperationalRecord', N'U') IS NULL
BEGIN
    CREATE TABLE meta.CdcDemoOperationalRecord (
        OperationalRecordId BIGINT IDENTITY(1, 1) NOT NULL
            CONSTRAINT PK_CdcDemoOperationalRecord PRIMARY KEY,
        DemoRunId UNIQUEIDENTIFIER NOT NULL,
        OperationalStatus NVARCHAR(32) NOT NULL,
        DemoNote NVARCHAR(200) NOT NULL,
        CreatedAtUtc DATETIME2(3) NOT NULL
            CONSTRAINT DF_CdcDemoOperationalRecord_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        UpdatedAtUtc DATETIME2(3) NOT NULL
            CONSTRAINT DF_CdcDemoOperationalRecord_UpdatedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT CK_CdcDemoOperationalRecord_Status
            CHECK (OperationalStatus IN (N'INITIAL', N'UPDATED', N'INSERTED'))
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM cdc.change_tables
    WHERE source_object_id = OBJECT_ID(N'meta.CdcDemoOperationalRecord')
)
BEGIN
    EXEC sys.sp_cdc_enable_table
        @source_schema = N'meta',
        @source_name = N'CdcDemoOperationalRecord',
        @role_name = NULL,
        @supports_net_changes = 0;
END;
GO

IF OBJECT_ID(N'meta.CdcConsumerWatermark', N'U') IS NULL
BEGIN
    CREATE TABLE meta.CdcConsumerWatermark (
        ConsumerName NVARCHAR(128) NOT NULL
            CONSTRAINT PK_CdcConsumerWatermark PRIMARY KEY,
        LastStartLsn BINARY(10) NOT NULL,
        UpdatedAtUtc DATETIME2(3) NOT NULL
            CONSTRAINT DF_CdcConsumerWatermark_UpdatedAtUtc DEFAULT SYSUTCDATETIME()
    );
END;
GO

IF OBJECT_ID(N'meta.CdcDemoConsumedChange', N'U') IS NULL
BEGIN
    CREATE TABLE meta.CdcDemoConsumedChange (
        ConsumerName NVARCHAR(128) NOT NULL,
        DemoRunId UNIQUEIDENTIFIER NOT NULL,
        StartLsn BINARY(10) NOT NULL,
        SequenceValue BINARY(10) NOT NULL,
        OperationCode INT NOT NULL,
        ConsumedAtUtc DATETIME2(3) NOT NULL
            CONSTRAINT DF_CdcDemoConsumedChange_ConsumedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT PK_CdcDemoConsumedChange
            PRIMARY KEY (ConsumerName, StartLsn, SequenceValue, OperationCode)
    );
END;
GO

CREATE OR ALTER PROCEDURE meta.sp_ConsumeCdcDemoChanges
    @ConsumerName NVARCHAR(128),
    @DemoRunId UNIQUEIDENTIFIER
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @InsertedRows BIGINT = 0;
    DECLARE @LastStartLsn BINARY(10);

    BEGIN TRANSACTION;
    BEGIN TRY
        INSERT INTO meta.CdcDemoConsumedChange (
            ConsumerName, DemoRunId, StartLsn, SequenceValue, OperationCode
        )
        SELECT
            @ConsumerName,
            changes.DemoRunId,
            changes.__$start_lsn,
            changes.__$seqval,
            changes.__$operation
        FROM cdc.meta_CdcDemoOperationalRecord_CT AS changes
        WHERE changes.DemoRunId = @DemoRunId
          AND NOT EXISTS (
              SELECT 1
              FROM meta.CdcDemoConsumedChange AS consumed
              WHERE consumed.ConsumerName = @ConsumerName
                AND consumed.StartLsn = changes.__$start_lsn
                AND consumed.SequenceValue = changes.__$seqval
                AND consumed.OperationCode = changes.__$operation
          );
        SET @InsertedRows = @@ROWCOUNT;

        SELECT TOP (1)
            @LastStartLsn = changes.__$start_lsn
        FROM cdc.meta_CdcDemoOperationalRecord_CT AS changes
        WHERE changes.DemoRunId = @DemoRunId
        ORDER BY changes.__$start_lsn DESC, changes.__$seqval DESC;

        IF @LastStartLsn IS NOT NULL
        BEGIN
            UPDATE meta.CdcConsumerWatermark
            SET LastStartLsn = @LastStartLsn,
                UpdatedAtUtc = SYSUTCDATETIME()
            WHERE ConsumerName = @ConsumerName;

            IF @@ROWCOUNT = 0
            BEGIN
                INSERT INTO meta.CdcConsumerWatermark (ConsumerName, LastStartLsn)
                VALUES (@ConsumerName, @LastStartLsn);
            END;
        END;

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        THROW;
    END CATCH;

    SELECT @InsertedRows AS NewlyConsumedRows, @LastStartLsn AS LastStartLsn;
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion = N'V9'
)
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V9', N'Isolated synthetic CDC engineering demonstration');
END;
GO
