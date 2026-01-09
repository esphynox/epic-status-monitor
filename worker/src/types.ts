/**
 * Type definitions for Epic Status Bot
 */

// Cloudflare Worker environment bindings
export interface Env {
  STATE: KVNamespace;
  SUBSCRIPTIONS: KVNamespace;
  TELEGRAM_TOKEN: string;
  WEBHOOK_SECRET?: string;
}

// Epic Status API types
export interface StatusUpdate {
  id: string;
  status: string;
  body: string;
  created_at: string;
}

export interface Component {
  id: string;
  name: string;
  status: string;
}

export interface StatusEvent {
  id: string;
  name: string;
  status: string;
  impact: string;
  shortlink: string;
  created_at: string;
  updated_at: string;
  incident_updates: StatusUpdate[];
  components: Component[];
  scheduled_for?: string;
  scheduled_until?: string;
}

export type EventType = 'incident' | 'maintenance';

export interface ParsedEvent extends StatusEvent {
  eventType: EventType;
  fingerprint: string;
}

// State storage types
export interface BotState {
  seenIds: string[];
  fingerprints: Record<string, string>;
  lastChecked: string;
}

// Subscription types
export interface UserSubscription {
  chatId: number;
  services: string[];        // Empty = all services
  minImpact: 'none' | 'minor' | 'major' | 'critical';
  eventTypes: string[];      // ['incidents', 'maintenance'], empty or ['all'] = all
  createdAt: string;
  updatedAt: string;
}

// Telegram types
export interface TelegramUpdate {
  update_id: number;
  message?: TelegramMessage;
}

export interface TelegramMessage {
  message_id: number;
  from?: TelegramUser;
  chat: TelegramChat;
  date: number;
  text?: string;
}

export interface TelegramUser {
  id: number;
  first_name: string;
  last_name?: string;
  username?: string;
}

export interface TelegramChat {
  id: number;
  type: 'private' | 'group' | 'supergroup' | 'channel';
  title?: string;
  username?: string;
  first_name?: string;
}
