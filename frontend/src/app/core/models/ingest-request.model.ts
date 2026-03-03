import { LogSource } from './internal-message.model';

export interface IngestRequest {
  tenant_id: string;
  log_id?: string;
  text: string;
  source: LogSource;
}

export type IngestFormat = 'json' | 'text';
