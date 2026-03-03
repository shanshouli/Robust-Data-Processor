import { ErrorHandler, Injectable } from '@angular/core';
import { MatSnackBar } from '@angular/material/snack-bar';

@Injectable()
export class GlobalErrorHandler implements ErrorHandler {
  constructor(private snackBar: MatSnackBar) {}

  handleError(error: unknown): void {
    console.error('Unhandled error', error);
    this.snackBar.open('Unexpected error occurred. Please try again.', 'Dismiss', {
      duration: 6000
    });
  }
}
