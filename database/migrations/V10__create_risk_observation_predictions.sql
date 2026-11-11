-- V10: prediction storage at the proven aggregate risk-observation grain.
USE DWH_Insurance;
GO
IF OBJECT_ID(N'dwh.RiskObservationPrediction', N'U') IS NULL
BEGIN
    CREATE TABLE dwh.RiskObservationPrediction (
        RiskObservationPredictionKey BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
        SourceFile NVARCHAR(128) NOT NULL,
        SourceRowNumber INT NOT NULL,
        SourceRecordHash CHAR(64) NOT NULL,
        ScoringPopulation NVARCHAR(64) NOT NULL,
        ModelVersion NVARCHAR(160) NOT NULL,
        ScoreProbability DECIMAL(12,10) NOT NULL,
        ThresholdValue DECIMAL(5,4) NOT NULL,
        PredictedHasClaim BIT NOT NULL,
        ScoringRunId UNIQUEIDENTIFIER NOT NULL,
        ScoredAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_RiskObservationPrediction_ScoredAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT CK_RiskObservationPrediction_Probability CHECK (ScoreProbability >= 0 AND ScoreProbability <= 1),
        CONSTRAINT CK_RiskObservationPrediction_Threshold CHECK (ThresholdValue > 0 AND ThresholdValue < 1),
        CONSTRAINT UQ_RiskObservationPrediction_Idempotency UNIQUE (SourceFile, SourceRowNumber, ScoringPopulation, ModelVersion)
    );
END;
GO
IF NOT EXISTS (SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion = N'V10')
    INSERT meta.SchemaVersion(MigrationVersion, Description) VALUES (N'V10', N'Risk observation batch prediction storage');
GO
