/**
 * Telegram Bot API client
 */

import type { ParsedEvent, UserSubscription } from './types';

const TELEGRAM_API = 'https://api.telegram.org/bot';

const STATUS_EMOJI: Record<string, string> = {
  // Incident statuses
  investigating: '🔍',
  identified: '🔎',
  monitoring: '👀',
  resolved: '✅',
  postmortem: '📝',
  // Maintenance statuses
  scheduled: '📅',
  in_progress: '🔧',
  verifying: '🔎',
  completed: '✅',
};

const IMPACT_EMOJI: Record<string, string> = {
  none: '⚪',
  minor: '🟡',
  major: '🟠',
  critical: '🔴',
  maintenance: '🔵',
};

/**
 * Format an event into a Telegram message
 */
export function formatEventMessage(event: ParsedEvent, isUpdate = false): string {
  const statusEmoji = STATUS_EMOJI[event.status] || '🚨';
  const isMaintenance = event.eventType === 'maintenance';
  const impactEmoji = isMaintenance 
    ? IMPACT_EMOJI.maintenance 
    : (IMPACT_EMOJI[event.impact] || '⚪');

  let header: string;
  if (isUpdate) {
    header = '🔄 UPDATE';
  } else if (isMaintenance) {
    header = '🔧 SCHEDULED MAINTENANCE';
  } else {
    header = '🚨 NEW INCIDENT';
  }

  const lines: string[] = [
    header,
    '',
    `${statusEmoji} <b>${escapeHtml(event.name)}</b>`,
    `Status: ${event.status.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}`,
  ];

  // Show impact for incidents only
  if (!isMaintenance) {
    lines.push(`Impact: ${impactEmoji} ${event.impact.charAt(0).toUpperCase() + event.impact.slice(1)}`);
  }

  // Show scheduled time for maintenance
  if (isMaintenance && event.scheduled_for) {
    const start = event.scheduled_for.slice(0, 16).replace('T', ' ');
    const end = event.scheduled_until?.slice(11, 16) || '';
    lines.push(`⏰ Scheduled: ${start}${end ? ` → ${end}` : ''} UTC`);
  }

  // Add latest update body
  const latestUpdate = event.incident_updates?.[0];
  if (latestUpdate?.body) {
    let body = latestUpdate.body;
    if (body.length > 500) {
      body = body.slice(0, 497) + '...';
    }
    lines.push('', `📋 <i>${escapeHtml(body)}</i>`);
  }

  // Add affected components
  const componentNames = event.components?.slice(0, 5).map(c => c.name) || [];
  if (componentNames.length > 0) {
    lines.push('', `🎮 Affected: ${componentNames.join(', ')}`);
  }

  // Add link
  if (event.shortlink) {
    lines.push('', `🔗 ${event.shortlink}`);
  }

  return lines.join('\n');
}

/**
 * Escape HTML special characters
 */
function escapeHtml(text: string): string {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}

/**
 * Send a message via Telegram API
 */
export async function sendMessage(
  token: string,
  chatId: number,
  text: string,
  parseMode: 'HTML' | 'Markdown' = 'HTML'
): Promise<boolean> {
  const url = `${TELEGRAM_API}${token}/sendMessage`;
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        chat_id: chatId,
        text,
        parse_mode: parseMode,
        disable_web_page_preview: true,
      }),
    });

    if (!response.ok) {
      const error = await response.text();
      console.error(`Telegram API error for chat ${chatId}:`, error);
      return false;
    }

    return true;
  } catch (error) {
    console.error(`Failed to send message to ${chatId}:`, error);
    return false;
  }
}

/**
 * Send event notification to a user
 */
export async function sendEventNotification(
  token: string,
  chatId: number,
  event: ParsedEvent,
  isUpdate = false
): Promise<boolean> {
  const message = formatEventMessage(event, isUpdate);
  return sendMessage(token, chatId, message);
}

/**
 * Set webhook URL for the bot
 */
export async function setWebhook(token: string, url: string, secret?: string): Promise<boolean> {
  const apiUrl = `${TELEGRAM_API}${token}/setWebhook`;
  
  const body: Record<string, string> = { url };
  if (secret) {
    body.secret_token = secret;
  }

  try {
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });

    const result = await response.json() as { ok: boolean; description?: string };
    if (!result.ok) {
      console.error('Failed to set webhook:', result.description);
      return false;
    }
    return true;
  } catch (error) {
    console.error('Error setting webhook:', error);
    return false;
  }
}

/**
 * Delete webhook (for switching to polling mode)
 */
export async function deleteWebhook(token: string): Promise<boolean> {
  const url = `${TELEGRAM_API}${token}/deleteWebhook`;
  
  try {
    const response = await fetch(url, { method: 'POST' });
    const result = await response.json() as { ok: boolean };
    return result.ok;
  } catch (error) {
    console.error('Error deleting webhook:', error);
    return false;
  }
}
