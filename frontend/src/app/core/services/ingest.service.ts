import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';
import { IngestFormat, IngestRequest } from '../models/ingest-request.model';

@Injectable({ providedIn: 'root' })
export class IngestService {
  private readonly ingestUrl = `${environment.apiBaseUrl}/ingest`;

  constructor(private http: HttpClient) {}

  ingest(request: IngestRequest, format: IngestFormat): Observable<void> {
    if (format === 'text') {
      const headers = new HttpHeaders({
        'Content-Type': 'text/plain',
        'X-Tenant-ID': request.tenant_id
      });
      return this.http.post<void>(this.ingestUrl, request.text, { headers });
    }

    const headers = new HttpHeaders({
      'Content-Type': 'application/json'
    });
    return this.http.post<void>(
      this.ingestUrl,
      {
        tenant_id: request.tenant_id,
        log_id: request.log_id || undefined,
        text: request.text
      },
      { headers }
    );
  }
}
