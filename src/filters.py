"""
Event filtering system.
Allows subscribing to specific services, impact levels, and event types.
"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .epic_status import StatusEvent, EventType


@dataclass
class FilterConfig:
    """Configuration for filtering status events."""
    
    # Services to monitor (empty = all)
    # Examples: ["Fortnite", "Epic Games Store", "Rocket League"]
    services: list[str] = field(default_factory=list)
    
    # Minimum impact level to notify (for incidents)
    # Options: "none", "minor", "major", "critical"
    # "none" = all incidents, "critical" = only critical
    min_impact: str = "none"
    
    # Event types to monitor
    # Options: "incidents", "maintenance", "all"
    event_types: str = "all"
    
    # Keywords to always include (regardless of other filters)
    # Useful for specific game modes: ["LEGO Fortnite", "Rocket Racing"]
    always_include_keywords: list[str] = field(default_factory=list)
    
    # Keywords to always exclude
    exclude_keywords: list[str] = field(default_factory=list)

    IMPACT_LEVELS = ["none", "minor", "major", "critical"]

    def matches(self, event: StatusEvent) -> bool:
        """Check if an event matches this filter configuration."""
        
        # Check exclusions first
        if self.exclude_keywords:
            event_text = f"{event.name} {' '.join(event.component_names)}".lower()
            for keyword in self.exclude_keywords:
                if keyword.lower() in event_text:
                    return False
        
        # Check always-include keywords
        if self.always_include_keywords:
            event_text = f"{event.name} {' '.join(event.component_names)}".lower()
            for keyword in self.always_include_keywords:
                if keyword.lower() in event_text:
                    return True
        
        # Check event type
        if self.event_types == "incidents" and event.is_maintenance:
            return False
        if self.event_types == "maintenance" and event.is_incident:
            return False
        
        # Check impact level (for incidents only)
        if event.is_incident and self.min_impact != "none":
            event_impact_idx = self.IMPACT_LEVELS.index(event.impact) if event.impact in self.IMPACT_LEVELS else 0
            min_impact_idx = self.IMPACT_LEVELS.index(self.min_impact)
            if event_impact_idx < min_impact_idx:
                return False
        
        # Check services filter
        if self.services:
            # Match if event name or any component matches a watched service
            event_text = f"{event.name} {' '.join(event.component_names)}".lower()
            matched = any(service.lower() in event_text for service in self.services)
            if not matched:
                return False
        
        return True


def load_filter_config(config_path: Path | str | None = None) -> FilterConfig:
    """
    Load filter configuration from file or environment.
    
    Priority:
    1. Explicit config_path argument
    2. CONFIG_FILE environment variable
    3. config.json in project root
    4. Default (no filtering)
    """
    # Determine config path
    if config_path is None:
        config_path = os.environ.get("CONFIG_FILE")
    
    if config_path is None:
        default_path = Path(__file__).parent.parent / "config.json"
        if default_path.exists():
            config_path = default_path
    
    if config_path is None:
        # Check environment variables for simple config
        services_env = os.environ.get("WATCH_SERVICES", "")
        if services_env:
            services = [s.strip() for s in services_env.split(",") if s.strip()]
            return FilterConfig(services=services)
        return FilterConfig()
    
    # Load from file
    config_path = Path(config_path)
    if not config_path.exists():
        print(f"⚠️ Config file not found: {config_path}, using defaults")
        return FilterConfig()
    
    try:
        with open(config_path, "r") as f:
            data = json.load(f)
        
        return FilterConfig(
            services=data.get("services", []),
            min_impact=data.get("min_impact", "none"),
            event_types=data.get("event_types", "all"),
            always_include_keywords=data.get("always_include_keywords", []),
            exclude_keywords=data.get("exclude_keywords", []),
        )
    except (json.JSONDecodeError, KeyError) as e:
        print(f"⚠️ Error loading config: {e}, using defaults")
        return FilterConfig()


def filter_events(events: list[StatusEvent], config: FilterConfig) -> list[StatusEvent]:
    """Filter events based on configuration."""
    return [event for event in events if config.matches(event)]
