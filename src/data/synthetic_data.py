"""
HFT Dashboard - Synthetic Data Generator
==========================================

Generates realistic synthetic trading data for demonstration and testing.
This allows the dashboard to work without live WebSocket connection.
"""

import random
import math
import time
from datetime import datetime, timedelta
from typing import List, Tuple, Optional
from dataclasses import dataclass, field
import numpy as np


@dataclass
class SyntheticTrade:
    """Represents a synthetic trade."""
    timestamp: datetime
    price: float
    quantity: float
    is_buyer_maker: bool
    trade_id: int


@dataclass
class SyntheticDepth:
    """Represents synthetic order book depth."""
    bids: List[Tuple[float, float]]  # (price, quantity)
    asks: List[Tuple[float, float]]  # (price, quantity)
    best_bid: float
    best_ask: float
    bid_volume: float
    ask_volume: float
    timestamp: datetime


class SyntheticDataGenerator:
    """
    Generates realistic synthetic trading data for BTC/USDT.
    
    Features:
    - Realistic price movements with trends and volatility
    - Order book depth with realistic spreads
    - Trade flow with realistic volumes
    - Multiple market scenarios (trending, ranging, volatile)
    """
    
    def __init__(
        self,
        base_price: float = 87500.0,
        volatility: float = 0.0002,
        trend_strength: float = 0.00001,
        scenario: str = "normal"
    ):
        """
        Initialize the synthetic data generator.
        
        Args:
            base_price: Starting price for BTC/USDT
            volatility: Price volatility factor (higher = more volatile)
            trend_strength: Trend bias factor
            scenario: Market scenario - "normal", "bullish", "bearish", "volatile", "ranging"
        """
        self.base_price = base_price
        self.current_price = base_price
        self.volatility = volatility
        self.trend_strength = trend_strength
        self.scenario = scenario
        self.trade_id_counter = 1000000
        
        # Internal state
        self._trend_direction = 0.0
        self._momentum = 0.0
        self._last_update = datetime.utcnow()
        
        # Trade history for VWAP calculation
        self._trade_history: List[SyntheticTrade] = []
        self._price_history: List[Tuple[datetime, float]] = []
        
        # Configure scenario
        self._configure_scenario()
    
    def _configure_scenario(self):
        """Configure parameters based on market scenario."""
        scenarios = {
            "normal": {"volatility": 0.0002, "trend": 0.0, "spread_mult": 1.0},
            "bullish": {"volatility": 0.0003, "trend": 0.00005, "spread_mult": 0.8},
            "bearish": {"volatility": 0.0003, "trend": -0.00005, "spread_mult": 0.8},
            "volatile": {"volatility": 0.0008, "trend": 0.0, "spread_mult": 1.5},
            "ranging": {"volatility": 0.0001, "trend": 0.0, "spread_mult": 0.6},
        }
        
        config = scenarios.get(self.scenario, scenarios["normal"])
        self.volatility = config["volatility"]
        self._trend_direction = config["trend"]
        self._spread_multiplier = config["spread_mult"]
    
    def set_scenario(self, scenario: str):
        """Change market scenario."""
        self.scenario = scenario
        self._configure_scenario()
    
    def _generate_price_movement(self) -> float:
        """Generate realistic price movement using geometric Brownian motion."""
        # Random walk component
        random_walk = random.gauss(0, 1) * self.volatility * self.current_price
        
        # Trend component
        trend = self._trend_direction * self.current_price
        
        # Momentum component (prices tend to continue in same direction briefly)
        self._momentum = 0.7 * self._momentum + 0.3 * random_walk
        
        # Mean reversion (prices tend to revert to base over time)
        reversion = (self.base_price - self.current_price) * 0.00001
        
        # Combine all components
        price_change = random_walk + trend + self._momentum * 0.3 + reversion
        
        return price_change
    
    def generate_trade(self) -> SyntheticTrade:
        """Generate a single synthetic trade."""
        # Update price
        price_change = self._generate_price_movement()
        self.current_price = max(self.current_price + price_change, self.base_price * 0.5)
        
        # Generate trade details
        # Quantity follows a power law distribution (many small, few large trades)
        quantity = random.paretovariate(2.5) * 0.001
        quantity = min(quantity, 5.0)  # Cap at 5 BTC
        quantity = round(quantity, 5)
        
        # Buyer/seller - slightly biased by trend
        buy_probability = 0.5 + self._trend_direction * 100
        is_buyer_maker = random.random() > buy_probability
        
        # Create trade
        trade = SyntheticTrade(
            timestamp=datetime.utcnow(),
            price=round(self.current_price, 2),
            quantity=quantity,
            is_buyer_maker=is_buyer_maker,
            trade_id=self.trade_id_counter
        )
        
        self.trade_id_counter += 1
        self._trade_history.append(trade)
        
        # Keep only last 1000 trades
        if len(self._trade_history) > 1000:
            self._trade_history = self._trade_history[-1000:]
        
        return trade
    
    def generate_trades(self, count: int = 100) -> List[SyntheticTrade]:
        """Generate multiple synthetic trades."""
        trades = []
        base_time = datetime.utcnow() - timedelta(seconds=count * 0.1)
        
        for i in range(count):
            trade = self.generate_trade()
            # Backdate trades for historical data
            trade.timestamp = base_time + timedelta(seconds=i * 0.1 + random.uniform(0, 0.05))
            trades.append(trade)
        
        return trades
    
    def generate_depth(self) -> SyntheticDepth:
        """Generate synthetic order book depth."""
        # Base spread (typically 0.01% for BTC/USDT)
        base_spread = self.current_price * 0.0001 * self._spread_multiplier
        
        mid_price = self.current_price
        best_bid = mid_price - base_spread / 2
        best_ask = mid_price + base_spread / 2
        
        # Generate bid levels (10 levels)
        bids = []
        cumulative_drop = 0
        for i in range(10):
            # Price drops more at each level
            price_drop = base_spread * (0.5 + random.uniform(0.2, 0.8)) * (1 + i * 0.1)
            cumulative_drop += price_drop
            price = round(best_bid - cumulative_drop, 2)
            
            # Quantity increases at deeper levels (more liquidity away from mid)
            quantity = random.paretovariate(1.5) * 0.5 * (1 + i * 0.2)
            quantity = round(min(quantity, 10.0), 4)
            
            bids.append((price, quantity))
        
        # Generate ask levels (10 levels)
        asks = []
        cumulative_rise = 0
        for i in range(10):
            price_rise = base_spread * (0.5 + random.uniform(0.2, 0.8)) * (1 + i * 0.1)
            cumulative_rise += price_rise
            price = round(best_ask + cumulative_rise, 2)
            
            quantity = random.paretovariate(1.5) * 0.5 * (1 + i * 0.2)
            quantity = round(min(quantity, 10.0), 4)
            
            asks.append((price, quantity))
        
        # Calculate volumes
        bid_volume = sum(q for _, q in bids)
        ask_volume = sum(q for _, q in asks)
        
        return SyntheticDepth(
            bids=bids,
            asks=asks,
            best_bid=round(best_bid, 2),
            best_ask=round(best_ask, 2),
            bid_volume=round(bid_volume, 4),
            ask_volume=round(ask_volume, 4),
            timestamp=datetime.utcnow()
        )
    
    def generate_historical_prices(self, minutes: int = 5, interval_seconds: float = 1.0) -> List[Tuple[datetime, float, float]]:
        """
        Generate historical price data for charts.
        
        Returns list of (timestamp, price, vwap) tuples.
        """
        data = []
        num_points = int(minutes * 60 / interval_seconds)
        
        # Reset to generate consistent history
        temp_price = self.base_price
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Running VWAP calculation
        cumulative_pv = 0.0
        cumulative_volume = 0.0
        
        for i in range(num_points):
            # Generate price movement
            change = random.gauss(0, 1) * self.volatility * temp_price
            trend = self._trend_direction * temp_price
            temp_price = max(temp_price + change + trend, self.base_price * 0.9)
            
            # Generate volume for VWAP
            volume = random.paretovariate(2.0) * 0.1
            cumulative_pv += temp_price * volume
            cumulative_volume += volume
            
            vwap = cumulative_pv / cumulative_volume if cumulative_volume > 0 else temp_price
            
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            data.append((timestamp, round(temp_price, 2), round(vwap, 2)))
        
        return data
    
    def generate_volatility_data(self, minutes: int = 5, interval_seconds: float = 5.0) -> List[Tuple[datetime, float]]:
        """
        Generate historical volatility data for charts.
        
        Returns list of (timestamp, volatility_bps) tuples.
        """
        data = []
        num_points = int(minutes * 60 / interval_seconds)
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        # Base volatility varies over time
        base_vol = 15.0  # Base volatility in bps
        
        for i in range(num_points):
            # Volatility clustering - high vol tends to follow high vol
            vol_change = random.gauss(0, 2)
            vol = base_vol + vol_change + random.uniform(-5, 5)
            vol = max(5.0, min(50.0, vol))  # Clamp between 5-50 bps
            
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            data.append((timestamp, round(vol, 2)))
            
            # Update base for clustering effect
            base_vol = 0.8 * base_vol + 0.2 * vol
        
        return data
    
    def generate_spread_data(self, minutes: int = 2, interval_seconds: float = 5.0) -> List[Tuple[datetime, float]]:
        """
        Generate historical spread data for charts.
        
        Returns list of (timestamp, spread_bps) tuples.
        """
        data = []
        num_points = int(minutes * 60 / interval_seconds)
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        base_spread = 1.0  # Base spread in bps
        
        for i in range(num_points):
            # Spread varies with market activity
            spread = base_spread + random.gauss(0, 0.3)
            spread = max(0.5, min(3.0, spread))
            
            timestamp = start_time + timedelta(seconds=i * interval_seconds)
            data.append((timestamp, round(spread, 3)))
        
        return data
    
    def calculate_features(self) -> dict:
        """Calculate trading features from synthetic data."""
        depth = self.generate_depth()
        recent_trades = self._trade_history[-100:] if self._trade_history else self.generate_trades(100)
        
        # Calculate metrics
        if recent_trades:
            prices = [t.price for t in recent_trades]
            quantities = [t.quantity for t in recent_trades]
            
            # VWAP
            total_pv = sum(p * q for p, q in zip(prices, quantities))
            total_vol = sum(quantities)
            vwap = total_pv / total_vol if total_vol > 0 else self.current_price
            
            # Volatility (standard deviation of returns)
            if len(prices) > 1:
                returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
                volatility = np.std(returns) * 10000  # In bps
            else:
                volatility = 15.0
            
            # Trade velocity
            time_span = (recent_trades[-1].timestamp - recent_trades[0].timestamp).total_seconds()
            velocity = len(recent_trades) / max(time_span, 1)
        else:
            vwap = self.current_price
            volatility = 15.0
            velocity = 10.0
        
        # Order book imbalance
        imbalance = (depth.bid_volume - depth.ask_volume) / (depth.bid_volume + depth.ask_volume) if (depth.bid_volume + depth.ask_volume) > 0 else 0
        
        # Spread
        spread = depth.best_ask - depth.best_bid
        spread_bps = (spread / self.current_price) * 10000
        
        return {
            "mid_price": round(self.current_price, 2),
            "vwap": round(vwap, 2),
            "spread": round(spread, 4),
            "spread_bps": round(spread_bps, 2),
            "bid_volume": depth.bid_volume,
            "ask_volume": depth.ask_volume,
            "imbalance": round(imbalance, 4),
            "volatility": round(volatility, 2),
            "velocity": round(velocity, 2),
            "velocity_baseline": 10.0,
            "best_bid": depth.best_bid,
            "best_ask": depth.best_ask,
        }


# Singleton instance for consistent data across the app
_generator_instance: Optional[SyntheticDataGenerator] = None


def get_synthetic_generator(scenario: str = "normal") -> SyntheticDataGenerator:
    """Get or create the synthetic data generator singleton."""
    global _generator_instance
    if _generator_instance is None:
        _generator_instance = SyntheticDataGenerator(scenario=scenario)
    return _generator_instance


def reset_synthetic_generator(scenario: str = "normal"):
    """Reset the synthetic data generator with a new scenario."""
    global _generator_instance
    _generator_instance = SyntheticDataGenerator(scenario=scenario)
    return _generator_instance
