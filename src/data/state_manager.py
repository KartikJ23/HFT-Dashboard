"""
HFT Live Dashboard - State Manager
===================================

Thread-safe state management using circular buffers.
Stores all streaming data and derived metrics.
"""

import threading
from collections import deque
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    TRADES_BUFFER_SIZE,
    DEPTH_BUFFER_SIZE,
    PRICE_HISTORY_SIZE,
    SPREAD_HISTORY_SIZE,
    VOLATILITY_HISTORY_SIZE,
    VELOCITY_HISTORY_SIZE
)


@dataclass
class Trade:
    """Represents a single trade."""
    timestamp: datetime
    price: float
    quantity: float
    is_buyer_maker: bool  # True = SELL, False = BUY
    trade_id: int


@dataclass
class DepthSnapshot:
    """Represents an order book snapshot."""
    timestamp: datetime
    bids: List[Tuple[float, float]]  # [(price, qty), ...]
    asks: List[Tuple[float, float]]  # [(price, qty), ...]
    best_bid: float
    best_ask: float
    bid_volume: float
    ask_volume: float


@dataclass
class PricePoint:
    """Represents a price point for charting."""
    timestamp: datetime
    price: float
    vwap: float


@dataclass
class SpreadPoint:
    """Represents a spread measurement."""
    timestamp: datetime
    spread_bps: float


@dataclass
class VolatilityPoint:
    """Represents a volatility measurement."""
    timestamp: datetime
    volatility_bps: float


@dataclass
class VelocityPoint:
    """Represents a velocity measurement."""
    timestamp: datetime
    velocity: float


class StateManager:
    """
    Thread-safe state management for HFT dashboard.
    
    Uses collections.deque with maxlen for automatic circular buffer behavior.
    All public methods are thread-safe using a reentrant lock.
    """
    
    def __init__(self):
        """Initialize all buffers and locks."""
        # Thread lock for safe concurrent access
        self._lock = threading.RLock()
        
        # Raw data buffers
        self._trades: deque = deque(maxlen=TRADES_BUFFER_SIZE)
        self._depth: deque = deque(maxlen=DEPTH_BUFFER_SIZE)
        
        # Derived data buffers for charting
        self._price_history: deque = deque(maxlen=PRICE_HISTORY_SIZE)
        self._spread_history: deque = deque(maxlen=SPREAD_HISTORY_SIZE)
        self._volatility_history: deque = deque(maxlen=VOLATILITY_HISTORY_SIZE)
        self._velocity_history: deque = deque(maxlen=VELOCITY_HISTORY_SIZE)
        
        # Current state
        self._current_price: float = 0.0
        self._current_spread: float = 0.0
        self._current_spread_bps: float = 0.0
        self._current_mid_price: float = 0.0
        
        # Connection status
        self._is_connected: bool = False
        self._connection_status: str = "disconnected"  # connected, reconnecting, disconnected
        self._last_update: Optional[datetime] = None
        self._last_trade_time: Optional[datetime] = None
        self._last_depth_time: Optional[datetime] = None
        
        # Velocity baseline (running average)
        self._velocity_baseline: float = 20.0
        self._velocity_samples: deque = deque(maxlen=60)  # 1 minute of samples
        
        # Error tracking
        self._last_error: Optional[str] = None
        self._error_count: int = 0
    
    # =========================================================================
    # TRADE DATA METHODS
    # =========================================================================
    
    def add_trade(self, trade: Trade) -> None:
        """Add a new trade to the buffer."""
        with self._lock:
            self._trades.append(trade)
            self._current_price = trade.price
            self._last_trade_time = trade.timestamp
            self._last_update = datetime.utcnow()
    
    def add_trade_raw(self, timestamp: datetime, price: float, quantity: float,
                      is_buyer_maker: bool, trade_id: int) -> None:
        """Add a new trade from raw values."""
        trade = Trade(
            timestamp=timestamp,
            price=price,
            quantity=quantity,
            is_buyer_maker=is_buyer_maker,
            trade_id=trade_id
        )
        self.add_trade(trade)
    
    def get_trades(self, limit: Optional[int] = None) -> List[Trade]:
        """Get recent trades, optionally limited."""
        with self._lock:
            if limit is None:
                return list(self._trades)
            return list(self._trades)[-limit:]
    
    def get_trades_since(self, since: datetime) -> List[Trade]:
        """Get trades since a specific timestamp."""
        with self._lock:
            return [t for t in self._trades if t.timestamp >= since]
    
    # =========================================================================
    # DEPTH DATA METHODS
    # =========================================================================
    
    def add_depth(self, depth: DepthSnapshot) -> None:
        """Add a new depth snapshot to the buffer."""
        with self._lock:
            self._depth.append(depth)
            self._current_mid_price = (depth.best_bid + depth.best_ask) / 2
            self._current_spread = depth.best_ask - depth.best_bid
            if self._current_mid_price > 0:
                self._current_spread_bps = (self._current_spread / self._current_mid_price) * 10000
            self._last_depth_time = depth.timestamp
            self._last_update = datetime.utcnow()
    
    def add_depth_raw(self, timestamp: datetime, bids: List[List[str]], 
                      asks: List[List[str]]) -> None:
        """Add a new depth snapshot from raw Binance data."""
        # Parse bids and asks
        parsed_bids = [(float(b[0]), float(b[1])) for b in bids]
        parsed_asks = [(float(a[0]), float(a[1])) for a in asks]
        
        # Calculate aggregates
        best_bid = parsed_bids[0][0] if parsed_bids else 0.0
        best_ask = parsed_asks[0][0] if parsed_asks else 0.0
        bid_volume = sum(qty for _, qty in parsed_bids)
        ask_volume = sum(qty for _, qty in parsed_asks)
        
        depth = DepthSnapshot(
            timestamp=timestamp,
            bids=parsed_bids,
            asks=parsed_asks,
            best_bid=best_bid,
            best_ask=best_ask,
            bid_volume=bid_volume,
            ask_volume=ask_volume
        )
        self.add_depth(depth)
    
    def get_latest_depth(self) -> Optional[DepthSnapshot]:
        """Get the most recent depth snapshot."""
        with self._lock:
            return self._depth[-1] if self._depth else None
    
    def get_depth_history(self, limit: Optional[int] = None) -> List[DepthSnapshot]:
        """Get depth history, optionally limited."""
        with self._lock:
            if limit is None:
                return list(self._depth)
            return list(self._depth)[-limit:]
    
    # =========================================================================
    # PRICE HISTORY METHODS
    # =========================================================================
    
    def add_price_point(self, timestamp: datetime, price: float, vwap: float) -> None:
        """Add a price point for charting."""
        with self._lock:
            point = PricePoint(timestamp=timestamp, price=price, vwap=vwap)
            self._price_history.append(point)
    
    def get_price_history(self) -> List[PricePoint]:
        """Get price history for charting."""
        with self._lock:
            return list(self._price_history)
    
    # =========================================================================
    # SPREAD HISTORY METHODS
    # =========================================================================
    
    def add_spread_point(self, timestamp: datetime, spread_bps: float) -> None:
        """Add a spread point for heatmap."""
        with self._lock:
            point = SpreadPoint(timestamp=timestamp, spread_bps=spread_bps)
            self._spread_history.append(point)
    
    def get_spread_history(self) -> List[SpreadPoint]:
        """Get spread history for heatmap."""
        with self._lock:
            return list(self._spread_history)
    
    # =========================================================================
    # VOLATILITY HISTORY METHODS
    # =========================================================================
    
    def add_volatility_point(self, timestamp: datetime, volatility_bps: float) -> None:
        """Add a volatility point for charting."""
        with self._lock:
            point = VolatilityPoint(timestamp=timestamp, volatility_bps=volatility_bps)
            self._volatility_history.append(point)
    
    def get_volatility_history(self) -> List[VolatilityPoint]:
        """Get volatility history for charting."""
        with self._lock:
            return list(self._volatility_history)
    
    # =========================================================================
    # VELOCITY HISTORY METHODS
    # =========================================================================
    
    def add_velocity_point(self, timestamp: datetime, velocity: float) -> None:
        """Add a velocity point and update baseline."""
        with self._lock:
            point = VelocityPoint(timestamp=timestamp, velocity=velocity)
            self._velocity_history.append(point)
            
            # Update baseline with exponential moving average
            self._velocity_samples.append(velocity)
            if len(self._velocity_samples) >= 10:
                self._velocity_baseline = sum(self._velocity_samples) / len(self._velocity_samples)
    
    def get_velocity_history(self) -> List[VelocityPoint]:
        """Get velocity history."""
        with self._lock:
            return list(self._velocity_history)
    
    def get_velocity_baseline(self) -> float:
        """Get the current velocity baseline."""
        with self._lock:
            return self._velocity_baseline
    
    # =========================================================================
    # CURRENT STATE GETTERS
    # =========================================================================
    
    def get_current_price(self) -> float:
        """Get the current price."""
        with self._lock:
            return self._current_price
    
    def get_current_spread(self) -> float:
        """Get the current spread in absolute terms."""
        with self._lock:
            return self._current_spread
    
    def get_current_spread_bps(self) -> float:
        """Get the current spread in basis points."""
        with self._lock:
            return self._current_spread_bps
    
    def get_current_mid_price(self) -> float:
        """Get the current mid price."""
        with self._lock:
            return self._current_mid_price
    
    # =========================================================================
    # CONNECTION STATUS METHODS
    # =========================================================================
    
    def set_connected(self, is_connected: bool) -> None:
        """Set connection status."""
        with self._lock:
            self._is_connected = is_connected
            if is_connected:
                self._connection_status = "connected"
            else:
                self._connection_status = "disconnected"
    
    def set_reconnecting(self) -> None:
        """Set status to reconnecting."""
        with self._lock:
            self._is_connected = False
            self._connection_status = "reconnecting"
    
    def is_connected(self) -> bool:
        """Check if connected."""
        with self._lock:
            return self._is_connected
    
    def get_connection_status(self) -> str:
        """Get connection status string."""
        with self._lock:
            return self._connection_status
    
    def get_last_update(self) -> Optional[datetime]:
        """Get timestamp of last data update."""
        with self._lock:
            return self._last_update
    
    # =========================================================================
    # ERROR HANDLING METHODS
    # =========================================================================
    
    def set_error(self, error: str) -> None:
        """Record an error."""
        with self._lock:
            self._last_error = error
            self._error_count += 1
    
    def get_last_error(self) -> Optional[str]:
        """Get last error message."""
        with self._lock:
            return self._last_error
    
    def get_error_count(self) -> int:
        """Get total error count."""
        with self._lock:
            return self._error_count
    
    def clear_error(self) -> None:
        """Clear last error."""
        with self._lock:
            self._last_error = None
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def get_buffer_sizes(self) -> Dict[str, int]:
        """Get current sizes of all buffers."""
        with self._lock:
            return {
                "trades": len(self._trades),
                "depth": len(self._depth),
                "price_history": len(self._price_history),
                "spread_history": len(self._spread_history),
                "volatility_history": len(self._volatility_history),
                "velocity_history": len(self._velocity_history)
            }
    
    def clear_all(self) -> None:
        """Clear all buffers. Use with caution."""
        with self._lock:
            self._trades.clear()
            self._depth.clear()
            self._price_history.clear()
            self._spread_history.clear()
            self._volatility_history.clear()
            self._velocity_history.clear()
            self._current_price = 0.0
            self._current_spread = 0.0
            self._current_spread_bps = 0.0
            self._current_mid_price = 0.0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of current state."""
        with self._lock:
            return {
                "current_price": self._current_price,
                "current_spread_bps": self._current_spread_bps,
                "current_mid_price": self._current_mid_price,
                "is_connected": self._is_connected,
                "connection_status": self._connection_status,
                "last_update": self._last_update.isoformat() if self._last_update else None,
                "buffer_sizes": self.get_buffer_sizes(),
                "velocity_baseline": self._velocity_baseline,
                "error_count": self._error_count
            }
