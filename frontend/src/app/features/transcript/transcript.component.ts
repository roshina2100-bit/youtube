import { Component, signal, computed } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterModule } from '@angular/router';
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
import { MatSlideToggleModule } from '@angular/material/slide-toggle';

import { ApiService } from '@core/services/api.service';
import { NotificationService } from '@core/services/notification.service';

interface TranscriptData {
  segments: TranscriptSegment[];
  speakers: SpeakerInfo[];
  total_duration: number;
  language: string;
  normalized: boolean;
}

interface TranscriptSegment {
  id: string;
  start: number;
  end: number;
  text: string;
  speaker: string | null;
  language: string | null;
  confidence: number;
}

interface SpeakerInfo {
  id: string;
  name: string | null;
  gender: string | null;
  language: string | null;
  segments_count: number;
  total_duration: number;
}

interface LanguageDetectionResult {
  detected_language: string;
  confidence: number;
  detector: string;
  alternatives: any[];
  manual_override: boolean;
}

@Component({
  selector: 'app-transcript',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterModule,
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
    MatSlideToggleModule,
  ],
  template: `
    <div class="transcript-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Transcript</h1>
          <p class="subtitle">View, edit, and manage transcript</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="normalizeTranscript()" [disabled]="normalizing()">
            <mat-icon>auto_fix_high</mat-icon>
            <span>{{ normalizing() ? 'Normalizing...' : 'Normalize' }}</span>
          </button>
          <button mat-button (click)="detectLanguage()" [disabled]="detectingLanguage()">
            <mat-icon>translate</mat-icon>
            <span>{{ detectingLanguage() ? 'Detecting...' : 'Detect language' }}</span>
          </button>
        </div>
      </header>

      @if (transcript(); as data) {
        <section class="transcript-meta">
          <mat-chip-set>
            <mat-chip>{{ data.language?.toUpperCase() || 'UNKNOWN' }}</mat-chip>
            <mat-chip>{{ data.segments.length }} segments</mat-chip>
            <mat-chip>{{ formatDuration(data.total_duration) }}</mat-chip>
            <mat-chip [class.normalized-chip]="data.normalized" [class.raw-chip]="!data.normalized">
              {{ data.normalized ? 'Normalized' : 'Raw' }}
            </mat-chip>
          </mat-chip-set>
          @if (languageDetection(); as detection) {
            <mat-chip-set>
              <mat-chip>
                <mat-icon>translate</mat-icon>
                {{ detection.detected_language?.toUpperCase() }} · {{ (detection.confidence * 100).toFixed(0) }}%
              </mat-chip>
            </mat-chip-set>
          }
        </section>

        <mat-card class="transcript-card">
          <mat-card-content>
            <div class="transcript-controls">
              <mat-form-field appearance="outline" class="search-field">
                <mat-label>Search transcript</mat-label>
                <input matInput [ngModel]="searchTerm()" (ngModelChange)="searchTerm.set($event)" placeholder="Search transcript">
                <mat-icon matPrefix>search</mat-icon>
              </mat-form-field>
              <mat-form-field appearance="outline" class="speaker-filter">
                <mat-label>Filter speakers</mat-label>
                <mat-select [ngModel]="speakerFilter()" (ngModelChange)="speakerFilter.set($event)" multiple>
                  @for (speaker of speakers(); track speaker.id) {
                    <mat-option [value]="speaker.id">{{ speaker.name || speaker.id }}</mat-option>
                  }
                </mat-select>
              </mat-form-field>
              <mat-slide-toggle [(ngModel)]="showTimestamps">Show timestamps</mat-slide-toggle>
            </div>

            <div class="transcript-segments">
              @for (segment of filteredSegments(); track segment.id) {
                <article class="segment">
                  @if (showTimestamps) {
                    <span class="segment-time">{{ formatTime(segment.start) }}–{{ formatTime(segment.end) }}</span>
                  }
                  @if (segment.speaker) {
                    <span class="segment-speaker">{{ segment.speaker }}</span>
                  }
                  <span class="segment-text"
                        [attr.contenteditable]="editingSegmentId() === segment.id"
                        (blur)="saveSegmentEdit(segment, $event)"
                        (keydown.enter)="$event.preventDefault(); saveSegmentEdit(segment, $event)"
                        (keydown.escape)="cancelSegmentEdit()">{{ segment.text }}</span>
                  <div class="segment-actions">
                    <button mat-icon-button (click)="startEditSegment(segment)" matTooltip="Edit segment" aria-label="Edit segment">
                      <mat-icon>edit</mat-icon>
                    </button>
                    <button mat-icon-button (click)="playSegment(segment)" matTooltip="Play segment" aria-label="Play segment">
                      <mat-icon>play_arrow</mat-icon>
                    </button>
                    <button mat-icon-button color="warn" (click)="deleteSegment(segment)" matTooltip="Delete segment" aria-label="Delete segment">
                      <mat-icon>delete</mat-icon>
                    </button>
                  </div>
                </article>
              } @empty {
                <p class="empty-filter">No transcript segments match these filters.</p>
              }
            </div>
          </mat-card-content>
        </mat-card>
      } @else {
        <mat-card class="empty-state">
          <mat-card-content>
            <mat-icon>description</mat-icon>
            <h2>No transcript available</h2>
            <p>Import a transcript or process source media to generate one.</p>
            <button mat-raised-button color="primary" (click)="goToSource()">
              <mat-icon>add</mat-icon>
              Import source
            </button>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .transcript-page { display: flex; flex-direction: column; gap: 20px; }
    .page-header { display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }
    .page-header h1 { margin: 0 0 4px; font-size: 1.75rem; font-weight: 600; }
    .subtitle { margin: 0; color: #666; }
    .header-actions { margin-left: auto; display: flex; gap: 8px; flex-wrap: wrap; }
    .header-actions button { display: inline-flex; align-items: center; gap: 8px; }
    .transcript-meta { display: flex; align-items: center; justify-content: space-between; gap: 12px; flex-wrap: wrap; }
    .normalized-chip { background: #e8f5e9; color: #2e7d32; }
    .raw-chip { background: #fff3e0; color: #e65100; }
    .transcript-card { width: 100%; }
    .transcript-controls { display: flex; align-items: center; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
    .search-field { flex: 1 1 240px; }
    .speaker-filter { flex: 0 1 220px; }
    .transcript-segments { display: flex; flex-direction: column; gap: 8px; }
    .segment { display: flex; align-items: flex-start; gap: 12px; padding: 12px; background: #fafafa; border-radius: 6px; }
    .segment-time { flex: 0 0 142px; color: #666; font: 12px 'Roboto Mono', monospace; }
    .segment-speaker { flex: 0 0 100px; color: #3949ab; font-size: 13px; font-weight: 600; }
    .segment-text { flex: 1 1 auto; min-width: 0; line-height: 1.5; white-space: pre-wrap; outline: none; }
    .segment-text[contenteditable="true"] { background: white; box-shadow: 0 0 0 1px #3949ab; border-radius: 3px; }
    .segment-actions { display: flex; gap: 2px; opacity: 0; }
    .segment:hover .segment-actions, .segment:focus-within .segment-actions { opacity: 1; }
    .empty-filter, .empty-state { text-align: center; color: #666; }
    .empty-state { padding: 40px 20px; }
    .empty-state mat-icon { width: 48px; height: 48px; font-size: 48px; color: #777; }
    @media (max-width: 720px) {
      .header-actions { width: 100%; margin-left: 0; }
      .header-actions button { flex: 1 1 auto; }
      .segment { flex-wrap: wrap; }
      .segment-time, .segment-speaker { flex-basis: auto; }
      .segment-text { flex-basis: 100%; order: 2; }
      .segment-actions { opacity: 1; margin-left: auto; }
    }
  `],
})
export class TranscriptComponent {
  projectId = signal<string>('');
  normalizing = signal(false);
  detectingLanguage = signal(false);
  editingSegmentId = signal<string | null>(null);
  showTimestamps = true;
  searchTerm = signal('');
  speakerFilter = signal<string[]>([]);

  transcript = signal<TranscriptData | null>(null);
  languageDetection = signal<LanguageDetectionResult | null>(null);

  private projectIdParam = '';

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private apiService: ApiService,
    private notificationService: NotificationService,
  ) {
    this.route.paramMap.subscribe(params => {
      this.projectIdParam = params.get('id') || '';
      this.projectId.set(this.projectIdParam);
      if (this.projectIdParam) {
        this.loadTranscript();
        this.loadLanguageDetection();
      }
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
      next: (d) => this.languageDetection.set(d),
      error: () => {},
    });
  }

  speakers = computed(() => {
    const t = this.transcript();
    return t?.speakers || [];
  });

  filteredSegments = computed(() => {
    const t = this.transcript();
    if (!t) return [];

    let segments = t.segments || [];

    if (this.searchTerm) {
      const term = this.searchTerm().toLowerCase();
      segments = segments.filter((s: TranscriptSegment) => s.text.toLowerCase().includes(term));
    }

    if (this.speakerFilter().length > 0) {
      segments = segments.filter((s: TranscriptSegment) => this.speakerFilter().includes(s.speaker || ''));
    }

    return segments;
  });

  startEditSegment(segment: TranscriptSegment): void {
    this.editingSegmentId.set(segment.id);
  }

  saveSegmentEdit(segment: TranscriptSegment, event: FocusEvent): void {
    const updatedText = (event.currentTarget as HTMLElement).textContent?.trim();
    if (updatedText) {
      this.transcript.update(data => data ? ({
        ...data,
        segments: data.segments.map(item => item.id === segment.id ? { ...item, text: updatedText } : item),
      }) : data);
    }
    this.editingSegmentId.set(null);
  }

  cancelSegmentEdit(): void {
    this.editingSegmentId.set(null);
  }

  playSegment(segment: TranscriptSegment): void {
    // Would play audio segment
  }

  deleteSegment(segment: TranscriptSegment): void {
    if (confirm('Delete this segment?')) {
      // Would call API
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

  goToSource(): void {
    this.router.navigate(['/projects', this.projectIdParam, 'source']);
  }

  async resetLanguageOverride(): Promise<void> {
    // Would call API
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  };

  formatDuration(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    if (hrs > 0) return `${hrs}h ${mins}m ${secs}s`;
    if (mins > 0) return `${mins}m ${secs}s`;
    return `${secs}s`;
  };

  formatTime(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    const ms = Math.floor((seconds % 1) * 1000);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}.${ms.toString().padStart(3, '0')}`;
  }
}