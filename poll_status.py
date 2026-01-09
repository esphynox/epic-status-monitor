#!/usr/bin/env python3
"""
Epic Games Status Monitor - Main Entry Point
Polls status.epicgames.com for incidents and scheduled maintenances,
then sends Telegram notifications.
"""

import argparse
import sys
from datetime import datetime, timezone

from src.epic_status import fetch_all_events
from src.filters import load_filter_config, filter_events
from src.state import JsonFileState
from src.notifiers import TelegramNotifier


def main() -> int:
    parser = argparse.ArgumentParser(description="Poll Epic Games status and send notifications")
    parser.add_argument("--dry-run", action="store_true", help="Print messages but still update state (for testing)")
    args = parser.parse_args()
    """Main polling function."""
    print(f"🕐 Starting Epic Games Status check at {datetime.now(timezone.utc).isoformat()}")

    # Load filter configuration
    filter_config = load_filter_config()
    if filter_config.services:
        print(f"🎯 Filtering for: {', '.join(filter_config.services)}")

    # Fetch current incidents + active/upcoming maintenances
    all_events = fetch_all_events(include_upcoming=True)
    
    # Apply filters
    events = filter_events(all_events, filter_config)
    
    total_incidents = sum(1 for e in all_events if e.is_incident)
    total_maintenance = sum(1 for e in all_events if e.is_maintenance)
    filtered_incidents = sum(1 for e in events if e.is_incident)
    filtered_maintenance = sum(1 for e in events if e.is_maintenance)
    
    print(f"📊 Found {total_incidents} incident(s), {total_maintenance} maintenance(s) total")
    if filter_config.services or filter_config.min_impact != "none":
        print(f"📋 After filtering: {filtered_incidents} incident(s), {filtered_maintenance} maintenance(s)")

    # Initialize state and notifier
    state = JsonFileState()
    notifier = TelegramNotifier()

    new_count = 0
    update_count = 0

    for event in events:
        event_type = "maintenance" if event.is_maintenance else "incident"
        
        if state.is_new_event(event):
            # New event
            print(f"🆕 New {event_type}: {event.name}")
            sent = notifier.send_new_event(event)
            if sent or args.dry_run:
                state.mark_seen(event)
                new_count += 1

        elif state.is_updated_event(event):
            # Existing event with updates
            print(f"🔄 Updated {event_type}: {event.name}")
            sent = notifier.send_event_update(event)
            if sent or args.dry_run:
                state.mark_seen(event)
                update_count += 1

    # Clean up resolved events and save state
    state.cleanup(events)
    state.save()

    # Summary
    print(f"\n📈 Summary:")
    print(f"   - New events notified: {new_count}")
    print(f"   - Updated events notified: {update_count}")
    print(f"   - Total tracked events: {state.tracked_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
