"""
HFT Live Dashboard - Feature Engine
=====================================

Calculates all trading features from raw data.
Features:
- Mid Price, Spread, Spread (bps)
- VWAP (30-second window)
- Order Book Imbalance (top 10 levels)
- Trade Velocity (3-second smoothed)
- Volatility (60-second rolling std dev)
- Buy Pressure (30-second window)
- Price vs VWAP percentage
"""

import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional, List, Any
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    VWAP_WINDOW_SECONDS,
    VELOCITY_WINDOW_SECONDS,
    VOLATILITY_WINDOW_SECONDS,
    BUY_PRESSURE_WINDOW_SECONDS,
    DEFAULT_VELOCITY_BASELINE
)
from data.state_manager import StateManager, Trade, DepthSnapshot


@dataclass
class Features:
    """Container for all calculated features."""
    # Core metrics
    mid_price: float = 0.0
    spread: float = 0.0
    spread_bps: float = 0.0
    
    # VWAP
    vwap: float = 0.0
    price_vs_vwap: float = 0.0
    
    # Order book
    imbalance: float = 0.0
    imbalance_pct: float = 0.0
    bid_volume: float = 0.0
    ask_volume: float = 0.0
    
    # Trade flow
    velocity: float = 0.0
    velocity_baseline: float = DEFAULT_VELOCITY_BASELINE
    buy_pressure: float = 0.5
    
    # Volatility
    volatility_bps: float = 0.0
    
    # Current price
    current_price: float = 0.0
    price_change: float = 0.0
    price_change_pct: float = 0.0
    
    # Timestamp
    timestamp: datetime = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for easy access."""
        return {
            "mid_price": self.mid_price,
            "spread": self.spread,
            "spread_bps": self.spread_bps,
            "vwap": self.vwap,
            "price_vs_vwap": self.price_vs_vwap,
            "imbalance": self.imbalance,
            "imbalance_pct": self.imbalance_pct,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "velocity": self.velocity,
            "velocity_baseline": self.velocity_baseline,
            "buy_pressure": self.buy_pressure,
            "volatility_bps": self.volatility_bps,
            "current_price": self.current_price,
            "price_change": self.price_change,
            "price_change_pct": self.price_change_pct,
            "timestamp": self.timestamp
        }


class FeatureEngine:
    """
    Calculates all trading features from StateManager data.
    
    All calculations handle edge cases:
    - Empty data returns sensible defaults
    - Division by zero is prevented
    - Invalid data is filtered
    """
    
    def __init__(self, state_manager: StateManager):
        """
        Initialize the feature engine.
        
        Args:
            state_manager: StateManager instance containing raw data
        """
        self.state = state_manager
        
        # Cache for previous values (for change calculations)
        self._previous_price: Optional[float] = None
        self._first_price: Optional[float] = None
        
        # Smoothing for velocity
        self._velocity_ema: float = 0.0
        self._velocity_alpha: float = 0.3  # EMA smoothing factor
    
    def calculate_all(self) -> Features:
        """
        Calculate all features from current state.
        
        Returns:
            Features dataclass with all calculated values
        """
        now = datetime.utcnow()
        features = Features(timestamp=now)
        
        try:
            # Get latest depth for spread/imbalance calculations
            depth = self.state.get_latest_depth()
            
            if depth:
                # Mid price and spread
                features.mid_price = self._calculate_mid_price(depth)
                features.spread = self._calculate_spread(depth)
                features.spread_bps = self._calculate_spread_bps(depth)
                
                # Order book imbalance
                features.imbalance = self._calculate_imbalance(depth)
                features.imbalance_pct = features.imbalance * 100
                features.bid_volume = depth.bid_volume
                features.ask_volume = depth.ask_volume
            
            # Current price
            features.current_price = self.state.get_current_price()
            
            # Store first price for session change calculation
            if self._first_price is None and features.current_price > 0:
                self._first_price = features.current_price
            
            # Price change
            features.price_change, features.price_change_pct = self._calculate_price_change(
                features.current_price
            )
            
            # VWAP (30-second window)
            features.vwap = self._calculate_vwap(now)
            
            # Price vs VWAP
            features.price_vs_vwap = self._calculate_price_vs_vwap(
                features.current_price, features.vwap
            )
            
            # Trade velocity (3-second window, smoothed)
            features.velocity = self._calculate_velocity(now)
            features.velocity_baseline = self.state.get_velocity_baseline()
            
            # Buy pressure (30-second window)
            features.buy_pressure = self._calculate_buy_pressure(now)
            
            # Volatility (60-second rolling)
            features.volatility_bps = self._calculate_volatility(now)
            
            # Update state with derived data for charting
            self._update_history(features)
            
        except Exception as e:
            # Log error but don't crash - return partial features
            print(f"Feature calculation error: {e}")
            import traceback
            traceback.print_exc()
        
        return features
    
    # =========================================================================
    # CORE CALCULATIONS
    # =========================================================================
    
    def _calculate_mid_price(self, depth: DepthSnapshot) -> float:
        """Calculate mid price from order book."""
        if depth.best_bid <= 0 or depth.best_ask <= 0:
            return 0.0
        return (depth.best_bid + depth.best_ask) / 2
    
    def _calculate_spread(self, depth: DepthSnapshot) -> float:
        """Calculate absolute spread."""
        if depth.best_bid <= 0 or depth.best_ask <= 0:
            return 0.0
        return depth.best_ask - depth.best_bid
    
    def _calculate_spread_bps(self, depth: DepthSnapshot) -> float:
        """Calculate spread in basis points."""
        mid_price = self._calculate_mid_price(depth)
        spread = self._calculate_spread(depth)
        
        if mid_price <= 0:
            return 0.0
        
        return (spread / mid_price) * 10000
    
    def _calculate_imbalance(self, depth: DepthSnapshot) -> float:
        """
        Calculate order book imbalance.
        
        Formula: (bid_volume - ask_volume) / (bid_volume + ask_volume)
        Range: -1.0 (all asks) to +1.0 (all bids)
        """
        total_volume = depth.bid_volume + depth.ask_volume
        
        if total_volume <= 0:
            return 0.0
        
        return (depth.bid_volume - depth.ask_volume) / total_volume
    
    def _calculate_price_change(self, current_price: float) -> tuple:
        """Calculate price change from session start."""
        if self._first_price is None or self._first_price <= 0:
            return 0.0, 0.0
        
        if current_price <= 0:
            return 0.0, 0.0
        
        change = current_price - self._first_price
        change_pct = (change / self._first_price) * 100
        
        return change, change_pct
    
    # =========================================================================
    # VWAP CALCULATION
    # =========================================================================
    
    def _calculate_vwap(self, now: datetime) -> float:
        """
        Calculate Volume-Weighted Average Price.
        
        Formula: Σ(Price × Quantity) / Σ(Quantity)
        Window: Last VWAP_WINDOW_SECONDS seconds
        """
        cutoff = now - timedelta(seconds=VWAP_WINDOW_SECONDS)
        trades = self.state.get_trades_since(cutoff)
        
        if not trades:
            # Return current price if no trades
            return self.state.get_current_price()
        
        total_value = 0.0
        total_volume = 0.0
        
        for trade in trades:
            total_value += trade.price * trade.quantity
            total_volume += trade.quantity
        
        if total_volume <= 0:
            return self.state.get_current_price()
        
        return total_value / total_volume
    
    def _calculate_price_vs_vwap(self, price: float, vwap: float) -> float:
        """
        Calculate price deviation from VWAP as percentage.
        
        Formula: ((Price - VWAP) / VWAP) × 100
        """
        if vwap <= 0 or price <= 0:
            return 0.0
        
        return ((price - vwap) / vwap) * 100
    
    # =========================================================================
    # VELOCITY CALCULATION
    # =========================================================================
    
    def _calculate_velocity(self, now: datetime) -> float:
        """
        Calculate trade velocity (trades per second).
        
        Uses exponential moving average for smoothing.
        Window: Last VELOCITY_WINDOW_SECONDS seconds
        """
        cutoff = now - timedelta(seconds=VELOCITY_WINDOW_SECONDS)
        trades = self.state.get_trades_since(cutoff)
        
        raw_velocity = len(trades) / VELOCITY_WINDOW_SECONDS
        
        # Apply EMA smoothing
        self._velocity_ema = (
            self._velocity_alpha * raw_velocity + 
            (1 - self._velocity_alpha) * self._velocity_ema
        )
        
        return self._velocity_ema
    
    # =========================================================================
    # BUY PRESSURE CALCULATION
    # =========================================================================
    
    def _calculate_buy_pressure(self, now: datetime) -> float:
        """
        Calculate buy pressure ratio.
        
        Formula: Buy Volume / Total Volume
        Window: Last BUY_PRESSURE_WINDOW_SECONDS seconds
        
        Note: is_buyer_maker=True means the taker was a seller (market sell)
              is_buyer_maker=False means the taker was a buyer (market buy)
        """
        cutoff = now - timedelta(seconds=BUY_PRESSURE_WINDOW_SECONDS)
        trades = self.state.get_trades_since(cutoff)
        
        if not trades:
            return 0.5  # Neutral
        
        buy_volume = 0.0
        total_volume = 0.0
        
        for trade in trades:
            total_volume += trade.quantity
            if not trade.is_buyer_maker:  # Taker was buyer = market buy
                buy_volume += trade.quantity
        
        if total_volume <= 0:
            return 0.5
        
        return buy_volume / total_volume
    
    # =========================================================================
    # VOLATILITY CALCULATION
    # =========================================================================
    
    def _calculate_volatility(self, now: datetime) -> float:
        """
        Calculate rolling volatility in basis points.
        
        Uses standard deviation of log returns.
        Window: Last VOLATILITY_WINDOW_SECONDS seconds
        """
        cutoff = now - timedelta(seconds=VOLATILITY_WINDOW_SECONDS)
        trades = self.state.get_trades_since(cutoff)
        
        if len(trades) < 10:  # Need minimum trades for meaningful volatility
            return 0.0
        
        # Extract prices
        prices = [t.price for t in trades]
        
        if len(prices) < 2:
            return 0.0
        
        # Calculate returns
        returns = []
        for i in range(1, len(prices)):
            if prices[i-1] > 0:
                ret = (prices[i] - prices[i-1]) / prices[i-1]
                returns.append(ret)
        
        if len(returns) < 2:
            return 0.0
        
        # Standard deviation of returns (in bps)
        std_dev = np.std(returns)
        volatility_bps = std_dev * 10000
        
        return volatility_bps
    
    # =========================================================================
    # HISTORY UPDATES
    # =========================================================================
    
    def _update_history(self, features: Features) -> None:
        """Update historical data buffers for charting."""
        now = features.timestamp or datetime.utcnow()
        
        # Update price history
        if features.current_price > 0:
            self.state.add_price_point(
                timestamp=now,
                price=features.current_price,
                vwap=features.vwap if features.vwap > 0 else features.current_price
            )
        
        # Update spread history (sample less frequently)
        spread_history = self.state.get_spread_history()
        should_sample = True
        if spread_history:
            last_spread = spread_history[-1]
            if (now - last_spread.timestamp).total_seconds() < 1.0:
                should_sample = False
        
        if should_sample and features.spread_bps >= 0:
            self.state.add_spread_point(
                timestamp=now,
                spread_bps=features.spread_bps
            )
        
        # Update volatility history
        vol_history = self.state.get_volatility_history()
        should_sample_vol = True
        if vol_history:
            last_vol = vol_history[-1]
            if (now - last_vol.timestamp).total_seconds() < 1.0:
                should_sample_vol = False
        
        if should_sample_vol:
            self.state.add_volatility_point(
                timestamp=now,
                volatility_bps=features.volatility_bps
            )
        
        # Update velocity history
        self.state.add_velocity_point(
            timestamp=now,
            velocity=features.velocity
        )
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_price_chart_data(self, window_seconds: int = 120) -> List[Dict]:
        """
        Get price and VWAP data for charting.
        
        Args:
            window_seconds: Number of seconds to include
            
        Returns:
            List of dicts with timestamp, price, vwap
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        history = self.state.get_price_history()
        
        return [
            {
                "timestamp": p.timestamp,
                "price": p.price,
                "vwap": p.vwap
            }
            for p in history
            if p.timestamp >= cutoff
        ]
    
    def get_spread_chart_data(self, window_seconds: int = 60) -> List[Dict]:
        """Get spread data for heatmap."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        history = self.state.get_spread_history()
        
        return [
            {
                "timestamp": s.timestamp,
                "spread_bps": s.spread_bps
            }
            for s in history
            if s.timestamp >= cutoff
        ]
    
    def get_volatility_chart_data(self, window_seconds: int = 180) -> List[Dict]:
        """Get volatility data for charting."""
        now = datetime.utcnow()
        cutoff = now - timedelta(seconds=window_seconds)
        
        history = self.state.get_volatility_history()
        
        return [
            {
                "timestamp": v.timestamp,
                "volatility_bps": v.volatility_bps
            }
            for v in history
            if v.timestamp >= cutoff
        ]


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    """Test the feature engine with mock data."""
    from datetime import datetime, timedelta
    import random
    
    print("Testing Feature Engine...")
    print("=" * 50)
    
    # Create state manager
    state = StateManager()
    
    # Generate mock trades
    base_price = 42000.0
    now = datetime.utcnow()
    
    for i in range(100):
        price = base_price + random.uniform(-50, 50)
        state.add_trade_raw(
            timestamp=now - timedelta(seconds=60-i*0.6),
            price=price,
            quantity=random.uniform(0.001, 0.1),
            is_buyer_maker=random.choice([True, False]),
            trade_id=i
        )
    
    # Generate mock depth
    state.add_depth_raw(
        timestamp=now,
        bids=[[str(base_price - i), str(random.uniform(0.5, 2.0))] for i in range(10)],
        asks=[[str(base_price + 1 + i), str(random.uniform(0.5, 2.0))] for i in range(10)]
    )
    
    # Create engine and calculate features
    engine = FeatureEngine(state)
    features = engine.calculate_all()
    
    # Print results
    print(f"\n{'Feature':<20} {'Value':>15}")
    print("-" * 40)
    print(f"{'Mid Price':<20} ${features.mid_price:>14,.2f}")
    print(f"{'Spread':<20} ${features.spread:>14,.4f}")
    print(f"{'Spread (bps)':<20} {features.spread_bps:>14.2f}")
    print(f"{'VWAP':<20} ${features.vwap:>14,.2f}")
    print(f"{'Price vs VWAP':<20} {features.price_vs_vwap:>14.4f}%")
    print(f"{'Imbalance':<20} {features.imbalance:>14.4f}")
    print(f"{'Imbalance %':<20} {features.imbalance_pct:>14.2f}%")
    print(f"{'Velocity':<20} {features.velocity:>14.2f}/s")
    print(f"{'Buy Pressure':<20} {features.buy_pressure:>14.2f}")
    print(f"{'Volatility (bps)':<20} {features.volatility_bps:>14.2f}")
    
    print("\nTest complete!")
