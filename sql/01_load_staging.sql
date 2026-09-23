-- P1-INGEST canonical staging entry point.
--
-- Deployment prerequisites: V1 through V4.
--
-- The runtime loader is scripts/load_brvehins1_to_staging.py. It streams CSV
-- with Python's RFC-aware parser so quoted commas are parsed correctly and
-- SourceRowNumber remains the original 1-based file ordinal. Run it with an
-- SQLSERVER_SA_PASSWORD environment variable before using this SQL verification
-- entry point.
--
-- Example:
-- python scripts/load_brvehins1_to_staging.py --source-file brvehins1a.csv
--
-- Override the SQLCMD SourceFile variable only with one of the five frozen
-- canonical names when checking batch status below.

:setvar SourceFile "brvehins1a.csv"

USE [DWH_Insurance];
GO

-- Required when writing tables referenced by the filtered idempotency index.
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;
GO

IF OBJECT_ID(N'stg.BrVehIns1', N'U') IS NULL
    THROW 51020, N'Missing stg.BrVehIns1. Run V2__create_staging_schema.sql first.', 1;

SELECT
    batch.BatchId,
    batch.SourceFile,
    batch.ExpectedSourceRows,
    batch.StagingRows,
    batch.RejectedRows,
    batch.Status,
    batch.ElapsedMilliseconds,
    batch.ErrorMessage
FROM meta.IngestionBatch AS batch
WHERE batch.SourceFile = N'$(SourceFile)'
ORDER BY batch.StartedAtUtc;
GO
