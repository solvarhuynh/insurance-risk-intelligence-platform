-- Repeat the real Track-A workloads without dropping indexes or clearing cache.
-- Historical before/after evidence: data/evidence.json; retained indexes: migration V14.
USE DWH_Insurance;
GO
SET STATISTICS IO ON;
SET STATISTICS TIME ON;
GO
SELECT c.CompanyCode, m.YearMonth, SUM(f.Premiums) AS Premiums, SUM(f.Claims) AS Claims
FROM dwh.FactSusepInsuranceMarket f
JOIN dwh.DimSusepCompany c ON c.SusepCompanyKey=f.SusepCompanyKey
JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
WHERE c.CompanyCode=6572 AND m.CalendarYear>=2018
GROUP BY c.CompanyCode,m.YearMonth ORDER BY m.YearMonth;
GO
SELECT s.State,p.Product,m.YearMonth,SUM(f.Premiums) AS Premiums,SUM(f.Claims) AS Claims
FROM dwh.FactSusepInsuranceMarket f
JOIN dwh.DimSusepState s ON s.SusepStateKey=f.SusepStateKey
JOIN dwh.DimSusepProduct p ON p.SusepProductKey=f.SusepProductKey
JOIN dwh.DimSusepMonth m ON m.SusepMonthKey=f.SusepMonthKey
WHERE s.State=N'SP' AND p.Product=N'0588 - DPVAT' AND m.CalendarYear>=2018
GROUP BY s.State,p.Product,m.YearMonth ORDER BY m.YearMonth;
GO
SET STATISTICS IO OFF;
SET STATISTICS TIME OFF;
