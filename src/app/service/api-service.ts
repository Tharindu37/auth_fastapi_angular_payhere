import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../environments/environment.development';

@Injectable({
  providedIn: 'root'
})
export class ApiService {
  constructor(private http: HttpClient) { }

  // Test 3rd-party consumer style using x-api-key
  getProtectedData(apiKey: string): Observable<any> {
    const headers = new HttpHeaders({ 'x-api-key': apiKey });
    // return this.http.get(`${environment.apiUrl}/v1/data`, { headers });
    return this.http.get(`http://localhost:8000/v1/data`, { headers });
  }
}
