USE DWH_Insurance;
GO
EXEC dq.sp_RunQualityGate @RunLabel=N'production';
GO
