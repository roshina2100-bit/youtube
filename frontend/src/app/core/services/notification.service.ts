import { Injectable, signal, computed } from '@angular/core';
import { MatSnackBar, MatSnackBarConfig } from '@angular/material/snack-bar';

export interface Notification {
  id: string;
  message: string;
  type: 'success' | 'error' | 'warning' | 'info';
  timestamp: Date;
  action?: string;
}

@Injectable({
  providedIn: 'root',
})
export class NotificationService {
  private _notifications = signal<Notification[]>([]);
  readonly notifications = this._notifications.asReadonly();
  readonly unreadCount = computed(() => this._notifications().filter(n => !n.action).length);

  constructor(private snackBar: MatSnackBar) {}

  showSuccess(message: string, action?: string): void {
    this.show(message, 'success', action);
  }

  showError(message: string, action?: string): void {
    this.show(message, 'error', action);
  }

  showWarning(message: string, action?: string): void {
    this.show(message, 'warning', action);
  }

  showInfo(message: string, action?: string): void {
    this.show(message, 'info', action);
  }

  private show(message: string, type: Notification['type'], action?: string): void {
    const notification: Notification = {
      id: crypto.randomUUID(),
      message,
      type,
      timestamp: new Date(),
      action,
    };

    this._notifications.update(notifications => [...notifications, notification]);

    // Show snackbar
    const config: MatSnackBarConfig = {
      duration: type === 'error' ? 8000 : 5000,
      horizontalPosition: 'end',
      verticalPosition: 'bottom',
      panelClass: [`snackbar-${type}`],
    };

    this.snackBar.open(message, action || 'Dismiss', config);
  }

  dismiss(notificationId: string): void {
    this._notifications.update(notifications => 
      notifications.filter(n => n.id !== notificationId)
    );
  }

  clearAll(): void {
    this._notifications.set([]);
  }
}