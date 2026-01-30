"""
HFT Live Dashboard - Insight Generator
========================================

Transforms triggered rules into formatted insights for display.
Handles priority sorting and insight limiting.
"""

from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import INSIGHT_CONFIG, COLORS
from decision.rule_engine import RuleEngine, TriggeredRule
from features.feature_engine import Features


@dataclass
class Insight:
    """Formatted insight for UI display."""
    id: int
    priority: str
    priority_emoji: str
    priority_color: str
    insight: str
    action: str
    how_to_overcome: str
    expected_impact: str
    triggered_at: datetime
    age_seconds: float = 0.0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "priority": self.priority,
            "priority_emoji": self.priority_emoji,
            "priority_color": self.priority_color,
            "insight": self.insight,
            "action": self.action,
            "how_to_overcome": self.how_to_overcome,
            "expected_impact": self.expected_impact,
            "triggered_at": self.triggered_at.isoformat() if self.triggered_at else None,
            "age_seconds": self.age_seconds
        }


class InsightGenerator:
    """
    Generates and manages trading insights.
    
    Features:
    - Converts triggered rules to formatted insights
    - Priority-based sorting (HIGH > MEDIUM > LOW)
    - Limits number of displayed insights
    - Tracks insight history and freshness
    """
    
    def __init__(self, rule_engine: Optional[RuleEngine] = None):
        """
        Initialize the insight generator.
        
        Args:
            rule_engine: Optional RuleEngine instance (creates one if not provided)
        """
        self.rule_engine = rule_engine or RuleEngine()
        self.config = INSIGHT_CONFIG
        
        # Priority ordering (lower = higher priority)
        self.priority_order = {
            "HIGH": 1,
            "MEDIUM": 2,
            "LOW": 3
        }
        
        # Active insights (persists between updates)
        self._active_insights: List[Insight] = []
        self._insight_ttl_seconds = 30  # How long to show an insight
    
    def generate(self, features: Features) -> List[Insight]:
        """
        Generate insights from current features.
        
        Args:
            features: Current market features
            
        Returns:
            List of top insights, sorted by priority
        """
        now = datetime.utcnow()
        
        # Evaluate rules
        triggered_rules = self.rule_engine.evaluate(features)
        
        # Convert to insights
        new_insights = [
            self._rule_to_insight(rule, now)
            for rule in triggered_rules
        ]
        
        # Merge with active insights
        self._merge_insights(new_insights, now)
        
        # Clean expired insights
        self._clean_expired(now)
        
        # Sort by priority
        sorted_insights = self._sort_by_priority(self._active_insights)
        
        # Return top N insights
        return sorted_insights[:self.config.max_insights]
    
    def _rule_to_insight(self, rule: TriggeredRule, now: datetime) -> Insight:
        """Convert a triggered rule to an insight."""
        priority_config = self.config.priorities.get(
            rule.priority,
            {"emoji": "⚪", "color": COLORS.text_secondary}
        )
        
        return Insight(
            id=rule.id,
            priority=rule.priority,
            priority_emoji=priority_config["emoji"],
            priority_color=priority_config["color"],
            insight=rule.insight,
            action=rule.action,
            how_to_overcome=rule.how_to_overcome,
            expected_impact=rule.expected_impact,
            triggered_at=rule.triggered_at,
            age_seconds=(now - rule.triggered_at).total_seconds()
        )
    
    def _merge_insights(self, new_insights: List[Insight], now: datetime) -> None:
        """Merge new insights with active insights."""
        # Create lookup of new insights by rule ID
        new_by_id = {i.id: i for i in new_insights}
        
        # Update existing or add new
        updated_ids = set()
        for i, insight in enumerate(self._active_insights):
            if insight.id in new_by_id:
                # Update existing insight
                self._active_insights[i] = new_by_id[insight.id]
                updated_ids.add(insight.id)
        
        # Add truly new insights
        for insight in new_insights:
            if insight.id not in updated_ids:
                self._active_insights.append(insight)
    
    def _clean_expired(self, now: datetime) -> None:
        """Remove expired insights."""
        self._active_insights = [
            insight for insight in self._active_insights
            if (now - insight.triggered_at).total_seconds() < self._insight_ttl_seconds
        ]
    
    def _sort_by_priority(self, insights: List[Insight]) -> List[Insight]:
        """Sort insights by priority (HIGH first) then by recency."""
        return sorted(
            insights,
            key=lambda i: (
                self.priority_order.get(i.priority, 99),
                -i.triggered_at.timestamp()  # More recent first
            )
        )
    
    def get_all_active(self) -> List[Insight]:
        """Get all active insights (not limited)."""
        now = datetime.utcnow()
        self._clean_expired(now)
        return self._sort_by_priority(self._active_insights)
    
    def clear_all(self) -> None:
        """Clear all active insights."""
        self._active_insights.clear()
        self.rule_engine.reset_cooldowns()
    
    def set_ttl(self, seconds: float) -> None:
        """Set insight time-to-live."""
        self._insight_ttl_seconds = seconds
    
    def set_max_insights(self, count: int) -> None:
        """Set maximum insights to display."""
        self.config.max_insights = count
    
    def get_insight_count(self) -> Dict[str, int]:
        """Get count of insights by priority."""
        counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        for insight in self._active_insights:
            if insight.priority in counts:
                counts[insight.priority] += 1
        return counts


def generate_default_insights() -> List[Insight]:
    """
    Generate default/placeholder insights when no rules are triggered.
    
    Returns informational insights to show the system is working.
    """
    now = datetime.utcnow()
    
    return [
        Insight(
            id=0,
            priority="LOW",
            priority_emoji="🟢",
            priority_color=COLORS.accent_green,
            insight="Market conditions normal — no action required",
            action="Continue monitoring; no immediate action needed",
            how_to_overcome="Maintain current strategy parameters",
            expected_impact="Steady execution quality",
            triggered_at=now,
            age_seconds=0
        )
    ]


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    """Test the insight generator."""
    print("Testing Insight Generator...")
    print("=" * 60)
    
    # Create generator
    generator = InsightGenerator()
    generator.rule_engine.set_cooldown(0)  # No cooldown for testing
    generator.set_ttl(60)  # 60 second TTL
    
    # Test with features that trigger multiple rules
    test_features = Features(
        spread_bps=7.5,  # Triggers Rule 1 (wide spread)
        imbalance=-0.55,  # Triggers Rule 3 (sell pressure)
        imbalance_pct=-55.0,
        volatility_bps=22.0,  # Triggers Rule 5 (high volatility)
        velocity=45.0,
        velocity_baseline=20.0,  # Triggers Rule 7 (velocity spike)
        price_vs_vwap=0.12,  # Triggers Rule 9 (overbought)
        current_price=42100,
        vwap=42000
    )
    
    print("\nInput Features:")
    print(f"  Spread: {test_features.spread_bps:.1f} bps")
    print(f"  Imbalance: {test_features.imbalance_pct:.1f}%")
    print(f"  Volatility: {test_features.volatility_bps:.1f} bps")
    print(f"  Velocity: {test_features.velocity:.1f}/s (baseline: {test_features.velocity_baseline:.1f}/s)")
    print(f"  Price vs VWAP: {test_features.price_vs_vwap:.2f}%")
    
    # Generate insights
    insights = generator.generate(test_features)
    
    print(f"\nGenerated Insights ({len(insights)} shown, {len(generator.get_all_active())} total):")
    print("-" * 60)
    
    for insight in insights:
        print(f"\n{insight.priority_emoji} {insight.priority} (Rule {insight.id})")
        print(f"   Insight: {insight.insight}")
        print(f"   Action: {insight.action}")
        print(f"   How to Overcome: {insight.how_to_overcome}")
        print(f"   Expected Impact: {insight.expected_impact}")
    
    # Test counts
    counts = generator.get_insight_count()
    print(f"\nInsight Counts: HIGH={counts['HIGH']}, MEDIUM={counts['MEDIUM']}, LOW={counts['LOW']}")
    
    # Test with no triggers
    print("\n" + "=" * 60)
    print("Testing with normal market conditions:")
    
    normal_features = Features(
        spread_bps=3.0,
        imbalance=0.1,
        imbalance_pct=10.0,
        volatility_bps=12.0,
        velocity=22.0,
        velocity_baseline=20.0,
        price_vs_vwap=0.02,
        current_price=42000,
        vwap=42000
    )
    
    generator.clear_all()
    insights = generator.generate(normal_features)
    
    if not insights:
        print("No insights triggered - using defaults")
        insights = generate_default_insights()
    
    for insight in insights:
        print(f"\n{insight.priority_emoji} {insight.priority}")
        print(f"   Insight: {insight.insight}")
    
    print("\nTest complete!")
