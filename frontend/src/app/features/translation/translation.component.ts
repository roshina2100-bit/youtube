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

interface LanguageWorkspace {
  language: string;
  scenes: Record<string, SceneTranslation>;
  semantic_review: SemanticReview;
  voice_prompts: Record<string, Record<string, string>>;
  music_prompts: Record<string, string>;
  status: string;
  completed_scenes: number;
  total_scenes: number;
}

interface SceneTranslation {
  scene_id: string;
  language: string;
  version: string;
  source_language: string;
  narration: string;
  dialogue: any[];
  character_names: Record<string, string>;
  location_name: string;
  cultural_notes: string;
  semantic_review: SemanticReview;
  voice_prompts: Record<string, string>;
  translated_by: string;
  translated_at: string;
  reviewed_by: string | null;
  reviewed_at: string | null;
}

interface SemanticReview {
  reviewed: boolean;
  reviewed_at: string | null;
  reviewed_by: string | null;
  checks: SemanticCheck[];
  issues: string[];
  flags: string[];
  status: string;
  notes: string;
}

interface SemanticCheck {
  check_name: string;
  passed: boolean;
  details: string;
  severity: string;
}

@Component({
  selector: 'app-translation',
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
    <div class="translation-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Translation</h1>
          <p class="subtitle">Translate and review content for all target languages</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="translateAll()" [disabled]="translating()">
            @if (translating()) {
              <mat-spinner diameter="20"></mat-spinner>
              Translating...
            } @else {
              <mat-icon>translate</mat-icon>
              Translate All
            }
          </button>
        </div>
      </header>

      @if (languages().length === 0) {
        <mat-card class="empty-state">
          <mat-card-content>
            <mat-icon>translate</mat-icon>
            <h3>No translations yet</h3>
            <p>Generate scenes first, then translate to target languages</p>
          </mat-card-content>
        </mat-card>
      } @else {
        <div class="languages-overview">
          <h2>Target Languages</h2>
          <div class="language-chips">
            @for (lang of languages(); track lang) {
              <mat-chip [class.selected]="selectedLanguage() === lang" (click)="selectLanguage(lang)">
                {{ lang.toUpperCase() }}
                @if (getWorkspace(lang)?.completed_scenes > 0) {
                  <span class="chip-progress">{{ getWorkspace(lang)?.completed_scenes }}/{{ getWorkspace(lang)?.total_scenes }}</span>
                }
              </mat-chip>
            }
          </div>
        </div>

        @if (selectedLanguage(); as lang) {
          <div class="language-workspace">
            <div class="workspace-header">
              <h2>{{ lang.toUpperCase() }} Translation</h2>
              <div class="workspace-progress">
                <span>{{ getWorkspace(lang)?.completed_scenes || 0 }} / {{ getWorkspace(lang)?.total_scenes || 0 }} scenes completed</span>
                <mat-progress-bar mode="determinate" [value]="getProgress(lang)"></mat-progress-bar>
              </div>
            </div>

            <mat-tab-group>
              <!-- Scenes Tab -->
              <mat-tab label="Scenes">
                <div class="tab-content">
                  @for (scene of getSceneTranslations(lang); track scene.scene_id) {
                    <mat-expansion-panel [expanded]="expandedScene() === scene.scene_id" (opened)="expandedScene.set(scene.scene_id)" (closed)="expandedScene.set('')">
                      <mat-expansion-panel-header>
                        <mat-panel-title>
                          <mat-icon>movie</mat-icon>
                          Scene {{ getSceneOrder(scene.scene_id) }}: {{ getSceneTitle(scene.scene_id) }}
                        </mat-panel-title>
                        <mat-panel-description>
                          <mat-chip [class]="'status-' + scene.semantic_review.status">{{ scene.semantic_review.status | titlecase }}</mat-chip>
                        </mat-panel-description>
                      </mat-expansion-panel-header>
                      <div class="scene-translation-content">
                        <div class="translation-field">
                          <label>Narration</label>
                          <textarea [(ngModel)]="scene.narration" rows="3" placeholder="Translated narration..."></textarea>
                        </div>
                        <div class="translation-field">
                          <label>Location</label>
                          <input [(ngModel)]="scene.location_name" placeholder="Translated location name">
                        </div>
                        <div class="translation-field">
                          <label>Cultural Notes</label>
                          <textarea [(ngModel)]="scene.cultural_notes" rows="2" placeholder="Cultural context notes..."></textarea>
                        </div>
                        <div class="translation-field">
                          <label>Character Names</label>
                          <div class="character-names">
                            @for (charId of getCharacterIds(); track charId) {
                              <div class="character-name-row">
                                <span>{{ getCharacterName(charId) }}</span>
                                <input [(ngModel)]="scene.character_names[charId]" placeholder="Translated name">
                              </div>
                            }
                          </div>
                        </div>
                        <div class="translation-field">
                          <label>Dialogue</label>
                          <div class="dialogue-list">
                            @for (dlg of scene.dialogue; track dlg.speaker) {
                              <div class="dialogue-item">
                                <span class="dialogue-speaker">{{ scene.character_names[dlg.speaker] || dlg.speaker }}:</span>
                                <input [(ngModel)]="dlg.text" placeholder="Translated dialogue">
                              </div>
                            }
                          </div>
                        </div>
                        <div class="scene-actions">
                          <button mat-button (click)="saveTranslation(lang, scene.scene_id)">
                            <mat-icon>save</mat-icon>
                            Save Translation
                          </button>
                          <button mat-button (click)="reviewTranslation(lang, scene.scene_id)" [disabled]="reviewing(scene.scene_id)">
                            @if (reviewing(scene.scene_id)) {
                              <mat-spinner diameter="16"></mat-spinner>
                              Reviewing...
                            } @else {
                              <mat-icon>fact_check</mat-icon>
                              Semantic Review
                            }
                          </button>
                          <button mat-button (click)="approveTranslation(lang, scene.scene_id)" [disabled]="scene.semantic_review.status === 'approved'">
                            <mat-icon>check_circle</mat-icon>
                            Approve
                          </button>
                        </div>
                      </div>
                    </mat-expansion-panel>
                  }
                </div>
              </mat-tab>

              <!-- Semantic Review Tab -->
              <mat-tab label="Semantic Review">
                <div class="tab-content">
                  @for (scene of getSceneTranslations(lang); track scene.scene_id) {
                    <mat-expansion-panel>
                      <mat-expansion-panel-header>
                        <mat-panel-title>
                          Scene {{ getSceneOrder(scene.scene_id) }}: {{ getSceneTitle(scene.scene_id) }}
                        </mat-panel-title>
                        <mat-panel-description>
                          <mat-chip [class]="'status-' + scene.semantic_review.status">{{ scene.semantic_review.status | titlecase }}</mat-chip>
                        </mat-panel-description>
                      </mat-expansion-panel-header>
                      <div class="review-content">
                        <div class="review-summary">
                          <mat-chip [class]="'status-' + scene.semantic_review.status">{{ scene.semantic_review.status | titlecase }}</mat-chip>
                          <span>Checks: {{ countPassedChecks(scene.semantic_review.checks) }}/{{ scene.semantic_review.checks.length }} passed</span>
                        </div>
                        <div class="review-checks">
                          @for (check of scene.semantic_review.checks; track check.check_name) {
                            <div class="review-check" [class]="'severity-' + check.severity">
                              <mat-icon [class]="check.passed ? 'passed' : 'failed'">
                                {{ check.passed ? 'check_circle' : 'cancel' }}
                              </mat-icon>
                              <span class="check-name">{{ check.check_name | titlecase }}</span>
                              <span class="check-details">{{ check.details }}</span>
                              <span class="check-severity">{{ check.severity }}</span>
                            </div>
                          }
                        </div>
                        @if (scene.semantic_review.issues.length > 0) {
                          <div class="review-issues">
                            <h4>Issues</h4>
                            <ul>
                              @for (issue of scene.semantic_review.issues; track issue) {
                                <li>{{ issue }}</li>
                              }
                            </ul>
                          </div>
                        }
                        <div class="review-actions">
                          <button mat-button (click)="approveTranslation(lang, scene.scene_id)" [disabled]="scene.semantic_review.status === 'approved'">
                            <mat-icon>check_circle</mat-icon>
                            Approve
                          </button>
                          <button mat-button (click)="requestChanges(lang, scene.scene_id)">
                            <mat-icon>edit</mat-icon>
                            Request Changes
                          </button>
                        </div>
                      </div>
                    </mat-expansion-panel>
                  }
                </div>
              </mat-tab>

              <!-- Voice Prompts Tab -->
              <mat-tab label="Voice Prompts">
                <div class="tab-content">
                  <div class="voice-prompts">
                    @for (speaker of getSpeakers(); track speaker) {
                      <mat-card>
                        <mat-card-header>
                          <mat-card-title>{{ speaker }}</mat-card-title>
                        </mat-card-header>
                        <mat-card-content>
                          <mat-form-field appearance="outline" class="full-width">
                            <mat-label>Voice Prompt</mat-label>
                            <textarea [ngModel]="getVoicePrompt(lang, speaker)" (ngModelChange)="setVoicePrompt(lang, speaker, $event)" rows="3" placeholder="Describe the voice characteristics..."></textarea>
                          </mat-form-field>
                        </mat-card-content>
                      </mat-card>
                    }
                  </div>
                </div>
              </mat-tab>
            </mat-tab-group>
          </div>
        }
      }
    </div>
  `,
  styles: [`
    .translation-page {
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

    .languages-overview {
      margin-bottom: 24px;
    }

    .languages-overview h2 {
      margin: 0 0 16px;
      font-size: 1.25rem;
    }

    .language-chips {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
    }

    .language-chips mat-chip {
      cursor: pointer;
      transition: all 0.2s ease;
    }

    .language-chips mat-chip:hover {
      background: #e3f2fd;
    }

    .language-chips mat-chip.selected {
      background: #3f51b5;
      color: white;
    }

    .chip-progress {
      margin-left: 8px;
      font-size: 0.6875rem;
      opacity: 0.8;
    }

    .language-workspace {
      background: white;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.08);
      border: 1px solid #e8e8e8;
      overflow: hidden;
    }

    .workspace-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 24px;
      border-bottom: 1px solid #e8e8e8;
    }

    .workspace-header h2 {
      margin: 0;
      font-size: 1.25rem;
    }

    .workspace-progress {
      display: flex;
      flex-direction: column;
      gap: 8px;
      min-width: 200px;
    }

    .workspace-progress span {
      font-size: 0.8125rem;
      color: #666;
    }

    .tab-content {
      padding: 24px 0;
    }

    .scene-translation-content {
      padding: 16px 0;
    }

    .translation-field {
      margin-bottom: 16px;
    }

    .translation-field label {
      display: block;
      margin-bottom: 8px;
      font-weight: 500;
      color: #333;
    }

    .translation-field textarea,
    .translation-field input {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #ddd;
      border-radius: 8px;
      font-size: 1rem;
      font-family: inherit;
    }

    .character-names {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .character-name-row {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .character-name-row span {
      min-width: 120px;
      font-weight: 500;
      color: #333;
    }

    .character-name-row input {
      flex: 1;
    }

    .dialogue-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }

    .dialogue-item {
      display: flex;
      gap: 12px;
      align-items: center;
    }

    .dialogue-speaker {
      min-width: 120px;
      font-weight: 500;
      color: #333;
    }

    .dialogue-item input {
      flex: 1;
    }

    .scene-actions {
      display: flex;
      gap: 12px;
      padding-top: 16px;
      margin-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .review-content {
      padding: 16px 0;
    }

    .review-summary {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }

    .review-checks {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 16px;
    }

    .review-check {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 12px;
      background: #fafafa;
      border-radius: 8px;
    }

    .review-check.severity-error {
      border-left: 4px solid #c62828;
    }

    .review-check.severity-warning {
      border-left: 4px solid #e65100;
    }

    .review-check.severity-info {
      border-left: 4px solid #1565c0;
    }

    .review-check .passed {
      color: #2e7d32;
    }

    .review-check .failed {
      color: #c62828;
    }

    .check-name {
      font-weight: 500;
      min-width: 180px;
    }

    .check-details {
      flex: 1;
      color: #666;
      font-size: 0.8125rem;
    }

    .check-severity {
      font-size: 0.6875rem;
      text-transform: uppercase;
      font-weight: 500;
    }

    .review-issues {
      margin-bottom: 16px;
    }

    .review-issues h4 {
      margin: 0 0 8px;
      font-size: 0.875rem;
    }

    .review-issues ul {
      margin: 0;
      padding-left: 20px;
      color: #c62828;
    }

    .review-actions {
      display: flex;
      gap: 12px;
      padding-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .voice-prompts {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    @media (max-width: 768px) {
      .workspace-header {
        flex-direction: column;
        align-items: flex-start;
      }
    }
  `],
})
export class TranslationComponent implements OnInit {
  projectId = signal<string>('');
  translating = signal(false);
  reviewingScenes = signal<Set<string>>(new Set());
  expandedScene = signal<string>('');
  selectedLanguage = signal<string>('');

  languages = signal<string[]>([]);
  workspaces = signal<Record<string, any>>({});

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
      next: (langs) => {
        this.languages.set(langs);
        if (langs.length > 0 && !this.selectedLanguage()) {
          this.selectLanguage(langs[0]);
        }
      },
    });
  }

  async translateAll(): Promise<void> {
    this.translating.set(true);
    try {
      await this.apiService.translateProject(this.projectIdParam, this.languages()).toPromise();
      this.notificationService.showSuccess('Translation started');
    } catch {
      this.notificationService.showError('Failed to start translation');
    } finally {
      this.translating.set(false);
    }
  }

  selectLanguage(lang: string): void {
    this.selectedLanguage.set(lang);
    this.loadWorkspace(lang);
  }

  loadWorkspace(lang: string): void {
    this.apiService.getLanguageWorkspace(this.projectIdParam, lang).subscribe({
      next: (ws) => {
        this.workspaces.update(wsMap => ({ ...wsMap, [lang]: ws }));
      },
      error: () => {},
    });
  }

  getWorkspace(lang: string) {
    return this.workspaces()[lang];
  }

  getProgress(lang: string): number {
    const ws = this.getWorkspace(lang);
    if (!ws || ws.total_scenes === 0) return 0;
    return (ws.completed_scenes / ws.total_scenes) * 100;
  }

  countPassedChecks(checks: Array<{ passed: boolean }> = []): number {
    return checks.filter(check => check.passed).length;
  }

  getSceneTranslations(lang: string) {
    const ws = this.getWorkspace(lang);
    if (!ws) return [];
    return Object.values(ws.scenes || {});
  }

  getSceneOrder(sceneId: string): number {
    // Would get from scene data
    return 1;
  }

  getSceneTitle(sceneId: string): string {
    return sceneId;
  }

  getCharacterIds(): string[] {
    return []; // Would get from story
  }

  getCharacterName(charId: string): string {
    return charId;
  }

  getSpeakers(): string[] {
    return ['narrator']; // Would get from transcript
  }

  getVoicePrompt(lang: string, speaker: string): string {
    const ws = this.getWorkspace(lang);
    return ws?.voice_prompts?.[speaker] || '';
  }

  setVoicePrompt(lang: string, speaker: string, prompt: string): void {
    const workspace = this.getWorkspace(lang);
    if (!workspace) return;
    this.workspaces.update(workspaces => ({
      ...workspaces,
      [lang]: {
        ...workspace,
        voice_prompts: { ...workspace.voice_prompts, [speaker]: prompt },
      },
    }));
  }

  async saveTranslation(lang: string, sceneId: string): Promise<void> {
    // Would save translation
  }

  async reviewTranslation(lang: string, sceneId: string): Promise<void> {
    this.reviewingScenes.update(set => new Set([...set, sceneId]));
    try {
      await this.apiService.reviewTranslation(this.projectIdParam, lang, sceneId).toPromise();
      this.notificationService.showSuccess('Semantic review completed');
      this.loadWorkspace(lang);
    } catch {
      this.notificationService.showError('Review failed');
    } finally {
      this.reviewingScenes.update(set => {
        const newSet = new Set(set);
        newSet.delete(sceneId);
        return newSet;
      });
    }
  }

  reviewing(sceneId: string): boolean {
    return this.reviewingScenes().has(sceneId);
  }

  async approveTranslation(lang: string, sceneId: string): Promise<void> {
    try {
      await this.apiService.approveTranslation(this.projectIdParam, lang, sceneId, true).toPromise();
      this.notificationService.showSuccess('Translation approved');
      this.loadWorkspace(lang);
    } catch {
      this.notificationService.showError('Failed to approve');
    }
  }

  async requestChanges(lang: string, sceneId: string): Promise<void> {
    // Would request changes
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }
}