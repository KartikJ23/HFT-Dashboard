"""
HFT Dashboard - Alert Manager
==============================

Comprehensive alert system with custom thresholds, priority levels,
visual notifications, and history tracking.

Features:
- Custom alert rules with user-defined thresholds
- Priority classification (Critical, High, Medium, Low)
- Alert history with timestamps
- Sound/visual notification triggers
- Cooldown to prevent alert spam
- Alert statistics and analytics
"""

import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Callable, Any
from collections import deque
from enum import Enum
import uuid


class AlertPriority(Enum):
    """Alert priority levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(Enum):
    """Types of alerts."""
    PRICE_THRESHOLD = "price_threshold"
    SPREAD_THRESHOLD = "spread_threshold"
    VOLATILITY_THRESHOLD = "volatility_threshold"
    IMBALANCE_THRESHOLD = "imbalance_threshold"
    VELOCITY_THRESHOLD = "velocity_threshold"
    PRICE_CHANGE = "price_change"
    ML_SIGNAL = "ml_signal"
    REGIME_CHANGE = "regime_change"
    CUSTOM = "custom"


@dataclass
class AlertRule:
    """Definition of an alert rule."""
    id: str
    name: str
    alert_type: AlertType
    condition: str  # e.g., "price > 90000" or "spread_bps > 5"
    threshold: float
    comparison: str  # ">", "<", ">=", "<=", "==", "!="
    priority: AlertPriority
    message_template: str
    enabled: bool = True
    cooldown_seconds: int = 30  # Minimum time between same alerts
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.utcnow()


@dataclass
class Alert:
    """A triggered alert instance."""
    id: str
    rule_id: str
    rule_name: str
    priority: AlertPriority
    alert_type: AlertType
    message: str
    value: float  # The value that triggered the alert
    threshold: float
    timestamp: datetime
    acknowledged: bool = False
    acknowledged_at: Optional[datetime] = None
    
    # Visual properties
    icon: str = "⚠️"
    color: str = "#f59e0b"
    
    def __post_init__(self):
        # Set icon and color based on priority
        priority_styles = {
            AlertPriority.CRITICAL: ("🚨", "#ef4444"),
            AlertPriority.HIGH: ("🔴", "#f97316"),
            AlertPriority.MEDIUM: ("🟡", "#eab308"),
            AlertPriority.LOW: ("🟢", "#22c55e"),
            AlertPriority.INFO: ("ℹ️", "#3b82f6")
        }
        self.icon, self.color = priority_styles.get(
            self.priority, ("⚠️", "#f59e0b")
        )


@dataclass
class AlertStats:
    """Alert statistics."""
    total_alerts: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0
    info_count: int = 0
    alerts_per_minute: float = 0.0
    most_common_type: Optional[AlertType] = None
    last_alert_time: Optional[datetime] = None


class AlertManager:
    """
    Manages alert rules, evaluates conditions, and tracks history.
    
    Usage:
        manager = AlertManager()
        manager.add_rule(...)
        alerts = manager.evaluate(current_features)
        manager.get_active_alerts()
    """
    
    def __init__(self, max_history: int = 500):
        """
        Initialize the alert manager.
        
        Args:
            max_history: Maximum number of alerts to retain in history
        """
        self.rules: Dict[str, AlertRule] = {}
        self.alert_history: deque = deque(maxlen=max_history)
        self.active_alerts: List[Alert] = []
        
        # Cooldown tracking
        self._last_triggered: Dict[str, datetime] = {}
        
        # Statistics
        self._alert_counts: Dict[AlertType, int] = {}
        self._start_time = datetime.utcnow()
        
        # Initialize with default rules
        self._create_default_rules()
    
    def _create_default_rules(self):
        """Create default alert rules for common HFT scenarios."""
        default_rules = [
            AlertRule(
                id="price_high",
                name="Price Above Threshold",
                alert_type=AlertType.PRICE_THRESHOLD,
                condition="price > threshold",
                threshold=100000,  # Will be updated by user
                comparison=">",
                priority=AlertPriority.HIGH,
                message_template="Price reached ${value:,.2f} (above ${threshold:,.2f})",
                enabled=False  # Disabled by default, user enables
            ),
            AlertRule(
                id="price_low",
                name="Price Below Threshold",
                alert_type=AlertType.PRICE_THRESHOLD,
                condition="price < threshold",
                threshold=80000,
                comparison="<",
                priority=AlertPriority.HIGH,
                message_template="Price dropped to ${value:,.2f} (below ${threshold:,.2f})",
                enabled=False
            ),
            AlertRule(
                id="spread_wide",
                name="Spread Widening",
                alert_type=AlertType.SPREAD_THRESHOLD,
                condition="spread_bps > threshold",
                threshold=5.0,
                comparison=">",
                priority=AlertPriority.MEDIUM,
                message_template="Spread widened to {value:.2f} bps (threshold: {threshold:.1f} bps)",
                enabled=True
            ),
            AlertRule(
                id="volatility_spike",
                name="Volatility Spike",
                alert_type=AlertType.VOLATILITY_THRESHOLD,
                condition="volatility_bps > threshold",
                threshold=25.0,
                comparison=">",
                priority=AlertPriority.HIGH,
                message_template="Volatility spiked to {value:.1f} bps — High risk regime!",
                enabled=True
            ),
            AlertRule(
                id="volatility_low",
                name="Low Volatility",
                alert_type=AlertType.VOLATILITY_THRESHOLD,
                condition="volatility_bps < threshold",
                threshold=8.0,
                comparison="<",
                priority=AlertPriority.LOW,
                message_template="Low volatility at {value:.1f} bps — Range-bound market",
                enabled=True
            ),
            AlertRule(
                id="strong_buy_pressure",
                name="Strong Buy Pressure",
                alert_type=AlertType.IMBALANCE_THRESHOLD,
                condition="imbalance > threshold",
                threshold=0.6,
                comparison=">",
                priority=AlertPriority.MEDIUM,
                message_template="Strong buying pressure: {value:.1%} order book imbalance",
                enabled=True
            ),
            AlertRule(
                id="strong_sell_pressure",
                name="Strong Sell Pressure",
                alert_type=AlertType.IMBALANCE_THRESHOLD,
                condition="imbalance < threshold",
                threshold=-0.6,
                comparison="<",
                priority=AlertPriority.HIGH,
                message_template="Strong selling pressure: {value:.1%} order book imbalance",
                enabled=True
            ),
            AlertRule(
                id="velocity_spike",
                name="Trade Velocity Spike",
                alert_type=AlertType.VELOCITY_THRESHOLD,
                condition="velocity > threshold",
                threshold=50.0,
                comparison=">",
                priority=AlertPriority.MEDIUM,
                message_template="Trade velocity spike: {value:.1f} trades/sec (normal: ~{threshold:.0f})",
                enabled=True
            ),
            AlertRule(
                id="ml_strong_signal",
                name="ML Strong Signal",
                alert_type=AlertType.ML_SIGNAL,
                condition="signal_strength > threshold",
                threshold=70.0,
                comparison=">",
                priority=AlertPriority.HIGH,
                message_template="ML detected strong {direction} signal (confidence: {value:.0f}%)",
                enabled=True
            ),
            AlertRule(
                id="regime_change",
                name="Market Regime Change",
                alert_type=AlertType.REGIME_CHANGE,
                condition="regime != previous_regime",
                threshold=0,
                comparison="!=",
                priority=AlertPriority.MEDIUM,
                message_template="Market regime changed to {regime}",
                enabled=True
            ),
            AlertRule(
                id="price_1pct_move",
                name="1% Price Move",
                alert_type=AlertType.PRICE_CHANGE,
                condition="price_change_pct > threshold",
                threshold=1.0,
                comparison=">",
                priority=AlertPriority.HIGH,
                message_template="Price moved {value:+.2f}% in session",
                enabled=True,
                cooldown_seconds=60
            )
        ]
        
        for rule in default_rules:
            self.rules[rule.id] = rule
    
    def add_rule(self, rule: AlertRule) -> str:
        """
        Add a new alert rule.
        
        Args:
            rule: AlertRule to add
            
        Returns:
            Rule ID
        """
        if not rule.id:
            rule.id = str(uuid.uuid4())[:8]
        
        self.rules[rule.id] = rule
        return rule.id
    
    def remove_rule(self, rule_id: str) -> bool:
        """Remove an alert rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
            return True
        return False
    
    def enable_rule(self, rule_id: str, enabled: bool = True):
        """Enable or disable a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].enabled = enabled
    
    def update_threshold(self, rule_id: str, new_threshold: float):
        """Update the threshold for a rule."""
        if rule_id in self.rules:
            self.rules[rule_id].threshold = new_threshold
    
    def evaluate(self, features: Dict[str, Any], 
                 ml_prediction: Optional[Any] = None,
                 previous_regime: Optional[str] = None) -> List[Alert]:
        """
        Evaluate all enabled rules against current features.
        
        Args:
            features: Dictionary of current market features
            ml_prediction: Optional ML prediction result
            previous_regime: Previous market regime for change detection
            
        Returns:
            List of triggered alerts
        """
        now = datetime.utcnow()
        triggered_alerts = []
        
        for rule_id, rule in self.rules.items():
            if not rule.enabled:
                continue
            
            # Check cooldown
            if rule_id in self._last_triggered:
                elapsed = (now - self._last_triggered[rule_id]).total_seconds()
                if elapsed < rule.cooldown_seconds:
                    continue
            
            # Evaluate rule
            triggered, value = self._evaluate_rule(
                rule, features, ml_prediction, previous_regime
            )
            
            if triggered:
                alert = self._create_alert(rule, value, features, ml_prediction)
                triggered_alerts.append(alert)
                
                # Update tracking
                self._last_triggered[rule_id] = now
                self.alert_history.append(alert)
                self._alert_counts[rule.alert_type] = \
                    self._alert_counts.get(rule.alert_type, 0) + 1
        
        # Update active alerts
        self.active_alerts = triggered_alerts
        
        return triggered_alerts
    
    def _evaluate_rule(self, rule: AlertRule, features: Dict[str, Any],
                       ml_prediction: Optional[Any],
                       previous_regime: Optional[str]) -> tuple:
        """Evaluate a single rule."""
        try:
            value = 0.0
            
            if rule.alert_type == AlertType.PRICE_THRESHOLD:
                value = features.get("current_price", features.get("mid_price", 0))
                
            elif rule.alert_type == AlertType.SPREAD_THRESHOLD:
                value = features.get("spread_bps", 0)
                
            elif rule.alert_type == AlertType.VOLATILITY_THRESHOLD:
                value = features.get("volatility_bps", features.get("volatility", 0))
                
            elif rule.alert_type == AlertType.IMBALANCE_THRESHOLD:
                value = features.get("imbalance", 0)
                
            elif rule.alert_type == AlertType.VELOCITY_THRESHOLD:
                value = features.get("velocity", 0)
                
            elif rule.alert_type == AlertType.PRICE_CHANGE:
                value = abs(features.get("price_change_pct", 0))
                
            elif rule.alert_type == AlertType.ML_SIGNAL:
                if ml_prediction:
                    value = getattr(ml_prediction, "signal_strength", 0)
                else:
                    return False, 0
                    
            elif rule.alert_type == AlertType.REGIME_CHANGE:
                if ml_prediction and previous_regime:
                    current_regime = getattr(ml_prediction, "regime", None)
                    if current_regime and str(current_regime) != str(previous_regime):
                        return True, 0
                return False, 0
            
            # Compare
            threshold = rule.threshold
            comparison = rule.comparison
            
            if comparison == ">":
                return value > threshold, value
            elif comparison == "<":
                return value < threshold, value
            elif comparison == ">=":
                return value >= threshold, value
            elif comparison == "<=":
                return value <= threshold, value
            elif comparison == "==":
                return value == threshold, value
            elif comparison == "!=":
                return value != threshold, value
            
            return False, value
            
        except Exception as e:
            return False, 0
    
    def _create_alert(self, rule: AlertRule, value: float,
                      features: Dict[str, Any],
                      ml_prediction: Optional[Any]) -> Alert:
        """Create an alert instance from a triggered rule."""
        # Format message
        try:
            format_vars = {
                "value": value,
                "threshold": rule.threshold,
                **features
            }
            
            if ml_prediction:
                format_vars["direction"] = getattr(
                    ml_prediction, "signal_action", "UNKNOWN"
                )
                format_vars["regime"] = str(getattr(
                    ml_prediction, "regime", "UNKNOWN"
                ))
            
            message = rule.message_template.format(**format_vars)
        except Exception:
            message = f"{rule.name}: Value={value:.2f}, Threshold={rule.threshold:.2f}"
        
        return Alert(
            id=str(uuid.uuid4())[:8],
            rule_id=rule.id,
            rule_name=rule.name,
            priority=rule.priority,
            alert_type=rule.alert_type,
            message=message,
            value=value,
            threshold=rule.threshold,
            timestamp=datetime.utcnow()
        )
    
    def acknowledge_alert(self, alert_id: str) -> bool:
        """Acknowledge an alert."""
        for alert in self.alert_history:
            if alert.id == alert_id:
                alert.acknowledged = True
                alert.acknowledged_at = datetime.utcnow()
                return True
        return False
    
    def acknowledge_all(self):
        """Acknowledge all alerts."""
        now = datetime.utcnow()
        for alert in self.alert_history:
            if not alert.acknowledged:
                alert.acknowledged = True
                alert.acknowledged_at = now
    
    def get_active_alerts(self, max_count: int = 10) -> List[Alert]:
        """Get most recent active alerts."""
        return list(self.active_alerts)[:max_count]
    
    def get_alert_history(self, 
                          minutes: int = 60,
                          priority: Optional[AlertPriority] = None,
                          alert_type: Optional[AlertType] = None,
                          acknowledged: Optional[bool] = None) -> List[Alert]:
        """
        Get alert history with optional filters.
        
        Args:
            minutes: How far back to look
            priority: Filter by priority level
            alert_type: Filter by alert type
            acknowledged: Filter by acknowledgment status
        """
        cutoff = datetime.utcnow() - timedelta(minutes=minutes)
        
        alerts = [a for a in self.alert_history if a.timestamp >= cutoff]
        
        if priority:
            alerts = [a for a in alerts if a.priority == priority]
        
        if alert_type:
            alerts = [a for a in alerts if a.alert_type == alert_type]
        
        if acknowledged is not None:
            alerts = [a for a in alerts if a.acknowledged == acknowledged]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def get_stats(self) -> AlertStats:
        """Get alert statistics."""
        stats = AlertStats()
        
        stats.total_alerts = len(self.alert_history)
        
        # Count by priority
        for alert in self.alert_history:
            if alert.priority == AlertPriority.CRITICAL:
                stats.critical_count += 1
            elif alert.priority == AlertPriority.HIGH:
                stats.high_count += 1
            elif alert.priority == AlertPriority.MEDIUM:
                stats.medium_count += 1
            elif alert.priority == AlertPriority.LOW:
                stats.low_count += 1
            else:
                stats.info_count += 1
        
        # Alerts per minute
        elapsed_minutes = (datetime.utcnow() - self._start_time).total_seconds() / 60
        if elapsed_minutes > 0:
            stats.alerts_per_minute = stats.total_alerts / elapsed_minutes
        
        # Most common type
        if self._alert_counts:
            stats.most_common_type = max(
                self._alert_counts.keys(),
                key=lambda k: self._alert_counts[k]
            )
        
        # Last alert time
        if self.alert_history:
            stats.last_alert_time = self.alert_history[-1].timestamp
        
        return stats
    
    def get_rules_summary(self) -> List[Dict]:
        """Get summary of all rules."""
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "type": rule.alert_type.value,
                "threshold": rule.threshold,
                "priority": rule.priority.value,
                "enabled": rule.enabled,
                "cooldown": rule.cooldown_seconds
            }
            for rule in self.rules.values()
        ]
    
    def clear_history(self):
        """Clear alert history."""
        self.alert_history.clear()
        self.active_alerts.clear()
        self._alert_counts.clear()
        self._start_time = datetime.utcnow()
