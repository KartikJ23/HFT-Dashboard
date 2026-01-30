"""
HFT Live Dashboard - Rule Engine
=================================

Evaluates trading rules against current market features.
Implements 10 trading rules with priority levels.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import THRESHOLDS, RULES
from features.feature_engine import Features


@dataclass
class TriggeredRule:
    """Represents a triggered rule with all metadata."""
    id: int
    priority: str
    condition: str
    insight: str
    action: str
    how_to_overcome: str
    expected_impact: str
    triggered_at: datetime
    feature_values: Dict[str, float]


class RuleEngine:
    """
    Evaluates trading rules against market features.
    
    Implements 10 rules covering:
    - Spread conditions (Rules 1-2)
    - Order book imbalance (Rules 3-4)
    - Volatility (Rules 5-6)
    - Trade velocity (Rules 7-8)
    - Price vs VWAP (Rules 9-10)
    """
    
    def __init__(self):
        """Initialize the rule engine."""
        self.thresholds = THRESHOLDS
        self.rules = RULES
        
        # Track last triggered rules to avoid spam
        self._last_triggered: Dict[int, datetime] = {}
        self._cooldown_seconds = 5  # Minimum seconds between same rule triggers
    
    def evaluate(self, features: Features) -> List[TriggeredRule]:
        """
        Evaluate all rules against current features.
        
        Args:
            features: Current market features
            
        Returns:
            List of triggered rules
        """
        triggered = []
        now = datetime.utcnow()
        
        # Rule 1: Spread too wide
        if self._should_trigger(1, now):
            if features.spread_bps > self.thresholds.spread_high_bps:
                triggered.append(self._create_triggered_rule(
                    rule_id=1,
                    features=features,
                    now=now
                ))
        
        # Rule 2: Spread optimal (low)
        if self._should_trigger(2, now):
            if features.spread_bps < self.thresholds.spread_low_bps and features.spread_bps > 0:
                triggered.append(self._create_triggered_rule(
                    rule_id=2,
                    features=features,
                    now=now
                ))
        
        # Rule 3: Strong sell pressure
        if self._should_trigger(3, now):
            if features.imbalance < self.thresholds.imbalance_strong_sell:
                triggered.append(self._create_triggered_rule(
                    rule_id=3,
                    features=features,
                    now=now
                ))
        
        # Rule 4: Strong buy pressure
        if self._should_trigger(4, now):
            if features.imbalance > self.thresholds.imbalance_strong_buy:
                triggered.append(self._create_triggered_rule(
                    rule_id=4,
                    features=features,
                    now=now
                ))
        
        # Rule 5: High volatility
        if self._should_trigger(5, now):
            if features.volatility_bps > self.thresholds.volatility_high_bps:
                triggered.append(self._create_triggered_rule(
                    rule_id=5,
                    features=features,
                    now=now
                ))
        
        # Rule 6: Low volatility
        if self._should_trigger(6, now):
            if 0 < features.volatility_bps < self.thresholds.volatility_low_bps:
                triggered.append(self._create_triggered_rule(
                    rule_id=6,
                    features=features,
                    now=now
                ))
        
        # Rule 7: Velocity spike
        if self._should_trigger(7, now):
            threshold = features.velocity_baseline * self.thresholds.velocity_spike_multiplier
            if features.velocity > threshold and features.velocity_baseline > 0:
                triggered.append(self._create_triggered_rule(
                    rule_id=7,
                    features=features,
                    now=now
                ))
        
        # Rule 8: Thin market (low velocity)
        if self._should_trigger(8, now):
            threshold = features.velocity_baseline * self.thresholds.velocity_thin_multiplier
            if 0 < features.velocity < threshold and features.velocity_baseline > 0:
                triggered.append(self._create_triggered_rule(
                    rule_id=8,
                    features=features,
                    now=now
                ))
        
        # Rule 9: Price above VWAP (overbought)
        if self._should_trigger(9, now):
            if features.price_vs_vwap > self.thresholds.price_overbought_pct:
                triggered.append(self._create_triggered_rule(
                    rule_id=9,
                    features=features,
                    now=now
                ))
        
        # Rule 10: Price below VWAP (value zone)
        if self._should_trigger(10, now):
            if features.price_vs_vwap < self.thresholds.price_oversold_pct:
                triggered.append(self._create_triggered_rule(
                    rule_id=10,
                    features=features,
                    now=now
                ))
        
        return triggered
    
    def _should_trigger(self, rule_id: int, now: datetime) -> bool:
        """Check if rule should trigger based on cooldown."""
        if rule_id not in self._last_triggered:
            return True
        
        elapsed = (now - self._last_triggered[rule_id]).total_seconds()
        return elapsed >= self._cooldown_seconds
    
    def _create_triggered_rule(self, rule_id: int, features: Features, 
                                now: datetime) -> TriggeredRule:
        """Create a triggered rule with formatted messages."""
        # Find rule definition
        rule_def = next((r for r in self.rules if r["id"] == rule_id), None)
        
        if rule_def is None:
            raise ValueError(f"Unknown rule ID: {rule_id}")
        
        # Update last triggered time
        self._last_triggered[rule_id] = now
        
        # Format insight message with feature values
        insight = self._format_message(rule_def["insight"], features)
        
        # Store feature values for reference
        feature_values = {
            "spread_bps": features.spread_bps,
            "imbalance": features.imbalance,
            "imbalance_pct": features.imbalance_pct,
            "volatility_bps": features.volatility_bps,
            "velocity": features.velocity,
            "baseline": features.velocity_baseline,
            "price_vs_vwap": features.price_vs_vwap,
            "current_price": features.current_price,
            "vwap": features.vwap
        }
        
        return TriggeredRule(
            id=rule_id,
            priority=rule_def["priority"],
            condition=rule_def["condition"],
            insight=insight,
            action=rule_def["action"],
            how_to_overcome=rule_def["how_to_overcome"],
            expected_impact=rule_def["expected_impact"],
            triggered_at=now,
            feature_values=feature_values
        )
    
    def _format_message(self, template: str, features: Features) -> str:
        """Format a message template with feature values."""
        try:
            return template.format(
                spread_bps=features.spread_bps,
                imbalance=features.imbalance,
                imbalance_pct=features.imbalance_pct,
                volatility_bps=features.volatility_bps,
                velocity=features.velocity,
                baseline=features.velocity_baseline,
                price_vs_vwap=features.price_vs_vwap,
                price=features.current_price,
                vwap=features.vwap
            )
        except (KeyError, ValueError) as e:
            # Return template if formatting fails
            return template
    
    def reset_cooldowns(self) -> None:
        """Reset all rule cooldowns."""
        self._last_triggered.clear()
    
    def set_cooldown(self, seconds: float) -> None:
        """Set cooldown period between same rule triggers."""
        self._cooldown_seconds = seconds
    
    def get_all_rules(self) -> List[Dict]:
        """Get all rule definitions."""
        return self.rules.copy()


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    """Test the rule engine with mock features."""
    print("Testing Rule Engine...")
    print("=" * 50)
    
    engine = RuleEngine()
    engine.set_cooldown(0)  # No cooldown for testing
    
    # Test cases
    test_cases = [
        {
            "name": "Wide Spread (Rule 1)",
            "features": Features(
                spread_bps=8.0,
                imbalance=0.0,
                volatility_bps=15.0,
                velocity=25.0,
                velocity_baseline=20.0,
                price_vs_vwap=0.0
            ),
            "expected_rule": 1
        },
        {
            "name": "Low Spread (Rule 2)",
            "features": Features(
                spread_bps=1.5,
                imbalance=0.0,
                volatility_bps=15.0,
                velocity=25.0,
                velocity_baseline=20.0,
                price_vs_vwap=0.0
            ),
            "expected_rule": 2
        },
        {
            "name": "Strong Sell Pressure (Rule 3)",
            "features": Features(
                spread_bps=3.0,
                imbalance=-0.6,
                imbalance_pct=-60.0,
                volatility_bps=15.0,
                velocity=25.0,
                velocity_baseline=20.0,
                price_vs_vwap=0.0
            ),
            "expected_rule": 3
        },
        {
            "name": "Velocity Spike (Rule 7)",
            "features": Features(
                spread_bps=3.0,
                imbalance=0.0,
                volatility_bps=15.0,
                velocity=50.0,
                velocity_baseline=20.0,
                price_vs_vwap=0.0
            ),
            "expected_rule": 7
        },
        {
            "name": "Overbought (Rule 9)",
            "features": Features(
                spread_bps=3.0,
                imbalance=0.0,
                volatility_bps=15.0,
                velocity=25.0,
                velocity_baseline=20.0,
                price_vs_vwap=0.15,
                current_price=42100,
                vwap=42000
            ),
            "expected_rule": 9
        }
    ]
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 40)
        
        triggered = engine.evaluate(test["features"])
        
        if triggered:
            for rule in triggered:
                print(f"  ✓ Rule {rule.id} ({rule.priority})")
                print(f"    Insight: {rule.insight}")
                print(f"    Action: {rule.action}")
        else:
            print("  ✗ No rules triggered")
        
        # Verify expected rule
        rule_ids = [r.id for r in triggered]
        if test["expected_rule"] in rule_ids:
            print(f"  ✓ Expected rule {test['expected_rule']} triggered")
        else:
            print(f"  ✗ Expected rule {test['expected_rule']} NOT triggered")
    
    print("\nTest complete!")
