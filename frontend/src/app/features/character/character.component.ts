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

interface CharacterBible {
  character_id: string;
  canonical_name: string;
  aliases: string[];
  role: string;
  importance: string;
  status: string;
  current_version: string;
  approved_version: string | null;
  reference_image: string | null;
  scenes: string[];
  versions: Record<string, CharacterVersion>;
  physical_appearance: PhysicalAppearance;
  clothing: Clothing;
  personality: Personality;
  relationships: any[];
  story_role: string;
  character_arc: string;
  visual_identity: string;
  negative_prompt: string;
  continuity_rules: ContinuityRules;
  prompt_template: string;
}

interface CharacterVersion {
  version: string;
  prompt: string;
  negative_prompt: string;
  image_path: string | null;
  image_metadata: any;
  reference_image_path: string | null;
  created_at: string;
  created_by: string;
  approved: boolean;
  approved_at: string | null;
  approved_by: string | null;
}

interface PhysicalAppearance {
  face: string;
  hair: string;
  skin: string;
  body: string;
  eyes: string;
  distinguishing_features: string[];
}

interface Clothing {
  upper: string;
  lower: string;
  footwear: string;
  outerwear: string;
  accessories: string[];
  jewelry: string[];
  headwear: string;
  props: string[];
}

interface Personality {
  traits: string[];
  emotions: string[];
  motivations: string[];
  fears: string[];
  quirks: string[];
}

interface ContinuityRules {
  locked_features: string[];
  variable_features: string[];
  forbidden_changes: string[];
}

@Component({
  selector: 'app-character',
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
    <div class="character-page">
      <header class="page-header">
        <button mat-icon-button (click)="goBack()" aria-label="Go back">
          <mat-icon>arrow_back</mat-icon>
        </button>
        <div>
          <h1>Characters</h1>
          <p class="subtitle">Manage character bibles, images, and approvals</p>
        </div>
        <div class="header-actions">
          <button mat-raised-button color="primary" (click)="extractCharacters()" [disabled]="extracting()">
            @if (extracting()) {
              <mat-spinner diameter="20"></mat-spinner>
              Extract Characters
            } @else {
              <mat-icon>person_add</mat-icon>
              Extract Characters
            }
          </button>
        </div>
      </header>

      @if (characters().length === 0 && !loading()) {
        <mat-card class="empty-state">
          <mat-card-content>
            <mat-icon>people</mat-icon>
            <h3>No characters yet</h3>
            <p>Extract characters from the story analysis to get started</p>
            <button mat-raised-button color="primary" (click)="extractCharacters()">
              <mat-icon>person_add</mat-icon>
              Extract Characters
            </button>
          </mat-card-content>
        </mat-card>
      } @else {
        <div class="characters-grid">
          @for (char of characters(); track char.character_id) {
            <mat-card class="character-card" [class.approved]="char.status === 'approved' || char.status === 'locked'">
              <mat-card-header>
                <mat-card-title>{{ char.canonical_name }}</mat-card-title>
                <mat-card-subtitle>{{ char.role | titlecase }} • {{ char.importance }}</mat-card-subtitle>
              </mat-card-header>
              <mat-card-content>
                <div class="character-status">
                  <mat-chip [class]="'status-' + char.status">{{ char.status | titlecase }}</mat-chip>
                  @if (char.approved_version) {
                    <mat-chip color="primary">Approved v{{ char.approved_version }}</mat-chip>
                  }
                </div>
                @if (char.reference_image) {
                  <img [src]="'assets/' + char.reference_image" alt="{{ char.canonical_name }}" class="reference-image">
                }
                <div class="character-meta">
                  <span><mat-icon>tag</mat-icon> {{ char.aliases.length }} aliases</span>
                  <span><mat-icon>movie</mat-icon> {{ char.scenes.length }} scenes</span>
                  <span><mat-icon>history</mat-icon> v{{ char.current_version }}</span>
                </div>
              </mat-card-content>
              <mat-card-actions>
                <button mat-button [routerLink]="['/projects', projectId(), 'characters', char.character_id]">
                  <mat-icon>visibility</mat-icon>
                  View Details
                </button>
                <button mat-button (click)="generatePrompt(char.character_id)" [disabled]="generatingPrompt(char.character_id)">
                  <mat-icon>auto_awesome</mat-icon>
                  Generate Prompt
                </button>
                <button mat-button (click)="generateImage(char.character_id)" [disabled]="generatingImage(char.character_id)">
                  <mat-icon>image</mat-icon>
                  Generate Image
                </button>
              </mat-card-actions>
            </mat-card>
          }
        </div>
      }
    </div>
  `,
  styles: [`
    .character-page {
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

    .characters-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
      gap: 20px;
    }

    .character-card {
      transition: box-shadow 0.2s ease;
    }

    .character-card:hover {
      box-shadow: 0 4px 16px rgba(0,0,0,0.12);
    }

    .character-card.approved {
      border: 2px solid #4caf50;
    }

    .character-status {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .reference-image {
      width: 100%;
      max-height: 200px;
      object-fit: cover;
      border-radius: 8px;
      margin: 12px 0;
    }

    .character-meta {
      display: flex;
      gap: 16px;
      font-size: 0.8125rem;
      color: #666;
    }

    .character-meta span {
      display: flex;
      align-items: center;
      gap: 4px;
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
      .characters-grid {
        grid-template-columns: 1fr;
      }
    }
  `],
})
export class CharacterComponent implements OnInit {
  projectId = signal<string>('');
  loading = signal(false);
  extracting = signal(false);
  generatingPrompts = signal<Set<string>>(new Set());
  generatingImages = signal<Set<string>>(new Set());

  characters = signal<any[]>([]);

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
        this.loadCharacters();
      }
    });
  }

  loadCharacters(): void {
    this.loading.set(true);
    this.apiService.getCharacters(this.projectIdParam).subscribe({
      next: (chars) => {
        this.characters.set(chars);
        this.loading.set(false);
      },
      error: () => {
        this.loading.set(false);
      },
    });
  }

  async extractCharacters(): Promise<void> {
    this.extracting.set(true);
    try {
      await this.apiService.extractCharacters(this.projectIdParam, {}).toPromise();
      this.notificationService.showSuccess('Character extraction started');
      setTimeout(() => this.loadCharacters(), 5000);
    } catch {
      this.notificationService.showError('Failed to start character extraction');
    } finally {
      this.extracting.set(false);
    }
  }

  generatingPrompt(characterId: string): boolean {
    return this.generatingPrompts().has(characterId);
  }

  generatingImage(characterId: string): boolean {
    return this.generatingImages().has(characterId);
  }

  async generatePrompt(characterId: string): Promise<void> {
    this.generatingPrompts.update(set => new Set([...set, characterId]));
    try {
      await this.apiService.generateCharacterPrompt(this.projectIdParam, characterId).toPromise();
      this.notificationService.showSuccess('Prompt generated');
    } catch {
      this.notificationService.showError('Failed to generate prompt');
    } finally {
      this.generatingPrompts.update(set => {
        const newSet = new Set(set);
        newSet.delete(characterId);
        return newSet;
      });
    }
  }

  async generateImage(characterId: string): Promise<void> {
    this.generatingImages.update(set => new Set([...set, characterId]));
    try {
      await this.apiService.generateCharacterImage(this.projectIdParam, characterId).toPromise();
      this.notificationService.showSuccess('Image generation started');
    } catch {
      this.notificationService.showError('Failed to generate image');
    } finally {
      this.generatingImages.update(set => {
        const newSet = new Set(set);
        newSet.delete(characterId);
        return newSet;
      });
    }
  }

  goBack(): void {
    this.router.navigate(['/projects', this.projectIdParam]);
  }
}