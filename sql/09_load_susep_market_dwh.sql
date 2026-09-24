-- Track A SUSEP DWH load entry point. Apply V11-V12 before running.
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
EXEC dwh.sp_LoadSusepDimensions;
EXEC dwh.sp_LoadFactSusepInsuranceMarket;
GO
SELECT
    (SELECT COUNT_BIG(*) FROM stg.SusepInsuranceMarket) AS SusepStagingRows,
    (SELECT COUNT_BIG(*) FROM dwh.FactSusepInsuranceMarket) AS SusepFactRows,
    (SELECT COUNT_BIG(*) FROM dwh.DimSusepMonth) AS SusepMonthRows,
    (SELECT COUNT_BIG(*) FROM dwh.DimSusepCompany) AS SusepCompanyRows,
    (SELECT COUNT_BIG(*) FROM dwh.DimSusepProduct) AS SusepProductRows,
    (SELECT COUNT_BIG(*) FROM dwh.DimSusepState) AS SusepStateRows;
GO
