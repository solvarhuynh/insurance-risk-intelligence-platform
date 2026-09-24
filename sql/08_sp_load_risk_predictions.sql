-- P1-ML-05 entry point.  The maintained loader is ml/predict_risk_batch.py.
-- It loads a joblib artifact and MERGEs the bounded held-out test population directly
-- into dwh.RiskObservationPrediction.  No customer/policy table is involved.
USE DWH_Insurance;
GO
SELECT
    N'Use: python ml/predict_risk_batch.py [--run-id <UUID>]' AS EntryPoint,
    N'Idempotency: SourceFile + SourceRowNumber + ScoringPopulation + ModelVersion' AS Policy,
    N'Population: bounded_held_out_test only; this is an out-of-sample batch demonstration.' AS Scope;
GO
