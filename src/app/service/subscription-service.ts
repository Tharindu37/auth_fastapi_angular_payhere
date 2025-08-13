import { HttpClient } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment.development';

@Injectable({
  providedIn: 'root'
})
export class SubscriptionService {
  constructor(private http: HttpClient) { }

  getPlans(): Observable<any[]> {
    // return this.http.get<any[]>(`${environment.apiUrl}/plans`);
    return this.http.get<any[]>(`http://localhost:8000/plans`);
  }

  subscribe(formData: FormData): Observable<string> {
    // Backend returns HTML string that auto-submits to PayHere
    return this.http.post(`${environment.apiUrl}/subscribe`, formData, { responseType: 'text' });
  }
}
