"""
HFT Dashboard - ML Predictor Engine
=====================================

Real-time machine learning predictions for price direction,
momentum, and market regime classification.

Features:
- 5-second price direction prediction
- Momentum score calculation
- Market regime detection (Trending/Ranging/Volatile)
- Confidence scoring with accuracy tracking
- Feature importance analysis

Note: Uses lightweight statistical models for real-time inference.
For production, integrate with proper ML frameworks (scikit-learn, XGBoost).
"""

import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from collections import deque
from enum import Enum
import math


class PredictionDirection(Enum):
    """Price direction prediction."""
    STRONG_UP = "strong_up"
    UP = "up"
    NEUTRAL = "neutral"
    DOWN = "down"
    STRONG_DOWN = "strong_down"


class MarketRegime(Enum):
    """Market regime classification."""
    TRENDING_UP = "trending_up"
    TRENDING_DOWN = "trending_down"
    RANGING = "ranging"
    VOLATILE = "volatile"
    BREAKOUT = "breakout"


@dataclass
class PredictionResult:
    """Container for ML prediction results."""
    
    # Direction prediction
    direction: PredictionDirection = PredictionDirection.NEUTRAL
    direction_confidence: float = 0.5
    predicted_move_bps: float = 0.0
    
    # Momentum
    momentum_score: float = 0.0  # -100 to +100
    momentum_strength: str = "Neutral"
    
    # Market regime
    regime: MarketRegime = MarketRegime.RANGING
    regime_confidence: float = 0.5
    
    # Trend analysis
    trend_strength: float = 0.0  # 0 to 100
    trend_direction: str = "Neutral"
    
    # Reversal probability
    reversal_probability: float = 0.0
    
    # Model performance
    model_accuracy: float = 0.0  # Rolling accuracy
    predictions_made: int = 0
    correct_predictions: int = 0
    
    # Timing
    prediction_timestamp: datetime = None
    prediction_horizon_seconds: int = 5
    
    # Feature importance (for explainability)
    feature_importance: Dict[str, float] = field(default_factory=dict)
    
    # Signal strength for trading
    signal_strength: float = 0.0  # 0 to 100
    signal_action: str = "HOLD"


class MLPredictor:
    """
    Real-time ML prediction engine for HFT signals.
    
    Uses ensemble of statistical indicators:
    - Price momentum (ROC, RSI-like)
    - Order book imbalance
    - Volatility regime
    - Trade flow analysis
    - Mean reversion signals
    """
    
    def __init__(self, history_size: int = 500):
        """
        Initialize the predictor.
        
        Args:
            history_size: Number of data points to retain for calculations
        """
        # Price history for technical calculations
        self.price_history: deque = deque(maxlen=history_size)
        self.returns_history: deque = deque(maxlen=history_size)
        self.volume_history: deque = deque(maxlen=history_size)
        self.imbalance_history: deque = deque(maxlen=history_size)
        self.volatility_history: deque = deque(maxlen=history_size)
        self.spread_history: deque = deque(maxlen=history_size)
        
        # Prediction tracking
        self.prediction_history: deque = deque(maxlen=100)
        self.actual_outcomes: deque = deque(maxlen=100)
        
        # Model weights (would be trained in production)
        self.weights = {
            "momentum": 0.25,
            "imbalance": 0.20,
            "volatility": 0.15,
            "mean_reversion": 0.15,
            "volume": 0.10,
            "spread": 0.10,
            "trend": 0.05
        }
        
        # State tracking
        self.last_prediction: Optional[PredictionResult] = None
        self.predictions_made = 0
        self.correct_predictions = 0
        
    def update(self, price: float, volume: float = 0.0, 
               imbalance: float = 0.0, volatility: float = 0.0,
               spread: float = 0.0):
        """
        Update the predictor with new market data.
        
        Args:
            price: Current price
            volume: Trade volume
            imbalance: Order book imbalance (-1 to +1)
            volatility: Current volatility (bps)
            spread: Current spread (bps)
        """
        timestamp = datetime.utcnow()
        
        # Calculate return if we have history
        if len(self.price_history) > 0:
            last_price = self.price_history[-1][1]
            if last_price > 0:
                ret = (price - last_price) / last_price * 10000  # in bps
                self.returns_history.append((timestamp, ret))
        
        # Store data points
        self.price_history.append((timestamp, price))
        self.volume_history.append((timestamp, volume))
        self.imbalance_history.append((timestamp, imbalance))
        self.volatility_history.append((timestamp, volatility))
        self.spread_history.append((timestamp, spread))
        
        # Validate previous prediction if enough time has passed
        self._validate_predictions()
    
    def predict(self) -> PredictionResult:
        """
        Generate ML prediction based on current market state.
        
        Returns:
            PredictionResult with all predictions and confidence scores
        """
        result = PredictionResult(prediction_timestamp=datetime.utcnow())
        
        if len(self.price_history) < 10:
            # Not enough data
            result.direction = PredictionDirection.NEUTRAL
            result.direction_confidence = 0.0
            result.regime = MarketRegime.RANGING
            result.signal_action = "WAIT"
            return result
        
        # Calculate all signals
        momentum_signal = self._calculate_momentum()
        imbalance_signal = self._calculate_imbalance_signal()
        volatility_signal = self._calculate_volatility_signal()
        mean_reversion_signal = self._calculate_mean_reversion()
        volume_signal = self._calculate_volume_signal()
        spread_signal = self._calculate_spread_signal()
        trend_signal = self._calculate_trend()
        
        # Weighted ensemble prediction
        weighted_signal = (
            momentum_signal * self.weights["momentum"] +
            imbalance_signal * self.weights["imbalance"] +
            volatility_signal * self.weights["volatility"] +
            mean_reversion_signal * self.weights["mean_reversion"] +
            volume_signal * self.weights["volume"] +
            spread_signal * self.weights["spread"] +
            trend_signal * self.weights["trend"]
        )
        
        # Direction prediction
        result.direction, result.direction_confidence = self._signal_to_direction(weighted_signal)
        result.predicted_move_bps = weighted_signal * 2  # Scale to expected bps move
        
        # Momentum score (-100 to +100)
        result.momentum_score = np.clip(momentum_signal * 100, -100, 100)
        result.momentum_strength = self._momentum_to_strength(result.momentum_score)
        
        # Market regime detection
        result.regime, result.regime_confidence = self._detect_regime()
        
        # Trend analysis
        result.trend_strength = abs(trend_signal) * 100
        result.trend_direction = "Bullish" if trend_signal > 0.1 else "Bearish" if trend_signal < -0.1 else "Neutral"
        
        # Reversal probability
        result.reversal_probability = self._calculate_reversal_probability()
        
        # Signal strength and action
        result.signal_strength = min(abs(weighted_signal) * 100, 100)
        result.signal_action = self._determine_action(weighted_signal, result.regime)
        
        # Feature importance
        result.feature_importance = {
            "Momentum": abs(momentum_signal) * self.weights["momentum"],
            "Order Imbalance": abs(imbalance_signal) * self.weights["imbalance"],
            "Volatility": abs(volatility_signal) * self.weights["volatility"],
            "Mean Reversion": abs(mean_reversion_signal) * self.weights["mean_reversion"],
            "Volume Flow": abs(volume_signal) * self.weights["volume"],
            "Spread": abs(spread_signal) * self.weights["spread"],
            "Trend": abs(trend_signal) * self.weights["trend"]
        }
        
        # Normalize feature importance to sum to 100%
        total_importance = sum(result.feature_importance.values())
        if total_importance > 0:
            result.feature_importance = {
                k: v / total_importance * 100 
                for k, v in result.feature_importance.items()
            }
        
        # Model accuracy tracking
        result.predictions_made = self.predictions_made
        result.correct_predictions = self.correct_predictions
        result.model_accuracy = (
            self.correct_predictions / self.predictions_made * 100
            if self.predictions_made > 0 else 50.0
        )
        
        # Store prediction for validation
        self.prediction_history.append({
            "timestamp": result.prediction_timestamp,
            "direction": result.direction,
            "price": self.price_history[-1][1] if self.price_history else 0
        })
        
        self.last_prediction = result
        return result
    
    def _calculate_momentum(self) -> float:
        """Calculate momentum signal using ROC and trend."""
        if len(self.returns_history) < 5:
            return 0.0
        
        recent_returns = [r[1] for r in list(self.returns_history)[-20:]]
        
        # Short-term momentum (last 5 returns)
        short_momentum = np.mean(recent_returns[-5:]) if len(recent_returns) >= 5 else 0
        
        # Medium-term momentum (last 20 returns)
        medium_momentum = np.mean(recent_returns) if len(recent_returns) >= 10 else 0
        
        # RSI-like calculation
        gains = [r for r in recent_returns if r > 0]
        losses = [-r for r in recent_returns if r < 0]
        
        avg_gain = np.mean(gains) if gains else 0
        avg_loss = np.mean(losses) if losses else 0.001
        
        rs = avg_gain / avg_loss if avg_loss > 0 else 1
        rsi = 100 - (100 / (1 + rs))
        
        # Normalize RSI to -1 to +1
        rsi_signal = (rsi - 50) / 50
        
        # Combined momentum
        momentum = (short_momentum / 10 + medium_momentum / 20 + rsi_signal) / 3
        
        return np.clip(momentum, -1, 1)
    
    def _calculate_imbalance_signal(self) -> float:
        """Calculate signal from order book imbalance."""
        if len(self.imbalance_history) < 3:
            return 0.0
        
        recent_imbalance = [i[1] for i in list(self.imbalance_history)[-10:]]
        
        # Current imbalance
        current = recent_imbalance[-1]
        
        # Trend in imbalance
        if len(recent_imbalance) >= 5:
            imbalance_trend = recent_imbalance[-1] - recent_imbalance[-5]
        else:
            imbalance_trend = 0
        
        # Persistence (is imbalance consistent?)
        persistence = np.mean(recent_imbalance)
        
        signal = (current * 0.5 + imbalance_trend * 0.3 + persistence * 0.2)
        
        return np.clip(signal, -1, 1)
    
    def _calculate_volatility_signal(self) -> float:
        """Calculate signal from volatility regime."""
        if len(self.volatility_history) < 5:
            return 0.0
        
        recent_vol = [v[1] for v in list(self.volatility_history)[-20:]]
        
        current_vol = recent_vol[-1]
        avg_vol = np.mean(recent_vol)
        
        # High volatility = mean reversion more likely
        if current_vol > avg_vol * 1.5:
            return -0.3  # Expect pullback
        elif current_vol < avg_vol * 0.5:
            return 0.1  # Low vol, trend continuation
        
        return 0.0
    
    def _calculate_mean_reversion(self) -> float:
        """Calculate mean reversion signal."""
        if len(self.price_history) < 20:
            return 0.0
        
        prices = [p[1] for p in list(self.price_history)[-50:]]
        
        current_price = prices[-1]
        mean_price = np.mean(prices)
        std_price = np.std(prices) if len(prices) > 1 else 1
        
        # Z-score
        z_score = (current_price - mean_price) / std_price if std_price > 0 else 0
        
        # Mean reversion signal (opposite of z-score)
        signal = -z_score / 3  # Damped signal
        
        return np.clip(signal, -1, 1)
    
    def _calculate_volume_signal(self) -> float:
        """Calculate signal from volume analysis."""
        if len(self.volume_history) < 5 or len(self.returns_history) < 5:
            return 0.0
        
        recent_volumes = [v[1] for v in list(self.volume_history)[-10:]]
        recent_returns = [r[1] for r in list(self.returns_history)[-10:]]
        
        avg_volume = np.mean(recent_volumes) if recent_volumes else 1
        current_volume = recent_volumes[-1] if recent_volumes else 0
        
        # Volume-price confirmation
        current_return = recent_returns[-1] if recent_returns else 0
        
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        # High volume confirms direction
        if volume_ratio > 1.5:
            return np.sign(current_return) * 0.5
        
        return 0.0
    
    def _calculate_spread_signal(self) -> float:
        """Calculate signal from spread analysis."""
        if len(self.spread_history) < 3:
            return 0.0
        
        recent_spreads = [s[1] for s in list(self.spread_history)[-10:]]
        
        current_spread = recent_spreads[-1]
        avg_spread = np.mean(recent_spreads)
        
        # Widening spread = potential volatility/reversal
        if current_spread > avg_spread * 1.5:
            return -0.2  # Caution signal
        elif current_spread < avg_spread * 0.7:
            # Tight spread = good liquidity, trend may continue
            if len(self.returns_history) > 0:
                return np.sign(list(self.returns_history)[-1][1]) * 0.1
        
        return 0.0
    
    def _calculate_trend(self) -> float:
        """Calculate trend strength and direction."""
        if len(self.price_history) < 20:
            return 0.0
        
        prices = [p[1] for p in list(self.price_history)[-30:]]
        
        # Simple linear regression slope
        x = np.arange(len(prices))
        slope = np.polyfit(x, prices, 1)[0]
        
        # Normalize by average price
        avg_price = np.mean(prices)
        normalized_slope = slope / avg_price * 1000  # Per 1000 data points
        
        return np.clip(normalized_slope, -1, 1)
    
    def _signal_to_direction(self, signal: float) -> Tuple[PredictionDirection, float]:
        """Convert raw signal to direction enum and confidence."""
        confidence = min(abs(signal), 1.0)
        
        if signal > 0.5:
            return PredictionDirection.STRONG_UP, confidence
        elif signal > 0.15:
            return PredictionDirection.UP, confidence
        elif signal < -0.5:
            return PredictionDirection.STRONG_DOWN, confidence
        elif signal < -0.15:
            return PredictionDirection.DOWN, confidence
        else:
            return PredictionDirection.NEUTRAL, 1 - abs(signal)
    
    def _momentum_to_strength(self, score: float) -> str:
        """Convert momentum score to descriptive strength."""
        if score > 60:
            return "Very Strong Bullish"
        elif score > 30:
            return "Strong Bullish"
        elif score > 10:
            return "Bullish"
        elif score < -60:
            return "Very Strong Bearish"
        elif score < -30:
            return "Strong Bearish"
        elif score < -10:
            return "Bearish"
        else:
            return "Neutral"
    
    def _detect_regime(self) -> Tuple[MarketRegime, float]:
        """Detect current market regime."""
        if len(self.returns_history) < 20 or len(self.volatility_history) < 5:
            return MarketRegime.RANGING, 0.5
        
        returns = [r[1] for r in list(self.returns_history)[-30:]]
        volatilities = [v[1] for v in list(self.volatility_history)[-10:]]
        
        # Trend strength
        trend = self._calculate_trend()
        
        # Volatility level
        avg_vol = np.mean(volatilities) if volatilities else 15
        
        # Return distribution
        positive_returns = sum(1 for r in returns if r > 0)
        return_ratio = positive_returns / len(returns)
        
        # Classify regime
        if avg_vol > 25:
            return MarketRegime.VOLATILE, min(avg_vol / 25, 1.0)
        elif abs(trend) > 0.5:
            if trend > 0:
                return MarketRegime.TRENDING_UP, abs(trend)
            else:
                return MarketRegime.TRENDING_DOWN, abs(trend)
        elif avg_vol < 10 and abs(trend) < 0.2:
            return MarketRegime.RANGING, 0.7
        else:
            # Check for breakout conditions
            recent_vol = volatilities[-1] if volatilities else 15
            if recent_vol > avg_vol * 1.5 and abs(trend) > 0.3:
                return MarketRegime.BREAKOUT, 0.6
            return MarketRegime.RANGING, 0.5
    
    def _calculate_reversal_probability(self) -> float:
        """Calculate probability of trend reversal."""
        if len(self.returns_history) < 10:
            return 0.5
        
        returns = [r[1] for r in list(self.returns_history)[-20:]]
        
        # Consecutive same-direction returns
        same_direction = 1
        current_sign = np.sign(returns[-1])
        
        for r in reversed(returns[:-1]):
            if np.sign(r) == current_sign:
                same_direction += 1
            else:
                break
        
        # More consecutive = higher reversal probability
        reversal_prob = min(same_direction * 0.1, 0.8)
        
        # Extreme RSI also indicates reversal
        momentum = self._calculate_momentum()
        if abs(momentum) > 0.7:
            reversal_prob = min(reversal_prob + 0.2, 0.9)
        
        return reversal_prob
    
    def _determine_action(self, signal: float, regime: MarketRegime) -> str:
        """Determine trading action based on signal and regime."""
        if regime == MarketRegime.VOLATILE:
            if abs(signal) > 0.5:
                return "CAUTION" if signal > 0 else "CAUTION"
            return "WAIT"
        
        if signal > 0.5:
            return "STRONG BUY"
        elif signal > 0.2:
            return "BUY"
        elif signal < -0.5:
            return "STRONG SELL"
        elif signal < -0.2:
            return "SELL"
        else:
            return "HOLD"
    
    def _validate_predictions(self):
        """Validate past predictions against actual outcomes."""
        if len(self.prediction_history) < 2 or len(self.price_history) < 2:
            return
        
        now = datetime.utcnow()
        
        # Check predictions from ~5 seconds ago
        for i, pred in enumerate(list(self.prediction_history)):
            if (now - pred["timestamp"]).total_seconds() >= 5:
                # Find price at prediction time and now
                pred_price = pred["price"]
                current_price = self.price_history[-1][1]
                
                if pred_price > 0:
                    actual_move = (current_price - pred_price) / pred_price * 10000
                    
                    # Check if direction was correct
                    predicted_up = pred["direction"] in [
                        PredictionDirection.UP, 
                        PredictionDirection.STRONG_UP
                    ]
                    actual_up = actual_move > 0.5  # At least 0.5 bps move
                    
                    predicted_down = pred["direction"] in [
                        PredictionDirection.DOWN,
                        PredictionDirection.STRONG_DOWN
                    ]
                    actual_down = actual_move < -0.5
                    
                    if (predicted_up and actual_up) or (predicted_down and actual_down):
                        self.correct_predictions += 1
                    
                    self.predictions_made += 1
                
                # Remove validated prediction
                if pred in self.prediction_history:
                    self.prediction_history.remove(pred)
                break
    
    def get_accuracy_stats(self) -> Dict[str, float]:
        """Get prediction accuracy statistics."""
        accuracy = (
            self.correct_predictions / self.predictions_made * 100
            if self.predictions_made > 0 else 50.0
        )
        
        return {
            "accuracy": accuracy,
            "total_predictions": self.predictions_made,
            "correct_predictions": self.correct_predictions,
            "win_rate": accuracy
        }
    
    def reset_stats(self):
        """Reset accuracy tracking statistics."""
        self.predictions_made = 0
        self.correct_predictions = 0
        self.prediction_history.clear()
