-- V3: Register the canonical client-side staging loader approach.
--
-- SQL Server on this Linux runtime cannot safely use FORMAT=CSV together with
-- an internal identity column while retaining source-line ordinals. The actual
-- loader is scripts/load_brvehins1_to_staging.py, which streams RFC-aware CSV
-- rows and assigns SourceRowNumber before parameterized insertion.

USE [DWH_Insurance];
GO

IF NOT EXISTS (
    SELECT 1
    FROM meta.SchemaVersion
    WHERE MigrationVersion = N'V3'
)
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V3', N'Client-side streaming canonical brvehins1 loader');
END;
GO
