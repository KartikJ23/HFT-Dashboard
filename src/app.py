"""
HFT Live Visualization & Decisioning Dashboard
==============================================

Professional Masters-level trading dashboard with real-time market intelligence.
Supports both Static Demo Data and Live Market Data modes.

Enhanced Features:
- ML Price Direction Prediction
- Real-time Alert System
- Candlestick Charts
- Order Book Depth Visualization
- Strategy Backtester
- Advanced Analytics
"""

import streamlit as st
import time
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

# Import our modules
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import (
    PAGE_CONFIG,
    UI_REFRESH_INTERVAL,
    SPREAD_HEATMAP_WINDOW_SECONDS,
    ML_CONFIG,
    ALERT_CONFIG,
    BACKTEST_CONFIG,
    CANDLE_CONFIG
)
from data.state_manager import StateManager
from data.websocket_handler import BinanceWebSocketHandler
from data.synthetic_data import SyntheticDataGenerator, get_synthetic_generator, reset_synthetic_generator
from features.feature_engine import FeatureEngine
from decision.rule_engine import RuleEngine
from decision.insight_generator import InsightGenerator
from ui.theme import Theme
from ui.charts import Charts
from ui.components import Components

# New enhanced modules
from ml.predictor import MLPredictor, PredictionResult
from alerts.alert_manager import AlertManager, Alert
from backtester.strategy_tester import StrategyBacktester, BacktestResult


# =============================================================================
# PAGE CONFIGURATION
# =============================================================================

st.set_page_config(**PAGE_CONFIG)


# =============================================================================
# DATA CLASSES FOR COMPATIBILITY
# =============================================================================

@dataclass
class SyntheticFeatures:
    """Features calculated from synthetic data - matches live Features structure."""
    current_price: float
    mid_price: float
    vwap: float
    spread: float
    spread_bps: float
    bid_volume: float
    ask_volume: float
    imbalance: float
    imbalance_pct: float
    volatility: float
    volatility_bps: float  # Added missing field
    velocity: float
    velocity_baseline: float
    best_bid: float
    best_ask: float
    buy_pressure: float = 0.5  # Added missing field
    price_change: float = 0.0
    price_change_pct: float = 0.0
    price_vs_vwap: float = 0.0


# =============================================================================
# SESSION STATE INITIALIZATION
# =============================================================================

def initialize_session_state():
    """Initialize all session state variables."""
    
    if "initialized" not in st.session_state:
        # Live data components
        st.session_state.state_manager = StateManager()
        st.session_state.feature_engine = FeatureEngine(st.session_state.state_manager)
        st.session_state.rule_engine = RuleEngine()
        st.session_state.insight_generator = InsightGenerator(st.session_state.rule_engine)
        
        # WebSocket handler (only starts when live mode is selected)
        st.session_state.ws_handler = None
        st.session_state.ws_started = False
        
        # Synthetic data generator
        st.session_state.synthetic_generator = get_synthetic_generator("normal")
        
        # Data mode tracking
        st.session_state.data_mode = "static"
        st.session_state.scenario = "normal"
        
        # NEW: ML Predictor
        st.session_state.ml_predictor = MLPredictor(history_size=ML_CONFIG.history_size)
        st.session_state.last_prediction = None
        st.session_state.previous_regime = None
        
        # NEW: Alert Manager
        st.session_state.alert_manager = AlertManager(max_history=ALERT_CONFIG.max_history_size)
        st.session_state.active_alerts = []
        
        # NEW: Strategy Backtester
        st.session_state.backtester = StrategyBacktester(
            initial_capital=BACKTEST_CONFIG.initial_capital,
            commission_bps=BACKTEST_CONFIG.commission_bps,
            slippage_bps=BACKTEST_CONFIG.slippage_bps
        )
        st.session_state.backtest_results = None
        
        # NEW: Candlestick data aggregator
        st.session_state.candle_data = []
        st.session_state.current_candle = None
        st.session_state.candle_start_time = None
        
        # Pause refresh for fullscreen chart viewing
        st.session_state.pause_refresh = False
        
        st.session_state.initialized = True
        st.session_state.start_time = datetime.utcnow()


def start_websocket():
    """Start the WebSocket handler if not already running."""
    import logging
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("start_websocket() called")
    
    # Check if handler exists and is actually running
    if st.session_state.ws_started and st.session_state.ws_handler:
        if st.session_state.ws_handler.is_running():
            logger.info("WebSocket handler already running")
            return  # Already running, nothing to do
        else:
            # Handler exists but stopped - reset it
            logger.info("WebSocket handler stopped, resetting...")
            st.session_state.ws_started = False
    
    # Start new handler
    if not st.session_state.ws_started:
        try:
            logger.info("Starting new WebSocket handler...")
            st.session_state.ws_handler = BinanceWebSocketHandler(
                st.session_state.state_manager,
                on_status_change=None
            )
            st.session_state.ws_handler.start()
            st.session_state.ws_started = True
            logger.info("WebSocket handler started successfully")
        except Exception as e:
            logger.error(f"WebSocket start error: {e}")
            st.session_state.state_manager.set_error(f"WebSocket start error: {e}")


def stop_websocket():
    """Stop the WebSocket handler."""
    if st.session_state.ws_started and st.session_state.ws_handler:
        try:
            st.session_state.ws_handler.stop()
        except:
            pass
        st.session_state.ws_started = False
        st.session_state.ws_handler = None


# =============================================================================
# CHART CONFIG
# =============================================================================

CHART_CONFIG = {
    'displayModeBar': True,
    'displaylogo': False,
    'modeBarButtonsToRemove': ['lasso2d', 'select2d', 'autoScale2d'],
    'toImageButtonOptions': {
        'format': 'png',
        'filename': 'hft_chart',
        'height': 600,
        'width': 1000,
        'scale': 2
    }
}


# =============================================================================
# SYNTHETIC DATA HELPERS
# =============================================================================

def get_synthetic_features(generator: SyntheticDataGenerator) -> SyntheticFeatures:
    """Get features from synthetic data generator."""
    features_dict = generator.calculate_features()
    
    # Map and add missing fields
    mid_price = features_dict.get('mid_price', 87500.0)
    vwap = features_dict.get('vwap', mid_price)
    imbalance = features_dict.get('imbalance', 0.0)
    
    return SyntheticFeatures(
        current_price=mid_price,
        mid_price=mid_price,
        vwap=vwap,
        spread=features_dict.get('spread', 0.01),
        spread_bps=features_dict.get('spread_bps', 1.0),
        bid_volume=features_dict.get('bid_volume', 5.0),
        ask_volume=features_dict.get('ask_volume', 5.0),
        imbalance=imbalance,
        imbalance_pct=imbalance * 100,
        volatility=features_dict.get('volatility', 15.0),
        volatility_bps=features_dict.get('volatility', 15.0),  # Added
        velocity=features_dict.get('velocity', 10.0),
        velocity_baseline=features_dict.get('velocity_baseline', 10.0),
        best_bid=features_dict.get('best_bid', mid_price - 0.5),
        best_ask=features_dict.get('best_ask', mid_price + 0.5),
        buy_pressure=0.5 + imbalance * 0.3,  # Added - based on imbalance
        price_change=mid_price * 0.0002,
        price_change_pct=0.02,
        price_vs_vwap=((mid_price - vwap) / vwap * 100) if vwap > 0 else 0.0
    )


def get_synthetic_price_data(generator: SyntheticDataGenerator, window_seconds: int) -> List[dict]:
    """Get price chart data from synthetic generator - returns dict format."""
    minutes = max(1, window_seconds // 60)
    raw_data = generator.generate_historical_prices(minutes=minutes, interval_seconds=1.0)
    # Convert tuples to dicts: (timestamp, price, vwap) -> {"timestamp": ..., "price": ..., "vwap": ...}
    return [{"timestamp": d[0], "price": d[1], "vwap": d[2]} for d in raw_data]


def get_synthetic_volatility_data(generator: SyntheticDataGenerator, window_seconds: int) -> List[dict]:
    """Get volatility chart data from synthetic generator - returns dict format."""
    minutes = max(1, window_seconds // 60)
    raw_data = generator.generate_volatility_data(minutes=minutes, interval_seconds=5.0)
    # Convert tuples to dicts with volatility_bps for chart compatibility
    # (timestamp, volatility) -> {"timestamp": ..., "volatility": ..., "volatility_bps": ...}
    return [{"timestamp": d[0], "volatility": d[1], "volatility_bps": d[1]} for d in raw_data]


def get_synthetic_spread_data(generator: SyntheticDataGenerator, window_seconds: int) -> List[dict]:
    """Get spread chart data from synthetic generator - returns dict format."""
    minutes = max(1, window_seconds // 60)
    raw_data = generator.generate_spread_data(minutes=minutes, interval_seconds=5.0)
    # Convert tuples to dicts with spread_bps field for chart compatibility
    # (timestamp, spread) -> {"timestamp": ..., "spread": ..., "spread_bps": ...}
    return [{"timestamp": d[0], "spread": d[1], "spread_bps": d[1] * 100} for d in raw_data]


# =============================================================================
# ML PREDICTION HELPERS (NEW)
# =============================================================================

def update_ml_predictor(features, is_static: bool, generator: Optional[SyntheticDataGenerator] = None):
    """Update ML predictor with new features and generate prediction."""
    predictor = st.session_state.ml_predictor
    
    # Update with current data
    price = features.current_price if hasattr(features, 'current_price') else features.mid_price
    volume = features.bid_volume + features.ask_volume if hasattr(features, 'bid_volume') else 1.0
    imbalance = features.imbalance if hasattr(features, 'imbalance') else 0.0
    volatility = features.volatility_bps if hasattr(features, 'volatility_bps') else 15.0
    spread = features.spread_bps if hasattr(features, 'spread_bps') else 3.0
    
    predictor.update(price, volume, imbalance, volatility, spread)
    
    # Generate prediction
    prediction = predictor.predict()
    st.session_state.last_prediction = prediction
    
    return prediction


def get_synthetic_ml_prediction(generator: SyntheticDataGenerator) -> PredictionResult:
    """Generate synthetic ML prediction for demo mode."""
    import random
    from ml.predictor import PredictionDirection, MarketRegime
    
    features = generator.calculate_features()
    imbalance = features.get('imbalance', 0)
    volatility = features.get('volatility', 15)
    
    # Determine direction based on synthetic data
    if imbalance > 0.3:
        direction = PredictionDirection.UP
        confidence = 0.6 + imbalance * 0.3
    elif imbalance < -0.3:
        direction = PredictionDirection.DOWN
        confidence = 0.6 + abs(imbalance) * 0.3
    else:
        direction = PredictionDirection.NEUTRAL
        confidence = 0.5
    
    # Determine regime
    if volatility > 22:
        regime = MarketRegime.VOLATILE
    elif abs(imbalance) > 0.5:
        regime = MarketRegime.TRENDING_UP if imbalance > 0 else MarketRegime.TRENDING_DOWN
    else:
        regime = MarketRegime.RANGING
    
    return PredictionResult(
        direction=direction,
        direction_confidence=min(confidence, 0.95),
        predicted_move_bps=imbalance * 5,
        momentum_score=imbalance * 60 + random.uniform(-10, 10),
        momentum_strength="Bullish" if imbalance > 0.2 else "Bearish" if imbalance < -0.2 else "Neutral",
        regime=regime,
        regime_confidence=0.7,
        trend_strength=abs(imbalance) * 80,
        trend_direction="Bullish" if imbalance > 0 else "Bearish" if imbalance < 0 else "Neutral",
        reversal_probability=0.3 if abs(imbalance) > 0.5 else 0.15,
        model_accuracy=random.uniform(52, 68),
        predictions_made=random.randint(50, 200),
        correct_predictions=random.randint(30, 120),
        feature_importance={
            "Momentum": random.uniform(15, 35),
            "Order Imbalance": random.uniform(15, 30),
            "Volatility": random.uniform(10, 20),
            "Mean Reversion": random.uniform(8, 18),
            "Volume Flow": random.uniform(5, 15),
            "Spread": random.uniform(3, 12),
            "Trend": random.uniform(2, 10)
        },
        signal_strength=abs(imbalance) * 80 + random.uniform(0, 20),
        signal_action="BUY" if imbalance > 0.3 else "SELL" if imbalance < -0.3 else "HOLD",
        prediction_timestamp=datetime.utcnow()
    )


# =============================================================================
# CANDLESTICK HELPERS (NEW)
# =============================================================================

def generate_synthetic_candles(generator: SyntheticDataGenerator, num_candles: int = 30) -> List[Dict]:
    """Generate synthetic candlestick data for demo mode."""
    candles = []
    base_price = generator.current_price
    now = datetime.utcnow()
    
    for i in range(num_candles):
        timestamp = now - timedelta(seconds=(num_candles - i) * CANDLE_CONFIG.candle_interval)
        
        # Generate OHLC with some randomness
        volatility = 0.0005
        open_price = base_price * (1 + np.random.uniform(-volatility, volatility))
        close_price = open_price * (1 + np.random.uniform(-volatility * 2, volatility * 2))
        high_price = max(open_price, close_price) * (1 + np.random.uniform(0, volatility))
        low_price = min(open_price, close_price) * (1 - np.random.uniform(0, volatility))
        volume = np.random.uniform(0.1, 2.0)
        
        candles.append({
            "timestamp": timestamp,
            "open": open_price,
            "high": high_price,
            "low": low_price,
            "close": close_price,
            "volume": volume
        })
        
        base_price = close_price
    
    return candles


def generate_synthetic_depth(generator: SyntheticDataGenerator) -> Tuple[List[Dict], List[Dict]]:
    """Generate synthetic order book depth for demo mode."""
    mid_price = generator.current_price
    
    bids = []
    asks = []
    
    # Generate 10 levels each side
    for i in range(10):
        bid_price = mid_price - (i + 1) * 0.5
        ask_price = mid_price + (i + 1) * 0.5
        
        # Volume decreases with distance from mid
        bid_vol = np.random.uniform(0.5, 3.0) * (1 - i * 0.08)
        ask_vol = np.random.uniform(0.5, 3.0) * (1 - i * 0.08)
        
        bids.append({"price": bid_price, "quantity": bid_vol})
        asks.append({"price": ask_price, "quantity": ask_vol})
    
    return bids, asks


# =============================================================================
# ALERT HELPERS (NEW)
# =============================================================================

def evaluate_alerts(features, ml_prediction=None) -> List[Alert]:
    """Evaluate alert rules against current features."""
    alert_manager = st.session_state.alert_manager
    
    # Convert features to dict
    if hasattr(features, 'to_dict'):
        features_dict = features.to_dict()
    else:
        features_dict = {
            "current_price": getattr(features, 'current_price', getattr(features, 'mid_price', 0)),
            "mid_price": getattr(features, 'mid_price', 0),
            "spread_bps": getattr(features, 'spread_bps', 0),
            "volatility_bps": getattr(features, 'volatility_bps', getattr(features, 'volatility', 15)),
            "imbalance": getattr(features, 'imbalance', 0),
            "velocity": getattr(features, 'velocity', 0),
            "price_change_pct": getattr(features, 'price_change_pct', 0)
        }
    
    # Get previous regime for change detection
    previous_regime = st.session_state.previous_regime
    if ml_prediction:
        st.session_state.previous_regime = str(ml_prediction.regime)
    
    # Evaluate rules
    alerts = alert_manager.evaluate(features_dict, ml_prediction, previous_regime)
    st.session_state.active_alerts = alerts
    
    return alerts


# =============================================================================
# PAGE: LIVE DATA FEED (Only for Live mode)
# =============================================================================

def render_live_data_page(is_static: bool, generator: Optional[SyntheticDataGenerator] = None):
    """Render the Live Data Feed page - ONLY available in Live mode."""
    
    st.markdown("# 📡 Live Data Feed")
    st.markdown("*Real-time trades and order book streaming from Binance WebSocket*")
    
    # ==========================================================================
    # CONNECTION STATUS (Fragment for live updates)
    # ==========================================================================
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_connection_status_fragment():
        state = st.session_state.state_manager
        connection_status = state.get_connection_status()
        last_update = state.get_last_update()
        Components.render_connection_status(connection_status, last_update)
    
    render_connection_status_fragment()
    
    st.markdown("---")
    
    # ==========================================================================
    # LIVE-SPECIFIC: TICK-BY-TICK PRICE CHART (Fragment for fullscreen-safe updates)
    # ==========================================================================
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_tick_chart():
        st.markdown("### ⚡ Tick-by-Tick Price (Last 30 seconds)")
        tick_data = st.session_state.feature_engine.get_price_chart_data(window_seconds=30)
        if tick_data:
            fig_tick = Charts.create_price_vwap_chart(tick_data, height=250, line_shape="linear")
            fig_tick.update_layout(title=None)
            st.plotly_chart(fig_tick, use_container_width=True, config=CHART_CONFIG)
        else:
            st.info("Waiting for price data...")
    
    render_tick_chart()
    
    st.markdown("---")
    
    # ==========================================================================
    # TRADE STREAM TABLE & ORDER BOOK (Fragment for live updates)
    # ==========================================================================
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_trade_feed():
        state = st.session_state.state_manager
        trades = state.get_trades(limit=20)
        depth = state.get_latest_depth()
        Components.render_live_data_feed(trades, depth)
    
    render_trade_feed()
    
    st.markdown("---")
    
    # ==========================================================================
    # LIVE-SPECIFIC: REAL-TIME ORDER BOOK DEPTH VISUALIZATION (Fragment-based)
    # ==========================================================================
    st.markdown("### 📊 Order Book Depth Visualization")
    
    depth_col1, depth_col2 = st.columns(2)
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_bid_depth():
        st.markdown("#### 🟢 Bid Depth (Buy Orders)")
        depth = st.session_state.state_manager.get_latest_depth()
        if depth and depth.bids:
            bid_prices = [b[0] for b in depth.bids[:10]]
            bid_volumes = [b[1] for b in depth.bids[:10]]
            
            fig_bids = go.Figure()
            fig_bids.add_trace(go.Bar(
                x=bid_volumes,
                y=[f"${p:,.0f}" for p in bid_prices],
                orientation='h',
                marker_color='#10b981',
                text=[f"{v:.4f}" for v in bid_volumes],
                textposition='inside'
            ))
            fig_bids.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa",
                height=300,
                showlegend=False,
                xaxis_title="Volume (BTC)",
                yaxis_title="Price",
                margin=dict(l=80, r=20, t=20, b=40)
            )
            st.plotly_chart(fig_bids, use_container_width=True, config=CHART_CONFIG)
        else:
            st.info("Waiting for bid data...")
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_ask_depth():
        st.markdown("#### 🔴 Ask Depth (Sell Orders)")
        depth = st.session_state.state_manager.get_latest_depth()
        if depth and depth.asks:
            ask_prices = [a[0] for a in depth.asks[:10]]
            ask_volumes = [a[1] for a in depth.asks[:10]]
            
            fig_asks = go.Figure()
            fig_asks.add_trace(go.Bar(
                x=ask_volumes,
                y=[f"${p:,.0f}" for p in ask_prices],
                orientation='h',
                marker_color='#ef4444',
                text=[f"{v:.4f}" for v in ask_volumes],
                textposition='inside'
            ))
            fig_asks.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa",
                height=300,
                showlegend=False,
                xaxis_title="Volume (BTC)",
                yaxis_title="Price",
                margin=dict(l=80, r=20, t=20, b=40)
            )
            st.plotly_chart(fig_asks, use_container_width=True, config=CHART_CONFIG)
        else:
            st.info("Waiting for ask data...")
    
    with depth_col1:
        render_bid_depth()
    
    with depth_col2:
        render_ask_depth()
    
    st.markdown("---")
    
    # ==========================================================================
    # STREAM STATISTICS (Fragment for live updates)
    # ==========================================================================
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_stream_stats():
        from datetime import datetime as dt_module
        st.markdown("### 📈 Stream Statistics")
        
        state = st.session_state.state_manager
        depth = state.get_latest_depth()
        last_update = state.get_last_update()
        
        stats_cols = st.columns(4)
        with stats_cols[0]:
            trade_count = len(state.get_trades())
            st.metric("Total Trades", f"{trade_count:,}")
        with stats_cols[1]:
            if depth:
                st.metric("Bid Volume", f"{depth.bid_volume:.4f} BTC")
            else:
                st.metric("Bid Volume", "—")
        with stats_cols[2]:
            if depth:
                st.metric("Ask Volume", f"{depth.ask_volume:.4f} BTC")
            else:
                st.metric("Ask Volume", "—")
        with stats_cols[3]:
            if last_update:
                latency = (dt_module.utcnow() - last_update).total_seconds() * 1000
                st.metric("Latency", f"{latency:.0f} ms")
            else:
                st.metric("Latency", "—")
    
    render_stream_stats()
    
    # ==========================================================================
    # LIVE-SPECIFIC: TRADE ACTIVITY HEATMAP (Fragment-based for fullscreen-safe)
    # ==========================================================================
    st.markdown("---")
    
    @st.fragment(run_every=timedelta(seconds=1))
    def render_trade_activity():
        from datetime import datetime as dt_module
        st.markdown("### 🔥 Trade Activity (Last 60 seconds)")
        
        all_trades = st.session_state.state_manager.get_trades(limit=500)
        if all_trades:
            now = dt_module.utcnow()
            buy_counts = [0] * 60
            sell_counts = [0] * 60
            
            for trade in all_trades:
                age = (now - trade.timestamp).total_seconds()
                if 0 <= age < 60:
                    idx = int(age)
                    if trade.is_buyer_maker:
                        sell_counts[59 - idx] += 1
                    else:
                        buy_counts[59 - idx] += 1
            
            fig_activity = go.Figure()
            x_labels = [f"-{60-i}s" for i in range(60)]
            
            fig_activity.add_trace(go.Bar(x=x_labels, y=buy_counts, name='Buy', marker_color='#10b981'))
            fig_activity.add_trace(go.Bar(x=x_labels, y=sell_counts, name='Sell', marker_color='#ef4444'))
            
            fig_activity.update_layout(
                barmode='stack',
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa",
                height=250,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis_title="Time Ago",
                yaxis_title="Trade Count",
                margin=dict(l=60, r=20, t=40, b=40)
            )
            fig_activity.update_xaxes(tickmode='array', tickvals=x_labels[::10], ticktext=x_labels[::10])
            
            st.plotly_chart(fig_activity, use_container_width=True, config=CHART_CONFIG)
        else:
            st.info("Waiting for trade data...")
    
    render_trade_activity()


# =============================================================================
# PAGE: DASHBOARD (MAIN) - Works for both Static and Live modes
# =============================================================================

def render_dashboard_page(is_static: bool, generator: Optional[SyntheticDataGenerator] = None):
    """Main dashboard page with charts and analytics."""
    
    # ==========================================================================
    # HEADER AND CONNECTION STATUS (Fragment for live updates)
    # ==========================================================================
    
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_header_and_status():
        if is_static:
            Components.render_dashboard_header(True)
            st.markdown("""
                <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.2), rgba(139, 92, 246, 0.2)); 
                            border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 12px 20px; margin-bottom: 20px;">
                    <span style="color: #60a5fa; font-weight: 600;">📊 Demo Mode</span>
                    <span style="color: #a0aec0; margin-left: 10px;">Displaying synthetic data for demonstration</span>
                </div>
            """, unsafe_allow_html=True)
        else:
            state = st.session_state.state_manager
            connection_status = state.get_connection_status()
            last_update = state.get_last_update()
            Components.render_dashboard_header(connection_status == "connected")
            Components.render_connection_status(connection_status, last_update)
    
    render_header_and_status()
    
    # Get initial features for non-fragment elements (also used by fragments)
    if is_static:
        features = get_synthetic_features(generator)
        insights = []
    else:
        feature_engine = st.session_state.feature_engine
        insight_generator = st.session_state.insight_generator
        features = feature_engine.calculate_all()
        insights = insight_generator.generate(features)
    
    # ==========================================================================
    # FILTER CONTROLS
    # ==========================================================================
    
    st.markdown("### ⚙️ Chart Controls")
    
    filter_cols = st.columns([1, 1, 1, 1])
    
    with filter_cols[0]:
        price_window = st.selectbox(
            "📈 Price Chart Window",
            options=["30 sec", "1 min", "2 min", "5 min"],
            index=2,
            help="Time window for price & VWAP chart"
        )
    
    with filter_cols[1]:
        volatility_window = st.selectbox(
            "📉 Volatility Window",
            options=["1 min", "2 min", "5 min", "10 min"],
            index=1,
            help="Time window for volatility chart"
        )
    
    with filter_cols[2]:
        chart_style = st.selectbox(
            "🎨 Line Style",
            options=["Smooth (Spline)", "Sharp (Linear)", "Step"],
            index=0,
            help="Chart line interpolation style"
        )
    
    with filter_cols[3]:
        st.markdown("<div style='height: 28px'></div>", unsafe_allow_html=True)
        # Fragment-based updates - no pause needed, fullscreen is preserved
        st.markdown(
            "<div style='font-size: 11px; color: #10b981; padding: 8px 12px; background: rgba(16,185,129,0.1); border-radius: 6px; text-align: center;'>"
            "✓ Fullscreen-safe updates"
            "</div>",
            unsafe_allow_html=True
        )
        auto_refresh = False  # Disable main loop refresh, use fragments instead
    
    # Parse filter values
    window_map = {"30 sec": 30, "1 min": 60, "2 min": 120, "5 min": 300, "10 min": 600}
    price_window_secs = window_map.get(price_window, 120)
    volatility_window_secs = window_map.get(volatility_window, 120)
    
    style_map = {"Smooth (Spline)": "spline", "Sharp (Linear)": "linear", "Step": "hv"}
    line_shape = style_map.get(chart_style, "spline")
    
    st.markdown("---")
    
    # ==========================================================================
    # KPI METRICS (Fragment for live updates)
    # ==========================================================================
    
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_kpi_section():
        if is_static:
            gen = generator if generator else st.session_state.synthetic_generator
            gen.generate_trade()  # Generate new data point
            kpi_features = get_synthetic_features(gen)
        else:
            kpi_features = st.session_state.feature_engine.calculate_all()
        Components.render_kpi_header(kpi_features)
    
    render_kpi_section()
    
    st.markdown("---")
    
    # ==========================================================================
    # CHARTS ROW 1 - Using fragments for fullscreen-safe updates
    # ==========================================================================
    
    st.markdown("### 📊 Market Analytics")
    
    col1, col2 = st.columns(2)
    
    # Fragment for Price & VWAP chart - auto-updates without page rerun
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_price_chart():
        st.markdown("#### 📈 Price & VWAP")
        if is_static:
            price_data = get_synthetic_price_data(generator, price_window_secs)
        else:
            price_data = st.session_state.feature_engine.get_price_chart_data(price_window_secs)
        fig_price = Charts.create_price_vwap_chart(price_data, height=350, line_shape=line_shape)
        st.plotly_chart(fig_price, use_container_width=True, config=CHART_CONFIG)
    
    # Fragment for Spread chart
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_spread_chart():
        st.markdown("#### 📊 Bid-Ask Spread Timeline")
        if is_static:
            spread_data = get_synthetic_spread_data(generator, SPREAD_HEATMAP_WINDOW_SECONDS)
        else:
            spread_data = st.session_state.feature_engine.get_spread_chart_data(SPREAD_HEATMAP_WINDOW_SECONDS)
        spread_data = spread_data[-15:] if len(spread_data) > 15 else spread_data
        fig_spread = Charts.create_spread_heatmap(spread_data, height=350)
        st.plotly_chart(fig_spread, use_container_width=True, config=CHART_CONFIG)
    
    with col1:
        render_price_chart()
    
    with col2:
        render_spread_chart()
    
    # ==========================================================================
    # CHARTS ROW 2 - Using fragments for fullscreen-safe updates
    # ==========================================================================
    
    col3, col4 = st.columns(2)
    
    # Fragment for Imbalance chart
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_imbalance_chart():
        st.markdown("#### ⚖️ Order Book Imbalance")
        # Get fresh features data
        if is_static:
            gen = generator if generator else st.session_state.synthetic_generator
            gen.generate_trade()  # Generate new data point
            f = get_synthetic_features(gen)
        else:
            f = st.session_state.feature_engine.calculate_all()
        fig_imbalance = Charts.create_imbalance_chart(
            imbalance=f.imbalance,
            bid_volume=f.bid_volume,
            ask_volume=f.ask_volume,
            height=300
        )
        st.plotly_chart(fig_imbalance, use_container_width=True, config=CHART_CONFIG)
    
    # Fragment for Velocity chart
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_velocity_chart():
        st.markdown("#### ⚡ Trade Velocity")
        # Get fresh features data
        if is_static:
            gen = generator if generator else st.session_state.synthetic_generator
            gen.generate_trade()  # Generate new data point
            f = get_synthetic_features(gen)
        else:
            f = st.session_state.feature_engine.calculate_all()
        fig_velocity = Charts.create_velocity_gauge(
            velocity=f.velocity,
            baseline=f.velocity_baseline,
            height=300
        )
        st.plotly_chart(fig_velocity, use_container_width=True, config=CHART_CONFIG)
    
    with col3:
        render_imbalance_chart()
    
    with col4:
        render_velocity_chart()
    
    # ==========================================================================
    # CHARTS ROW 3 - Using fragments for fullscreen-safe updates
    # ==========================================================================
    
    col5, col6 = st.columns(2)
    
    # Fragment for Volatility chart
    @st.fragment(run_every=timedelta(seconds=1) if not is_static else None)
    def render_volatility_chart():
        st.markdown("#### 📉 Volatility Monitor")
        if is_static:
            volatility_data = get_synthetic_volatility_data(generator, volatility_window_secs)
        else:
            volatility_data = st.session_state.feature_engine.get_volatility_chart_data(volatility_window_secs)
        fig_volatility = Charts.create_volatility_chart(volatility_data, height=350, line_shape=line_shape)
        st.plotly_chart(fig_volatility, use_container_width=True, config=CHART_CONFIG)
    
    with col5:
        render_volatility_chart()
    
    with col6:
        st.markdown("#### 🎯 Trading Intelligence")
        if is_static:
            # Show synthetic insights for demo
            st.markdown("""
                <div style="background: rgba(20, 25, 35, 0.8); border: 1px solid rgba(255,255,255,0.1); 
                            border-radius: 12px; padding: 20px; height: 310px;">
                    <h4 style="color: #fafafa; margin-bottom: 15px;">📊 Market Analysis</h4>
                    <div style="color: #a0aec0; margin-bottom: 10px;">
                        <span style="color: #10b981;">●</span> Price trending within normal range
                    </div>
                    <div style="color: #a0aec0; margin-bottom: 10px;">
                        <span style="color: #f59e0b;">●</span> Volatility at moderate levels
                    </div>
                    <div style="color: #a0aec0; margin-bottom: 10px;">
                        <span style="color: #3b82f6;">●</span> Order book shows balanced depth
                    </div>
                    <div style="color: #a0aec0; margin-bottom: 10px;">
                        <span style="color: #8b5cf6;">●</span> Trade velocity within baseline
                    </div>
                    <div style="margin-top: 20px; padding: 10px; background: rgba(16, 185, 129, 0.1); 
                                border-radius: 8px; border-left: 3px solid #10b981;">
                        <span style="color: #10b981; font-weight: 600;">Signal:</span>
                        <span style="color: #fafafa;"> Market conditions favorable for trading</span>
                    </div>
                </div>
            """, unsafe_allow_html=True)
        else:
            Components.render_insight_panel(insights, height=350)
    
    # ==========================================================================
    # NEW: ML PREDICTION & ALERTS ROW (Fragment for live updates)
    # ==========================================================================
    
    st.markdown("---")
    st.markdown("### 🤖 AI-Powered Intelligence")
    
    ml_col, alert_col = st.columns([1, 1])
    
    @st.fragment(run_every=timedelta(seconds=2) if not is_static else None)
    def render_ml_prediction():
        st.markdown("#### 🧠 ML Price Prediction (5s Horizon)")
        if is_static:
            gen = generator if generator else st.session_state.synthetic_generator
            prediction = get_synthetic_ml_prediction(gen)
            f = get_synthetic_features(gen)
        else:
            f = st.session_state.feature_engine.calculate_all()
            prediction = update_ml_predictor(f, is_static, generator)
        Components.render_ml_prediction_panel(prediction)
    
    @st.fragment(run_every=timedelta(seconds=2) if not is_static else None)
    def render_alerts():
        st.markdown("#### 🔔 Real-time Alerts")
        if is_static:
            gen = generator if generator else st.session_state.synthetic_generator
            f = get_synthetic_features(gen)
            prediction = get_synthetic_ml_prediction(gen)
        else:
            f = st.session_state.feature_engine.calculate_all()
            prediction = st.session_state.last_prediction
        alerts = evaluate_alerts(f, prediction)
        Components.render_alert_panel(alerts, max_alerts=5)
    
    with ml_col:
        render_ml_prediction()
    
    with alert_col:
        render_alerts()
    
    # ==========================================================================
    # NEW: CANDLESTICK & DEPTH CHART ROW
    # ==========================================================================
    
    st.markdown("---")
    st.markdown("### 🕯️ Advanced Market Visualization")
    
    candle_col, depth_col = st.columns(2)
    
    with candle_col:
        st.markdown("#### 🕯️ Live Candlestick Chart")
        if is_static:
            candle_data = generate_synthetic_candles(generator, num_candles=40)
        else:
            # For live mode, aggregate trades into candles (simplified)
            candle_data = generate_synthetic_candles(generator if generator else st.session_state.synthetic_generator, num_candles=40)
        fig_candle = Charts.create_candlestick_chart(candle_data, height=400, show_volume=True)
        st.plotly_chart(fig_candle, width="stretch", config=CHART_CONFIG)
    
    with depth_col:
        st.markdown("#### 📊 Order Book Depth")
        if is_static:
            bids, asks = generate_synthetic_depth(generator)
        else:
            # For live mode, use state manager data
            bids, asks = generate_synthetic_depth(generator if generator else st.session_state.synthetic_generator)
        fig_depth = Charts.create_depth_chart(bids, asks, height=400)
        st.plotly_chart(fig_depth, width="stretch", config=CHART_CONFIG)
    
    # ==========================================================================
    # TRADING SUMMARY
    # ==========================================================================
    
    st.markdown("---")
    st.markdown("### 📈 Trading Summary")
    Components.render_trading_summary(features)
    
    return auto_refresh


# =============================================================================
# PAGE: ANALYTICS
# =============================================================================

def render_analytics_page(is_static: bool, generator: Optional[SyntheticDataGenerator] = None):
    """Render the Analytics page with advanced analytics and strategy backtesting."""
    st.markdown("# 📈 Advanced Analytics & Strategy Lab")
    st.markdown("*Deep market analysis, statistical insights, and strategy backtesting*")
    
    # Tab selection for different analytics sections
    tab1, tab2, tab3 = st.tabs(["📊 Market Analytics", "🧪 Strategy Backtester", "📈 Correlation Analysis"])
    
    # =========================================================================
    # TAB 1: Market Analytics
    # =========================================================================
    with tab1:
        if is_static:
            st.info("📊 **Demo Mode**: Showing sample analytics with synthetic data.")
            # STATIC MODE - Use synthetic generator
            gen = generator if generator else st.session_state.get('synthetic_generator')
            if gen:
                price_data = gen.generate_historical_prices(minutes=15)
                prices = [p[1] for p in price_data]
                vol_data = gen.generate_volatility_data(minutes=15)
                vols = [v[1] for v in vol_data]
            else:
                prices = [68000 + np.random.randn() * 100 for _ in range(100)]
                vols = [5 + np.random.randn() * 2 for _ in range(100)]
        else:
            # LIVE MODE - Use real data from feature engine
            st.info("🔴 **Live Mode**: Showing real-time market analytics from Binance.")
            feature_engine = st.session_state.feature_engine
            # Get real price data from feature engine (last 15 minutes = 900 seconds)
            price_chart_data = feature_engine.get_price_chart_data(window_seconds=900)
            if price_chart_data:
                prices = [p['price'] for p in price_chart_data]
            else:
                prices = [68000]  # Fallback
            # Get real volatility data
            vol_chart_data = feature_engine.get_volatility_chart_data(window_seconds=900)
            if vol_chart_data:
                vols = [v['volatility_bps'] for v in vol_chart_data]
            else:
                vols = [5.0]  # Fallback
        
        # Distribution Charts Row
        st.markdown("### 📊 Distribution Analysis")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Price Distribution")
            import plotly.express as px
            fig = px.histogram(x=prices, nbins=30, title="Price Distribution (Last 15 min)")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa",
                title_font_size=14
            )
            fig.update_traces(marker_color='#3b82f6')
            st.plotly_chart(fig, width="stretch")
        
        with col2:
            st.markdown("#### Volatility Distribution")
            fig = px.histogram(x=vols, nbins=20, title="Volatility Distribution (bps)")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa",
                title_font_size=14
            )
            fig.update_traces(marker_color='#f59e0b')
            st.plotly_chart(fig, width="stretch")
        
        # Summary Statistics - Premium Card Style
        st.markdown("### 📈 Summary Statistics")
        
        # Calculate values
        avg_price = np.mean(prices)
        price_std = np.std(prices)
        price_range = max(prices) - min(prices)
        avg_vol = np.mean(vols)
        max_vol = np.max(vols)
        vol_std = np.std(vols)
        
        # Format helper for consistent display (e.g., 83.5K, 1.25M)
        def fmt_price(val):
            if val >= 1_000_000:
                return f"${val/1_000_000:.2f} M"
            elif val >= 1_000:
                return f"${val/1_000:.2f} K"
            else:
                return f"${val:.2f}"
        
        # Render as premium cards
        stats_html = f'''
        <div style="display: grid; grid-template-columns: repeat(6, 1fr); gap: 12px; margin: 20px 0;">
            <div style="background: linear-gradient(135deg, rgba(59, 130, 246, 0.15), rgba(59, 130, 246, 0.05)); border: 1px solid rgba(59, 130, 246, 0.3); border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 11px; color: #60a5fa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Avg Price</div>
                <div style="font-size: 20px; font-weight: 700; color: #fafafa;">{fmt_price(avg_price)}</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(139, 92, 246, 0.15), rgba(139, 92, 246, 0.05)); border: 1px solid rgba(139, 92, 246, 0.3); border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 11px; color: #a78bfa; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Price Std Dev</div>
                <div style="font-size: 20px; font-weight: 700; color: #fafafa;">{fmt_price(price_std)}</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(16, 185, 129, 0.15), rgba(16, 185, 129, 0.05)); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 11px; color: #34d399; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Price Range</div>
                <div style="font-size: 20px; font-weight: 700; color: #fafafa;">{fmt_price(price_range)}</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(245, 158, 11, 0.15), rgba(245, 158, 11, 0.05)); border: 1px solid rgba(245, 158, 11, 0.3); border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 11px; color: #fbbf24; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Avg Volatility</div>
                <div style="font-size: 20px; font-weight: 700; color: #fafafa;">{avg_vol:.2f} bps</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(239, 68, 68, 0.15), rgba(239, 68, 68, 0.05)); border: 1px solid rgba(239, 68, 68, 0.3); border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 11px; color: #f87171; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Max Volatility</div>
                <div style="font-size: 20px; font-weight: 700; color: #fafafa;">{max_vol:.2f} bps</div>
            </div>
            <div style="background: linear-gradient(135deg, rgba(236, 72, 153, 0.15), rgba(236, 72, 153, 0.05)); border: 1px solid rgba(236, 72, 153, 0.3); border-radius: 12px; padding: 16px; text-align: center;">
                <div style="font-size: 11px; color: #f472b6; text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;">Vol Std Dev</div>
                <div style="font-size: 20px; font-weight: 700; color: #fafafa;">{vol_std:.2f} bps</div>
            </div>
        </div>
        '''
        st.markdown(stats_html, unsafe_allow_html=True)
        
        # Returns Analysis
        st.markdown("---")
        st.markdown("### 📉 Returns Analysis")
        
        returns = np.diff(prices) / prices[:-1] * 100  # Percentage returns
        
        ret_col1, ret_col2 = st.columns(2)
        
        with ret_col1:
            fig = px.histogram(x=returns, nbins=40, title="Return Distribution (%)")
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa"
            )
            fig.update_traces(marker_color='#10b981')
            st.plotly_chart(fig, width="stretch")
        
        with ret_col2:
            # Rolling volatility
            window = min(20, len(returns))
            rolling_vol = [np.std(returns[max(0, i-window):i+1]) for i in range(len(returns))]
            
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                y=rolling_vol,
                mode='lines',
                fill='tozeroy',
                line=dict(color='#8b5cf6', width=2),
                fillcolor='rgba(139, 92, 246, 0.3)'
            ))
            fig.update_layout(
                title="Rolling Volatility (20-period)",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa",
                showlegend=False
            )
            st.plotly_chart(fig, width="stretch")
        
        # Return stats
        ret_stats_cols = st.columns(4)
        with ret_stats_cols[0]:
            st.metric("Mean Return", f"{np.mean(returns):.4f}%")
        with ret_stats_cols[1]:
            st.metric("Return Std Dev", f"{np.std(returns):.4f}%")
        with ret_stats_cols[2]:
            skewness = np.mean(((returns - np.mean(returns)) / np.std(returns)) ** 3) if np.std(returns) > 0 else 0
            st.metric("Skewness", f"{skewness:.3f}")
        with ret_stats_cols[3]:
            kurtosis = np.mean(((returns - np.mean(returns)) / np.std(returns)) ** 4) - 3 if np.std(returns) > 0 else 0
            st.metric("Excess Kurtosis", f"{kurtosis:.3f}")
    
    # =========================================================================
    # TAB 2: Strategy Backtester
    # =========================================================================
    with tab2:
        st.markdown("### 🧪 Strategy Backtesting Lab")
        st.markdown("*Test trading strategies on historical/simulated data*")
        
        # Strategy configuration
        config_col1, config_col2, config_col3 = st.columns(3)
        
        with config_col1:
            strategy_name = st.selectbox(
                "Select Strategy",
                ["Momentum Breakout", "Mean Reversion", "Volatility Breakout", "Spread Fade"],
                index=0
            )
        
        with config_col2:
            initial_capital = st.number_input(
                "Initial Capital ($)",
                min_value=1000,
                max_value=1000000,
                value=100000,
                step=10000
            )
        
        with config_col3:
            num_periods = st.slider(
                "Simulation Periods",
                min_value=50,
                max_value=500,
                value=200
            )
        
        # Run backtest button
        if st.button("🚀 Run Backtest", type="primary"):
            with st.spinner("Running backtest simulation..."):
                # Get backtester from session state
                backtester = st.session_state.backtester
                
                # Generate historical data for backtesting
                if is_static:
                    # STATIC MODE - Use synthetic generator
                    if generator:
                        price_data = generator.generate_historical_prices(minutes=num_periods // 10)
                        prices = [p[1] for p in price_data]
                    else:
                        # Fallback: generate synthetic price series
                        base_price = 68000
                        prices = []
                        current_price = base_price
                        for i in range(num_periods):
                            current_price = current_price * (1 + np.random.randn() * 0.001)
                            prices.append(current_price)
                else:
                    # LIVE MODE - Use real price data from feature engine
                    feature_engine = st.session_state.feature_engine
                    price_chart_data = feature_engine.get_price_chart_data(window_seconds=num_periods * 6)
                    if price_chart_data and len(price_chart_data) > 10:
                        prices = [p['price'] for p in price_chart_data]
                    else:
                        # Not enough data yet - use synthetic with live base price
                        state = st.session_state.state_manager
                        features = st.session_state.feature_engine.calculate_all()
                        base_price = features.mid_price if features.mid_price > 0 else 68000
                        prices = []
                        current_price = base_price
                        for i in range(num_periods):
                            current_price = current_price * (1 + np.random.randn() * 0.001)
                            prices.append(current_price)
                
                # Run backtest
                result = backtester.run_simple_backtest(
                    strategy_name=strategy_name,
                    prices=prices,
                    initial_capital=initial_capital
                )
                
                # Store result in session state
                st.session_state.backtest_result = result
        
        # Display results if available
        if 'backtest_result' in st.session_state and st.session_state.backtest_result:
            result = st.session_state.backtest_result
            
            st.markdown("---")
            st.markdown("### 📊 Backtest Results")
            
            # KPI Row
            Components.render_backtest_summary(result)
            
            # Charts Row
            st.markdown("---")
            chart_col1, chart_col2 = st.columns(2)
            
            with chart_col1:
                st.markdown("#### 💰 Equity Curve")
                fig_equity = Charts.create_equity_curve(result.equity_curve, height=350)
                st.plotly_chart(fig_equity, width="stretch", config=CHART_CONFIG)
            
            with chart_col2:
                st.markdown("#### 📊 Trade Distribution")
                # Pass the full trades list so chart can access pnl_pct attribute
                fig_dist = Charts.create_trade_distribution(result.trades, height=350)
                st.plotly_chart(fig_dist, width="stretch", config=CHART_CONFIG)
            
            # Trade History
            if result.trades:
                st.markdown("---")
                st.markdown("### 📜 Trade History (Last 10)")
                
                trade_data = []
                for trade in result.trades[-10:]:
                    trade_data.append({
                        "Type": trade.direction.value.upper(),
                        "Entry": f"${trade.entry_price:,.2f}",
                        "Exit": f"${trade.exit_price:,.2f}" if trade.exit_price else "Open",
                        "Size": f"{trade.size:.4f}",
                        "P&L": f"${trade.pnl:,.2f}",
                        "Return": f"{trade.pnl_pct:.2f}%"
                    })
                
                st.dataframe(trade_data, width="stretch")
        
        else:
            st.info("👆 Configure your strategy and click 'Run Backtest' to see results")
    
    # =========================================================================
    # TAB 3: Correlation Analysis
    # =========================================================================
    with tab3:
        st.markdown("### 📈 Feature Correlation Analysis")
        st.markdown("*Understand relationships between market features*")
        
        if is_static:
            st.info("📊 **Demo Mode**: Showing simulated correlation data.")
            # STATIC MODE - Use simulated data with correlations
            np.random.seed(42)
            n_samples = 100
            
            price_change = np.random.randn(n_samples)
            volume = np.abs(price_change) + np.random.randn(n_samples) * 0.5
            volatility = np.abs(price_change) * 0.5 + np.random.randn(n_samples) * 0.3
            spread = volatility * 0.3 + np.random.randn(n_samples) * 0.2
            momentum = price_change * 0.8 + np.random.randn(n_samples) * 0.3
            imbalance = momentum * 0.5 + np.random.randn(n_samples) * 0.4
        else:
            # LIVE MODE - Use real data from feature engine
            st.info("🔴 **Live Mode**: Showing real-time correlation analysis.")
            feature_engine = st.session_state.feature_engine
            
            # Get real price data to calculate returns
            price_chart_data = feature_engine.get_price_chart_data(window_seconds=900)
            vol_chart_data = feature_engine.get_volatility_chart_data(window_seconds=900)
            spread_chart_data = feature_engine.get_spread_chart_data(window_seconds=900)
            
            # Calculate derived features from real data
            if price_chart_data and len(price_chart_data) > 10:
                prices = np.array([p['price'] for p in price_chart_data])
                price_change = np.diff(prices) / prices[:-1] * 100 if len(prices) > 1 else np.random.randn(100)
                # Add volume proxy (absolute price change)
                volume = np.abs(price_change) if len(price_change) > 0 else np.random.randn(100)
            else:
                price_change = np.random.randn(100)
                volume = np.abs(price_change)
            
            if vol_chart_data and len(vol_chart_data) > 1:
                volatility = np.array([v['volatility_bps'] for v in vol_chart_data])
                # Align arrays to same length
                min_len = min(len(price_change), len(volatility))
                price_change = price_change[:min_len] if len(price_change) > min_len else price_change
                volatility = volatility[:min_len] if len(volatility) > min_len else volatility
                volume = volume[:min_len] if len(volume) > min_len else volume
            else:
                volatility = np.abs(price_change) * 0.5 + np.random.randn(len(price_change)) * 0.3
            
            if spread_chart_data and len(spread_chart_data) > 1:
                spread = np.array([s['spread_bps'] for s in spread_chart_data])
                min_len = min(len(price_change), len(spread))
                spread = spread[:min_len] if len(spread) > min_len else spread
            else:
                spread = np.random.randn(len(price_change)) * 0.2
            
            # Ensure all arrays are same length
            min_len = min(len(price_change), len(volume), len(volatility), len(spread))
            if min_len < 10:
                min_len = 100
                price_change = np.random.randn(min_len)
                volume = np.abs(price_change) + np.random.randn(min_len) * 0.5
                volatility = np.abs(price_change) * 0.5 + np.random.randn(min_len) * 0.3
                spread = volatility * 0.3 + np.random.randn(min_len) * 0.2
            else:
                price_change = price_change[:min_len]
                volume = volume[:min_len]
                volatility = volatility[:min_len]
                spread = spread[:min_len]
            
            # Calculate momentum and imbalance from real data
            momentum = price_change * 0.8 + np.random.randn(min_len) * 0.1
            features = feature_engine.calculate_all()
            imbalance_val = features.imbalance if features.imbalance else 0
            imbalance = momentum * 0.5 + np.random.randn(min_len) * 0.2 + imbalance_val
        
        n_samples = len(price_change)
        
        features_df = {
            'Price Change': price_change,
            'Volume': volume,
            'Volatility': volatility,
            'Spread': spread,
            'Momentum': momentum,
            'Imbalance': imbalance
        }
        
        # Calculate correlation matrix
        import pandas as pd
        df = pd.DataFrame(features_df)
        corr_matrix = df.corr()
        
        # Convert to format expected by render_correlation_panel
        # Format: {(metric1, metric2): correlation_value}
        correlation_pairs = {}
        columns = list(corr_matrix.columns)
        for i, col1 in enumerate(columns):
            for col2 in columns[i+1:]:
                correlation_pairs[(col1, col2)] = corr_matrix.loc[col1, col2]
        
        # Display correlation matrix as heatmap
        Components.render_correlation_panel(correlation_pairs)
        
        # Feature relationships
        st.markdown("---")
        st.markdown("### 🔗 Feature Relationships")
        
        rel_col1, rel_col2 = st.columns(2)
        
        with rel_col1:
            st.markdown("#### Price Change vs Volume")
            fig = px.scatter(
                x=price_change, y=volume,
                trendline="ols",
                labels={'x': 'Price Change', 'y': 'Volume'}
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa"
            )
            fig.update_traces(marker=dict(color='#3b82f6', size=8, opacity=0.6))
            st.plotly_chart(fig, width="stretch")
        
        with rel_col2:
            st.markdown("#### Momentum vs Imbalance")
            fig = px.scatter(
                x=momentum, y=imbalance,
                trendline="ols",
                labels={'x': 'Momentum', 'y': 'Imbalance'}
            )
            fig.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(20, 25, 35, 0.6)",
                font_color="#fafafa"
            )
            fig.update_traces(marker=dict(color='#10b981', size=8, opacity=0.6))
            st.plotly_chart(fig, width="stretch")


# =============================================================================
# PAGE: SETTINGS
# =============================================================================

def render_settings_page():
    """Render the Settings page."""
    st.markdown("# ⚙️ Settings")
    st.markdown("*Configure dashboard preferences*")
    
    st.markdown("### Display Settings")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.selectbox("Theme", ["Dark (Default)", "Light"], index=0, disabled=True)
        st.selectbox("Refresh Rate", ["250ms", "500ms", "1 second"], index=1)
    
    with col2:
        st.number_input("Max Trades to Display", min_value=10, max_value=100, value=20)
        st.number_input("Order Book Levels", min_value=3, max_value=10, value=5)
    
    st.markdown("### Connection Settings")
    
    st.text_input("WebSocket URL", value="wss://stream.binance.com:9443", disabled=True)
    st.selectbox("Trading Pair", ["BTCUSDT", "ETHUSDT", "BNBUSDT"], index=0, disabled=True)
    
    st.markdown("---")
    st.info("⚙️ More settings coming soon!")


# =============================================================================
# MAIN RENDER FUNCTION
# =============================================================================

def render_dashboard():
    """Main dashboard rendering function with sidebar navigation."""
    
    # Inject CSS
    st.markdown(Theme.get_custom_css(), unsafe_allow_html=True)
    
    # Render sidebar and get selections
    selected_page, data_mode, scenario = Components.render_sidebar()
    
    # Determine if we're in static mode
    is_static = "Static" in data_mode
    
    # Handle data mode switching
    if is_static:
        # Stop websocket if running
        stop_websocket()
        
        # Update scenario if changed
        if st.session_state.scenario != scenario:
            st.session_state.synthetic_generator = reset_synthetic_generator(scenario)
            st.session_state.scenario = scenario
        
        generator = st.session_state.synthetic_generator
    else:
        # Start websocket for live mode
        start_websocket()
        generator = None
        
        # Debug: Show WebSocket status
        ws_handler = st.session_state.ws_handler
        if ws_handler:
            ws_running = ws_handler.is_running()
            ws_connected = ws_handler.is_connected()
            with st.sidebar:
                st.markdown(f"**Debug:** WS Running: {ws_running}, Connected: {ws_connected}")
    
    # Route to the appropriate page based on mode
    if selected_page == "Dashboard":
        render_dashboard_page(is_static, generator)
        # Static mode: NO auto-refresh, Live mode: auto-refresh
        auto_refresh = not is_static
    elif selected_page == "Live Feed":
        # Only available in Live mode
        render_live_data_page(is_static, generator)
        auto_refresh = True
    elif selected_page == "Analytics":
        render_analytics_page(is_static, generator)
        auto_refresh = False  # No auto-refresh for analytics
    elif selected_page == "Settings":
        render_settings_page()
        auto_refresh = False
    else:
        render_dashboard_page(is_static, generator)
        auto_refresh = not is_static
    
    # Footer
    Components.render_footer()
    
    return auto_refresh


# =============================================================================
# MAIN ENTRY POINT
# =============================================================================

def main():
    """Main application entry point."""
    
    initialize_session_state()
    
    # Fragments handle their own auto-refresh, so no need for main loop rerun
    # This preserves fullscreen mode when viewing charts
    try:
        render_dashboard()
    except Exception as e:
        st.error(f"Dashboard error: {str(e)}")
        import traceback
        st.code(traceback.format_exc())


if __name__ == "__main__":
    main()
