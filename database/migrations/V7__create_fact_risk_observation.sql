-- V7: one fact per canonical staging source row; no policy/customer semantics.
USE DWH_Insurance;
GO
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO
IF OBJECT_ID(N'dwh.FactRiskObservation', N'U') IS NULL
CREATE TABLE dwh.FactRiskObservation (
 FactRiskObservationKey BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY, StageRowId BIGINT NOT NULL UNIQUE,
 BatchId UNIQUEIDENTIFIER NOT NULL, SourceFile NVARCHAR(128) NOT NULL, SourceRowNumber INT NOT NULL, SourceRecordHash CHAR(64) NOT NULL, LoadTimestampUtc DATETIME2(3) NOT NULL,
 DriverProfileKey INT NOT NULL, VehicleKey INT NOT NULL, GeographyKey INT NOT NULL,
 ExposTotal DECIMAL(21,17) NOT NULL, ExposFireRob DECIMAL(19,6) NOT NULL, PremTotal DECIMAL(34,27) NOT NULL, PremFireRob DECIMAL(19,6) NOT NULL, SumInsAvg DECIMAL(19,6) NOT NULL,
 ClaimNbRob INT NOT NULL, ClaimNbPartColl INT NOT NULL, ClaimNbTotColl INT NOT NULL, ClaimNbFire INT NOT NULL, ClaimNbOther INT NOT NULL,
 ClaimAmountRob DECIMAL(19,6) NOT NULL, ClaimAmountPartColl DECIMAL(19,6) NOT NULL, ClaimAmountTotColl DECIMAL(19,6) NOT NULL, ClaimAmountFire DECIMAL(19,6) NOT NULL, ClaimAmountOther DECIMAL(19,6) NOT NULL,
 TotalClaimCount AS (ClaimNbRob+ClaimNbPartColl+ClaimNbTotColl+ClaimNbFire+ClaimNbOther) PERSISTED,
 TotalClaimAmount AS (ClaimAmountRob+ClaimAmountPartColl+ClaimAmountTotColl+ClaimAmountFire+ClaimAmountOther) PERSISTED,
 HasClaim AS (CONVERT(bit, CASE WHEN ClaimNbRob+ClaimNbPartColl+ClaimNbTotColl+ClaimNbFire+ClaimNbOther > 0 THEN 1 ELSE 0 END)) PERSISTED,
 ClaimFrequency AS (CASE WHEN ExposTotal > 0 THEN CONVERT(DECIMAL(38,17),(ClaimNbRob+ClaimNbPartColl+ClaimNbTotColl+ClaimNbFire+ClaimNbOther))/ExposTotal END) PERSISTED,
 LossRatio AS (CASE WHEN PremTotal > 0 THEN CONVERT(DECIMAL(38,6),(ClaimAmountRob+ClaimAmountPartColl+ClaimAmountTotColl+ClaimAmountFire+ClaimAmountOther))/PremTotal END) PERSISTED,
 CONSTRAINT UQ_FactRiskObservation_Source UNIQUE(SourceFile,SourceRowNumber),
 CONSTRAINT FK_FactRiskObservation_Stage FOREIGN KEY(StageRowId) REFERENCES stg.BrVehIns1(StageRowId),
 CONSTRAINT FK_FactRiskObservation_Driver FOREIGN KEY(DriverProfileKey) REFERENCES dwh.DimDriverProfile(DriverProfileKey),
 CONSTRAINT FK_FactRiskObservation_Vehicle FOREIGN KEY(VehicleKey) REFERENCES dwh.DimVehicle(VehicleKey),
 CONSTRAINT FK_FactRiskObservation_Geography FOREIGN KEY(GeographyKey) REFERENCES dwh.DimGeography(GeographyKey)
);
GO
CREATE OR ALTER PROCEDURE dwh.sp_LoadFactRiskObservation AS
BEGIN SET NOCOUNT ON; SET XACT_ABORT ON; BEGIN TRANSACTION; BEGIN TRY
 INSERT dwh.FactRiskObservation (StageRowId,BatchId,SourceFile,SourceRowNumber,SourceRecordHash,LoadTimestampUtc,DriverProfileKey,VehicleKey,GeographyKey,ExposTotal,ExposFireRob,PremTotal,PremFireRob,SumInsAvg,ClaimNbRob,ClaimNbPartColl,ClaimNbTotColl,ClaimNbFire,ClaimNbOther,ClaimAmountRob,ClaimAmountPartColl,ClaimAmountTotColl,ClaimAmountFire,ClaimAmountOther)
 SELECT s.StageRowId,s.BatchId,s.SourceFile,s.SourceRowNumber,s.SourceRecordHash,s.LoadTimestampUtc,d.DriverProfileKey,v.VehicleKey,g.GeographyKey,s.ExposTotal,s.ExposFireRob,s.PremTotal,s.PremFireRob,s.SumInsAvg,s.ClaimNbRob,s.ClaimNbPartColl,s.ClaimNbTotColl,s.ClaimNbFire,s.ClaimNbOther,s.ClaimAmountRob,s.ClaimAmountPartColl,s.ClaimAmountTotColl,s.ClaimAmountFire,s.ClaimAmountOther
 FROM stg.BrVehIns1 s JOIN dwh.DimDriverProfile d ON d.IsUnknown=0 AND ((d.Gender=s.Gender) OR (d.Gender IS NULL AND s.Gender IS NULL)) AND ((d.DrivAge=s.DrivAge) OR (d.DrivAge IS NULL AND s.DrivAge IS NULL))
 JOIN dwh.DimVehicle v ON v.IsUnknown=0 AND ((v.VehYear=s.VehYear) OR (v.VehYear IS NULL AND s.VehYear IS NULL)) AND ((v.VehModel=s.VehModel) OR (v.VehModel IS NULL AND s.VehModel IS NULL)) AND ((v.VehGroup=s.VehGroup) OR (v.VehGroup IS NULL AND s.VehGroup IS NULL))
 JOIN dwh.DimGeography g ON g.IsUnknown=0 AND ((g.Area=s.Area) OR (g.Area IS NULL AND s.Area IS NULL)) AND ((g.State=s.State) OR (g.State IS NULL AND s.State IS NULL)) AND ((g.StateAb=s.StateAb) OR (g.StateAb IS NULL AND s.StateAb IS NULL))
 WHERE NOT EXISTS(SELECT 1 FROM dwh.FactRiskObservation f WHERE f.StageRowId=s.StageRowId);
 DECLARE @r BIGINT=@@ROWCOUNT; INSERT meta.PipelineAudit(StageName,Status,RowsAffected,Detail) VALUES(N'P1-DWH-03 Load FactRiskObservation',N'SUCCESS',@r,N'One row per staging source row'); COMMIT; END TRY BEGIN CATCH IF @@TRANCOUNT>0 ROLLBACK; INSERT meta.PipelineAudit(StageName,Status,Detail) VALUES(N'P1-DWH-03 Load FactRiskObservation',N'FAILED',ERROR_MESSAGE()); THROW; END CATCH END;
GO
IF NOT EXISTS(SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion=N'V7') INSERT meta.SchemaVersion(MigrationVersion,Description) VALUES(N'V7',N'Canonical risk observation fact');
GO
