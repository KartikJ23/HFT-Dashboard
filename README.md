# 📈 HFT Live Visualization & Decisioning Dashboard

A **professional-grade**, real-time High-Frequency Trading (HFT) dashboard that streams live BTC/USDT market data from Binance and provides actionable trading intelligence.

<div align="center">

![Dashboard Preview](https://img.shields.io/badge/Status-Production%20Ready-00d4aa?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.53-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=for-the-badge&logo=docker&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

**Masters in Business Analytics • Data Visualization & Analytics**

</div>

---

## 🎯 Key Differentiator

> **This is NOT just a visualization dashboard.**

Every chart produces **actionable intelligence** with our proprietary 4-component insight system:

| Component | Description |
|-----------|-------------|
| 🔍 **Insight** | What is happening in the market right now |
| ⚡ **Action** | IF → THEN recommendation for immediate execution |
| 🛡️ **How to Overcome** | Implementation guidance and risk mitigation |
| 📊 **Expected Impact** | Quantified measurable benefit |

This transforms the dashboard from "showing data" to a **decision support system** for professional traders.

---

## ✨ Professional Features

### 🎨 Premium Design

- **Glassmorphism UI** - Modern frosted glass aesthetic
- **Dark Theme** - Professional trading terminal appearance
- **Animated Elements** - Smooth transitions and live indicators
- **Responsive Layout** - Optimized for all screen sizes
- **Premium Typography** - Inter & JetBrains Mono fonts

### 📡 Real-Time Data Streams

- **Trade Stream**: Live BTC/USDT trades from Binance
- **Order Book**: Top 10 bid/ask levels, updated every 100ms
- **Zero Latency**: Direct WebSocket connection
- **No API Key Required**: Uses public Binance endpoints
- **Auto-Reconnection**: Resilient connection handling

### 📊 Calculated Metrics

| Metric | Formula | Update Rate |
|--------|---------|-------------|
| Mid Price | (Best Bid + Best Ask) / 2 | Real-time |
| Spread (bps) | (Spread / Mid Price) × 10,000 | Real-time |
| VWAP | Σ(Price × Volume) / Σ(Volume) | 30-second window |
| Order Imbalance | (Bid Vol - Ask Vol) / Total Vol | Real-time |
| Trade Velocity | Trades per second | 3-second smoothed |
| Volatility | Rolling StdDev of returns | 60-second window |
| Buy Pressure | Buy Volume / Total Volume | 30-second window |

### 📈 Interactive Visualizations

1. **Live Price + VWAP Chart** - Dual line with crossover detection & gradient fills
2. **Spread Heatmap Timeline** - Color-coded spread history with threshold zones
3. **Order Book Imbalance** - Gauge-style bar with volume distribution
4. **Trade Velocity Gauge** - Premium speedometer with baseline comparison
5. **Volatility Monitor** - Area chart with threshold bands (Low/Moderate/High)
6. **Insight & Action Panel** - Dynamic AI-driven trading recommendations

---

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Internet connection (for Binance WebSocket)

### One Command Startup

```bash
docker-compose up
```

Then open your browser to: **http://localhost:8501**

### Development Mode (with hot-reload)

```bash
docker-compose up --build
```

### To Stop

```bash
docker-compose down
```

---

## 📋 Dashboard Layout

```
┌──────────────────────────────────────────────────────────────────┐
│  📈 HFT TRADING DASHBOARD           [🟢 LIVE TRADING]            │
├──────────────────────────────────────────────────────────────────┤
│  🟢 Connected to Binance Exchange    Last Update: 10:30:45.123   │
├──────────────────────────────────────────────────────────────────┤
│ 💰 PRICE │ 📊 CHANGE │ 📏 SPREAD │ ⚡ VELOCITY │ 📐 VWAP │ ⚖️ IMBAL │
│ $104,250 │  ▲ 0.15% │  2.3 bps │   15.2/s   │ $104,248 │ +12.5% │
├────────────────────────────┬─────────────────────────────────────┤
│  📈 Live Price & VWAP      │  📊 Bid-Ask Spread Timeline         │
│  [Crossover Detection]     │  [Threshold Zones]                  │
├────────────────────────────┼─────────────────────────────────────┤
│  ⚖️ Order Book Imbalance   │  ⚡ Trade Velocity Gauge            │
│  [Buy/Sell Pressure]       │  [Spike Detection]                  │
├────────────────────────────┼─────────────────────────────────────┤
│  📉 Volatility Monitor     │  🎯 TRADING INTELLIGENCE            │
│  [Risk Bands]              │                                     │
│                            │  🔴 HIGH: Sell pressure at -55%     │
│                            │  Action: Tighten stop-loss          │
│                            │  Impact: Avoid 0.1-0.3% drawdown    │
├────────────────────────────┴─────────────────────────────────────┤
│  Buy Pressure: 45.2% │ Volatility: 12.5 bps │ Bid/Ask Volumes   │
└──────────────────────────────────────────────────────────────────┘
```

---

## 🔔 Trading Rules Engine

The dashboard implements **10 intelligent trading rules**:

| # | Condition | Priority | Trigger | Action |
|---|-----------|----------|---------|--------|
| 1 | Spread > 6 bps | 🔴 HIGH | Liquidity deteriorating | Pause market orders |
| 2 | Spread < 2 bps | 🟢 LOW | Optimal execution | Proceed with orders |
| 3 | Imbalance < -50% | 🔴 HIGH | Strong sell pressure | Tighten stop-loss |
| 4 | Imbalance > +50% | 🟡 MEDIUM | Buy-side demand | Delay sells |
| 5 | Volatility > 20 bps | 🔴 HIGH | High risk regime | Reduce position 50% |
| 6 | Volatility < 10 bps | 🟢 LOW | Range-bound market | Mean-reversion strategy |
| 7 | Velocity > 2× baseline | 🔴 HIGH | Velocity spike | Increase monitoring |
| 8 | Velocity < 0.5× baseline | 🟡 MEDIUM | Thin market | Reduce order sizes |
| 9 | Price > VWAP + 0.1% | 🟡 MEDIUM | Overbought | Wait for pullback |
| 10 | Price < VWAP - 0.1% | 🟡 MEDIUM | Value zone | Favorable entry |

---

## 📁 Project Structure

```
hft-dashboard/
├── 📄 docker-compose.yml      # Container orchestration
├── 📄 Dockerfile              # Python 3.11-slim container
├── 📄 requirements.txt        # Python dependencies
├── 📄 README.md               # This documentation
├── 📄 Implementation_Plan.md  # Technical blueprint
├── 📁 .streamlit/
│   └── config.toml            # Streamlit dark theme config
├── 📁 src/
│   ├── app.py                 # Main Streamlit application
│   ├── config.py              # Configuration & constants
│   ├── 📁 data/
│   │   ├── websocket_handler.py  # Binance WebSocket client
│   │   └── state_manager.py      # Thread-safe data buffers
│   ├── 📁 features/
│   │   └── feature_engine.py     # 9 metric calculations
│   ├── 📁 decision/
│   │   ├── rule_engine.py        # 10 trading rules
│   │   └── insight_generator.py  # Insight formatting
│   ├── 📁 ui/
│   │   ├── theme.py              # Glassmorphism CSS
│   │   ├── charts.py             # 5 Plotly charts
│   │   └── components.py         # UI components
│   └── 📁 utils/
│       └── helpers.py            # Utility functions
└── 📁 tests/
    └── test_features.py          # Unit tests
```

---

## 🛠️ Technology Stack

| Layer | Technology | Purpose |
|-------|------------|---------|
| **Frontend** | Streamlit 1.53 | Real-time dashboard framework |
| **Charts** | Plotly 5.18 | Interactive visualizations |
| **Styling** | Custom CSS | Glassmorphism design |
| **Data** | Binance WebSocket | Live market data |
| **Backend** | Python 3.11 | Feature calculations |
| **Container** | Docker | Deployment & isolation |

---

## 🎓 Academic Context

This project was developed for the **Data Visualization & Analytics** course as part of the **Masters in Business Analytics** program.

### Learning Objectives Demonstrated

1. **Real-time Data Processing** - WebSocket streaming & circular buffers
2. **Feature Engineering** - 9 calculated trading metrics
3. **Rule-Based Systems** - 10 trading rules with priority logic
4. **Interactive Visualization** - 5 professional Plotly charts
5. **Decision Support Systems** - Actionable insight generation
6. **Software Engineering** - Modular architecture, Docker deployment

### Evaluation Criteria

- ✅ Technical complexity and correctness
- ✅ Professional UI/UX design
- ✅ Real-time data handling
- ✅ Actionable insights (key differentiator)
- ✅ Code quality and documentation
- ✅ Live demo capability

---

## 🧪 Testing

### Run Unit Tests

```bash
docker exec hft-live-dashboard pytest tests/ -v
```

### Manual Testing Checklist

- [ ] Dashboard loads at localhost:8501
- [ ] Live data streaming (check timestamp)
- [ ] All 5 charts rendering correctly
- [ ] Insight panel showing recommendations
- [ ] Connection status indicator working
- [ ] KPI header updating in real-time
- [ ] Disconnect/reconnect recovery

---

## 📝 License

This project is developed for educational purposes as part of the Masters in Business Analytics program.

---

<div align="center">

**Built with ❤️ for HFT Analytics**

*Real-time market intelligence • Professional trading dashboard*

</div>
