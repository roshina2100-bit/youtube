import { Injectable, signal, computed } from '@angular/core';
import { Router } from '@angular/router';

export interface User {
  id: string;
  email: string;
  name: string;
  roles: string[];
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private _user = signal<User | null>(null);
  private _token = signal<string | null>(null);

  readonly user = this._user.asReadonly();
  readonly token = this._token.asReadonly();
  readonly isAuthenticated = computed(() => !!this._token());

  constructor(private router: Router) {
    // Load from localStorage on init
    const storedToken = localStorage.getItem('auth_token');
    const storedUser = localStorage.getItem('auth_user');
    
    if (storedToken) {
      this._token.set(storedToken);
    }
    if (storedUser) {
      try {
        this._user.set(JSON.parse(storedUser));
      } catch {
        localStorage.removeItem('auth_user');
      }
    }
  }

  getToken(): string | null {
    return this._token();
  }

  login(token: string, user: User): void {
    this._token.set(token);
    this._user.set(user);
    localStorage.setItem('auth_token', token);
    localStorage.setItem('auth_user', JSON.stringify(user));
  }

  logout(): void {
    this._token.set(null);
    this._user.set(null);
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    this.router.navigate(['/login']);
  }

  hasRole(role: string): boolean {
    const user = this._user();
    return user?.roles.includes(role) ?? false;
  }
}