"""
HFT Dashboard - Strategy Backtester
=====================================

Rule-based backtesting engine with P&L simulation,
risk metrics, and performance analytics.

Features:
- Backtest trading rules against historical data
- P&L calculation with transaction costs
- Risk metrics (Sharpe, Max Drawdown, Win Rate)
- Trade-by-trade analysis
- Strategy comparison
- Monte Carlo simulation for confidence intervals
"""

import numpy as np
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Callable
from collections import deque
from enum import Enum
import random


class TradeDirection(Enum):
    """Trade direction."""
    LONG = "long"
    SHORT = "short"
    CLOSE = "close"


class TradeStatus(Enum):
    """Trade status."""
    OPEN = "open"
    CLOSED = "closed"
    STOPPED = "stopped"


@dataclass
class TradeSignal:
    """A trading signal from the strategy."""
    timestamp: datetime
    direction: TradeDirection
    price: float
    size: float = 1.0
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reason: str = ""
    confidence: float = 0.5


@dataclass
class Trade:
    """A completed trade."""
    id: int
    entry_time: datetime
    exit_time: datetime
    direction: TradeDirection
    entry_price: float
    exit_price: float
    size: float
    pnl: float
    pnl_pct: float
    pnl_bps: float
    commission: float
    status: TradeStatus
    holding_time_seconds: float
    entry_reason: str = ""
    exit_reason: str = ""


@dataclass
class BacktestResult:
    """Complete backtest results."""
    # Summary metrics
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    win_rate: float = 0.0
    
    # P&L statistics
    avg_win: float = 0.0
    avg_loss: float = 0.0
    profit_factor: float = 0.0
    expectancy: float = 0.0
    
    # Risk metrics
    max_drawdown: float = 0.0
    max_drawdown_pct: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    calmar_ratio: float = 0.0
    
    # Timing metrics
    avg_holding_time: float = 0.0
    max_holding_time: float = 0.0
    
    # Trade details
    trades: List[Trade] = field(default_factory=list)
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    drawdown_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    
    # Strategy info
    strategy_name: str = ""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    initial_capital: float = 10000.0
    final_capital: float = 10000.0


@dataclass
class StrategyRule:
    """A trading strategy rule."""
    id: str
    name: str
    entry_condition: Callable[[Dict], bool]
    exit_condition: Callable[[Dict, Trade], bool]
    direction: TradeDirection
    size: float = 1.0
    stop_loss_pct: float = 0.5  # 0.5% stop loss
    take_profit_pct: float = 1.0  # 1% take profit
    enabled: bool = True


class StrategyBacktester:
    """
    Backtesting engine for HFT trading strategies.
    
    Tests trading rules against historical price data
    and calculates comprehensive performance metrics.
    """
    
    def __init__(self, 
                 initial_capital: float = 10000.0,
                 commission_bps: float = 1.0,
                 slippage_bps: float = 0.5):
        """
        Initialize the backtester.
        
        Args:
            initial_capital: Starting capital for simulation
            commission_bps: Commission per trade in basis points
            slippage_bps: Estimated slippage in basis points
        """
        self.initial_capital = initial_capital
        self.commission_bps = commission_bps
        self.slippage_bps = slippage_bps
        
        # Strategy rules
        self.rules: Dict[str, StrategyRule] = {}
        
        # State
        self._reset_state()
        
        # Initialize with default strategies
        self._create_default_strategies()
    
    def _reset_state(self):
        """Reset backtest state."""
        self.current_capital = self.initial_capital
        self.current_position: Optional[Trade] = None
        self.trades: List[Trade] = []
        self.equity_curve: List[Tuple[datetime, float]] = []
        self.trade_counter = 0
    
    def _create_default_strategies(self):
        """Create default trading strategies."""
        
        # Strategy 1: Momentum Breakout
        def momentum_entry(features: Dict) -> bool:
            imbalance = features.get("imbalance", 0)
            velocity = features.get("velocity", 0)
            baseline = features.get("velocity_baseline", 20)
            return imbalance > 0.4 and velocity > baseline * 1.5
        
        def momentum_exit(features: Dict, trade: Trade) -> bool:
            imbalance = features.get("imbalance", 0)
            return imbalance < 0 or trade.holding_time_seconds > 30
        
        self.add_strategy(StrategyRule(
            id="momentum_breakout",
            name="Momentum Breakout",
            entry_condition=momentum_entry,
            exit_condition=momentum_exit,
            direction=TradeDirection.LONG,
            stop_loss_pct=0.3,
            take_profit_pct=0.5
        ))
        
        # Strategy 2: Mean Reversion
        def mean_reversion_entry(features: Dict) -> bool:
            price_vs_vwap = features.get("price_vs_vwap", 0)
            volatility = features.get("volatility_bps", 15)
            return price_vs_vwap < -0.15 and volatility < 20
        
        def mean_reversion_exit(features: Dict, trade: Trade) -> bool:
            price_vs_vwap = features.get("price_vs_vwap", 0)
            return price_vs_vwap > 0 or trade.holding_time_seconds > 60
        
        self.add_strategy(StrategyRule(
            id="mean_reversion",
            name="Mean Reversion",
            entry_condition=mean_reversion_entry,
            exit_condition=mean_reversion_exit,
            direction=TradeDirection.LONG,
            stop_loss_pct=0.2,
            take_profit_pct=0.3
        ))
        
        # Strategy 3: Volatility Breakout
        def volatility_entry(features: Dict) -> bool:
            volatility = features.get("volatility_bps", 15)
            spread = features.get("spread_bps", 3)
            imbalance = features.get("imbalance", 0)
            return volatility > 22 and spread < 5 and abs(imbalance) > 0.5
        
        def volatility_exit(features: Dict, trade: Trade) -> bool:
            volatility = features.get("volatility_bps", 15)
            return volatility < 15 or trade.holding_time_seconds > 20
        
        self.add_strategy(StrategyRule(
            id="volatility_breakout",
            name="Volatility Breakout",
            entry_condition=volatility_entry,
            exit_condition=volatility_exit,
            direction=TradeDirection.LONG,
            stop_loss_pct=0.5,
            take_profit_pct=0.8
        ))
        
        # Strategy 4: Spread Fade
        def spread_fade_entry(features: Dict) -> bool:
            spread = features.get("spread_bps", 3)
            return spread > 6  # Wide spread
        
        def spread_fade_exit(features: Dict, trade: Trade) -> bool:
            spread = features.get("spread_bps", 3)
            return spread < 3 or trade.holding_time_seconds > 45
        
        self.add_strategy(StrategyRule(
            id="spread_fade",
            name="Spread Fade",
            entry_condition=spread_fade_entry,
            exit_condition=spread_fade_exit,
            direction=TradeDirection.LONG,
            stop_loss_pct=0.2,
            take_profit_pct=0.4
        ))
    
    def add_strategy(self, rule: StrategyRule):
        """Add a strategy rule."""
        self.rules[rule.id] = rule
    
    def remove_strategy(self, rule_id: str):
        """Remove a strategy rule."""
        if rule_id in self.rules:
            del self.rules[rule_id]
    
    def run_simple_backtest(self,
                            strategy_name: str,
                            prices: List[float],
                            initial_capital: float = 10000.0) -> BacktestResult:
        """
        Simplified backtest interface that takes just a price series.
        
        This is a convenience method for the UI that simulates trades
        based on the price series with random entry/exit conditions.
        
        Args:
            strategy_name: Name of the strategy for display
            prices: List of price values
            initial_capital: Starting capital
            
        Returns:
            BacktestResult with simulated trades and metrics
        """
        self.initial_capital = initial_capital
        self._reset_state()
        
        if not prices or len(prices) < 10:
            return BacktestResult(strategy_name=strategy_name)
        
        trades = []
        equity = [initial_capital]
        current_capital = initial_capital
        
        # Calculate returns and volatility for entry/exit decisions
        returns = []
        for i in range(1, len(prices)):
            ret = (prices[i] - prices[i-1]) / prices[i-1]
            returns.append(ret)
        
        # Simple momentum-based simulation
        position = None
        position_entry_price = 0
        position_size = 0
        
        # Calculate rolling momentum
        lookback = min(20, len(prices) // 5)
        
        for i in range(lookback, len(prices)):
            price = prices[i]
            
            # Calculate momentum signal
            recent_returns = returns[max(0, i-lookback-1):i-1]
            if len(recent_returns) > 0:
                momentum = sum(recent_returns) / len(recent_returns)
            else:
                momentum = 0
            
            # Calculate recent volatility
            if len(recent_returns) > 1:
                volatility = (sum(r**2 for r in recent_returns) / len(recent_returns)) ** 0.5
            else:
                volatility = 0.001
            
            # Entry logic based on strategy type
            if position is None:
                entry_signal = False
                direction = TradeDirection.LONG
                
                if "Momentum" in strategy_name:
                    # More lenient entry: momentum exceeds 50% of volatility
                    entry_signal = abs(momentum) > volatility * 0.5 and momentum != 0
                    direction = TradeDirection.LONG if momentum > 0 else TradeDirection.SHORT
                elif "Mean Reversion" in strategy_name:
                    # Enter when price moved significantly
                    entry_signal = abs(momentum) > volatility * 1.0
                    direction = TradeDirection.SHORT if momentum > 0 else TradeDirection.LONG
                elif "Volatility" in strategy_name:
                    entry_signal = volatility > 0.0005 and abs(momentum) > volatility * 0.3
                    direction = TradeDirection.LONG if momentum > 0 else TradeDirection.SHORT
                else:  # Spread Fade
                    entry_signal = i % 15 == 0  # Enter periodically for demo
                    direction = TradeDirection.LONG
                
                if entry_signal:
                    position_size = current_capital * 0.1 / price  # 10% position
                    position_entry_price = price
                    position = direction
            
            else:
                # Exit logic
                exit_signal = False
                
                if position == TradeDirection.LONG:
                    pnl_pct = (price - position_entry_price) / position_entry_price * 100
                else:
                    pnl_pct = (position_entry_price - price) / position_entry_price * 100
                
                # Exit conditions
                if pnl_pct <= -0.5:  # Stop loss at 0.5%
                    exit_signal = True
                elif pnl_pct >= 0.3:  # Take profit at 0.3%
                    exit_signal = True
                elif i > lookback + 10 and ((position == TradeDirection.LONG and momentum < 0) or
                                            (position == TradeDirection.SHORT and momentum > 0)):
                    exit_signal = True
                
                if exit_signal:
                    # Record trade
                    trade = Trade(
                        id=len(trades) + 1,
                        entry_time=datetime.utcnow() - timedelta(seconds=(len(prices)-i)*5),
                        exit_time=datetime.utcnow() - timedelta(seconds=(len(prices)-i)*5),
                        direction=position,
                        entry_price=position_entry_price,
                        exit_price=price,
                        size=position_size,
                        pnl=pnl_pct * position_size * position_entry_price / 100,
                        pnl_pct=pnl_pct,
                        pnl_bps=pnl_pct * 100,
                        commission=position_size * position_entry_price * 0.001,
                        status=TradeStatus.CLOSED,
                        holding_time_seconds=float(np.random.randint(5, 60)),
                        entry_reason=strategy_name,
                        exit_reason="Signal Exit"
                    )
                    trades.append(trade)
                    
                    # Update capital
                    current_capital += trade.pnl - trade.commission
                    position = None
            
            equity.append(current_capital)
        
        # Build result
        result = BacktestResult(strategy_name=strategy_name)
        result.trades = trades
        result.total_trades = len(trades)
        result.winning_trades = len([t for t in trades if t.pnl > 0])
        result.losing_trades = len([t for t in trades if t.pnl <= 0])
        result.win_rate = result.winning_trades / result.total_trades if result.total_trades > 0 else 0
        result.total_pnl = sum(t.pnl for t in trades)
        result.total_return_pct = (current_capital - initial_capital) / initial_capital * 100 if initial_capital > 0 else 0
        result.final_capital = current_capital
        
        # Calculate metrics
        if len(trades) > 0:
            winning_pnls = [t.pnl for t in trades if t.pnl > 0]
            losing_pnls = [abs(t.pnl) for t in trades if t.pnl <= 0]
            result.avg_win = sum(winning_pnls) / len(winning_pnls) if winning_pnls else 0
            result.avg_loss = sum(losing_pnls) / len(losing_pnls) if losing_pnls else 0
            result.profit_factor = sum(winning_pnls) / sum(losing_pnls) if sum(losing_pnls) > 0 else 999
        
        # Calculate equity curve returns for Sharpe etc.
        if len(equity) > 1:
            equity_returns = [(equity[i] - equity[i-1]) / equity[i-1] for i in range(1, len(equity)) if equity[i-1] > 0]
            if len(equity_returns) > 0:
                mean_ret = sum(equity_returns) / len(equity_returns)
                std_ret = (sum((r - mean_ret)**2 for r in equity_returns) / len(equity_returns)) ** 0.5
                result.sharpe_ratio = (mean_ret / std_ret) * (252 ** 0.5) if std_ret > 0 else 0
                
                # Sortino
                neg_returns = [r for r in equity_returns if r < 0]
                if len(neg_returns) > 0:
                    downside_std = (sum(r**2 for r in neg_returns) / len(neg_returns)) ** 0.5
                    result.sortino_ratio = (mean_ret / downside_std) * (252 ** 0.5) if downside_std > 0 else 0
        
        # Max drawdown
        peak = equity[0]
        max_dd = 0
        for e in equity:
            if e > peak:
                peak = e
            dd = (peak - e) / peak if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        result.max_drawdown_pct = max_dd * 100
        
        # Calmar ratio
        result.calmar_ratio = result.total_return_pct / result.max_drawdown_pct if result.max_drawdown_pct > 0 else 0
        
        # Equity curve timestamps
        result.equity_curve = [
            (datetime.utcnow() - timedelta(seconds=(len(equity)-i)*5), e)
            for i, e in enumerate(equity)
        ]
        
        return result
    
    def run_backtest(self, 
                     price_data: List[Dict],
                     strategy_id: Optional[str] = None) -> BacktestResult:
        """
        Run backtest on historical price data.
        
        Args:
            price_data: List of dicts with timestamp, price, and features
            strategy_id: Specific strategy to test (None = test all)
            
        Returns:
            BacktestResult with full metrics
        """
        self._reset_state()
        
        if not price_data:
            return BacktestResult(strategy_name="No Data")
        
        strategies = {strategy_id: self.rules[strategy_id]} \
            if strategy_id and strategy_id in self.rules \
            else {k: v for k, v in self.rules.items() if v.enabled}
        
        for data_point in price_data:
            timestamp = data_point.get("timestamp", datetime.utcnow())
            price = data_point.get("price", 0)
            
            if price <= 0:
                continue
            
            # Check if we have an open position
            if self.current_position:
                # Check exit conditions
                for rule_id, rule in strategies.items():
                    # Create pseudo-trade for exit evaluation
                    holding_time = (timestamp - self.current_position.entry_time).total_seconds()
                    
                    class PseudoTrade:
                        pass
                    
                    pt = PseudoTrade()
                    pt.holding_time_seconds = holding_time
                    pt.entry_price = self.current_position.entry_price
                    pt.direction = self.current_position.direction
                    
                    # Check stop loss / take profit
                    pnl_pct = (price - pt.entry_price) / pt.entry_price * 100
                    if pt.direction == TradeDirection.SHORT:
                        pnl_pct = -pnl_pct
                    
                    exit_trade = False
                    exit_reason = ""
                    
                    if pnl_pct <= -rule.stop_loss_pct:
                        exit_trade = True
                        exit_reason = "Stop Loss"
                    elif pnl_pct >= rule.take_profit_pct:
                        exit_trade = True
                        exit_reason = "Take Profit"
                    elif rule.exit_condition(data_point, pt):
                        exit_trade = True
                        exit_reason = "Signal Exit"
                    
                    if exit_trade:
                        self._close_position(timestamp, price, exit_reason)
                        break
            
            else:
                # Check entry conditions
                for rule_id, rule in strategies.items():
                    if rule.entry_condition(data_point):
                        self._open_position(
                            timestamp, price, rule.direction,
                            rule.size, f"{rule.name} Entry"
                        )
                        break
            
            # Record equity
            equity = self._calculate_equity(price)
            self.equity_curve.append((timestamp, equity))
        
        # Close any remaining position
        if self.current_position and price_data:
            last_price = price_data[-1].get("price", 0)
            if last_price > 0:
                self._close_position(
                    price_data[-1].get("timestamp", datetime.utcnow()),
                    last_price, "End of Backtest"
                )
        
        # Calculate results
        result = self._calculate_results(strategy_id or "All Strategies")
        
        return result
    
    def _open_position(self, timestamp: datetime, price: float,
                       direction: TradeDirection, size: float, reason: str):
        """Open a new position."""
        # Apply slippage
        slippage = price * self.slippage_bps / 10000
        entry_price = price + slippage if direction == TradeDirection.LONG else price - slippage
        
        self.trade_counter += 1
        
        self.current_position = Trade(
            id=self.trade_counter,
            entry_time=timestamp,
            exit_time=timestamp,  # Will be updated
            direction=direction,
            entry_price=entry_price,
            exit_price=0,
            size=size,
            pnl=0,
            pnl_pct=0,
            pnl_bps=0,
            commission=0,
            status=TradeStatus.OPEN,
            holding_time_seconds=0,
            entry_reason=reason
        )
    
    def _close_position(self, timestamp: datetime, price: float, reason: str):
        """Close the current position."""
        if not self.current_position:
            return
        
        pos = self.current_position
        
        # Apply slippage
        slippage = price * self.slippage_bps / 10000
        exit_price = price - slippage if pos.direction == TradeDirection.LONG else price + slippage
        
        # Calculate P&L
        if pos.direction == TradeDirection.LONG:
            pnl = (exit_price - pos.entry_price) * pos.size
            pnl_pct = (exit_price - pos.entry_price) / pos.entry_price * 100
        else:
            pnl = (pos.entry_price - exit_price) * pos.size
            pnl_pct = (pos.entry_price - exit_price) / pos.entry_price * 100
        
        pnl_bps = pnl_pct * 100
        
        # Calculate commission
        commission = (pos.entry_price + exit_price) * pos.size * self.commission_bps / 10000
        
        # Net P&L
        net_pnl = pnl - commission
        
        # Update position
        pos.exit_time = timestamp
        pos.exit_price = exit_price
        pos.pnl = net_pnl
        pos.pnl_pct = pnl_pct - (commission / pos.entry_price * 100)
        pos.pnl_bps = pos.pnl_pct * 100
        pos.commission = commission
        pos.status = TradeStatus.CLOSED if "Stop" not in reason else TradeStatus.STOPPED
        pos.holding_time_seconds = (timestamp - pos.entry_time).total_seconds()
        pos.exit_reason = reason
        
        # Update capital
        self.current_capital += net_pnl
        
        # Store trade
        self.trades.append(pos)
        
        # Clear position
        self.current_position = None
    
    def _calculate_equity(self, current_price: float) -> float:
        """Calculate current equity including unrealized P&L."""
        equity = self.current_capital
        
        if self.current_position:
            pos = self.current_position
            if pos.direction == TradeDirection.LONG:
                unrealized = (current_price - pos.entry_price) * pos.size
            else:
                unrealized = (pos.entry_price - current_price) * pos.size
            equity += unrealized
        
        return equity
    
    def _calculate_results(self, strategy_name: str) -> BacktestResult:
        """Calculate comprehensive backtest results."""
        result = BacktestResult(strategy_name=strategy_name)
        
        if not self.trades:
            result.initial_capital = self.initial_capital
            result.final_capital = self.current_capital
            return result
        
        # Basic metrics
        result.total_trades = len(self.trades)
        result.trades = self.trades.copy()
        result.equity_curve = self.equity_curve.copy()
        
        result.initial_capital = self.initial_capital
        result.final_capital = self.current_capital
        result.total_pnl = self.current_capital - self.initial_capital
        result.total_pnl_pct = result.total_pnl / self.initial_capital * 100
        
        # Win/Loss analysis
        winners = [t for t in self.trades if t.pnl > 0]
        losers = [t for t in self.trades if t.pnl <= 0]
        
        result.winning_trades = len(winners)
        result.losing_trades = len(losers)
        result.win_rate = len(winners) / len(self.trades) * 100 if self.trades else 0
        
        result.avg_win = np.mean([t.pnl for t in winners]) if winners else 0
        result.avg_loss = np.mean([t.pnl for t in losers]) if losers else 0
        
        # Profit factor
        gross_profit = sum(t.pnl for t in winners)
        gross_loss = abs(sum(t.pnl for t in losers))
        result.profit_factor = gross_profit / gross_loss if gross_loss > 0 else float('inf')
        
        # Expectancy
        result.expectancy = (
            (result.win_rate / 100 * result.avg_win) +
            ((1 - result.win_rate / 100) * result.avg_loss)
        )
        
        # Drawdown
        result.max_drawdown, result.max_drawdown_pct, result.drawdown_curve = \
            self._calculate_drawdown()
        
        # Sharpe Ratio (assuming risk-free = 0)
        returns = [t.pnl_pct for t in self.trades]
        if len(returns) > 1:
            avg_return = np.mean(returns)
            std_return = np.std(returns)
            result.sharpe_ratio = avg_return / std_return * np.sqrt(252) if std_return > 0 else 0
            
            # Sortino (downside deviation)
            negative_returns = [r for r in returns if r < 0]
            downside_std = np.std(negative_returns) if negative_returns else 1
            result.sortino_ratio = avg_return / downside_std * np.sqrt(252) if downside_std > 0 else 0
        
        # Calmar Ratio
        if result.max_drawdown_pct > 0:
            annualized_return = result.total_pnl_pct  # Simplified
            result.calmar_ratio = annualized_return / result.max_drawdown_pct
        
        # Timing metrics
        holding_times = [t.holding_time_seconds for t in self.trades]
        result.avg_holding_time = np.mean(holding_times) if holding_times else 0
        result.max_holding_time = max(holding_times) if holding_times else 0
        
        # Time range
        result.start_time = self.trades[0].entry_time
        result.end_time = self.trades[-1].exit_time
        
        return result
    
    def _calculate_drawdown(self) -> Tuple[float, float, List[Tuple[datetime, float]]]:
        """Calculate maximum drawdown from equity curve."""
        if not self.equity_curve:
            return 0, 0, []
        
        peak = self.initial_capital
        max_dd = 0
        max_dd_pct = 0
        drawdown_curve = []
        
        for timestamp, equity in self.equity_curve:
            if equity > peak:
                peak = equity
            
            dd = peak - equity
            dd_pct = dd / peak * 100 if peak > 0 else 0
            
            if dd > max_dd:
                max_dd = dd
                max_dd_pct = dd_pct
            
            drawdown_curve.append((timestamp, dd_pct))
        
        return max_dd, max_dd_pct, drawdown_curve
    
    def generate_synthetic_data(self, 
                                 minutes: int = 60,
                                 base_price: float = 87500,
                                 volatility: float = 0.0002) -> List[Dict]:
        """
        Generate synthetic price data for backtesting.
        
        Args:
            minutes: Duration in minutes
            base_price: Starting price
            volatility: Price volatility (as fraction)
        """
        data = []
        price = base_price
        start_time = datetime.utcnow() - timedelta(minutes=minutes)
        
        for i in range(minutes * 60):  # 1-second intervals
            timestamp = start_time + timedelta(seconds=i)
            
            # Random walk with drift
            change = np.random.normal(0, volatility * price)
            price = max(price + change, price * 0.9)  # Floor at 90%
            
            # Generate features
            imbalance = np.random.uniform(-0.8, 0.8)
            velocity = np.random.uniform(5, 60)
            spread_bps = np.random.uniform(1, 8)
            volatility_bps = np.random.uniform(8, 30)
            price_vs_vwap = np.random.uniform(-0.2, 0.2)
            
            data.append({
                "timestamp": timestamp,
                "price": price,
                "imbalance": imbalance,
                "velocity": velocity,
                "velocity_baseline": 20,
                "spread_bps": spread_bps,
                "volatility_bps": volatility_bps,
                "price_vs_vwap": price_vs_vwap
            })
        
        return data
    
    def compare_strategies(self, price_data: List[Dict]) -> Dict[str, BacktestResult]:
        """
        Compare all strategies against the same data.
        
        Returns:
            Dict mapping strategy ID to BacktestResult
        """
        results = {}
        
        for rule_id in self.rules.keys():
            result = self.run_backtest(price_data, strategy_id=rule_id)
            results[rule_id] = result
        
        return results
    
    def get_strategies_summary(self) -> List[Dict]:
        """Get summary of all strategies."""
        return [
            {
                "id": rule.id,
                "name": rule.name,
                "direction": rule.direction.value,
                "stop_loss": f"{rule.stop_loss_pct}%",
                "take_profit": f"{rule.take_profit_pct}%",
                "enabled": rule.enabled
            }
            for rule in self.rules.values()
        ]
