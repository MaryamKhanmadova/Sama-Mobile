import type { BackendCase } from './backend';
export type Message = { role: 'user' | 'assistant'; text: string };
export type Queue = 'unassigned' | 'ai' | 'agent' | 'waiting';
export type Action = 'refund' | 'apply_bundle' | 'explain_charge' | 'escalate';
export interface Decision { action: Action; amountAzn?: number; policy: { clause: string; text: string }; accountFact: { field: string; value: string }; confidence: number; guardrail: 'passed' | 'human_review'; explanation: string }
export interface Conversation { id: string; title: string; preview: string; time: string; status: 'open' | 'closed'; channel: 'text' | 'call'; messages: Message[]; queue?: Queue; priority?: 'normal' | 'high' | 'urgent'; language?: 'az' | 'ru' | 'en'; customer?: string; assignee?: string; createdAt?: string; waitingMinutes?: number; decision?: Decision; backendCase?: BackendCase; sessionId?: string }
export interface VolumePoint { date: string; incoming: number; resolved: number }
export interface DashboardData { conversations: Conversation[]; volume: VolumePoint[]; medianFirstResponseSeconds: number | null; resolvedToday: number; resolution: { ai: number; agent: number; handoff: number } }
export interface SubmitResponse { conversation: Conversation }
