# HFT Live Visualization & Decisioning Dashboard
## Implementation Plan (Blueprint Document)

---

## Table of Contents
1. [Architecture Overview](#1-architecture-overview)
2. [Component Breakdown](#2-component-breakdown)
3. [API/Data Contracts](#3-apidata-contracts)
4. [State Schema](#4-state-schema)
5. [Feature Calculations](#5-feature-calculations)
6. [Rule Engine Logic](#6-rule-engine-logic)
7. [UI Layout](#7-ui-layout)
8. [Docker Setup](#8-docker-setup)
9. [Development Phases](#9-development-phases)
10. [Testing Checklist](#10-testing-checklist)
11. [Risk Mitigation](#11-risk-mitigation)

---

## 1. Architecture Overview

### System Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           BINANCE WEBSOCKET                                  │
│  wss://stream.binance.com:9443/ws/btcusdt@trade                             │
│  wss://stream.binance.com:9443/ws/btcusdt@depth10@100ms                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         WEBSOCKET HANDLER                                    │
│  • Async connection management                                               │
│  • Auto-reconnection with exponential backoff                               │
│  • Message parsing and validation                                            │
│  • Thread-safe data push to State Manager                                    │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STATE MANAGER                                       │
│  • Circular buffers (collections.deque)                                      │
│  • Thread-safe access (threading.Lock)                                       │
│  • Buffers: trades, depth, prices, spreads, volatility                      │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         FEATURE ENGINE                                       │
│  • Real-time calculations: Mid Price, Spread, VWAP                          │
│  • Derived metrics: Imbalance, Velocity, Volatility                         │
│  • Rolling windows with timestamp-based filtering                            │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         DECISION LAYER                                       │
│  ┌─────────────────────┐     ┌─────────────────────┐                        │
│  │    Rule Engine      │────▶│  Insight Generator  │                        │
│  │  (10 trading rules) │     │  (Priority sorting) │                        │
│  └─────────────────────┘     └─────────────────────┘                        │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              UI LAYER                                        │
│  ┌────────────────────────────────────────────────────────────────────────┐ │
│  │                         KPI HEADER                                      │ │
│  │  Price | Change | Spread | Velocity | Status | Timestamp               │ │
│  └────────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  Chart 1: Price + VWAP      │  │  Chart 2: Spread Heatmap            │ │
│  └──────────────────────────────┘  └──────────────────────────────────────┘ │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  Chart 3: Order Book        │  │  Chart 4: Trade Velocity            │ │
│  │           Imbalance         │  │           Gauge                     │ │
│  └──────────────────────────────┘  └──────────────────────────────────────┘ │
│  ┌──────────────────────────────┐  ┌──────────────────────────────────────┐ │
│  │  Chart 5: Volatility        │  │  Chart 6: Insight & Action Panel   │ │
│  │           Monitor           │  │           (DIFFERENTIATOR)          │ │
│  └──────────────────────────────┘  └──────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DOCKER                                          │
│  • Container: python:3.11-slim                                               │
│  • Port: 8501:8501                                                           │
│  • Command: streamlit run src/app.py                                         │
│  • Auto-restart on failure                                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Flow

```
BINANCE ──WebSocket──▶ HANDLER ──Parse──▶ STATE ──Calculate──▶ FEATURES
                                                                   │
                                                                   ▼
    UI ◀──Render── CHARTS ◀──Format── INSIGHTS ◀──Evaluate── RULES
```

---

## 2. Component Breakdown

### 2.1 Configuration Module (`config.py`)

| Constant | Value | Purpose |
|----------|-------|---------|
| `TRADE_WS_URL` | `wss://stream.binance.com:9443/ws/btcusdt@trade` | Trade stream endpoint |
| `DEPTH_WS_URL` | `wss://stream.binance.com:9443/ws/btcusdt@depth10@100ms` | Order book endpoint |
| `TRADES_BUFFER_SIZE` | 1000 | Max trades to store |
| `DEPTH_BUFFER_SIZE` | 100 | Max depth snapshots |
| `PRICE_HISTORY_SIZE` | 200 | Price history for charts |
| `SPREAD_HISTORY_SIZE` | 100 | Spread history for heatmap |
| `VOLATILITY_HISTORY_SIZE` | 200 | Volatility history |
| `VWAP_WINDOW_SECONDS` | 30 | VWAP calculation window |
| `VELOCITY_WINDOW_SECONDS` | 3 | Trade velocity window |
| `VOLATILITY_WINDOW_SECONDS` | 60 | Volatility calculation window |
| `RECONNECT_DELAY_BASE` | 1.0 | Base reconnection delay |
| `RECONNECT_MAX_ATTEMPTS` | 3 | Max reconnection attempts |
| `UI_REFRESH_INTERVAL` | 0.5 | Dashboard refresh rate (seconds) |

### 2.2 Data Layer

#### `websocket_handler.py`
- **Class**: `BinanceWebSocketHandler`
- **Responsibilities**:
  - Establish dual WebSocket connections (trade + depth)
  - Parse incoming JSON messages
  - Handle disconnections with exponential backoff
  - Thread-safe data push to StateManager
  - Connection status tracking

#### `state_manager.py`
- **Class**: `StateManager`
- **Responsibilities**:
  - Thread-safe circular buffers using `collections.deque`
  - Store raw trades, depth snapshots, derived metrics
  - Provide getter methods with lock protection
  - Track connection status and last update time

### 2.3 Feature Engine

#### `feature_engine.py`
- **Class**: `FeatureEngine`
- **Responsibilities**:
  - Calculate all 9 trading features
  - Maintain rolling windows with timestamp filtering
  - Handle edge cases (division by zero, empty data)
  - Return consistent data structures for UI

### 2.4 Decision Layer

#### `rule_engine.py`
- **Class**: `RuleEngine`
- **Responsibilities**:
  - Evaluate 10 trading rules against current features
  - Return list of triggered rules with metadata
  - Track baseline values for velocity comparison

#### `insight_generator.py`
- **Class**: `InsightGenerator`
- **Responsibilities**:
  - Transform triggered rules into formatted insights
  - Priority sorting (HIGH → MEDIUM → LOW)
  - Return top 3 insights with full context

### 2.5 UI Layer

#### `theme.py`
- **Class**: `Theme`
- **Constants**: All color codes, fonts, sizes
- **Methods**: Apply theme to Plotly figures

#### `charts.py`
- **Functions**: One function per chart type
  - `create_price_vwap_chart()`
  - `create_spread_heatmap()`
  - `create_imbalance_chart()`
  - `create_velocity_gauge()`
  - `create_volatility_chart()`

#### `components.py`
- **Functions**:
  - `render_kpi_header()` - Top metrics bar
  - `render_insight_panel()` - Decision support cards
  - `render_connection_status()` - Status indicator

### 2.6 Main Application

#### `app.py`
- **Responsibilities**:
  - Streamlit page configuration
  - Session state initialization
  - WebSocket thread management
  - Main render loop with refresh interval
  - Layout composition

---

## 3. API/Data Contracts

### 3.1 Binance Trade Stream Message

```json
{
  "e": "trade",           // Event type
  "E": 1672531200000,     // Event time (ms)
  "s": "BTCUSDT",         // Symbol
  "t": 123456789,         // Trade ID
  "p": "42000.50",        // Price (string)
  "q": "0.001",           // Quantity (string)
  "b": 88888,             // Buyer order ID
  "a": 88889,             // Seller order ID
  "T": 1672531200000,     // Trade time (ms)
  "m": true,              // Is buyer maker? (true = sell, false = buy)
  "M": true               // Ignore
}
```

**Parsed Trade Object**:
```python
{
    "timestamp": datetime,     # Converted from T
    "price": float,           # Converted from p
    "quantity": float,        # Converted from q
    "is_buyer_maker": bool,   # From m (True = SELL, False = BUY)
    "trade_id": int           # From t
}
```

### 3.2 Binance Depth Stream Message

```json
{
  "lastUpdateId": 123456789,
  "bids": [
    ["42000.00", "1.5"],     // [price, quantity]
    ["41999.00", "2.0"],
    // ... up to 10 levels
  ],
  "asks": [
    ["42001.00", "1.0"],
    ["42002.00", "0.5"],
    // ... up to 10 levels
  ]
}
```

**Parsed Depth Object**:
```python
{
    "timestamp": datetime,     # When received
    "bids": List[Tuple[float, float]],  # [(price, qty), ...]
    "asks": List[Tuple[float, float]],  # [(price, qty), ...]
    "best_bid": float,        # bids[0][0]
    "best_ask": float,        # asks[0][0]
    "bid_volume": float,      # Sum of all bid quantities
    "ask_volume": float       # Sum of all ask quantities
}
```

### 3.3 Feature Output Schema

```python
{
    "mid_price": float,           # (best_bid + best_ask) / 2
    "spread": float,              # best_ask - best_bid
    "spread_bps": float,          # (spread / mid_price) * 10000
    "vwap": float,                # Volume-weighted average price
    "imbalance": float,           # (bid_vol - ask_vol) / (bid_vol + ask_vol)
    "velocity": float,            # Trades per second (smoothed)
    "volatility_bps": float,      # Rolling std dev in bps
    "buy_pressure": float,        # Buy volume / total volume
    "price_vs_vwap": float,       # ((price - vwap) / vwap) * 100
    "timestamp": datetime         # Calculation timestamp
}
```

### 3.4 Insight Output Schema

```python
{
    "id": int,                    # Rule ID (1-10)
    "priority": str,              # "HIGH" | "MEDIUM" | "LOW"
    "priority_emoji": str,        # "🔴" | "🟡" | "🟢"
    "insight": str,               # What is happening
    "action": str,                # IF → THEN recommendation
    "how_to_overcome": str,       # Implementation guidance
    "expected_impact": str,       # Quantified benefit
    "triggered_at": datetime      # When triggered
}
```

---

## 4. State Schema

### 4.1 Buffer Definitions

```python
# trades_buffer: deque(maxlen=1000)
# Stores individual trade records
[
    {
        "timestamp": datetime(2024, 1, 15, 10, 30, 45, 123456),
        "price": 42000.50,
        "quantity": 0.001,
        "is_buyer_maker": True,
        "trade_id": 123456789
    },
    # ... up to 1000 records
]

# depth_buffer: deque(maxlen=100)
# Stores order book snapshots
[
    {
        "timestamp": datetime(2024, 1, 15, 10, 30, 45),
        "bids": [(42000.0, 1.5), (41999.0, 2.0), ...],
        "asks": [(42001.0, 1.0), (42002.0, 0.5), ...],
        "best_bid": 42000.0,
        "best_ask": 42001.0,
        "bid_volume": 15.5,
        "ask_volume": 12.3
    },
    # ... up to 100 records
]

# price_history: deque(maxlen=200)
# For price chart
[
    {"timestamp": datetime, "price": 42000.50, "vwap": 41998.25},
    # ... up to 200 records
]

# spread_history: deque(maxlen=100)
# For spread heatmap
[
    {"timestamp": datetime, "spread_bps": 2.5},
    # ... up to 100 records
]

# volatility_history: deque(maxlen=200)
# For volatility chart
[
    {"timestamp": datetime, "volatility_bps": 15.2},
    # ... up to 200 records
]
```

### 4.2 Session State Variables

```python
st.session_state = {
    "state_manager": StateManager,    # Data buffers
    "feature_engine": FeatureEngine,  # Calculator
    "rule_engine": RuleEngine,        # Rules evaluator
    "insight_generator": InsightGenerator,
    "ws_thread": Thread,              # WebSocket thread
    "is_connected": bool,             # Connection status
    "last_update": datetime,          # Last data update
    "velocity_baseline": float,       # For velocity comparison
    "initialized": bool               # Startup flag
}
```

---

## 5. Feature Calculations

### 5.1 Mid Price
```python
mid_price = (best_bid + best_ask) / 2
# Example: (42000.00 + 42001.00) / 2 = 42000.50
```

### 5.2 Spread
```python
spread = best_ask - best_bid
# Example: 42001.00 - 42000.00 = 1.00
```

### 5.3 Spread in Basis Points
```python
spread_bps = (spread / mid_price) * 10000
# Example: (1.00 / 42000.50) * 10000 = 2.38 bps
```

### 5.4 VWAP (Volume-Weighted Average Price)
```python
# Window: Last 30 seconds
trades_in_window = filter(trades, timestamp >= now - 30s)
vwap = sum(price * quantity for each trade) / sum(quantity)

# Example:
# Trades: [(42000, 0.1), (42010, 0.2), (41990, 0.15)]
# VWAP = (42000*0.1 + 42010*0.2 + 41990*0.15) / (0.1 + 0.2 + 0.15)
#      = (4200 + 8402 + 6298.5) / 0.45
#      = 42001.11
```

### 5.5 Order Book Imbalance
```python
imbalance = (bid_volume - ask_volume) / (bid_volume + ask_volume)
# Range: -1.0 (all sells) to +1.0 (all buys)

# Example:
# bid_volume = 15.5, ask_volume = 12.3
# imbalance = (15.5 - 12.3) / (15.5 + 12.3) = 3.2 / 27.8 = 0.115 (11.5% buy bias)
```

### 5.6 Trade Velocity
```python
# Window: Last 3 seconds
trades_in_window = filter(trades, timestamp >= now - 3s)
velocity = len(trades_in_window) / 3.0  # trades per second

# Example: 45 trades in 3 seconds = 15 trades/sec
```

### 5.7 Rolling Volatility
```python
# Window: Last 60 seconds, calculate every second
prices_in_window = [trade.price for trade in trades if timestamp >= now - 60s]
returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
volatility = std(returns) * 10000  # Convert to bps

# Example:
# Returns: [0.0001, -0.0002, 0.00015, -0.0001]
# Std Dev: 0.000158
# Volatility: 1.58 bps
```

### 5.8 Buy Pressure
```python
# Window: Last 30 seconds
trades_in_window = filter(trades, timestamp >= now - 30s)
buy_volume = sum(qty for trade if not is_buyer_maker)
total_volume = sum(qty for all trades)
buy_pressure = buy_volume / total_volume

# Example:
# Buy volume: 5.2, Total volume: 10.0
# Buy pressure: 0.52 (52%)
```

### 5.9 Price vs VWAP
```python
price_vs_vwap = ((current_price - vwap) / vwap) * 100

# Example:
# Price: 42050, VWAP: 42000
# Price vs VWAP: ((42050 - 42000) / 42000) * 100 = 0.119%
```

---

## 6. Rule Engine Logic

### Decision Tree

```
                            ┌─────────────────┐
                            │  Get Features   │
                            └────────┬────────┘
                                     │
        ┌───────────────────────────┴───────────────────────────┐
        ▼                           ▼                           ▼
   ┌─────────┐               ┌─────────────┐              ┌──────────┐
   │ Spread  │               │  Imbalance  │              │ Volatility│
   └────┬────┘               └──────┬──────┘              └─────┬─────┘
        │                           │                           │
   ┌────┴────┐               ┌──────┴──────┐              ┌─────┴─────┐
   │>6 bps?  │               │< -50%?      │              │>20 bps?   │
   │ Rule 1  │               │  Rule 3     │              │ Rule 5    │
   └────┬────┘               └──────┬──────┘              └─────┬─────┘
   │<2 bps?  │               │> +50%?      │              │<10 bps?   │
   │ Rule 2  │               │  Rule 4     │              │ Rule 6    │
   └─────────┘               └─────────────┘              └───────────┘

        ┌───────────────────────────┴───────────────────────────┐
        ▼                                                       ▼
   ┌──────────┐                                           ┌───────────┐
   │ Velocity │                                           │Price/VWAP │
   └────┬─────┘                                           └─────┬─────┘
        │                                                       │
   ┌────┴────┐                                           ┌─────┴─────┐
   │>2× base?│                                           │>+0.1%?    │
   │ Rule 7  │                                           │ Rule 9    │
   └────┬────┘                                           └─────┬─────┘
   │<0.5×base│                                           │<-0.1%?    │
   │ Rule 8  │                                           │ Rule 10   │
   └─────────┘                                           └───────────┘
```

### Rule Definitions Table

| ID | Condition | Priority | Insight Template | Action | How to Overcome | Impact |
|----|-----------|----------|------------------|--------|-----------------|--------|
| 1 | `spread_bps > 6` | HIGH | "Spread widened to {x:.1f} bps — liquidity deteriorating" | "Pause market orders; use limit orders only" | "Set limit orders at mid-price; accept partial fills" | "Save 6-8 bps per trade" |
| 2 | `spread_bps < 2` | LOW | "Excellent liquidity — spread at {x:.1f} bps" | "Optimal execution window — proceed with orders" | "Prioritize larger orders now" | "Best execution quality" |
| 3 | `imbalance < -0.5` | HIGH | "Strong sell pressure at {x:.1f}%" | "Tighten stop-loss if long; delay buys" | "Set alerts for imbalance reversal" | "Avoid 0.1-0.3% drawdown" |
| 4 | `imbalance > 0.5` | MEDIUM | "Buy-side demand at {x:.1f}%" | "Prices supported; delay sells" | "Wait for imbalance weakening" | "Improve sell price 0.05%" |
| 5 | `volatility_bps > 20` | HIGH | "High volatility at {x:.1f} bps" | "Reduce position size by 50%" | "Scale down; wait for mean-reversion" | "Reduce drawdown 40%" |
| 6 | `volatility_bps < 10` | LOW | "Low volatility — range-bound" | "Good for mean-reversion strategies" | "Tighter targets; frequent small trades" | "Increase trade frequency" |
| 7 | `velocity > 2 * baseline` | HIGH | "Velocity spike: {x:.1f}/s vs {y:.1f}/s baseline" | "Prepare for volatility; increase monitoring" | "Check news; tighten risk parameters" | "10-30 second early warning" |
| 8 | `velocity < 0.5 * baseline` | MEDIUM | "Thin market: {x:.1f}/s activity" | "Expect slippage; reduce order sizes" | "Split large orders into chunks" | "Reduce market impact 50%" |
| 9 | `price_vs_vwap > 0.1` | MEDIUM | "Price {x:.2f}% above VWAP — overbought" | "Wait for pullback if buying" | "Set limit orders at VWAP level" | "Reduce slippage 3-5 bps" |
| 10 | `price_vs_vwap < -0.1` | MEDIUM | "Price {x:.2f}% below VWAP — value zone" | "Favorable entry vs average" | "Use window for cost-averaging" | "Improve entry 0.05-0.1%" |

### Priority Weighting

```python
PRIORITY_ORDER = {
    "HIGH": 1,    # 🔴 Urgent action required
    "MEDIUM": 2,  # 🟡 Monitor and consider action
    "LOW": 3      # 🟢 Informational
}

# Sort insights by priority, then by timestamp (most recent first)
sorted_insights = sorted(insights, key=lambda x: (PRIORITY_ORDER[x.priority], -x.timestamp))
```

---

## 7. UI Layout

### 7.1 Page Configuration

```python
st.set_page_config(
    page_title="HFT Live Dashboard",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="collapsed"
)
```

### 7.2 Layout Structure

```
┌────────────────────────────────────────────────────────────────────────────┐
│                           CONNECTION STATUS BAR                             │
│  🟢 Connected to Binance | Last Update: 10:30:45.123                       │
├────────────────────────────────────────────────────────────────────────────┤
│                              KPI HEADER                                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐  │
│  │  PRICE  │ │ CHANGE  │ │ SPREAD  │ │VELOCITY │ │  VWAP   │ │IMBALANCE│  │
│  │$42,150.5│ │ +0.15%  │ │ 2.3 bps │ │ 15/sec  │ │$42,148  │ │ +12.5%  │  │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘ └─────────┘  │
├──────────────────────────────────┬─────────────────────────────────────────┤
│      CHART 1: PRICE + VWAP       │       CHART 2: SPREAD HEATMAP          │
│                                  │                                         │
│  [Line chart with dual overlay]  │  [Horizontal bar with color gradient]  │
│                                  │                                         │
│  Height: 300px                   │  Height: 300px                          │
├──────────────────────────────────┼─────────────────────────────────────────┤
│   CHART 3: ORDER IMBALANCE       │      CHART 4: TRADE VELOCITY           │
│                                  │                                         │
│  [Diverging horizontal bar]      │  [Speedometer gauge]                   │
│                                  │                                         │
│  Height: 250px                   │  Height: 250px                          │
├──────────────────────────────────┼─────────────────────────────────────────┤
│   CHART 5: VOLATILITY MONITOR    │   CHART 6: INSIGHT & ACTION PANEL      │
│                                  │                                         │
│  [Area chart with bands]         │  ┌────────────────────────────────┐    │
│                                  │  │ 🔴 HIGH: Spread widened...     │    │
│                                  │  │    Action: Pause market orders │    │
│                                  │  │    Overcome: Set limit orders  │    │
│                                  │  │    Impact: Save 6-8 bps        │    │
│                                  │  ├────────────────────────────────┤    │
│                                  │  │ 🟡 MEDIUM: Velocity spike...   │    │
│  Height: 300px                   │  │    ...                         │    │
│                                  │  └────────────────────────────────┘    │
└──────────────────────────────────┴─────────────────────────────────────────┘
```

### 7.3 Streamlit Column Layout

```python
# KPI Header
kpi_cols = st.columns(6)

# Charts Row 1
col1, col2 = st.columns(2)
with col1:
    # Price + VWAP Chart
with col2:
    # Spread Heatmap

# Charts Row 2
col3, col4 = st.columns(2)
with col3:
    # Imbalance Chart
with col4:
    # Velocity Gauge

# Charts Row 3
col5, col6 = st.columns(2)
with col5:
    # Volatility Monitor
with col6:
    # Insight Panel
```

### 7.4 Custom CSS

```css
/* Dark theme overrides */
.stApp {
    background-color: #0e1117;
}

/* Card styling */
.insight-card {
    background-color: #1a1f2e;
    border: 1px solid #2d3748;
    border-radius: 8px;
    padding: 16px;
    margin-bottom: 12px;
}

/* Priority badges */
.priority-high { color: #ff6b6b; }
.priority-medium { color: #ffe66d; }
.priority-low { color: #00d4aa; }

/* KPI values */
.kpi-value {
    font-size: 24px;
    font-weight: bold;
    color: #fafafa;
}

.kpi-label {
    font-size: 12px;
    color: #a0a0a0;
    text-transform: uppercase;
}
```

---

## 8. Docker Setup

### 8.1 Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose Streamlit port
EXPOSE 8501

# Health check
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health || exit 1

# Run Streamlit
CMD ["streamlit", "run", "src/app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

### 8.2 docker-compose.yml

```yaml
version: '3.8'

services:
  hft-dashboard:
    build: .
    ports:
      - "8501:8501"
    restart: unless-stopped
    environment:
      - PYTHONUNBUFFERED=1
    volumes:
      - ./src:/app/src:ro  # Optional: for development hot-reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8501/_stcore/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### 8.3 requirements.txt

```
streamlit==1.29.0
plotly==5.18.0
pandas==2.1.4
numpy==1.26.2
websockets==12.0
python-dateutil==2.8.2
```

---

## 9. Development Phases

### Phase 1: Foundation (Est. 30 mins)

**Files to create:**
- `requirements.txt`
- `Dockerfile`
- `docker-compose.yml`
- `src/config.py`
- `src/__init__.py`

**Verification:**
```bash
docker-compose build
docker-compose up
# Should see Streamlit startup message
# Access localhost:8501 - should show empty Streamlit page
```

**Success Criteria:**
- [ ] Docker builds without errors
- [ ] Container starts successfully
- [ ] localhost:8501 accessible
- [ ] No Python import errors

---

### Phase 2: Data Layer (Est. 45 mins)

**Files to create:**
- `src/data/__init__.py`
- `src/data/websocket_handler.py`
- `src/data/state_manager.py`

**Verification:**
```python
# Test in container
python -c "from src.data.websocket_handler import BinanceWebSocketHandler; print('OK')"
# Run standalone test to see trades streaming
```

**Success Criteria:**
- [ ] WebSocket connects to Binance
- [ ] Trades print to console
- [ ] Depth updates received
- [ ] Reconnection works (test by briefly disconnecting)
- [ ] StateManager stores data correctly

---

### Phase 3: Feature Engine (Est. 45 mins)

**Files to create:**
- `src/features/__init__.py`
- `src/features/feature_engine.py`

**Verification:**
```python
# Feed sample data and verify calculations
features = engine.calculate_all()
assert 'mid_price' in features
assert 'spread_bps' in features
# Verify VWAP calculation with known values
```

**Success Criteria:**
- [ ] All 9 features calculate correctly
- [ ] No division by zero errors
- [ ] Handles empty data gracefully
- [ ] Rolling windows work correctly

---

### Phase 4: Decision Layer (Est. 45 mins)

**Files to create:**
- `src/decision/__init__.py`
- `src/decision/rule_engine.py`
- `src/decision/insight_generator.py`

**Verification:**
```python
# Test with mock features that trigger each rule
test_features = {"spread_bps": 8.0, ...}  # Should trigger Rule 1
insights = generator.generate(test_features)
assert len(insights) > 0
assert insights[0]['priority'] == 'HIGH'
```

**Success Criteria:**
- [ ] All 10 rules implemented
- [ ] Priority sorting works
- [ ] Insight formatting correct
- [ ] Dynamic value insertion works

---

### Phase 5: UI Components (Est. 60 mins)

**Files to create:**
- `src/ui/__init__.py`
- `src/ui/theme.py`
- `src/ui/charts.py`
- `src/ui/components.py`

**Verification:**
```python
# Test each chart with sample data
fig = create_price_vwap_chart(sample_price_data)
fig.show()  # Should render in browser
```

**Success Criteria:**
- [ ] All 5 charts render correctly
- [ ] Dark theme applied
- [ ] Colors match specification
- [ ] Charts are responsive

---

### Phase 6: Integration (Est. 60 mins)

**Files to create:**
- `src/app.py`
- `src/utils/__init__.py`
- `src/utils/helpers.py`

**Verification:**
```bash
docker-compose up
# Full dashboard should work
# All charts updating
# Insights generating
```

**Success Criteria:**
- [ ] Dashboard loads without errors
- [ ] All components integrated
- [ ] Real-time updates working
- [ ] No console errors

---

### Phase 7: Polish (Est. 45 mins)

**Files to create/update:**
- `README.md`
- Error handling improvements
- Reconnection logic refinement
- `tests/test_features.py`

**Verification:**
- Full testing checklist (see Section 10)

**Success Criteria:**
- [ ] All checklist items pass
- [ ] README is comprehensive
- [ ] Error handling robust

---

## 10. Testing Checklist

### 10.1 Startup Tests

| Test | Command/Action | Expected Result |
|------|----------------|-----------------|
| Docker build | `docker-compose build` | No errors |
| Container start | `docker-compose up` | Container runs |
| Dashboard access | Open localhost:8501 | Page loads |
| Initial connection | Wait 5 seconds | Data streaming |

### 10.2 Data Flow Tests

| Test | Action | Expected Result |
|------|--------|-----------------|
| Trade stream | Observe price | Updates continuously |
| Depth stream | Observe spread | Updates every 100ms |
| Buffer limits | Run for 5 mins | No memory growth |
| Data accuracy | Compare to Binance | Prices match |

### 10.3 Feature Calculation Tests

| Feature | Test Method | Validation |
|---------|-------------|------------|
| Mid Price | Manual calc | Within 0.01% |
| Spread | Manual calc | Exact match |
| VWAP | Sample trades | Within 0.1% |
| Imbalance | Fixed order book | Exact match |
| Velocity | Count trades | Within 1 trade |
| Volatility | Sample returns | Within 5% |

### 10.4 UI Tests

| Test | Action | Expected Result |
|------|--------|-----------------|
| KPI Header | Observe | All 6 metrics visible |
| Price Chart | Observe | Smooth line updates |
| Spread Heatmap | Wait 60s | Full timeline visible |
| Imbalance | Observe | Bar moves with data |
| Velocity Gauge | Observe | Needle updates |
| Volatility | Wait 60s | Area chart fills |
| Insight Panel | Trigger conditions | Cards appear |

### 10.5 Error Handling Tests

| Scenario | Action | Expected Result |
|----------|--------|-----------------|
| Network disconnect | Disable WiFi | Yellow "Reconnecting" |
| Network reconnect | Enable WiFi | Auto-recovery |
| 3 failed reconnects | Block Binance IP | Red "Disconnected" |
| Zero volume | Wait for low activity | No crashes |
| Empty buffers | Fresh start | Graceful handling |

### 10.6 Performance Tests

| Metric | Threshold | Test Method |
|--------|-----------|-------------|
| CPU usage | < 50% | Task Manager |
| Memory | < 500MB | Docker stats |
| Update latency | < 500ms | Visual observation |
| Chart render | < 100ms | No visible lag |

### 10.7 Visual Tests

| Element | Requirement | Check |
|---------|-------------|-------|
| Background | #0e1117 | Color picker |
| Cards | #1a1f2e | Color picker |
| Text | #fafafa | Readable |
| Green accent | #00d4aa | Matches |
| Red accent | #ff6b6b | Matches |
| Layout | No overflow | All screen sizes |

---

## 11. Risk Mitigation

### 11.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Binance blocks IP | Low | High | Fallback to cached data display |
| WebSocket instability | Medium | Medium | Robust reconnection with backoff |
| High latency | Medium | Medium | Buffer recent data, show stale indicator |
| Memory leak | Low | High | Use deque with maxlen, monitor in tests |
| Python GIL blocking | Medium | Medium | Use async for I/O, threading for compute |

### 11.2 Presentation Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Demo crashes | Low | High | Test 10+ times before presentation |
| No internet | Low | High | Prepare offline video backup |
| Slow start | Low | Medium | Pre-warm container before demo |
| Questions on code | High | Low | Comment code thoroughly |
| Questions on math | High | Low | Prepare formula explanations |

### 11.3 Data Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| No market activity | Low | Medium | Demo during market hours |
| Extreme volatility | Low | Medium | Adjustable thresholds in config |
| Data gaps | Medium | Low | Interpolate missing points |
| Timestamp sync | Low | Low | Use server timestamps |

### 11.4 Contingency Plans

**Plan A: Primary Demo**
- Full live dashboard with Binance connection
- All features working in real-time

**Plan B: Cached Data**
- Pre-recorded data playback
- Same dashboard, simulated feed
- Implement in `websocket_handler.py` with `--demo` flag

**Plan C: Video Backup**
- 5-minute recorded demo video
- Voiceover explaining features
- Store on USB drive

### 11.5 Pre-Presentation Checklist

```
□ Docker running smoothly
□ Internet connection stable
□ Binance accessible (test in browser)
□ Dashboard loads in < 10 seconds
□ All charts updating
□ Insight panel showing rules
□ No console errors
□ Laptop fully charged
□ Screen resolution optimal (1080p+)
□ Browser zoom at 100%
□ Video backup ready on USB
□ Code commented for Q&A
□ Formula cheat sheet printed
```

---

## Appendix A: File Dependency Graph

```
requirements.txt
    └── Dockerfile
        └── docker-compose.yml
            └── src/app.py
                ├── src/config.py
                ├── src/data/
                │   ├── websocket_handler.py
                │   └── state_manager.py
                ├── src/features/
                │   └── feature_engine.py
                ├── src/decision/
                │   ├── rule_engine.py
                │   └── insight_generator.py
                ├── src/ui/
                │   ├── theme.py
                │   ├── charts.py
                │   └── components.py
                └── src/utils/
                    └── helpers.py
```

---

## Appendix B: Quick Reference - Binance WebSocket

### Connection Example
```python
import asyncio
import websockets
import json

async def connect():
    uri = "wss://stream.binance.com:9443/ws/btcusdt@trade"
    async with websockets.connect(uri) as ws:
        while True:
            msg = await ws.recv()
            data = json.loads(msg)
            print(f"Price: {data['p']}, Qty: {data['q']}")

asyncio.run(connect())
```

### Combined Stream (Multiple Streams)
```python
uri = "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/btcusdt@depth10@100ms"
# Messages have format: {"stream": "btcusdt@trade", "data": {...}}
```

---

## Appendix C: Streamlit Refresh Pattern

```python
import streamlit as st
import time

# Initialize session state
if 'data' not in st.session_state:
    st.session_state.data = []

# Main loop with auto-refresh
placeholder = st.empty()

while True:
    with placeholder.container():
        # Render UI components
        st.metric("Price", st.session_state.data[-1] if st.session_state.data else "N/A")
    
    time.sleep(0.5)  # 500ms refresh
    st.rerun()
```

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-01-26 | HFT Dashboard Team | Initial blueprint |

---

**END OF IMPLEMENTATION PLAN**

*This document serves as the complete blueprint for the HFT Live Visualization & Decisioning Dashboard. All development should follow this plan phase by phase, with verification at each step.*
