-- P1-INC-02 verification entry point.
-- Apply migrations/V9__create_synthetic_cdc_demo.sql before running this file.
-- CDC is intentionally limited to meta.CdcDemoOperationalRecord.

USE [DWH_Insurance];
GO

SELECT
    DB_NAME() AS DatabaseName,
    is_cdc_enabled AS IsCdcEnabled
FROM sys.databases
WHERE name = DB_NAME();
GO

SELECT
    change_table.capture_instance,
    SCHEMA_NAME(source_table.schema_id) AS SourceSchema,
    source_table.name AS SourceTable,
    change_table.start_lsn
FROM cdc.change_tables AS change_table
JOIN sys.tables AS source_table
    ON source_table.object_id = change_table.source_object_id
WHERE source_table.object_id = OBJECT_ID(N'meta.CdcDemoOperationalRecord');
GO

SELECT
    watermark.ConsumerName,
    sys.fn_varbintohexstr(watermark.LastStartLsn) AS LastStartLsn,
    watermark.UpdatedAtUtc
FROM meta.CdcConsumerWatermark AS watermark
ORDER BY watermark.ConsumerName;
GO
