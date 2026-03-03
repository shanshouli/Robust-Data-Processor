import { ChangeDetectionStrategy, Component, Input, OnChanges } from '@angular/core';
import { CommonModule, DatePipe } from '@angular/common';
import { MatTableDataSource, MatTableModule } from '@angular/material/table';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatChipsModule } from '@angular/material/chips';
import { MatIconModule } from '@angular/material/icon';

import { InternalMessage } from '../../../../core/models/internal-message.model';

@Component({
  selector: 'app-log-stream-table',
  standalone: true,
  imports: [
    CommonModule,
    DatePipe,
    MatTableModule,
    MatProgressSpinnerModule,
    MatChipsModule,
    MatIconModule
  ],
  templateUrl: './log-stream-table.component.html',
  styleUrl: './log-stream-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class LogStreamTableComponent implements OnChanges {
  @Input() logs: InternalMessage[] = [];
  @Input() loading = false;
  @Input() lastUpdated: string | null = null;
  @Input() error: string | null = null;

  readonly displayedColumns = ['tenant', 'logId', 'source', 'text', 'receivedAt'];
  readonly dataSource = new MatTableDataSource<InternalMessage>();

  ngOnChanges(): void {
    this.dataSource.data = this.logs;
  }
}
