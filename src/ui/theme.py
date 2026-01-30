"""
HFT Live Dashboard - Professional Theme Configuration
=======================================================

Premium dark theme styling for Streamlit and Plotly charts.
Glassmorphism design with professional trading dashboard aesthetics.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import COLORS, CHART_CONFIG


class Theme:
    """
    Professional Theme configuration for the HFT Dashboard.
    
    Features:
    - Glassmorphism design
    - Animated gradients
    - Professional trading aesthetics
    - Consistent color system
    """
    
    # ==========================================================================
    # COLOR CONSTANTS - PREMIUM MULTI-COLOR PALETTE
    # ==========================================================================
    
    # Base colors
    BACKGROUND = "#0a0a0f"
    CARD_BG = "rgba(20, 25, 35, 0.8)"
    CARD_BG_SOLID = "#141923"
    BORDER = "rgba(255, 255, 255, 0.1)"
    BORDER_GLOW = "rgba(168, 85, 247, 0.4)"
    
    # Text colors
    TEXT_PRIMARY = "#ffffff"
    TEXT_SECONDARY = "#a0aec0"
    TEXT_MUTED = "#718096"
    
    # Accent colors - MULTI-COLOR PALETTE
    GREEN = "#10b981"
    GREEN_LIGHT = "#34d399"
    RED = "#ef4444"
    RED_LIGHT = "#f87171"
    YELLOW = "#f59e0b"
    YELLOW_LIGHT = "#fbbf24"
    CYAN = "#06b6d4"
    CYAN_LIGHT = "#22d3ee"
    PURPLE = "#8b5cf6"
    PURPLE_LIGHT = "#a78bfa"
    BLUE = "#3b82f6"
    BLUE_LIGHT = "#60a5fa"
    PINK = "#ec4899"
    ORANGE = "#f97316"
    INDIGO = "#6366f1"
    TEAL = "#14b8a6"
    
    # Gradient colors
    GRADIENT_START = "#667eea"
    GRADIENT_END = "#764ba2"
    
    # Status colors
    STATUS_CONNECTED = GREEN
    STATUS_RECONNECTING = YELLOW
    STATUS_DISCONNECTED = RED
    
    # ==========================================================================
    # PLOTLY LAYOUT TEMPLATES
    # ==========================================================================
    
    @classmethod
    def get_base_layout(cls, title: str = "", height: int = None) -> dict:
        """Get premium Plotly layout with glassmorphism and smooth transitions."""
        return {
            "title": {
                "text": f"<b>{title}</b>" if title else "",
                "font": {
                    "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                    "size": 14,
                    "color": cls.TEXT_PRIMARY
                },
                "x": 0.02,
                "xanchor": "left",
                "y": 0.98,
                "yanchor": "top"
            },
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(20, 25, 35, 0.6)",
            "font": {
                "family": "Inter, -apple-system, BlinkMacSystemFont, sans-serif",
                "color": cls.TEXT_PRIMARY,
                "size": 11
            },
            "height": height or 300,
            "margin": dict(l=50, r=30, t=40, b=35),
            "xaxis": {
                "gridcolor": "rgba(255,255,255,0.05)",
                "tickfont": {"color": cls.TEXT_SECONDARY, "size": 10},
                "showgrid": True,
                "zeroline": False,
                "showline": True,
                "linecolor": "rgba(255,255,255,0.1)",
                "linewidth": 1
            },
            "yaxis": {
                "gridcolor": "rgba(255,255,255,0.05)",
                "tickfont": {"color": cls.TEXT_SECONDARY, "size": 10},
                "showgrid": True,
                "zeroline": False,
                "showline": True,
                "linecolor": "rgba(255,255,255,0.1)",
                "linewidth": 1
            },
            "showlegend": True,
            "legend": {
                "font": {"color": cls.TEXT_SECONDARY, "size": 10},
                "bgcolor": "rgba(0,0,0,0)",
                "borderwidth": 0
            },
            "hoverlabel": {
                "bgcolor": cls.CARD_BG_SOLID,
                "bordercolor": cls.BORDER_GLOW,
                "font": {"color": cls.TEXT_PRIMARY, "size": 11}
            },
            "transition": {
                "duration": 300,
                "easing": "cubic-in-out"
            },
            "uirevision": "constant"
        }
    
    @classmethod
    def get_gauge_layout(cls, title: str = "") -> dict:
        """Get premium Plotly layout for gauge charts with smooth transitions."""
        layout = cls.get_base_layout(title, 250)
        layout["showlegend"] = False
        layout["transition"] = {"duration": 500, "easing": "cubic-in-out"}
        return layout
    
    # ==========================================================================
    # PREMIUM CSS STYLES
    # ==========================================================================
    
    @classmethod
    def get_custom_css(cls) -> str:
        """Get premium CSS with glassmorphism and animations."""
        return """
        <style>
            /* Import premium fonts */
            @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');
            
            /* CSS Variables - PREMIUM MULTI-COLOR PALETTE */
            :root {
                --bg-primary: #0a0a0f;
                --bg-secondary: #0f1119;
                --bg-card: rgba(20, 25, 35, 0.8);
                --bg-card-hover: rgba(30, 35, 50, 0.9);
                --border-default: rgba(255, 255, 255, 0.1);
                --border-glow: rgba(168, 85, 247, 0.4);
                --text-primary: #ffffff;
                --text-secondary: #a0aec0;
                --text-muted: #718096;
                
                /* Multi-color accent palette */
                --accent-green: #10b981;
                --accent-emerald: #34d399;
                --accent-red: #ef4444;
                --accent-rose: #f43f5e;
                --accent-yellow: #f59e0b;
                --accent-amber: #fbbf24;
                --accent-cyan: #06b6d4;
                --accent-teal: #14b8a6;
                --accent-purple: #8b5cf6;
                --accent-violet: #a78bfa;
                --accent-blue: #3b82f6;
                --accent-indigo: #6366f1;
                --accent-pink: #ec4899;
                --accent-orange: #f97316;
                
                /* Gradients */
                --gradient-purple: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                --gradient-green: linear-gradient(135deg, #10b981 0%, #34d399 100%);
                --gradient-orange: linear-gradient(135deg, #f97316 0%, #fbbf24 100%);
                --gradient-pink: linear-gradient(135deg, #ec4899 0%, #f43f5e 100%);
                --gradient-blue: linear-gradient(135deg, #3b82f6 0%, #06b6d4 100%);
                --gradient-gold: linear-gradient(135deg, #f59e0b 0%, #fcd34d 100%);
            }
            
            /* Global Styles */
            .stApp {
                background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 50%, #0a0a0f 100%);
                background-attachment: fixed;
            }
            
            /* Animated background gradient */
            .stApp::before {
                content: '';
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: 
                    radial-gradient(ellipse at 20% 20%, rgba(102, 126, 234, 0.08) 0%, transparent 50%),
                    radial-gradient(ellipse at 80% 80%, rgba(118, 75, 162, 0.08) 0%, transparent 50%),
                    radial-gradient(ellipse at 50% 50%, rgba(78, 205, 196, 0.05) 0%, transparent 70%);
                pointer-events: none;
                z-index: -1;
            }
            
            /* Remove default Streamlit padding */
            .block-container {
                padding: 1rem 2rem 2rem 2rem !important;
                max-width: 100% !important;
            }
            
            /* Hide Streamlit branding */
            #MainMenu, footer, header {
                visibility: hidden;
            }
            
            /* Scrollbar styling */
            ::-webkit-scrollbar {
                width: 8px;
                height: 8px;
            }
            
            ::-webkit-scrollbar-track {
                background: var(--bg-secondary);
            }
            
            ::-webkit-scrollbar-thumb {
                background: var(--border-default);
                border-radius: 4px;
            }
            
            ::-webkit-scrollbar-thumb:hover {
                background: var(--text-muted);
            }
            
            /* Premium Card Styles */
            .glass-card {
                background: var(--bg-card);
                backdrop-filter: blur(20px);
                -webkit-backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 16px;
                padding: 20px;
                transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
            }
            
            .glass-card:hover {
                background: var(--bg-card-hover);
                border-color: var(--border-glow);
                box-shadow: 0 8px 32px rgba(78, 205, 196, 0.1);
                transform: translateY(-2px);
            }
            
            /* KPI Cards Container - Ensures uniform sizing */
            [data-testid="stHorizontalBlock"] {
                display: flex;
                align-items: stretch !important;
            }
            
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] {
                display: flex;
                flex-direction: column;
            }
            
            [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] > div {
                flex: 1;
                display: flex;
                flex-direction: column;
            }
            
            /* KPI Card Styles - UNIFORM HEIGHT */
            .kpi-card {
                background: linear-gradient(145deg, rgba(20, 25, 35, 0.9), rgba(15, 20, 30, 0.9));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 16px;
                padding: 18px 20px;
                text-align: center;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
                min-height: 130px;
                height: 100%;
                display: flex;
                flex-direction: column;
                justify-content: center;
                box-sizing: border-box;
            }
            
            .kpi-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                right: 0;
                height: 3px;
                background: var(--gradient-2);
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            
            .kpi-card:hover::before {
                opacity: 1;
            }
            
            .kpi-card:hover {
                border-color: var(--accent-cyan);
                box-shadow: 0 4px 24px rgba(78, 205, 196, 0.15);
                transform: translateY(-2px);
            }
            
            .kpi-label {
                font-family: 'Inter', sans-serif;
                font-size: 11px;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 10px;
                white-space: nowrap;
            }
            
            .kpi-value {
                font-family: 'JetBrains Mono', monospace;
                font-size: 24px;
                font-weight: 700;
                color: var(--text-primary);
                line-height: 1.3;
                transition: color 0.3s ease;
            }
            
            .kpi-delta {
                font-family: 'Inter', sans-serif;
                font-size: 11px;
                font-weight: 500;
                margin-top: 8px;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }
            
            .kpi-delta.positive { color: var(--accent-green); }
            .kpi-delta.negative { color: var(--accent-red); }
            .kpi-delta.neutral { color: var(--text-secondary); }
            
            /* Connection Status Bar */
            .status-bar {
                background: linear-gradient(90deg, rgba(20, 25, 35, 0.95), rgba(15, 20, 30, 0.95));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 12px;
                padding: 12px 20px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 20px;
            }
            
            .status-indicator {
                display: flex;
                align-items: center;
                gap: 10px;
            }
            
            .status-dot {
                width: 10px;
                height: 10px;
                border-radius: 50%;
                animation: pulse 2s ease-in-out infinite;
            }
            
            .status-dot.connected {
                background: var(--accent-green);
                box-shadow: 0 0 12px var(--accent-green);
            }
            
            .status-dot.reconnecting {
                background: var(--accent-yellow);
                box-shadow: 0 0 12px var(--accent-yellow);
                animation: blink 1s ease-in-out infinite;
            }
            
            .status-dot.disconnected {
                background: var(--accent-red);
                box-shadow: 0 0 12px var(--accent-red);
            }
            
            @keyframes pulse {
                0%, 100% { opacity: 1; transform: scale(1); }
                50% { opacity: 0.7; transform: scale(1.1); }
            }
            
            @keyframes blink {
                0%, 100% { opacity: 1; }
                50% { opacity: 0.3; }
            }
            
            /* Insight Panel Styles */
            .insight-container {
                background: linear-gradient(145deg, rgba(20, 25, 35, 0.9), rgba(15, 20, 30, 0.9));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 16px;
                padding: 20px;
                height: 100%;
            }
            
            .insight-header {
                display: flex;
                align-items: center;
                gap: 12px;
                margin-bottom: 20px;
                padding-bottom: 16px;
                border-bottom: 1px solid var(--border-default);
            }
            
            .insight-header-icon {
                font-size: 24px;
            }
            
            .insight-header-text {
                font-family: 'Inter', sans-serif;
                font-size: 16px;
                font-weight: 700;
                color: var(--text-primary);
                letter-spacing: -0.3px;
            }
            
            .insight-card {
                background: rgba(15, 20, 30, 0.6);
                border: 1px solid var(--border-default);
                border-radius: 12px;
                padding: 16px;
                margin-bottom: 12px;
                transition: all 0.3s ease;
                position: relative;
                overflow: hidden;
            }
            
            .insight-card::before {
                content: '';
                position: absolute;
                top: 0;
                left: 0;
                bottom: 0;
                width: 4px;
                border-radius: 4px 0 0 4px;
            }
            
            .insight-card.high::before {
                background: linear-gradient(180deg, #ff6b6b, #ff8a8a);
            }
            
            .insight-card.medium::before {
                background: linear-gradient(180deg, #ffd93d, #ffe066);
            }
            
            .insight-card.low::before {
                background: linear-gradient(180deg, #00d4aa, #00ffc8);
            }
            
            .insight-card:hover {
                background: rgba(25, 30, 45, 0.8);
                border-color: var(--border-glow);
                transform: translateX(4px);
            }
            
            .priority-badge {
                display: inline-flex;
                align-items: center;
                gap: 6px;
                padding: 4px 12px;
                border-radius: 20px;
                font-family: 'Inter', sans-serif;
                font-size: 10px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 10px;
            }
            
            .priority-badge.high {
                background: rgba(255, 107, 107, 0.15);
                color: #ff6b6b;
                border: 1px solid rgba(255, 107, 107, 0.3);
            }
            
            .priority-badge.medium {
                background: rgba(255, 217, 61, 0.15);
                color: #ffd93d;
                border: 1px solid rgba(255, 217, 61, 0.3);
            }
            
            .priority-badge.low {
                background: rgba(0, 212, 170, 0.15);
                color: #00d4aa;
                border: 1px solid rgba(0, 212, 170, 0.3);
            }
            
            .insight-title {
                font-family: 'Inter', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary);
                line-height: 1.5;
                margin-bottom: 12px;
            }
            
            .insight-row {
                display: flex;
                align-items: flex-start;
                margin-bottom: 8px;
            }
            
            .insight-label {
                font-family: 'Inter', sans-serif;
                font-size: 10px;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                min-width: 55px;
                padding-top: 2px;
            }
            
            .insight-value {
                font-family: 'Inter', sans-serif;
                font-size: 13px;
                color: var(--text-secondary);
                line-height: 1.4;
            }
            
            .insight-value.action {
                color: var(--accent-cyan);
                font-weight: 500;
            }
            
            .insight-value.impact {
                color: var(--accent-green);
                font-weight: 600;
            }
            
            /* Chart Container - Anti-flicker */
            .chart-container {
                background: linear-gradient(145deg, rgba(20, 25, 35, 0.9), rgba(15, 20, 30, 0.9));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 16px;
                padding: 16px;
                transition: border-color 0.3s ease, box-shadow 0.3s ease;
                min-height: 340px;
                position: relative;
            }
            
            .chart-container:hover {
                border-color: var(--border-glow);
                box-shadow: 0 8px 32px rgba(78, 205, 196, 0.08);
            }
            
            /* Plotly chart anti-flicker */
            .js-plotly-plot {
                transition: none !important;
            }
            
            .js-plotly-plot .plotly {
                transition: none !important;
            }
            
            .js-plotly-plot .main-svg {
                transition: none !important;
            }
            
            /* Prevent Streamlit container flicker */
            [data-testid="stVerticalBlock"] {
                transition: none !important;
            }
            
            /* Chart titles for professional look */
            .chart-title {
                font-family: 'Inter', sans-serif;
                font-size: 14px;
                font-weight: 600;
                color: var(--text-primary);
                margin-bottom: 12px;
                padding-left: 4px;
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .chart-title-icon {
                font-size: 16px;
            }
            
            /* Filter Controls Styling */
            .filter-bar {
                display: flex;
                align-items: center;
                gap: 16px;
                margin-bottom: 20px;
                padding: 16px 20px;
                background: linear-gradient(90deg, rgba(20, 25, 35, 0.95), rgba(15, 20, 30, 0.95));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 12px;
            }
            
            .filter-group {
                display: flex;
                align-items: center;
                gap: 8px;
            }
            
            .filter-label {
                font-family: 'Inter', sans-serif;
                font-size: 11px;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }
            
            /* Streamlit selectbox styling */
            [data-testid="stSelectbox"] {
                min-width: 120px;
            }
            
            [data-testid="stSelectbox"] > div > div {
                background: rgba(15, 20, 30, 0.8) !important;
                border: 1px solid var(--border-default) !important;
                border-radius: 8px !important;
                color: var(--text-primary) !important;
                font-family: 'Inter', sans-serif !important;
                font-size: 13px !important;
            }
            
            [data-testid="stSelectbox"] > div > div:hover {
                border-color: var(--accent-cyan) !important;
            }
            
            /* Radio button styling */
            [data-testid="stRadio"] > div {
                display: flex !important;
                flex-direction: row !important;
                gap: 0 !important;
                background: rgba(15, 20, 30, 0.8);
                border: 1px solid var(--border-default);
                border-radius: 8px;
                padding: 4px;
            }
            
            [data-testid="stRadio"] label {
                padding: 6px 14px !important;
                border-radius: 6px !important;
                font-family: 'Inter', sans-serif !important;
                font-size: 12px !important;
                font-weight: 500 !important;
                transition: all 0.2s ease !important;
                margin: 0 !important;
            }
            
            [data-testid="stRadio"] label:hover {
                background: rgba(78, 205, 196, 0.1) !important;
            }
            
            [data-testid="stRadio"] label[data-checked="true"] {
                background: var(--accent-cyan) !important;
                color: #0a0a0f !important;
            }
            
            [data-testid="stRadio"] > label {
                display: none !important;
            }
            
            [data-testid="stRadio"] [data-testid="stMarkdownContainer"] {
                display: none !important;
            }
            
            /* Dashboard Header */
            .dashboard-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                margin-bottom: 24px;
                padding: 20px 24px;
                background: linear-gradient(90deg, rgba(20, 25, 35, 0.95), rgba(15, 20, 30, 0.95));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 16px;
            }
            
            .logo-section {
                display: flex;
                align-items: center;
                gap: 16px;
            }
            
            .logo-icon {
                width: 48px;
                height: 48px;
                background: var(--gradient-2);
                border-radius: 12px;
                display: flex;
                align-items: center;
                justify-content: center;
                font-size: 24px;
            }
            
            .logo-text {
                display: flex;
                flex-direction: column;
            }
            
            .logo-title {
                font-family: 'Inter', sans-serif;
                font-size: 22px;
                font-weight: 800;
                background: linear-gradient(135deg, #ffffff 0%, #4ecdc4 100%);
                -webkit-background-clip: text;
                -webkit-text-fill-color: transparent;
                background-clip: text;
                letter-spacing: -0.5px;
            }
            
            .logo-subtitle {
                font-family: 'Inter', sans-serif;
                font-size: 12px;
                color: var(--text-muted);
                font-weight: 500;
                letter-spacing: 0.5px;
            }
            
            .live-badge {
                display: flex;
                align-items: center;
                gap: 8px;
                padding: 8px 16px;
                background: rgba(0, 212, 170, 0.1);
                border: 1px solid rgba(0, 212, 170, 0.3);
                border-radius: 20px;
            }
            
            .live-dot {
                width: 8px;
                height: 8px;
                background: var(--accent-green);
                border-radius: 50%;
                animation: pulse 2s ease-in-out infinite;
            }
            
            .live-text {
                font-family: 'Inter', sans-serif;
                font-size: 12px;
                font-weight: 600;
                color: var(--accent-green);
                text-transform: uppercase;
                letter-spacing: 1px;
            }
            
            /* Section Headers */
            .section-header {
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 16px;
            }
            
            .section-icon {
                font-size: 18px;
            }
            
            .section-title {
                font-family: 'Inter', sans-serif;
                font-size: 15px;
                font-weight: 700;
                color: var(--text-primary);
                letter-spacing: -0.3px;
            }
            
            /* Metrics Row */
            .metrics-summary {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 16px;
                margin-top: 20px;
                padding: 20px;
                background: linear-gradient(145deg, rgba(20, 25, 35, 0.9), rgba(15, 20, 30, 0.9));
                backdrop-filter: blur(20px);
                border: 1px solid var(--border-default);
                border-radius: 16px;
            }
            
            .metric-item {
                text-align: center;
                padding: 12px;
                background: rgba(15, 20, 30, 0.5);
                border-radius: 12px;
                border: 1px solid transparent;
                transition: all 0.3s ease;
            }
            
            .metric-item:hover {
                border-color: var(--border-glow);
                background: rgba(20, 25, 35, 0.8);
            }
            
            .metric-label {
                font-family: 'Inter', sans-serif;
                font-size: 10px;
                font-weight: 600;
                color: var(--text-muted);
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 4px;
            }
            
            .metric-value {
                font-family: 'JetBrains Mono', monospace;
                font-size: 18px;
                font-weight: 600;
                color: var(--text-primary);
            }
            
            /* Plotly chart overrides - Enhanced Mode Bar */
            .js-plotly-plot .plotly .modebar {
                background: rgba(20, 25, 35, 0.9) !important;
                border-radius: 8px !important;
                padding: 4px 8px !important;
                border: 1px solid rgba(255,255,255,0.1) !important;
                right: 10px !important;
                top: 10px !important;
            }
            
            .js-plotly-plot .plotly .modebar-btn {
                padding: 6px !important;
            }
            
            .js-plotly-plot .plotly .modebar-btn path {
                fill: #a0aec0 !important;
            }
            
            .js-plotly-plot .plotly .modebar-btn:hover path {
                fill: #8b5cf6 !important;
            }
            
            .js-plotly-plot .plotly .modebar-btn.active path {
                fill: #f59e0b !important;
            }
            
            /* Animation classes */
            .fade-in {
                animation: fadeIn 0.5s ease-out;
            }
            
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            
            /* Responsive adjustments */
            @media (max-width: 1200px) {
                .kpi-value { font-size: 22px; }
                .metrics-summary { grid-template-columns: repeat(2, 1fr); }
            }
        </style>
        """
    
    # ==========================================================================
    # COLOR UTILITY METHODS
    # ==========================================================================
    
    @classmethod
    def get_spread_color(cls, spread_bps: float) -> str:
        """Get color based on spread value."""
        if spread_bps < 3:
            return cls.GREEN
        elif spread_bps < 6:
            return cls.YELLOW
        else:
            return cls.RED
    
    @classmethod
    def get_velocity_color(cls, velocity: float) -> str:
        """Get color based on velocity value."""
        if velocity < 30:
            return cls.GREEN
        elif velocity < 60:
            return cls.YELLOW
        else:
            return cls.RED
    
    @classmethod
    def get_imbalance_color(cls, imbalance: float) -> str:
        """Get color based on imbalance value."""
        if imbalance > 0.3:
            return cls.GREEN
        elif imbalance < -0.3:
            return cls.RED
        elif imbalance > 0:
            return cls.GREEN
        else:
            return cls.RED
    
    @classmethod
    def get_volatility_color(cls, volatility_bps: float) -> str:
        """Get color based on volatility value."""
        if volatility_bps < 15:
            return cls.GREEN
        elif volatility_bps < 20:
            return cls.YELLOW
        else:
            return cls.RED
