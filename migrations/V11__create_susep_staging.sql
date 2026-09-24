-- V11: Track A SUSEP staging and ingestion metadata.
-- This migration deliberately creates objects separate from Track B brvehins1.
-- Raw CSV stays outside SQL Server and is never modified by this migration.

USE [DWH_Insurance];
GO

SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO

IF OBJECT_ID(N'meta.SusepSourceFileManifest', N'U') IS NULL
CREATE TABLE meta.SusepSourceFileManifest (
    SourceFile NVARCHAR(260) NOT NULL CONSTRAINT PK_SusepSourceFileManifest PRIMARY KEY,
    ExpectedSourceRows BIGINT NOT NULL,
    ExpectedSourceBytes BIGINT NOT NULL,
    ExpectedHeader NVARCHAR(500) NOT NULL,
    IsCanonical BIT NOT NULL CONSTRAINT DF_SusepSourceFileManifest_IsCanonical DEFAULT 1,
    CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepSourceFileManifest_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_SusepSourceFileManifest_Rows CHECK (ExpectedSourceRows > 0),
    CONSTRAINT CK_SusepSourceFileManifest_Bytes CHECK (ExpectedSourceBytes > 0)
);
GO

IF NOT EXISTS (SELECT 1 FROM meta.SusepSourceFileManifest WHERE SourceFile=N'insurance_dataset.csv')
INSERT INTO meta.SusepSourceFileManifest(SourceFile,ExpectedSourceRows,ExpectedSourceBytes,ExpectedHeader,IsCanonical)
VALUES(N'insurance_dataset.csv',8338214,751126569,N'company_code,company_name,year_month,product,state,premiums,claims,claim_premium_ratio',1);
GO

IF OBJECT_ID(N'meta.SusepIngestionBatch', N'U') IS NULL
CREATE TABLE meta.SusepIngestionBatch (
    BatchId UNIQUEIDENTIFIER NOT NULL CONSTRAINT PK_SusepIngestionBatch PRIMARY KEY,
    SourceFile NVARCHAR(260) NOT NULL,
    SourceFileSha256 CHAR(64) NOT NULL,
    SourceBytes BIGINT NOT NULL,
    ExpectedSourceRows BIGINT NOT NULL,
    AcceptedRows BIGINT NULL,
    RejectedRows BIGINT NOT NULL CONSTRAINT DF_SusepIngestionBatch_RejectedRows DEFAULT 0,
    StartedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepIngestionBatch_StartedAtUtc DEFAULT SYSUTCDATETIME(),
    CompletedAtUtc DATETIME2(3) NULL,
    ElapsedMilliseconds BIGINT NULL,
    Status NVARCHAR(20) NOT NULL,
    ErrorMessage NVARCHAR(2048) NULL,
    CONSTRAINT UQ_SusepIngestionBatch_BatchSource UNIQUE(BatchId,SourceFile),
    CONSTRAINT FK_SusepIngestionBatch_Manifest FOREIGN KEY(SourceFile) REFERENCES meta.SusepSourceFileManifest(SourceFile),
    CONSTRAINT CK_SusepIngestionBatch_Status CHECK(Status IN(N'RUNNING',N'SUCCESS',N'FAILED')),
    CONSTRAINT CK_SusepIngestionBatch_Rows CHECK(ExpectedSourceRows > 0 AND RejectedRows >= 0),
    CONSTRAINT CK_SusepIngestionBatch_SourceHash CHECK(LEN(SourceFileSha256)=64)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'meta.SusepIngestionBatch') AND name=N'UX_SusepIngestionBatch_SuccessfulSourceVersion')
CREATE UNIQUE INDEX UX_SusepIngestionBatch_SuccessfulSourceVersion
ON meta.SusepIngestionBatch(SourceFile,SourceFileSha256)
WHERE Status=N'SUCCESS';
GO

IF OBJECT_ID(N'meta.SusepPipelineAudit', N'U') IS NULL
CREATE TABLE meta.SusepPipelineAudit (
    AuditId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SusepPipelineAudit PRIMARY KEY,
    BatchId UNIQUEIDENTIFIER NULL,
    StageName NVARCHAR(128) NOT NULL,
    EventAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepPipelineAudit_EventAtUtc DEFAULT SYSUTCDATETIME(),
    Status NVARCHAR(20) NOT NULL,
    RowsAffected BIGINT NULL,
    Detail NVARCHAR(2048) NULL,
    CONSTRAINT FK_SusepPipelineAudit_Batch FOREIGN KEY(BatchId) REFERENCES meta.SusepIngestionBatch(BatchId),
    CONSTRAINT CK_SusepPipelineAudit_Status CHECK(Status IN(N'STARTED',N'SUCCESS',N'FAILED',N'WARNING',N'SKIPPED'))
);
GO

IF OBJECT_ID(N'stg.SusepInsuranceMarket', N'U') IS NULL
CREATE TABLE stg.SusepInsuranceMarket (
    SusepStageRowId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SusepInsuranceMarket PRIMARY KEY,
    BatchId UNIQUEIDENTIFIER NOT NULL,
    SourceFile NVARCHAR(260) NOT NULL,
    SourceFileSha256 CHAR(64) NOT NULL,
    SourceRowNumber INT NOT NULL,
    SourceRecordHash CHAR(64) NOT NULL,
    LoadTimestampUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepInsuranceMarket_LoadTimestampUtc DEFAULT SYSUTCDATETIME(),
    CompanyCode INT NOT NULL,
    CompanyName NVARCHAR(116) NOT NULL,
    YearMonth DATE NOT NULL,
    Product NVARCHAR(42) NOT NULL,
    State NVARCHAR(2) NOT NULL,
    PremiumsRaw NVARCHAR(100) NOT NULL,
    Premiums DECIMAL(38,18) NOT NULL,
    ClaimsRaw NVARCHAR(100) NOT NULL,
    Claims DECIMAL(38,18) NOT NULL,
    ClaimPremiumRatioRaw NVARCHAR(100) NULL,
    ClaimPremiumRatio DECIMAL(38,18) NULL,
    CONSTRAINT FK_SusepInsuranceMarket_BatchSource FOREIGN KEY(BatchId,SourceFile) REFERENCES meta.SusepIngestionBatch(BatchId,SourceFile),
    CONSTRAINT UQ_SusepInsuranceMarket_SourceIdentity UNIQUE(SourceFile,SourceFileSha256,SourceRowNumber),
    CONSTRAINT CK_SusepInsuranceMarket_SourceRowNumber CHECK(SourceRowNumber > 0),
    CONSTRAINT CK_SusepInsuranceMarket_SourceHash CHECK(LEN(SourceRecordHash)=64),
    CONSTRAINT CK_SusepInsuranceMarket_MonthStart CHECK(DAY(YearMonth)=1)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'stg.SusepInsuranceMarket') AND name=N'IX_SusepInsuranceMarket_Batch')
CREATE INDEX IX_SusepInsuranceMarket_Batch ON stg.SusepInsuranceMarket(BatchId);
GO

IF OBJECT_ID(N'stg.SusepInsuranceMarketReject', N'U') IS NULL
CREATE TABLE stg.SusepInsuranceMarketReject (
    SusepRejectId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SusepInsuranceMarketReject PRIMARY KEY,
    BatchId UNIQUEIDENTIFIER NOT NULL,
    SourceFile NVARCHAR(260) NOT NULL,
    SourceFileSha256 CHAR(64) NOT NULL,
    SourceRowNumber INT NOT NULL,
    SourceRecordHash CHAR(64) NOT NULL,
    RawPayload NVARCHAR(MAX) NOT NULL,
    RejectReason NVARCHAR(2048) NOT NULL,
    RejectedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepInsuranceMarketReject_RejectedAtUtc DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_SusepInsuranceMarketReject_BatchSource FOREIGN KEY(BatchId,SourceFile) REFERENCES meta.SusepIngestionBatch(BatchId,SourceFile),
    CONSTRAINT UQ_SusepInsuranceMarketReject_SourceIdentity UNIQUE(SourceFile,SourceFileSha256,SourceRowNumber),
    CONSTRAINT CK_SusepInsuranceMarketReject_SourceRowNumber CHECK(SourceRowNumber > 0),
    CONSTRAINT CK_SusepInsuranceMarketReject_SourceHash CHECK(LEN(SourceRecordHash)=64)
);
GO

IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID(N'stg.SusepInsuranceMarketReject') AND name=N'IX_SusepInsuranceMarketReject_Batch')
CREATE INDEX IX_SusepInsuranceMarketReject_Batch ON stg.SusepInsuranceMarketReject(BatchId);
GO

IF NOT EXISTS (SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion=N'V11')
INSERT INTO meta.SchemaVersion(MigrationVersion,Description)
VALUES(N'V11',N'Track A SUSEP staging, reject handling and separate ingestion metadata');
GO
