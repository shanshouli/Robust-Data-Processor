import { Injectable } from '@angular/core';
import { Observable, interval } from 'rxjs';
import { map } from 'rxjs/operators';
import { InternalMessage, LogSource } from '../models/internal-message.model';

const SOURCES: LogSource[] = ['json', 'text'];
const SAMPLE_MESSAGES = [
  'User authenticated successfully from 10.0.24.12',
  'Payment processor timeout, retry scheduled',
  'Webhook payload received and queued',
  'Anomalous request pattern detected for /ingest',
  'Token refresh completed for service account',
  'DLQ message rerouted for manual inspection',
  'Access policy mismatch on tenant boundary check'
];

@Injectable({ providedIn: 'root' })
export class LogStreamService {
  stream$(tenantId: string): Observable<InternalMessage> {
    return interval(1100).pipe(
      map((tick) => this.buildMessage(tenantId, tick))
    );
  }

  private buildMessage(tenantId: string, tick: number): InternalMessage {
    const source = SOURCES[tick % SOURCES.length];
    const text = SAMPLE_MESSAGES[tick % SAMPLE_MESSAGES.length];
    return {
      tenant_id: tenantId,
      log_id: `log-${tenantId}-${Date.now()}-${tick}`,
      source,
      text,
      received_at: new Date().toISOString()
    };
  }
}
