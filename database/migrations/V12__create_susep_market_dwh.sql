-- V12: Track A SUSEP market dimensional model and idempotent load procedures.
-- The model intentionally has one market-observation fact; it creates no
-- customer, policy, vehicle, exposure, or cross-track relationship.

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

IF COL_LENGTH(N'meta.SusepIngestionBatch',N'SourcePremiumsAnalyticTotal') IS NULL
ALTER TABLE meta.SusepIngestionBatch ADD SourcePremiumsAnalyticTotal DECIMAL(38,18) NULL, SourceClaimsAnalyticTotal DECIMAL(38,18) NULL;
GO

IF OBJECT_ID(N'dwh.DimSusepMonth', N'U') IS NULL
CREATE TABLE dwh.DimSusepMonth (
    SusepMonthKey INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DimSusepMonth PRIMARY KEY,
    YearMonth DATE NOT NULL CONSTRAINT UQ_DimSusepMonth_YearMonth UNIQUE,
    CalendarYear SMALLINT NOT NULL,
    CalendarMonth TINYINT NOT NULL,
    CONSTRAINT CK_DimSusepMonth_MonthStart CHECK(DAY(YearMonth)=1),
    CONSTRAINT CK_DimSusepMonth_Month CHECK(CalendarMonth BETWEEN 1 AND 12)
);
GO

IF OBJECT_ID(N'dwh.DimSusepCompany', N'U') IS NULL
CREATE TABLE dwh.DimSusepCompany (
    SusepCompanyKey INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DimSusepCompany PRIMARY KEY,
    CompanyCode INT NOT NULL CONSTRAINT UQ_DimSusepCompany_Code UNIQUE,
    CompanyName NVARCHAR(116) NOT NULL
);
GO

IF OBJECT_ID(N'dwh.DimSusepProduct', N'U') IS NULL
CREATE TABLE dwh.DimSusepProduct (
    SusepProductKey INT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DimSusepProduct PRIMARY KEY,
    Product NVARCHAR(42) NOT NULL CONSTRAINT UQ_DimSusepProduct_Product UNIQUE
);
GO

IF OBJECT_ID(N'dwh.DimSusepState', N'U') IS NULL
CREATE TABLE dwh.DimSusepState (
    SusepStateKey SMALLINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_DimSusepState PRIMARY KEY,
    State NVARCHAR(2) NOT NULL CONSTRAINT UQ_DimSusepState_State UNIQUE
);
GO

IF OBJECT_ID(N'dwh.FactSusepInsuranceMarket', N'U') IS NULL
CREATE TABLE dwh.FactSusepInsuranceMarket (
    FactSusepInsuranceMarketKey BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_FactSusepInsuranceMarket PRIMARY KEY,
    SusepStageRowId BIGINT NOT NULL CONSTRAINT UQ_FactSusepInsuranceMarket_StageRow UNIQUE,
    BatchId UNIQUEIDENTIFIER NOT NULL,
    SourceFile NVARCHAR(260) NOT NULL,
    SourceFileSha256 CHAR(64) NOT NULL,
    SourceRowNumber INT NOT NULL,
    SourceRecordHash CHAR(64) NOT NULL,
    LoadTimestampUtc DATETIME2(3) NOT NULL,
    SusepMonthKey INT NOT NULL,
    SusepCompanyKey INT NOT NULL,
    SusepProductKey INT NOT NULL,
    SusepStateKey SMALLINT NOT NULL,
    Premiums DECIMAL(38,18) NOT NULL,
    Claims DECIMAL(38,18) NOT NULL,
    ClaimPremiumRatio DECIMAL(38,18) NULL,
    CONSTRAINT UQ_FactSusepInsuranceMarket_SourceIdentity UNIQUE(SourceFile,SourceFileSha256,SourceRowNumber),
    CONSTRAINT FK_FactSusepInsuranceMarket_Stage FOREIGN KEY(SusepStageRowId) REFERENCES stg.SusepInsuranceMarket(SusepStageRowId),
    CONSTRAINT FK_FactSusepInsuranceMarket_Month FOREIGN KEY(SusepMonthKey) REFERENCES dwh.DimSusepMonth(SusepMonthKey),
    CONSTRAINT FK_FactSusepInsuranceMarket_Company FOREIGN KEY(SusepCompanyKey) REFERENCES dwh.DimSusepCompany(SusepCompanyKey),
    CONSTRAINT FK_FactSusepInsuranceMarket_Product FOREIGN KEY(SusepProductKey) REFERENCES dwh.DimSusepProduct(SusepProductKey),
    CONSTRAINT FK_FactSusepInsuranceMarket_State FOREIGN KEY(SusepStateKey) REFERENCES dwh.DimSusepState(SusepStateKey),
    CONSTRAINT CK_FactSusepInsuranceMarket_SourceRowNumber CHECK(SourceRowNumber > 0),
    CONSTRAINT CK_FactSusepInsuranceMarket_SourceHash CHECK(LEN(SourceRecordHash)=64)
);
GO

CREATE OR ALTER PROCEDURE dwh.sp_LoadSusepDimensions AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
    BEGIN TRY
        IF EXISTS (
            SELECT 1 FROM stg.SusepInsuranceMarket
            GROUP BY CompanyCode HAVING COUNT(DISTINCT CompanyName) > 1
        )
            THROW 51110,N'SUSEP company_code maps to multiple company_name values; dimensions are unsafe to load.',1;

        INSERT INTO dwh.DimSusepMonth(YearMonth,CalendarYear,CalendarMonth)
        SELECT s.YearMonth,YEAR(s.YearMonth),MONTH(s.YearMonth)
        FROM stg.SusepInsuranceMarket s
        WHERE NOT EXISTS(SELECT 1 FROM dwh.DimSusepMonth d WHERE d.YearMonth=s.YearMonth)
        GROUP BY s.YearMonth;

        INSERT INTO dwh.DimSusepCompany(CompanyCode,CompanyName)
        SELECT s.CompanyCode,MIN(s.CompanyName)
        FROM stg.SusepInsuranceMarket s
        WHERE NOT EXISTS(SELECT 1 FROM dwh.DimSusepCompany d WHERE d.CompanyCode=s.CompanyCode)
        GROUP BY s.CompanyCode;

        INSERT INTO dwh.DimSusepProduct(Product)
        SELECT s.Product
        FROM stg.SusepInsuranceMarket s
        WHERE NOT EXISTS(SELECT 1 FROM dwh.DimSusepProduct d WHERE d.Product=s.Product)
        GROUP BY s.Product;

        INSERT INTO dwh.DimSusepState(State)
        SELECT s.State
        FROM stg.SusepInsuranceMarket s
        WHERE NOT EXISTS(SELECT 1 FROM dwh.DimSusepState d WHERE d.State=s.State)
        GROUP BY s.State;

        INSERT INTO meta.SusepPipelineAudit(StageName,Status,RowsAffected,Detail)
        VALUES(N'DWH_LOAD_DIMENSIONS',N'SUCCESS',
               (SELECT COUNT_BIG(*) FROM dwh.DimSusepMonth)+(SELECT COUNT_BIG(*) FROM dwh.DimSusepCompany)+(SELECT COUNT_BIG(*) FROM dwh.DimSusepProduct)+(SELECT COUNT_BIG(*) FROM dwh.DimSusepState),
               N'Month, company, product and state dimensions loaded from Track A staging.');
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        INSERT INTO meta.SusepPipelineAudit(StageName,Status,Detail) VALUES(N'DWH_LOAD_DIMENSIONS',N'FAILED',ERROR_MESSAGE());
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER PROCEDURE dwh.sp_LoadFactSusepInsuranceMarket AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;
    BEGIN TRANSACTION;
    BEGIN TRY
        INSERT INTO dwh.FactSusepInsuranceMarket(
            SusepStageRowId,BatchId,SourceFile,SourceFileSha256,SourceRowNumber,SourceRecordHash,LoadTimestampUtc,
            SusepMonthKey,SusepCompanyKey,SusepProductKey,SusepStateKey,Premiums,Claims,ClaimPremiumRatio
        )
        SELECT
            s.SusepStageRowId,s.BatchId,s.SourceFile,s.SourceFileSha256,s.SourceRowNumber,s.SourceRecordHash,s.LoadTimestampUtc,
            m.SusepMonthKey,c.SusepCompanyKey,p.SusepProductKey,g.SusepStateKey,s.Premiums,s.Claims,s.ClaimPremiumRatio
        FROM stg.SusepInsuranceMarket s
        JOIN meta.SusepIngestionBatch b ON b.BatchId=s.BatchId AND b.Status=N'SUCCESS'
        JOIN dwh.DimSusepMonth m ON m.YearMonth=s.YearMonth
        JOIN dwh.DimSusepCompany c ON c.CompanyCode=s.CompanyCode
        JOIN dwh.DimSusepProduct p ON p.Product=s.Product
        JOIN dwh.DimSusepState g ON g.State=s.State
        WHERE NOT EXISTS(SELECT 1 FROM dwh.FactSusepInsuranceMarket f WHERE f.SusepStageRowId=s.SusepStageRowId);

        DECLARE @rows BIGINT=@@ROWCOUNT;
        INSERT INTO meta.SusepPipelineAudit(StageName,Status,RowsAffected,Detail)
        VALUES(N'DWH_LOAD_FACT',N'SUCCESS',@rows,N'One fact per accepted SUSEP source market observation.');
        COMMIT;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK;
        INSERT INTO meta.SusepPipelineAudit(StageName,Status,Detail) VALUES(N'DWH_LOAD_FACT',N'FAILED',ERROR_MESSAGE());
        THROW;
    END CATCH
END;
GO

CREATE OR ALTER VIEW dwh.vwSusepInsuranceMarket AS
SELECT
    m.YearMonth,m.CalendarYear,m.CalendarMonth,c.CompanyCode,c.CompanyName,p.Product,g.State,
    f.Premiums,f.Claims,f.ClaimPremiumRatio AS SourceClaimPremiumRatio,
    CASE WHEN f.Premiums<>0 THEN f.Claims/f.Premiums END AS RowDerivedClaimPremiumRatio,
    f.SourceFile,f.SourceFileSha256,f.SourceRowNumber,f.SourceRecordHash
FROM dwh.FactSusepInsuranceMarket f
JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
JOIN dwh.DimSusepCompany c ON c.SusepCompanyKey=f.SusepCompanyKey
JOIN dwh.DimSusepProduct p ON p.SusepProductKey=f.SusepProductKey
JOIN dwh.DimSusepState g ON g.SusepStateKey=f.SusepStateKey;
GO

IF NOT EXISTS(SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion=N'V12')
INSERT INTO meta.SchemaVersion(MigrationVersion,Description)
VALUES(N'V12',N'Track A SUSEP market dimensions, one observation fact and idempotent DWH procedures');
GO
