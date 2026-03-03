import { Injectable } from '@angular/core';
import { Observable, interval } from 'rxjs';
import { map } from 'rxjs/operators';

export interface IngestionStats {
  totalProcessed: number;
  errorRate: number;
  latencyMs: number;
}

@Injectable({ providedIn: 'root' })
export class StatsService {
  stats$(tenantId: string): Observable<IngestionStats> {
    return interval(2000).pipe(
      map((tick) => this.buildStats(tenantId, tick))
    );
  }

  private buildStats(tenantId: string, tick: number): IngestionStats {
    const base = tenantId.charCodeAt(0) * 1000;
    const totalProcessed = base + tick * 27;
    const errorRate = Math.max(0.2, Math.min(4.5, (tick % 12) * 0.4 + 0.3));
    const latencyMs = 120 + (tick % 6) * 18 + (tenantId.length * 4);

    return {
      totalProcessed,
      errorRate: Number(errorRate.toFixed(2)),
      latencyMs
    };
  }
}
