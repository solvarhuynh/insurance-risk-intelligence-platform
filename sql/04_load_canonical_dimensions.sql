-- P1-DWH-02 canonical dimension entry point.
-- Prerequisite: migrations/V6__create_canonical_dimensions.sql has succeeded.
-- The loader uses only brvehins1 staging descriptors and is idempotent.

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

IF OBJECT_ID(N'dwh.sp_LoadCanonicalDimensions', N'P') IS NULL
    THROW 51030, N'Missing canonical dimension loader. Run V6 first.', 1;
GO

EXEC dwh.sp_LoadCanonicalDimensions;
GO

SELECT
    N'DimDriverProfile' AS DimensionName,
    COUNT_BIG(*) AS DimensionRowCount,
    SUM(CASE WHEN IsUnknown = 1 THEN 1 ELSE 0 END) AS UnknownRows
FROM dwh.DimDriverProfile
UNION ALL
SELECT N'DimVehicle', COUNT_BIG(*), SUM(CASE WHEN IsUnknown = 1 THEN 1 ELSE 0 END)
FROM dwh.DimVehicle
UNION ALL
SELECT N'DimGeography', COUNT_BIG(*), SUM(CASE WHEN IsUnknown = 1 THEN 1 ELSE 0 END)
FROM dwh.DimGeography;
GO
