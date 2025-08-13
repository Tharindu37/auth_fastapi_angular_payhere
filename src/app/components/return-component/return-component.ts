import { Component } from '@angular/core';

@Component({
  selector: 'app-return-component',
  imports: [],
  template: `
    <h2>Subscription Result</h2>
    <p>If your payment succeeded, the backend will display your API key on this page.</p>
    <p><em>Tip:</em> If you don't see the key yet, the webhook may not have reached your server. Try again after a moment.</p>
  `,
  styles: [`
    h2 { margin-bottom: 12px; }
    p { max-width: 600px; }
  `]
})
export class ReturnComponent {

}
