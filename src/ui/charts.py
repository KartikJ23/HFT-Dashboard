"""
HFT Live Dashboard - Professional Charts Module
=================================================

Premium Plotly chart creation with professional trading aesthetics.
Features gradient fills, smooth animations, and professional annotations.

Charts:
1. Live Price + VWAP Crossover (Dual line with gradient fill)
2. Bid-Ask Spread Heatmap Timeline (Gradient bar chart)
3. Order Book Imbalance Indicator (Gauge-style bar)
4. Trade Velocity Gauge (Premium speedometer)
5. Rolling Volatility Monitor (Area chart with bands)
"""

import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import numpy as np

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COLORS, CHART_CONFIG
from ui.theme import Theme


class Charts:
    """
    Creates premium dashboard charts using Plotly Graph Objects.
    
    Each method returns a Plotly Figure ready for display.
    """
    
    # ==========================================================================
    # CHART 1: LIVE PRICE + VWAP CROSSOVER (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_price_vwap_chart(price_data: List[Dict], 
                                 height: int = 300,
                                 line_shape: str = "spline") -> go.Figure:
        """
        Create premium dual line chart showing price and VWAP overlay.
        Features gradient fill and crossover markers.
        
        Args:
            price_data: List of price data dictionaries
            height: Chart height in pixels
            line_shape: Line interpolation style ('spline', 'linear', 'hv')
        """
        fig = go.Figure()
        
        if not price_data:
            # Show animated loading state
            fig.add_annotation(
                text="📡 Connecting to market feed...",
                xref="paper", yref="paper",
                x=0.5, y=0.55,
                showarrow=False,
                font=dict(size=18, color="#f59e0b", family="Inter")
            )
            fig.add_annotation(
                text="Live data will appear shortly",
                xref="paper", yref="paper",
                x=0.5, y=0.42,
                showarrow=False,
                font=dict(size=12, color=Theme.TEXT_MUTED, family="Inter")
            )
            # Add a pulsing circle effect
            fig.add_shape(
                type="circle",
                xref="paper", yref="paper",
                x0=0.45, y0=0.65, x1=0.55, y1=0.75,
                fillcolor="rgba(245, 158, 11, 0.2)",
                line=dict(color="#f59e0b", width=2)
            )
        else:
            timestamps = [d["timestamp"] for d in price_data]
            prices = [d["price"] for d in price_data]
            vwaps = [d["vwap"] for d in price_data]
            
            # Price line with gradient fill - GOLD color
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=prices,
                mode="lines",
                name="💰 Price",
                line=dict(color="#fbbf24", width=3, shape=line_shape),
                fill="tonexty",
                fillcolor="rgba(251, 191, 36, 0.1)",
                hovertemplate="<b>Price</b>: $%{y:,.2f}<extra></extra>"
            ))
            
            # VWAP line - PURPLE color
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=vwaps,
                mode="lines",
                name="📐 VWAP",
                line=dict(color="#a78bfa", width=2.5, dash="dot", shape=line_shape),
                hovertemplate="<b>VWAP</b>: $%{y:,.2f}<extra></extra>"
            ))
            
            # Crossover markers
            crossovers_x = []
            crossovers_y = []
            crossover_colors = []
            crossover_labels = []
            
            for i in range(1, len(prices)):
                prev_diff = prices[i-1] - vwaps[i-1]
                curr_diff = prices[i] - vwaps[i]
                
                if prev_diff * curr_diff < 0:
                    crossovers_x.append(timestamps[i])
                    crossovers_y.append(prices[i])
                    if curr_diff > 0:
                        crossover_colors.append(Theme.GREEN)
                        crossover_labels.append("Bullish Cross")
                    else:
                        crossover_colors.append(Theme.RED)
                        crossover_labels.append("Bearish Cross")
            
            if crossovers_x:
                fig.add_trace(go.Scatter(
                    x=crossovers_x,
                    y=crossovers_y,
                    mode="markers",
                    name="Crossover",
                    marker=dict(
                        size=12,
                        color=crossover_colors,
                        symbol="diamond",
                        line=dict(width=2, color="white")
                    ),
                    text=crossover_labels,
                    hovertemplate="<b>%{text}</b><br>Price: $%{y:,.2f}<extra></extra>"
                ))
            
            # Add price annotations
            if prices:
                last_price = prices[-1]
                first_price = prices[0]
                change = ((last_price - first_price) / first_price) * 100 if first_price else 0
                
                fig.add_annotation(
                    x=timestamps[-1],
                    y=last_price,
                    text=f"${last_price:,.2f}",
                    showarrow=True,
                    arrowhead=0,
                    arrowcolor=Theme.CYAN,
                    ax=40,
                    ay=0,
                    font=dict(color=Theme.CYAN, size=12, family="JetBrains Mono"),
                    bgcolor="rgba(20, 25, 35, 0.9)",
                    borderpad=4,
                    bordercolor=Theme.CYAN
                )
        
        # Apply premium layout
        layout = Theme.get_base_layout("Live Price & VWAP Crossover", height)
        layout["yaxis"]["tickprefix"] = "$"
        layout["yaxis"]["tickformat"] = ",.0f"
        layout["xaxis"]["title"] = ""
        layout["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=Theme.TEXT_SECONDARY, size=11, family="Inter"),
            bgcolor="rgba(0,0,0,0)"
        )
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 2: BID-ASK SPREAD HEATMAP (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_spread_heatmap(spread_data: List[Dict], 
                               height: int = 300) -> go.Figure:
        """
        Create premium horizontal bar chart with gradient colors for spread.
        """
        fig = go.Figure()
        
        if not spread_data:
            fig.add_annotation(
                text="📊 Collecting spread data...",
                xref="paper", yref="paper",
                x=0.5, y=0.55,
                showarrow=False,
                font=dict(size=18, color="#8b5cf6", family="Inter")
            )
            fig.add_annotation(
                text="Bars will populate in a few seconds",
                xref="paper", yref="paper",
                x=0.5, y=0.42,
                showarrow=False,
                font=dict(size=12, color=Theme.TEXT_MUTED, family="Inter")
            )
            max_spread = 10
        else:
            # Use gradient colors based on spread value
            colors = []
            for d in spread_data:
                s = d["spread_bps"]
                if s < 3:
                    colors.append("#10b981")  # Green
                elif s < 4:
                    colors.append("#14b8a6")  # Teal
                elif s < 5:
                    colors.append("#06b6d4")  # Cyan
                elif s < 6:
                    colors.append("#f59e0b")  # Amber
                elif s < 8:
                    colors.append("#f97316")  # Orange
                else:
                    colors.append("#ef4444")  # Red
            
            spreads = [d["spread_bps"] for d in spread_data]
            times = [d["timestamp"].strftime("%H:%M:%S") for d in spread_data]
            max_spread = max(spreads) if spreads else 10
            
            # Create gradient-colored bars
            fig.add_trace(go.Bar(
                y=times,
                x=spreads,
                orientation="h",
                marker=dict(
                    color=colors,
                    line=dict(width=1, color="rgba(255,255,255,0.1)"),
                    opacity=0.95
                ),
                text=[f"{s:.2f}" for s in spreads],
                textposition="outside",
                textfont=dict(color=Theme.TEXT_SECONDARY, size=10, family="JetBrains Mono"),
                hovertemplate="<b>Spread</b>: %{x:.2f} bps<br><b>Time</b>: %{y}<extra></extra>"
            ))
            
            # Threshold zones with distinct colors
            fig.add_vrect(x0=0, x1=3, fillcolor="#10b981", opacity=0.08, line_width=0)
            fig.add_vrect(x0=3, x1=6, fillcolor="#f59e0b", opacity=0.08, line_width=0)
            fig.add_vrect(x0=6, x1=max(10, max_spread * 1.2), fillcolor="#ef4444", opacity=0.08, line_width=0)
            
            # Threshold lines
            fig.add_vline(x=3, line_dash="dash", line_color=Theme.YELLOW, line_width=1, opacity=0.7)
            fig.add_vline(x=6, line_dash="dash", line_color=Theme.RED, line_width=1, opacity=0.7)
        
        # Apply layout
        layout = Theme.get_base_layout("Bid-Ask Spread Timeline", height)
        layout["xaxis"]["title"] = dict(text="Spread (bps)", font=dict(size=11, color=Theme.TEXT_MUTED))
        layout["xaxis"]["range"] = [0, max(10, max_spread * 1.2) if spread_data else 10]
        layout["yaxis"]["title"] = ""
        layout["showlegend"] = False
        layout["bargap"] = 0.3
        
        # Zone labels
        layout["annotations"] = [
            dict(x=1.5, y=1.08, xref="x", yref="paper", text="Optimal", showarrow=False, 
                 font=dict(color=Theme.GREEN, size=10, family="Inter")),
            dict(x=4.5, y=1.08, xref="x", yref="paper", text="Normal", showarrow=False, 
                 font=dict(color=Theme.YELLOW, size=10, family="Inter")),
            dict(x=8, y=1.08, xref="x", yref="paper", text="Wide", showarrow=False, 
                 font=dict(color=Theme.RED, size=10, family="Inter")),
        ]
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 3: ORDER BOOK IMBALANCE (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_imbalance_chart(imbalance: float, 
                                bid_volume: float,
                                ask_volume: float,
                                height: int = 250) -> go.Figure:
        """
        Create premium order book imbalance visualization with vibrant colors.
        """
        fig = go.Figure()
        
        imbalance_pct = imbalance * 100
        
        # Background gradient zones with distinct colors
        fig.add_vrect(x0=-100, x1=-50, fillcolor="#ef4444", opacity=0.12, line_width=0)
        fig.add_vrect(x0=-50, x1=0, fillcolor="#f97316", opacity=0.08, line_width=0)
        fig.add_vrect(x0=0, x1=50, fillcolor="#22c55e", opacity=0.08, line_width=0)
        fig.add_vrect(x0=50, x1=100, fillcolor="#10b981", opacity=0.12, line_width=0)
        
        # Main imbalance bar with enhanced color
        if imbalance > 0.3:
            bar_color = "#10b981"  # Strong green
        elif imbalance > 0:
            bar_color = "#22c55e"  # Light green
        elif imbalance > -0.3:
            bar_color = "#f97316"  # Orange
        else:
            bar_color = "#ef4444"  # Red
        
        fig.add_trace(go.Bar(
            y=["⚖️ Imbalance"],
            x=[imbalance_pct],
            orientation="h",
            marker=dict(
                color=bar_color,
                line=dict(width=2, color="rgba(255,255,255,0.2)"),
                opacity=0.95
            ),
            text=f"{abs(imbalance_pct):.1f}%",
            textposition="outside",
            textfont=dict(color=bar_color, size=18, family="JetBrains Mono"),
            hovertemplate=f"<b>Imbalance</b>: {imbalance_pct:+.1f}%<extra></extra>"
        ))
        
        # Center line with glow effect
        fig.add_vline(x=0, line_color="rgba(255,255,255,0.5)", line_width=3)
        
        # Volume indicators
        total_vol = bid_volume + ask_volume
        bid_pct = (bid_volume / total_vol * 100) if total_vol > 0 else 50
        ask_pct = (ask_volume / total_vol * 100) if total_vol > 0 else 50
        
        # Apply layout
        layout = Theme.get_base_layout("", height)
        layout["xaxis"]["range"] = [-100, 100]
        layout["xaxis"]["ticksuffix"] = "%"
        layout["xaxis"]["title"] = ""
        layout["xaxis"]["tickvals"] = [-100, -50, 0, 50, 100]
        layout["yaxis"]["visible"] = False
        layout["showlegend"] = False
        
        # Side labels and volume info with enhanced colors
        layout["annotations"] = [
            dict(
                x=-50, y=1.3, xref="x", yref="paper",
                text="🔴 SELL PRESSURE",
                showarrow=False,
                font=dict(color="#ef4444", size=13, family="Inter")
            ),
            dict(
                x=50, y=1.3, xref="x", yref="paper",
                text="🟢 BUY PRESSURE",
                showarrow=False,
                font=dict(color="#10b981", size=13, family="Inter")
            ),
            dict(
                x=-75, y=-0.35, xref="x", yref="paper",
                text=f"Ask: {ask_volume:.3f} ({ask_pct:.1f}%)",
                showarrow=False,
                font=dict(color=Theme.RED, size=11, family="JetBrains Mono")
            ),
            dict(
                x=80, y=-0.3, xref="x", yref="paper",
                text=f"Bid: {bid_volume:.3f} ({bid_pct:.1f}%)",
                showarrow=False,
                font=dict(color=Theme.GREEN, size=11, family="JetBrains Mono")
            ),
        ]
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 4: TRADE VELOCITY GAUGE (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_velocity_gauge(velocity: float,
                               baseline: float,
                               height: int = 250) -> go.Figure:
        """
        Create premium speedometer gauge for trade velocity with vibrant colors.
        """
        max_range = max(100, velocity * 1.5, baseline * 3)
        
        # Determine status color with vibrant palette
        ratio = velocity / baseline if baseline > 0 else 1
        if ratio > 2:
            needle_color = "#ef4444"  # Red
            status = "🔴 VELOCITY SPIKE"
            status_color = "#ef4444"
        elif ratio > 1.5:
            needle_color = "#f97316"  # Orange
            status = "🟠 ELEVATED"
            status_color = "#f97316"
        elif ratio > 1.2:
            needle_color = "#f59e0b"  # Amber
            status = "🟡 RISING"
            status_color = "#f59e0b"
        else:
            needle_color = "#10b981"  # Green
            status = "🟢 NORMAL"
            status_color = "#10b981"
        
        fig = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=velocity,
            delta={
                "reference": baseline,
                "valueformat": ".1f",
                "prefix": "vs base: ",
                "increasing": {"color": "#ef4444"},
                "decreasing": {"color": "#10b981"},
                "font": {"size": 13, "family": "Inter"}
            },
            number={
                "suffix": " /sec",
                "font": {"size": 32, "color": needle_color, "family": "JetBrains Mono"}
            },
            title={
                "text": f"<b>Trade Velocity</b><br><span style='font-size:12px;color:{status_color}'>{status}</span>",
                "font": {"size": 15, "color": Theme.TEXT_PRIMARY, "family": "Inter"}
            },
            gauge={
                "axis": {
                    "range": [0, max_range],
                    "tickcolor": Theme.TEXT_MUTED,
                    "tickfont": {"color": Theme.TEXT_SECONDARY, "size": 11},
                    "tickwidth": 2
                },
                "bar": {"color": needle_color, "thickness": 0.35},
                "bgcolor": "rgba(20, 25, 35, 0.9)",
                "bordercolor": "rgba(255,255,255,0.1)",
                "borderwidth": 2,
                "steps": [
                    {"range": [0, 30], "color": "rgba(16, 185, 129, 0.25)"},
                    {"range": [30, 50], "color": "rgba(245, 158, 11, 0.2)"},
                    {"range": [50, 70], "color": "rgba(249, 115, 22, 0.2)"},
                    {"range": [70, max_range], "color": "rgba(239, 68, 68, 0.2)"},
                ],
                "threshold": {
                    "line": {"color": "#06b6d4", "width": 4},
                    "thickness": 0.85,
                    "value": baseline
                }
            }
        ))
        
        layout = Theme.get_gauge_layout("")
        layout["height"] = height
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 5: ROLLING VOLATILITY MONITOR (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_volatility_chart(volatility_data: List[Dict],
                                 height: int = 300,
                                 line_shape: str = "spline") -> go.Figure:
        """
        Create premium area chart with threshold bands for volatility.
        
        Args:
            volatility_data: List of volatility data dictionaries
            height: Chart height in pixels
            line_shape: Line interpolation style ('spline', 'linear', 'hv')
        """
        fig = go.Figure()
        
        y_max = 30
        
        if not volatility_data:
            fig.add_annotation(
                text="📉 Calculating volatility...",
                xref="paper", yref="paper",
                x=0.5, y=0.55,
                showarrow=False,
                font=dict(size=18, color="#ec4899", family="Inter")
            )
            fig.add_annotation(
                text="Analyzing price movements",
                xref="paper", yref="paper",
                x=0.5, y=0.42,
                showarrow=False,
                font=dict(size=12, color=Theme.TEXT_MUTED, family="Inter")
            )
        else:
            timestamps = [d["timestamp"] for d in volatility_data]
            volatilities = [d["volatility_bps"] for d in volatility_data]
            
            max_vol = max(volatilities) if volatilities else 30
            y_max = max(30, max_vol * 1.2)
            
            # Threshold zones with distinct vibrant colors
            fig.add_hrect(y0=0, y1=15, fillcolor="#10b981", opacity=0.12, line_width=0)
            fig.add_hrect(y0=15, y1=20, fillcolor="#f59e0b", opacity=0.12, line_width=0)
            fig.add_hrect(y0=20, y1=y_max, fillcolor="#ef4444", opacity=0.12, line_width=0)
            
            # Threshold lines with labels
            fig.add_hline(y=15, line_dash="dash", line_color="#f59e0b", line_width=2, opacity=0.8)
            fig.add_hline(y=20, line_dash="dash", line_color="#ef4444", line_width=2, opacity=0.8)
            
            # Get current volatility color
            current_vol = volatilities[-1] if volatilities else 0
            if current_vol < 15:
                vol_color = "#10b981"  # Green
            elif current_vol < 20:
                vol_color = "#f59e0b"  # Amber
            else:
                vol_color = "#ef4444"  # Red
            
            # Main volatility area with gradient
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=volatilities,
                mode="lines",
                fill="tozeroy",
                name="📉 Volatility",
                line=dict(color=vol_color, width=3, shape=line_shape),
                fillcolor=f"rgba({int(vol_color[1:3], 16)}, {int(vol_color[3:5], 16)}, {int(vol_color[5:7], 16)}, 0.35)",
                hovertemplate="<b>Volatility</b>: %{y:.2f} bps<extra></extra>"
            ))
            
            # Current value annotation with enhanced styling
            if volatilities:
                if current_vol < 15:
                    status = "🟢 LOW"
                elif current_vol < 20:
                    status = "🟡 MODERATE"
                else:
                    status = "🔴 HIGH"
                    
                fig.add_annotation(
                    x=timestamps[-1],
                    y=current_vol,
                    text=f"<b>{current_vol:.1f}</b> bps • {status}",
                    showarrow=True,
                    arrowhead=2,
                    arrowcolor=vol_color,
                    ax=60,
                    ay=-25,
                    font=dict(color=vol_color, size=12, family="Inter"),
                    bgcolor="rgba(20, 25, 35, 0.95)",
                    borderpad=6,
                    bordercolor=vol_color,
                    borderwidth=2
                )
        
        # Apply layout
        layout = Theme.get_base_layout("Rolling Volatility (60s Window)", height)
        layout["yaxis"]["title"] = dict(text="Volatility (bps)", font=dict(size=11, color=Theme.TEXT_MUTED))
        layout["yaxis"]["range"] = [0, y_max]
        layout["xaxis"]["title"] = ""
        layout["showlegend"] = False
        
        # Zone labels on right
        layout["annotations"] = layout.get("annotations", []) + [
            dict(x=1.02, y=7.5, xref="paper", yref="y", text="LOW", showarrow=False,
                 font=dict(color=Theme.GREEN, size=10, family="Inter", weight="bold")),
            dict(x=1.02, y=17.5, xref="paper", yref="y", text="MOD", showarrow=False,
                 font=dict(color=Theme.YELLOW, size=10, family="Inter", weight="bold")),
        ]
        
        if y_max > 22:
            layout["annotations"].append(
                dict(x=1.02, y=min(25, y_max - 3), xref="paper", yref="y", text="HIGH", showarrow=False,
                     font=dict(color=Theme.RED, size=10, family="Inter", weight="bold"))
            )
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # MINI SPARKLINE CHARTS
    # ==========================================================================
    
    @staticmethod
    def create_mini_sparkline(values: List[float], 
                               color: str = None,
                               height: int = 50) -> go.Figure:
        """Create mini sparkline chart for inline metrics."""
        fig = go.Figure()
        
        if values and len(values) > 1:
            trend_color = color or (Theme.GREEN if values[-1] >= values[0] else Theme.RED)
            
            fig.add_trace(go.Scatter(
                y=values,
                mode="lines",
                line=dict(color=trend_color, width=1.5, shape="spline"),
                fill="tozeroy",
                fillcolor=f"rgba({int(trend_color[1:3], 16)}, {int(trend_color[3:5], 16)}, {int(trend_color[5:7], 16)}, 0.2)",
                hoverinfo="skip"
            ))
        
        fig.update_layout(
            height=height,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(visible=False),
            yaxis=dict(visible=False),
            showlegend=False
        )
        
        return fig
    
    # ==========================================================================
    # CHART 6: CANDLESTICK CHART (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_candlestick_chart(candle_data: List[Dict],
                                  height: int = 400,
                                  show_volume: bool = True) -> go.Figure:
        """
        Create premium OHLC candlestick chart with volume bars.
        
        Args:
            candle_data: List of dicts with open, high, low, close, volume, timestamp
            height: Chart height in pixels
            show_volume: Whether to show volume subplot
        """
        if show_volume:
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.03,
                row_heights=[0.75, 0.25]
            )
        else:
            fig = go.Figure()
        
        if not candle_data:
            fig.add_annotation(
                text="🕯️ Building candlesticks...",
                xref="paper", yref="paper",
                x=0.5, y=0.55,
                showarrow=False,
                font=dict(size=18, color="#fbbf24", family="Inter")
            )
            fig.add_annotation(
                text="Aggregating trade data into OHLC candles",
                xref="paper", yref="paper",
                x=0.5, y=0.42,
                showarrow=False,
                font=dict(size=12, color=Theme.TEXT_MUTED, family="Inter")
            )
        else:
            timestamps = [d["timestamp"] for d in candle_data]
            opens = [d["open"] for d in candle_data]
            highs = [d["high"] for d in candle_data]
            lows = [d["low"] for d in candle_data]
            closes = [d["close"] for d in candle_data]
            volumes = [d.get("volume", 0) for d in candle_data]
            
            # Determine colors for each candle
            colors = ["#10b981" if c >= o else "#ef4444" 
                      for o, c in zip(opens, closes)]
            
            # Candlestick trace
            candlestick = go.Candlestick(
                x=timestamps,
                open=opens,
                high=highs,
                low=lows,
                close=closes,
                increasing=dict(
                    line=dict(color="#10b981", width=1),
                    fillcolor="#10b981"
                ),
                decreasing=dict(
                    line=dict(color="#ef4444", width=1),
                    fillcolor="#ef4444"
                ),
                name="OHLC",
                hoverinfo="all"
            )
            
            if show_volume:
                fig.add_trace(candlestick, row=1, col=1)
                
                # Volume bars
                fig.add_trace(go.Bar(
                    x=timestamps,
                    y=volumes,
                    marker=dict(
                        color=colors,
                        opacity=0.6,
                        line=dict(width=0)
                    ),
                    name="Volume",
                    hovertemplate="<b>Volume</b>: %{y:.4f} BTC<extra></extra>"
                ), row=2, col=1)
            else:
                fig.add_trace(candlestick)
            
            # Add moving averages
            if len(closes) >= 10:
                ma10 = [np.mean(closes[max(0, i-9):i+1]) for i in range(len(closes))]
                fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=ma10,
                    mode="lines",
                    name="MA(10)",
                    line=dict(color="#8b5cf6", width=1.5, dash="dot"),
                    hovertemplate="<b>MA(10)</b>: $%{y:,.2f}<extra></extra>"
                ), row=1, col=1) if show_volume else fig.add_trace(go.Scatter(
                    x=timestamps,
                    y=ma10,
                    mode="lines",
                    name="MA(10)",
                    line=dict(color="#8b5cf6", width=1.5, dash="dot"),
                    hovertemplate="<b>MA(10)</b>: $%{y:,.2f}<extra></extra>"
                ))
            
            # Current price annotation
            if closes:
                last_price = closes[-1]
                last_open = opens[-1]
                change_pct = (last_price - last_open) / last_open * 100 if last_open else 0
                arrow_color = "#10b981" if change_pct >= 0 else "#ef4444"
                
                fig.add_annotation(
                    x=timestamps[-1],
                    y=last_price,
                    text=f"${last_price:,.2f}",
                    showarrow=True,
                    arrowhead=0,
                    arrowcolor=arrow_color,
                    ax=50,
                    ay=0,
                    font=dict(color=arrow_color, size=11, family="JetBrains Mono"),
                    bgcolor="rgba(20, 25, 35, 0.95)",
                    borderpad=4,
                    bordercolor=arrow_color
                )
        
        # Layout
        layout = Theme.get_base_layout("Live Candlestick Chart (5s candles)", height)
        layout["xaxis"]["rangeslider"] = dict(visible=False)
        layout["yaxis"]["tickprefix"] = "$"
        layout["yaxis"]["tickformat"] = ",.0f"
        layout["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=Theme.TEXT_SECONDARY, size=10, family="Inter"),
            bgcolor="rgba(0,0,0,0)"
        )
        
        if show_volume:
            layout["yaxis2"] = dict(
                title=dict(text="Vol", font=dict(size=10, color=Theme.TEXT_MUTED)),
                tickfont=dict(size=9, color=Theme.TEXT_SECONDARY),
                gridcolor="rgba(255,255,255,0.05)",
                showgrid=True
            )
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 7: ORDER BOOK DEPTH CHART (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_depth_chart(bids: List[Dict], asks: List[Dict],
                           height: int = 350) -> go.Figure:
        """
        Create premium order book depth visualization.
        Shows cumulative bid/ask volume at each price level.
        
        Args:
            bids: List of dicts with price, quantity (sorted high to low)
            asks: List of dicts with price, quantity (sorted low to high)
            height: Chart height in pixels
        """
        fig = go.Figure()
        
        if not bids and not asks:
            fig.add_annotation(
                text="📊 Loading order book depth...",
                xref="paper", yref="paper",
                x=0.5, y=0.55,
                showarrow=False,
                font=dict(size=18, color="#06b6d4", family="Inter")
            )
            fig.add_annotation(
                text="Awaiting order book data",
                xref="paper", yref="paper",
                x=0.5, y=0.42,
                showarrow=False,
                font=dict(size=12, color=Theme.TEXT_MUTED, family="Inter")
            )
        else:
            # Calculate cumulative volumes
            bid_prices = [b["price"] for b in bids]
            bid_volumes = [b["quantity"] for b in bids]
            cumulative_bid = np.cumsum(bid_volumes).tolist()
            
            ask_prices = [a["price"] for a in asks]
            ask_volumes = [a["quantity"] for a in asks]
            cumulative_ask = np.cumsum(ask_volumes).tolist()
            
            # Get mid price for center line
            mid_price = (bid_prices[0] + ask_prices[0]) / 2 if bid_prices and ask_prices else 0
            
            # Bid depth (green area)
            fig.add_trace(go.Scatter(
                x=bid_prices,
                y=cumulative_bid,
                mode="lines",
                name="🟢 Bids",
                line=dict(color="#10b981", width=2),
                fill="tozeroy",
                fillcolor="rgba(16, 185, 129, 0.3)",
                hovertemplate="<b>Bid Price</b>: $%{x:,.2f}<br><b>Cumulative</b>: %{y:.4f} BTC<extra></extra>"
            ))
            
            # Ask depth (red area)
            fig.add_trace(go.Scatter(
                x=ask_prices,
                y=cumulative_ask,
                mode="lines",
                name="🔴 Asks",
                line=dict(color="#ef4444", width=2),
                fill="tozeroy",
                fillcolor="rgba(239, 68, 68, 0.3)",
                hovertemplate="<b>Ask Price</b>: $%{x:,.2f}<br><b>Cumulative</b>: %{y:.4f} BTC<extra></extra>"
            ))
            
            # Mid price line
            if mid_price:
                fig.add_vline(
                    x=mid_price,
                    line_dash="dash",
                    line_color="#fbbf24",
                    line_width=2,
                    annotation_text=f"Mid: ${mid_price:,.2f}",
                    annotation_position="top",
                    annotation_font=dict(color="#fbbf24", size=11, family="JetBrains Mono")
                )
            
            # Wall detection (large cumulative jumps)
            max_bid_vol = max(cumulative_bid) if cumulative_bid else 0
            max_ask_vol = max(cumulative_ask) if cumulative_ask else 0
            
            # Annotate significant walls
            for i, (price, vol) in enumerate(zip(bid_prices, bid_volumes)):
                if vol > max_bid_vol * 0.3:  # Large single order
                    fig.add_annotation(
                        x=price,
                        y=cumulative_bid[i],
                        text=f"🛡️ Wall",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#10b981",
                        ax=-30,
                        ay=-20,
                        font=dict(color="#10b981", size=9, family="Inter"),
                        bgcolor="rgba(20, 25, 35, 0.9)",
                        borderpad=3
                    )
                    break  # Only show first wall
            
            for i, (price, vol) in enumerate(zip(ask_prices, ask_volumes)):
                if vol > max_ask_vol * 0.3:
                    fig.add_annotation(
                        x=price,
                        y=cumulative_ask[i],
                        text=f"🧱 Wall",
                        showarrow=True,
                        arrowhead=2,
                        arrowcolor="#ef4444",
                        ax=30,
                        ay=-20,
                        font=dict(color="#ef4444", size=9, family="Inter"),
                        bgcolor="rgba(20, 25, 35, 0.9)",
                        borderpad=3
                    )
                    break
        
        # Layout
        layout = Theme.get_base_layout("Order Book Depth", height)
        layout["xaxis"]["title"] = dict(text="Price (USD)", font=dict(size=11, color=Theme.TEXT_MUTED))
        layout["xaxis"]["tickprefix"] = "$"
        layout["xaxis"]["tickformat"] = ",.0f"
        layout["yaxis"]["title"] = dict(text="Cumulative Volume (BTC)", font=dict(size=11, color=Theme.TEXT_MUTED))
        layout["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            font=dict(color=Theme.TEXT_SECONDARY, size=11, family="Inter"),
            bgcolor="rgba(0,0,0,0)"
        )
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 8: ML PREDICTION GAUGE (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_prediction_gauge(direction: str, confidence: float,
                                 momentum: float, height: int = 200) -> go.Figure:
        """
        Create ML prediction visualization with direction and confidence.
        
        Args:
            direction: 'up', 'down', or 'neutral'
            confidence: 0-100 confidence percentage
            momentum: -100 to +100 momentum score
            height: Chart height
        """
        fig = go.Figure()
        
        # Determine colors based on direction
        if "up" in direction.lower():
            main_color = "#10b981"
            direction_text = "📈 BULLISH"
        elif "down" in direction.lower():
            main_color = "#ef4444"
            direction_text = "📉 BEARISH"
        else:
            main_color = "#6b7280"
            direction_text = "➡️ NEUTRAL"
        
        # Create gauge for confidence
        fig.add_trace(go.Indicator(
            mode="gauge+number",
            value=confidence,
            number={
                "suffix": "%",
                "font": {"size": 36, "color": main_color, "family": "JetBrains Mono"}
            },
            title={
                "text": f"<b>{direction_text}</b><br><span style='font-size:12px;color:#a0aec0'>Model Confidence</span>",
                "font": {"size": 14, "color": Theme.TEXT_PRIMARY, "family": "Inter"}
            },
            gauge={
                "axis": {
                    "range": [0, 100],
                    "tickcolor": Theme.TEXT_MUTED,
                    "tickfont": {"color": Theme.TEXT_SECONDARY, "size": 10}
                },
                "bar": {"color": main_color, "thickness": 0.4},
                "bgcolor": "rgba(20, 25, 35, 0.9)",
                "bordercolor": "rgba(255,255,255,0.1)",
                "borderwidth": 2,
                "steps": [
                    {"range": [0, 40], "color": "rgba(107, 114, 128, 0.2)"},
                    {"range": [40, 60], "color": "rgba(245, 158, 11, 0.15)"},
                    {"range": [60, 80], "color": "rgba(16, 185, 129, 0.15)"},
                    {"range": [80, 100], "color": "rgba(16, 185, 129, 0.25)"}
                ],
                "threshold": {
                    "line": {"color": "#fbbf24", "width": 3},
                    "thickness": 0.8,
                    "value": 70  # Good confidence threshold
                }
            }
        ))
        
        layout = Theme.get_gauge_layout("")
        layout["height"] = height
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 9: MOMENTUM BAR (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_momentum_bar(momentum: float, height: int = 120) -> go.Figure:
        """
        Create horizontal momentum bar (-100 to +100).
        
        Args:
            momentum: -100 to +100 momentum score
            height: Chart height
        """
        fig = go.Figure()
        
        # Clamp momentum
        momentum = max(-100, min(100, momentum))
        
        # Determine color
        if momentum > 30:
            bar_color = "#10b981"
        elif momentum > 10:
            bar_color = "#22c55e"
        elif momentum < -30:
            bar_color = "#ef4444"
        elif momentum < -10:
            bar_color = "#f97316"
        else:
            bar_color = "#6b7280"
        
        # Background zones
        fig.add_vrect(x0=-100, x1=-30, fillcolor="#ef4444", opacity=0.1, line_width=0)
        fig.add_vrect(x0=-30, x1=0, fillcolor="#f97316", opacity=0.08, line_width=0)
        fig.add_vrect(x0=0, x1=30, fillcolor="#22c55e", opacity=0.08, line_width=0)
        fig.add_vrect(x0=30, x1=100, fillcolor="#10b981", opacity=0.1, line_width=0)
        
        # Momentum bar
        fig.add_trace(go.Bar(
            y=["Momentum"],
            x=[momentum],
            orientation="h",
            marker=dict(
                color=bar_color,
                line=dict(width=2, color="rgba(255,255,255,0.3)"),
                opacity=0.95
            ),
            text=f"{momentum:+.0f}",
            textposition="outside",
            textfont=dict(color=bar_color, size=20, family="JetBrains Mono"),
            hovertemplate=f"<b>Momentum</b>: {momentum:+.1f}<extra></extra>"
        ))
        
        # Center line
        fig.add_vline(x=0, line_color="rgba(255,255,255,0.5)", line_width=2)
        
        # Layout
        layout = Theme.get_base_layout("", height)
        layout["xaxis"]["range"] = [-100, 100]
        layout["xaxis"]["tickvals"] = [-100, -50, 0, 50, 100]
        layout["yaxis"]["visible"] = False
        layout["showlegend"] = False
        layout["margin"] = dict(l=20, r=20, t=30, b=20)
        
        layout["annotations"] = [
            dict(x=-65, y=1.2, xref="x", yref="paper", text="🔴 Bearish",
                 showarrow=False, font=dict(color="#ef4444", size=11, family="Inter")),
            dict(x=65, y=1.2, xref="x", yref="paper", text="🟢 Bullish",
                 showarrow=False, font=dict(color="#10b981", size=11, family="Inter")),
        ]
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 10: REGIME INDICATOR (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_regime_indicator(regime: str, confidence: float,
                                 height: int = 150) -> go.Figure:
        """
        Create market regime indicator visualization.
        
        Args:
            regime: Market regime (trending_up, trending_down, ranging, volatile, breakout)
            confidence: Regime confidence 0-100
            height: Chart height
        """
        fig = go.Figure()
        
        # Regime styling
        regime_styles = {
            "trending_up": ("📈 TRENDING UP", "#10b981", "Bullish momentum in control"),
            "trending_down": ("📉 TRENDING DOWN", "#ef4444", "Bearish momentum in control"),
            "ranging": ("↔️ RANGING", "#6b7280", "Sideways consolidation"),
            "volatile": ("⚡ VOLATILE", "#f59e0b", "High volatility regime"),
            "breakout": ("🚀 BREAKOUT", "#8b5cf6", "Potential breakout forming")
        }
        
        regime_key = regime.lower().replace(" ", "_") if regime else "ranging"
        title, color, description = regime_styles.get(
            regime_key, ("❓ UNKNOWN", "#6b7280", "Analyzing market...")
        )
        
        # Create donut gauge
        fig.add_trace(go.Pie(
            values=[confidence, 100 - confidence],
            hole=0.7,
            marker=dict(
                colors=[color, "rgba(30, 41, 59, 0.5)"],
                line=dict(color="rgba(255,255,255,0.1)", width=1)
            ),
            textinfo="none",
            hoverinfo="skip",
            rotation=90
        ))
        
        # Center text
        fig.add_annotation(
            text=f"<b>{title}</b><br><span style='font-size:24px;color:{color}'>{confidence:.0f}%</span>",
            x=0.5, y=0.5,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=13, color=Theme.TEXT_PRIMARY, family="Inter"),
            align="center"
        )
        
        # Description
        fig.add_annotation(
            text=description,
            x=0.5, y=-0.05,
            xref="paper", yref="paper",
            showarrow=False,
            font=dict(size=11, color=Theme.TEXT_MUTED, family="Inter")
        )
        
        fig.update_layout(
            height=height,
            margin=dict(l=10, r=10, t=10, b=30),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            showlegend=False
        )
        
        return fig
    
    # ==========================================================================
    # CHART 11: BACKTEST EQUITY CURVE (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_equity_curve(equity_data: List[tuple],
                            initial_capital: float = 10000,
                            height: int = 350) -> go.Figure:
        """
        Create backtest equity curve visualization.
        
        Args:
            equity_data: List of (timestamp, equity) tuples
            initial_capital: Starting capital for baseline
            height: Chart height
        """
        fig = go.Figure()
        
        if not equity_data:
            fig.add_annotation(
                text="📊 No backtest data available",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color=Theme.TEXT_MUTED, family="Inter")
            )
        else:
            timestamps = [d[0] for d in equity_data]
            equity = [d[1] for d in equity_data]
            
            # Determine overall color
            final_equity = equity[-1] if equity else initial_capital
            is_profitable = final_equity >= initial_capital
            main_color = "#10b981" if is_profitable else "#ef4444"
            
            # Equity curve
            fig.add_trace(go.Scatter(
                x=timestamps,
                y=equity,
                mode="lines",
                name="Equity",
                line=dict(color=main_color, width=2.5),
                fill="tozeroy",
                fillcolor=f"rgba({16 if is_profitable else 239}, {185 if is_profitable else 68}, {129 if is_profitable else 68}, 0.2)",
                hovertemplate="<b>Equity</b>: $%{y:,.2f}<extra></extra>"
            ))
            
            # Initial capital baseline
            fig.add_hline(
                y=initial_capital,
                line_dash="dash",
                line_color="#6b7280",
                line_width=1,
                annotation_text=f"Initial: ${initial_capital:,.0f}",
                annotation_position="right",
                annotation_font=dict(color="#6b7280", size=10)
            )
            
            # High water mark
            hwm = max(equity)
            fig.add_hline(
                y=hwm,
                line_dash="dot",
                line_color="#fbbf24",
                line_width=1,
                annotation_text=f"Peak: ${hwm:,.0f}",
                annotation_position="right",
                annotation_font=dict(color="#fbbf24", size=10)
            )
            
            # Final equity annotation
            pnl = final_equity - initial_capital
            pnl_pct = pnl / initial_capital * 100
            
            fig.add_annotation(
                x=timestamps[-1],
                y=final_equity,
                text=f"${final_equity:,.0f}<br><span style='color:{main_color}'>{pnl_pct:+.2f}%</span>",
                showarrow=True,
                arrowhead=0,
                arrowcolor=main_color,
                ax=50,
                ay=-30,
                font=dict(color=main_color, size=12, family="JetBrains Mono"),
                bgcolor="rgba(20, 25, 35, 0.95)",
                borderpad=5,
                bordercolor=main_color
            )
        
        layout = Theme.get_base_layout("Backtest Equity Curve", height)
        layout["yaxis"]["tickprefix"] = "$"
        layout["yaxis"]["tickformat"] = ",.0f"
        layout["xaxis"]["title"] = ""
        layout["showlegend"] = False
        
        fig.update_layout(**layout)
        return fig
    
    # ==========================================================================
    # CHART 12: TRADE DISTRIBUTION (PREMIUM)
    # ==========================================================================
    
    @staticmethod
    def create_trade_distribution(trades: List,
                                   height: int = 300) -> go.Figure:
        """
        Create trade P&L distribution histogram.
        
        Args:
            trades: List of Trade objects, dicts with pnl_pct, or raw P&L values
            height: Chart height
        """
        fig = go.Figure()
        
        if not trades:
            fig.add_annotation(
                text="📊 No trades to analyze",
                xref="paper", yref="paper",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=16, color=Theme.TEXT_MUTED, family="Inter")
            )
        else:
            # Handle different input formats
            pnls = []
            for t in trades:
                if isinstance(t, (int, float)):
                    # Raw numeric value
                    pnls.append(float(t))
                elif hasattr(t, 'pnl_pct'):
                    # Trade object with pnl_pct attribute
                    pnls.append(t.pnl_pct)
                elif isinstance(t, dict):
                    # Dictionary with pnl_pct key
                    pnls.append(t.get("pnl_pct", 0))
                else:
                    pnls.append(0)
            
            # Split wins and losses
            wins = [p for p in pnls if p > 0]
            losses = [p for p in pnls if p <= 0]
            
            # Wins histogram
            if wins:
                fig.add_trace(go.Histogram(
                    x=wins,
                    name="Wins",
                    marker=dict(color="#10b981", opacity=0.8),
                    nbinsx=15
                ))
            
            # Losses histogram
            if losses:
                fig.add_trace(go.Histogram(
                    x=losses,
                    name="Losses",
                    marker=dict(color="#ef4444", opacity=0.8),
                    nbinsx=15
                ))
            
            # Zero line
            fig.add_vline(x=0, line_color="white", line_width=2)
            
            # Stats annotation
            avg_win = np.mean(wins) if wins else 0
            avg_loss = np.mean(losses) if losses else 0
            win_rate = len(wins) / len(pnls) * 100 if pnls else 0
            
            fig.add_annotation(
                text=f"Win Rate: {win_rate:.1f}% | Avg Win: {avg_win:+.2f}% | Avg Loss: {avg_loss:.2f}%",
                x=0.5, y=1.08,
                xref="paper", yref="paper",
                showarrow=False,
                font=dict(size=11, color=Theme.TEXT_SECONDARY, family="Inter"),
                bgcolor="rgba(20, 25, 35, 0.8)",
                borderpad=5
            )
        
        layout = Theme.get_base_layout("Trade P&L Distribution", height)
        layout["xaxis"]["title"] = dict(text="P&L (%)", font=dict(size=11, color=Theme.TEXT_MUTED))
        layout["yaxis"]["title"] = dict(text="Count", font=dict(size=11, color=Theme.TEXT_MUTED))
        layout["barmode"] = "overlay"
        layout["legend"] = dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(color=Theme.TEXT_SECONDARY, size=10),
            bgcolor="rgba(0,0,0,0)"
        )
        
        fig.update_layout(**layout)
        return fig
