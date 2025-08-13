import { Routes } from '@angular/router';
import { LoginComponent } from './components/login-component/login-component';
import { PlansComponent } from './components/plans-component/plans-component';
import { ReturnComponent } from './components/return-component/return-component';
import { ApiTestComponent } from './components/api-test-component/api-test-component';
import { authGuard } from './guards/auth-guard';

export const routes: Routes = [
    { path: '', redirectTo: 'login', pathMatch: 'full' },
    { path: 'login', component: LoginComponent },
    { path: 'plans', component: PlansComponent, canActivate: [authGuard] },
    { path: 'subscribe/return', component: ReturnComponent },
    { path: 'api-test', component: ApiTestComponent, canActivate: [authGuard] },
    { path: '**', redirectTo: 'login' },
];
