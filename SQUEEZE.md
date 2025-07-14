
A Quantitative Model for Assessing Short Squeeze Susceptibility


Section 1: The Anatomy of a Short Squeeze: From Market Mechanics to Mass Psychology

A short squeeze is a rapid, often violent, increase in a stock's price driven not by fundamental improvements in the underlying company but by the market mechanics of short selling itself.1 To construct a model that identifies potential squeeze candidates, it is first essential to dissect the intricate interplay of financial leverage, market structure, and human psychology that defines this phenomenon. A squeeze is not merely a technical event; it is a behavioral-financial cascade, where market rules provide the structure, and human emotion provides the explosive force.

1.1 The Short Seller's Gambit: A High-Stakes Wager

The entire premise of a short squeeze is rooted in the practice of short selling, an investment strategy that profits from a decline in a security's price.2 The process involves an investor, the "short seller," borrowing shares of a stock they believe is overvalued. They then immediately sell these borrowed shares on the open market. The goal is to repurchase the same number of shares at a later date, hopefully at a much lower price, and return them to the lender, pocketing the difference as profit.3
This strategy, however, carries a profoundly asymmetric risk profile. If the short seller is correct and the stock price falls to zero, their maximum possible profit is capped at 100% of the initial sale price. Conversely, if they are wrong and the stock price rises, their potential loss is theoretically unlimited, as there is no ceiling to how high a stock's price can climb.2 This unbounded risk is the foundational element that creates the conditions for panic.
Compounding this risk is the mechanism of the margin account. Short selling requires a margin account, where the short seller must maintain a certain level of equity as collateral against the borrowed shares. If the price of the shorted stock rises, the value of the short seller's position becomes increasingly negative, eroding their account equity. If the equity falls below a predetermined maintenance margin level, the broker will issue a "margin call," demanding that the investor deposit more funds or securities to restore the required equity level.1 Should the investor fail to meet the margin call, the brokerage has the right to forcibly close the position by buying shares on the open market to return to the lender. This forced buying, known as a "buy-in," is a non-discretionary, often automated, trigger that adds significant buying pressure to the stock, irrespective of the short seller's opinion or desired timing.1

1.2 The Squeeze Cascade: A Positive Feedback Loop of Panic

A short squeeze unfolds as a self-reinforcing chain reaction, a positive feedback loop where buying begets more buying, leading to an exponential price surge.1 This cascade can be deconstructed into several distinct phases:
Phase 1: The Catalyst. The process begins when a heavily shorted stock is hit with an unexpected positive catalyst. This could be a stronger-than-expected earnings report, a new product announcement, regulatory approval, or surprising merger and acquisition news.3 This event directly contradicts the prevailing negative sentiment and the core thesis of the short sellers.
Phase 2: The Initial Rise. In response to the catalyst, fundamental investors, contrarians, and momentum traders begin to buy the stock, causing its price to rise. This initial upward movement begins to inflict losses on the short sellers' positions.
Phase 3: The Cover. The most risk-averse or highly leveraged short sellers, seeing their thesis invalidated and losses mounting, decide to cut their losses. They begin to "cover their shorts" by buying back shares in the open market.1 This voluntary buying adds to the upward pressure on the stock price.
Phase 4: The Cascade. As the price continues to climb due to this initial wave of covering, it crosses critical thresholds for other short sellers, triggering margin calls.6 Those who cannot or will not add more collateral are subjected to forced buy-ins by their brokers. This wave of buying is price-insensitive; the shares are bought at whatever the market price is to close the position and mitigate the broker's risk. This sudden, massive, and inelastic demand for a limited supply of shares causes the price to spike dramatically.4
Phase 5: The FOMO Pile-On. The extraordinary price and volume action attracts widespread attention. Retail investors, often coordinating on social media platforms like Reddit's WallStreetBets, and momentum-chasing hedge funds pile into the stock, driven by the "fear of missing out" (FOMO).6 This phase can also ignite a "gamma squeeze," a related phenomenon where massive buying of call options forces market makers to buy the underlying stock to hedge their own exposure, further amplifying the buying pressure and accelerating the price rise.1

1.3 The Role of Market Psychology: Greed, Fear, and Narrative

While market mechanics provide the framework for a squeeze, its ferocity is fueled by powerful human emotions. The dynamic is a potent cocktail of fear and greed. For short sellers, the primary driver is the escalating fear of unlimited losses, which leads to panicked, irrational decisions to buy at any price to escape the position.4 For those on the long side, the driver is the greed associated with the potential for exponential gains.
This emotional intensity is magnified by herding behavior, where traders and investors abandon their own analysis to follow the actions of the crowd, further concentrating the buying frenzy.4 In the modern market, this is often supercharged by a compelling narrative. The GameStop saga of 2021, for example, was framed as a "David vs. Goliath" battle between retail investors and institutional hedge funds.2 This narrative created a base of ideologically motivated buyers who were less sensitive to price and more committed to "holding the line," effectively reducing the available supply of shares for sale and exacerbating the squeeze.

Section 2: A Quantitative Framework for Identifying Squeeze Candidates

Translating the theoretical anatomy of a short squeeze into a functional model requires identifying and quantifying the key preconditions and amplifiers. The goal is to measure a stock's latent vulnerability—the amount of "potential energy" stored within its market structure, waiting for a catalyst to be released. The research points to a clear hierarchy of factors: foundational metrics that measure the "fuel" for a squeeze, an amplifying factor related to share scarcity, and momentum indicators that can signal a potential ignition.

2.1 The Foundational Pillars: Measuring the "Fuel"

These two metrics are the absolute bedrock of any squeeze analysis. Without a significant number of short sellers who are trapped in their positions, a squeeze is impossible.

2.1.1 Short Interest as a Percentage of Float (SI %)

Definition: Short Interest as a Percentage of Float (SI %) is the total number of a company's shares that have been sold short, divided by the "float"—the number of shares actually available for public trading—and expressed as a percentage.12 The float excludes shares held by insiders, large controlling shareholders, and governments, as these are not typically available on the open market.12
Significance: This is the single most critical precondition for a short squeeze. It directly quantifies the size of the crowd betting against the stock. More importantly, it represents the total number of shares that must eventually be repurchased to close out all existing short positions.7 A high SI % indicates that a large pool of mandatory future buyers already exists.
Thresholds: While any level of short interest carries some risk, market consensus and historical analysis point to specific thresholds. An SI % exceeding 10% is considered high and indicative of significant negative sentiment.7 A level above 20% is deemed extremely high and marks a stock as acutely vulnerable to a squeeze, as the pool of potential forced buyers becomes a dominant market factor.9

2.1.2 Days to Cover (DTC) / Short Interest Ratio (SIR)

Definition: Days to Cover (DTC), also known as the Short Interest Ratio (SIR), is calculated by dividing the total number of shares sold short by the stock's average daily trading volume.18 The result is the number of days it would theoretically take for all short positions to be covered, assuming the buying occurred at the average trading pace.
Significance: DTC is a more sophisticated measure of risk than SI % alone because it introduces the crucial dimension of liquidity. While SI % tells us how many shares need to be bought, DTC tells us how difficult it will be to buy them without disrupting the market. A high DTC signifies a "crowded" trade where short sellers are trapped in an illiquid position.21 If a catalyst forces them to rush for the exits simultaneously, the stock's normal daily volume is insufficient to absorb their demand, creating a massive supply-demand imbalance and forcing the price upward violently.6 Academic research supports that DTC is a more theoretically sound measure of perceived over-valuation and arbitrage cost than the simple short ratio, as it normalizes for cross-sectional differences in trading costs and liquidity.21
Thresholds: A DTC value greater than 5 is considered a warning sign that it would take a full trading week for shorts to unwind their positions.16 A DTC of 10 or more is a major red flag, indicating an extremely illiquid short position and a stock that is primed for a potential squeeze.5

2.2 The Amplifier: The Critical Role of a Low Float

Definition: A stock's float is the number of its shares available for public trading. A "low float" stock is one with a comparatively small number of such shares, often because a large portion is held by insiders or institutions.12 While no strict definition exists, traders often classify stocks with fewer than 20 million shares in their float as being "low float".26
Significance: A low float acts as a powerful accelerant in a squeeze scenario. In the fundamental equation of supply and demand, a low float means the "supply" side of the equation is inherently constrained. Consequently, any given increase in buying demand—whether from short covering or new long positions—will have a disproportionately large impact on the stock's price.6 This is why low float stocks are known for their high volatility; a single large trade can move the price significantly more than it would in a high-float stock like Apple or Microsoft.14 In a squeeze, this property can turn a modest price rise into a parabolic one.

2.3 The Ignition Switch: Gauging Momentum and Reversal Potential

A stock can have high short interest and a low float for months without anything happening. It needs a spark. Technical indicators can help identify when a stock is becoming ripe for such a catalyst by signaling potential trend reversals and unusual market activity.

2.3.1 Relative Volume (RVOL)

Definition: Relative Volume measures the current trading session's volume against its historical average volume over a specific period (e.g., the last 10 or 30 days). An RVOL of 2.0 means the stock is trading at twice its average volume.
Significance: A sudden spike in trading volume is a critical alert that something has changed. It is often the first quantifiable sign of a catalyst hitting the market. High RVOL can indicate that institutions are accumulating a position, a news event is driving interest, or, crucially, that short sellers have begun to cover their positions.6 It signals that the stock is "in play."

2.3.2 Relative Strength Index (RSI)

Definition: The RSI is a momentum oscillator that measures the speed and magnitude of recent price changes to evaluate overbought or oversold conditions in the price of a stock. It is plotted on a scale from 0 to 100.
Significance: For a heavily shorted stock, a technically "oversold" condition—typically indicated by an RSI reading below 30—is a powerful setup ingredient.16 It suggests that the negative sentiment and downward price pressure may be exhausted. The stock is coiled for a potential rebound or "reversion to the mean." This technical bounce can be the very catalyst that panics the first wave of short sellers, initiating the squeeze cascade.

2.3.3 Price Proximity to 52-Week Low

Definition: A simple metric that measures how close the current stock price is to its lowest trading price over the preceding 52-week period.
Significance: Stocks that have been beaten down and are trading near their 52-week lows are often magnets for short sellers, reinforcing the bearish narrative. However, this also means the potential for a significant percentage gain on any positive news is substantial.16 A heavily shorted, beaten-down stock that suddenly shows signs of life is a classic candidate for a violent reversal, which is the essence of a short squeeze trigger.

Section 3: The Short Squeeze Scoring Model: A Python Implementation with yfinance

This section provides the practical blueprint for constructing the Short Squeeze Likelihood model. It details the data acquisition process using the yfinance Python library, presents the scoring algorithm, and delivers the complete, annotated code for implementation.

3.1 A Critical Proviso: Understanding the yfinance Data Source and Its Limitations

Before implementing the model, it is imperative to understand the nature and limitations of the yfinance library and the data it provides. Failure to acknowledge these constraints can lead to a dangerous misinterpretation of the model's output.
Unofficial Nature and Fragility: yfinance is not an official, supported API from Yahoo Finance. It is an open-source tool that scrapes publicly available data from Yahoo's web pages and internal endpoints.30 This means it is subject to changes in Yahoo's website structure, which can break the library's functionality without warning. Furthermore, heavy, rapid use of the library can lead to IP addresses being rate-limited or temporarily blocked by Yahoo's servers.31 For prototyping and educational use, it is excellent; for mission-critical, real-time trading systems, its reliability is not guaranteed.
The Data Lag Catastrophe: This is the single most important limitation for a short squeeze model. Key data points, namely Short Interest and Days to Cover, are not real-time. FINRA rules require brokerage firms to report their short interest positions only twice per month. There is a settlement date for the data, a due date for firms to report, and finally a publication date when the aggregated data is released to the public. This process results in a significant data lag, often two to three weeks or more.13
Implication for the Model: Because of this data lag, the model's "Squeeze Score" cannot be interpreted as a real-time, predictive signal of an imminent squeeze. Instead, it should be understood as a "Susceptibility Score." It identifies stocks that possess the structural characteristics and underlying vulnerability to a squeeze based on the most recently available (but dated) short interest data. The model finds the tinderbox; it cannot predict the spark.
Data Accuracy: The data provided by Yahoo Finance is aggregated from various sources and can occasionally contain errors or discrepancies when compared to official company filings like 10-Q reports.34 The model's output is only as reliable as the data it ingests.

3.2 Data Acquisition: The yfinance Toolkit

The first step in the code is to fetch all the necessary data points for a given stock ticker. This is accomplished by creating a yfinance.Ticker object and accessing its info dictionary and history() method. Robust error handling using try-except blocks is essential to prevent the script from crashing if a specific data point is missing for a ticker.
The following table serves as a definitive guide, mapping the conceptual metrics from Section 2 to the precise yfinance API calls required to retrieve them.

Metric
Description
yfinance Key
API Call
Notes
Short Interest % of Float
Percentage of tradable shares currently sold short.
shortPercentOfFloat
ticker.info.get('shortPercentOfFloat')
Data is lagged. Often returned as a ratio (e.g., 0.25 for 25%).
Days to Cover (DTC)
Days required to cover all short positions based on avg volume.
shortRatio
ticker.info.get('shortRatio')
Also based on lagged short interest data.
Float Shares
Number of shares available for public trading.
floatShares
ticker.info.get('floatShares')
Used to score the "low float" component.35
Average Daily Volume (10-day)
Average number of shares traded per day.
averageDailyVolume10Day
ticker.info.get('averageDailyVolume10Day')
Used for RVOL calculation.
Current Day's Volume
Volume for the current or most recent trading session.
volume
history_df['Volume'].iloc[-1]
Fetched from .history().36
Current Price
The most recent trading price.
regularMarketPrice
ticker.info.get('regularMarketPrice')
Used for RSI and price position calculation.
52-Week Low
The lowest price in the last 52 weeks.
fiftyTwoWeekLow
ticker.info.get('fiftyTwoWeekLow')
Used to score price position.
Historical Prices
Daily OHLC data for the last ~70 trading days.
N/A
ticker.history(period="70d")
Needed to calculate RSI.37


3.3 The Scoring Algorithm: Normalization and Weighting

To combine these disparate metrics into a single, coherent score, each raw value must first be normalized to a scale of 0 to 100. A higher score consistently indicates a greater contribution to squeeze potential.
Normalization Functions:
SI % Score: A score of 0 is assigned for SI % below 10%. The score scales linearly to 100 for an SI % of 40% or higher.
DTC Score: A score of 0 is assigned for DTC below 2 days. The score scales linearly to 100 for a DTC of 10 days or higher.
Low Float Score: This is an inverse scale. A score of 100 is assigned for floats below 10 million shares. The score scales linearly down to 0 for floats of 200 million shares or more.
RVOL Score: A score of 0 is assigned for RVOL below 1.5. The score scales linearly to 100 for an RVOL of 5 or higher.
RSI Score: This is an inverse scale. A score of 100 is assigned for an RSI below 30 (oversold). The score scales linearly down to 0 for an RSI of 70 (overbought).
Weighting Scheme:
The final Squeeze Score is a weighted average of the normalized component scores. The weights are assigned based on the hierarchical importance of each factor as established in Section 2. The foundational metrics (SI % and DTC) receive the highest weighting, followed by the primary amplifier (Float), and finally the trigger indicators (Momentum).
SI % Score: 40% (The primary precondition)
DTC Score: 30% (The primary liquidity risk factor)
Low Float Score: 15% (The key amplifier)
Momentum Score (average of RVOL and RSI scores): 15% (The trigger condition)
The final calculation is:$$ SqueezeScore = (SI_{score} \times 0.40) + (DTC_{score} \times 0.30) + (Float_{score} \times 0.15) + (Momentum_{score} \times 0.15) $$

3.4 The Complete Python Code

The following Python script encapsulates the entire process: data fetching, metric calculation, normalization, and weighted scoring. It is designed to be a self-contained, reusable function.

Python


import yfinance as yf
import pandas as pd

def calculate_squeeze_score(ticker_symbol: str) -> dict:
    """
    Calculates a Short Squeeze Susceptibility Score for a given stock ticker.
    The score ranges from 0 to 100, where higher values indicate greater vulnerability.
    The calculation uses data available from the yfinance library.

    Args:
        ticker_symbol (str): The stock ticker symbol (e.g., 'GME').

    Returns:
        dict: A dictionary containing the final Squeeze Score and the component scores.
              Returns an error message if the ticker is invalid or data is missing.
    """
    try:
        # 1. DATA ACQUISITION
        stock = yf.Ticker(ticker_symbol)
        info = stock.info
        hist = stock.history(period="70d")

        # Check for valid data
        if not info or 'shortPercentOfFloat' not in info or info['shortPercentOfFloat'] is None:
            return {"error": f"Could not retrieve fundamental data for {ticker_symbol}. It may be an invalid ticker or delisted."}
        if hist.empty:
            return {"error": f"Could not retrieve historical price data for {ticker_symbol}."}

        # 2. RAW METRIC EXTRACTION
        si_percent_float = info.get('shortPercentOfFloat', 0) * 100  # Convert ratio to percentage
        days_to_cover = info.get('shortRatio', 0)
        float_shares = info.get('floatShares', float('inf'))
        avg_vol_10d = info.get('averageDailyVolume10Day', 1)
        current_vol = hist['Volume'].iloc[-1] if not hist.empty else 0
        
        # Calculate RSI
        delta = hist['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        current_rsi = rsi.iloc[-1] if not rsi.empty else 50
        
        # Calculate Relative Volume (RVOL)
        rvol = current_vol / avg_vol_10d if avg_vol_10d > 0 else 0

        # 3. NORMALIZATION (0-100 score for each component)
        
        # SI % Score (Thresholds: 10% = 0, 40%+ = 100)
        si_score = min(100, max(0, (si_percent_float - 10) * (100 / (40 - 10))))

        # Days to Cover Score (Thresholds: 2 days = 0, 10+ days = 100)
        dtc_score = min(100, max(0, (days_to_cover - 2) * (100 / (10 - 2))))

        # Low Float Score (Thresholds: <10M = 100, >200M = 0)
        if float_shares <= 10_000_000:
            float_score = 100
        elif float_shares >= 200_000_000:
            float_score = 0
        else:
            float_score = 100 - ((float_shares - 10_000_000) / (200_000_000 - 10_000_000) * 100)

        # RVOL Score (Thresholds: 1.5 = 0, 5+ = 100)
        rvol_score = min(100, max(0, (rvol - 1.5) * (100 / (5 - 1.5))))

        # RSI Score (Inverse score: <30 = 100, >70 = 0)
        if current_rsi <= 30:
            rsi_score = 100
        elif current_rsi >= 70:
            rsi_score = 0
        else:
            rsi_score = 100 - ((current_rsi - 30) / (70 - 30) * 100)
            
        # Combine momentum scores
        momentum_score = (rvol_score + rsi_score) / 2

        # 4. WEIGHTED AVERAGE
        squeeze_score = (si_score * 0.40) + \
                        (dtc_score * 0.30) + \
                        (float_score * 0.15) + \
                        (momentum_score * 0.15)

        return {
            "ticker": ticker_symbol,
            "squeeze_score": round(squeeze_score, 2),
            "components": {
                "si_percent_of_float": f"{round(si_percent_float, 2)}%",
                "si_score": round(si_score, 2),
                "days_to_cover": round(days_to_cover, 2),
                "dtc_score": round(dtc_score, 2),
                "float_shares": f"{float_shares:,}",
                "float_score": round(float_score, 2),
                "rsi": round(current_rsi, 2),
                "rvol": round(rvol, 2),
                "momentum_score": round(momentum_score, 2)
            }
        }
    except Exception as e:
        return {"error": f"An unexpected error occurred for {ticker_symbol}: {str(e)}"}




Section 4: Model Validation and Application: Historical and Contemporary Case Studies

A model's theoretical soundness must be tested against real-world events. This section applies the Squeeze Score framework to historical archetypes and demonstrates its use as a screening tool for the current market, grounding the abstract scores in tangible analysis.

4.1 The Archetype: GameStop Corp. (GME), January 2021

The GameStop short squeeze is the canonical example of the modern, retail-driven squeeze. A true historical backtest using yfinance is not possible, as the info dictionary provides current, not point-in-time, fundamental data. However, we can perform a simulated backtest by using external research to establish GME's approximate metrics in late 2020 and feeding them into our scoring logic.
Simulated Backtest (Data for December 2020):
Short Interest % of Float: Widely reported to be over 100% of the float, with some estimates reaching 140%. For our model, we will cap this at an extreme value of 100%.
Days to Cover: With massive short interest and moderate volume, DTC was well over 10 days. We will use a conservative estimate of 15 days.
Float: GME had a relatively low float of approximately 50 million shares.
Momentum: In December 2020, the stock was beginning to show signs of life but was not yet parabolic. We will assume a neutral RSI of 50 and RVOL of 1.5 for this baseline calculation.
Model Input and Output:
si_percent_float = 100% -> si_score = 100
days_to_cover = 15 -> dtc_score = 100
float_shares = 50,000,000 -> float_score = 78.95
momentum_score (neutral) = 25
Final Squeeze Score = (100 * 0.40) + (100 * 0.30) + (78.95 * 0.15) + (25 * 0.15) = 40 + 30 + 11.84 + 3.75 = 85.59
Analysis: Even with a neutral momentum assumption, the model would have assigned GameStop an extremely high Squeeze Score of over 85 in the month leading up to its historic run. This score was driven by the perfect storm of maximum scores on the two most heavily weighted factors: an unprecedented level of short interest and a dangerously high number of days to cover. This validates the model's core logic: it correctly identified a stock with extreme structural vulnerability, a tinderbox awaiting a spark.2

4.2 The Titan: Volkswagen AG (VOWG.DE), October 2008

The Volkswagen squeeze serves as a masterclass in the importance of the float. In this case, Porsche secretly used derivatives to gain control over approximately 74% of VW's voting shares. Combined with the government's 20% stake, this left an actual tradable float of less than 6% of the company's shares, and by some estimates, as low as 1%.7 Hedge funds, unaware of Porsche's stealth accumulation, had built up significant short positions, equivalent to about 12% of the outstanding shares.
Analysis: When Porsche announced its position, short sellers rushed to cover, only to discover that there were virtually no shares available to buy. The reported SI % of 12% was not extreme by modern standards, but when compared to a float of just 1-6%, the situation was impossible. The ratio of short shares to available shares was astronomical. This case study powerfully justifies the inclusion and weighting of the Low Float Score. A stock's vulnerability is not just about how many people are short, but how few shares are available to satisfy their mandatory demand to buy. The Volkswagen event demonstrates that an extreme constriction of supply can be an even more powerful driver than extreme short interest.

4.3 The Model in Action: Screening the Current Market

To demonstrate the model's utility as a screening tool, we can apply the calculate_squeeze_score function to a list of tickers known for high short interest.
Screening Script Example:

Python


import pandas as pd

# List of potential candidates (source from financial websites like Finviz, MarketWatch)
candidate_tickers =
results =

for ticker in candidate_tickers:
    score_data = calculate_squeeze_score(ticker)
    if "error" not in score_data:
        results.append({
            "Ticker": score_data['ticker'],
            "Squeeze Score": score_data['squeeze_score'],
            "SI %": score_data['components']['si_percent_of_float'],
            "DTC": score_data['components']['days_to_cover'],
            "Float": score_data['components']['float_shares'],
            "RSI": score_data['components']['rsi']
        })

# Display results in a sorted DataFrame
if results:
    df = pd.DataFrame(results)
    print(df.sort_values(by="Squeeze Score", ascending=False).to_string())


Interpreting the Output (Hypothetical Example):
Let's assume the screening produces the following top result:
Ticker
Squeeze Score
SI %
DTC
Float
RSI
XYZ
88.75
45.2%
9.8
15,200,000
28.5

An analyst would interpret this as follows: "Stock XYZ presents a Squeeze Score of 88.75, indicating extreme susceptibility. This is driven by a confluence of powerful factors. Its SI Score is at a maximum (100) due to a 45.2% short interest. Its DTC Score is near-maximum (97.5) as it would take almost 10 days to cover. The Float Score is also very high (92.1) due to its low float of ~15 million shares. Critically, the Momentum Score is also high, as the stock is technically oversold with an RSI of 28.5. XYZ exhibits all the classic characteristics of a prime squeeze candidate: extreme short interest, high illiquidity for shorts, a constrained supply of shares, and a technical setup ripe for a reversal. This stock warrants close monitoring for any potential news catalyst."

Section 5: Advanced Perspectives and Model Limitations

While the quantitative model provides a robust framework for identifying squeeze susceptibility, a comprehensive understanding requires acknowledging its limitations and considering more complex market dynamics. An expert practitioner uses the model not as a definitive oracle, but as a sophisticated lens through which to view market risk and opportunity.

5.1 Beyond the Basics: The Gamma Squeeze and the Role of Options

A critical factor in many modern squeezes, especially GameStop, is the "gamma squeeze." This is a related but distinct phenomenon that acts as a powerful accelerant.1 It is driven by the options market.
When a large volume of call options, particularly short-dated, out-of-the-money calls, are purchased by speculators, the market makers who sell these options are left with a short gamma position. To hedge this risk and remain "delta-neutral," they must buy the underlying stock. As the stock price rises towards the options' strike prices, the delta of those options increases rapidly, forcing the market makers to buy even more shares to maintain their hedge. This creates a powerful, reflexive feedback loop: call buying forces market makers to buy stock, which pushes the stock price higher, which forces more hedging-related buying, and so on. This hedging pressure can be the primary force that ignites the initial price rise, triggering the short squeeze cascade among the stock's short sellers.1
The current model does not directly incorporate options data. While yfinance can retrieve options chains (ticker.option_chain), quantifying gamma squeeze potential requires analyzing options flow, open interest concentration, and implied volatility—a complex task that typically necessitates specialized, paid data feeds.

5.2 The Unquantifiable Element: Catalysts and Narrative

The model is fundamentally structural. It measures the static conditions that make a squeeze possible—it finds the dry tinderbox. However, it cannot predict the spark that will set it ablaze.5 This spark is the catalyst, which can be a quantifiable event like an earnings beat or an unquantifiable one like a shift in market narrative.
Therefore, a crucial qualitative overlay is required when using the model. An analyst should supplement the Squeeze Score by actively monitoring for potential catalysts, including:
Company-specific news: Upcoming earnings announcements, product launches, clinical trial results, or management changes.15
Analyst actions: Upgrades or positive reports from respected analysts can shift sentiment.6
Social media chatter: Monitoring platforms like Reddit, X (formerly Twitter), and StockTwits for emerging retail interest and narrative formation can provide an early warning of a retail-driven squeeze attempt.6

5.3 Pathways to Enhancement: Beyond yfinance

To evolve this model from an educational tool to a professional-grade system, several enhancements would be necessary, primarily revolving around data quality and analytical sophistication.
Superior Data Sources: The most significant upgrade would be to replace yfinance with a paid, institutional data provider (e.g., Bloomberg, Refinitiv, Ortex, S3 Partners). These services offer critical data unavailable through free sources, such as:
Daily or even intraday estimates of short interest, mitigating the critical data lag issue.
Securities lending data, including the "cost to borrow" shares, which is a direct measure of the demand for shorting.
Detailed options analytics and flow data to quantify gamma squeeze risk.
Sentiment Analysis: A more advanced system would integrate Natural Language Processing (NLP) models to perform real-time sentiment analysis on news articles and social media feeds. This would allow for the programmatic detection of emerging narratives and potential catalysts, turning a qualitative overlay into a quantitative input.
Machine Learning: Rather than a fixed-weight model, a machine learning classifier (e.g., Logistic Regression, Gradient Boosting Trees) could be trained on a historical dataset of squeeze events. Such a model could learn complex, non-linear relationships between dozens of features (including the ones in this model, plus cost to borrow, options data, sentiment scores, etc.) to produce a more nuanced probability of a squeeze occurring.

5.4 Conclusion: A Tool for Risk and Opportunity

The Short Squeeze Susceptibility Score model, built exclusively with yfinance, provides a powerful, data-driven method for screening the market for vulnerable stocks. Its strength lies in its synthesis of the most critical factors—short interest, liquidity constraints, and share scarcity—into a single, interpretable score.
However, its limitations, particularly the significant lag in short interest data, must be respected. The model does not predict the future; it assesses present vulnerability based on past data. It identifies stocks that are structurally primed for a squeeze, but it cannot forecast the timing or certainty of such an event.
Perhaps the model's most sophisticated application is not for speculators hunting for the next big gain, but as a risk management tool for short sellers themselves. By running this model on their own portfolio of short positions, they can receive an early warning when a stock's risk profile changes dramatically. A sudden spike in a stock's Squeeze Score, perhaps driven by a technical breakdown into oversold territory, can signal that the position has become significantly more dangerous, prompting a proactive reduction in size or the implementation of a hedge using call options.
Ultimately, the Squeeze Score should be used as one component of a broader analytical process, combining quantitative screening with a qualitative awareness of market catalysts and narratives. It is a tool for identifying where the financial system's inherent pressures are most concentrated, offering a map to potential zones of extreme volatility and opportunity.
Works cited
en.wikipedia.org, accessed July 12, 2025, https://en.wikipedia.org/wiki/Short_squeeze
Short squeeze | EBSCO Research Starters, accessed July 12, 2025, https://www.ebsco.com/research-starters/business-and-management/short-squeeze
Short Squeeze | Stock Market Definition + GME/AMC Examples - Wall Street Prep, accessed July 12, 2025, https://www.wallstreetprep.com/knowledge/short-squeeze/
What Is a Short Squeeze? Explanation and Examples - TIOmarkets, accessed July 12, 2025, https://tiomarkets.com/en/article/short-squeeze
How To Scan For Short Squeezes - The Three Rules You Should Know - Scanz, accessed July 12, 2025, https://scanz.com/how-to-scan-for-short-squeezes/
Short Squeeze Explained (2025): Meaning, Overview, and FAQs - The Trading Analyst, accessed July 12, 2025, https://thetradinganalyst.com/what-is-a-short-squeeze/
Short Squeeze: Identifying Vulnerable Stocks - Chase.com, accessed July 12, 2025, https://www.chase.com/personal/investments/learning-and-insights/article/what-is-a-short-squeeze
Short squeeze defined: Triggers, trading strategies, and risks, accessed July 12, 2025, https://onemoneyway.com/en/dictionary/short-squeeze/
What Is a Short Squeeze? Definition, Causes, and Examples - XS, accessed July 12, 2025, https://www.xs.com/en/blog/short-squeeze/
Short Squeeze Explained: Why It Happens and How It Works - Plus500, accessed July 12, 2025, https://www.plus500.com/en-bg/newsandmarketinsights/short-squeeze
Short Squeeze Meaning and Examples - Plus500, accessed July 12, 2025, https://www.plus500.com/en-bh/newsandmarketinsights/short-squeeze
Short Interest | Formula + Calculator - Wall Street Prep, accessed July 12, 2025, https://www.wallstreetprep.com/knowledge/short-interest/
Short Interest: What It Is, How It Works & Examples | Seeking Alpha, accessed July 12, 2025, https://seekingalpha.com/article/4450371-short-interest
Understanding Low-Float Stocks | SoFi, accessed July 12, 2025, https://www.sofi.com/learn/content/understanding-low-float-stocks/
What Is Short Interest and Why Does It Matter to Investors? | The Motley Fool, accessed July 12, 2025, https://www.fool.com/terms/s/short-interest/
How to spot a short squeeze - a guide for traders - ADSS, accessed July 12, 2025, https://www.adss.com/en/howtotrade/learn-how-to-spot-a-short-squeeze/
How to recognize a short squeeze in the market | FBS, accessed July 12, 2025, https://fbs.com/fbs-academy/traders-blog/how-to-recognize-a-short-squeeze-in-the-market
Short interest ratio - Wikipedia, accessed July 12, 2025, https://en.wikipedia.org/wiki/Short_interest_ratio
What Does Days to Cover Mean, and How Do Investors Use It? - Investopedia, accessed July 12, 2025, https://www.investopedia.com/terms/d/daystocover.asp
Days to Cover | Formula + Calculator - Wall Street Prep, accessed July 12, 2025, https://www.wallstreetprep.com/knowledge/days-to-cover/
Days to Cover and Stock Returns - National Bureau of Economic Research, accessed July 12, 2025, https://www.nber.org/system/files/working_papers/w21166/w21166.pdf
Days To Cover: Explained Simply | Blog - TradeZero, accessed July 12, 2025, https://tradezero.com/en-us/blog/days-to-cover-explained-simply
How to Recognize a Short Squeeze - CenterPoint Securities, accessed July 12, 2025, https://centerpointsecurities.com/how-to-recognize-a-short-squeeze/
Short Ratio Explained: Why It Changes The Game | Blog - TradeZero, accessed July 12, 2025, https://tradezero.com/en-us/blog/short-ratio-explained
What is the short interest ratio? - FOREX.com, accessed July 12, 2025, https://www.forex.com/en-ca/news-and-analysis/what-is-the-short-interest-ratio/
Low Float Stocks: 2 Key Factors to Consider Before Trading Them, accessed July 12, 2025, https://www.warriortrading.com/low-float-stocks/
www.ig.com, accessed July 12, 2025, https://www.ig.com/en/trading-strategies/what-is-a-stock-float-and-how-does-it-work--230623#:~:text=Because%20there%20are%20fewer%20shares,spread%20than%20high%20float%20stocks.
Days to Cover in Short Squeezes: Explanation and Importance - Tradingsim, accessed July 12, 2025, https://www.tradingsim.com/blog/days-to-cover
www.adss.com, accessed July 12, 2025, https://www.adss.com/en/howtotrade/learn-how-to-spot-a-short-squeeze/#:~:text=Signs%20of%20a%20Short%20Squeeze&text=These%20are%3A,the%20minimum%20short%20squeeze%20price.
yfinance documentation - GitHub Pages, accessed July 12, 2025, https://ranaroussi.github.io/yfinance/
Why yfinance Keeps Getting Blocked, and What to Use Instead | by Trading Dude - Medium, accessed July 12, 2025, https://medium.com/@trading.dude/why-yfinance-keeps-getting-blocked-and-what-to-use-instead-92d84bb2cc01
Short Interest Reporting | FINRA.org, accessed July 12, 2025, https://www.finra.org/filing-reporting/regulatory-filing-systems/short-interest
Where to get accurate timely data on short shares as % of float? : r/investing - Reddit, accessed July 12, 2025, https://www.reddit.com/r/investing/comments/1jp57ex/where_to_get_accurate_timely_data_on_short_shares/
Yahoo Finance FLOAT Anomaly explained with math : r/Superstonk - Reddit, accessed July 12, 2025, https://www.reddit.com/r/Superstonk/comments/pmlnwc/yahoo_finance_float_anomaly_explained_with_math/
Get the Float Size of a Stock with Yahoo Finance Data - eloquent code, accessed July 12, 2025, https://eloquentcode.com/get-the-float-size-of-a-stock-with-yahoo-finance-data
YFinance Python Package in a Spreadsheet - Row Zero, accessed July 12, 2025, https://rowzero.io/blog/yfinance
yfinance: 10 Ways to Get Stock Data with Python | by Kasper Junge - Medium, accessed July 12, 2025, https://medium.com/@kasperjuunge/yfinance-10-ways-to-get-stock-data-with-python-6677f49e8282
3 Secrets to Finding the Next Short-Squeeze Stocks - Nasdaq, accessed July 12, 2025, https://www.nasdaq.com/articles/3-secrets-to-finding-the-next-short-squeeze-stocks

