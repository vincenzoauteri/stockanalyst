# Valuation Function Enhancement Plan

This document outlines a plan to enhance the application's stock valuation functionality, drawing on the principles from `stockval.md`. The goal is to evolve from the current relative scoring system to a more robust, multi-model "Valuation Scorecard" that provides a more comprehensive estimate of a stock's intrinsic value.

## Summary of Proposed Enhancements

The current valuation system is a good starting point but lacks absolute valuation models and contextual market data. The proposed enhancements will create a more sophisticated framework by:

1.  **Integrating Absolute Valuation Models:** Implement both Discounted Cash Flow (DCF) and Dividend Discount Model (DDM) to calculate a fundamentals-based intrinsic value in dollars.
2.  **Improving Relative Valuation:** Activate sector-average comparisons and introduce the PEG ratio to better contextualize valuation multiples.
3.  **Introducing Asset-Based Concepts:** Use Price-to-Book ratio to identify companies trading near or below their net asset value, establishing a "margin of safety" floor.
4.  **Synthesizing Results:** Combine the outputs of all models into a weighted-average intrinsic value and a "Valuation Football Field" summary, providing a defensible valuation range.

## TODO List

### Phase 1: Foundational Enhancements

-   [ ] **Enhance Data Collection:**
    -   [ ] Fetch or calculate **Beta** for each stock. This can be derived from historical price data against the S&P 500.
    -   [ ] Add configurable values for the **Risk-Free Rate** (e.g., 10-year Treasury yield) and **Equity Risk Premium**.
-   [ ] **Calculate Historical Growth:**
    -   [ ] Create a function to calculate historical revenue and earnings growth rates over 1, 3, and 5-year periods using the `income_statements` table.
-   [ ] **Activate Sector Comparison:**
    -   [ ] Uncomment and integrate the `get_sector_averages` function into the main calculation flow.
    -   [ ] Modify the scoring logic for P/E, P/S, and P/B to be relative to the sector average, not just a static scale.
-   [ ] **Implement PEG Ratio:**
    -   [ ] Add a PEG ratio calculation to the `calculate_financial_ratios` function.
    -   [ ] Add a `peg_score` to the scoring model.

### Phase 2: Implement Absolute Valuation Models

-   [ ] **Implement Dividend Discount Model (DDM):**
    -   [ ] Create a `calculate_ddm_value` function.
    -   [ ] Use data from `corporate_actions` to get the latest dividend (D0).
    -   [ ] Use historical dividend data to calculate a dividend growth rate (g).
    -   [ ] Use the configured Risk-Free Rate and Beta to calculate the Cost of Equity (r).
    -   [ ] Return an intrinsic value for dividend-paying stocks where `r > g`.
-   [ ] **Implement Discounted Cash Flow (DCF) Model:**
    -   [ ] Create a `calculate_dcf_value` function.
    -   [ ] **Calculate WACC:**
        -   [ ] Implement a function to calculate the Weighted Average Cost of Capital (WACC).
        -   [ ] Use Market Cap for the Market Value of Equity.
        -   [ ] Use `total_debt` from the balance sheet for the Market Value of Debt.
        -   [ ] Use the calculated Cost of Equity (from Beta, Risk-Free Rate, ERP).
        -   [ ] Estimate a Cost of Debt (e.g., based on interest expense and total debt).
    -   [ ] **Forecast Free Cash Flow (FCF):**
        -   [ ] Calculate historical Free Cash Flow to the Firm (FCFF) using data from financial statements.
        -   [ ] Implement a simple two-stage FCF forecast: a 5-year high-growth period using the historical growth rate, followed by a perpetual growth period using a conservative rate (e.g., 2.5%).
    -   [ ] **Calculate Terminal Value:**
        -   [ ] Use the Gordon Growth (Perpetuity Growth) model to calculate terminal value.
    -   [ ] **Calculate Final DCF Value:**
        -   [ ] Discount all future FCFs and the terminal value back to the present to get Enterprise Value.
        -   [ ] Convert Enterprise Value to Equity Value per share.

### Phase 3: Synthesis and Presentation

-   [ ] **Create Valuation Scorecard:**
    -   [ ] In `YFinanceUndervaluationCalculator`, create a new master function `get_valuation_scorecard`.
    -   [ ] This function will call the existing relative scoring model, the DDM model, and the DCF model.
-   [ ] **Calculate Weighted Intrinsic Value:**
    -   [ ] Assign weights to each model's output (e.g., DCF: 40%, Relative: 40%, DDM: 20% if applicable).
    -   [ ] Calculate a final, weighted-average intrinsic value per share.
-   [ ] **Update Database Schema:**
    -   [ ] Add new columns to the `undervaluation_scores` table to store the outputs: `dcf_value`, `ddm_value`, `relative_value`, `final_intrinsic_value`.
-   [ ] **Update Frontend:**
    -   [ ] Modify the "Valuation" tab on the stock detail page to display the new scorecard.
    -   [ ] Show the valuation range from each model (a simple "Valuation Football Field").
    -   [ ] Clearly display the final intrinsic value and compare it to the current market price.

## Needed Additional Data (Summary)

-   **Beta:** For Cost of Equity calculation.
-   **Risk-Free Rate:** For Cost of Equity and WACC.
-   **Equity Risk Premium (ERP):** For Cost of Equity and WACC.
-   **(Future) Analyst Growth Estimates:** For more reliable DCF forecasts.
