-- ============================================================================
-- Script: 04_sp_dim_others.sql
-- Giai doan: Giai doan 4 — ETL bang T-SQL voi Incremental Load & Audit Log
--            (Phan 4c: Stored Procedures chinh cho cac Dimension con lai)
-- Muc dich: Dinh nghia cac Stored Procedure nap du lieu vao cac bang Dimension:
--           - sp_Load_DimPolicy: UPSERT san pham bao hiem
--           - sp_Load_DimDate: Sinh/nap du lieu chieu thoi gian
--           - sp_Load_DimRegion: UPSERT vung/bang dia ly (SUSEP)
--           Ap dung MERGE UPSERT, ghi log vao ETL_Audit_Log, dam bao idempotent.
-- Tham chieu: implementation-guide.md (Giai doan 4, Muc 5, 6, 8)
--
-- Input mong doi:
--   - Du lieu nguon tu Staging qua CDC net changes hoac ham tao calendar
--   - BatchId tu Airflow / execution context
--
-- Output mong doi:
--   - Cac bang Dim_Policy, Dim_Date, Dim_Region duoc cap nhat day du
--   - Ghi log thoi gian, so dong anh huong, trang thai vao ETL_Audit_Log
--   - Chay lai nhieu lan cung mot batch khong lam thay doi du lieu
-- ============================================================================

/*
STALE SCAFFOLD — REQUIRES REFACTOR.

The historical commented examples below assume SUSEP/Porto policy, date and
region entities. They are intentionally retained as history only and are not
executed. The executable canonical entry point is
`sql/04_load_canonical_dimensions.sql`.
*/

USE DWH_Insurance;
GO

-- ----------------------------------------------------------------------------
-- 1. Stored Procedure: sp_Load_DimPolicy
-- ----------------------------------------------------------------------------
-- TODO: Cai dat sp_Load_DimPolicy voi MERGE UPSERT va Audit Log
/*
CREATE OR ALTER PROCEDURE dbo.sp_Load_DimPolicy
    @BatchId UNIQUEIDENTIFIER = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF @BatchId IS NULL SET @BatchId = NEWID();
    DECLARE @StartTime DATETIME2 = SYSUTCDATETIME();
    DECLARE @RowsAffected INT = 0;
    DECLARE @LogId BIGINT;

    INSERT INTO dbo.ETL_Audit_Log (BatchId, ProcedureName, StartTime, Status)
    VALUES (@BatchId, 'sp_Load_DimPolicy', @StartTime, 'RUNNING');
    SET @LogId = SCOPE_IDENTITY();

    BEGIN TRY
        BEGIN TRANSACTION;

        -- TODO: MERGE du lieu policy tu Staging vao Dim_Policy
        /*
        MERGE dbo.Dim_Policy AS Target
        USING (SELECT DISTINCT PolicyNumber, PolicyTypeCode, ... FROM Staging_InsuranceRaw.dbo.stg_susep_raw) AS Source
        ON Target.PolicyNumber = Source.PolicyNumber
        WHEN MATCHED THEN
            UPDATE SET Target.PolicyTypeCode = Source.PolicyTypeCode, Target.PolicyTypeName = Source.PolicyTypeName
        WHEN NOT MATCHED THEN
            INSERT (PolicyNumber, PolicyTypeCode, PolicyTypeName)
            VALUES (Source.PolicyNumber, Source.PolicyTypeCode, Source.PolicyTypeName);
        */

        SET @RowsAffected = @@ROWCOUNT;
        COMMIT TRANSACTION;

        UPDATE dbo.ETL_Audit_Log
        SET EndTime = SYSUTCDATETIME(), RowsAffected = @RowsAffected, Status = 'SUCCESS'
        WHERE LogId = @LogId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        UPDATE dbo.ETL_Audit_Log
        SET EndTime = SYSUTCDATETIME(), Status = 'FAILED', ErrorMessage = ERROR_MESSAGE()
        WHERE LogId = @LogId;
        THROW;
    END CATCH
END
GO
*/

-- ----------------------------------------------------------------------------
-- 2. Stored Procedure: sp_Load_DimRegion
-- ----------------------------------------------------------------------------
-- TODO: Cai dat sp_Load_DimRegion voi MERGE UPSERT va Audit Log
/*
CREATE OR ALTER PROCEDURE dbo.sp_Load_DimRegion
    @BatchId UNIQUEIDENTIFIER = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF @BatchId IS NULL SET @BatchId = NEWID();
    DECLARE @StartTime DATETIME2 = SYSUTCDATETIME();
    DECLARE @RowsAffected INT = 0;
    DECLARE @LogId BIGINT;

    INSERT INTO dbo.ETL_Audit_Log (BatchId, ProcedureName, StartTime, Status)
    VALUES (@BatchId, 'sp_Load_DimRegion', @StartTime, 'RUNNING');
    SET @LogId = SCOPE_IDENTITY();

    BEGIN TRY
        BEGIN TRANSACTION;

        -- TODO: MERGE du lieu vung dia ly tu Staging vao Dim_Region
        /*
        MERGE dbo.Dim_Region AS Target
        USING (SELECT DISTINCT RegionCode, StateCode, RegionName FROM Staging_InsuranceRaw.dbo.stg_susep_raw) AS Source
        ON Target.RegionCode = Source.RegionCode
        WHEN MATCHED THEN
            UPDATE SET Target.StateCode = Source.StateCode, Target.RegionName = Source.RegionName
        WHEN NOT MATCHED THEN
            INSERT (RegionCode, StateCode, RegionName)
            VALUES (Source.RegionCode, Source.StateCode, Source.RegionName);
        */

        SET @RowsAffected = @@ROWCOUNT;
        COMMIT TRANSACTION;

        UPDATE dbo.ETL_Audit_Log
        SET EndTime = SYSUTCDATETIME(), RowsAffected = @RowsAffected, Status = 'SUCCESS'
        WHERE LogId = @LogId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        UPDATE dbo.ETL_Audit_Log
        SET EndTime = SYSUTCDATETIME(), Status = 'FAILED', ErrorMessage = ERROR_MESSAGE()
        WHERE LogId = @LogId;
        THROW;
    END CATCH
END
GO
*/


-- ----------------------------------------------------------------------------
-- 3. Stored Procedure: sp_Load_DimDate
-- ----------------------------------------------------------------------------
-- TODO: Cai dat sp_Load_DimDate sinh lich chuan va nap vao Dim_Date
/*
CREATE OR ALTER PROCEDURE dbo.sp_Load_DimDate
    @StartDate DATE = '2003-01-01',
    @EndDate DATE = '2030-12-31',
    @BatchId UNIQUEIDENTIFIER = NULL
AS
BEGIN
    SET NOCOUNT ON;
    IF @BatchId IS NULL SET @BatchId = NEWID();
    DECLARE @StartTime DATETIME2 = SYSUTCDATETIME();
    DECLARE @RowsAffected INT = 0;
    DECLARE @LogId BIGINT;

    INSERT INTO dbo.ETL_Audit_Log (BatchId, ProcedureName, StartTime, Status)
    VALUES (@BatchId, 'sp_Load_DimDate', @StartTime, 'RUNNING');
    SET @LogId = SCOPE_IDENTITY();

    BEGIN TRY
        BEGIN TRANSACTION;

        -- TODO: Tao CTE Calendar va INSERT vao Dim_Date neu chua ton tai
        /*
        WITH DateRange AS (
            SELECT @StartDate AS FullDate
            UNION ALL
            SELECT DATEADD(DAY, 1, FullDate)
            FROM DateRange
            WHERE FullDate < @EndDate
        )
        INSERT INTO dbo.Dim_Date (DateKey, FullDate, DayNumberOfWeek, DayName, DayNumberOfMonth, DayNumberOfYear, MonthNumberOfYear, MonthName, Quarter, CalendarYear)
        SELECT 
            CONVERT(INT, FORMAT(FullDate, 'yyyyMMdd')),
            FullDate,
            DATEPART(WEEKDAY, FullDate),
            DATENAME(WEEKDAY, FullDate),
            DAY(FullDate),
            DATEPART(DAYOFYEAR, FullDate),
            MONTH(FullDate),
            DATENAME(MONTH, FullDate),
            DATEPART(QUARTER, FullDate),
            YEAR(FullDate)
        FROM DateRange
        WHERE CONVERT(INT, FORMAT(FullDate, 'yyyyMMdd')) NOT IN (SELECT DateKey FROM dbo.Dim_Date)
        OPTION (MAXRECURSION 0);
        */

        SET @RowsAffected = @@ROWCOUNT;
        COMMIT TRANSACTION;

        UPDATE dbo.ETL_Audit_Log
        SET EndTime = SYSUTCDATETIME(), RowsAffected = @RowsAffected, Status = 'SUCCESS'
        WHERE LogId = @LogId;
    END TRY
    BEGIN CATCH
        IF @@TRANCOUNT > 0 ROLLBACK TRANSACTION;
        UPDATE dbo.ETL_Audit_Log
        SET EndTime = SYSUTCDATETIME(), Status = 'FAILED', ErrorMessage = ERROR_MESSAGE()
        WHERE LogId = @LogId;
        THROW;
    END CATCH
END
GO
*/
