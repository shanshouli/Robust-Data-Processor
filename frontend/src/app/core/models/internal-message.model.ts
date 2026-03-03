export type LogSource = 'json' | 'text';

export interface InternalMessage {
  tenant_id: string;
  log_id: string;
  source: LogSource;
  text: string;
  received_at: string;
}
