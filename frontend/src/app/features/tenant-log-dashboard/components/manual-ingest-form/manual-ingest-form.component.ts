import { ChangeDetectionStrategy, Component, EventEmitter, Input, OnChanges, Output, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatButtonModule } from '@angular/material/button';
import { MatRadioModule } from '@angular/material/radio';
import { MatIconModule } from '@angular/material/icon';
import { toSignal } from '@angular/core/rxjs-interop';
import { startWith } from 'rxjs/operators';
import { computed } from '@angular/core';

import { IngestFormat, IngestRequest } from '../../../../core/models/ingest-request.model';

export interface ManualIngestEvent {
  format: IngestFormat;
  payload: IngestRequest;
}

@Component({
  selector: 'app-manual-ingest-form',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatRadioModule,
    MatIconModule
  ],
  templateUrl: './manual-ingest-form.component.html',
  styleUrl: './manual-ingest-form.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush
})
export class ManualIngestFormComponent implements OnChanges {
  @Input({ required: true }) tenant = '';
  @Input() loading = false;
  @Output() submitIngest = new EventEmitter<ManualIngestEvent>();

  readonly form = this.fb.group({
    tenant_id: ['', Validators.required],
    log_id: [''],
    format: ['json' as IngestFormat, Validators.required],
    text: ['', [Validators.required, Validators.minLength(5)]]
  });

  private readonly textChanges = toSignal(
    this.form.controls.text.valueChanges.pipe(startWith(this.form.controls.text.value || '')),
    { initialValue: '' }
  );

  readonly charCount = computed(() => (this.textChanges() || '').length);

  constructor(private fb: FormBuilder) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['tenant']?.currentValue) {
      this.form.patchValue({ tenant_id: this.tenant }, { emitEvent: false });
    }
  }

  submit(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }

    const value = this.form.getRawValue();
    this.submitIngest.emit({
      format: value.format || 'json',
      payload: {
        tenant_id: value.tenant_id || this.tenant,
        log_id: value.log_id || undefined,
        text: value.text || '',
        source: value.format || 'json'
      }
    });

    this.form.patchValue({ log_id: '', text: '' }, { emitEvent: false });
  }
}
