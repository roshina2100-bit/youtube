import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatListModule } from '@angular/material/list';
import { RouterModule } from '@angular/router';

import { ApiService } from '@core/services/api.service';
import { ProjectSummary, ProjectStatus } from '@shared/models/project.model';
import { Job, JobStatus, JobType } from '@shared/models/job.model';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    RouterModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressBarModule,
    MatChipsModule,
    MatDividerModule,
    MatListModule,
  ],
  template: `
    <div class="dashboard">
      <header class="dashboard-header">
        <h1>Dashboard</h1>
        <a routerLink="/projects/new" class="btn-primary">
          <mat-icon>add</mat-icon>
          New Project
        </a>
      </header>

      <section class="stats-grid">
        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon primary">
              <mat-icon>folder</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ totalProjects() }}</span>
              <span class="stat-label">Total Projects</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon accent">
              <mat-icon>play_circle</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ inProgressProjects() }}</span>
              <span class="stat-label">In Progress</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon success">
              <mat-icon>check_circle</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ completedProjects() }}</span>
              <span class="stat-label">Completed</span>
            </div>
          </mat-card-content>
        </mat-card>

        <mat-card class="stat-card">
          <mat-card-content>
            <div class="stat-icon warning">
              <mat-icon>schedule</mat-icon>
            </div>
            <div class="stat-info">
              <span class="stat-value">{{ activeJobs() }}</span>
              <span class="stat-label">Active Jobs</span>
            </div>
          </mat-card-content>
        </mat-card>
      </section>

      <section class="recent-projects">
        <div class="section-header">
          <h2>Recent Projects</h2>
          <a routerLink="/projects" class="view-all">View All</a>
        </div>

        @if (recentProjects().length === 0) {
          <mat-card class="empty-state">
            <mat-card-content>
              <mat-icon>folder_open</mat-icon>
              <h3>No projects yet</h3>
              <p>Create your first project to get started</p>
              <a routerLink="/projects/new" class="btn-primary">
                <mat-icon>add</mat-icon>
                Create Project
              </a>
            </mat-card-content>
          </mat-card>
        } @else {
          <div class="projects-list">
            @for (project of recentProjects(); track project.project_id) {
              <mat-card class="project-card" [routerLink]="['/projects', project.project_id]">
                <mat-card-content>
                  <div class="project-header">
                    <div class="project-info">
                      <h3>{{ project.name }}</h3>
                      <p class="project-description">{{ project.description || 'No description' }}</p>
                    </div>
                    <mat-chip-set>
                      <mat-chip [class]="'status-' + project.status">{{ project.status | titlecase }}</mat-chip>
                    </mat-chip-set>
                  </div>

                  <mat-divider></mat-divider>

                  <div class="project-meta">
                    <div class="meta-item">
                      <mat-icon>translate</mat-icon>
                      <span>{{ project.target_languages.length }} languages</span>
                    </div>
                    <div class="meta-item">
                      <mat-icon>timeline</mat-icon>
                      <span>{{ project.current_stage | titlecase }}</span>
                    </div>
                    <div class="meta-item">
                      <mat-icon>analytics</mat-icon>
                      <span>{{ project.progress_percent.toFixed(0) }}% complete</span>
                    </div>
                  </div>

                  <mat-progress-bar 
                    mode="determinate" 
                    [value]="project.progress_percent"
                    class="progress-bar">
                  </mat-progress-bar>
                </mat-card-content>
              </mat-card>
            }
          </div>
        }
      </section>

      <section class="recent-activity">
        <div class="section-header">
          <h2>Recent Activity</h2>
        </div>

        @if (recentJobs().length === 0) {
          <mat-card class="empty-state">
            <mat-card-content>
              <mat-icon>history</mat-icon>
              <h3>No recent activity</h3>
              <p>Job activity will appear here</p>
            </mat-card-content>
          </mat-card>
        } @else {
          <mat-card class="activity-list">
            <mat-list>
              @for (job of recentJobs(); track job.job_id) {
                <mat-list-item class="activity-item">
                  <div matListItemIcon class="activity-icon" [class]="'status-' + job.status">
                    <mat-icon>{{ getJobIcon(job.type) }}</mat-icon>
                  </div>
                  <div matListItemTitle>{{ getJobTitle(job.type) }}</div>
                  <div matListItemLine>{{ job.project_id | slice:0:8 }}... • {{ job.current_step || 'Queued' }}</div>
                  <div matListItemMeta>
                    <mat-chip [class]="'status-' + job.status" class="small-chip">
                      {{ job.status | titlecase }}
                    </mat-chip>
                    @if (job.progress > 0 && job.status === 'running') {
                      <mat-progress-bar mode="determinate" [value]="job.progress" class="mini-progress"></mat-progress-bar>
                    }
                  </div>
                </mat-list-item>
                <mat-divider [inset]="true"></mat-divider>
              }
            </mat-list>
          </mat-card>
        }
      </section>
    </div>
  `,
  styles: [`
    .dashboard {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .dashboard-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      flex-wrap: wrap;
      gap: 16px;
    }

    .dashboard-header h1 {
      margin: 0;
      font-size: 2rem;
      font-weight: 600;
    }

    .stats-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
    }

    .stat-card {
      background: white;
    }

    .stat-card mat-card-content {
      display: flex;
      align-items: center;
      gap: 16px;
      padding: 20px;
    }

    .stat-icon {
      width: 48px;
      height: 48px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 24px;
    }

    .stat-icon.primary { background: #e3f2fd; color: #1565c0; }
    .stat-icon.accent { background: #fff3e0; color: #e65100; }
    .stat-icon.success { background: #e8f5e9; color: #2e7d32; }
    .stat-icon.warning { background: #f3e5f5; color: #7b1fa2; }

    .stat-info {
      display: flex;
      flex-direction: column;
    }

    .stat-value {
      font-size: 1.75rem;
      font-weight: 700;
      line-height: 1;
    }

    .stat-label {
      font-size: 0.875rem;
      color: #666;
    }

    .section-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;
    }

    .section-header h2 {
      margin: 0;
      font-size: 1.25rem;
      font-weight: 600;
    }

    .view-all {
      color: #3f51b5;
      text-decoration: none;
      font-weight: 500;
      font-size: 0.875rem;
    }

    .view-all:hover {
      text-decoration: underline;
    }

    .empty-state {
      text-align: center;
      padding: 48px 24px;
    }

    .empty-state mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #999;
      margin-bottom: 16px;
    }

    .empty-state h3 {
      margin: 0 0 8px;
      color: #333;
    }

    .empty-state p {
      margin: 0 0 24px;
      color: #666;
    }

    .projects-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .project-card {
      cursor: pointer;
      transition: box-shadow 0.2s ease, transform 0.2s ease;
    }

    .project-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
      transform: translateY(-2px);
    }

    .project-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      margin-bottom: 12px;
    }

    .project-info h3 {
      margin: 0 0 4px;
      font-size: 1.125rem;
      font-weight: 600;
    }

    .project-description {
      margin: 0;
      color: #666;
      font-size: 0.875rem;
    }

    .project-meta {
      display: flex;
      gap: 16px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .meta-item {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: 0.8125rem;
      color: #666;
    }

    .meta-item mat-icon {
      font-size: 18px;
      width: 18px;
      height: 18px;
    }

    .progress-bar {
      margin-top: 8px;
    }

    .activity-list mat-list {
      padding: 0;
    }

    .activity-item {
      padding: 12px 16px;
      border-radius: 8px;
      transition: background 0.2s ease;
    }

    .activity-item:hover {
      background: #f5f5f5;
    }

    .activity-icon {
      width: 40px;
      height: 40px;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .activity-icon.status-running { background: #e3f2fd; color: #1565c0; }
    .activity-icon.status-completed { background: #e8f5e9; color: #2e7d32; }
    .activity-icon.status-failed { background: #ffebee; color: #c62828; }
    .activity-icon.status-queued { background: #f5f5f5; color: #757575; }
    .activity-icon.status-cancelled { background: #fafafa; color: #9e9e9e; }

    .mini-progress {
      width: 100px;
      height: 4px;
    }

    .small-chip {
      font-size: 0.6875rem;
      height: 20px;
    }

    @media (max-width: 768px) {
      .dashboard-header {
        flex-direction: column;
        align-items: flex-start;
      }

      .project-meta {
        flex-direction: column;
        gap: 8px;
      }
    }
  `],
})
export class DashboardComponent implements OnInit {
  projects = signal<ProjectSummary[]>([]);
  jobs = signal<Job[]>([]);
  loading = signal(false);

  totalProjects = computed(() => this.projects().length);
  inProgressProjects = computed(() => this.projects().filter(p => p.status === 'in_progress').length);
  completedProjects = computed(() => this.projects().filter(p => p.status === 'completed').length);
  activeJobs = computed(() => this.jobs().filter(j => j.status === 'running' || j.status === 'queued').length);

  recentProjects = computed(() => 
    this.projects()
      .sort((a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime())
      .slice(0, 5)
  );

  recentJobs = computed(() => 
    this.jobs()
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())
      .slice(0, 10)
  );

  constructor(private apiService: ApiService) {}

  ngOnInit(): void {
    this.loadData();
  }

  loadData(): void {
    this.loading.set(true);
    
    this.apiService.getProjects(undefined, 20).subscribe({
      next: (response) => {
        this.projects.set(response.projects);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });

    // Get recent jobs from all projects (simplified - would need project context)
    // For now, we'll skip this or implement a global jobs endpoint
  }

  getJobIcon(type: JobType): string {
    const icons: Record<string, string> = {
      'story_analysis': 'psychology',
      'character_extraction': 'person',
      'character_image_gen': 'image',
      'scene_generation': 'movie',
      'image_generation': 'image',
      'video_generation': 'videocam',
      'translation': 'translate',
      'tts_generation': 'record_voice_over',
      'music_generation': 'music_note',
      'sfx_generation': 'volume_up',
      'final_render': 'movie_creation',
    };
    return icons[type] || 'settings';
  }

  getJobTitle(type: JobType): string {
    const titles: Record<string, string> = {
      'story_analysis': 'Story Analysis',
      'character_extraction': 'Character Extraction',
      'character_prompt_gen': 'Character Prompt Generation',
      'character_image_gen': 'Character Image Generation',
      'scene_generation': 'Scene Generation',
      'scene_prompt_gen': 'Scene Prompt Generation',
      'image_generation': 'Image Generation',
      'video_generation': 'Video Generation',
      'translation': 'Translation',
      'semantic_review': 'Semantic Review',
      'tts_generation': 'TTS Generation',
      'music_generation': 'Music Generation',
      'sfx_generation': 'SFX Generation',
      'audio_mixing': 'Audio Mixing',
      'silent_master': 'Silent Master Generation',
      'final_render': 'Final Render',
      'export': 'Project Export',
    };
    return titles[type] || type;
  }
}