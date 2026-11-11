-- V2: Canonical staging foundation for brvehins1.
-- This migration creates typed staging and a transient text landing table.
-- It does not read or change any raw CSV file.

USE [DWH_Insurance];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'meta.IngestionBatch')
      AND name = N'UX_IngestionBatch_BatchSource'
)
BEGIN
    CREATE UNIQUE INDEX UX_IngestionBatch_BatchSource
        ON meta.IngestionBatch (BatchId, SourceFile);
END;
GO

IF OBJECT_ID(N'stg.BrVehIns1', N'U') IS NULL
BEGIN
    CREATE TABLE stg.BrVehIns1 (
        StageRowId BIGINT IDENTITY(1, 1) NOT NULL
            CONSTRAINT PK_BrVehIns1 PRIMARY KEY,
        BatchId UNIQUEIDENTIFIER NOT NULL,
        SourceFile NVARCHAR(128) NOT NULL,
        SourceRowNumber INT NOT NULL,
        SourceRecordHash CHAR(64) NOT NULL,
        LoadTimestampUtc DATETIME2(3) NOT NULL
            CONSTRAINT DF_BrVehIns1_LoadTimestampUtc DEFAULT SYSUTCDATETIME(),
        Gender NVARCHAR(20) NULL,
        DrivAge NVARCHAR(20) NULL,
        VehYear SMALLINT NULL,
        VehModel NVARCHAR(255) NULL,
        VehGroup NVARCHAR(255) NULL,
        Area NVARCHAR(100) NULL,
        State NVARCHAR(100) NULL,
        StateAb CHAR(2) NULL,
        ExposTotal DECIMAL(21, 17) NOT NULL,
        ExposFireRob DECIMAL(19, 6) NOT NULL,
        PremTotal DECIMAL(34, 27) NOT NULL,
        PremFireRob DECIMAL(19, 6) NOT NULL,
        SumInsAvg DECIMAL(19, 6) NOT NULL,
        ClaimNbRob INT NOT NULL,
        ClaimNbPartColl INT NOT NULL,
        ClaimNbTotColl INT NOT NULL,
        ClaimNbFire INT NOT NULL,
        ClaimNbOther INT NOT NULL,
        ClaimAmountRob DECIMAL(19, 6) NOT NULL,
        ClaimAmountPartColl DECIMAL(19, 6) NOT NULL,
        ClaimAmountTotColl DECIMAL(19, 6) NOT NULL,
        ClaimAmountFire DECIMAL(19, 6) NOT NULL,
        ClaimAmountOther DECIMAL(19, 6) NOT NULL,
        CONSTRAINT FK_BrVehIns1_BatchSource
            FOREIGN KEY (BatchId, SourceFile)
            REFERENCES meta.IngestionBatch (BatchId, SourceFile),
        CONSTRAINT CK_BrVehIns1_SourceRowNumber
            CHECK (SourceRowNumber > 0),
        CONSTRAINT CK_BrVehIns1_SourceRecordHashLength
            CHECK (LEN(SourceRecordHash) = 64)
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'stg.BrVehIns1')
      AND name = N'UX_BrVehIns1_SourceIdentity'
)
BEGIN
    CREATE UNIQUE INDEX UX_BrVehIns1_SourceIdentity
        ON stg.BrVehIns1 (SourceFile, SourceRowNumber);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'stg.BrVehIns1')
      AND name = N'IX_BrVehIns1_BatchId'
)
BEGIN
    CREATE INDEX IX_BrVehIns1_BatchId
        ON stg.BrVehIns1 (BatchId);
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM meta.SchemaVersion
    WHERE MigrationVersion = N'V2'
)
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V2', N'Canonical brvehins1 typed staging foundation');
END;
GO
