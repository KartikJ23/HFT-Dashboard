"""
HFT Live Dashboard - Unit Tests
================================

Tests for feature calculations and rule engine.
"""

import pytest
from datetime import datetime, timedelta
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from data.state_manager import StateManager, Trade, DepthSnapshot
from features.feature_engine import FeatureEngine, Features
from decision.rule_engine import RuleEngine, TriggeredRule
from decision.insight_generator import InsightGenerator, Insight


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def state_manager():
    """Create a fresh StateManager instance."""
    return StateManager()


@pytest.fixture
def populated_state(state_manager):
    """Create StateManager with sample data."""
    now = datetime.utcnow()
    
    # Add sample trades
    for i in range(100):
        state_manager.add_trade_raw(
            timestamp=now - timedelta(seconds=60 - i * 0.6),
            price=42000.0 + (i % 10) - 5,
            quantity=0.01 + (i % 5) * 0.01,
            is_buyer_maker=(i % 2 == 0),
            trade_id=i
        )
    
    # Add sample depth
    state_manager.add_depth_raw(
        timestamp=now,
        bids=[[str(42000 - i), str(1.0 + i * 0.1)] for i in range(10)],
        asks=[[str(42001 + i), str(0.8 + i * 0.1)] for i in range(10)]
    )
    
    return state_manager


@pytest.fixture
def feature_engine(populated_state):
    """Create FeatureEngine with populated state."""
    return FeatureEngine(populated_state)


@pytest.fixture
def rule_engine():
    """Create RuleEngine with no cooldown."""
    engine = RuleEngine()
    engine.set_cooldown(0)
    return engine


# =============================================================================
# STATE MANAGER TESTS
# =============================================================================

class TestStateManager:
    """Tests for StateManager."""
    
    def test_initialization(self, state_manager):
        """Test initial state."""
        assert state_manager.get_current_price() == 0.0
        assert state_manager.is_connected() == False
        assert len(state_manager.get_trades()) == 0
    
    def test_add_trade(self, state_manager):
        """Test adding trades."""
        now = datetime.utcnow()
        state_manager.add_trade_raw(
            timestamp=now,
            price=42000.0,
            quantity=0.01,
            is_buyer_maker=True,
            trade_id=1
        )
        
        trades = state_manager.get_trades()
        assert len(trades) == 1
        assert trades[0].price == 42000.0
        assert state_manager.get_current_price() == 42000.0
    
    def test_add_depth(self, state_manager):
        """Test adding depth snapshots."""
        now = datetime.utcnow()
        state_manager.add_depth_raw(
            timestamp=now,
            bids=[["42000", "1.0"], ["41999", "2.0"]],
            asks=[["42001", "1.5"], ["42002", "1.0"]]
        )
        
        depth = state_manager.get_latest_depth()
        assert depth is not None
        assert depth.best_bid == 42000.0
        assert depth.best_ask == 42001.0
        assert state_manager.get_current_mid_price() == 42000.5
    
    def test_buffer_limits(self, state_manager):
        """Test circular buffer behavior."""
        now = datetime.utcnow()
        
        # Add more trades than buffer size
        for i in range(1500):
            state_manager.add_trade_raw(
                timestamp=now,
                price=42000.0,
                quantity=0.01,
                is_buyer_maker=True,
                trade_id=i
            )
        
        # Buffer should be limited
        trades = state_manager.get_trades()
        assert len(trades) <= 1000
    
    def test_connection_status(self, state_manager):
        """Test connection status tracking."""
        assert state_manager.get_connection_status() == "disconnected"
        
        state_manager.set_connected(True)
        assert state_manager.get_connection_status() == "connected"
        assert state_manager.is_connected() == True
        
        state_manager.set_reconnecting()
        assert state_manager.get_connection_status() == "reconnecting"
        assert state_manager.is_connected() == False


# =============================================================================
# FEATURE ENGINE TESTS
# =============================================================================

class TestFeatureEngine:
    """Tests for FeatureEngine calculations."""
    
    def test_mid_price_calculation(self, feature_engine):
        """Test mid price calculation."""
        features = feature_engine.calculate_all()
        # (42000 + 42001) / 2 = 42000.5
        assert abs(features.mid_price - 42000.5) < 0.1
    
    def test_spread_calculation(self, feature_engine):
        """Test spread calculation."""
        features = feature_engine.calculate_all()
        # 42001 - 42000 = 1
        assert abs(features.spread - 1.0) < 0.1
    
    def test_spread_bps_calculation(self, feature_engine):
        """Test spread in basis points."""
        features = feature_engine.calculate_all()
        # (1 / 42000.5) * 10000 ≈ 2.38 bps
        assert 2.0 < features.spread_bps < 3.0
    
    def test_imbalance_calculation(self, feature_engine):
        """Test order book imbalance."""
        features = feature_engine.calculate_all()
        # Should be between -1 and 1
        assert -1.0 <= features.imbalance <= 1.0
    
    def test_vwap_calculation(self, feature_engine):
        """Test VWAP calculation."""
        features = feature_engine.calculate_all()
        # Should be close to average price
        assert 41990 < features.vwap < 42010
    
    def test_velocity_calculation(self, feature_engine):
        """Test velocity calculation."""
        features = feature_engine.calculate_all()
        # Should be positive
        assert features.velocity >= 0
    
    def test_buy_pressure_calculation(self, feature_engine):
        """Test buy pressure calculation."""
        features = feature_engine.calculate_all()
        # Should be between 0 and 1
        assert 0.0 <= features.buy_pressure <= 1.0
    
    def test_empty_state(self, state_manager):
        """Test with empty state."""
        engine = FeatureEngine(state_manager)
        features = engine.calculate_all()
        
        # Should return defaults without crashing
        assert features.mid_price == 0.0
        assert features.spread_bps == 0.0
        assert features.velocity == 0.0


# =============================================================================
# RULE ENGINE TESTS
# =============================================================================

class TestRuleEngine:
    """Tests for RuleEngine."""
    
    def test_rule_1_wide_spread(self, rule_engine):
        """Test Rule 1: Spread > 6 bps."""
        features = Features(spread_bps=8.0)
        triggered = rule_engine.evaluate(features)
        
        rule_ids = [r.id for r in triggered]
        assert 1 in rule_ids
    
    def test_rule_2_low_spread(self, rule_engine):
        """Test Rule 2: Spread < 2 bps."""
        features = Features(spread_bps=1.5)
        triggered = rule_engine.evaluate(features)
        
        rule_ids = [r.id for r in triggered]
        assert 2 in rule_ids
    
    def test_rule_3_sell_pressure(self, rule_engine):
        """Test Rule 3: Imbalance < -50%."""
        features = Features(
            spread_bps=3.0,
            imbalance=-0.6,
            imbalance_pct=-60.0
        )
        triggered = rule_engine.evaluate(features)
        
        rule_ids = [r.id for r in triggered]
        assert 3 in rule_ids
    
    def test_rule_5_high_volatility(self, rule_engine):
        """Test Rule 5: Volatility > 20 bps."""
        features = Features(
            spread_bps=3.0,
            volatility_bps=25.0
        )
        triggered = rule_engine.evaluate(features)
        
        rule_ids = [r.id for r in triggered]
        assert 5 in rule_ids
    
    def test_rule_7_velocity_spike(self, rule_engine):
        """Test Rule 7: Velocity > 2x baseline."""
        features = Features(
            spread_bps=3.0,
            velocity=50.0,
            velocity_baseline=20.0
        )
        triggered = rule_engine.evaluate(features)
        
        rule_ids = [r.id for r in triggered]
        assert 7 in rule_ids
    
    def test_rule_9_overbought(self, rule_engine):
        """Test Rule 9: Price > VWAP + 0.1%."""
        features = Features(
            spread_bps=3.0,
            price_vs_vwap=0.15
        )
        triggered = rule_engine.evaluate(features)
        
        rule_ids = [r.id for r in triggered]
        assert 9 in rule_ids
    
    def test_no_rules_triggered(self, rule_engine):
        """Test with normal market conditions."""
        features = Features(
            spread_bps=3.0,
            imbalance=0.1,
            volatility_bps=15.0,
            velocity=22.0,
            velocity_baseline=20.0,
            price_vs_vwap=0.02
        )
        triggered = rule_engine.evaluate(features)
        
        # Should trigger no HIGH priority rules
        high_rules = [r for r in triggered if r.priority == "HIGH"]
        assert len(high_rules) == 0
    
    def test_priority_assignment(self, rule_engine):
        """Test correct priority assignment."""
        # Rule 1 should be HIGH
        features = Features(spread_bps=8.0)
        triggered = rule_engine.evaluate(features)
        
        rule_1 = next((r for r in triggered if r.id == 1), None)
        assert rule_1 is not None
        assert rule_1.priority == "HIGH"


# =============================================================================
# INSIGHT GENERATOR TESTS
# =============================================================================

class TestInsightGenerator:
    """Tests for InsightGenerator."""
    
    def test_insight_generation(self):
        """Test basic insight generation."""
        generator = InsightGenerator()
        generator.rule_engine.set_cooldown(0)
        
        features = Features(
            spread_bps=8.0,
            imbalance=-0.6,
            imbalance_pct=-60.0
        )
        
        insights = generator.generate(features)
        assert len(insights) > 0
    
    def test_priority_sorting(self):
        """Test insights are sorted by priority."""
        generator = InsightGenerator()
        generator.rule_engine.set_cooldown(0)
        generator.set_max_insights(10)
        
        features = Features(
            spread_bps=8.0,       # HIGH
            imbalance=0.6,        # MEDIUM
            imbalance_pct=60.0,
            volatility_bps=5.0    # LOW
        )
        
        insights = generator.generate(features)
        
        # Check sorting
        if len(insights) >= 2:
            for i in range(len(insights) - 1):
                current_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}[insights[i].priority]
                next_order = {"HIGH": 1, "MEDIUM": 2, "LOW": 3}[insights[i+1].priority]
                assert current_order <= next_order
    
    def test_max_insights_limit(self):
        """Test insight limit enforcement."""
        generator = InsightGenerator()
        generator.rule_engine.set_cooldown(0)
        generator.set_max_insights(3)
        
        # Trigger many rules
        features = Features(
            spread_bps=8.0,
            imbalance=-0.6,
            imbalance_pct=-60.0,
            volatility_bps=25.0,
            velocity=50.0,
            velocity_baseline=20.0,
            price_vs_vwap=0.15
        )
        
        insights = generator.generate(features)
        assert len(insights) <= 3
    
    def test_insight_formatting(self):
        """Test insight message formatting."""
        generator = InsightGenerator()
        generator.rule_engine.set_cooldown(0)
        
        features = Features(spread_bps=8.5)
        insights = generator.generate(features)
        
        if insights:
            # Check insight has all required fields
            insight = insights[0]
            assert insight.insight is not None
            assert insight.action is not None
            assert insight.how_to_overcome is not None
            assert insight.expected_impact is not None
            assert "8.5" in insight.insight  # Value should be formatted in


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

class TestIntegration:
    """Integration tests for the full pipeline."""
    
    def test_full_pipeline(self, populated_state):
        """Test full data -> features -> rules -> insights pipeline."""
        # Create components
        feature_engine = FeatureEngine(populated_state)
        rule_engine = RuleEngine()
        rule_engine.set_cooldown(0)
        insight_generator = InsightGenerator(rule_engine)
        
        # Calculate features
        features = feature_engine.calculate_all()
        
        # Should have valid features
        assert features.mid_price > 0
        assert features.spread_bps >= 0
        
        # Generate insights (may or may not trigger based on data)
        insights = insight_generator.generate(features)
        
        # Should return a list (possibly empty)
        assert isinstance(insights, list)
    
    def test_thread_safety(self, state_manager):
        """Test thread-safe operations."""
        import threading
        
        errors = []
        
        def writer():
            try:
                for i in range(100):
                    state_manager.add_trade_raw(
                        timestamp=datetime.utcnow(),
                        price=42000.0,
                        quantity=0.01,
                        is_buyer_maker=True,
                        trade_id=i
                    )
            except Exception as e:
                errors.append(e)
        
        def reader():
            try:
                for _ in range(100):
                    _ = state_manager.get_trades()
                    _ = state_manager.get_current_price()
            except Exception as e:
                errors.append(e)
        
        # Run concurrent threads
        threads = [
            threading.Thread(target=writer),
            threading.Thread(target=reader),
            threading.Thread(target=writer),
            threading.Thread(target=reader)
        ]
        
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        
        # Should complete without errors
        assert len(errors) == 0


# =============================================================================
# RUN TESTS
# =============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
