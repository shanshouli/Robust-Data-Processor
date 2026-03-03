import { Injectable, computed, effect, signal } from '@angular/core';
import { finalize } from 'rxjs/operators';
import { IngestFormat, IngestRequest } from '../../core/models/ingest-request.model';
import { InternalMessage } from '../../core/models/internal-message.model';
import { IngestService } from '../../core/services/ingest.service';
import { LogStreamService } from '../../core/services/log-stream.service';
import { IngestionStats, StatsService } from '../../core/services/stats.service';

const MAX_LOGS = 200;

@Injectable({ providedIn: 'root' })
export class TenantLogDashboardStore {
  private readonly tenantsList = ['acme', 'beta', 'gamma'];

  readonly tenants = signal<string[]>(this.tenantsList);
  readonly selectedTenant = signal<string>(this.tenantsList[0]);
  readonly logs = signal<InternalMessage[]>([]);
  readonly stats = signal<IngestionStats>({
    totalProcessed: 0,
    errorRate: 0,
    latencyMs: 0
  });
  readonly loading = signal<boolean>(true);
  readonly ingestLoading = signal<boolean>(false);
  readonly error = signal<string | null>(null);

  readonly lastUpdated = computed(() => this.logs()[0]?.received_at ?? null);

  constructor(
    private logStreamService: LogStreamService,
    private statsService: StatsService,
    private ingestService: IngestService
  ) {
    effect((onCleanup) => {
      const tenant = this.selectedTenant();
      this.loading.set(true);
      this.error.set(null);
      this.logs.set([]);

      const subscription = this.logStreamService.stream$(tenant).subscribe({
        next: (log) => {
          this.logs.update((current) => [log, ...current].slice(0, MAX_LOGS));
          this.loading.set(false);
        },
        error: () => {
          this.error.set('Live stream unavailable. Retrying shortly.');
          this.loading.set(false);
        }
      });

      onCleanup(() => subscription.unsubscribe());
    });

    effect((onCleanup) => {
      const tenant = this.selectedTenant();
      const subscription = this.statsService.stats$(tenant).subscribe({
        next: (stats) => this.stats.set(stats),
        error: () =>
          this.stats.set({
            totalProcessed: 0,
            errorRate: 0,
            latencyMs: 0
          })
      });

      onCleanup(() => subscription.unsubscribe());
    });
  }

  selectTenant(tenantId: string): void {
    if (tenantId && tenantId !== this.selectedTenant()) {
      this.selectedTenant.set(tenantId);
    }
  }

  ingest(request: IngestRequest, format: IngestFormat) {
    this.ingestLoading.set(true);
    return this.ingestService.ingest(request, format).pipe(
      finalize(() => this.ingestLoading.set(false))
    );
  }
}
