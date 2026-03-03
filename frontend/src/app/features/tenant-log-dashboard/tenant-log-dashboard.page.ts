import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { CommonModule } from '@angular/common';

import { TenantLogDashboardStore } from './tenant-log-dashboard.store';
import { StatsCardsComponent } from './components/stats-cards/stats-cards.component';
import { LogStreamTableComponent } from './components/log-stream-table/log-stream-table.component';
import { ManualIngestEvent, ManualIngestFormComponent } from './components/manual-ingest-form/manual-ingest-form.component';
import { TenantFilterComponent } from './components/tenant-filter/tenant-filter.component';

@Component({
  selector: 'app-tenant-log-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    StatsCardsComponent,
    LogStreamTableComponent,
    ManualIngestFormComponent,
    TenantFilterComponent
  ],
  templateUrl: './tenant-log-dashboard.page.html',
  styleUrl: './tenant-log-dashboard.page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TenantLogDashboardPage {
  readonly store = inject(TenantLogDashboardStore);

  onManualIngest(event: ManualIngestEvent): void {
    this.store.ingest(event.payload, event.format).subscribe();
  }
}
