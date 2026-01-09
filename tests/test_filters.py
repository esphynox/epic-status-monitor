"""Tests for filters.py - Event filtering logic."""

import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

import pytest

from src.epic_status import Component, EventType, StatusEvent
from src.filters import FilterConfig, filter_events, load_filter_config


@pytest.mark.unit
class TestFilterConfigMatches:
    """Test FilterConfig.matches() method."""

    def test_matches_all_services_default(self, sample_incident):
        """Test default config matches all events."""
        config = FilterConfig()
        assert config.matches(sample_incident) is True

    def test_matches_single_service(self, sample_fortnite_incident, sample_incident):
        """Test filtering by single service."""
        config = FilterConfig(services=["Fortnite"])
        assert config.matches(sample_fortnite_incident) is True
        assert config.matches(sample_incident) is False  # Epic Games Store

    def test_matches_multiple_services(self, sample_fortnite_incident, sample_incident):
        """Test filtering by multiple services."""
        config = FilterConfig(services=["Fortnite", "Epic Games Store"])
        assert config.matches(sample_fortnite_incident) is True
        assert config.matches(sample_incident) is True

    def test_matches_service_case_insensitive(self, sample_fortnite_incident):
        """Test service matching is case-insensitive."""
        config = FilterConfig(services=["fortnite"])
        assert config.matches(sample_fortnite_incident) is True

    def test_matches_service_in_component_name(self, sample_incident):
        """Test matching service in component names."""
        config = FilterConfig(services=["Launcher"])
        assert config.matches(sample_incident) is True  # Has "Launcher" component

    def test_matches_impact_none(self, sample_incident):
        """Test min_impact='none' matches all."""
        config = FilterConfig(min_impact="none")
        assert config.matches(sample_incident) is True

    def test_matches_impact_minor(self, sample_incident):
        """Test min_impact='minor' filters correctly."""
        # sample_incident has impact="major"
        config = FilterConfig(min_impact="minor")
        assert config.matches(sample_incident) is True  # major >= minor

    def test_matches_impact_major(self, sample_incident):
        """Test min_impact='major' filters correctly."""
        config = FilterConfig(min_impact="major")
        assert config.matches(sample_incident) is True  # major >= major

        # Create a minor incident
        minor_incident = StatusEvent(
            id="minor",
            name="Minor Issue",
            status="investigating",
            impact="minor",
            shortlink="https://stspg.io/minor",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        assert config.matches(minor_incident) is False  # minor < major

    def test_matches_impact_critical(self):
        """Test min_impact='critical' filters correctly."""
        config = FilterConfig(min_impact="critical")
        
        major_incident = StatusEvent(
            id="major",
            name="Major Issue",
            status="investigating",
            impact="major",
            shortlink="https://stspg.io/major",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        assert config.matches(major_incident) is False  # major < critical

        critical_incident = StatusEvent(
            id="critical",
            name="Critical Issue",
            status="investigating",
            impact="critical",
            shortlink="https://stspg.io/critical",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        assert config.matches(critical_incident) is True

    def test_matches_impact_only_applies_to_incidents(self, sample_maintenance):
        """Test impact filtering doesn't apply to maintenance."""
        config = FilterConfig(min_impact="critical")
        # Maintenance should pass regardless of impact filter
        assert config.matches(sample_maintenance) is True

    def test_matches_event_type_all(self, sample_incident, sample_maintenance):
        """Test event_types='all' matches both."""
        config = FilterConfig(event_types="all")
        assert config.matches(sample_incident) is True
        assert config.matches(sample_maintenance) is True

    def test_matches_event_type_incidents_only(self, sample_incident, sample_maintenance):
        """Test event_types='incidents' only matches incidents."""
        config = FilterConfig(event_types="incidents")
        assert config.matches(sample_incident) is True
        assert config.matches(sample_maintenance) is False

    def test_matches_event_type_maintenance_only(self, sample_incident, sample_maintenance):
        """Test event_types='maintenance' only matches maintenance."""
        config = FilterConfig(event_types="maintenance")
        assert config.matches(sample_incident) is False
        assert config.matches(sample_maintenance) is True

    def test_matches_always_include_keywords(self, sample_incident):
        """Test always_include_keywords bypass other filters."""
        config = FilterConfig(
            services=["Fortnite"],  # Would normally exclude sample_incident
            always_include_keywords=["Epic Games Store"],
        )
        assert config.matches(sample_incident) is True

    def test_matches_exclude_keywords(self, sample_fortnite_incident):
        """Test exclude_keywords filter."""
        config = FilterConfig(
            services=["Fortnite"],
            exclude_keywords=["Matchmaking"],  # In the event name
        )
        assert config.matches(sample_fortnite_incident) is False

    def test_matches_exclude_keywords_case_insensitive(self, sample_fortnite_incident):
        """Test exclude_keywords is case-insensitive."""
        config = FilterConfig(
            services=["Fortnite"],
            exclude_keywords=["matchmaking"],  # lowercase
        )
        assert config.matches(sample_fortnite_incident) is False

    def test_matches_combined_filters(self):
        """Test combining multiple filters."""
        fortnite_major = StatusEvent(
            id="fn-major",
            name="Fortnite Major Issue",
            status="investigating",
            impact="major",
            shortlink="https://stspg.io/fn",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[Component(id="fn", name="Fortnite", status="degraded")],
            event_type=EventType.INCIDENT,
        )

        config = FilterConfig(
            services=["Fortnite"],
            min_impact="major",
            event_types="incidents",
        )
        assert config.matches(fortnite_major) is True

        # Should not match minor incident
        fortnite_minor = StatusEvent(
            id="fn-minor",
            name="Fortnite Minor Issue",
            status="investigating",
            impact="minor",
            shortlink="https://stspg.io/fn",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[Component(id="fn", name="Fortnite", status="degraded")],
            event_type=EventType.INCIDENT,
        )
        assert config.matches(fortnite_minor) is False

    def test_matches_unknown_impact_level(self):
        """Test handling of unknown impact levels."""
        unknown_impact = StatusEvent(
            id="unknown",
            name="Unknown Impact",
            status="investigating",
            impact="unknown_level",
            shortlink="https://stspg.io/test",
            created_at="2024-01-15T10:00:00Z",
            updated_at="2024-01-15T10:00:00Z",
            updates=[],
            components=[],
            event_type=EventType.INCIDENT,
        )
        
        config = FilterConfig(min_impact="major")
        # Unknown impact should be treated as lowest priority
        assert config.matches(unknown_impact) is False


@pytest.mark.unit
class TestLoadFilterConfig:
    """Test load_filter_config function."""

    def test_load_from_file(self, temp_config_file):
        """Test loading config from file."""
        config_data = {
            "services": ["Fortnite"],
            "min_impact": "major",
            "event_types": "incidents",
            "always_include_keywords": ["LEGO"],
            "exclude_keywords": ["test"],
        }
        temp_config_file.write_text(json.dumps(config_data))
        
        config = load_filter_config(temp_config_file)
        assert config.services == ["Fortnite"]
        assert config.min_impact == "major"
        assert config.event_types == "incidents"
        assert config.always_include_keywords == ["LEGO"]
        assert config.exclude_keywords == ["test"]

    def test_load_default_when_file_not_found(self):
        """Test default config when file doesn't exist."""
        config = load_filter_config(Path("/nonexistent/file.json"))
        assert config.services == []
        assert config.min_impact == "none"
        assert config.event_types == "all"

    def test_load_default_when_no_path(self, clear_env_vars, monkeypatch):
        """Test default config when no path provided and no defaults exist."""
        clear_env_vars("CONFIG_FILE", "WATCH_SERVICES")
        monkeypatch.setattr(Path, "exists", lambda self: False)
        
        config = load_filter_config()
        assert config.services == []
        assert config.min_impact == "none"

    def test_load_from_env_var_watch_services(self, mock_env_vars, clear_env_vars):
        """Test loading services from WATCH_SERVICES env var."""
        clear_env_vars("CONFIG_FILE")
        mock_env_vars(WATCH_SERVICES="Fortnite, Rocket League, Epic Games Store")
        
        config = load_filter_config()
        assert config.services == ["Fortnite", "Rocket League", "Epic Games Store"]
        assert config.min_impact == "none"  # Defaults

    def test_load_from_env_var_config_file(self, temp_config_file, mock_env_vars):
        """Test loading from CONFIG_FILE env var."""
        config_data = {"services": ["FromEnvFile"]}
        temp_config_file.write_text(json.dumps(config_data))
        mock_env_vars(CONFIG_FILE=str(temp_config_file))
        
        config = load_filter_config()
        assert config.services == ["FromEnvFile"]

    def test_load_invalid_json(self, temp_config_file):
        """Test handling of invalid JSON in config file."""
        temp_config_file.write_text("invalid json{")
        
        config = load_filter_config(temp_config_file)
        # Should return defaults on error
        assert config.services == []
        assert config.min_impact == "none"

    def test_load_partial_config(self, temp_config_file):
        """Test loading config with missing fields."""
        temp_config_file.write_text(json.dumps({"services": ["Fortnite"]}))
        
        config = load_filter_config(temp_config_file)
        assert config.services == ["Fortnite"]
        assert config.min_impact == "none"  # Default
        assert config.event_types == "all"  # Default


@pytest.mark.unit
class TestFilterEvents:
    """Test filter_events function."""

    def test_filter_events_all_match(self, sample_incident, sample_maintenance):
        """Test filtering when all events match."""
        config = FilterConfig()
        events = [sample_incident, sample_maintenance]
        
        filtered = filter_events(events, config)
        assert len(filtered) == 2

    def test_filter_events_some_match(self, sample_incident, sample_fortnite_incident):
        """Test filtering when some events match."""
        config = FilterConfig(services=["Fortnite"])
        events = [sample_incident, sample_fortnite_incident]
        
        filtered = filter_events(events, config)
        assert len(filtered) == 1
        assert filtered[0].id == "fortnite-incident"

    def test_filter_events_none_match(self, sample_incident):
        """Test filtering when no events match."""
        config = FilterConfig(services=["Unreal Engine"])
        events = [sample_incident]
        
        filtered = filter_events(events, config)
        assert len(filtered) == 0

    def test_filter_events_empty_list(self):
        """Test filtering empty event list."""
        config = FilterConfig()
        filtered = filter_events([], config)
        assert filtered == []
