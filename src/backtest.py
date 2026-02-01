"""Backtesting module for Golden Cross strategy."""

import pandas as pd
import numpy as np
from dataclasses import dataclass
from datetime import datetime
import yfinance as yf


@dataclass
class Trade:
    """Represents a single trade."""
    ticker: str
    entry_date: datetime
    entry_price: float
    exit_date: datetime | None = None
    exit_price: float | None = None

    @property
    def return_pct(self) -> float | None:
        if self.exit_price is None:
            return None
        return (self.exit_price - self.entry_price) / self.entry_price * 100

    @property
    def is_winner(self) -> bool | None:
        if self.return_pct is None:
            return None
        return self.return_pct > 0


@dataclass
class BacktestResult:
    """Results of backtest."""
    ticker: str
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    avg_return: float
    total_return: float
    max_drawdown: float
    trades: list[Trade]


def get_sp500_tickers() -> list[str]:
    """Get S&P 500 ticker symbols."""
    url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
    try:
        tables = pd.read_html(url)
        df = tables[0]
        tickers = df['Symbol'].tolist()
        # Clean up tickers (replace . with -)
        tickers = [t.replace('.', '-') for t in tickers]
        return tickers
    except Exception as e:
        print(f"Error fetching S&P 500 list: {e}")
        # Fallback to major stocks
        return [
            "AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "TSLA", "BRK-B",
            "UNH", "JNJ", "JPM", "V", "PG", "XOM", "HD", "CVX", "MA", "ABBV",
            "MRK", "PFE", "KO", "PEP", "COST", "AVGO", "TMO", "MCD", "WMT",
            "CSCO", "ACN", "ABT", "DHR", "NEE", "LLY", "NKE", "TXN", "UPS"
        ]


def calculate_golden_cross_signals(df: pd.DataFrame) -> pd.DataFrame:
    """Calculate golden cross and dead cross signals."""
    df = df.copy()

    # Calculate SMAs
    df['SMA_25'] = df['Close'].rolling(window=25).mean()
    df['SMA_75'] = df['Close'].rolling(window=75).mean()

    # Golden cross: SMA_25 crosses above SMA_75
    df['golden_cross'] = (
        (df['SMA_25'] > df['SMA_75']) &
        (df['SMA_25'].shift(1) <= df['SMA_75'].shift(1))
    )

    # Dead cross: SMA_25 crosses below SMA_75
    df['dead_cross'] = (
        (df['SMA_25'] < df['SMA_75']) &
        (df['SMA_25'].shift(1) >= df['SMA_75'].shift(1))
    )

    return df


def run_backtest_single(ticker: str, period: str = "5y") -> BacktestResult | None:
    """Run backtest for a single ticker."""
    try:
        # Fetch data
        stock = yf.Ticker(ticker)
        df = stock.history(period=period)

        if df.empty or len(df) < 100:
            return None

        # Calculate signals
        df = calculate_golden_cross_signals(df)

        trades = []
        current_trade = None
        equity_curve = [100.0]  # Start with $100

        for date, row in df.iterrows():
            if pd.isna(row['SMA_25']) or pd.isna(row['SMA_75']):
                continue

            # Golden cross - BUY
            if row['golden_cross'] and current_trade is None:
                current_trade = Trade(
                    ticker=ticker,
                    entry_date=date,
                    entry_price=row['Close']
                )

            # Dead cross - SELL
            elif row['dead_cross'] and current_trade is not None:
                current_trade.exit_date = date
                current_trade.exit_price = row['Close']
                trades.append(current_trade)

                # Update equity
                ret = current_trade.return_pct / 100
                equity_curve.append(equity_curve[-1] * (1 + ret))

                current_trade = None

        # Close open trade at last price
        if current_trade is not None:
            current_trade.exit_date = df.index[-1]
            current_trade.exit_price = df['Close'].iloc[-1]
            trades.append(current_trade)
            ret = current_trade.return_pct / 100
            equity_curve.append(equity_curve[-1] * (1 + ret))

        if not trades:
            return None

        # Calculate metrics
        returns = [t.return_pct for t in trades if t.return_pct is not None]
        winning = [r for r in returns if r > 0]
        losing = [r for r in returns if r <= 0]

        # Max drawdown
        equity_series = pd.Series(equity_curve)
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max * 100
        max_drawdown = drawdown.min()

        return BacktestResult(
            ticker=ticker,
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            win_rate=len(winning) / len(trades) * 100 if trades else 0,
            avg_return=np.mean(returns) if returns else 0,
            total_return=(equity_curve[-1] / equity_curve[0] - 1) * 100,
            max_drawdown=max_drawdown,
            trades=trades
        )

    except Exception as e:
        print(f"Error backtesting {ticker}: {e}")
        return None


def run_backtest_portfolio(tickers: list[str], period: str = "5y", max_stocks: int = 50) -> dict:
    """Run backtest for multiple tickers."""
    results = []
    errors = 0

    # Limit number of stocks
    tickers = tickers[:max_stocks]

    print(f"Running backtest on {len(tickers)} stocks...")

    for i, ticker in enumerate(tickers):
        if (i + 1) % 10 == 0:
            print(f"  Progress: {i + 1}/{len(tickers)}")

        result = run_backtest_single(ticker, period)
        if result:
            results.append(result)
        else:
            errors += 1

    if not results:
        return {"error": "No valid results"}

    # Aggregate statistics
    all_trades = []
    for r in results:
        all_trades.extend(r.trades)

    all_returns = [t.return_pct for t in all_trades if t.return_pct is not None]
    winning_trades = [r for r in all_returns if r > 0]
    losing_trades = [r for r in all_returns if r <= 0]

    # Portfolio metrics
    avg_win_rate = np.mean([r.win_rate for r in results])
    avg_return = np.mean(all_returns) if all_returns else 0
    avg_max_dd = np.mean([r.max_drawdown for r in results])

    # Best and worst performers
    sorted_results = sorted(results, key=lambda x: x.total_return, reverse=True)

    return {
        "summary": {
            "stocks_analyzed": len(results),
            "stocks_with_errors": errors,
            "total_trades": len(all_trades),
            "winning_trades": len(winning_trades),
            "losing_trades": len(losing_trades),
            "overall_win_rate": len(winning_trades) / len(all_trades) * 100 if all_trades else 0,
            "avg_return_per_trade": avg_return,
            "avg_win_rate_per_stock": avg_win_rate,
            "avg_max_drawdown": avg_max_dd,
            "median_return": np.median(all_returns) if all_returns else 0,
            "std_return": np.std(all_returns) if all_returns else 0,
        },
        "best_performers": [
            {"ticker": r.ticker, "total_return": r.total_return, "win_rate": r.win_rate, "trades": r.total_trades}
            for r in sorted_results[:10]
        ],
        "worst_performers": [
            {"ticker": r.ticker, "total_return": r.total_return, "win_rate": r.win_rate, "trades": r.total_trades}
            for r in sorted_results[-10:]
        ],
        "all_results": results
    }


if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv()

    print("=" * 60)
    print("Golden Cross Backtest - S&P 500")
    print("=" * 60)
    print("Strategy: Buy on Golden Cross (SMA25 > SMA75)")
    print("          Sell on Dead Cross (SMA25 < SMA75)")
    print("Period: 5 years")
    print("=" * 60)

    # Get S&P 500 tickers
    print("\nFetching S&P 500 ticker list...")
    tickers = get_sp500_tickers()
    print(f"Found {len(tickers)} tickers")

    # Run backtest (limit to 50 for speed)
    print("\nRunning backtest (first 50 stocks)...")
    results = run_backtest_portfolio(tickers, period="5y", max_stocks=50)

    if "error" in results:
        print(f"Error: {results['error']}")
    else:
        summary = results["summary"]

        print("\n" + "=" * 60)
        print("RESULTS SUMMARY")
        print("=" * 60)
        print(f"Stocks Analyzed:     {summary['stocks_analyzed']}")
        print(f"Total Trades:        {summary['total_trades']}")
        print(f"Winning Trades:      {summary['winning_trades']}")
        print(f"Losing Trades:       {summary['losing_trades']}")
        print("-" * 60)
        print(f"Overall Win Rate:    {summary['overall_win_rate']:.1f}%")
        print(f"Avg Return/Trade:    {summary['avg_return_per_trade']:.2f}%")
        print(f"Median Return:       {summary['median_return']:.2f}%")
        print(f"Std Dev:             {summary['std_return']:.2f}%")
        print(f"Avg Max Drawdown:    {summary['avg_max_drawdown']:.2f}%")

        print("\n" + "-" * 60)
        print("TOP 10 PERFORMERS")
        print("-" * 60)
        for p in results["best_performers"]:
            print(f"  {p['ticker']:6s} | Return: {p['total_return']:+7.1f}% | Win Rate: {p['win_rate']:.0f}% | Trades: {p['trades']}")

        print("\n" + "-" * 60)
        print("BOTTOM 10 PERFORMERS")
        print("-" * 60)
        for p in results["worst_performers"]:
            print(f"  {p['ticker']:6s} | Return: {p['total_return']:+7.1f}% | Win Rate: {p['win_rate']:.0f}% | Trades: {p['trades']}")
