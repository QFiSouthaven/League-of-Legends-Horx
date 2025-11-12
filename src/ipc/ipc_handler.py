"""
IPC Handler Module with Adaptive Jitter Control

This module implements the Inter-Process Communication bridge between the Python
backend and the Electron frontend. It includes adaptive jitter control to minimize
behavioral footprints by applying context-aware randomized delays.
"""

import asyncio
import json
import random
import time
from typing import Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from enum import Enum
import websockets
from websockets.server import WebSocketServerProtocol


class EventCategory(Enum):
    """Event categories for jitter control"""
    INFORMATIONAL = "informational"
    OBJECTIVE_TIMER = "objective_timers"
    MINIMAP_ALERT = "minimap_alerts"
    PURCHASE_SUGGESTION = "purchase_suggestions"
    TACTICAL = "tactical"


@dataclass
class GameEvent:
    """Represents a game event to be sent to the overlay"""
    category: EventCategory
    event_type: str
    data: Dict[str, Any]
    timestamp: float
    priority: int = 5  # 1-10, higher = more urgent


class AdaptiveJitterControl:
    """
    Implements context-aware randomized delays for events.

    This system categorizes events and applies specified jitter ranges to
    minimize the application's behavioral footprint and appear more human-like.
    """

    def __init__(self, jitter_ranges: Dict[str, tuple]):
        """
        Initialize the jitter control system.

        Args:
            jitter_ranges: Dictionary mapping event categories to (min, max) delay tuples in ms
        """
        self.jitter_ranges = jitter_ranges
        self.last_event_times: Dict[str, float] = {}

    def apply_jitter(self, event: GameEvent) -> float:
        """
        Calculate and return the jitter delay for an event.

        Args:
            event: The game event to apply jitter to

        Returns:
            Delay in seconds
        """
        category_name = event.category.value

        # Get jitter range for this category
        jitter_range = self.jitter_ranges.get(category_name, (50, 200))

        # Apply priority-based adjustment
        # Higher priority = less jitter (more responsive)
        priority_factor = 1.0 - (event.priority / 20.0)  # Max 50% reduction
        min_jitter, max_jitter = jitter_range

        adjusted_min = min_jitter * priority_factor
        adjusted_max = max_jitter * priority_factor

        # Generate random jitter in the range
        jitter_ms = random.uniform(adjusted_min, adjusted_max)

        # Ensure minimum spacing between similar events (anti-spam)
        current_time = time.time()
        last_time = self.last_event_times.get(category_name, 0)

        if current_time - last_time < 0.1:  # Minimum 100ms between same category
            jitter_ms += 100  # Add extra delay

        self.last_event_times[category_name] = current_time

        return jitter_ms / 1000.0  # Convert to seconds


class IPCHandler:
    """
    Handles IPC communication between Python backend and Electron frontend.

    Uses WebSocket for bidirectional communication with adaptive jitter control.
    """

    def __init__(self, host: str = "127.0.0.1", port: int = 8765,
                 jitter_ranges: Optional[Dict[str, tuple]] = None):
        """
        Initialize the IPC handler.

        Args:
            host: WebSocket server host
            port: WebSocket server port
            jitter_ranges: Optional custom jitter ranges
        """
        self.host = host
        self.port = port
        self.server = None
        self.clients: set = set()
        self.event_queue: asyncio.Queue = asyncio.Queue()
        self.running = False

        # Initialize jitter control
        if jitter_ranges is None:
            jitter_ranges = {
                "informational": (100, 300),
                "objective_timers": (50, 200),
                "minimap_alerts": (30, 80),
                "purchase_suggestions": (150, 400),
                "tactical": (20, 60)
            }

        self.jitter_control = AdaptiveJitterControl(jitter_ranges)

        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}

    async def start(self):
        """Start the WebSocket server"""
        self.running = True
        self.server = await websockets.serve(
            self._handle_client,
            self.host,
            self.port
        )
        print(f"IPC WebSocket server started on {self.host}:{self.port}")

        # Start event processing loop
        asyncio.create_task(self._process_event_queue())

    async def stop(self):
        """Stop the WebSocket server"""
        self.running = False

        # Close all client connections
        if self.clients:
            await asyncio.gather(
                *[client.close() for client in self.clients],
                return_exceptions=True
            )

        # Stop the server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        print("IPC WebSocket server stopped")

    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """
        Handle a new client connection.

        Args:
            websocket: The WebSocket connection
        """
        self.clients.add(websocket)
        print(f"Client connected: {websocket.remote_address}")

        try:
            async for message in websocket:
                await self._handle_message(message, websocket)
        except websockets.exceptions.ConnectionClosed:
            print(f"Client disconnected: {websocket.remote_address}")
        finally:
            self.clients.remove(websocket)

    async def _handle_message(self, message: str, websocket: WebSocketServerProtocol):
        """
        Handle incoming message from client.

        Args:
            message: JSON message from client
            websocket: The WebSocket connection
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            # Call registered handler if exists
            if msg_type in self.message_handlers:
                handler = self.message_handlers[msg_type]
                response = await handler(data)

                if response:
                    await websocket.send(json.dumps(response))
            else:
                print(f"Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            print(f"Invalid JSON received: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")

    def register_handler(self, message_type: str, handler: Callable):
        """
        Register a message handler for a specific message type.

        Args:
            message_type: The message type to handle
            handler: Async function to handle the message
        """
        self.message_handlers[message_type] = handler

    async def send_event(self, event: GameEvent):
        """
        Queue an event to be sent to all connected clients with jitter.

        Args:
            event: The game event to send
        """
        await self.event_queue.put(event)

    async def _process_event_queue(self):
        """Process queued events with adaptive jitter"""
        while self.running:
            try:
                # Get next event from queue
                event = await asyncio.wait_for(
                    self.event_queue.get(),
                    timeout=1.0
                )

                # Apply jitter delay
                jitter_delay = self.jitter_control.apply_jitter(event)
                await asyncio.sleep(jitter_delay)

                # Send to all connected clients
                await self._broadcast_event(event)

            except asyncio.TimeoutError:
                # No events in queue, continue
                continue
            except Exception as e:
                print(f"Error processing event: {e}")

    async def _broadcast_event(self, event: GameEvent):
        """
        Broadcast an event to all connected clients.

        Args:
            event: The game event to broadcast
        """
        if not self.clients:
            return

        message = {
            "type": "game_event",
            "category": event.category.value,
            "event_type": event.event_type,
            "data": event.data,
            "timestamp": event.timestamp
        }

        message_json = json.dumps(message)

        # Send to all clients
        await asyncio.gather(
            *[client.send(message_json) for client in self.clients],
            return_exceptions=True
        )

    async def send_direct(self, message: Dict[str, Any]):
        """
        Send a message directly without jitter (for system messages).

        Args:
            message: The message to send
        """
        if not self.clients:
            return

        message_json = json.dumps(message)

        await asyncio.gather(
            *[client.send(message_json) for client in self.clients],
            return_exceptions=True
        )


# Convenience functions for creating events
def create_objective_event(objective_name: str, respawn_time: float, **kwargs) -> GameEvent:
    """Create an objective timer event"""
    return GameEvent(
        category=EventCategory.OBJECTIVE_TIMER,
        event_type="objective_timer",
        data={
            "objective": objective_name,
            "respawn_time": respawn_time,
            **kwargs
        },
        timestamp=time.time(),
        priority=8
    )


def create_minimap_event(enemy_location: tuple, champion_name: Optional[str] = None, **kwargs) -> GameEvent:
    """Create a minimap alert event"""
    return GameEvent(
        category=EventCategory.MINIMAP_ALERT,
        event_type="minimap_alert",
        data={
            "location": enemy_location,
            "champion": champion_name,
            **kwargs
        },
        timestamp=time.time(),
        priority=9
    )


def create_informational_event(event_type: str, data: Dict[str, Any], priority: int = 5) -> GameEvent:
    """Create a generic informational event"""
    return GameEvent(
        category=EventCategory.INFORMATIONAL,
        event_type=event_type,
        data=data,
        timestamp=time.time(),
        priority=priority
    )


def create_purchase_event(item_name: str, cost: int, **kwargs) -> GameEvent:
    """Create a purchase suggestion event"""
    return GameEvent(
        category=EventCategory.PURCHASE_SUGGESTION,
        event_type="purchase_suggestion",
        data={
            "item": item_name,
            "cost": cost,
            **kwargs
        },
        timestamp=time.time(),
        priority=4
    )


# Example usage and testing
async def main():
    """Test the IPC handler"""
    handler = IPCHandler()

    # Register a test handler
    async def handle_ping(data):
        print(f"Received ping: {data}")
        return {"type": "pong", "timestamp": time.time()}

    handler.register_handler("ping", handle_ping)

    # Start the server
    await handler.start()

    # Simulate sending events
    for i in range(5):
        event = create_objective_event(
            objective_name="Dragon",
            respawn_time=time.time() + 300
        )
        await handler.send_event(event)
        print(f"Queued event {i+1}")
        await asyncio.sleep(0.5)

    # Keep running
    try:
        await asyncio.Future()  # Run forever
    except KeyboardInterrupt:
        await handler.stop()


if __name__ == "__main__":
    asyncio.run(main())
