-- V14: evidence-based retained indexes for the two measured SUSEP market workloads.
-- The indexes do not create a relationship to Track B and do not change fact grain.

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

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id=OBJECT_ID(N'dwh.FactSusepInsuranceMarket')
      AND name=N'IX_FactSusepInsuranceMarket_CompanyMonth_Perf'
)
CREATE NONCLUSTERED INDEX IX_FactSusepInsuranceMarket_CompanyMonth_Perf
ON dwh.FactSusepInsuranceMarket(SusepCompanyKey,SusepMonthKey)
INCLUDE(Premiums,Claims);
GO

IF NOT EXISTS (
    SELECT 1 FROM sys.indexes
    WHERE object_id=OBJECT_ID(N'dwh.FactSusepInsuranceMarket')
      AND name=N'IX_FactSusepInsuranceMarket_StateProductMonth_Perf'
)
CREATE NONCLUSTERED INDEX IX_FactSusepInsuranceMarket_StateProductMonth_Perf
ON dwh.FactSusepInsuranceMarket(SusepStateKey,SusepProductKey,SusepMonthKey)
INCLUDE(Premiums,Claims);
GO

IF NOT EXISTS(SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion=N'V14')
INSERT INTO meta.SchemaVersion(MigrationVersion,Description)
VALUES(N'V14',N'Evidence-based Track A SUSEP performance indexes for company/month and state/product/month workloads');
GO
