import { Component } from '@angular/core';
import { ApiService } from '../../service/api-service';

@Component({
  selector: 'app-api-test-component',
  imports: [],
  standalone: true,
  template: `
    <h2>Test API</h2>
    <button (click)="callApi()">Call Protected API</button>
    <pre>{{ result }}</pre>
  `
})
export class ApiTestComponent {
  result = '';

  constructor(private api: ApiService) { }

  callApi() {
    const apiKey = 'FuRZkeRXgMR95pIUpqfV6bu8EWefYy5Op2z5svG6GjE';

    this.api.getProtectedData(apiKey).subscribe({
      next: (data) => {
        console.log('Protected Data:', data);
      },
      error: (err) => {
        console.error('Error fetching data:', err);
      }
    });

  }
}
