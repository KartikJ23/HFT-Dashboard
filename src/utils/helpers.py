"""
HFT Live Dashboard - Helper Utilities
=======================================

Common utility functions used across the dashboard.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Union
import logging

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class Helpers:
    """Utility helper functions."""
    
    @staticmethod
    def format_price(price: float, decimals: int = 2) -> str:
        """Format price with commas and decimals."""
        if price == 0:
            return "$0.00"
        return f"${price:,.{decimals}f}"
    
    @staticmethod
    def format_percent(value: float, decimals: int = 2, with_sign: bool = True) -> str:
        """Format percentage value."""
        if with_sign:
            return f"{value:+.{decimals}f}%"
        return f"{value:.{decimals}f}%"
    
    @staticmethod
    def format_bps(value: float, decimals: int = 2) -> str:
        """Format value in basis points."""
        return f"{value:.{decimals}f} bps"
    
    @staticmethod
    def format_velocity(value: float) -> str:
        """Format velocity (trades per second)."""
        return f"{value:.1f}/sec"
    
    @staticmethod
    def format_timestamp(dt: Optional[datetime], 
                         format_str: str = "%H:%M:%S.%f") -> str:
        """Format datetime to string."""
        if dt is None:
            return "--:--:--.---"
        return dt.strftime(format_str)[:-3]  # Remove last 3 digits of microseconds
    
    @staticmethod
    def format_volume(volume: float) -> str:
        """Format volume with appropriate suffix."""
        if volume >= 1_000_000:
            return f"{volume / 1_000_000:.2f}M"
        elif volume >= 1_000:
            return f"{volume / 1_000:.2f}K"
        else:
            return f"{volume:.4f}"
    
    @staticmethod
    def safe_divide(numerator: float, denominator: float, 
                    default: float = 0.0) -> float:
        """Safe division that returns default on zero/invalid."""
        try:
            if denominator == 0 or denominator is None:
                return default
            return numerator / denominator
        except (TypeError, ZeroDivisionError):
            return default
    
    @staticmethod
    def clamp(value: float, min_val: float, max_val: float) -> float:
        """Clamp value between min and max."""
        return max(min_val, min(max_val, value))
    
    @staticmethod
    def time_ago(dt: datetime) -> str:
        """Get human-readable time ago string."""
        if dt is None:
            return "Never"
        
        now = datetime.utcnow()
        delta = now - dt
        
        seconds = delta.total_seconds()
        
        if seconds < 1:
            return "Just now"
        elif seconds < 60:
            return f"{int(seconds)}s ago"
        elif seconds < 3600:
            return f"{int(seconds // 60)}m ago"
        elif seconds < 86400:
            return f"{int(seconds // 3600)}h ago"
        else:
            return f"{int(seconds // 86400)}d ago"
    
    @staticmethod
    def is_stale(dt: Optional[datetime], max_age_seconds: float = 5.0) -> bool:
        """Check if a timestamp is stale."""
        if dt is None:
            return True
        
        age = (datetime.utcnow() - dt).total_seconds()
        return age > max_age_seconds
    
    @staticmethod
    def interpolate_color(color1: str, color2: str, factor: float) -> str:
        """
        Interpolate between two hex colors.
        
        Args:
            color1: Starting hex color (e.g., "#ff0000")
            color2: Ending hex color
            factor: Interpolation factor (0.0 = color1, 1.0 = color2)
            
        Returns:
            Interpolated hex color
        """
        factor = max(0, min(1, factor))
        
        # Parse hex colors
        r1, g1, b1 = int(color1[1:3], 16), int(color1[3:5], 16), int(color1[5:7], 16)
        r2, g2, b2 = int(color2[1:3], 16), int(color2[3:5], 16), int(color2[5:7], 16)
        
        # Interpolate
        r = int(r1 + (r2 - r1) * factor)
        g = int(g1 + (g2 - g1) * factor)
        b = int(b1 + (b2 - b1) * factor)
        
        return f"#{r:02x}{g:02x}{b:02x}"
    
    @staticmethod
    def get_trend_direction(values: List[float], min_samples: int = 3) -> str:
        """
        Determine trend direction from a list of values.
        
        Returns: 'up', 'down', or 'flat'
        """
        if len(values) < min_samples:
            return 'flat'
        
        recent = values[-min_samples:]
        
        # Simple linear regression direction
        n = len(recent)
        sum_x = sum(range(n))
        sum_y = sum(recent)
        sum_xy = sum(i * recent[i] for i in range(n))
        sum_xx = sum(i * i for i in range(n))
        
        denominator = n * sum_xx - sum_x * sum_x
        if denominator == 0:
            return 'flat'
        
        slope = (n * sum_xy - sum_x * sum_y) / denominator
        
        # Threshold for flatness
        threshold = 0.0001 * (sum_y / n) if sum_y != 0 else 0.0001
        
        if slope > threshold:
            return 'up'
        elif slope < -threshold:
            return 'down'
        else:
            return 'flat'
    
    @staticmethod
    def moving_average(values: List[float], window: int = 5) -> List[float]:
        """Calculate simple moving average."""
        if len(values) < window:
            return values
        
        result = []
        for i in range(len(values)):
            start = max(0, i - window + 1)
            result.append(sum(values[start:i+1]) / (i - start + 1))
        
        return result
    
    @staticmethod
    def exponential_moving_average(values: List[float], 
                                    alpha: float = 0.3) -> List[float]:
        """Calculate exponential moving average."""
        if not values:
            return []
        
        result = [values[0]]
        for i in range(1, len(values)):
            ema = alpha * values[i] + (1 - alpha) * result[-1]
            result.append(ema)
        
        return result


# =============================================================================
# LOGGING UTILITIES
# =============================================================================

def setup_logging(level: str = "INFO") -> logging.Logger:
    """
    Set up logging configuration.
    
    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR)
        
    Returns:
        Logger instance
    """
    logging.basicConfig(
        level=getattr(logging, level.upper()),
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    return logging.getLogger("hft-dashboard")


# =============================================================================
# DATA VALIDATION
# =============================================================================

def validate_trade_data(data: Dict) -> bool:
    """Validate trade data from WebSocket."""
    required_fields = ["t", "p", "q", "T", "m"]
    return all(field in data for field in required_fields)


def validate_depth_data(data: Dict) -> bool:
    """Validate depth data from WebSocket."""
    required_fields = ["bids", "asks"]
    return all(field in data for field in required_fields)


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    print("Testing Helpers...")
    print("=" * 50)
    
    h = Helpers()
    
    # Test formatting
    print(f"Price: {h.format_price(42150.50)}")
    print(f"Percent: {h.format_percent(0.125)}")
    print(f"BPS: {h.format_bps(2.35)}")
    print(f"Velocity: {h.format_velocity(15.7)}")
    print(f"Volume: {h.format_volume(1234567.89)}")
    
    # Test timestamp
    now = datetime.utcnow()
    print(f"Timestamp: {h.format_timestamp(now)}")
    print(f"Time ago: {h.time_ago(now - timedelta(minutes=5))}")
    
    # Test safe divide
    print(f"Safe divide: {h.safe_divide(10, 0)}")
    
    # Test trend
    values = [1, 2, 3, 4, 5]
    print(f"Trend (up): {h.get_trend_direction(values)}")
    
    values = [5, 4, 3, 2, 1]
    print(f"Trend (down): {h.get_trend_direction(values)}")
    
    # Test color interpolation
    print(f"Color interp: {h.interpolate_color('#ff0000', '#00ff00', 0.5)}")
    
    print("\nTest complete!")
