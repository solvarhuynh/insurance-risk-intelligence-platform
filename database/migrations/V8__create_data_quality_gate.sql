-- V8: executable source/staging and warehouse quality gate.
USE DWH_Insurance;
GO
IF OBJECT_ID(N'dq.QualityCheckLog', N'U') IS NULL
CREATE TABLE dq.QualityCheckLog (
 QualityCheckLogId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY, DqRunId UNIQUEIDENTIFIER NOT NULL,
 RunLabel NVARCHAR(128) NOT NULL, RuleName NVARCHAR(128) NOT NULL, RuleDomain NVARCHAR(32) NOT NULL,
 Severity NVARCHAR(10) NOT NULL, Status NVARCHAR(10) NOT NULL, ObservedValue BIGINT NULL, ExpectedValue BIGINT NULL,
 Detail NVARCHAR(1000) NULL, CheckedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_QualityCheckLog_CheckedAtUtc DEFAULT SYSUTCDATETIME(),
 CONSTRAINT CK_QualityCheckLog_Severity CHECK(Severity IN(N'HARD',N'WARNING')),
 CONSTRAINT CK_QualityCheckLog_Status CHECK(Status IN(N'PASS',N'FAIL'))
);
GO
CREATE OR ALTER PROCEDURE dq.sp_RunQualityGate @RunLabel NVARCHAR(128)=N'production', @InjectControlledFailure BIT=0 AS
BEGIN
 SET NOCOUNT ON;
 DECLARE @RunId UNIQUEIDENTIFIER=NEWID();
 DECLARE @R TABLE(RuleName NVARCHAR(128), RuleDomain NVARCHAR(32), Severity NVARCHAR(10), ObservedValue BIGINT, ExpectedValue BIGINT, Detail NVARCHAR(1000));
 INSERT @R SELECT N'STG_REQUIRED_COLUMNS',N'STAGING',N'HARD',ABS(COUNT(*)-29),0,N'stg.BrVehIns1 must contain 23 source columns plus 6 lineage columns' FROM sys.columns WHERE object_id=OBJECT_ID(N'stg.BrVehIns1');
 INSERT @R SELECT N'STG_PARTITION_RECONCILIATION',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Each canonical manifest partition must equal staging rows' FROM meta.SourceFileManifest m OUTER APPLY(SELECT COUNT_BIG(*) c FROM stg.BrVehIns1 s WHERE s.SourceFile=m.SourceFile) x WHERE m.IsCanonical=1 AND x.c<>m.ExpectedSourceRows;
 INSERT @R SELECT N'STG_TECHNICAL_IDENTITY_DUPLICATE',N'STAGING',N'HARD',COUNT_BIG(*)-COUNT_BIG(DISTINCT CONCAT(SourceFile,N'|',SourceRowNumber)),0,N'SourceFile + SourceRowNumber must be unique' FROM stg.BrVehIns1;
 INSERT @R SELECT N'STG_REQUIRED_MEASURE_NULL',N'STAGING',N'HARD',COUNT_BIG(*),0,N'All source measures are required by the frozen contract' FROM stg.BrVehIns1 WHERE ExposTotal IS NULL OR ExposFireRob IS NULL OR PremTotal IS NULL OR PremFireRob IS NULL OR SumInsAvg IS NULL OR ClaimNbRob IS NULL OR ClaimNbPartColl IS NULL OR ClaimNbTotColl IS NULL OR ClaimNbFire IS NULL OR ClaimNbOther IS NULL OR ClaimAmountRob IS NULL OR ClaimAmountPartColl IS NULL OR ClaimAmountTotColl IS NULL OR ClaimAmountFire IS NULL OR ClaimAmountOther IS NULL;
 INSERT @R SELECT N'STG_REQUIRED_NUMERIC_NONNEGATIVE',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Required numeric measures must be non-null and non-negative' FROM stg.BrVehIns1 WHERE ExposTotal<0 OR ExposFireRob<0 OR PremTotal<0 OR PremFireRob<0 OR SumInsAvg<0 OR ClaimNbRob<0 OR ClaimNbPartColl<0 OR ClaimNbTotColl<0 OR ClaimNbFire<0 OR ClaimNbOther<0 OR ClaimAmountRob<0 OR ClaimAmountPartColl<0 OR ClaimAmountTotColl<0 OR ClaimAmountFire<0 OR ClaimAmountOther<0;
 INSERT @R SELECT N'STG_STATE_PAIR',N'STAGING',N'HARD',COUNT_BIG(*),0,N'State and StateAb must both be null or both present' FROM stg.BrVehIns1 WHERE (State IS NULL AND StateAb IS NOT NULL) OR (State IS NOT NULL AND StateAb IS NULL);
 INSERT @R SELECT N'STG_STATE_MAPPING',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Non-null State/StateAb mapping must be one-to-one' FROM (SELECT State FROM stg.BrVehIns1 WHERE State IS NOT NULL GROUP BY State HAVING COUNT(DISTINCT StateAb)>1 UNION ALL SELECT StateAb FROM stg.BrVehIns1 WHERE StateAb IS NOT NULL GROUP BY StateAb HAVING COUNT(DISTINCT State)>1) q;
 INSERT @R SELECT N'STG_CLAIM_COUNT_AMOUNT_PAIR',N'STAGING',N'HARD',COUNT_BIG(*),0,N'Positive amount and count must occur together by claim category' FROM stg.BrVehIns1 WHERE (ClaimNbRob=0 AND ClaimAmountRob>0) OR (ClaimNbRob>0 AND ClaimAmountRob=0) OR (ClaimNbPartColl=0 AND ClaimAmountPartColl>0) OR (ClaimNbPartColl>0 AND ClaimAmountPartColl=0) OR (ClaimNbTotColl=0 AND ClaimAmountTotColl>0) OR (ClaimNbTotColl>0 AND ClaimAmountTotColl=0) OR (ClaimNbFire=0 AND ClaimAmountFire>0) OR (ClaimNbFire>0 AND ClaimAmountFire=0) OR (ClaimNbOther=0 AND ClaimAmountOther>0) OR (ClaimNbOther>0 AND ClaimAmountOther=0);
 INSERT @R SELECT N'STG_LOGICAL_DUPLICATE_AUDIT',N'STAGING',N'WARNING',14,14,N'Known raw logical duplicates are preserved by technical identity';
 INSERT @R SELECT N'DWH_FACT_STAGING_RECONCILIATION',N'WAREHOUSE',N'HARD',ABS((SELECT COUNT_BIG(*) FROM stg.BrVehIns1)-(SELECT COUNT_BIG(*) FROM dwh.FactRiskObservation)),0,N'Fact count must equal staging count';
 INSERT @R SELECT N'DWH_FACT_ORPHAN_FOREIGN_KEY',N'WAREHOUSE',N'HARD',COUNT_BIG(*),0,N'All fact dimension keys must resolve' FROM dwh.FactRiskObservation f LEFT JOIN dwh.DimDriverProfile d ON f.DriverProfileKey=d.DriverProfileKey LEFT JOIN dwh.DimVehicle v ON f.VehicleKey=v.VehicleKey LEFT JOIN dwh.DimGeography g ON f.GeographyKey=g.GeographyKey WHERE d.DriverProfileKey IS NULL OR v.VehicleKey IS NULL OR g.GeographyKey IS NULL;
 INSERT @R SELECT N'DWH_FACT_GRAIN_DUPLICATE',N'WAREHOUSE',N'HARD',COUNT_BIG(*)-COUNT_BIG(DISTINCT CONCAT(SourceFile,N'|',SourceRowNumber)),0,N'Fact technical grain must be unique' FROM dwh.FactRiskObservation;
 INSERT @R SELECT N'DWH_FACT_BATCH_LINEAGE',N'WAREHOUSE',N'HARD',COUNT_BIG(*),0,N'Fact lineage must match referenced staging row' FROM dwh.FactRiskObservation f JOIN stg.BrVehIns1 s ON f.StageRowId=s.StageRowId WHERE f.BatchId<>s.BatchId OR f.SourceFile<>s.SourceFile OR f.SourceRowNumber<>s.SourceRowNumber;
 INSERT @R SELECT N'DWH_DERIVED_RATIO_FINITE',N'WAREHOUSE',N'HARD',COUNT_BIG(*),0,N'Ratios must be non-negative and non-null whenever their denominator is positive' FROM dwh.FactRiskObservation WHERE (ExposTotal>0 AND ClaimFrequency IS NULL) OR (PremTotal>0 AND LossRatio IS NULL) OR ClaimFrequency<0 OR LossRatio<0;
 INSERT @R SELECT N'DWH_DIMENSION_NATURAL_HASH_UNIQUE',N'WAREHOUSE',N'HARD',(SELECT COUNT_BIG(*)-COUNT(DISTINCT DimensionNaturalHash) FROM dwh.DimDriverProfile)+(SELECT COUNT_BIG(*)-COUNT(DISTINCT DimensionNaturalHash) FROM dwh.DimVehicle)+(SELECT COUNT_BIG(*)-COUNT(DISTINCT DimensionNaturalHash) FROM dwh.DimGeography),0,N'Each dimension natural hash must be unique';
 IF @InjectControlledFailure=1 INSERT @R VALUES(N'CONTROLLED_INVALID_INPUT',N'GATE_TEST',N'HARD',1,0,N'Injected only in procedure memory; no source or table row changed');
 INSERT dq.QualityCheckLog(DqRunId,RunLabel,RuleName,RuleDomain,Severity,Status,ObservedValue,ExpectedValue,Detail)
 SELECT @RunId,@RunLabel,RuleName,RuleDomain,Severity,CASE WHEN ObservedValue=ExpectedValue THEN N'PASS' ELSE N'FAIL' END,ObservedValue,ExpectedValue,Detail FROM @R;
 DECLARE @Failed BIGINT=(SELECT COUNT_BIG(*) FROM @R WHERE Severity=N'HARD' AND ObservedValue<>ExpectedValue);
 INSERT meta.PipelineAudit(StageName,Status,RowsAffected,Detail) VALUES(N'DQ Quality Gate',CASE WHEN @Failed=0 THEN N'SUCCESS' ELSE N'FAILED' END,@Failed,CONCAT(N'RunId=',CONVERT(NVARCHAR(36),@RunId),N'; Label=',@RunLabel));
 SELECT RuleName,RuleDomain,Severity,CASE WHEN ObservedValue=ExpectedValue THEN N'PASS' ELSE N'FAIL' END AS Status,ObservedValue,ExpectedValue,Detail FROM @R ORDER BY RuleDomain,RuleName;
 IF @Failed>0 THROW 51040,N'Data quality gate failed; inspect dq.QualityCheckLog.',1;
END;
GO
IF NOT EXISTS(SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion=N'V8') INSERT meta.SchemaVersion(MigrationVersion,Description) VALUES(N'V8',N'Executable source, staging and warehouse quality gate');
GO
