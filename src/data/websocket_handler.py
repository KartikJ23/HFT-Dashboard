"""
HFT Live Dashboard - WebSocket Handler
=======================================

Manages WebSocket connections to Binance for real-time trade and depth data.
Features:
- Dual stream connection (trades + order book)
- Automatic reconnection with exponential backoff
- Thread-safe data push to StateManager
- Connection status tracking
"""

import asyncio
import json
import threading
import logging
from datetime import datetime
from typing import Optional, Callable
import time

import websockets
from websockets.exceptions import ConnectionClosed, ConnectionClosedError

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import (
    COMBINED_WS_URL,
    TRADE_WS_URL,
    DEPTH_WS_URL,
    RECONNECT_DELAY_BASE,
    RECONNECT_DELAY_MAX,
    RECONNECT_MAX_ATTEMPTS,
    HEARTBEAT_TIMEOUT
)
from data.state_manager import StateManager


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BinanceWebSocketHandler:
    """
    Handles WebSocket connections to Binance exchange.
    
    Connects to both trade and depth streams via combined stream endpoint.
    Automatically reconnects on disconnection with exponential backoff.
    """
    
    def __init__(self, state_manager: StateManager, 
                 on_status_change: Optional[Callable[[str], None]] = None):
        """
        Initialize the WebSocket handler.
        
        Args:
            state_manager: StateManager instance for storing data
            on_status_change: Optional callback for connection status changes
        """
        self.state_manager = state_manager
        self.on_status_change = on_status_change
        
        # Connection state
        self._running = False
        self._connected = False
        self._reconnect_count = 0
        self._last_message_time: Optional[float] = None
        
        # Threading
        self._thread: Optional[threading.Thread] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stop_event = threading.Event()
        
        # Statistics
        self._message_count = 0
        self._trade_count = 0
        self._depth_count = 0
        self._error_count = 0
    
    def start(self) -> None:
        """Start the WebSocket connection in a background thread."""
        if self._running:
            logger.warning("WebSocket handler already running")
            return
        
        self._running = True
        self._stop_event.clear()
        
        # Create and start the background thread
        self._thread = threading.Thread(target=self._run_event_loop, daemon=True)
        self._thread.start()
        logger.info("WebSocket handler started")
    
    def stop(self) -> None:
        """Stop the WebSocket connection."""
        if not self._running:
            return
        
        self._running = False
        self._stop_event.set()
        
        # Cancel the event loop
        if self._loop and self._loop.is_running():
            self._loop.call_soon_threadsafe(self._loop.stop)
        
        # Wait for thread to finish
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        
        self._connected = False
        self.state_manager.set_connected(False)
        logger.info("WebSocket handler stopped")
    
    def is_running(self) -> bool:
        """Check if handler is running."""
        return self._running
    
    def is_connected(self) -> bool:
        """Check if WebSocket is connected."""
        return self._connected
    
    def get_stats(self) -> dict:
        """Get connection statistics."""
        return {
            "running": self._running,
            "connected": self._connected,
            "message_count": self._message_count,
            "trade_count": self._trade_count,
            "depth_count": self._depth_count,
            "error_count": self._error_count,
            "reconnect_count": self._reconnect_count,
            "last_message_age": (
                time.time() - self._last_message_time 
                if self._last_message_time else None
            )
        }
    
    def _run_event_loop(self) -> None:
        """Run the asyncio event loop in a background thread."""
        try:
            # Create new event loop for this thread
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)
            
            # Run the main connection handler
            self._loop.run_until_complete(self._connection_handler())
            
        except Exception as e:
            logger.error(f"Event loop error: {e}")
            self._error_count += 1
            self.state_manager.set_error(str(e))
        finally:
            if self._loop:
                self._loop.close()
    
    async def _connection_handler(self) -> None:
        """Main connection handler with reconnection logic."""
        while self._running and not self._stop_event.is_set():
            try:
                await self._connect_and_stream()
            except ConnectionClosed as e:
                logger.warning(f"WebSocket connection closed: {e}")
                self._handle_disconnect()
            except ConnectionClosedError as e:
                logger.warning(f"WebSocket connection closed with error: {e}")
                self._handle_disconnect()
            except Exception as e:
                logger.error(f"WebSocket error: {e}")
                self._error_count += 1
                self.state_manager.set_error(str(e))
                self._handle_disconnect()
            
            # Check if we should retry
            if self._running and not self._stop_event.is_set():
                delay = self._get_reconnect_delay()
                if delay > 0:
                    logger.info(f"Reconnecting in {delay:.1f} seconds...")
                    await asyncio.sleep(delay)
    
    async def _connect_and_stream(self) -> None:
        """Establish connection and stream data."""
        logger.info(f"Connecting to Binance WebSocket...")
        
        # Update status
        self.state_manager.set_reconnecting()
        self._update_status("reconnecting")
        
        async with websockets.connect(
            COMBINED_WS_URL,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5
        ) as websocket:
            # Connection successful
            self._connected = True
            self._reconnect_count = 0
            self.state_manager.set_connected(True)
            self._update_status("connected")
            logger.info("Connected to Binance WebSocket")
            
            # Start heartbeat checker
            heartbeat_task = asyncio.create_task(self._heartbeat_checker())
            
            try:
                # Stream messages
                async for message in websocket:
                    if self._stop_event.is_set():
                        break
                    
                    self._last_message_time = time.time()
                    self._message_count += 1
                    
                    try:
                        await self._process_message(message)
                    except Exception as e:
                        logger.error(f"Error processing message: {e}")
                        self._error_count += 1
            finally:
                heartbeat_task.cancel()
                try:
                    await heartbeat_task
                except asyncio.CancelledError:
                    pass
    
    async def _heartbeat_checker(self) -> None:
        """Check for connection heartbeat."""
        while self._running and self._connected:
            await asyncio.sleep(HEARTBEAT_TIMEOUT)
            
            if self._last_message_time:
                age = time.time() - self._last_message_time
                if age > HEARTBEAT_TIMEOUT:
                    logger.warning(f"No message for {age:.1f}s, connection may be stale")
    
    async def _process_message(self, raw_message: str) -> None:
        """Process incoming WebSocket message."""
        try:
            message = json.loads(raw_message)
            
            # Combined stream format: {"stream": "...", "data": {...}}
            if "stream" in message and "data" in message:
                stream = message["stream"]
                data = message["data"]
                
                if "trade" in stream:
                    self._process_trade(data)
                elif "depth" in stream:
                    self._process_depth(data)
            else:
                # Direct stream format (shouldn't happen with combined URL)
                if "e" in message and message["e"] == "trade":
                    self._process_trade(message)
                elif "bids" in message and "asks" in message:
                    self._process_depth(message)
                    
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            self._error_count += 1
    
    def _process_trade(self, data: dict) -> None:
        """Process a trade message."""
        try:
            # Parse trade data
            timestamp = datetime.utcfromtimestamp(data["T"] / 1000.0)
            price = float(data["p"])
            quantity = float(data["q"])
            is_buyer_maker = data["m"]  # True = sell, False = buy
            trade_id = data["t"]
            
            # Store in state manager
            self.state_manager.add_trade_raw(
                timestamp=timestamp,
                price=price,
                quantity=quantity,
                is_buyer_maker=is_buyer_maker,
                trade_id=trade_id
            )
            
            self._trade_count += 1
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing trade: {e}")
            self._error_count += 1
    
    def _process_depth(self, data: dict) -> None:
        """Process a depth (order book) message."""
        try:
            # Parse depth data
            timestamp = datetime.utcnow()
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            
            # Store in state manager
            self.state_manager.add_depth_raw(
                timestamp=timestamp,
                bids=bids,
                asks=asks
            )
            
            self._depth_count += 1
            
        except (KeyError, ValueError) as e:
            logger.error(f"Error parsing depth: {e}")
            self._error_count += 1
    
    def _handle_disconnect(self) -> None:
        """Handle disconnection."""
        self._connected = False
        self._reconnect_count += 1
        
        if self._reconnect_count >= RECONNECT_MAX_ATTEMPTS:
            self.state_manager.set_connected(False)
            self._update_status("disconnected")
            logger.error(f"Max reconnection attempts ({RECONNECT_MAX_ATTEMPTS}) reached")
        else:
            self.state_manager.set_reconnecting()
            self._update_status("reconnecting")
    
    def _get_reconnect_delay(self) -> float:
        """Calculate reconnection delay with exponential backoff."""
        if self._reconnect_count >= RECONNECT_MAX_ATTEMPTS:
            return 0  # Stop trying
        
        delay = RECONNECT_DELAY_BASE * (2 ** self._reconnect_count)
        return min(delay, RECONNECT_DELAY_MAX)
    
    def _update_status(self, status: str) -> None:
        """Update connection status and notify callback."""
        if self.on_status_change:
            try:
                self.on_status_change(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")


# =============================================================================
# STANDALONE TEST
# =============================================================================

if __name__ == "__main__":
    """Test the WebSocket handler standalone."""
    import time
    
    print("Testing Binance WebSocket Handler...")
    print("=" * 50)
    
    # Create state manager
    state = StateManager()
    
    # Create handler with status callback
    def on_status(status):
        print(f"[STATUS] {status}")
    
    handler = BinanceWebSocketHandler(state, on_status_change=on_status)
    
    # Start handler
    handler.start()
    
    # Run for 30 seconds
    try:
        for i in range(30):
            time.sleep(1)
            
            # Print stats every 5 seconds
            if (i + 1) % 5 == 0:
                stats = handler.get_stats()
                price = state.get_current_price()
                spread = state.get_current_spread_bps()
                
                print(f"\n[{i+1}s] Price: ${price:,.2f} | Spread: {spread:.2f} bps")
                print(f"     Trades: {stats['trade_count']} | Depth: {stats['depth_count']}")
                print(f"     Buffers: {state.get_buffer_sizes()}")
                
    except KeyboardInterrupt:
        print("\nStopping...")
    finally:
        handler.stop()
    
    print("\nTest complete!")
