Model of valuation using DCF (built on streamlit) 

Employing Python and Streamlit, this project provides a completely interactive Discounted Cash Flow (DCF) valuation model. Using Yahoo Finance, the model dynamically retrieves financial data for **any public company** (e.g., MSFT, AAPL, GOOGL) and calculates the fair value per share depending on basic inputs and user-modifiable assumptions. 

Essential Characteristics 

- Enter any valid stock ticker (e.g., `MSFT`, `AAPL`, `TSLA`) via the sidebar. 
- Use `yfinance` and `pandas_datareader` for real-time financial data recovery. 
- Automatically computes: 
- Free Cash Flow to the Firm (FCFF) 
- Weighted Average Cost of Capital (WACC). 
- Terminal Value using Gordon Growth Model 
- Enterprise Value, Equity Value, and Fair Value per Share 
- Sidebar controls for: 
- Period for forecasts 
- FCFF development rate 
- Growth rate at a terminal 
- Markanalysis on combinations of WACC and terminal growth rate 
- Clear representations of historical and expected FCFF 

How to Run 
Needed is Python 3.9+. Dependencies should be installed through: 

```bash 
pip install -r requirements. txt