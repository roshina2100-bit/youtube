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

import { ApiService } from '@core/services/api.service';
import { NotificationService } from '@core/services/notification.service';

interface StoryGraph {
  story_id: string;
  title: string;
  summary: string;
  source_language: string;
  acts: Act[];
  characters: CharacterRef[];
  locations: LocationRef[];
  events: Event[];
  themes: Theme[];
  relationships: Relationship[];
  cultural_context: CulturalContext;
}

interface Act {
  act_id: string;
  title: string;
  order: number;
  summary: string;
  scenes: string[];
  characters: string[];
  locations: string[];
  themes: string[];
  start_time: number;
  end_time: number;
}

interface CharacterRef {
  character_id: string;
  canonical_name: string;
  aliases: string[];
  role: string;
  importance: string;
  first_appearance: string;
  description: string;
}

interface LocationRef {
  location_id: string;
  name: string;
  description: string;
  type: string;
  scenes: string[];
}

interface Event {
  event_id: string;
  time: string;
  description: string;
  scene_id: string;
  characters: string[];
  location_id: string;
  importance: string;
}

interface Theme {
  name: string;
  prominence: number;
  description: string;
  related_characters: string[];
  related_scenes: string[];
}

interface Relationship {
  character_id: string;
  related_character_id: string;
  type: string;
  description: string;
  strength: number;
}

interface CulturalContext {
  period: string;
  culture: string;
  religion: string;
  mythology: string;
  historical_notes: string;
  cultural_sensitivities: string[];
  source_facts: string[];
  ai_interpretations: string[];
  visualization_choices: string[];
}

@Component({
  selector: 'app-story',
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
  ],
  template: `
    <div class="story-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Story Intelligence</h1>
          <p class="subtitle">Analyze and explore the story structure</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="analyzeStory()" [disabled]="analyzing()">
            @if (analyzing()) {
              <mat-spinner diameter="20"></mat-spinner>
              Analyzing...
            } @else {
              <mat-icon>psychology</mat-icon>
              Analyze Story
            }
          </button>
          <button mat-button (click)="extractCharacters()" [disabled]="extractingCharacters()">
            @if (extractingCharacters()) {
              <mat-spinner diameter="16"></mat-spinner>
              Extract Characters
            } @else {
              <mat-icon>person_add</mat-icon>
              Extract Characters
            }
          </button>
        </div>
      </header>

      @if (story(); as s) {
        <div class="story-overview">
          <mat-card>
            <mat-card-header>
              <mat-card-title>{{ s.title }}</mat-card-title>
              <mat-card-subtitle>{{ s.summary }}</mat-card-subtitle>
            </mat-card-header>
            <mat-card-content>
              <div class="overview-stats">
                <div class="stat">
                  <mat-icon>menu_book</mat-icon>
                  <span>{{ s.acts.length }} Acts</span>
                </div>
                <div class="stat">
                  <mat-icon>people</mat-icon>
                  <span>{{ s.characters.length }} Characters</span>
                </div>
                <div class="stat">
                  <mat-icon>location_on</mat-icon>
                  <span>{{ s.locations.length }} Locations</span>
                </div>
                <div class="stat">
                  <mat-icon>event</mat-icon>
                  <span>{{ s.events.length }} Events</span>
                </div>
                <div class="stat">
                  <mat-icon>psychology</mat-icon>
                  <span>{{ s.themes.length }} Themes</span>
                </div>
              </div>
            </mat-card-content>
          </mat-card>

          <mat-tab-group>
            <!-- Acts Tab -->
            <mat-tab label="Acts">
              <div class="tab-content">
                @for (act of story().acts; track act.act_id) {
                  <mat-expansion-panel>
                    <mat-expansion-panel-header>
                      <mat-panel-title>
                        <mat-icon>menu_book</mat-icon>
                        Act {{ act.order }}: {{ act.title }}
                      </mat-panel-title>
                      <mat-panel-description>
                        {{ act.scenes.length }} scenes • {{ act.characters.length }} characters
                      </mat-panel-description>
                    </mat-expansion-panel-header>
                    <div class="act-content">
                      <p>{{ act.summary }}</p>
                      <div class="act-meta">
                        <span><mat-icon>schedule</mat-icon> {{ formatTime(act.start_time) }} - {{ formatTime(act.end_time) }}</span>
                        <span><mat-icon>location_on</mat-icon> {{ act.locations.length }} locations</span>
                        <span><mat-icon>psychology</mat-icon> {{ act.themes.length }} themes</span>
                      </div>
                    </div>
                  </mat-expansion-panel>
                }
              </div>
            </mat-tab>

            <!-- Characters Tab -->
            <mat-tab label="Characters">
              <div class="tab-content">
                <div class="characters-grid">
                  @for (char of story().characters; track char.character_id) {
                    <mat-card class="character-card">
                      <mat-card-header>
                        <mat-card-title>{{ char.canonical_name }}</mat-card-title>
                        <mat-card-subtitle>{{ char.role | titlecase }} • {{ char.importance }}</mat-card-subtitle>
                      </mat-card-header>
                      <mat-card-content>
                        <p>{{ char.description }}</p>
                        @if (char.aliases.length > 0) {
                          <div class="aliases">
                            <strong>Aliases:</strong> {{ char.aliases.join(', ') }}
                          </div>
                        }
                      </mat-card-content>
                      <mat-card-actions>
                        <button mat-button [routerLink]="['/projects', projectId(), 'characters', char.character_id]">
                          <mat-icon>visibility</mat-icon>
                          View Details
                        </button>
                      </mat-card-actions>
                    </mat-card>
                  }
                </div>
              </div>
            </mat-tab>

            <!-- Locations Tab -->
            <mat-tab label="Locations">
              <div class="tab-content">
                <div class="locations-grid">
                  @for (loc of story().locations; track loc.location_id) {
                    <mat-card class="location-card">
                      <mat-card-header>
                        <mat-card-title>{{ loc.name }}</mat-card-title>
                        <mat-card-subtitle>{{ loc.type }}</mat-card-subtitle>
                      </mat-card-header>
                      <mat-card-content>
                        <p>{{ loc.description }}</p>
                        <div class="location-meta">
                          <span><mat-icon>movie</mat-icon> {{ loc.scenes.length }} scenes</span>
                        </div>
                      </mat-card-content>
                    </mat-card>
                  }
                </div>
              </div>
            </mat-tab>

            <!-- Events Tab -->
            <mat-tab label="Events">
              <div class="tab-content">
                <div class="timeline">
                  @for (event of story().events; track event.event_id) {
                    <div class="timeline-item">
                      <div class="timeline-marker"></div>
                      <div class="timeline-content">
                        <div class="timeline-time">{{ event.time }}</div>
                        <div class="timeline-description">{{ event.description }}</div>
                        <div class="timeline-meta">
                          <span><mat-icon>person</mat-icon> {{ event.characters.length }} characters</span>
                          <span><mat-icon>location_on</mat-icon> {{ event.location_id }}</span>
                        </div>
                      </div>
                    </div>
                  }
                </div>
              </div>
            </mat-tab>

            <!-- Themes Tab -->
            <mat-tab label="Themes">
              <div class="tab-content">
                <div class="themes-grid">
                  @for (theme of story().themes; track theme.name) {
                    <mat-card class="theme-card">
                      <mat-card-header>
                        <mat-card-title>{{ theme.name }}</mat-card-title>
                        <mat-card-subtitle>Prominence: {{ (theme.prominence * 100).toFixed(0) }}%</mat-card-subtitle>
                      </mat-card-header>
                      <mat-card-content>
                        <p>{{ theme.description }}</p>
                        <div class="theme-relations">
                          <span><mat-icon>people</mat-icon> {{ theme.related_characters.length }} characters</span>
                          <span><mat-icon>movie</mat-icon> {{ theme.related_scenes.length }} scenes</span>
                        </div>
                      </mat-card-content>
                    </mat-card>
                  }
                </div>
              </div>
            </mat-tab>

            <!-- Relationships Tab -->
            <mat-tab label="Relationships">
              <div class="tab-content">
                <div class="relationships-list">
                  @for (rel of story().relationships; track rel.character_id + rel.related_character_id) {
                    <mat-card class="relationship-card">
                      <mat-card-content>
                        <div class="relationship-main">
                          <span class="character-name">{{ getCharacterName(rel.character_id) }}</span>
                          <mat-icon class="relationship-type">{{ getRelationshipIcon(rel.type) }}</mat-icon>
                          <span class="character-name">{{ getCharacterName(rel.related_character_id) }}</span>
                        </div>
                        <div class="relationship-details">
                          <span class="relationship-type-label">{{ rel.type | titlecase }}</span>
                          <span class="relationship-strength">Strength: {{ (rel.strength * 100).toFixed(0) }}%</span>
                        </div>
                        <p class="relationship-description">{{ rel.description }}</p>
                      </mat-card-content>
                    </mat-card>
                  }
                </div>
              </div>
            </mat-tab>

            <!-- Cultural Context Tab -->
            <mat-tab label="Cultural Context">
              <div class="tab-content">
                <mat-card>
                  <mat-card-header>
                    <mat-card-title>Cultural Context</mat-card-title>
                  </mat-card-header>
                  <mat-card-content>
                    <div class="cultural-grid">
                      <div class="cultural-item">
                        <h3>Period</h3>
                        <p>{{ story().cultural_context.period || 'Not specified' }}</p>
                      </div>
                      <div class="cultural-item">
                        <h3>Culture</h3>
                        <p>{{ story().cultural_context.culture || 'Not specified' }}</p>
                      </div>
                      <div class="cultural-item">
                        <h3>Religion</h3>
                        <p>{{ story().cultural_context.religion || 'Not specified' }}</p>
                      </div>
                      <div class="cultural-item">
                        <h3>Mythology</h3>
                        <p>{{ story().cultural_context.mythology || 'Not specified' }}</p>
                      </div>
                    </div>

                    <mat-divider></mat-divider>

                    <div class="cultural-section">
                      <h3>Historical Notes</h3>
                      <p>{{ story().cultural_context.historical_notes || 'None' }}</p>
                    </div>

                    <div class="cultural-section">
                      <h3>Cultural Sensitivities</h3>
                      <mat-chip-set>
                        @for (sensitivity of story().cultural_context.cultural_sensitivities; track sensitivity) {
                          <mat-chip>{{ sensitivity }}</mat-chip>
                        }
                      </mat-chip-set>
                    </div>

                    <div class="cultural-section">
                      <h3>Source Facts</h3>
                      <ul>
                        @for (fact of story().cultural_context.source_facts; track fact) {
                          <li>{{ fact }}</li>
                        }
                      </ul>
                    </div>

                    <div class="cultural-section">
                      <h3>AI Interpretations</h3>
                      <ul>
                        @for (interp of story().cultural_context.ai_interpretations; track interp) {
                          <li>{{ interp }}</li>
                        }
                      </ul>
                    </div>

                    <div class="cultural-section">
                      <h3>Visualization Choices</h3>
                      <ul>
                        @for (choice of story().cultural_context.visualization_choices; track choice) {
                          <li>{{ choice }}</li>
                        }
                      </ul>
                    </div>
                  </mat-card-content>
                </mat-card>
              </div>
            </mat-tab>
          </mat-tab-group>
        </div>
      } @else {
        <mat-card class="empty-state">
          <mat-card-content>
            <mat-icon>menu_book</mat-icon>
            <h3>No story analyzed yet</h3>
            <p>Import a transcript and analyze the story to get started</p>
            <button mat-raised-button color="primary" (click)="analyzeStory()">
              <mat-icon>psychology</mat-icon>
              Analyze Story
            </button>
          </mat-card-content>
        </mat-card>
      }
    </div>
  `,
  styles: [`
    .story-page {
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

    .story-overview {
      margin-bottom: 24px;
    }

    .overview-stats {
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
      margin-top: 16px;
    }

    .stat {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 12px 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .stat mat-icon {
      color: #3f51b5;
    }

    .tab-content {
      padding: 24px 0;
    }

    .act-content {
      padding: 16px 0;
    }

    .act-meta {
      display: flex;
      gap: 16px;
      margin-top: 12px;
      font-size: 0.8125rem;
      color: #666;
    }

    .act-meta span {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .characters-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
    }

    .character-card {
      transition: box-shadow 0.2s ease;
    }

    .character-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .aliases {
      margin-top: 8px;
      font-size: 0.8125rem;
      color: #666;
    }

    .locations-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 16px;
    }

    .location-meta {
      margin-top: 12px;
      font-size: 0.8125rem;
      color: #666;
    }

    .timeline {
      display: flex;
      flex-direction: column;
      gap: 16px;
    }

    .timeline-item {
      display: flex;
      gap: 16px;
      padding: 16px;
      background: #fafafa;
      border-radius: 8px;
    }

    .timeline-marker {
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: #3f51b5;
      margin-top: 4px;
      flex-shrink: 0;
    }

    .timeline-content {
      flex: 1;
    }

    .timeline-time {
      font-size: 0.75rem;
      font-weight: 500;
      color: #3f51b5;
      font-family: 'Roboto Mono', monospace;
    }

    .timeline-description {
      margin: 4px 0;
      color: #333;
    }

    .timeline-meta {
      display: flex;
      gap: 16px;
      font-size: 0.75rem;
      color: #666;
    }

    .themes-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
      gap: 16px;
    }

    .theme-card {
      transition: box-shadow 0.2s ease;
    }

    .theme-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .theme-relations {
      display: flex;
      gap: 16px;
      margin-top: 12px;
      font-size: 0.8125rem;
      color: #666;
    }

    .theme-relations span {
      display: flex;
      align-items: center;
      gap: 4px;
    }

    .relationships-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .relationship-card {
      transition: box-shadow 0.2s ease;
    }

    .relationship-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .relationship-main {
      display: flex;
      align-items: center;
      gap: 12px;
      margin-bottom: 8px;
    }

    .character-name {
      font-weight: 600;
      color: #333;
    }

    .relationship-type {
      color: #3f51b5;
      font-size: 24px;
    }

    .relationship-details {
      display: flex;
      gap: 16px;
      font-size: 0.8125rem;
      color: #666;
    }

    .relationship-type-label {
      text-transform: capitalize;
      font-weight: 500;
    }

    .relationship-strength {
      color: #3f51b5;
      font-weight: 500;
    }

    .relationship-description {
      margin: 8px 0 0;
      color: #666;
      font-size: 0.875rem;
    }

    .cultural-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 16px;
      margin-bottom: 24px;
    }

    .cultural-item {
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
    }

    .cultural-item h3 {
      margin: 0 0 8px;
      font-size: 0.875rem;
      font-weight: 600;
      color: #666;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .cultural-item p {
      margin: 0;
      color: #333;
    }

    .cultural-section {
      margin-bottom: 24px;
    }

    .cultural-section h3 {
      margin: 0 0 12px;
      font-size: 1rem;
      font-weight: 600;
      color: #333;
    }

    .cultural-section p {
      margin: 0;
      color: #666;
    }

    .cultural-section ul {
      margin: 0;
      padding-left: 20px;
      color: #666;
    }

    .cultural-section li {
      margin-bottom: 4px;
    }

    @media (max-width: 768px) {
      .cultural-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class StoryComponent implements OnInit {
  projectId = signal<string>('');
  analyzing = signal(false);
  extractingCharacters = signal(false);

  story = signal<any>(null);

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
        this.loadStory();
      }
    });
  }

  loadStory(): void {
    this.apiService.getStory(this.projectIdParam).subscribe({
      next: (s) => this.story.set(s),
      error: () => {},
    });
  }

  async analyzeStory(): Promise<void> {
    this.analyzing.set(true);
    try {
      await this.apiService.analyzeStory(this.projectIdParam, {}).toPromise();
      this.notificationService.showSuccess('Story analysis started');
      // Poll for completion or wait for notification
      setTimeout(() => this.loadStory(), 5000);
    } catch {
      this.notificationService.showError('Failed to start story analysis');
    } finally {
      this.analyzing.set(false);
    }
  }

  async extractCharacters(): Promise<void> {
    this.extractingCharacters.set(true);
    try {
      await this.apiService.extractCharacters(this.projectIdParam, {}).toPromise();
      this.notificationService.showSuccess('Character extraction started');
    } catch {
      this.notificationService.showError('Failed to start character extraction');
    } finally {
      this.extractingCharacters.set(false);
    }
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }

  formatTime(seconds: number): string {
    const hrs = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    return `${hrs.toString().padStart(2, '0')}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  getCharacterName(characterId: string): string {
    const story = this.story();
    if (!story) return characterId;
    const char = story.characters.find((c: any) => c.character_id === characterId);
    return char?.canonical_name || characterId;
  }

  getRelationshipIcon(type: string): string {
    const icons: Record<string, string> = {
      family: 'family_restroom',
      romantic: 'favorite',
      rivalry: 'sports_mma',
      mentor: 'school',
      ally: 'groups',
      enemy: 'block',
    };
    return icons[type] || 'link';
  }
}