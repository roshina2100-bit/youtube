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

interface LanguageAudio {
  language: string;
  audio_files: Record<string, string[]>;
}

@Component({
  selector: 'app-audio',
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
    MatSlideToggleModule,
  ],
  template: `
    <div class="audio-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Audio Generation</h1>
          <p class="subtitle">Generate TTS, music, sound effects, and mix audio</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="generateAllAudio()" [disabled]="generatingAll()">
            @if (generatingAll()) {
              <mat-spinner diameter="20"></mat-spinner>
              Generate All Audio
            } @else {
              <mat-icon>audiotrack</mat-icon>
              Generate All Audio
            }
          </button>
        </div>
      </header>

      @if (languages().length === 0) {
        <mat-card class="empty-state">
          <mat-card-content>
            <mat-icon>audiotrack</mat-icon>
            <h3>No languages configured</h3>
            <p>Complete translation first, then generate audio for each language</p>
          </mat-card-content>
        </mat-card>
      } @else {
        <mat-tab-group>
          @for (lang of languages(); track lang) {
            <mat-tab [label]="lang.toUpperCase()">
              <div class="tab-content">
                @if (audioData(); as audio) {
                  <div class="audio-workspace">
                    <div class="workspace-header">
                      <h2>{{ lang.toUpperCase() }} Audio</h2>
                      <div class="workspace-actions">
                        <button mat-raised-button color="primary" (click)="generateAllForLanguage(lang)" [disabled]="generatingLanguage(lang)">
                          @if (generatingLanguage(lang)) {
                            <mat-spinner diameter="20"></mat-spinner>
                            Generate All
                          } @else {
                            <mat-icon>audiotrack</mat-icon>
                            Generate All Audio
                          }
                        </button>
                        <button mat-button (click)="mixAudio(lang)" [disabled]="mixing(lang)">
                          @if (mixing(lang)) {
                            <mat-spinner diameter="16"></mat-spinner>
                            Mix Audio
                          } @else {
                            <mat-icon>tune</mat-icon>
                            Mix Master
                          }
                        </button>
                      </div>
                    </div>

                    <mat-tab-group>
                      <!-- Narration Tab -->
                      <mat-tab label="Narration">
                        <div class="tab-content">
                          @if (audioData()?.audio_files?.narration?.length > 0) {
                            <div class="audio-list">
                              @for (file of audioData().audio_files.narration; track file) {
                                <mat-card class="audio-item">
                                  <mat-card-content>
                                    <div class="audio-info">
                                      <mat-icon>record_voice_over</mat-icon>
                                      <span>{{ file }}</span>
                                    </div>
                                    <div class="audio-controls">
                                      <button mat-icon-button (click)="playAudio(lang, 'narration', file)">
                                        <mat-icon>play_arrow</mat-icon>
                                      </button>
                                      <button mat-icon-button (click)="downloadAudio(lang, 'narration', file)">
                                        <mat-icon>download</mat-icon>
                                      </button>
                                    </div>
                                  </mat-card-content>
                                </mat-card>
                              }
                            </div>
                          } @else {
                            <div class="empty-audio">
                              <mat-icon>record_voice_over</mat-icon>
                              <p>No narration generated yet</p>
                              <button mat-raised-button color="primary" (click)="generateTTS(lang)">
                                <mat-icon>record_voice_over</mat-icon>
                                Generate TTS
                              </button>
                            </div>
                          }
                        </div>
                      </mat-tab>

                      <!-- Dialogue Tab -->
                      <mat-tab label="Dialogue">
                        <div class="tab-content">
                          @if (audioData()?.audio_files?.dialogue?.length > 0) {
                            <div class="audio-list">
                              @for (file of audioData().audio_files.dialogue; track file) {
                                <mat-card class="audio-item">
                                  <mat-card-content>
                                    <div class="audio-info">
                                      <mat-icon>record_voice_over</mat-icon>
                                      <span>{{ file }}</span>
                                    </div>
                                    <div class="audio-controls">
                                      <button mat-icon-button (click)="playAudio(lang, 'dialogue', file)">
                                        <mat-icon>play_arrow</mat-icon>
                                      </button>
                                      <button mat-icon-button (click)="downloadAudio(lang, 'dialogue', file)">
                                        <mat-icon>download</mat-icon>
                                      </button>
                                    </div>
                                  </mat-card-content>
                                </mat-card>
                              }
                            </div>
                          } @else {
                            <div class="empty-audio">
                              <mat-icon>record_voice_over</mat-icon>
                              <p>No dialogue generated yet</p>
                              <button mat-raised-button color="primary" (click)="generateTTS(lang)">
                                <mat-icon>record_voice_over</mat-icon>
                                Generate TTS
                              </button>
                            </div>
                          }
                        </div>
                      </mat-tab>

                      <!-- Music Tab -->
                      <mat-tab label="Music">
                        <div class="tab-content">
                          @if (audioData()?.audio_files?.music?.length > 0) {
                            <div class="audio-list">
                              @for (file of audioData().audio_files.music; track file) {
                                <mat-card class="audio-item">
                                  <mat-card-content>
                                    <div class="audio-info">
                                      <mat-icon>music_note</mat-icon>
                                      <span>{{ file }}</span>
                                    </div>
                                    <div class="audio-controls">
                                      <button mat-icon-button (click)="playAudio(lang, 'music', file)">
                                        <mat-icon>play_arrow</mat-icon>
                                      </button>
                                      <button mat-icon-button (click)="downloadAudio(lang, 'music', file)">
                                        <mat-icon>download</mat-icon>
                                      </button>
                                    </div>
                                  </mat-card-content>
                                </mat-card>
                              }
                            </div>
                          } @else {
                            <div class="empty-audio">
                              <mat-icon>music_note</mat-icon>
                              <p>No music generated yet</p>
                              <button mat-raised-button color="primary" (click)="generateMusic(lang)">
                                <mat-icon>music_note</mat-icon>
                                Generate Music
                              </button>
                            </div>
                          }
                        </div>
                      </mat-tab>

                      <!-- SFX Tab -->
                      <mat-tab label="Sound Effects">
                        <div class="tab-content">
                          @if (audioData()?.audio_files?.sfx?.length > 0) {
                            <div class="audio-list">
                              @for (file of audioData().audio_files.sfx; track file) {
                                <mat-card class="audio-item">
                                  <mat-card-content>
                                    <div class="audio-info">
                                      <mat-icon>volume_up</mat-icon>
                                      <span>{{ file }}</span>
                                    </div>
                                    <div class="audio-controls">
                                      <button mat-icon-button (click)="playAudio(lang, 'sfx', file)">
                                        <mat-icon>play_arrow</mat-icon>
                                      </button>
                                      <button mat-icon-button (click)="downloadAudio(lang, 'sfx', file)">
                                        <mat-icon>download</mat-icon>
                                      </button>
                                    </div>
                                  </mat-card-content>
                                </mat-card>
                              }
                            </div>
                          } @else {
                            <div class="empty-audio">
                              <mat-icon>volume_up</mat-icon>
                              <p>No sound effects generated yet</p>
                              <button mat-raised-button color="primary" (click)="generateSFX(lang)">
                                <mat-icon>volume_up</mat-icon>
                                Generate SFX
                              </button>
                            </div>
                          }
                        </div>
                      </mat-tab>

                      <!-- Master Audio Tab -->
                      <mat-tab label="Master Audio">
                        <div class="tab-content">
                          @if (audioData()?.audio_files?.master) {
                            <div class="master-audio">
                              <mat-card>
                                <mat-card-header>
                                  <mat-card-title>Master Audio</mat-card-title>
                                  <mat-card-subtitle>Mixed and normalized master track</mat-card-subtitle>
                                </mat-card-header>
                                <mat-card-content>
                                  <div class="master-controls">
                                    <button mat-raised-button color="primary" (click)="playMasterAudio(lang)">
                                      <mat-icon>play_circle</mat-icon>
                                      Play Master
                                    </button>
                                    <button mat-button (click)="downloadAudio(lang, 'master', audioData().audio_files.master)">
                                      <mat-icon>download</mat-icon>
                                      Download
                                    </button>
                                    <button mat-button (click)="remixAudio(lang)">
                                      <mat-icon>refresh</mat-icon>
                                      Re-mix
                                    </button>
                                  </div>
                                </mat-card-content>
                              </mat-card>
                            </div>
                          } @else {
                            <div class="empty-audio">
                              <mat-icon>tune</mat-icon>
                              <p>No master audio mixed yet</p>
                              <button mat-raised-button color="primary" (click)="mixAudio(lang)">
                                <mat-icon>tune</mat-icon>
                                Mix Master Audio
                              </button>
                            </div>
                          }
                        </div>
                      </mat-tab>
                    </mat-tab-group>
                  </div>
                }
              </div>
            </mat-tab>
          }
        </mat-tab-group>
      }
    </div>
  `,
  styles: [`
    .audio-page {
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

    .workspace-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 16px 0;
      border-bottom: 1px solid #e8e8e8;
      margin-bottom: 24px;
    }

    .workspace-header h2 {
      margin: 0;
      font-size: 1.25rem;
    }

    .workspace-actions {
      display: flex;
      gap: 12px;
    }

    .tab-content {
      padding: 24px 0;
    }

    .audio-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .audio-item {
      transition: box-shadow 0.2s ease;
    }

    .audio-item:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .audio-info {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;
    }

    .audio-info mat-icon {
      color: #3f51b5;
    }

    .audio-controls {
      display: flex;
      gap: 8px;
    }

    .empty-audio {
      text-align: center;
      padding: 48px 24px;
    }

    .empty-audio mat-icon {
      font-size: 48px;
      width: 48px;
      height: 48px;
      color: #999;
      margin-bottom: 16px;
    }

    .empty-audio p {
      margin: 0 0 16px;
      color: #666;
    }

    .master-audio {
      margin-top: 16px;
    }

    .master-controls {
      display: flex;
      gap: 12px;
      flex-wrap: wrap;
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
      .workspace-header {
        flex-direction: column;
        align-items: flex-start;
      }

      .workspace-actions {
        width: 100%;
      }

      .workspace-actions button {
        width: 100%;
      }
    }
  `],
})
export class AudioComponent implements OnInit {
  projectId = signal<string>('');
  generatingAll = signal(false);
  generatingLanguages = signal<Set<string>>(new Set());
  mixingLanguages = signal<Set<string>>(new Set());

  languages = signal<string[]>([]);
  audioData = signal<any>(null);

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
      }
    });
  }

  loadLanguages(): void {
    this.apiService.getLanguages(this.projectIdParam).subscribe({
      next: (langs) => this.languages.set(langs),
    });
  }

  async loadAudioData(lang: string): Promise<void> {
    try {
      const data = await this.apiService.getLanguageAudio(this.projectIdParam, lang).toPromise();
      this.audioData.set(data);
    } catch {
      this.audioData.set(null);
    }
  }

  generatingLanguage(lang: string): boolean {
    return this.generatingLanguages().has(lang);
  }

  mixing(lang: string): boolean {
    return this.mixingLanguages().has(lang);
  }

  async generateAllAudio(): Promise<void> {
    this.generatingAll.set(true);
    try {
      for (const lang of this.languages()) {
        await this.generateAllForLanguage(lang);
      }
      this.notificationService.showSuccess('All audio generation started');
    } catch {
      this.notificationService.showError('Failed to start audio generation');
    } finally {
      this.generatingAll.set(false);
    }
  }

  async generateAllForLanguage(lang: string): Promise<void> {
    this.generatingLanguages.update(set => new Set([...set, lang]));
    try {
      await this.apiService.generateTTS(this.projectIdParam, { language: lang }).toPromise();
      await this.apiService.generateMusic(this.projectIdParam, { language: lang }).toPromise();
      await this.apiService.generateSFX(this.projectIdParam, { language: lang }).toPromise();
      this.notificationService.showSuccess(`Audio generation started for ${lang}`);
    } catch {
      this.notificationService.showError(`Failed to generate audio for ${lang}`);
    } finally {
      this.generatingLanguages.update(set => {
        const newSet = new Set(set);
        newSet.delete(lang);
        return newSet;
      });
    }
  }

  async generateTTS(lang: string): Promise<void> {
    try {
      await this.apiService.generateTTS(this.projectIdParam, { language: lang }).toPromise();
      this.notificationService.showSuccess('TTS generation started');
    } catch {
      this.notificationService.showError('Failed to generate TTS');
    }
  }

  async generateMusic(lang: string): Promise<void> {
    try {
      await this.apiService.generateMusic(this.projectIdParam, { language: lang }).toPromise();
      this.notificationService.showSuccess('Music generation started');
    } catch {
      this.notificationService.showError('Failed to generate music');
    }
  }

  async generateSFX(lang: string): Promise<void> {
    try {
      await this.apiService.generateSFX(this.projectIdParam, { language: lang }).toPromise();
      this.notificationService.showSuccess('SFX generation started');
    } catch {
      this.notificationService.showError('Failed to generate SFX');
    }
  }

  async mixAudio(lang: string): Promise<void> {
    this.mixingLanguages.update(set => new Set([...set, lang]));
    try {
      await this.apiService.mixAudio(this.projectIdParam, { language: lang }).toPromise();
      this.notificationService.showSuccess('Audio mixing started');
      await this.loadAudioData(lang);
    } catch {
      this.notificationService.showError('Failed to mix audio');
    } finally {
      this.mixingLanguages.update(set => {
        const newSet = new Set(set);
        newSet.delete(lang);
        return newSet;
      });
    }
  }

  async remixAudio(lang: string): Promise<void> {
    await this.mixAudio(lang);
  }

  async playAudio(lang: string, type: string, file: string): Promise<void> {
    // Would play audio
  }

  async playMasterAudio(lang: string): Promise<void> {
    // Would play master audio
  }

  async downloadAudio(lang: string, type: string, file: string): Promise<void> {
    // Would download audio
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }
}