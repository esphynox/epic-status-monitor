/**
 * Epic Games Status Bot - Cloudflare Worker
 * 
 * Handles:
 * - Webhook requests from Telegram (user commands)
 * - Cron triggers (status polling)
 * - Setup endpoints (webhook registration)
 */

import type { Env, TelegramUpdate, BotState, ParsedEvent } from './types';
import { fetchAllEvents } from './epic-status';
import { sendEventNotification, setWebhook } from './telegram';
import { handleMessage } from './commands';
import { getAllSubscriberIds, getSubscription, eventMatchesSubscription } from './subscriptions';

export default {
  /**
   * Handle HTTP requests (Telegram webhook + setup endpoints)
   */
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);

    // Setup endpoint: Register webhook with Telegram
    if (url.pathname === '/setup') {
      return handleSetup(request, env);
    }

    // Health check
    if (url.pathname === '/health') {
      return new Response('OK', { status: 200 });
    }

    // Telegram webhook endpoint
    if (url.pathname === '/webhook' && request.method === 'POST') {
      return handleWebhook(request, env);
    }

    // Manual trigger for testing
    if (url.pathname === '/poll' && request.method === 'POST') {
      await pollAndNotify(env);
      return new Response('Poll completed', { status: 200 });
    }

    return new Response('Not found', { status: 404 });
  },

  /**
   * Handle cron triggers (scheduled status polling)
   */
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(pollAndNotify(env));
  },
};

/**
 * Handle /setup endpoint - register webhook with Telegram
 */
async function handleSetup(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);
  const workerUrl = `${url.protocol}//${url.host}/webhook`;

  const success = await setWebhook(env.TELEGRAM_TOKEN, workerUrl, env.WEBHOOK_SECRET);

  if (success) {
    return new Response(`✅ Webhook registered: ${workerUrl}`, { status: 200 });
  } else {
    return new Response('❌ Failed to register webhook', { status: 500 });
  }
}

/**
 * Handle incoming Telegram webhook
 */
async function handleWebhook(request: Request, env: Env): Promise<Response> {
  // Verify webhook secret if configured
  if (env.WEBHOOK_SECRET) {
    const secret = request.headers.get('X-Telegram-Bot-Api-Secret-Token');
    if (secret !== env.WEBHOOK_SECRET) {
      return new Response('Unauthorized', { status: 401 });
    }
  }

  try {
    const update = await request.json() as TelegramUpdate;

    if (update.message) {
      await handleMessage(env, update.message);
    }

    return new Response('OK', { status: 200 });
  } catch (error) {
    console.error('Webhook error:', error);
    return new Response('Error processing update', { status: 500 });
  }
}

/**
 * Poll Epic status and send notifications to subscribers
 */
async function pollAndNotify(env: Env): Promise<void> {
  console.log('🕐 Starting Epic Games status check...');

  // Load current state
  const state = await loadState(env.STATE);

  // Fetch all events
  const events = await fetchAllEvents(true);
  console.log(`📊 Found ${events.length} events`);

  // Get all subscribers
  const subscriberIds = await getAllSubscriberIds(env.SUBSCRIPTIONS);
  console.log(`👥 ${subscriberIds.length} subscribers`);

  if (subscriberIds.length === 0) {
    console.log('No subscribers, skipping notifications');
    await saveState(env.STATE, state, events);
    return;
  }

  // Process each event
  let newCount = 0;
  let updateCount = 0;

  for (const event of events) {
    const isNew = !state.seenIds.includes(event.id);
    const isUpdated = !isNew && state.fingerprints[event.id] !== event.fingerprint;

    if (!isNew && !isUpdated) {
      continue; // Already notified, no changes
    }

    // Find matching subscribers for this event
    for (const chatId of subscriberIds) {
      const subscription = await getSubscription(env.SUBSCRIPTIONS, chatId);
      if (!subscription) continue;

      if (eventMatchesSubscription(event, subscription)) {
        const success = await sendEventNotification(
          env.TELEGRAM_TOKEN,
          chatId,
          event,
          isUpdated
        );

        if (success) {
          console.log(`✅ Notified ${chatId} about: ${event.name}`);
        }
      }
    }

    // Update state
    if (isNew) {
      state.seenIds.push(event.id);
      newCount++;
    }
    state.fingerprints[event.id] = event.fingerprint;
    if (isUpdated) updateCount++;
  }

  // Save updated state
  await saveState(env.STATE, state, events);

  console.log(`📈 Summary: ${newCount} new, ${updateCount} updated`);
}

/**
 * Load bot state from KV
 */
async function loadState(kv: KVNamespace): Promise<BotState> {
  const data = await kv.get('bot_state', 'json');
  if (data) {
    return data as BotState;
  }
  return {
    seenIds: [],
    fingerprints: {},
    lastChecked: new Date().toISOString(),
  };
}

/**
 * Save bot state to KV
 */
async function saveState(
  kv: KVNamespace,
  state: BotState,
  currentEvents: ParsedEvent[]
): Promise<void> {
  // Clean up old event IDs (keep last 100)
  const currentIds = new Set(currentEvents.map(e => e.id));
  
  // Keep IDs that are either current or in our recent history (max 100)
  const relevantIds = state.seenIds.filter(id => currentIds.has(id));
  const historicalIds = state.seenIds.filter(id => !currentIds.has(id)).slice(-50);
  
  state.seenIds = [...relevantIds, ...historicalIds];
  state.fingerprints = Object.fromEntries(
    Object.entries(state.fingerprints).filter(([id]) => state.seenIds.includes(id))
  );
  state.lastChecked = new Date().toISOString();

  await kv.put('bot_state', JSON.stringify(state));
}
