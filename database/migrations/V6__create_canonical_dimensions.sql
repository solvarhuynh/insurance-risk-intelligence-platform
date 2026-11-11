-- V6: Dimensions justified by the canonical brvehins1 contract.
-- No customer, policy, date or SCD2 entity is created: source evidence does
-- not support those semantics.

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

IF OBJECT_ID(N'dwh.DimDriverProfile', N'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimDriverProfile (
        DriverProfileKey INT IDENTITY(1, 1) NOT NULL
            CONSTRAINT PK_DimDriverProfile PRIMARY KEY,
        DimensionNaturalHash CHAR(64) NOT NULL,
        Gender NVARCHAR(20) NULL,
        DrivAge NVARCHAR(20) NULL,
        IsUnknown BIT NOT NULL CONSTRAINT DF_DimDriverProfile_IsUnknown DEFAULT 0,
        CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimDriverProfile_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_DimDriverProfile_NaturalHash UNIQUE (DimensionNaturalHash),
        CONSTRAINT CK_DimDriverProfile_UnknownHash
            CHECK ((IsUnknown = 0) OR (DimensionNaturalHash = REPLICATE('0', 64)))
    );
END;
GO

IF OBJECT_ID(N'dwh.DimVehicle', N'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimVehicle (
        VehicleKey INT IDENTITY(1, 1) NOT NULL
            CONSTRAINT PK_DimVehicle PRIMARY KEY,
        DimensionNaturalHash CHAR(64) NOT NULL,
        VehYear SMALLINT NULL,
        VehModel NVARCHAR(255) NULL,
        VehGroup NVARCHAR(255) NULL,
        IsUnknown BIT NOT NULL CONSTRAINT DF_DimVehicle_IsUnknown DEFAULT 0,
        CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimVehicle_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_DimVehicle_NaturalHash UNIQUE (DimensionNaturalHash),
        CONSTRAINT CK_DimVehicle_UnknownHash
            CHECK ((IsUnknown = 0) OR (DimensionNaturalHash = REPLICATE('0', 64)))
    );
END;
GO

IF OBJECT_ID(N'dwh.DimGeography', N'U') IS NULL
BEGIN
    CREATE TABLE dwh.DimGeography (
        GeographyKey INT IDENTITY(1, 1) NOT NULL
            CONSTRAINT PK_DimGeography PRIMARY KEY,
        DimensionNaturalHash CHAR(64) NOT NULL,
        Area NVARCHAR(100) NULL,
        State NVARCHAR(100) NULL,
        StateAb CHAR(2) NULL,
        IsUnknown BIT NOT NULL CONSTRAINT DF_DimGeography_IsUnknown DEFAULT 0,
        CreatedAtUtc DATETIME2(3) NOT NULL CONSTRAINT DF_DimGeography_CreatedAtUtc DEFAULT SYSUTCDATETIME(),
        CONSTRAINT UQ_DimGeography_NaturalHash UNIQUE (DimensionNaturalHash),
        CONSTRAINT CK_DimGeography_UnknownHash
            CHECK ((IsUnknown = 0) OR (DimensionNaturalHash = REPLICATE('0', 64)))
    );
END;
GO

-- Key 0 is reserved solely for an unresolved lookup. Source rows containing
-- NULL attributes still use their own null-preserved tuple, not this member.
IF NOT EXISTS (SELECT 1 FROM dwh.DimDriverProfile WHERE DriverProfileKey = 0)
BEGIN
    SET IDENTITY_INSERT dwh.DimDriverProfile ON;
    INSERT INTO dwh.DimDriverProfile (DriverProfileKey, DimensionNaturalHash, Gender, DrivAge, IsUnknown)
    VALUES (0, REPLICATE('0', 64), N'Unknown / missing', N'Unknown / missing', 1);
    SET IDENTITY_INSERT dwh.DimDriverProfile OFF;
END;
GO

IF NOT EXISTS (SELECT 1 FROM dwh.DimVehicle WHERE VehicleKey = 0)
BEGIN
    SET IDENTITY_INSERT dwh.DimVehicle ON;
    INSERT INTO dwh.DimVehicle (VehicleKey, DimensionNaturalHash, VehYear, VehModel, VehGroup, IsUnknown)
    VALUES (0, REPLICATE('0', 64), NULL, N'Unknown / not supplied', N'Unknown / not supplied', 1);
    SET IDENTITY_INSERT dwh.DimVehicle OFF;
END;
GO

IF NOT EXISTS (SELECT 1 FROM dwh.DimGeography WHERE GeographyKey = 0)
BEGIN
    SET IDENTITY_INSERT dwh.DimGeography ON;
    INSERT INTO dwh.DimGeography (GeographyKey, DimensionNaturalHash, Area, State, StateAb, IsUnknown)
    VALUES (0, REPLICATE('0', 64), N'Unknown / not supplied', N'Unknown / not supplied', NULL, 1);
    SET IDENTITY_INSERT dwh.DimGeography OFF;
END;
GO

CREATE OR ALTER PROCEDURE dwh.sp_LoadCanonicalDimensions
AS
BEGIN
    SET NOCOUNT ON;
    SET XACT_ABORT ON;

    DECLARE @DriverRows BIGINT = 0;
    DECLARE @VehicleRows BIGINT = 0;
    DECLARE @GeographyRows BIGINT = 0;

    BEGIN TRANSACTION;
    BEGIN TRY
        ;WITH DriverSource AS (
            SELECT DISTINCT
                CONVERT(CHAR(64), HASHBYTES('SHA2_256',
                    CONCAT(N'Driver|',
                        CASE WHEN Gender IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(Gender), N':', Gender) END,
                        N'|',
                        CASE WHEN DrivAge IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(DrivAge), N':', DrivAge) END
                    )), 2) AS DimensionNaturalHash,
                Gender,
                DrivAge
            FROM stg.BrVehIns1
        )
        INSERT INTO dwh.DimDriverProfile (DimensionNaturalHash, Gender, DrivAge)
        SELECT source.DimensionNaturalHash, source.Gender, source.DrivAge
        FROM DriverSource AS source
        WHERE NOT EXISTS (
            SELECT 1 FROM dwh.DimDriverProfile AS target
            WHERE target.DimensionNaturalHash = source.DimensionNaturalHash
        );
        SET @DriverRows = @@ROWCOUNT;

        ;WITH VehicleSource AS (
            SELECT DISTINCT
                CONVERT(CHAR(64), HASHBYTES('SHA2_256',
                    CONCAT(N'Vehicle|',
                        CASE WHEN VehYear IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(CONVERT(VARCHAR(6), VehYear)), N':', CONVERT(VARCHAR(6), VehYear)) END,
                        N'|',
                        CASE WHEN VehModel IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(VehModel), N':', VehModel) END,
                        N'|',
                        CASE WHEN VehGroup IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(VehGroup), N':', VehGroup) END
                    )), 2) AS DimensionNaturalHash,
                VehYear,
                VehModel,
                VehGroup
            FROM stg.BrVehIns1
        )
        INSERT INTO dwh.DimVehicle (DimensionNaturalHash, VehYear, VehModel, VehGroup)
        SELECT source.DimensionNaturalHash, source.VehYear, source.VehModel, source.VehGroup
        FROM VehicleSource AS source
        WHERE NOT EXISTS (
            SELECT 1 FROM dwh.DimVehicle AS target
            WHERE target.DimensionNaturalHash = source.DimensionNaturalHash
        );
        SET @VehicleRows = @@ROWCOUNT;

        ;WITH GeographySource AS (
            SELECT DISTINCT
                CONVERT(CHAR(64), HASHBYTES('SHA2_256',
                    CONCAT(N'Geography|',
                        CASE WHEN Area IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(Area), N':', Area) END,
                        N'|',
                        CASE WHEN State IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(State), N':', State) END,
                        N'|',
                        CASE WHEN StateAb IS NULL THEN N'N;' ELSE CONCAT(N'V', DATALENGTH(StateAb), N':', StateAb) END
                    )), 2) AS DimensionNaturalHash,
                Area,
                State,
                StateAb
            FROM stg.BrVehIns1
        )
        INSERT INTO dwh.DimGeography (DimensionNaturalHash, Area, State, StateAb)
        SELECT source.DimensionNaturalHash, source.Area, source.State, source.StateAb
        FROM GeographySource AS source
        WHERE NOT EXISTS (
            SELECT 1 FROM dwh.DimGeography AS target
            WHERE target.DimensionNaturalHash = source.DimensionNaturalHash
        );
        SET @GeographyRows = @@ROWCOUNT;

        INSERT INTO meta.PipelineAudit (StageName, Status, RowsAffected, Detail)
        VALUES (
            N'P1-DWH-02 Load canonical dimensions',
            N'SUCCESS',
            @DriverRows + @VehicleRows + @GeographyRows,
            CONCAT(N'Driver=', @DriverRows, N'; Vehicle=', @VehicleRows, N'; Geography=', @GeographyRows)
        );

        COMMIT TRANSACTION;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        INSERT INTO meta.PipelineAudit (StageName, Status, Detail)
        VALUES (N'P1-DWH-02 Load canonical dimensions', N'FAILED', ERROR_MESSAGE());
        THROW;
    END CATCH;
END;
GO

IF NOT EXISTS (SELECT 1 FROM meta.SchemaVersion WHERE MigrationVersion = N'V6')
BEGIN
    INSERT INTO meta.SchemaVersion (MigrationVersion, Description)
    VALUES (N'V6', N'Canonical driver, vehicle and geography dimensions');
END;
GO
