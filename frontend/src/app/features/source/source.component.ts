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
import { MatProgressBarModule } from '@angular/material/progress-bar';
import { MatChipsModule } from '@angular/material/chips';
import { MatDividerModule } from '@angular/material/divider';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatRadioModule } from '@angular/material/radio';

import { ApiService } from '@core/services/api.service';
import { NotificationService } from '@core/services/notification.service';
import { environment } from '@environments/environment';

interface SourceInfo {
  type: string;
  path: string;
  original_filename: string;
  duration_seconds: number;
  metadata: any;
}

@Component({
  selector: 'app-source',
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
    MatProgressBarModule,
    MatChipsModule,
    MatDividerModule,
    MatTabsModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
    MatRadioModule,
  ],
  template: `
    <div class="source-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Source Media</h1>
          <p class="subtitle">Import and manage source video, audio, or transcript</p>
        </div>
      </header>

      <mat-tab-group>
        <!-- Import Tab -->
        <mat-tab label="Import">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Import Source Media</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <div class="import-options">
                  <mat-radio-group [(ngModel)]="importType" class="import-type-group">
                    <mat-radio-button value="local_file">Local Video/Audio File</mat-radio-button>
                    <mat-radio-button value="transcript">Transcript File</mat-radio-button>
                    <mat-radio-button value="url" disabled>URL (Coming Soon)</mat-radio-button>
                  </mat-radio-group>
                </div>

                @if (importType === 'local_file') {
                  <div class="import-section">
                    <div class="drop-zone" 
                         (dragover)="onDragOver($event)" 
                         (dragleave)="onDragLeave($event)" 
                         (drop)="onDrop($event)"
                         [class.drag-over]="dragOver()">
                      <mat-icon>cloud_upload</mat-icon>
                      <p>Drag & drop video or audio file here, or click to browse</p>
                      <p class="hint">Supported: MP4, MOV, AVI, MKV, WebM, MP3, WAV, FLAC, OGG</p>
                      <input type="file" #fileInput hidden accept="video/*,audio/*" (change)="onFileSelected($event)">
                      <button mat-stroked-button (click)="fileInput.click()" class="browse-btn">
                        <mat-icon>folder_open</mat-icon>
                        Browse Files
                      </button>
                    </div>
                    @if (selectedFile()) {
                      <div class="selected-file">
                        <mat-icon>check_circle</mat-icon>
                        <span>{{ selectedFile()!.name }} ({{ formatFileSize(selectedFile()!.size) }})</span>
                      </div>
                    }
                  </div>
                }

                @if (importType === 'transcript') {
                  <div class="import-section">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Transcript Content</mat-label>
                      <textarea matInput [(ngModel)]="transcriptContent" rows="10" placeholder="Paste your transcript here..."></textarea>
                    </mat-form-field>
                    <mat-form-field appearance="outline">
                      <mat-label>Format</mat-label>
                      <mat-select [(ngModel)]="transcriptFormat">
                        <mat-option value="txt">Plain Text</mat-option>
                        <mat-option value="srt">SRT Subtitles</mat-option>
                        <mat-option value="vtt">VTT Subtitles</mat-option>
                        <mat-option value="json">JSON</mat-option>
                      </mat-select>
                    </mat-form-field>
                  </div>
                }

                <div class="form-actions">
                  <button mat-raised-button color="primary" 
                          (click)="importSource()" 
                          [disabled]="importing() || !canImport()">
                    @if (importing()) {
                      <mat-spinner diameter="20"></mat-spinner>
                      Importing...
                    } @else {
                      <mat-icon>cloud_upload</mat-icon>
                      Import Source
                    }
                  </button>
                </div>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Source Info Tab -->
        <mat-tab label="Source Info">
          <div class="tab-content">
            @if (sourceInfo(); as info) {
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Source Information</mat-card-title>
                </mat-card-header>
                <mat-card-content>
                  <div class="info-grid">
                    <div class="info-item">
                      <mat-icon>videocam</mat-icon>
                      <div>
                        <span class="info-label">Type</span>
                        <span class="info-value">{{ info.type | titlecase }}</span>
                      </div>
                    </div>
                    <div class="info-item">
                      <mat-icon>description</mat-icon>
                      <div>
                        <span class="info-label">Filename</span>
                        <span class="info-value">{{ info.original_filename }}</span>
                      </div>
                    </div>
                    <div class="info-item">
                      <mat-icon>timer</mat-icon>
                      <div>
                        <span class="info-label">Duration</span>
                        <span class="info-value">{{ formatDuration(info.duration_seconds) }}</span>
                      </div>
                    </div>
                    <div class="info-item">
                      <mat-icon>folder</mat-icon>
                      <div>
                        <span class="info-label">Path</span>
                        <span class="info-value">{{ info.path }}</span>
                      </div>
                    </div>
                  </div>

                  @if (info.metadata && Object.keys(info.metadata).length > 0) {
                    <mat-divider></mat-divider>
                    <h3>Metadata</h3>
                    <div class="metadata-display">
                      <pre>{{ info.metadata | json }}</pre>
                    </div>
                  }

                  <div class="actions">
                    <button mat-button (click)="downloadSource()">
                      <mat-icon>download</mat-icon>
                      Download
                    </button>
                    <button mat-button color="warn" (click)="deleteSource()">
                      <mat-icon>delete</mat-icon>
                      Delete Source
                    </button>
                  </div>
                </mat-card-content>
              </mat-card>
            } @else {
              <mat-card class="empty-state">
                <mat-card-content>
                  <mat-icon>videocam_off</mat-icon>
                  <h3>No source media imported</h3>
                  <p>Import a video, audio, or transcript file to get started</p>
                  <button mat-raised-button color="primary" (click)="switchToImportTab()">
                    <mat-icon>add</mat-icon>
                    Import Source
                  </button>
                </mat-card-content>
              </mat-card>
            }
          </div>
        </mat-tab>

        <!-- Transcript Tab -->
        <mat-tab label="Transcript">
          <div class="tab-content">
            @if (transcript(); as t) {
              <mat-card>
                <mat-card-header>
                  <mat-card-title>Transcript</mat-card-title>
                  <mat-card-subtitle>{{ t.language }} • {{ t.segments.length }} segments • {{ formatDuration(t.total_duration) }}</mat-card-subtitle>
                </mat-card-header>
                <mat-card-content>
                  <div class="transcript-controls">
                    <mat-form-field appearance="outline" class="search-field">
                      <mat-label>Search transcript</mat-label>
                      <input matInput [(ngModel)]="transcriptSearch" placeholder="Search...">
                      <mat-icon matPrefix>search</mat-icon>
                    </mat-form-field>
                    <button mat-button (click)="normalizeTranscript()" [disabled]="normalizing()">
                      @if (normalizing()) {
                        <mat-spinner diameter="16"></mat-spinner>
                        Normalizing...
                      } @else {
                        <mat-icon>auto_fix_high</mat-icon>
                        Normalize
                      }
                    </button>
                    <button mat-button (click)="detectLanguage()" [disabled]="detectingLanguage()">
                      @if (detectingLanguage()) {
                        <mat-spinner diameter="16"></mat-spinner>
                        Detect Language
                      } @else {
                        <mat-icon>translate</mat-icon>
                        Detect Language
                      }
                    </button>
                  </div>

                  @if (languageDetection()) {
                    <mat-chip-set class="language-chip">
                      <mat-chip [class]="'status-' + (languageDetection()?.manual_override ? 'manual' : 'auto')">
                        <mat-icon>translate</mat-icon>
                        {{ languageDetection()?.detected_language?.toUpperCase() }} ({{ (languageDetection()?.confidence * 100).toFixed(0) }}%)
                        @if (languageDetection()?.manual_override) {
                          <mat-icon matChipRemove (click)="resetLanguageOverride()">close</mat-icon>
                        }
                      </mat-chip>
                    </mat-chip-set>
                  }

                  <div class="transcript-segments">
                    @for (segment of filteredSegments(); track segment.id) {
                      <div class="segment" [class.current]="isCurrentSegment(segment)">
                        <span class="segment-time">{{ formatTime(segment.start) }} - {{ formatTime(segment.end) }}</span>
                        @if (segment.speaker) {
                          <span class="segment-speaker">{{ segment.speaker }}:</span>
                        }
                        <span class="segment-text">{{ segment.text }}</span>
                      </div>
                    }
                  </div>
                </mat-card-content>
              </mat-card>
            } @else {
              <mat-card class="empty-state">
                <mat-card-content>
                  <mat-icon>description</mat-icon>
                  <h3>No transcript available</h3>
                  <p>Import a transcript or process source media to generate one</p>
                </mat-card-content>
              </mat-card>
            }
          </div>
        </mat-tab>
      </mat-tab-group>
    </div>
  `,
  styles: [`
    .source-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
    }

    .page-header {
      display: flex;
      align-items: center;
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

    .tab-content {
      padding: 24px 0;
    }

    .import-type-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 24px;
    }

    .import-section {
      margin-bottom: 24px;
    }

    .drop-zone {
      border: 2px dashed #ccc;
      border-radius: 12px;
      padding: 48px 24px;
      text-align: center;
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .drop-zone:hover {
      border-color: #3f51b5;
      background: #f5f5ff;
    }

    .drop-zone.drag-over {
      border-color: #3f51b5;
      background: #e8eaff;
    }

    .drop-zone mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #999;
      margin-bottom: 16px;
    }

    .drop-zone p {
      margin: 8px 0;
      color: #666;
    }

    .drop-zone .hint {
      font-size: 0.8125rem;
      color: #999;
    }

    .browse-btn {
      margin-top: 16px;
    }

    .selected-file {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px 16px;
      background: #e8f5e9;
      border-radius: 8px;
      margin-top: 16px;
    }

    .selected-file mat-icon {
      color: #2e7d32;
    }

    .import-section mat-form-field {
      margin-bottom: 16px;
    }

    .form-actions {
      display: flex;
      justify-content: flex-end;
      padding-top: 16px;
      margin-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .info-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .info-item {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 16px;
      background: #fafafa;
      border-radius: 8px;
    }

    .info-item mat-icon {
      color: #3f51b5;
      margin-top: 4px;
    }

    .info-label {
      display: block;
      font-size: 0.75rem;
      font-weight: 500;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .info-value {
      display: block;
      font-size: 0.875rem;
      color: #333;
      word-break: break-all;
    }

    .metadata-display {
      background: #f5f5f5;
      padding: 16px;
      border-radius: 8px;
      max-height: 300px;
      overflow: auto;
    }

    .metadata-display pre {
      margin: 0;
      font-size: 0.75rem;
      white-space: pre-wrap;
      word-break: break-word;
    }

    .actions {
      display: flex;
      gap: 12px;
      padding-top: 16px;
      margin-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .transcript-controls {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
      margin-bottom: 16px;
    }

    .search-field {
      flex: 1;
      min-width: 250px;
    }

    .language-chip {
      margin-bottom: 16px;
    }

    .language-chip mat-chip {
      font-size: 0.8125rem;
    }

    .language-chip.status-manual {
      background: #e3f2fd;
      color: #1565c0;
    }

    .language-chip.status-auto {
      background: #fff3e0;
      color: #e65100;
    }

    .transcript-segments {
      display: flex;
      flex-direction: column;
      gap: 8px;
      max-height: 500px;
      overflow: auto;
    }

    .segment {
      display: flex;
      align-items: flex-start;
      gap: 12px;
      padding: 12px 16px;
      background: #fafafa;
      border-radius: 8px;
      transition: background 0.2s ease;
    }

    .segment:hover {
      background: #f0f0f0;
    }

    .segment.current {
      background: #e3f2fd;
      border-left: 3px solid #3f51b5;
    }

    .segment-time {
      font-size: 0.75rem;
      font-weight: 500;
      color: #666;
      min-width: 140px;
      font-family: 'Roboto Mono', monospace;
    }

    .segment-speaker {
      font-size: 0.8125rem;
      font-weight: 500;
      color: #3f51b5;
      min-width: 100px;
    }

    .segment-text {
      flex: 1;
      color: #333;
      line-height: 1.5;
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
      .info-grid {
        grid-template-columns: 1fr;
      }

      .transcript-controls {
        flex-direction: column;
      }

      .search-field {
        min-width: 0;
      }
    }
  `],
})
export class SourceComponent implements OnInit {
  projectId = signal<string>('');
  importing = signal(false);
  normalizing = signal(false);
  detectingLanguage = signal(false);
  dragOver = signal(false);
  selectedFile = signal<File | null>(null);
  importType = 'local_file';
  transcriptContent = '';
  transcriptFormat = 'txt';
  transcriptSearch = '';

  sourceInfo = signal<SourceInfo | null>(null);
  transcript = signal<any>(null);
  languageDetection = signal<any>(null);

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
        this.loadSourceInfo();
        this.loadTranscript();
        this.loadLanguageDetection();
      }
    });
  }

  loadSourceInfo(): void {
    this.apiService.getSourceInfo(this.projectIdParam).subscribe({
      next: (info: any) => this.sourceInfo.set(info),
      error: () => this.notificationService.showError('Failed to load source info'),
    });
  }

  loadTranscript(): void {
    this.apiService.getTranscript(this.projectIdParam).subscribe({
      next: (t) => this.transcript.set(t),
      error: () => {},
    });
  }

  loadLanguageDetection(): void {
    this.apiService.getLanguageDetection(this.projectIdParam).subscribe({
      next: (d: any) => this.languageDetection.set(d),
      error: () => {},
    });
  }

  canImport(): boolean {
    if (this.importType === 'local_file') {
      return !!this.selectedFile();
    }
    if (this.importType === 'transcript') {
      return this.transcriptContent.trim().length > 0;
    }
    return false;
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver.set(true);
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver.set(false);
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.dragOver.set(false);

    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.selectedFile.set(files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.selectedFile.set(input.files[0]);
    }
  }

  async importSource(): Promise<void> {
    if (!this.canImport()) return;

    this.importing.set(true);

    try {
      if (this.importType === 'local_file' && this.selectedFile()) {
        const formData = new FormData();
        formData.append('file', this.selectedFile()!);
        formData.append('source_type', 'local_file');

        await this.apiService.importSource(this.projectIdParam, formData).toPromise();
        this.notificationService.showSuccess('Source media imported successfully');
      } else if (this.importType === 'transcript') {
        const formData = new FormData();
        formData.append('content', this.transcriptContent);
        formData.append('format', this.transcriptFormat);

        await this.apiService.importTranscript(this.projectIdParam, formData).toPromise();
        this.notificationService.showSuccess('Transcript imported successfully');
      }

      this.selectedFile.set(null);
      this.transcriptContent = '';
      this.loadSourceInfo();
      this.loadTranscript();
    } catch (error) {
      this.notificationService.showError('Failed to import source');
    } finally {
      this.importing.set(false);
    }
  }

  async normalizeTranscript(): Promise<void> {
    this.normalizing.set(true);
    try {
      await this.apiService.normalizeTranscript(this.projectIdParam, {}).toPromise();
      this.notificationService.showSuccess('Transcript normalized');
      this.loadTranscript();
    } catch {
      this.notificationService.showError('Failed to normalize transcript');
    } finally {
      this.normalizing.set(false);
    }
  }

  async detectLanguage(): Promise<void> {
    this.detectingLanguage.set(true);
    try {
      await this.apiService.detectLanguage(this.projectIdParam).toPromise();
      this.notificationService.showSuccess('Language detected');
      this.loadLanguageDetection();
      this.loadTranscript();
    } catch {
      this.notificationService.showError('Failed to detect language');
    } finally {
      this.detectingLanguage.set(false);
    }
  }

  async resetLanguageOverride(): Promise<void> {
    // Would call API to reset language override
  }

  downloadSource(): void {
    window.open(`${environment.apiUrl}/projects/${this.projectIdParam}/source/download`, '_blank');
  }

  async deleteSource(): Promise<void> {
    if (confirm('Are you sure you want to delete the source media?')) {
      try {
        await this.apiService.deleteSource(this.projectIdParam).toPromise();
        this.notificationService.showSuccess('Source deleted');
        this.sourceInfo.set(null);
      } catch {
        this.notificationService.showError('Failed to delete source');
      }
    }
  }

  switchToImportTab(): void {
    // Would switch to import tab programmatically
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }

  filteredSegments = computed(() => {
    const t = this.transcript();
    if (!t || !this.transcriptSearch) return t?.segments || [];
    const term = this.transcriptSearch.toLowerCase();
    return t.segments.filter((s: any) => s.text.toLowerCase().includes(term));
  });

  isCurrentSegment(segment: any): boolean {
    // Would check if segment is currently playing
    return false;
  }

  formatFileSize(bytes: number): string {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  }

  formatDuration(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  }

  formatTime(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
}