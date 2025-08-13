import { Component } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { SubscriptionService } from '../../service/subscription-service';
import { NgFor } from '@angular/common';

@Component({
  selector: 'app-plans-component',
  standalone: true,
  imports: [FormsModule, NgFor],
  template: `
    <h2>Available Plans</h2>

    <div *ngFor="let plan of plans" class="plan">
      <div>
        <strong>{{ plan.name }}</strong>
        <div>{{ plan.price }} {{ plan.currency }}</div>
        <small>{{ plan.recurrence }} • {{ plan.duration }}</small>
      </div>

      <form (ngSubmit)="subscribe(plan.id)" class="card">
        <input [(ngModel)]="firstName" name="firstName" placeholder="First Name" required />
        <input [(ngModel)]="lastName" name="lastName" placeholder="Last Name" required />
        <input [(ngModel)]="email" name="email" placeholder="Email" required />
        <button type="submit">Subscribe</button>
      </form>
    </div>
  `,
  styles: [
    `.plan{padding:12px;border:1px solid #eee;border-radius:8px;margin:10px 0}`,
    `.card{display:flex;gap:8px;max-width:640px;margin-top:8px}`,
  ]
})
export class PlansComponent {
plans: any[] = [];
  firstName = '';
  lastName = '';
  email = '';

  constructor(private subs: SubscriptionService) {}

  ngOnInit(): void {
    this.subs.getPlans().subscribe((data) => (this.plans = data));
  }

  subscribe(planId: number) {
    const form = new FormData();
    form.append('first_name', this.firstName);
    form.append('last_name', this.lastName);
    form.append('email', this.email);
    form.append('plan_id', String(planId));

    this.subs.subscribe(form).subscribe((html: string) => {
      // The backend returns an auto-submit HTML form to PayHere
      const w = window.open('', '_self');
      if (w) {
        w.document.open();
        w.document.write(html);
        w.document.close();
      } else {
        // Fallback: render in iframe
        const iframe = document.createElement('iframe');
        iframe.style.width = '100%';
        iframe.style.height = '600px';
        document.body.appendChild(iframe);
        if (iframe.contentDocument) {
          iframe.contentDocument.open();
          iframe.contentDocument.write(html);
          iframe.contentDocument.close();
        }
      }
    });
  }
}
