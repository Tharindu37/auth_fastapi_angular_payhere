import { NgIf } from '@angular/common';
import { Component, signal } from '@angular/core';
import { RouterLink, RouterOutlet } from '@angular/router';
import { AuthService } from './service/auth-service';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterLink, RouterOutlet, NgIf],
  template: `
    <nav class="nav">
      <a routerLink="/login">Login</a>
      <a routerLink="/plans">Plans</a>
      <a routerLink="/api-test">API Test</a>
      <span class="spacer"></span>
      <button *ngIf="auth.isLoggedIn()" (click)="logout()">Logout</button>
    </nav>
    <main class="container">
      <router-outlet></router-outlet>
    </main>
  `,
  styles: [`
    .nav { display:flex; gap:12px; padding:12px; background:#f7f7f7; align-items:center; }
    .spacer { flex:1; }
    .container { padding: 16px; }
    a { text-decoration:none; }
  `]
})
export class App {
  protected readonly title = signal('auth-fastapi');
  constructor(public auth: AuthService) {}
  logout(){ this.auth.logout(); }
}
