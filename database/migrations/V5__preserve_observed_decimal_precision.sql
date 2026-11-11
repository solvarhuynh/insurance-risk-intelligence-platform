-- V5: Preserve lexical decimal precision observed in canonical brvehins1 raw CSV.
-- The profile found ExposTotal up to scale 17 and PremTotal up to scale 27.

USE [DWH_Insurance];
GO

IF EXISTS (
    SELECT 1
    FROM sys.columns
    WHERE object_id = OBJECT_ID(N'stg.BrVehIns1')
      AND name = N'ExposTotal'
      AND (precision <> 21 OR scale <> 17)
)
BEGIN
    IF EXISTS (SELECT 1 FROM stg.BrVehIns1)
        THROW 51050, N'Apply V5 before loading staging rows to avoid precision loss.', 1;

    ALTER TABLE stg.BrVehIns1
        ALTER COLUMN ExposTotal DECIMAL(21, 17) NOT NULL;
END;
GO

IF EXISTS (
    SELECT 1
    FROM sys.columns
    WHERE object_id = OBJECT_ID(N'stg.BrVehIns1')
      AND name = N'PremTotal'
      AND (precision <> 34 OR scale <> 27)
)
BEGIN
    IF EXISTS (SELECT 1 FROM stg.BrVehIns1)
        THROW 51051, N'Apply V5 before loading staging rows to avoid precision loss.', 1;

    ALTER TABLE stg.BrVehIns1
        ALTER COLUMN PremTotal DECIMAL(34, 27) NOT NULL;
END;
GO

IF NOT EXISTS (
    SELECT 1
    FROM meta.SchemaVersion
    WHERE MigrationVersion = N'V5'
)
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V5', N'Preserve observed ExposTotal and PremTotal decimal precision');
END;
GO
