-- V4: Remove the empty SQL Server Linux CSV landing experiment.
-- Exact source row ordinals are assigned by the streaming client loader instead.

USE [DWH_Insurance];
GO

IF OBJECT_ID(N'stg.BrVehIns1Landing', N'U') IS NOT NULL
BEGIN
    IF EXISTS (SELECT 1 FROM stg.BrVehIns1Landing)
        THROW 51040, N'Cannot remove non-empty obsolete landing table.', 1;

    DROP TABLE stg.BrVehIns1Landing;
END;
GO

IF OBJECT_ID(N'stg.usp_LoadBrVehIns1Partition', N'P') IS NOT NULL
    DROP PROCEDURE stg.usp_LoadBrVehIns1Partition;
GO

UPDATE meta.SchemaVersion
SET Description = N'Client-side streaming canonical brvehins1 loader'
WHERE MigrationVersion = N'V3';
GO

IF NOT EXISTS (
    SELECT 1
    FROM meta.SchemaVersion
    WHERE MigrationVersion = N'V4'
)
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V4', N'Remove unsupported Linux server-side CSV landing experiment');
END;
GO
