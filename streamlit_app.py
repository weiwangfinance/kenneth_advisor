import streamlit as st
import pandas as pd
import numpy as np
import json
import random
import time
import os
from dotenv import load_dotenv
load_dotenv()  # read .env

from util_app import search_news, get_historical_bars, analyze_stock_data, print_analysis, get_account_info, get_all_positions, place_market_order, place_stop_order, cancel_all_orders, get_latest_quote    


import alpaca_trade_api as tradeapi
import pandas as pd
from datetime import datetime, timedelta
import pytz

# ============ 配置 ============

BASE_URL = "https://paper-api.alpaca.markets"



st.set_page_config(
    page_title="AI Investment Advisor",
    page_icon="📈",
    layout="wide"
)


from openai import OpenAI


client = OpenAI(
    api_key= os.getenv("GLM_API_KEY"), # Fill your own api key
    base_url="https://open.bigmodel.cn/api/paas/v4",
)

def send_messages(messages):
    response = client.chat.completions.create(
        model="GLM-4.5-Flash", 
        messages=messages,
        tools=tools,  
        tool_choice="auto"
    )
    return response.choices[0].message


tools = [
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": "Searches for news from Google News RSS feed and returns parsed data including timestamp, title, and link.",
            "parameters": {
                "type": "object",
                "properties": {
                    "firm_name": {
                        "type": "string",
                        "description": "The keyword to search for in news articles."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "The maximum number of news items to return. Default is 10, maximum is 30.",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 30
                    }
                },
                "required": ["firm_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "print_analysis",
            "description": "Prints a formatted stock analysis report to the console from a structured analysis metrics dictionary. Displays data overview, price statistics, volume statistics, and performance metrics including price change and percentage change with directional indicators.",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis": {
                        "type": "object",
                        "description": "Analysis metrics dictionary containing stock data. Pass null to skip printing.",
                        "nullable": True,
                        "properties": {
                            "symbol": {
                                "type": "string",
                                "description": "The stock ticker symbol (e.g., 'AAPL', 'TSLA')."
                            },
                            "data_points": {
                                "type": "integer",
                                "description": "The number of data points used in the analysis.",
                                "minimum": 1
                            },
                            "date_range": {
                                "type": "object",
                                "description": "The date range of the data used in the analysis.",
                                "properties": {
                                    "start": {
                                        "type": "string",
                                        "description": "Start date in YYYY-MM-DD format."
                                    },
                                    "end": {
                                        "type": "string",
                                        "description": "End date in YYYY-MM-DD format."
                                    }
                                },
                                "required": ["start", "end"]
                            },
                            "price_stats": {
                                "type": "object",
                                "description": "Statistical summary of stock price data.",
                                "properties": {
                                    "current_close": {
                                        "type": "number",
                                        "description": "Most recent closing price in USD."
                                    },
                                    "highest": {
                                        "type": "number",
                                        "description": "Highest closing price in the period in USD."
                                    },
                                    "lowest": {
                                        "type": "number",
                                        "description": "Lowest closing price in the period in USD."
                                    },
                                    "avg_price": {
                                        "type": "number",
                                        "description": "Average closing price over the period in USD."
                                    }
                                },
                                "required": ["current_close", "highest", "lowest", "avg_price"]
                            },
                            "volume_stats": {
                                "type": "object",
                                "description": "Statistical summary of trading volume.",
                                "properties": {
                                    "total_volume": {
                                        "type": "number",
                                        "description": "Total cumulative volume over the period."
                                    },
                                    "avg_volume": {
                                        "type": "number",
                                        "description": "Average daily volume over the period."
                                    },
                                    "max_volume": {
                                        "type": "number",
                                        "description": "Highest single-day volume in the period."
                                    }
                                },
                                "required": ["total_volume", "avg_volume", "max_volume"]
                            },
                            "performance": {
                                "type": "object",
                                "description": "Performance metrics over the analysis period.",
                                "properties": {
                                    "price_change": {
                                        "type": "number",
                                        "description": "Absolute price change in USD from start to end."
                                    },
                                    "price_change_pct": {
                                        "type": "number",
                                        "description": "Percentage price change from start to end."
                                    }
                                },
                                "required": ["price_change", "price_change_pct"]
                            }
                        },
                        "required": [
                            "symbol", "data_points", "date_range",
                            "price_stats", "volume_stats", "performance"
                        ]
                    }
                },
                "required": ["analysis"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_account_info",
            "description": "Retrieve and display full trading account information including balance, equity, P&L, buying power, and account statuses.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
    "type": "function",
    "function": {
        "name": "get_all_positions",
        "description": "Retrieve and display all current open trading positions with symbol, quantity, entry price, current price, market value, and unrealized P&L.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
    },
    {
    "type": "function",
    "function": {
        "name": "place_market_order",
        "description": "Place a market order to buy or sell a stock. Supports 'buy' or 'sell' side with specified quantity. Order is DAY time-in-force.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, MSFT)"
                },
                "qty": {
                    "type": "number",
                    "description": "Number of shares to buy or sell"
                },
                "side": {
                    "type": "string",
                    "description": "Order side: 'buy' or 'sell'",
                    "enum": ["buy", "sell"],
                    "default": "buy"
                }
            },
            "required": ["symbol", "qty"]
        }
    }
    },
   
    {
    "type": "function",
    "function": {
        "name": "place_stop_order",
        "description": "Place a stop-loss order. Triggers a market order when the stop price is reached. Uses GTC (Good Till Cancelled) time-in-force.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, TSLA)"
                },
                "qty": {
                    "type": "number",
                    "description": "Number of shares for the stop order"
                },
                "stop_price": {
                    "type": "number",
                    "description": "Price at which the stop order triggers"
                },
                "side": {
                    "type": "string",
                    "description": "Order side: buy or sell (default sell for stop-loss)",
                    "enum": ["buy", "sell"],
                    "default": "sell"
                }
            },
            "required": ["symbol", "qty", "stop_price"]
        }
    }
},
    {
    "type": "function",
    "function": {
        "name": "cancel_all_orders",
        "description": "Cancel ALL currently open orders in the trading account.",
        "parameters": {
            "type": "object",
            "properties": {},
            "required": []
        }
    }
},
{
    "type": "function",
    "function": {
        "name": "get_latest_quote",
        "description": "Get real-time stock quote including ask price, bid price, spread, and timestamp for a given symbol.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "Stock ticker symbol (e.g., AAPL, MSFT, TSLA)"
                }
            },
            "required": ["symbol"]
        }
    }
}
    
]

TOOLS = {
    "search_news": search_news,
    "print_analysis": print_analysis,
    "get_account_info": get_account_info,
    "get_all_positions": get_all_positions,
    "place_market_order": place_market_order,
    "place_stop_order": place_stop_order,
    "cancel_all_orders": cancel_all_orders,
    "get_latest_quote": get_latest_quote
}


import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd

st.title("📊 AI Investment Advisor Dashboard")
st.markdown("---")

st.subheader("Stock Price  (Real Data)")

# 你可以选择的股票
stock_list = ["AAPL", "TSLA", "MSFT", "NVDA", "AMZN", "GOOG", "META", "NFLX"]
benchmark_symbol = "SPY"  # 标普500

with st.container(border=True):
    selected_stock = st.selectbox("Select a stock", stock_list)
    rolling_average = st.toggle("Rolling average (MA7)")



try:
    df = get_historical_bars(selected_stock, '1D', 100, use_iex=True)
    if df is None:
        st.error("No data from API")
        st.stop()



    df['MA20'] = df['close'].rolling(20).mean()
    df['MA60'] = df['close'].rolling(60).mean()

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))

    # MACD
    ema12 = df['close'].ewm(span=12, adjust=False).mean()
    ema26 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = ema12 - ema26
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()

    # ======================
    # K bar + RSI + MACD
    # ======================
    fig = make_subplots(
        rows=3, cols=1,
        row_heights=[0.5, 0.25, 0.25],
        shared_xaxes=True,
        vertical_spacing=0.05
    )

    # 1. K线
    fig.add_trace(go.Candlestick(
        x=df.index, open=df.open, high=df.high, low=df.low, close=df.close,
        name=selected_stock,
        increasing_line_color='#26a69a', decreasing_line_color='#ef4444'
    ), row=1, col=1)

    # MA
    fig.add_trace(go.Scatter(x=df.index, y=df.MA20, line=dict(width=1.5), name="MA20"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.MA60, line=dict(width=1.5), name="MA60"), row=1, col=1)

    # 2. RSI
    fig.add_trace(go.Scatter(x=df.index, y=df.RSI, line=dict(color='#6366f1', width=2), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", line_color="#ef4444", row=2, col=1)
    fig.add_hline(y=30, line_dash="dot", line_color="#26a69a", row=2, col=1)

    # 3. MACD
    fig.add_trace(go.Scatter(x=df.index, y=df.MACD, line=dict(color='#2563eb', width=2), name="MACD"), row=3, col=1)
    fig.add_trace(go.Scatter(x=df.index, y=df.Signal, line=dict(color='#f59e0b', width=2), name="Signal"), row=3, col=1)


    fig.update_layout(
        height=520,
        template="plotly_white",
        margin=dict(l=10, r=10, t=10, b=10),
        xaxis_rangeslider_visible=False
    )

    st.plotly_chart(fig, use_container_width=True)

  
    with st.expander("Show Data"):
        st.dataframe(df.round(2), use_container_width=True)

except Exception as e:
    st.error(f"Error: {str(e)}")

st.markdown("---")


st.subheader("🤖 AI Stock Assistant (GLM-4.5-Flash)")

# 
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "system", "content": "You are a professional stock trading assistant. You can use trading tools."},
        {"role": "assistant", "content": "Hello! I'm your AI investment advisor. How can I help you today?"}
    ]

# 
for message in st.session_state.messages:
    # 
    if isinstance(message, dict):
        role = message["role"]
        content = message["content"]
    else:
        role = message.role
        content = message.content or ""

    if role != "system":
        with st.chat_message(role):
            st.markdown(content)

if prompt := st.chat_input("Ask me to analyze stocks, check positions, place orders..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        placeholder = st.empty()
        placeholder.markdown("🤔 Thinking...")

        while True:
            response_msg = send_messages(st.session_state.messages)
            st.session_state.messages.append(response_msg)

    
            if response_msg.tool_calls:
                tool_call = response_msg.tool_calls[0]
                tool_name = tool_call.function.name
                tool_args = json.loads(tool_call.function.arguments)

                placeholder.markdown(f"🧵 Calling tool: **{tool_name}**...")

                try:
                    tool_func = TOOLS[tool_name]
                    result = tool_func(**tool_args)
                except Exception as e:
                    result = f"Tool error: {str(e)}"

                st.session_state.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": json.dumps(result, ensure_ascii=False)
                })

 
            else:
                final_answer = response_msg.content or "No response."
                placeholder.markdown(final_answer)
                break

    st.rerun()