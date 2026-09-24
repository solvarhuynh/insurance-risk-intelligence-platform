-- Track A only. This never invokes or changes Track-B dq.sp_RunQualityGate.
USE [DWH_Insurance];
GO
EXEC dq.sp_RunSusepQualityGate @RunLabel=N'manual-production', @InjectControlledFailure=0;
GO
