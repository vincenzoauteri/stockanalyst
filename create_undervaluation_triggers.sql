-- Database triggers to automatically recalculate undervaluation scores
-- when underlying financial data is updated

-- Function to trigger undervaluation score recalculation
CREATE OR REPLACE FUNCTION trigger_undervaluation_recalculation()
RETURNS TRIGGER AS $$
BEGIN
    -- Insert a recalculation request into a queue table
    INSERT INTO undervaluation_recalc_queue (symbol, trigger_table, triggered_at)
    VALUES (COALESCE(NEW.symbol, OLD.symbol), TG_TABLE_NAME, CURRENT_TIMESTAMP)
    ON CONFLICT (symbol) DO UPDATE SET
        triggered_at = CURRENT_TIMESTAMP,
        trigger_table = EXCLUDED.trigger_table;
    
    RETURN COALESCE(NEW, OLD);
END;
$$ LANGUAGE plpgsql;

-- Create queue table for recalculation requests
CREATE TABLE IF NOT EXISTS undervaluation_recalc_queue (
    symbol TEXT PRIMARY KEY,
    trigger_table TEXT NOT NULL,
    triggered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    status TEXT DEFAULT 'pending' CHECK (status IN ('pending', 'processing', 'completed', 'failed'))
);

-- Create triggers on all relevant tables

-- Trigger on company_profiles (price, market cap changes)
DROP TRIGGER IF EXISTS trigger_company_profiles_underval ON company_profiles;
CREATE TRIGGER trigger_company_profiles_underval
    AFTER INSERT OR UPDATE OF price, mktcap, sector
    ON company_profiles
    FOR EACH ROW
    EXECUTE FUNCTION trigger_undervaluation_recalculation();

-- Trigger on income_statements (earnings, revenue changes)
DROP TRIGGER IF EXISTS trigger_income_statements_underval ON income_statements;
CREATE TRIGGER trigger_income_statements_underval
    AFTER INSERT OR UPDATE OF total_revenue, net_income, basic_eps, diluted_eps
    ON income_statements
    FOR EACH ROW
    EXECUTE FUNCTION trigger_undervaluation_recalculation();

-- Trigger on balance_sheets (assets, equity, debt changes)
DROP TRIGGER IF EXISTS trigger_balance_sheets_underval ON balance_sheets;
CREATE TRIGGER trigger_balance_sheets_underval
    AFTER INSERT OR UPDATE OF total_assets, total_equity, total_debt, current_assets, current_liabilities
    ON balance_sheets
    FOR EACH ROW
    EXECUTE FUNCTION trigger_undervaluation_recalculation();

-- Trigger on cash_flow_statements (cash flow changes)
DROP TRIGGER IF EXISTS trigger_cash_flow_statements_underval ON cash_flow_statements;
CREATE TRIGGER trigger_cash_flow_statements_underval
    AFTER INSERT OR UPDATE OF operating_cash_flow, free_cash_flow
    ON cash_flow_statements
    FOR EACH ROW
    EXECUTE FUNCTION trigger_undervaluation_recalculation();

-- Create index for efficient queue processing
CREATE INDEX IF NOT EXISTS idx_underval_queue_pending ON undervaluation_recalc_queue (status, triggered_at) 
WHERE status = 'pending';

-- View to see pending recalculations
CREATE OR REPLACE VIEW pending_undervaluation_recalcs AS
SELECT 
    symbol,
    trigger_table,
    triggered_at,
    EXTRACT(EPOCH FROM (CURRENT_TIMESTAMP - triggered_at)) / 60 as minutes_pending
FROM undervaluation_recalc_queue 
WHERE status = 'pending'
ORDER BY triggered_at;

COMMENT ON TABLE undervaluation_recalc_queue IS 'Queue for automatic undervaluation score recalculation requests';
COMMENT ON FUNCTION trigger_undervaluation_recalculation() IS 'Trigger function to queue undervaluation score recalculations';