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
/filter fortnite - Only Fortnite updates
/filter incidents - Only incidents, no maintenance
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

<b>By service:</b>
/filter fortnite
/filter rocket league
/filter epic games store
/filter all (reset to all services)

<b>By event type:</b>
/filter incidents (no maintenance)
/filter maintenance (no incidents)
/filter events all (both)

<b>By impact (incidents only):</b>
/filter impact minor
/filter impact major
/filter impact critical

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
  const filterValue = args.slice(1).join(' ').toLowerCase();

  let message: string;

  switch (filterType) {
    case 'all':
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { services: [] });
      message = '✅ Now watching <b>all services</b>';
      break;

    case 'incidents':
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { eventTypes: 'incidents' });
      message = '✅ Now only receiving <b>incident</b> notifications (no maintenance)';
      break;

    case 'maintenance':
      await saveSubscription(env.SUBSCRIPTIONS, chatId, { eventTypes: 'maintenance' });
      message = '✅ Now only receiving <b>maintenance</b> notifications (no incidents)';
      break;

    case 'events':
      if (filterValue === 'all') {
        await saveSubscription(env.SUBSCRIPTIONS, chatId, { eventTypes: 'all' });
        message = '✅ Now receiving <b>all event types</b>';
      } else {
        message = '❓ Use: /filter events all';
      }
      break;

    case 'impact':
      if (['none', 'minor', 'major', 'critical'].includes(filterValue)) {
        await saveSubscription(env.SUBSCRIPTIONS, chatId, { 
          minImpact: filterValue as 'none' | 'minor' | 'major' | 'critical' 
        });
        message = `✅ Minimum impact set to <b>${filterValue}</b>`;
      } else {
        message = '❓ Use: /filter impact none|minor|major|critical';
      }
      break;

    default:
      // Assume it's a service name
      const serviceName = args.join(' ');
      const currentServices = subscription.services;
      
      // Toggle service: add if not present, keep if already there
      let newServices: string[];
      if (serviceName.toLowerCase() === 'all') {
        newServices = [];
      } else if (currentServices.length === 0) {
        // Was watching all, now just this one
        newServices = [serviceName];
      } else if (currentServices.map(s => s.toLowerCase()).includes(serviceName.toLowerCase())) {
        // Already watching, remove it
        newServices = currentServices.filter(s => s.toLowerCase() !== serviceName.toLowerCase());
        if (newServices.length === 0) {
          newServices = []; // Back to all
        }
      } else {
        // Add to list
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

<b>Commands:</b>
/start - Subscribe to updates
/unsubscribe - Stop receiving updates
/settings - View your subscription
/status - Check current Epic status
/filter - Customize what you receive
/help - Show this message

<b>Filter examples:</b>
/filter fortnite - Only Fortnite
/filter rocket league - Add Rocket League
/filter incidents - No maintenance alerts
/filter impact major - Only major+ incidents

<b>Links:</b>
🔗 status.epicgames.com
`.trim();

  await sendMessage(env.TELEGRAM_TOKEN, chatId, message);
}
