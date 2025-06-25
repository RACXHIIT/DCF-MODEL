import yfinance as yf
import pandas as pd
import numpy as np
import streamlit as st
import matplotlib.pyplot as plt
import pandas_datareader.data as web
from datetime import datetime

st.set_page_config(page_title="MSFT DCF Valuation", layout="wide")
ticker = st.sidebar.text_input("Enter Ticker Symbol", value="MSFT", max_chars=20).upper()

if ticker:
    try:
        st.title(f"{ticker} DCF Valuation Model")
        st.markdown(
            f"""
            This Program performs a Discounted Cash Flow (DCF) valuation for **{ticker}** using financial data from Yahoo Finance.
            Adjust the assumptions in the sidebar and observe how the valuation changes.
            """
        )

        st.sidebar.header("Assumptions & Parameters")

        forecast_years = st.sidebar.slider("Forecast Years", 5, 15, 10, help="Number of years to forecast FCFF")
        fcff_growth_rate = st.sidebar.slider("FCFF Growth Rate (%)", 0.0, 30.0, 14.0, help="Annual growth rate for FCFF during forecast period") / 100
        terminal_growth_rate = st.sidebar.slider("Terminal Growth Rate (%)", 0.0, 10.0, 5.0, help="Perpetual growth rate after forecast period") / 100

        beta = st.sidebar.number_input("Beta", value=1.0, min_value=0.0, step=0.01, help="Stock beta for cost of equity calculation")
        market_return = st.sidebar.number_input("Market Return (%)", value=9.0, min_value=0.0, step=0.1, help="Expected market return") / 100

        st.sidebar.markdown("---")
        st.sidebar.write("Note: Risk-free rate is pulled from the 10-Year Treasury yield (FRED)")

        # --- Data Fetching and Processing ---
        with st.spinner("Fetching financial data..."):

            msft = yf.Ticker(ticker)
            info = msft.info

            # Financial statements
            income_stmt = msft.financials.T / 1e9
            balance_sheet = msft.balance_sheet.T / 1e9
            cash_flow = msft.cash_flow.T / 1e9

            cfo = cash_flow['Cash Flow From Continuing Operating Activities']
            capex = cash_flow['Capital Expenditure']
            fcff = cfo + capex

            fcff_df = pd.DataFrame({
                "Cash From Operations": cfo,
                "Capex": capex,
                "Free Cash Flow To The Firm": fcff
            })
            fcff_df.sort_index(ascending=True, inplace=True)
            fcff_df.dropna(how="any", inplace=True)

            # Base FCFF - average last 3 years for stability
            base_fcff = fcff_df['Free Cash Flow To The Firm'].tail(3).mean()

            last_year = pd.to_datetime(fcff_df.index[-1]).year
            forecast_years_range = list(range(last_year + 1, last_year + 1 + forecast_years))

            projected_fcff = [base_fcff * (1 + fcff_growth_rate) ** i for i in range(1, forecast_years + 1)]
            projection_df = pd.DataFrame({
                "Year": forecast_years_range,
                "Projected FCFF": projected_fcff
            }).set_index("Year")

            # Risk free rate from FRED
            risk_free_rate = web.DataReader('DGS10', 'fred', start='2023-01-01', end=datetime.today()).dropna().iloc[-1, 0] / 100

            market_cap = info["marketCap"] / 1e9
            total_debt = info.get('totalDebt', 0) / 1e9
            cash = info.get('totalCash', 0) / 1e9
            net_debt = total_debt - cash

            # Cost of debt calculation
            interest_expense = abs(income_stmt['Interest Expense'].dropna().iloc[-1]) if total_debt > 0 else 0
            cost_of_debt = interest_expense / total_debt if total_debt > 0 else 0.02  # assume 2% if no debt info

            tax_rate = 0.21
            cost_of_equity = risk_free_rate + beta * (market_return - risk_free_rate)

            total_value = market_cap + net_debt
            equity_weight = market_cap / total_value if total_value != 0 else 1
            debt_weight = net_debt / total_value if total_value != 0 else 0

            wacc = (equity_weight * cost_of_equity) + (debt_weight * cost_of_debt * (1 - tax_rate))

            # Discount projected FCFFs
            discounted_fcffs = [fcff / ((1 + wacc) ** i) for i, fcff in enumerate(projection_df['Projected FCFF'], start=1)]

            # Terminal value calculation and discounting
            terminal_value = projected_fcff[-1] * (1 + terminal_growth_rate) / (wacc - terminal_growth_rate)
            terminal_value_discounted = terminal_value / ((1 + wacc) ** forecast_years)

            enterprise_value = sum(discounted_fcffs) + terminal_value_discounted
            equity_value = enterprise_value - net_debt
            shares_outstanding = info['sharesOutstanding']
            fair_value_per_share = (equity_value * 1e9) / shares_outstanding

        # --- Display Financial Summary ---
        st.subheader("Key Financial Inputs")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Market Cap (B)", f"${market_cap:.2f}")
            st.metric("Total Debt (B)", f"${total_debt:.2f}")
            st.metric("Total Cash (B)", f"${cash:.2f}")
            if net_debt >= 0:
                st.metric("Net Debt (B)", f"${net_debt:.2f}")
            else:
                st.metric("Net Debt", "O(Excess Cash)")

            st.metric("Interest Expense (B)", f"${interest_expense:.2f}")
        with col2:
            st.metric("Beta", f"{beta:.2f}")
            st.metric("Risk-Free Rate", f"{risk_free_rate*100:.2f}%")
            st.metric("Market Return", f"{market_return*100:.2f}%")
            st.metric("Cost of Debt", f"{cost_of_debt*100:.2f}%")
            st.metric("Cost of Equity", f"{cost_of_equity*100:.2f}%")
            st.metric("WACC", f"{wacc*100:.2f}%")

        st.markdown("---")

        # --- Valuation Results ---
        st.subheader("Valuation Results")
        st.write(f"**Forecast Period:** {forecast_years} years")
        st.write(f"**FCFF Growth Rate:** {fcff_growth_rate*100:.2f}%")
        st.write(f"**Terminal Growth Rate:** {terminal_growth_rate*100:.2f}%")

        st.metric("Enterprise Value (in Billions)", f"${enterprise_value:.2f}")
        st.metric("Equity Value (in Billions)", f"${equity_value:.2f}")
        st.metric("Fair Value per Share", f"${fair_value_per_share:.2f}")

        st.markdown("---")

        # --- Plot Historical + Projected FCFF ---
        historical_fcff = fcff_df["Free Cash Flow To The Firm"].tail(3)
        historical_fcff.index = pd.to_datetime(historical_fcff.index).year
        combined_fcff = pd.concat([historical_fcff, projection_df["Projected FCFF"]])

        st.subheader("Historical & Projected FCFF")
        fig, ax = plt.subplots(figsize=(10, 5))
        combined_fcff.plot(marker='o', ax=ax)
        ax.set_title('Free Cash Flow to Firm (FCFF)')
        ax.set_ylabel('FCFF (in Billions USD)')
        ax.set_xlabel('Year')
        ax.grid(True)
        plt.xticks(rotation=45)
        st.pyplot(fig)

        st.markdown("---")

        # --- Sensitivity Analysis ---
        st.subheader("Sensitivity Analysis")

        wacc_range = np.arange(wacc - 0.01, wacc + 0.015, 0.005)
        g_range = np.arange(0.035, 0.06, 0.005)

        sensitivity_df = pd.DataFrame(index=[f"{round(w*100,1)}%" for w in wacc_range],
                                    columns=[f"{round(g*100,1)}%" for g in g_range])

        for w in wacc_range:
            for g in g_range:
                if w <= g:
                    sensitivity_df.loc[f"{round(w*100,1)}%", f"{round(g*100,1)}%"] = "N/A"
                    continue
                tv = projected_fcff[-1] * (1 + g) / (w - g)
                tv_disc = tv / ((1 + w) ** forecast_years)
                ent_val = sum([
                    fcff / ((1 + w) ** i) for i, fcff in enumerate(projection_df["Projected FCFF"], start=1)
                ]) + tv_disc
                eq_val = ent_val - net_debt
                fair_price = (eq_val * 1e9) / shares_outstanding
                sensitivity_df.loc[f"{round(w*100,1)}%", f"{round(g*100,1)}%"] = round(fair_price, 2)

        st.dataframe(sensitivity_df)

    except Exception as e:
        st.error(f"⚠️ Error fetching data for {ticker} on Yfinance:" + "  Please Enter Another Stock ")
    st.markdown("---")
st.caption("Built by Rachit | Powered by Python, Streamlit, yFinance, FRED")

