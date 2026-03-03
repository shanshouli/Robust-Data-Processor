import { Routes } from '@angular/router';
import { TenantLogDashboardPage } from './features/tenant-log-dashboard/tenant-log-dashboard.page';

export const routes: Routes = [
  {
    path: '',
    component: TenantLogDashboardPage
  },
  {
    path: '**',
    redirectTo: ''
  }
];
