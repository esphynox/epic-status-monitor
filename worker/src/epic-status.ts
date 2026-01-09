/**
 * Epic Games Status API client
 */

import type { StatusEvent, ParsedEvent } from './types';

const BASE_URL = 'https://status.epicgames.com/api/v2';
const INCIDENTS_URL = `${BASE_URL}/incidents/unresolved.json`;
const MAINTENANCE_ACTIVE_URL = `${BASE_URL}/scheduled-maintenances/active.json`;
const MAINTENANCE_UPCOMING_URL = `${BASE_URL}/scheduled-maintenances/upcoming.json`;

/**
 * Generate a fingerprint for an event to detect updates
 */
function getFingerprint(event: StatusEvent): string {
  const latestUpdateId = event.incident_updates?.[0]?.id || '';
  return `${event.status}:${latestUpdateId}`;
}

/**
 * Parse raw event data into ParsedEvent
 */
function parseEvent(data: StatusEvent, eventType: 'incident' | 'maintenance'): ParsedEvent {
  return {
    ...data,
    eventType,
    fingerprint: getFingerprint(data),
  };
}

/**
 * Fetch events from a specific API endpoint
 */
async function fetchFromUrl(
  url: string,
  key: string,
  eventType: 'incident' | 'maintenance'
): Promise<ParsedEvent[]> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      console.error(`Failed to fetch ${url}: ${response.status}`);
      return [];
    }
    const data = await response.json() as Record<string, StatusEvent[]>;
    const events = data[key] || [];
    return events.map(e => parseEvent(e, eventType));
  } catch (error) {
    console.error(`Error fetching ${url}:`, error);
    return [];
  }
}

/**
 * Fetch unresolved incidents
 */
export async function fetchIncidents(): Promise<ParsedEvent[]> {
  return fetchFromUrl(INCIDENTS_URL, 'incidents', 'incident');
}

/**
 * Fetch active scheduled maintenances
 */
export async function fetchActiveMaintenances(): Promise<ParsedEvent[]> {
  return fetchFromUrl(MAINTENANCE_ACTIVE_URL, 'scheduled_maintenances', 'maintenance');
}

/**
 * Fetch upcoming scheduled maintenances
 */
export async function fetchUpcomingMaintenances(): Promise<ParsedEvent[]> {
  return fetchFromUrl(MAINTENANCE_UPCOMING_URL, 'scheduled_maintenances', 'maintenance');
}

/**
 * Fetch all active events (incidents + active maintenances)
 */
export async function fetchAllActiveEvents(): Promise<ParsedEvent[]> {
  const [incidents, maintenances] = await Promise.all([
    fetchIncidents(),
    fetchActiveMaintenances(),
  ]);
  return [...incidents, ...maintenances];
}

/**
 * Fetch all events including upcoming maintenances
 */
export async function fetchAllEvents(includeUpcoming = true): Promise<ParsedEvent[]> {
  const promises: Promise<ParsedEvent[]>[] = [
    fetchIncidents(),
    fetchActiveMaintenances(),
  ];
  
  if (includeUpcoming) {
    promises.push(fetchUpcomingMaintenances());
  }
  
  const results = await Promise.all(promises);
  return results.flat();
}

/**
 * Available Epic Games services (for help text)
 */
export const KNOWN_SERVICES = [
  'Fortnite',
  'Rocket League',
  'Fall Guys',
  'Epic Games Store',
  'Epic Online Services',
  'Unreal Engine',
  'UEFN',
  'Fab',
  'MetaHuman',
  'ArtStation',
  'Sketchfab',
];
