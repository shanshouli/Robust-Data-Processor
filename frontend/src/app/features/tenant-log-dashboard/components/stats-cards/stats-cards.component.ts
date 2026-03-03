import { ChangeDetectionStrategy, Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { IngestionStats } from '../../../../core/services/stats.service';
import { MetricCardComponent } from '../../../../shared/components/metric-card/metric-card.component';

@Component({
  selector: 'app-stats-cards',
  standalone: true,
  imports: [CommonModule, MatProgressBarModule, MetricCardComponent],
  templateUrl: './stats-cards.component.html',
  styleUrl: './stats-cards.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class StatsCardsComponent {
  @Input({ required: true }) stats!: IngestionStats;
  @Input() loading = false;
}
