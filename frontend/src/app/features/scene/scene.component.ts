import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatTabsModule } from '@angular/material/tabs';
import { MatProgressBarModule } from '@angular/material/progress-bar';

import { ApiService } from '@core/services/api.service';
import { NotificationService } from '@core/services/notification.service';

interface Scene {
  scene_id: string;
  act_id: string;
  order: number;
  title: string;
  duration_seconds: number;
  status: string;
  current_version: string;
  characters: string[];
  location_id: string;
  visual_style: string;
  has_video: boolean;
  has_audio: boolean;
}

interface SceneDetail {
  scene_id: string;
  version: string;
  act_id: string;
  order: number;
  title: string;
  duration_seconds: number;
  source_segments: string[];
  narration: string;
  dialogue: any[];
  characters: any[];
  location: any;
  action: string;
  emotion: string;
  camera: any;
  lens: any;
  framing: string;
  movement: string;
  lighting: any;
  atmosphere: string;
  props: string[];
  environment: string;
  visual_style: string;
  music: any;
  sound_effects: any[];
  prompts: any;
  images: string[];
  video_path: string | null;
  audio_paths: Record<string, string>;
}

@Component({
  selector: 'app-scene',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatChipsModule,
    MatDividerModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatExpansionModule,
    MatSlideToggleModule,
    MatTabsModule,
    MatProgressBarModule,
  ],
  template: `
    <div class="scene-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Scenes</h1>
          <p class="subtitle">Manage cinematic scenes, prompts, and generation</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="generateScenes()" [disabled]="generatingScenes()">
            @if (generatingScenes()) {
              <mat-spinner diameter="20"></mat-spinner>
              Generating...
            } @else {
              <mat-icon>movie</mat-icon>
              Generate Scenes
            }
          </button>
          <button mat-button (click)="generateSilentMaster()" [disabled]="generatingMaster()">
            @if (generatingMaster()) {
              <mat-spinner diameter="16"></mat-spinner>
              Silent Master
            } @else {
              <mat-icon>movie_creation</mat-icon>
              Silent Master
            }
          </button>
        </div>
      </header>

      @if (scenes().length === 0 && !loading()) {
        <mat-card class="empty-state">
          <mat-card-content>
            <mat-icon>movie</mat-icon>
            <h3>No scenes yet</h3>
            <p>Generate scenes from the story analysis to get started</p>
            <button mat-raised-button color="primary" (click)="generateScenes()">
              <mat-icon>movie</mat-icon>
              Generate Scenes
            </button>
          </mat-card-content>
        </mat-card>
      } @else {
        <div class="scenes-list">
          @for (scene of scenes(); track scene.scene_id) {
            <mat-card class="scene-card" [class.has-video]="scene.has_video">
              <mat-card-header>
                <mat-card-title>
                  <span class="scene-order">Scene {{ scene.order }}</span>
                  {{ scene.title }}
                </mat-card-title>
                <mat-card-subtitle>
                  Act {{ scene.act_id }} • {{ formatDuration(scene.duration_seconds) }} • {{ scene.status | titlecase }}
                </mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <div class="scene-meta">
                  <span><mat-icon>people</mat-icon> {{ scene.characters.length }} characters</span>
                  <span><mat-icon>location_on</mat-icon> {{ scene.location_id }}</span>
                  <span><mat-icon>palette</mat-icon> {{ scene.visual_style }}</span>
                </div>
                <div class="scene-status">
                  <mat-chip [class]="'status-' + scene.status">{{ scene.status | titlecase }}</mat-chip>
                  @if (scene.has_video) {
                    <mat-chip color="primary">Video Ready</mat-chip>
                  }
                  @if (scene.has_audio) {
                    <mat-chip color="accent">Audio Ready</mat-chip>
                  }
                </div>
              </mat-card-content>
              <mat-card-actions>
                <button mat-button [routerLink]="['/projects', projectId(), 'scenes', scene.scene_id]">
                  <mat-icon>visibility</mat-icon>
                  View Details
                </button>
                <button mat-button (click)="generatePrompts(scene.scene_id)" [disabled]="generatingPrompts(scene.scene_id)">
                  <mat-icon>auto_awesome</mat-icon>
                  Prompts
                </button>
                <button mat-button (click)="generateImage(scene.scene_id)" [disabled]="generatingImage(scene.scene_id)">
                  <mat-icon>image</mat-icon>
                  Image
                </button>
                <button mat-button (click)="generateVideo(scene.scene_id)" [disabled]="generatingVideo(scene.scene_id)">
                  <mat-icon>videocam</mat-icon>
                  Video
                </button>
              </mat-card-actions>
            </mat-card>
          }
        </div>

        <div class="master-section">
          <mat-card>
            <mat-card-header>
              <mat-card-title>Silent Master Video</mat-card-title>
            </mat-card-header>
            <mat-card-content>
              @if (silentMaster()) {
                <div class="master-info">
                  <mat-chip color="primary">Ready</mat-chip>
                  <span>{{ silentMaster() }}</span>
                  <button mat-button (click)="regenerateSilentMaster()">
                    <mat-icon>refresh</mat-icon>
                    Regenerate
                  </button>
                </div>
              } @else {
                <div class="master-empty">
                  <mat-icon>movie_creation</mat-icon>
                  <p>No silent master generated yet</p>
                  <button mat-raised-button color="primary" (click)="generateSilentMaster()">
                    <mat-icon>movie_creation</mat-icon>
                    Generate Silent Master
                  </button>
                </div>
              }
            </mat-card-content>
          </mat-card>
        </div>
      }
    </div>
  `,
  styles: [`
    .scene-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .page-header {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      flex-wrap: wrap;
      gap: 16px;
    }

    .page-header h1 {
      margin: 0 0 4px;
      font-size: 2rem;
      font-weight: 600;
    }

    .subtitle {
      margin: 0;
      color: #666;
    }

    .header-actions {
      display: flex;
      gap: 12px;
    }

    .scenes-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .scene-card {
      transition: box-shadow 0.2s ease;
    }

    .scene-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .scene-card.has-video {
      border-left: 4px solid #4caf50;
    }

    .scene-order {
      background: #3f51b5;
      color: white;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 600;
      margin-right: 8px;
    }

    .scene-meta {
      display: flex;
      gap: 16px;
      margin-bottom: 12px;
      font-size: 0.8125rem;
      color: #666;
    }

    .scene-meta span {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .scene-status {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }

    .master-section {
      margin-top: 24px;
    }

    .master-info {
      display: flex;
      align-items: center;
      gap: 16px;
      flex-wrap: wrap;
    }

    .master-empty {
      text-align: center;
      padding: 32px;
    }

    .master-empty mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #999;
      margin-bottom: 16px;
    }

    .empty-state {
      text-align: center;
      padding: 64px 24px;
    }

    .empty-state mat-icon {
      font-size: 64px;
      width: 64px;
      height: 64px;
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

    @media (max-width: 768px) {
      .header-actions {
        flex-direction: column;
        width: 100%;
      }

      .header-actions button {
        width: 100%;
      }
    }
  `],
})
export class SceneComponent implements OnInit {
  projectId = signal<string>('');
  loading = signal(false);
  generatingScenes = signal(false);
  generatingMaster = signal(false);
  generatingPrompts = signal<Set<string>>(new Set());
  generatingImages = signal<Set<string>>(new Set());
  generatingVideos = signal<Set<string>>(new Set());

  scenes = signal<any[]>([]);
  silentMaster = signal<string | null>(null);

  private projectIdParam = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private notificationService: NotificationService,
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe(params => {
      this.projectIdParam = params.get('id') || '';
      this.projectId.set(this.projectIdParam);
      if (this.projectIdParam) {
        this.loadScenes();
        this.loadSilentMaster();
      }
    });
  }

  loadScenes(): void {
    this.loading.set(true);
    this.apiService.getScenes(this.projectIdParam).subscribe({
      next: (scenes) => {
        this.scenes.set(scenes);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  loadSilentMaster(): void {
    this.apiService.getSilentMaster(this.projectIdParam).subscribe({
      next: (master) => this.silentMaster.set(master),
      error: () => {},
    });
  }

  async generateScenes(): Promise<void> {
    this.generatingScenes.set(true);
    try {
      await this.apiService.generateScenes(this.projectIdParam, {}).toPromise();
      this.notificationService.showSuccess('Scene generation started');
      setTimeout(() => this.loadScenes(), 5000);
    } catch {
      this.notificationService.showError('Failed to start scene generation');
    } finally {
      this.generatingScenes.set(false);
    }
  }

  async generateSilentMaster(): Promise<void> {
    this.generatingMaster.set(true);
    try {
      await this.apiService.generateSilentMaster(this.projectIdParam).toPromise();
      this.notificationService.showSuccess('Silent master generation started');
      setTimeout(() => this.loadSilentMaster(), 5000);
    } catch {
      this.notificationService.showError('Failed to generate silent master');
    } finally {
      this.generatingMaster.set(false);
    }
  }

  async regenerateSilentMaster(): Promise<void> {
    await this.generateSilentMaster();
  }

  generatingImage(sceneId: string): boolean {
    return false;
  }

  async generatePrompts(sceneId: string): Promise<void> {
    try {
      await this.apiService.generateScenePrompts(this.projectIdParam, sceneId).toPromise();
      this.notificationService.showSuccess('Prompts generated');
    } catch {
      this.notificationService.showError('Failed to generate prompts');
    }
  }

  async generateImage(sceneId: string): Promise<void> {
    try {
      await this.apiService.generateSceneImage(this.projectIdParam, sceneId).toPromise();
      this.notificationService.showSuccess('Image generation started');
    } catch {
      this.notificationService.showError('Failed to generate image');
    }
  }

  async generateVideo(sceneId: string): Promise<void> {
    try {
      await this.apiService.generateSceneVideo(this.projectIdParam, sceneId).toPromise();
      this.notificationService.showSuccess('Video generation started');
    } catch {
      this.notificationService.showError('Failed to generate video');
    }
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }

  formatDuration(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  }
}