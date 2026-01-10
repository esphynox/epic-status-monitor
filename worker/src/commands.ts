/**
 * Telegram bot command handlers
 */

import type { Env, TelegramMessage } from './types';
import { sendMessage } from './telegram';
import { 
  getSubscription, 
  saveSubscription, 
  deleteSubscription,
  formatSubscription 
} from './subscriptions';
import { fetchAllEvents, KNOWN_SERVICES } from './epic-status';
import pkg from '../package.json';

const PACKAGE_VERSION = pkg.version ?? 'unknown';

/**
 * Handle incoming Telegram message
 */
export async function handleMessage(env: Env, message: TelegramMessage): Promise<void> {
  const chatId = message.chat.id;
  const text = message.text?.trim() || '';

  // Parse command
  const [command, ...args] = text.split(/\s+/);
  const lowerCommand = command.toLowerCase();

  switch (lowerCommand) {
    case '/start':
      await handleStart(env, chatId);
      break;
    case '/subscribe':
      await handleSubscribe(env, chatId, args);
      break;
    case '/unsubscribe':
      await handleUnsubscribe(env, chatId);
      break;
    case '/settings':
      await handleSettings(env, chatId);
      break;
    case '/filter':
      await handleFilter(env, chatId, args);
      break;
    case '/status':
      await handleStatus(env, chatId);
      break;
    case '/help':
      await handleHelp(env, chatId);
      break;
    default:
      if (text.startsWith('/')) {
        await sendMessage(env.TELEGRAM_TOKEN, chatId, 
          '❓ Unknown command. Use /help to see available commands.');
      }
  }
}

/**
 * /start - Welcome message and auto-subscribe
 */
async function handleStart(env: Env, chatId: number): Promise<void> {
  // Auto-subscribe with default settings (all services)
  await saveSubscription(env.SUBSCRIPTIONS, chatId, {});

  const message = `
🎮 <b>Epic Games Status Bot</b>

Welcome! You're now subscribed to Epic Games status updates.

<b>Default settings:</b>
• All services (Fortnite, Rocket League, etc.)
• All event types (incidents + maintenance)
• All impact levels

<b>Customize with:</b>
/filter service fortnite - Only Fortnite updates
/filter event incidents - Only incidents, no maintenance
/filter impact major - Only major+ incidents
/settings - View current settings
/help - All commands

You'll receive notifications when Epic Games services have issues or scheduled maintenance.
`.trim();

  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}

/**
 * /subscribe [services...] - Subscribe to updates
 */
async function handleSubscribe(env: Env, chatId: number, args: string[]): Promise<void> {
  const services = args.length > 0 ? args : [];
  
  await saveSubscription(env.SUBSCRIPTIONS, chatId, { services });

  let message: string;
  if (services.length === 0) {
    message = '✅ Subscribed to <b>all Epic Games services</b>!';
  } else {
    message = `✅ Subscribed to: <b>${services.join(', ')}</b>`;
  }

  message += '\n\nUse /settings to view your subscription or /filter to customize.';
  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}

/**
 * /unsubscribe - Remove subscription
 */
async function handleUnsubscribe(env: Env, chatId: number): Promise<void> {
  await deleteSubscription(env.SUBSCRIPTIONS, chatId);
  await sendMessage(env.TELEGRAM_TOKEN, chatId, 
    '👋 Unsubscribed from Epic Games status updates.\n\nUse /start to subscribe again.');
}

/**
 * /settings - View current subscription
 */
async function handleSettings(env: Env, chatId: number): Promise<void> {
  const subscription = await getSubscription(env.SUBSCRIPTIONS, chatId);

  if (!subscription) {
    await sendMessage(env.TELEGRAM_TOKEN, chatId,
      '❌ You\'re not subscribed yet.\n\nUse /start to subscribe.');
    return;
  }

  const message = formatSubscription(subscription);
  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}

/**
 * /filter <option> - Customize subscription
 */
async function handleFilter(env: Env, chatId: number, args: string[]): Promise<void> {
  if (args.length === 0) {
    const message = `
  🔧 <b>Filter Options</b>

  <b>By service (multiple allowed):</b>
  /filter service fortnite, rocket league
  /filter service all (reset to all services)

  <b>By event type (multiple allowed):</b>
  /filter event incidents, maintenance
  /filter event incidents (only incidents)
  /filter event maintenance (only maintenance)
  /filter event (all event types)

  <b>By impact (incidents only):</b>
  /filter impact minor
  /filter impact major
  /filter impact critical

  <b>Examples:</b>
  /filter service fortnite, epic games store
  /filter event incidents, maintenance
  /filter impact major

  <b>Known services:</b>
  ${KNOWN_SERVICES.join(', ')}
  `.trim();
    await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
    return;
  }

  const subscription = await getSubscription(env.SUBSCRIPTIONS, chatId);
  if (!subscription) {
    await sendMessage(env.TELEGRAM_TOKEN, chatId,
      '❌ You\'re not subscribed yet. Use /start first.');
    return;
  }

  const filterType = args[0].toLowerCase();
  const filterValue = args.slice(1).join(' ');
  let message: string;

  if (filterType === 'service') {
    // /filter service fortnite, rocket league
    const services = filterValue.split(',').map(s => s.trim()).filter(Boolean);
    if (services.length === 0 || (services.length === 1 && services[0].toLowerCase() === 'all')) {
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { services: [] });
      message = '✅ Now watching <b>all services</b>';
    } else {
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { services });
      message = `✅ Now watching: <b>${services.join(', ')}</b>`;
    }
  } else if (filterType === 'event') {
    // /filter event incidents, maintenance
    const eventTypes = filterValue.split(',').map(e => e.trim().toLowerCase()).filter(Boolean);
    const validTypes = ['incidents', 'maintenance'];
    const selected = eventTypes.filter(e => validTypes.includes(e));
    if (selected.length === 0 || selected.length === 2) {
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { eventTypes: 'all' });
      message = '✅ Now receiving <b>all event types</b>';
    } else {
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { eventTypes: selected[0] });
      message = `✅ Now only receiving <b>${selected[0]}</b> notifications`;
    }
  } else if (filterType === 'impact') {
    // /filter impact minor
    const impact = filterValue.trim().toLowerCase();
    if (['none', 'minor', 'major', 'critical'].includes(impact)) {
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { minImpact: impact as 'none' | 'minor' | 'major' | 'critical' });
      message = `✅ Minimum impact set to <b>${impact}</b>`;
    } else {
      message = '❓ Use: /filter impact none|minor|major|critical';
    }
  } else {
    // Fallback: treat as single service (legacy)
    const serviceName = args.join(' ');
    const currentServices = subscription.services;
    let newServices: string[];
    if (serviceName.toLowerCase() === 'all') {
      newServices = [];
    } else if (currentServices.length === 0) {
      newServices = [serviceName];
    } else if (currentServices.map(s => s.toLowerCase()).includes(serviceName.toLowerCase())) {
      newServices = currentServices.filter(s => s.toLowerCase() !== serviceName.toLowerCase());
      if (newServices.length === 0) {
        newServices = [];
      }
    } else {
      newServices = [...currentServices, serviceName];
    }
    await saveSubscription(env.SUBSCRIPTIONS, chatId, { services: newServices });
    if (newServices.length === 0) {
      message = '✅ Now watching <b>all services</b>';
    } else {
      message = `✅ Now watching: <b>${newServices.join(', ')}</b>`;
    }
  }

  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}

/**
 * /status - Show current Epic Games status
 */
async function handleStatus(env: Env, chatId: number): Promise<void> {
  await sendMessage(env.TELEGRAM_TOKEN, chatId, '🔄 Checking Epic Games status...');

  const events = await fetchAllEvents(true);
  
  if (events.length === 0) {
    await sendMessage(env.TELEGRAM_TOKEN, chatId,
      '✅ <b>All systems operational!</b>\n\nNo active incidents or scheduled maintenance.');
    return;
  }

  const incidents = events.filter(e => e.eventType === 'incident');
  const maintenances = events.filter(e => e.eventType === 'maintenance');

  let message = `📊 <b>Epic Games Status</b>\n`;
  message += `\n🚨 ${incidents.length} active incident(s)`;
  message += `\n🔧 ${maintenances.length} maintenance(s)\n`;

  for (const event of events.slice(0, 5)) {
    const emoji = event.eventType === 'incident' ? '🚨' : '🔧';
    message += `\n${emoji} <b>${event.name}</b>`;
    message += `\n   Status: ${event.status}`;
    if (event.shortlink) {
      message += `\n   ${event.shortlink}`;
    }
    message += '\n';
  }

  if (events.length > 5) {
    message += `\n<i>...and ${events.length - 5} more</i>`;
  }

  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}

/**
 * /help - Show help message
 */
async function handleHelp(env: Env, chatId: number): Promise<void> {
  const message = `
🎮 <b>Epic Games Status Bot</b>
<b>Version:</b> ${PACKAGE_VERSION}

<b>Commands:</b>
/start - Subscribe to updates
/unsubscribe - Stop receiving updates
/settings - View your subscription
/status - Check current Epic status
/filter - Customize what you receive
/help - Show this message

<b>Filter examples:</b>
/filter service fortnite - Only Fortnite
/filter service fortnite, rocket league - Multiple services
/filter event incidents - No maintenance alerts
/filter impact major - Only major+ incidents

<b>Links:</b>
🔗 status.epicgames.com
`.trim();

  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}
