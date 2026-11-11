-- V1: Idempotent bootstrap for the Track B brvehins1 foundation.
-- This migration creates only database-level metadata and audit objects.
-- Business staging, dimensions, facts and DQ rules are added by later versions.

USE master;
GO

IF DB_ID(N'DWH_Insurance') IS NULL
BEGIN
    CREATE DATABASE [DWH_Insurance];
END;
GO

USE [DWH_Insurance];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
GO

IF SCHEMA_ID(N'meta') IS NULL EXEC(N'CREATE SCHEMA meta AUTHORIZATION dbo;');
IF SCHEMA_ID(N'stg') IS NULL EXEC(N'CREATE SCHEMA stg AUTHORIZATION dbo;');
IF SCHEMA_ID(N'dwh') IS NULL EXEC(N'CREATE SCHEMA dwh AUTHORIZATION dbo;');
IF SCHEMA_ID(N'dq') IS NULL EXEC(N'CREATE SCHEMA dq AUTHORIZATION dbo;');
GO

IF OBJECT_ID(N'meta.SchemaVersion', N'U') IS NULL
BEGIN
    CREATE TABLE meta.SchemaVersion (
        MigrationVersion NVARCHAR(50) NOT NULL PRIMARY KEY,
        Description NVARCHAR(255) NOT NULL,
        AppliedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SchemaVersion_AppliedAtUtc DEFAULT SYSUTCDATETIME(),
        AppliedBy NVARCHAR(128) NOT NULL CONSTRAINT DF_SchemaVersion_AppliedBy DEFAULT SUSER_SNAME()
    );
END;
GO

IF OBJECT_ID(N'meta.SourceFileManifest', N'U') IS NULL
BEGIN
    CREATE TABLE meta.SourceFileManifest (
        SourceFile NVARCHAR(128) NOT NULL PRIMARY KEY,
        ExpectedSourceRows BIGINT NOT NULL,
        IsCanonical BIT NOT NULL CONSTRAINT DF_SourceFileManifest_IsCanonical DEFAULT 1,
        CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SourceFileManifest_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT CK_SourceFileManifest_ExpectedSourceRows CHECK (ExpectedSourceRows > 0)
    );
END;
GO

INSERT INTO meta.SourceFileManifest (SourceFile, ExpectedSourceRows, IsCanonical)
SELECT source_values.SourceFile, source_values.ExpectedSourceRows, 1
FROM (VALUES
    (N'brvehins1a.csv', CONVERT(BIGINT, 393071)),
    (N'brvehins1b.csv', CONVERT(BIGINT, 393071)),
    (N'brvehins1c.csv', CONVERT(BIGINT, 393071)),
    (N'brvehins1d.csv', CONVERT(BIGINT, 393071)),
    (N'brvehins1e.csv', CONVERT(BIGINT, 393071))
) AS source_values (SourceFile, ExpectedSourceRows)
WHERE NOT EXISTS (
    SELECT 1
    FROM meta.SourceFileManifest AS target
    WHERE target.SourceFile = source_values.SourceFile
);
GO

IF OBJECT_ID(N'meta.IngestionBatch', N'U') IS NULL
BEGIN
    CREATE TABLE meta.IngestionBatch (
        BatchId UNIQUEIDENTIFIER NOT NULL PRIMARY KEY,
        SourceFile NVARCHAR(128) NOT NULL,
        ExpectedSourceRows BIGINT NOT NULL,
        StagingRows BIGINT NULL,
        RejectedRows BIGINT NOT NULL CONSTRAINT DF_IngestionBatch_RejectedRows DEFAULT 0,
        StartedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_IngestionBatch_StartedAtUtc DEFAULT SYSUTCDATETIME(),
        CompletedAtUtc DATETIME2(3) NULL,
        ElapsedMilliseconds BIGINT NULL,
        Status NVARCHAR(20) NOT NULL,
        ErrorMessage NVARCHAR(MAX) NULL,
        CONSTRAINT FK_IngestionBatch_SourceFileManifest
            FOREIGN KEY (SourceFile) REFERENCES meta.SourceFileManifest (SourceFile),
        CONSTRAINT CK_IngestionBatch_Status
            CHECK (Status IN (N'RUNNING', N'SUCCESS', N'FAILED', N'SKIPPED')),
        CONSTRAINT CK_IngestionBatch_ExpectedSourceRows CHECK (ExpectedSourceRows > 0),
        CONSTRAINT CK_IngestionBatch_RejectedRows CHECK (RejectedRows >= 0)
    );
END;
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id = OBJECT_ID(N'meta.IngestionBatch')
      AND name = N'UX_IngestionBatch_SuccessfulSourceFile'
)
BEGIN
    CREATE UNIQUE INDEX UX_IngestionBatch_SuccessfulSourceFile
        ON meta.IngestionBatch (SourceFile)
        WHERE Status = N'SUCCESS';
END;
GO

IF OBJECT_ID(N'meta.PipelineAudit', N'U') IS NULL
BEGIN
    CREATE TABLE meta.PipelineAudit (
        AuditId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        BatchId UNIQUEIDENTIFIER NULL,
        StageName NVARCHAR(128) NOT NULL,
        EventAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_PipelineAudit_EventAtUtc DEFAULT SYSUTCDATETIME(),
        Status NVARCHAR(20) NOT NULL,
        RowsAffected BIGINT NULL,
        Detail NVARCHAR(MAX) NULL,
        CONSTRAINT FK_PipelineAudit_IngestionBatch
            FOREIGN KEY (BatchId) REFERENCES meta.IngestionBatch (BatchId),
        CONSTRAINT CK_PipelineAudit_Status
            CHECK (Status IN (N'STARTED', N'SUCCESS', N'FAILED', N'WARNING', N'SKIPPED'))
    );
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM meta.SchemaVersion
    WHERE MigrationVersion = N'V1'
)
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V1', N'Track B brvehins1 foundation bootstrap');
END;
GO
