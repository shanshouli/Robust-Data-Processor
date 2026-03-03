import { ChangeDetectionStrategy, Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatSelectModule } from '@angular/material/select';

@Component({
  selector: 'app-tenant-filter',
  standalone: true,
  imports: [CommonModule, MatFormFieldModule, MatSelectModule],
  templateUrl: './tenant-filter.component.html',
  styleUrl: './tenant-filter.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class TenantFilterComponent {
  @Input({ required: true }) tenants: string[] = [];
  @Input({ required: true }) selected = '';
  @Output() selectedChange = new EventEmitter<string>();
}
