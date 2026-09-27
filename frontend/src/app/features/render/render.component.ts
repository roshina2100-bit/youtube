import { Component, OnInit, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule } from '@angular/forms';
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

interface OutputVideo {
  language: string;
  path: string;
  size_bytes: number;
  modified: number;
}

interface ExportPackage {
  filename: string;
  path: string;
  size_bytes: number;
  modified: number;
}

@Component({
  selector: 'app-render',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    ReactiveFormsModule,
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
    MatSlideToggleModule,
  ],
  template: `
    <div class="render-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Render & Export</h1>
          <p class="subtitle">Render final videos and export project packages</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="renderAllLanguages()" [disabled]="renderingAll()">
            @if (renderingAll()) {
              <mat-spinner diameter="20"></mat-spinner>
              Render All Languages
            } @else {
              <mat-icon>movie_creation</mat-icon>
              Render All Languages
            }
          </button>
          <button mat-button (click)="exportProject()" [disabled]="exporting()">
            @if (exporting()) {
              <mat-spinner diameter="16"></mat-spinner>
              Export Project
            } @else {
              <mat-icon>download</mat-icon>
              Export Project
            }
          </button>
        </div>
      </header>

      <mat-tab-group>
        <!-- Render Tab -->
        <mat-tab label="Render Videos">
          <div class="tab-content">
            @if (languages().length === 0) {
              <mat-card class="empty-state">
                <mat-card-content>
                  <mat-icon>movie_creation</mat-icon>
                  <h3>No languages configured</h3>
                  <p>Complete translation and audio generation first</p>
                </mat-card-content>
              </mat-card>
            } @else {
              <div class="render-options">
                <mat-card>
                  <mat-card-header>
                    <mat-card-title>Render Options</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="form-row">
                      <mat-form-field appearance="outline">
                        <mat-label>Subtitle Style</mat-label>
                        <mat-select [(ngModel)]="subtitleStyle">
                          <mat-option value="default">Default</mat-option>
                          <mat-option value="cinematic">Cinematic</mat-option>
                          <mat-option value="minimal">Minimal</mat-option>
                        </mat-select>
                      </mat-form-field>

                      <mat-slide-toggle [(ngModel)]="includeSubtitles" color="primary">
                        Include Subtitles
                      </mat-slide-toggle>
                    </div>
                  </mat-card-content>
                </mat-card>

                <div class="languages-render">
                  <h2>Render by Language</h2>
                  <div class="render-grid">
                    @for (lang of languages(); track lang) {
                      <mat-card class="render-card" [class.rendering]="renderingLanguage(lang)">
                        <mat-card-header>
                          <mat-card-title>{{ lang.toUpperCase() }}</mat-card-title>
                          <mat-card-subtitle>{{ getRenderStatus(lang) }}</mat-card-subtitle>
                        </mat-card-header>
                        <mat-card-content>
                          <div class="render-progress">
                            <mat-progress-bar mode="determinate" [value]="getRenderProgress(lang)"></mat-progress-bar>
                            <span>{{ getRenderProgress(lang) }}%</span>
                          </div>
                        </mat-card-content>
                        <mat-card-actions>
                          <button mat-raised-button color="primary" (click)="renderLanguage(lang)" [disabled]="renderingLanguage(lang) || rendered(lang)">
                            @if (renderingLanguage(lang)) {
                              <mat-spinner diameter="20"></mat-spinner>
                              Rendering...
                            } @else if (rendered(lang)) {
                              <mat-icon>check_circle</mat-icon>
                              Rendered
                            } @else {
                              <mat-icon>movie_creation</mat-icon>
                              Render
                            }
                          </button>
                          @if (rendered(lang)) {
                            <button mat-button (click)="previewVideo(lang)">
                              <mat-icon>visibility</mat-icon>
                              Preview
                            </button>
                            <button mat-button (click)="downloadVideo(lang)">
                              <mat-icon>download</mat-icon>
                              Download
                            </button>
                          }
                        </mat-card-actions>
                      </mat-card>
                    }
                  </div>

                  <div class="bulk-actions">
                    <button mat-raised-button color="primary" (click)="renderAllLanguages()" [disabled]="renderingAll()">
                      @if (renderingAll()) {
                        <mat-spinner diameter="20"></mat-spinner>
                        Render All Languages
                      } @else {
                        <mat-icon>movie_creation</mat-icon>
                        Render All Languages
                      }
                    </button>
                  </div>
                </div>
              </div>
            }
          </div>
        </mat-tab>

        <!-- Output Videos Tab -->
        <mat-tab label="Output Videos">
          <div class="tab-content">
            @if (outputVideos().length === 0) {
              <mat-card class="empty-state">
                <mat-card-content>
                  <mat-icon>folder_open</mat-icon>
                  <h3>No output videos yet</h3>
                  <p>Render videos first to see them here</p>
                </mat-card-content>
              </mat-card>
            } @else {
              <div class="outputs-list">
                @for (output of outputVideos(); track output.language) {
                  <mat-card class="output-card">
                    <mat-card-header>
                      <mat-card-title>{{ output.language.toUpperCase() }}</mat-card-title>
                      <mat-card-subtitle>{{ formatFileSize(output.size_bytes) }} • {{ formatDate(output.modified) }}</mat-card-subtitle>
                    </mat-card-header>
                    <mat-card-content>
                      <div class="output-actions">
                        <button mat-raised-button color="primary" (click)="previewVideo(output.language)">
                          <mat-icon>visibility</mat-icon>
                          Preview
                        </button>
                        <button mat-button (click)="downloadVideo(output.language)">
                          <mat-icon>download</mat-icon>
                          Download
                        </button>
                      </div>
                    </mat-card-content>
                  </mat-card>
                }
              </div>
            }
          </div>
        </mat-tab>

        <!-- Export Tab -->
        <mat-tab label="Export Project">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Export Project Package</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="exportForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Format</mat-label>
                      <mat-select formControlName="format">
                        <mat-option value="zip">ZIP</mat-option>
                        <mat-option value="tar.gz">TAR.GZ</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Include Approved Only</mat-label>
                      <mat-select formControlName="approvedOnly">
                        <mat-option [value]="true">Yes</mat-option>
                        <mat-option [value]="false">No</mat-option>
                      </mat-select>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <h3>Include Types</h3>
                    <div class="checkbox-grid">
                      @for (type of includeTypes; track type) {
                        <mat-checkbox [formControlName]="type">{{ type | titlecase }}</mat-checkbox>
                      }
                    </div>
                  </div>

                  <div class="form-row">
                    <h3>Languages</h3>
                    <div class="checkbox-grid">
                      @for (lang of languages(); track lang) {
                        <mat-checkbox [formControlName]="lang">{{ lang.toUpperCase() }}</mat-checkbox>
                      }
                    </div>
                  </div>

                  <div class="form-actions">
                    <button mat-raised-button color="primary" (click)="exportProject()" [disabled]="exporting()">
                      @if (exporting()) {
                        <mat-spinner diameter="20"></mat-spinner>
                        Exporting...
                      } @else {
                        <mat-icon>download</mat-icon>
                        Export Project
                      }
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            @if (exports().length > 0) {
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Previous Exports</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="exports-list">
                    @for (exp of exports(); track exp.filename) {
                      <mat-card class="export-item">
                        <mat-card-content>
                          <div class="export-info">
                            <mat-icon>file_download</mat-icon>
                            <div>
                              <span class="export-name">{{ exp.filename }}</span>
                              <span class="export-meta">{{ formatFileSize(exp.size_bytes) }} • {{ formatDate(exp.modified) }}</span>
                            </div>
                          </div>
                          <div class="export-actions">
                            <button mat-button (click)="downloadExport(exp.filename)">
                              <mat-icon>download</mat-icon>
                              Download
                            </button>
                          </div>
                        </mat-card-content>
                      </mat-card>
                    }
                  </div>
                </mat-card-content>
              </mat-card>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .render-page {
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

    .tab-content {
      padding: 24px 0;
    }

    .render-options {
      margin-bottom: 24px;
    }

    .form-row {
      display: flex;
      gap: 16px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }

    .form-row:last-child {
      margin-bottom: 0;
    }

    .full-width {
      flex: 1;
      min-width: 280px;
    }

    .languages-render {
      margin-top: 24px;
    }

    .languages-render h2 {
      margin: 0 0 16px;
      font-size: 1.25rem;
    }

    .render-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }

    .render-card {
      transition: box-shadow 0.2s ease;
    }

    .render-card.rendering {
      border: 2px solid #3f51b5;
    }

    .render-progress {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 16px;
    }

    .render-progress mat-progress-bar {
      flex: 1;
    }

    .render-progress span {
      font-weight: 500;
      min-width: 50px;
    }

    .bulk-actions {
      margin-top: 24px;
      padding-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .outputs-list {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .output-card {
      transition: box-shadow 0.2s ease;
    }

    .output-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .output-actions {
      display: flex;
      gap: 12px;
      margin-top: 16px;
    }

    .export-form {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .checkbox-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
      gap: 12px;
      margin-top: 12px;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      padding-top: 16px;
      margin-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .exports-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .export-item {
      transition: box-shadow 0.2s ease;
    }

    .export-item:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .export-info {
      display: flex;
      align-items: center;
      gap: 16px;
    }

    .export-info mat-icon {
      color: #3f51b5;
      font-size: 32px;
      width: 32px;
      height: 32px;
    }

    .export-name {
      display: block;
      font-weight: 500;
      color: #333;
    }

    .export-meta {
      display: block;
      font-size: 0.8125rem;
      color: #666;
    }

    .export-actions {
      display: flex;
      justify-content: flex-end;
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
      .render-grid {
        grid-template-columns: 1fr;
      }

      .checkbox-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class RenderComponent implements OnInit {
  projectId = signal<string>('');
  renderingAll = signal(false);
  renderingLanguages = signal<Set<string>>(new Set());
  exporting = signal(false);

  languages = signal<string[]>([]);
  outputVideos = signal<any[]>([]);
  exports = signal<any[]>([]);

  subtitleStyle = 'default';
  includeSubtitles = true;

  exportForm: any; // Would use FormBuilder

  includeTypes = [
    'project_manifest',
    'transcript',
    'story',
    'characters',
    'scenes',
    'translations',
    'prompts',
    'images',
    'videos',
    'audio',
    'outputs',
  ];

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
        this.loadLanguages();
        this.loadOutputs();
        this.loadExports();
      }
    });
  }

  loadLanguages(): void {
    this.apiService.getLanguages(this.projectIdParam).subscribe({
      next: (langs) => this.languages.set(langs),
    });
  }

  loadOutputs(): void {
    this.apiService.getOutputs(this.projectIdParam).subscribe({
      next: (outputs) => this.outputVideos.set(outputs),
    });
  }

  loadExports(): void {
    this.apiService.getExports(this.projectIdParam).subscribe({
      next: (exports) => this.exports.set(exports),
    });
  }

  async renderLanguage(lang: string): Promise<void> {
    try {
      await this.apiService.renderFinalVideo(this.projectIdParam, { language: lang, includeSubtitles: true }).toPromise();
      this.notificationService.showSuccess(`Rendering started for ${lang}`);
    } catch {
      this.notificationService.showError(`Failed to render ${lang}`);
    }
  }

  async renderAllLanguages(): Promise<void> {
    try {
      await this.apiService.renderAllLanguages(this.projectIdParam).toPromise();
      this.notificationService.showSuccess('Rendering started for all languages');
    } catch {
      this.notificationService.showError('Failed to start rendering');
    }
  }

  async exportProject(): Promise<void> {
    this.exporting.set(true);
    try {
      const formValue = this.exportForm.value;
      await this.apiService.exportProject(this.projectIdParam, formValue).toPromise();
      this.notificationService.showSuccess('Export started');
      this.loadExports();
    } catch {
      this.notificationService.showError('Failed to start export');
    } finally {
      this.exporting.set(false);
    }
  }

  async previewVideo(lang: string): Promise<void> {
    // Would open video preview
  }

  async downloadVideo(lang: string): Promise<void> {
    // Would download video
  }

  async downloadExport(filename: string): Promise<void> {
    // Would download export
  }

  renderingLanguage(lang: string): boolean {
    return false; // Would track per language
  }

  rendered(lang: string): boolean {
    return false; // Would check if rendered
  }

  getRenderStatus(lang: string): string {
    return 'Ready to render';
  }

  getRenderProgress(lang: string): number {
    return 0;
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDate(timestamp: number): string {
    return new Date(timestamp * 1000).toLocaleDateString();
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }
}