"""
HFT Dashboard - Strategy Backtester Module
============================================

Rule-based backtesting with P&L simulation and risk metrics.
"""

from .strategy_tester import StrategyBacktester, BacktestResult, TradeSignal

__all__ = ["StrategyBacktester", "BacktestResult", "TradeSignal"]
