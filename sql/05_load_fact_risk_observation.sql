USE DWH_Insurance;
GO
EXEC dwh.sp_LoadFactRiskObservation;
GO
SELECT COUNT_BIG(*) AS FactRows FROM dwh.FactRiskObservation;
GO
