import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../service/auth-service';
import { Router } from '@angular/router';

@Component({
  selector: 'app-login-component',
  standalone: true,
  imports: [FormsModule],
  template: `
    <h2>Register</h2>
    <form (ngSubmit)="onRegister()" class="card">
      <input [(ngModel)]="email" name="email" placeholder="Email" required />
      <input [(ngModel)]="password" name="password" placeholder="Password" type="password" required />
      <button type="submit">Register</button>
    </form>

    <h2>Login</h2>
    <form (ngSubmit)="onLogin()" class="card">
      <input [(ngModel)]="email" name="email2" placeholder="Email" required />
      <input [(ngModel)]="password" name="password2" placeholder="Password" type="password" required />
      <button type="submit">Login</button>
    </form>
  `,
  styles: [`.card{display:flex;gap:8px;max-width:420px;margin:8px 0}`]
})
export class LoginComponent {
email = '';
  password = '';

  constructor(private auth: AuthService, private router: Router) {}

  onRegister(){
    this.auth.register(this.email, this.password).subscribe({
      next: () => alert('Registered! Now login.'),
      error: (e) => alert(e?.error?.detail || 'Register failed'),
    });
  }

  onLogin(){
    this.auth.login(this.email, this.password).subscribe({
      next: () => this.router.navigate(['/plans']),
      error: (e) => alert(e?.error?.detail || 'Login failed'),
    });
  }
}
