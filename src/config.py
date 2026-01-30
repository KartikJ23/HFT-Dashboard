"""
HFT Live Dashboard - Configuration Module
==========================================

All constants, thresholds, and settings for the dashboard.
Centralized configuration for easy tuning and maintenance.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Tuple


# =============================================================================
# WEBSOCKET CONFIGURATION
# =============================================================================

# Binance WebSocket Endpoints (Public - No API Key Required)
TRADE_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@trade"
DEPTH_WS_URL = "wss://stream.binance.com:9443/ws/btcusdt@depth10@100ms"

# Combined stream URL for single connection
COMBINED_WS_URL = "wss://stream.binance.com:9443/stream?streams=btcusdt@trade/btcusdt@depth10@100ms"

# Trading pair
SYMBOL = "BTCUSDT"
SYMBOL_DISPLAY = "BTC/USDT"


# =============================================================================
# BUFFER SIZES (Circular Buffer Limits)
# =============================================================================

TRADES_BUFFER_SIZE = 1000       # Max trades to store
DEPTH_BUFFER_SIZE = 100         # Max depth snapshots
PRICE_HISTORY_SIZE = 200        # Price history for charts
SPREAD_HISTORY_SIZE = 100       # Spread history for heatmap
VOLATILITY_HISTORY_SIZE = 200   # Volatility history
VELOCITY_HISTORY_SIZE = 100     # Velocity history


# =============================================================================
# TIME WINDOWS (in seconds)
# =============================================================================

VWAP_WINDOW_SECONDS = 30            # VWAP calculation window
VELOCITY_WINDOW_SECONDS = 3         # Trade velocity smoothing
VOLATILITY_WINDOW_SECONDS = 60      # Volatility calculation window
BUY_PRESSURE_WINDOW_SECONDS = 30    # Buy pressure window
PRICE_CHART_WINDOW_SECONDS = 120    # 2 minutes for price chart
SPREAD_HEATMAP_WINDOW_SECONDS = 60  # 1 minute for spread heatmap
VOLATILITY_CHART_WINDOW_SECONDS = 180  # 3 minutes for volatility chart


# =============================================================================
# RECONNECTION SETTINGS
# =============================================================================

RECONNECT_DELAY_BASE = 1.0      # Base delay in seconds
RECONNECT_DELAY_MAX = 30.0      # Maximum delay cap
RECONNECT_MAX_ATTEMPTS = 3      # Max attempts before showing error
HEARTBEAT_TIMEOUT = 5.0         # Seconds without message = disconnected


# =============================================================================
# UI REFRESH SETTINGS
# =============================================================================

UI_REFRESH_INTERVAL = 0.5       # Dashboard refresh rate (seconds)
SPREAD_SAMPLE_INTERVAL = 5      # Sample spread every 5 seconds


# =============================================================================
# THRESHOLD SETTINGS (For Rule Engine)
# =============================================================================

@dataclass
class Thresholds:
    """Trading thresholds for rule engine evaluation."""
    
    # Spread thresholds (in basis points)
    spread_high_bps: float = 6.0        # Liquidity deteriorating
    spread_low_bps: float = 2.0         # Optimal execution
    
    # Imbalance thresholds (as decimal -1 to +1)
    imbalance_strong_sell: float = -0.5  # Strong sell pressure
    imbalance_strong_buy: float = 0.5    # Strong buy pressure
    
    # Volatility thresholds (in basis points)
    volatility_high_bps: float = 20.0   # High risk regime
    volatility_low_bps: float = 10.0    # Range-bound
    
    # Velocity multipliers (relative to baseline)
    velocity_spike_multiplier: float = 2.0   # Unusual activity
    velocity_thin_multiplier: float = 0.5    # Thin market
    
    # Price vs VWAP thresholds (percentage)
    price_overbought_pct: float = 0.1   # Overbought
    price_oversold_pct: float = -0.1    # Value zone


# Global thresholds instance
THRESHOLDS = Thresholds()


# =============================================================================
# VELOCITY BASELINE
# =============================================================================

# Default baseline (will be dynamically adjusted)
DEFAULT_VELOCITY_BASELINE = 20.0  # trades per second


# =============================================================================
# COLOR SCHEME (Dark Theme)
# =============================================================================

@dataclass
class Colors:
    """Color palette for the dashboard."""
    
    # Base colors
    background: str = "#0e1117"
    card_background: str = "#1a1f2e"
    border: str = "#2d3748"
    
    # Text colors
    text_primary: str = "#fafafa"
    text_secondary: str = "#a0a0a0"
    
    # Accent colors
    accent_green: str = "#00d4aa"
    accent_red: str = "#ff6b6b"
    accent_yellow: str = "#ffe66d"
    accent_cyan: str = "#4ecdc4"
    
    # Chart colors
    price_line: str = "#fafafa"
    vwap_line: str = "#4ecdc4"
    
    # Status colors
    status_connected: str = "#00d4aa"
    status_reconnecting: str = "#ffe66d"
    status_disconnected: str = "#ff6b6b"
    
    # Spread heatmap gradient
    spread_good: str = "#00d4aa"      # < 3 bps
    spread_medium: str = "#ffe66d"    # 3-6 bps
    spread_bad: str = "#ff6b6b"       # > 6 bps
    
    # Imbalance colors
    buy_pressure: str = "#00d4aa"
    sell_pressure: str = "#ff6b6b"
    
    # Velocity gauge zones
    velocity_low: str = "#00d4aa"     # 0-30 trades/sec
    velocity_medium: str = "#ffe66d"  # 30-60 trades/sec
    velocity_high: str = "#ff6b6b"    # 60+ trades/sec
    
    # Volatility zones
    volatility_low: str = "#00d4aa"   # < 15 bps
    volatility_medium: str = "#ffe66d"  # 15-20 bps
    volatility_high: str = "#ff6b6b"  # > 20 bps


# Global colors instance
COLORS = Colors()


# =============================================================================
# CHART CONFIGURATION
# =============================================================================

@dataclass
class ChartConfig:
    """Configuration for Plotly charts."""
    
    # Default chart dimensions
    default_height: int = 300
    gauge_height: int = 250
    
    # Font settings
    font_family: str = "Arial, sans-serif"
    font_size_title: int = 16
    font_size_axis: int = 12
    font_size_annotation: int = 11
    
    # Margin settings
    margin: Dict[str, int] = field(default_factory=lambda: {
        "l": 50, "r": 30, "t": 50, "b": 50
    })
    
    # Animation settings
    animate: bool = False  # Disable for performance
    
    # Velocity gauge ranges
    velocity_range: List[int] = field(default_factory=lambda: [0, 100])
    velocity_steps: List[Tuple[float, str]] = field(default_factory=lambda: [
        (0.3, Colors.velocity_low),     # 0-30
        (0.6, Colors.velocity_medium),  # 30-60
        (1.0, Colors.velocity_high)     # 60-100
    ])


# Global chart config instance
CHART_CONFIG = ChartConfig()


# =============================================================================
# INSIGHT CONFIGURATION
# =============================================================================

@dataclass
class InsightConfig:
    """Configuration for insight generation."""
    
    # Maximum insights to display
    max_insights: int = 3
    
    # Priority settings
    priorities: Dict[str, Dict] = field(default_factory=lambda: {
        "HIGH": {"emoji": "🔴", "order": 1, "color": Colors.accent_red},
        "MEDIUM": {"emoji": "🟡", "order": 2, "color": Colors.accent_yellow},
        "LOW": {"emoji": "🟢", "order": 3, "color": Colors.accent_green}
    })
    
    # Insight card styling
    card_padding: str = "16px"
    card_margin: str = "12px"
    card_border_radius: str = "8px"


# Global insight config instance
INSIGHT_CONFIG = InsightConfig()


# =============================================================================
# RULE DEFINITIONS
# =============================================================================

# Complete rule definitions for the decision engine
RULES = [
    {
        "id": 1,
        "condition": "spread_bps > 6",
        "priority": "HIGH",
        "insight": "Spread widened to {spread_bps:.1f} bps — liquidity deteriorating",
        "action": "Pause market orders; use limit orders only",
        "how_to_overcome": "Set limit orders at mid-price; accept partial fills",
        "expected_impact": "Save 6-8 bps per trade"
    },
    {
        "id": 2,
        "condition": "spread_bps < 2",
        "priority": "LOW",
        "insight": "Excellent liquidity — spread at {spread_bps:.1f} bps",
        "action": "Optimal execution window — proceed with orders",
        "how_to_overcome": "Prioritize larger orders now",
        "expected_impact": "Best execution quality"
    },
    {
        "id": 3,
        "condition": "imbalance < -0.5",
        "priority": "HIGH",
        "insight": "Strong sell pressure at {imbalance_pct:.1f}%",
        "action": "Tighten stop-loss if long; delay buys",
        "how_to_overcome": "Set alerts for imbalance reversal",
        "expected_impact": "Avoid 0.1-0.3% drawdown"
    },
    {
        "id": 4,
        "condition": "imbalance > 0.5",
        "priority": "MEDIUM",
        "insight": "Buy-side demand at {imbalance_pct:.1f}%",
        "action": "Prices supported; delay sells",
        "how_to_overcome": "Wait for imbalance weakening",
        "expected_impact": "Improve sell price 0.05%"
    },
    {
        "id": 5,
        "condition": "volatility_bps > 20",
        "priority": "HIGH",
        "insight": "High volatility at {volatility_bps:.1f} bps",
        "action": "Reduce position size by 50%",
        "how_to_overcome": "Scale down; wait for mean-reversion",
        "expected_impact": "Reduce drawdown 40%"
    },
    {
        "id": 6,
        "condition": "volatility_bps < 10",
        "priority": "LOW",
        "insight": "Low volatility — range-bound market",
        "action": "Good for mean-reversion strategies",
        "how_to_overcome": "Tighter targets; frequent small trades",
        "expected_impact": "Increase trade frequency"
    },
    {
        "id": 7,
        "condition": "velocity > 2 * baseline",
        "priority": "HIGH",
        "insight": "Velocity spike: {velocity:.1f}/s vs {baseline:.1f}/s baseline",
        "action": "Prepare for volatility; increase monitoring",
        "how_to_overcome": "Check news; tighten risk parameters",
        "expected_impact": "10-30 second early warning"
    },
    {
        "id": 8,
        "condition": "velocity < 0.5 * baseline",
        "priority": "MEDIUM",
        "insight": "Thin market: {velocity:.1f}/s activity",
        "action": "Expect slippage; reduce order sizes",
        "how_to_overcome": "Split large orders into chunks",
        "expected_impact": "Reduce market impact 50%"
    },
    {
        "id": 9,
        "condition": "price_vs_vwap > 0.1",
        "priority": "MEDIUM",
        "insight": "Price {price_vs_vwap:.2f}% above VWAP — overbought",
        "action": "Wait for pullback if buying",
        "how_to_overcome": "Set limit orders at VWAP level",
        "expected_impact": "Reduce slippage 3-5 bps"
    },
    {
        "id": 10,
        "condition": "price_vs_vwap < -0.1",
        "priority": "MEDIUM",
        "insight": "Price {price_vs_vwap:.2f}% below VWAP — value zone",
        "action": "Favorable entry vs average",
        "how_to_overcome": "Use window for cost-averaging",
        "expected_impact": "Improve entry 0.05-0.1%"
    }
]


# =============================================================================
# STREAMLIT PAGE CONFIG
# =============================================================================

PAGE_CONFIG = {
    "page_title": "HFT Live Dashboard",
    "page_icon": "📈",
    "layout": "wide",
    "initial_sidebar_state": "expanded"
}


# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
LOG_LEVEL = "INFO"


# =============================================================================
# ML PREDICTION CONFIGURATION
# =============================================================================

@dataclass
class MLConfig:
    """Configuration for ML prediction engine."""
    
    # Prediction horizon (seconds)
    prediction_horizon: int = 5
    
    # Model update frequency
    update_interval_ms: int = 500
    
    # Minimum data points for prediction
    min_data_points: int = 20
    
    # History size for calculations
    history_size: int = 500
    
    # Confidence thresholds
    high_confidence_threshold: float = 0.7
    low_confidence_threshold: float = 0.4
    
    # Feature weights (can be tuned)
    weights: Dict[str, float] = field(default_factory=lambda: {
        "momentum": 0.25,
        "imbalance": 0.20,
        "volatility": 0.15,
        "mean_reversion": 0.15,
        "volume": 0.10,
        "spread": 0.10,
        "trend": 0.05
    })


ML_CONFIG = MLConfig()


# =============================================================================
# ALERT CONFIGURATION
# =============================================================================

@dataclass
class AlertConfig:
    """Configuration for alert system."""
    
    # Maximum alerts to display
    max_display_alerts: int = 5
    
    # Alert history size
    max_history_size: int = 500
    
    # Default cooldown between same alerts (seconds)
    default_cooldown: int = 30
    
    # Sound notification (for future use)
    enable_sound: bool = False
    
    # Priority colors
    priority_colors: Dict[str, str] = field(default_factory=lambda: {
        "critical": "#ef4444",
        "high": "#f97316",
        "medium": "#eab308",
        "low": "#22c55e",
        "info": "#3b82f6"
    })


ALERT_CONFIG = AlertConfig()


# =============================================================================
# BACKTEST CONFIGURATION
# =============================================================================

@dataclass
class BacktestConfig:
    """Configuration for strategy backtester."""
    
    # Default capital
    initial_capital: float = 10000.0
    
    # Transaction costs (basis points)
    commission_bps: float = 1.0
    slippage_bps: float = 0.5
    
    # Default stop loss / take profit (percentage)
    default_stop_loss_pct: float = 0.5
    default_take_profit_pct: float = 1.0
    
    # Maximum holding time (seconds)
    max_holding_time: int = 60


BACKTEST_CONFIG = BacktestConfig()


# =============================================================================
# CANDLESTICK CONFIGURATION
# =============================================================================

@dataclass
class CandlestickConfig:
    """Configuration for candlestick chart generation."""
    
    # Candle interval (seconds)
    candle_interval: int = 5
    
    # Maximum candles to display
    max_candles: int = 60
    
    # Moving average periods
    ma_periods: List[int] = field(default_factory=lambda: [10, 20])
    
    # Show volume subplot
    show_volume: bool = True


CANDLE_CONFIG = CandlestickConfig()
