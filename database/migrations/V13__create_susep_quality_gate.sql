-- V13: executable Track-A SUSEP DQ and source-to-fact reconciliation evidence.
-- Track-A rules and logs are deliberately separate from dq.sp_RunQualityGate
-- because Track B has different grain and financial-measure semantics.

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

IF OBJECT_ID(N'meta.SusepReconciliationRun', N'U') IS NULL
CREATE TABLE meta.SusepReconciliationRun (
    SusepReconciliationRunId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SusepReconciliationRun PRIMARY KEY,
    BatchId UNIQUEIDENTIFIER NOT NULL,
    SourceRows BIGINT NOT NULL,
    AcceptedRows BIGINT NOT NULL,
    RejectedRows BIGINT NOT NULL,
    StagingRows BIGINT NOT NULL,
    FactRows BIGINT NOT NULL,
    SourcePremiumsAnalyticTotal DECIMAL(38,18) NOT NULL,
    StagingPremiumsTotal DECIMAL(38,18) NOT NULL,
    FactPremiumsTotal DECIMAL(38,18) NOT NULL,
    SourceClaimsAnalyticTotal DECIMAL(38,18) NOT NULL,
    StagingClaimsTotal DECIMAL(38,18) NOT NULL,
    FactClaimsTotal DECIMAL(38,18) NOT NULL,
    Status NVARCHAR(20) NOT NULL,
    Detail NVARCHAR(2048) NOT NULL,
    ReconciledAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepReconciliationRun_ReconciledAtUtc DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_SusepReconciliationRun_Batch FOREIGN KEY(BatchId) REFERENCES meta.SusepIngestionBatch(BatchId),
    CONSTRAINT CK_SusepReconciliationRun_Status CHECK(Status IN(N'SUCCESS',N'FAILED'))
);
GO

IF OBJECT_ID(N'dq.SusepQualityCheckLog', N'U') IS NULL
CREATE TABLE dq.SusepQualityCheckLog (
    SusepQualityCheckLogId BIGINT IDENTITY(1,1) NOT NULL CONSTRAINT PK_SusepQualityCheckLog PRIMARY KEY,
    DqRunId UNIQUEIDENTIFIER NOT NULL,
    RunLabel NVARCHAR(128) NOT NULL,
    RuleName NVARCHAR(128) NOT NULL,
    RuleDomain NVARCHAR(32) NOT NULL,
    Severity NVARCHAR(10) NOT NULL,
    Status NVARCHAR(10) NOT NULL,
    ObservedValue BIGINT NULL,
    ExpectedValue BIGINT NULL,
    Detail NVARCHAR(1000) NOT NULL,
    CheckedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_SusepQualityCheckLog_CheckedAtUtc DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_SusepQualityCheckLog_Severity CHECK(Severity IN(N'HARD',N'WARNING')),
    CONSTRAINT CK_SusepQualityCheckLog_Status CHECK(Status IN(N'PASS',N'WARNING',N'FAIL'))
);
GO

CREATE OR ALTER PROCEDURE dq.sp_RunSusepQualityGate
    @RunLabel NVARCHAR(128)=N'production',
    @InjectControlledFailure BIT=0
AS
BEGIN
    SET NOCOUNT ON;
    DECLARE @run_id UNIQUEIDENTIFIER=NEWID();
    DECLARE @rules TABLE(
        RuleName NVARCHAR(128),RuleDomain NVARCHAR(32),Severity NVARCHAR(10),
        ObservedValue BIGINT NULL,ExpectedValue BIGINT NULL,Detail NVARCHAR(1000)
    );

    INSERT @rules
    SELECT N'STG_REQUIRED_COLUMNS',N'STAGING',N'HARD',ABS(COUNT(*)-18),0,N'stg.SusepInsuranceMarket must contain 18 Track-A columns' FROM sys.columns WHERE object_id=OBJECT_ID(N'stg.SusepInsuranceMarket');
    INSERT @rules
    SELECT N'STG_SUCCESS_BATCH_RECONCILIATION',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Every SUCCESS batch must satisfy expected source rows = accepted + rejected = physical accepted/reject rows'
    FROM meta.SusepIngestionBatch b
    OUTER APPLY(SELECT COUNT_BIG(*) AS c FROM stg.SusepInsuranceMarket s WHERE s.BatchId=b.BatchId) s
    OUTER APPLY(SELECT COUNT_BIG(*) AS c FROM stg.SusepInsuranceMarketReject r WHERE r.BatchId=b.BatchId) r
    WHERE b.Status=N'SUCCESS' AND (b.ExpectedSourceRows<>b.AcceptedRows+b.RejectedRows OR b.AcceptedRows<>s.c OR b.RejectedRows<>r.c);
    INSERT @rules
    SELECT N'STG_REJECTED_SOURCE_ROWS',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Canonical source contract is expected to have no rejected rows; rejected records are retained for diagnosis'
    FROM stg.SusepInsuranceMarketReject;
    INSERT @rules
    SELECT N'STG_TECHNICAL_IDENTITY_DUPLICATE',N'STAGING',N'HARD',COUNT_BIG(*),0,N'SourceFile + SourceFileSha256 + SourceRowNumber must be unique'
    FROM (SELECT SourceFile,SourceFileSha256,SourceRowNumber FROM stg.SusepInsuranceMarket GROUP BY SourceFile,SourceFileSha256,SourceRowNumber HAVING COUNT_BIG(*)>1) d;
    INSERT @rules
    SELECT N'STG_REQUIRED_FIELD_NULL',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Company, month, product, state and premium/claims fields are required'
    FROM stg.SusepInsuranceMarket WHERE CompanyCode IS NULL OR CompanyName IS NULL OR YearMonth IS NULL OR Product IS NULL OR State IS NULL OR PremiumsRaw IS NULL OR Premiums IS NULL OR ClaimsRaw IS NULL OR Claims IS NULL;
    INSERT @rules
    SELECT N'STG_VALID_MONTH_START',N'STAGING',N'HARD',COUNT_BIG(*),0,N'year_month must be the first day of a valid month'
    FROM stg.SusepInsuranceMarket WHERE DAY(YearMonth)<>1;
    INSERT @rules
    SELECT N'STG_BUSINESS_GRAIN_DUPLICATE',N'STAGING',N'HARD',COUNT_BIG(*),0,N'company_code + year_month + product + state must be unique'
    FROM (SELECT CompanyCode,YearMonth,Product,State FROM stg.SusepInsuranceMarket GROUP BY CompanyCode,YearMonth,Product,State HAVING COUNT_BIG(*)>1) d;
    INSERT @rules
    SELECT N'STG_COMPANY_NAME_MAPPING',N'STAGING',N'HARD',COUNT_BIG(*),0,N'One company_code must map to one company_name'
    FROM (SELECT CompanyCode FROM stg.SusepInsuranceMarket GROUP BY CompanyCode HAVING COUNT(DISTINCT CompanyName)>1) d;

    INSERT @rules
    SELECT N'DWH_FACT_STAGING_RECONCILIATION',N'WAREHOUSE',N'HARD',ABS((SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarket)-(SELECT COUNT_BIG(*) FROM dwh.FactSusepInsuranceMarket)),0,N'One fact is required for every accepted stage row';
    INSERT @rules
    SELECT N'DWH_FACT_ORPHAN_FOREIGN_KEY',N'WAREHOUSE',N'HARD',COUNT_BIG(*),0,N'All Track-A fact dimension keys must resolve'
    FROM dwh.FactSusepInsuranceMarket f
    LEFT JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
    LEFT JOIN dwh.DimSusepCompany c ON c.SusepCompanyKey=f.SusepCompanyKey
    LEFT JOIN dwh.DimSusepProduct p ON p.SusepProductKey=f.SusepProductKey
    LEFT JOIN dwh.DimSusepState g ON g.SusepStateKey=f.SusepStateKey
    WHERE m.SusepMonthKey IS NULL OR c.SusepCompanyKey IS NULL OR p.SusepProductKey IS NULL OR g.SusepStateKey IS NULL;
    INSERT @rules
    SELECT N'DWH_FACT_GRAIN_DUPLICATE',N'WAREHOUSE',N'HARD',COUNT_BIG(*),0,N'Fact source technical identity must be unique'
    FROM (SELECT SourceFile,SourceFileSha256,SourceRowNumber FROM dwh.FactSusepInsuranceMarket GROUP BY SourceFile,SourceFileSha256,SourceRowNumber HAVING COUNT_BIG(*)>1) d;
    INSERT @rules
    SELECT N'DWH_FACT_STAGE_LINEAGE',N'WAREHOUSE',N'HARD',COUNT_BIG(*),0,N'Fact copied lineage and analytic measures must equal its staging row'
    FROM dwh.FactSusepInsuranceMarket f JOIN stg.SusepInsuranceMarket s ON s.SusepStageRowId=f.SusepStageRowId
    WHERE f.BatchId<>s.BatchId OR f.SourceFile<>s.SourceFile OR f.SourceFileSha256<>s.SourceFileSha256 OR f.SourceRowNumber<>s.SourceRowNumber OR f.SourceRecordHash<>s.SourceRecordHash OR f.Premiums<>s.Premiums OR f.Claims<>s.Claims OR (f.ClaimPremiumRatio<>s.ClaimPremiumRatio) OR (f.ClaimPremiumRatio IS NULL AND s.ClaimPremiumRatio IS NOT NULL) OR (f.ClaimPremiumRatio IS NOT NULL AND s.ClaimPremiumRatio IS NULL);
    INSERT @rules
    SELECT N'DWH_DIMENSION_NATURAL_KEY_UNIQUENESS',N'WAREHOUSE',N'HARD',
        (SELECT COUNT_BIG(*)-COUNT(DISTINCT YearMonth) FROM dwh.DimSusepMonth)+
        (SELECT COUNT_BIG(*)-COUNT(DISTINCT CompanyCode) FROM dwh.DimSusepCompany)+
        (SELECT COUNT_BIG(*)-COUNT(DISTINCT Product) FROM dwh.DimSusepProduct)+
        (SELECT COUNT_BIG(*)-COUNT(DISTINCT State) FROM dwh.DimSusepState),0,N'Each Track-A dimension natural key must be unique';
    INSERT @rules
    SELECT N'RECONCILIATION_LATEST_FULL_RUN',N'RECONCILIATION',N'HARD',
        CASE WHEN EXISTS(
            SELECT 1 FROM meta.SusepIngestionBatch b WHERE b.Status=N'SUCCESS' AND NOT EXISTS(
                SELECT 1 FROM meta.SusepReconciliationRun r WHERE r.BatchId=b.BatchId AND r.Status=N'SUCCESS'
            )
        ) THEN 1 ELSE 0 END,0,N'Every successful source version must have a successful direct source-to-staging-to-fact reconciliation run';

    INSERT @rules SELECT N'STG_NEGATIVE_PREMIUMS_SOURCE_CHARACTERISTIC',N'STAGING',N'WARNING',COUNT_BIG(*),NULL,N'Negative premiums are retained for source fidelity and must be reviewed, not silently rejected' FROM stg.SusepInsuranceMarket WHERE Premiums<0;
    INSERT @rules SELECT N'STG_NEGATIVE_CLAIMS_SOURCE_CHARACTERISTIC',N'STAGING',N'WARNING',COUNT_BIG(*),NULL,N'Negative claims are retained for source fidelity and must be reviewed, not silently rejected' FROM stg.SusepInsuranceMarket WHERE Claims<0;
    INSERT @rules SELECT N'STG_SOURCE_RATIO_NULL_OR_NA_CHARACTERISTIC',N'STAGING',N'WARNING',COUNT_BIG(*),NULL,N'NULL means source sentinel NA; SourceClaimPremiumRatio remains non-additive' FROM stg.SusepInsuranceMarket WHERE ClaimPremiumRatio IS NULL;
    INSERT @rules SELECT N'STG_NEGATIVE_SOURCE_RATIO_CHARACTERISTIC',N'STAGING',N'WARNING',COUNT_BIG(*),NULL,N'Source-provided ratio has negative values; it is not treated as a recomputable business rule' FROM stg.SusepInsuranceMarket WHERE ClaimPremiumRatio<0;

    IF @InjectControlledFailure=1
        INSERT @rules VALUES(N'CONTROLLED_INVALID_INPUT',N'GATE_TEST',N'HARD',1,0,N'Only a procedure-memory test row; no raw/staging/fact data is changed');

    INSERT dq.SusepQualityCheckLog(DqRunId,RunLabel,RuleName,RuleDomain,Severity,Status,ObservedValue,ExpectedValue,Detail)
    SELECT @run_id, @RunLabel, RuleName, RuleDomain, Severity,
        CASE WHEN Severity=N'WARNING' THEN N'WARNING' WHEN ObservedValue=ExpectedValue THEN N'PASS' ELSE N'FAIL' END,
        ObservedValue,ExpectedValue,Detail
    FROM @rules;

    DECLARE @failed BIGINT=(SELECT COUNT_BIG(*) FROM @rules WHERE Severity=N'HARD' AND ObservedValue<>ExpectedValue);
    INSERT meta.SusepPipelineAudit(StageName,Status,RowsAffected,Detail)
    VALUES(N'DQ_QUALITY_GATE',CASE WHEN @failed=0 THEN N'SUCCESS' ELSE N'FAILED' END,@failed,CONCAT(N'RunId=',CONVERT(NVARCHAR(36),@run_id),N'; Label=',@RunLabel));
    SELECT RuleName,RuleDomain,Severity,
        CASE WHEN Severity=N'WARNING' THEN N'WARNING' WHEN ObservedValue=ExpectedValue THEN N'PASS' ELSE N'FAIL' END AS Status,
        ObservedValue,ExpectedValue,Detail
    FROM @rules ORDER BY RuleDomain,RuleName;
    IF @failed>0 THROW 51130,N'SUSEP quality gate failed; inspect dq.SusepQualityCheckLog.',1;
END;
GO

IF NOT EXISTS(SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion=N'V13')
INSERT INTO meta.SchemaVersion(MigrationVersion,Description)
VALUES(N'V13',N'Track A SUSEP reconciliation evidence and independent executable DQ gate');
GO
