# 👇 强制安装缺少的库（魔法代码）
import subprocess
import sys
subprocess.check_call([sys.executable, "-m", "pip", "install", "pytz"])

# 然后才是你的其他 import
from dotenv import load_dotenv
load_dotenv()
import pytz


import feedparser
import urllib.parse
import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime, timedelta
import os


API_KEY = os.getenv("ALPACA_API_KEY")
SECRET_KEY = os.getenv("ALPACA_API_SECRET")
BASE_URL = "https://paper-api.alpaca.markets"



def search_news(firm_name: str, limit: int = 10) -> list:
    """
    Searches for news from Google News RSS and returns parsed data.

    Args:
        firm_name (str): The key word to search for.
        limit (int): The maximum number of news items to return. Default is 10.
    Returns:
        list: A list of dictionaries containing news entries with timestamp, title, and link.
    """
    # URL encode the firm name to handle spaces and special characters
    encoded_firm_name = urllib.parse.quote(firm_name)
    
    # Construct the RSS URL with properly encoded firm name
    rss_url = f"https://news.google.com/rss/search?q={encoded_firm_name}&hl=en-US&gl=US&ceid=US:en"
    
    print(f"Searching news for: {firm_name}")
    print(f"RSS URL: {rss_url}")
    
    try:
        # Parse RSS feed
        feed = feedparser.parse(rss_url)
        
        # Extract and return relevant fields as needed
        news_entries = []
        for entry in feed.entries[:limit]:
            news_item = {
                "timestamp": entry.get("published", "N/A"),
                "title": entry.get("title", "N/A"),
                "link": entry.get("link", "N/A")
            }
            news_entries.append(news_item)
        
        return news_entries
    
    except Exception as e:
        print(f"Error fetching news: {e}")
        return []





api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

def get_historical_bars(symbol, timeframe='1D', limit=100, use_iex=True):
    """
    Retrieve historical stock data from Alpaca API.
    
    Args:
        symbol (str): Stock ticker symbol (e.g., 'AAPL', 'TSLA')
        timeframe (str): Candle timeframe ('1Min', '5Min', '15Min', '1H', '1D')
        limit (int): Number of bars to retrieve (default: 100)
        use_iex (bool): Use IEX data source (free) instead of SIP (premium)
    
    Returns:
        pd.DataFrame: DataFrame with OHLCV data, indexed by timestamp
                     Columns: open, high, low, close, volume, vwap, trade_count
                     Returns None if request fails
    
    Raises:
        APIError: If API request fails or subscription doesn't permit data access
    
    Example:
        >>> df = get_historical_bars('AAPL', timeframe='1D', limit=100)
        >>> print(df.head())
        >>> print(f"Shape: {df.shape}")
    """
    
    api = tradeapi.REST(API_KEY, SECRET_KEY, BASE_URL, api_version='v2')

    try:
        # Set timezone to US Eastern Time
        et = pytz.timezone('US/Eastern')
        
        # Calculate end time (start from yesterday to avoid real-time data restrictions)
        end = datetime.now(et) - timedelta(days=1)
        
        # Calculate start time based on timeframe
        if timeframe == '1D':
            start = end - timedelta(days=limit)
        elif timeframe == '1H':
            start = end - timedelta(hours=limit)
        elif timeframe == '5Min':
            start = end - timedelta(minutes=limit * 5)
        elif timeframe == '15Min':
            start = end - timedelta(minutes=limit * 15)
        else:
            start = end - timedelta(days=limit)
        
        # Log request details
        print(f"📅 Time Range: {start.date()} to {end.date()}")
        print(f"⏱️  Timeframe: {timeframe}")
        print(f"📊 Requesting: {limit} bars")
        
        # Build API parameters
        params = {
            'start': start.isoformat(),
            'end': end.isoformat(),
            'limit': limit,
            'adjustment': 'raw'
        }
        
        # Add data source parameter
        if use_iex:
            params['feed'] = 'iex'
            print("🔗 Data Source: IEX (Free - 15 min delayed)")
        else:
            print("🔗 Data Source: SIP (Premium - Real-time)")
        
        # Fetch bars from API
        bars = api.get_bars(symbol, timeframe, **params)
        
        # Check if data was returned
        if len(bars) == 0:
            print("⚠️  Warning: No data returned from API!")
            return None
        
        # Convert bars to DataFrame
        df = pd.DataFrame([{
            'timestamp': bar.t,
            'open': bar.o,
            'high': bar.h,
            'low': bar.l,
            'close': bar.c,
            'volume': bar.v,
            'vwap': bar.vw if hasattr(bar, 'vw') else None,
            'trade_count': bar.n if hasattr(bar, 'n') else None
        } for bar in bars])
        
        # Process DataFrame
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.set_index('timestamp')
        
        # Sort by timestamp (oldest first)
        df = df.sort_index()
        
        # Log success
        print(f"✅ Successfully retrieved {symbol}: {len(df)} bars")
        print(f"📊 Date Range: {df.index.min().date()} to {df.index.max().date()}")
        
        return df
    
    except Exception as e:
        error_type = type(e).__name__
        error_msg = str(e)
        
        print(f"❌ Error: {error_type}")
        print(f"💬 Message: {error_msg}")
        
        # Automatic fallback: retry with IEX if SIP subscription error
        if "subscription does not permit" in error_msg.lower() and use_iex == False:
            print("\n🔄 Retrying with IEX data source...\n")
            return get_historical_bars(symbol, timeframe, limit, use_iex=True)
        
        return None


def analyze_stock_data(df, symbol):
    """
    Perform basic technical analysis on stock data.
    
    Args:
        df (pd.DataFrame): DataFrame with OHLCV data
        symbol (str): Stock ticker symbol
    
    Returns:
        dict: Dictionary containing analysis metrics
    """
    
    if df is None or df.empty:
        print(f"❌ No data available for {symbol}")
        return None
    
    analysis = {
        'symbol': symbol,
        'data_points': len(df),
        'date_range': {
            'start': df.index.min().date(),
            'end': df.index.max().date()
        },
        'price_stats': {
            'current_close': df['close'].iloc[-1],
            'highest': df['high'].max(),
            'lowest': df['low'].min(),
            'avg_price': df['close'].mean(),
        },
        'volume_stats': {
            'total_volume': df['volume'].sum(),
            'avg_volume': df['volume'].mean(),
            'max_volume': df['volume'].max(),
        },
        'performance': {
            'price_change': df['close'].iloc[-1] - df['close'].iloc[0],
            'price_change_pct': ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100,
        }
    }
    
    return analysis


def print_analysis(analysis):
    """
    Print formatted stock analysis report AND return the full text output.
    
    Args:
        analysis (dict): Analysis metrics dictionary
        
    Returns:
        str: The full formatted report text (for LLM tool response)
    """
    
    if analysis is None:
        return "No analysis data available."

    # 先把所有要输出的内容拼成字符串
    output = []
    output.append("\n" + "="*70)
    output.append(f"📈 STOCK ANALYSIS REPORT: {analysis['symbol']}")
    output.append("="*70)
    
    output.append(f"\n📊 Data Overview:")
    output.append(f"   • Data Points: {analysis['data_points']}")
    output.append(f"   • Date Range: {analysis['date_range']['start']} to {analysis['date_range']['end']}")
    
    output.append(f"\n💰 Price Statistics:")
    output.append(f"   • Current Close: ${analysis['price_stats']['current_close']:.2f}")
    output.append(f"   • Highest: ${analysis['price_stats']['highest']:.2f}")
    output.append(f"   • Lowest: ${analysis['price_stats']['lowest']:.2f}")
    output.append(f"   • Average: ${analysis['price_stats']['avg_price']:.2f}")
    
    output.append(f"\n📉 Volume Statistics:")
    output.append(f"   • Total Volume: {analysis['volume_stats']['total_volume']:,.0f}")
    output.append(f"   • Average Volume: {analysis['volume_stats']['avg_volume']:,.0f}")
    output.append(f"   • Max Volume: {analysis['volume_stats']['max_volume']:,.0f}")
    
    price_change = analysis['performance']['price_change']
    price_change_pct = analysis['performance']['price_change_pct']
    direction = "📈 UP" if price_change >= 0 else "📉 DOWN"
    
    output.append(f"\n{direction} Performance:")
    output.append(f"   • Price Change: ${price_change:.2f}")
    output.append(f"   • Percentage Change: {price_change_pct:.2f}%")
    
    output.append("\n" + "="*70 + "\n")

    # 合并成一段文本
    final_text = "\n".join(output)
    
    # 打印（保持原来的行为）
    print(final_text)
    
    # ✅ 关键：返回打印出来的内容，而不是对象
    return final_text




from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    MarketOrderRequest,
    LimitOrderRequest,
    StopOrderRequest,
    StopLimitOrderRequest,
    TrailingStopOrderRequest,
    GetOrdersRequest,
    ClosePositionRequest
)
from alpaca.trading.enums import (
    OrderSide,
    TimeInForce,
    OrderStatus,
    AssetClass
)
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockLatestQuoteRequest, StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from datetime import datetime, timedelta
import pandas as pd

# ─────────────────────────────────────────────
#  API Credentials (use environment variables!)

# paper=True  → Paper trading (sandbox)
# paper=False → Live trading  ⚠️ Real money!
trading_client = TradingClient(API_KEY, SECRET_KEY, paper=True)
data_client    = StockHistoricalDataClient(API_KEY, SECRET_KEY)




def get_account_info():
    """Retrieve and display full account information."""
    account = trading_client.get_account()
    res = ""

    res += "=" * 50 +'\n'
    res += ("        📊 ACCOUNT INFORMATION") +'\n'
    res += ("=" * 50) +'\n'
    res += (f"  Account ID       : {account.id}") +'\n'
    res += (f"  Account Status   : {account.status}") +'\n'
    res += (f"  Currency         : {account.currency}") +'\n'
    res += (f"  Cash             : ${float(account.cash):>12,.2f}") +'\n'
    res += (f"  Portfolio Value  : ${float(account.portfolio_value):>12,.2f}") +'\n'
    res += (f"  Buying Power     : ${float(account.buying_power):>12,.2f}") +'\n'
    res += (f"  Equity           : ${float(account.equity):>12,.2f}") +'\n'
    res += (f"  Last Equity      : ${float(account.last_equity):>12,.2f}") +'\n'
    res += (f"  P&L Today        : ${float(account.equity) - float(account.last_equity):>+12,.2f}") +'\n'
    res += (f"  Day Trade Count  : {account.daytrade_count}") +'\n'
    res += (f"  Pattern Day Trader: {account.pattern_day_trader}") +'\n'
    res += (f"  Trading Blocked  : {account.trading_blocked}") +'\n'
    res += (f"  Transfers Blocked: {account.transfers_blocked}") +'\n'
    res += ("=" * 50)
    print(res)
    return res

def get_all_positions():
    """Retrieve and display all open positions — returns printable text for LLM."""
    positions = trading_client.get_all_positions()

    output = []
    
    if not positions:
        text = "📭 No open positions."
        print(text)
        return text

    # 开始构建输出文本
    output.append("\n" + "=" * 75)
    output.append("                        📂 OPEN POSITIONS")
    output.append("=" * 75)
    output.append(f"  {'Symbol':<8} {'Qty':>8} {'Avg Entry':>12} {'Curr Price':>12} "
                  f"{'Market Val':>14} {'P&L':>12} {'P&L %':>8}")
    output.append("-" * 75)

    for pos in positions:
        pnl       = float(pos.unrealized_pl)
        pnl_pct   = float(pos.unrealized_plpc) * 100
        pnl_icon  = "🟢" if pnl >= 0 else "🔴"
        
        line = (f"  {pos.symbol:<8} "
                f"{float(pos.qty):>8.4f} "
                f"${float(pos.avg_entry_price):>11,.2f} "
                f"${float(pos.current_price):>11,.2f} "
                f"${float(pos.market_value):>13,.2f} "
                f"{pnl_icon}${pnl:>+10,.2f} "
                f"{pnl_pct:>+7.2f}%")
        output.append(line)

    output.append("=" * 75)
    
    final_text = "\n".join(output)
    
    print(final_text)
    
    return final_text


def place_market_order(symbol: str, qty: float, side: str = "buy"):
    """
    Place a market order.
    side: 'buy' or 'sell'
    Returns formatted text (not order object) for LLM tool use.
    """
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    request = MarketOrderRequest(
        symbol       = symbol,
        qty          = qty,
        side         = order_side,
        time_in_force= TimeInForce.DAY
    )

    order = trading_client.submit_order(request)

    # 构建输出文本
    output = []
    output.append(f"\n✅ Market Order Placed!")
    output.append(f"   ID     : {order.id}")
    output.append(f"   Symbol : {order.symbol}")
    output.append(f"   Side   : {order.side}")
    output.append(f"   Qty    : {order.qty}")
    output.append(f"   Status : {order.status}")
    
    # 合并成文本
    final_text = "\n".join(output)
    
    # 打印（保持原来显示）
    print(final_text)
    
    # ✅ 返回文本，不返回 ORDER 对象！
    return final_text


def place_stop_order(symbol: str, qty: float, stop_price: float, side: str = "sell"):
    """
    Place a stop order (stop-loss).
    Triggers a market order once stop_price is reached.
    Returns formatted text for LLM tool use.
    """
    order_side = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL

    request = StopOrderRequest(
        symbol        = symbol,
        qty           = qty,
        side          = order_side,
        time_in_force = TimeInForce.GTC,
        stop_price    = stop_price
    )

    order = trading_client.submit_order(request)
    
    output = []
    output.append(f"\n✅ Stop Order Placed!")
    output.append(f"   ID         : {order.id}")
    output.append(f"   Symbol     : {order.symbol}")
    output.append(f"   Stop Price : ${stop_price:,.2f}")
    output.append(f"   Status     : {order.status}")
    
    final_text = "\n".join(output)
    
    print(final_text)
    
    return final_text


def cancel_all_orders():
    """Cancel ALL open orders."""
    try:
        trading_client.cancel_orders()
        print("🚫 All open orders cancelled.")
    except Exception as e:
        print(f"❌ Error cancelling orders: {e}")


def get_latest_quote(symbol: str):
    """Get real-time quote for a symbol."""
    request = StockLatestQuoteRequest(symbol_or_symbols=symbol)
    quote   = data_client.get_stock_latest_quote(request)[symbol]

    output = []
    output.append(f"\n📈 Latest Quote — {symbol}")
    output.append(f"   Ask Price : ${float(quote.ask_price):,.2f}  (Size: {quote.ask_size})")
    output.append(f"   Bid Price : ${float(quote.bid_price):,.2f}  (Size: {quote.bid_size})")
    output.append(f"   Spread    : ${float(quote.ask_price) - float(quote.bid_price):,.4f}")
    output.append(f"   Timestamp : {quote.timestamp}")
    
    final_text = "\n".join(output)
    
    print(final_text)
    
    return final_text


