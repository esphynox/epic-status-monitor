/**
 * User subscription management with KV storage
 */

import type { Env, UserSubscription, ParsedEvent } from './types';

const IMPACT_LEVELS = ['none', 'minor', 'major', 'critical'] as const;

/**
 * Get a user's subscription
 */
export async function getSubscription(
  kv: KVNamespace,
  chatId: number
): Promise<UserSubscription | null> {
  const data = await kv.get(`sub:${chatId}`, 'json');
  return data as UserSubscription | null;
}

/**
 * Save a user's subscription
 */
export async function saveSubscription(
  kv: KVNamespace,
  chatId: number,
  subscription: Partial<UserSubscription>
): Promise<UserSubscription> {
  const existing = await getSubscription(kv, chatId);
  const now = new Date().toISOString();

  const updated: UserSubscription = {
    chatId,
    services: subscription.services ?? existing?.services ?? [],
    minImpact: subscription.minImpact ?? existing?.minImpact ?? 'none',
    eventTypes: subscription.eventTypes ?? existing?.eventTypes ?? 'all',
    createdAt: existing?.createdAt ?? now,
    updatedAt: now,
  };

  await kv.put(`sub:${chatId}`, JSON.stringify(updated));
  
  // Also add to subscriber index for efficient iteration
  await addToSubscriberIndex(kv, chatId);
  
  return updated;
}

/**
 * Delete a user's subscription
 */
export async function deleteSubscription(
  kv: KVNamespace,
  chatId: number
): Promise<void> {
  await kv.delete(`sub:${chatId}`);
  await removeFromSubscriberIndex(kv, chatId);
}

/**
 * Get all subscriber chat IDs
 */
export async function getAllSubscriberIds(kv: KVNamespace): Promise<number[]> {
  const index = await kv.get('subscriber_index', 'json');
  return (index as number[]) || [];
}

/**
 * Add chat ID to subscriber index
 */
async function addToSubscriberIndex(kv: KVNamespace, chatId: number): Promise<void> {
  const ids = await getAllSubscriberIds(kv);
  if (!ids.includes(chatId)) {
    ids.push(chatId);
    await kv.put('subscriber_index', JSON.stringify(ids));
  }
}

/**
 * Remove chat ID from subscriber index
 */
async function removeFromSubscriberIndex(kv: KVNamespace, chatId: number): Promise<void> {
  const ids = await getAllSubscriberIds(kv);
  const filtered = ids.filter(id => id !== chatId);
  await kv.put('subscriber_index', JSON.stringify(filtered));
}

/**
 * Check if an event matches a user's subscription filters
 */
export function eventMatchesSubscription(
  event: ParsedEvent,
  subscription: UserSubscription
): boolean {
  // Check event type filter
  if (subscription.eventTypes === 'incidents' && event.eventType === 'maintenance') {
    return false;
  }
  if (subscription.eventTypes === 'maintenance' && event.eventType === 'incident') {
    return false;
  }

  // Check impact level (for incidents only)
  if (event.eventType === 'incident' && subscription.minImpact !== 'none') {
    const eventImpactIdx = IMPACT_LEVELS.indexOf(event.impact as typeof IMPACT_LEVELS[number]);
    const minImpactIdx = IMPACT_LEVELS.indexOf(subscription.minImpact);
    if (eventImpactIdx < minImpactIdx) {
      return false;
    }
  }

  // Check services filter (empty = all services)
  if (subscription.services.length > 0) {
    const eventText = `${event.name} ${event.components?.map(c => c.name).join(' ') || ''}`.toLowerCase();
    const matched = subscription.services.some(service => 
      eventText.includes(service.toLowerCase())
    );
    if (!matched) {
      return false;
    }
  }

  return true;
}

/**
 * Get all subscriptions that match an event
 */
export async function getMatchingSubscriptions(
  kv: KVNamespace,
  event: ParsedEvent
): Promise<UserSubscription[]> {
  const subscriberIds = await getAllSubscriberIds(kv);
  const matches: UserSubscription[] = [];

  for (const chatId of subscriberIds) {
    const subscription = await getSubscription(kv, chatId);
    if (subscription && eventMatchesSubscription(event, subscription)) {
      matches.push(subscription);
    }
  }

  return matches;
}

/**
 * Format subscription for display
 */
export function formatSubscription(sub: UserSubscription): string {
  const lines: string[] = ['📋 <b>Your Subscription</b>', ''];

  if (sub.services.length === 0) {
    lines.push('🎮 Services: <i>All services</i>');
  } else {
    lines.push(`🎮 Services: ${sub.services.join(', ')}`);
  }

  lines.push(`⚡ Min Impact: ${sub.minImpact}`);
  lines.push(`📌 Event Types: ${sub.eventTypes}`);
  lines.push('');
  lines.push(`📅 Subscribed: ${sub.createdAt.slice(0, 10)}`);

  return lines.join('\n');
}
