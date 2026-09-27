import { Routes } from '@angular/router';

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/dashboard',
    pathMatch: 'full',
  },
  {
    path: 'dashboard',
    loadComponent: () => import('./features/dashboard/dashboard.component').then(m => m.DashboardComponent),
    title: 'Dashboard',
  },
  {
    path: 'projects',
    loadComponent: () => import('./features/projects/projects.component').then(m => m.ProjectsComponent),
    title: 'Projects',
  },
  {
    path: 'projects/new',
    loadComponent: () => import('./features/projects/project-create/project-create.component').then(m => m.ProjectCreateComponent),
    title: 'New Project',
  },
  {
    path: 'projects/:id',
    loadComponent: () => import('./features/projects/project-detail/project-detail.component').then(m => m.ProjectDetailComponent),
    title: 'Project Details',
  },
  {
    path: 'models',
    loadComponent: () => import('./features/models/models.component').then(m => m.ModelsComponent),
    title: 'Models',
  },
  {
    path: 'settings',
    loadComponent: () => import('./features/settings/settings.component').then(m => m.SettingsComponent),
    title: 'Settings',
  },
  {
    path: '**',
    redirectTo: '/dashboard',
  },
];