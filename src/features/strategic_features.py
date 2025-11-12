"""
Strategic Assistant Features

Implements core features based on the converged design:
1. Objective Timers
2. CS/Min Tracker
3. Purchase Suggestions
4. Map Awareness
"""

import time
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.analysis.ocr_reader import GameTime, ObjectiveType, ObjectiveEvent


class ItemTier(Enum):
    """Item tier categories"""
    STARTER = "starter"
    BASIC = "basic"
    EPIC = "epic"
    LEGENDARY = "legendary"
    MYTHIC = "mythic"


@dataclass
class Item:
    """Represents an in-game item"""
    name: str
    cost: int
    tier: ItemTier
    components: List[str] = field(default_factory=list)


@dataclass
class ObjectiveTimer:
    """Represents an objective respawn timer"""
    objective_type: ObjectiveType
    death_time: float
    respawn_time: float
    game_time_at_death: Optional[GameTime] = None

    def time_remaining(self, current_time: float) -> float:
        """Get time remaining until respawn"""
        return max(0, self.respawn_time - current_time)

    def is_active(self, current_time: float) -> bool:
        """Check if timer is still active"""
        return current_time < self.respawn_time


@dataclass
class CSStats:
    """CS tracking statistics"""
    current_cs: int
    game_time: GameTime
    cs_per_min: float

    def update(self, new_cs: int, new_game_time: GameTime):
        """Update CS stats"""
        self.current_cs = new_cs
        self.game_time = new_game_time

        # Calculate CS/min
        total_minutes = new_game_time.to_seconds() / 60.0
        if total_minutes > 0:
            self.cs_per_min = new_cs / total_minutes


class ObjectiveTimerManager:
    """
    Manages objective respawn timers.

    Tracks Dragon, Baron, and Herald timers based on death events.
    """

    # Respawn times in seconds
    RESPAWN_TIMES = {
        ObjectiveType.DRAGON: 300,  # 5 minutes
        ObjectiveType.BARON: 360,   # 6 minutes
        ObjectiveType.HERALD: 360,  # 6 minutes (first herald)
    }

    def __init__(self):
        """Initialize the timer manager"""
        self.active_timers: List[ObjectiveTimer] = []
        self.timer_history: List[ObjectiveTimer] = []

    def add_objective_event(self, event: ObjectiveEvent) -> Optional[ObjectiveTimer]:
        """
        Add an objective death event and create timer.

        Args:
            event: Objective death event

        Returns:
            Created ObjectiveTimer or None if not applicable
        """
        # Get respawn time for this objective
        respawn_duration = self.RESPAWN_TIMES.get(event.objective_type)

        if respawn_duration is None:
            return None

        # Create timer
        timer = ObjectiveTimer(
            objective_type=event.objective_type,
            death_time=event.timestamp,
            respawn_time=event.timestamp + respawn_duration,
            game_time_at_death=event.game_time
        )

        self.active_timers.append(timer)
        self.timer_history.append(timer)

        return timer

    def get_active_timers(self, current_time: float) -> List[ObjectiveTimer]:
        """
        Get all currently active timers.

        Args:
            current_time: Current timestamp

        Returns:
            List of active timers
        """
        # Clean up expired timers
        self.active_timers = [
            timer for timer in self.active_timers
            if timer.is_active(current_time)
        ]

        return self.active_timers

    def get_timer_for_objective(self, objective_type: ObjectiveType,
                                current_time: float) -> Optional[ObjectiveTimer]:
        """
        Get active timer for specific objective.

        Args:
            objective_type: Type of objective
            current_time: Current timestamp

        Returns:
            ObjectiveTimer or None
        """
        active = self.get_active_timers(current_time)

        for timer in active:
            if timer.objective_type == objective_type:
                return timer

        return None


class CSTracker:
    """
    Tracks CS (Creep Score) per minute.

    Calculates and monitors farming efficiency.
    """

    def __init__(self):
        """Initialize the CS tracker"""
        self.history: List[CSStats] = []
        self.current_stats: Optional[CSStats] = None

        # CS benchmarks for evaluation
        self.benchmarks = {
            "poor": 4.0,
            "below_average": 5.5,
            "average": 7.0,
            "good": 8.5,
            "excellent": 10.0
        }

    def update(self, cs: int, game_time: GameTime):
        """
        Update CS tracking with new data.

        Args:
            cs: Current CS count
            game_time: Current game time
        """
        if self.current_stats is None:
            self.current_stats = CSStats(cs, game_time, 0.0)
        else:
            self.current_stats.update(cs, game_time)

        # Add to history (sample every minute)
        if not self.history or \
           game_time.to_seconds() - self.history[-1].game_time.to_seconds() >= 60:
            self.history.append(CSStats(cs, game_time, self.current_stats.cs_per_min))

    def get_cs_per_min(self) -> float:
        """Get current CS per minute"""
        return self.current_stats.cs_per_min if self.current_stats else 0.0

    def get_performance_rating(self) -> str:
        """
        Get performance rating based on CS/min.

        Returns:
            Rating string: "excellent", "good", "average", "below_average", "poor"
        """
        cs_per_min = self.get_cs_per_min()

        if cs_per_min >= self.benchmarks["excellent"]:
            return "excellent"
        elif cs_per_min >= self.benchmarks["good"]:
            return "good"
        elif cs_per_min >= self.benchmarks["average"]:
            return "average"
        elif cs_per_min >= self.benchmarks["below_average"]:
            return "below_average"
        else:
            return "poor"

    def get_stats(self) -> Optional[CSStats]:
        """Get current CS stats"""
        return self.current_stats


class PurchaseAdvisor:
    """
    Provides item purchase suggestions based on gold and build path.

    Helps players optimize their gold spending.
    """

    def __init__(self):
        """Initialize the purchase advisor"""
        # Sample item database (simplified)
        self.items = self._load_items()
        self.build_paths: Dict[str, List[str]] = {}

    def _load_items(self) -> Dict[str, Item]:
        """
        Load item database.

        Returns:
            Dictionary of items
        """
        # Sample items (would be loaded from file in production)
        items = {
            "long_sword": Item("Long Sword", 350, ItemTier.BASIC),
            "cloth_armor": Item("Cloth Armor", 300, ItemTier.BASIC),
            "amplifying_tome": Item("Amplifying Tome", 435, ItemTier.BASIC),
            "vampiric_scepter": Item("Vampiric Scepter", 900, ItemTier.BASIC),
            "serrated_dirk": Item("Serrated Dirk", 1100, ItemTier.EPIC),
            "pickaxe": Item("Pickaxe", 875, ItemTier.BASIC),
            "infinity_edge": Item("Infinity Edge", 3400, ItemTier.LEGENDARY,
                                 ["pickaxe", "pickaxe", "long_sword"]),
            "blade_ruined_king": Item("Blade of the Ruined King", 3200, ItemTier.LEGENDARY,
                                     ["vampiric_scepter", "pickaxe"]),
        }

        return items

    def set_build_path(self, champion: str, items: List[str]):
        """
        Set recommended build path for a champion.

        Args:
            champion: Champion name
            items: List of item names in order
        """
        self.build_paths[champion] = items

    def get_next_item(self, champion: str, current_items: List[str],
                     current_gold: int) -> Optional[Tuple[str, int]]:
        """
        Get next recommended item to purchase.

        Args:
            champion: Champion name
            current_items: List of items already purchased
            current_gold: Current gold amount

        Returns:
            Tuple of (item_name, cost) or None
        """
        # Get build path for champion
        build_path = self.build_paths.get(champion, [])

        if not build_path:
            return None

        # Find next item not yet purchased
        for item_name in build_path:
            if item_name not in current_items:
                item = self.items.get(item_name)

                if item:
                    return (item.name, item.cost)

        return None

    def get_affordable_items(self, current_gold: int,
                            tier: Optional[ItemTier] = None) -> List[Tuple[str, int]]:
        """
        Get list of items that can be purchased with current gold.

        Args:
            current_gold: Current gold amount
            tier: Optional filter by tier

        Returns:
            List of (item_name, cost) tuples
        """
        affordable = []

        for name, item in self.items.items():
            if item.cost <= current_gold:
                if tier is None or item.tier == tier:
                    affordable.append((item.name, item.cost))

        # Sort by cost (descending)
        affordable.sort(key=lambda x: x[1], reverse=True)

        return affordable

    def should_suggest_purchase(self, current_gold: int, next_item_cost: int,
                               gold_threshold: float = 0.9) -> bool:
        """
        Determine if purchase should be suggested.

        Args:
            current_gold: Current gold amount
            next_item_cost: Cost of next item
            gold_threshold: Percentage threshold (0.9 = 90%)

        Returns:
            True if should suggest purchase
        """
        return current_gold >= (next_item_cost * gold_threshold)


class MapAwarenessMonitor:
    """
    Monitors minimap for threats and manages alerts.

    Coordinates with minimap analyzer to provide timely warnings.
    """

    def __init__(self):
        """Initialize the map awareness monitor"""
        self.recent_alerts: List[Tuple[float, Tuple[int, int]]] = []
        self.alert_cooldown = 5.0  # seconds

    def should_alert(self, position: Tuple[int, int], current_time: float) -> bool:
        """
        Determine if should create alert for this position.

        Args:
            position: Threat position
            current_time: Current timestamp

        Returns:
            True if should alert
        """
        # Check if similar alert was recently shown
        for alert_time, alert_pos in self.recent_alerts:
            if current_time - alert_time < self.alert_cooldown:
                # Check if position is similar
                distance = ((position[0] - alert_pos[0])**2 +
                          (position[1] - alert_pos[1])**2) ** 0.5

                if distance < 30:  # 30 pixel tolerance
                    return False

        return True

    def record_alert(self, position: Tuple[int, int], current_time: float):
        """
        Record that an alert was shown.

        Args:
            position: Alert position
            current_time: Current timestamp
        """
        self.recent_alerts.append((current_time, position))

        # Cleanup old alerts
        self.recent_alerts = [
            (t, pos) for t, pos in self.recent_alerts
            if current_time - t < self.alert_cooldown * 2
        ]


class StrategicAssistant:
    """
    Main strategic assistant that coordinates all features.

    Aggregates data from various analyzers and provides actionable insights.
    """

    def __init__(self, config):
        """
        Initialize the strategic assistant.

        Args:
            config: Application configuration
        """
        self.config = config

        # Initialize feature managers
        self.objective_timers = ObjectiveTimerManager()
        self.cs_tracker = CSTracker()
        self.purchase_advisor = PurchaseAdvisor()
        self.map_awareness = MapAwarenessMonitor()

        # State tracking
        self.last_update_time = time.time()

    def is_feature_enabled(self, feature_name: str) -> bool:
        """Check if a feature is enabled"""
        return self.config.features.get(feature_name, False)

    def process_ocr_data(self, ocr_data: Dict):
        """
        Process OCR data and update relevant features.

        Args:
            ocr_data: Dictionary of OCR results
        """
        # Update CS tracker
        if self.is_feature_enabled("cs_tracker"):
            cs = ocr_data.get("cs")
            game_time = ocr_data.get("game_time")

            if cs is not None and game_time is not None:
                self.cs_tracker.update(cs, game_time)

        # Process objective events
        if self.is_feature_enabled("objective_timers"):
            objective_events = ocr_data.get("objective_events", [])

            for event in objective_events:
                self.objective_timers.add_objective_event(event)

    def process_minimap_data(self, threats: List) -> List[Dict]:
        """
        Process minimap threat data.

        Args:
            threats: List of detected threats

        Returns:
            List of alert events
        """
        if not self.is_feature_enabled("map_awareness"):
            return []

        alerts = []
        current_time = time.time()

        for threat in threats:
            if threat.is_new and self.map_awareness.should_alert(threat.position, current_time):
                alerts.append({
                    "type": "minimap_alert",
                    "position": threat.position,
                    "confidence": threat.confidence
                })

                self.map_awareness.record_alert(threat.position, current_time)

        return alerts

    def get_state(self) -> Dict:
        """
        Get current state of all features.

        Returns:
            Dictionary containing current state
        """
        current_time = time.time()

        state = {
            "timestamp": current_time,
            "features": {}
        }

        # Objective timers
        if self.is_feature_enabled("objective_timers"):
            active_timers = self.objective_timers.get_active_timers(current_time)
            state["features"]["objective_timers"] = [
                {
                    "objective": timer.objective_type.value,
                    "time_remaining": timer.time_remaining(current_time)
                }
                for timer in active_timers
            ]

        # CS stats
        if self.is_feature_enabled("cs_tracker"):
            cs_stats = self.cs_tracker.get_stats()
            if cs_stats:
                state["features"]["cs_tracker"] = {
                    "cs": cs_stats.current_cs,
                    "cs_per_min": cs_stats.cs_per_min,
                    "rating": self.cs_tracker.get_performance_rating()
                }

        return state


# Testing
if __name__ == "__main__":
    from src.config.config_loader import load_default_config

    config = load_default_config()
    assistant = StrategicAssistant(config)

    print("Testing Strategic Assistant...")

    # Test objective timer
    event = ObjectiveEvent(
        objective_type=ObjectiveType.DRAGON,
        team="enemy",
        timestamp=time.time(),
        game_time=GameTime(minutes=5, seconds=30)
    )

    timer = assistant.objective_timers.add_objective_event(event)
    print(f"Created timer for {timer.objective_type.value}, "
          f"respawns in {timer.time_remaining(time.time()):.0f}s")

    # Test CS tracker
    assistant.cs_tracker.update(100, GameTime(minutes=10, seconds=0))
    print(f"CS/min: {assistant.cs_tracker.get_cs_per_min():.2f}, "
          f"Rating: {assistant.cs_tracker.get_performance_rating()}")

    # Get state
    state = assistant.get_state()
    print(f"\nCurrent state: {state}")
