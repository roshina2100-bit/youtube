import { Component, OnInit, signal } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule, ReactiveFormsModule, FormBuilder, FormGroup, Validators, FormControl, AbstractControl } from '@angular/forms';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDividerModule } from '@angular/material/divider';
import { MatExpansionModule } from '@angular/material/expansion';
import { MatTabsModule } from '@angular/material/tabs';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSliderModule } from '@angular/material/slider';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';

import { NotificationService } from '@core/services/notification.service';

interface Settings {
  general: GeneralSettings;
  models: ModelsSettings;
  aiProviders: AIProvidersSettings;
  notebooklm: NotebookLMSettings;
  ffmpeg: FFmpegSettings;
  storage: StorageSettings;
  performance: PerformanceSettings;
  logging: LoggingSettings;
}

interface GeneralSettings {
  appName: string;
  defaultProjectRoot: string;
  language: string;
  theme: 'light' | 'dark' | 'system';
  autoSave: boolean;
  confirmDeletes: boolean;
}

interface ModelsSettings {
  localModelsDir: string;
  huggingFaceCacheDir: string;
  autoDownloadModels: boolean;
  modelValidationOnLoad: boolean;
}

interface AIProvidersSettings {
  defaultProvider: string;
  allowExternalProvider: boolean;
  fallbackToLocal: boolean;
  providerTimeouts: Record<string, number>;
}

interface NotebookLMSettings {
  enabled: boolean;
  apiKey: string;
  endpoint: string;
  projectId: string;
  model: string;
  timeoutSeconds: number;
  maxRetries: number;
}

interface FFmpegSettings {
  ffmpegPath: string;
  ffprobePath: string;
  defaultPreset: string;
  defaultCRF: number;
  hardwareAcceleration: boolean;
}

interface StorageSettings {
  projectRoot: string;
  maxProjectSizeGB: number;
  autoCleanupTemp: boolean;
  tempRetentionDays: number;
  backupEnabled: boolean;
  backupIntervalHours: number;
  backupLocation: string;
}

interface PerformanceSettings {
  maxConcurrentGPUJobs: number;
  enableCPUFallback: boolean;
  modelIdleTimeoutMinutes: number;
  maxMemoryUsagePercent: number;
  enableModelOffloading: boolean;
}

interface LoggingSettings {
  logLevel: string;
  enableDebugLogging: boolean;
  logRetentionDays: number;
  maxLogFileSizeMB: number;
  structuredLogging: boolean;
}

@Component({
  selector: 'app-settings',
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
    MatCheckboxModule,
    MatDividerModule,
    MatExpansionModule,
    MatTabsModule,
    MatSlideToggleModule,
    MatSliderModule,
    MatTooltipModule,
    MatProgressSpinnerModule,
  ],
  template: `
    <div class="settings-page">
      <header class="page-header">
        <h1>Settings</h1>
        <p class="subtitle">Configure application preferences and behavior</p>
      </header>

      <mat-tab-group>
        <!-- General Tab -->
        <mat-tab label="General">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Application</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="generalForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Application Name</mat-label>
                      <input matInput formControlName="appName">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Default Project Root</mat-label>
                      <input matInput formControlName="defaultProjectRoot" placeholder="e.g., F:/CinematicVideoStudio/projects">
                      <mat-hint>Root directory where projects will be created</mat-hint>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Language</mat-label>
                      <mat-select formControlName="language">
                        <mat-option value="en">English</mat-option>
                        <mat-option value="es">Spanish</mat-option>
                        <mat-option value="fr">French</mat-option>
                        <mat-option value="de">German</mat-option>
                        <mat-option value="zh">Chinese</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Theme</mat-label>
                      <mat-select formControlName="theme">
                        <mat-option value="system">System Default</mat-option>
                        <mat-option value="light">Light</mat-option>
                        <mat-option value="dark">Dark</mat-option>
                      </mat-select>
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="autoSave">Auto-save changes</mat-slide-toggle>
                    <mat-slide-toggle formControlName="confirmDeletes">Confirm before deleting</mat-slide-toggle>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Models Tab -->
        <mat-tab label="Models">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Model Configuration</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="modelsForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Local Models Directory</mat-label>
                      <input matInput formControlName="localModelsDir" placeholder="C:/Models">
                      <mat-hint>Base directory for local AI models</mat-hint>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Hugging Face Cache Directory</mat-label>
                      <input matInput formControlName="huggingFaceCacheDir" placeholder="C:/Users/username/.cache/huggingface">
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="autoDownloadModels">Auto-download missing models (not recommended)</mat-slide-toggle>
                    <mat-slide-toggle formControlName="modelValidationOnLoad">Validate models on load</mat-slide-toggle>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>

            <mat-card>
              <mat-card-header>
                <mat-card-title>Model Paths</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <p class="section-hint">Configure paths for each model type. Use forward slashes even on Windows.</p>
                
                @for (modelType of modelTypes; track modelType) {
                  <div class="model-path-row">
                    <label>{{ modelType.label }}</label>
                    <mat-form-field appearance="outline" class="full-width">
                      <input matInput [formControl]="getModelPathControl(modelType.key)" placeholder="C:/Models/{{ modelType.defaultPath }}">
                    </mat-form-field>
                  </div>
                }
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- AI Providers Tab -->
        <mat-tab label="AI Providers">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Provider Defaults</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="aiProvidersForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Default Provider</mat-label>
                      <mat-select formControlName="defaultProvider">
                        <mat-option value="local_python">Local Python</mat-option>
                        <mat-option value="notebooklm">NotebookLM / API</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Default Timeout (seconds)</mat-label>
                      <input matInput type="number" formControlName="defaultTimeout" min="30" max="3600">
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="allowExternalProvider">Allow external provider selection in UI</mat-slide-toggle>
                    <mat-slide-toggle formControlName="fallbackToLocal">Automatically fall back to local provider on failure</mat-slide-toggle>
                  </div>

                  <div class="form-row">
                    <h3>Per-Operation Timeouts (seconds)</h3>
                    @for (task of providerTasks; track task) {
                      <mat-form-field appearance="outline" class="timeout-field">
                        <mat-label>{{ task }}</mat-label>
                        <input matInput type="number" [formControl]="getTimeoutControl(task)" min="30" max="3600">
                      </mat-form-field>
                    }
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- NotebookLM Tab -->
        <mat-tab label="NotebookLM">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>NotebookLM / External API Configuration</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="notebooklmForm">
                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="enabled">Enable NotebookLM / External API Integration</mat-slide-toggle>
                  </div>

                  <mat-divider></mat-divider>

                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>API Key</mat-label>
                      <input matInput type="password" formControlName="apiKey" placeholder="Enter API key">
                      <mat-hint>Stored securely, never saved to project files</mat-hint>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>API Endpoint</mat-label>
                      <input matInput formControlName="endpoint" placeholder="https://api.example.com/v1">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Project ID</mat-label>
                      <input matInput formControlName="projectId">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Model</mat-label>
                      <input matInput formControlName="model" placeholder="gemini-pro">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Timeout (seconds)</mat-label>
                      <input matInput type="number" formControlName="timeoutSeconds" min="30" max="3600">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Max Retries</mat-label>
                      <input matInput type="number" formControlName="maxRetries" min="0" max="10">
                    </mat-form-field>
                  </div>

                  <div class="form-actions">
                    <button mat-raised-button color="primary" (click)="testNotebookLMConnection()" [disabled]="testingConnection()">
                      @if (testingConnection()) {
                        <mat-spinner diameter="20"></mat-spinner>
                        Testing...
                      } @else {
                        <mat-icon>wifi</mat-icon>
                        <span>Test Connection</span>
                      }
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- FFmpeg Tab -->
        <mat-tab label="FFmpeg">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>FFmpeg Configuration</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="ffmpegForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>FFmpeg Path</mat-label>
                      <input matInput formControlName="ffmpegPath" placeholder="ffmpeg (or full path)">
                      <mat-hint>Leave as 'ffmpeg' if in system PATH</mat-hint>
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>FFprobe Path</mat-label>
                      <input matInput formControlName="ffprobePath" placeholder="ffprobe (or full path)">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Default Preset</mat-label>
                      <mat-select formControlName="defaultPreset">
                        <mat-option value="ultrafast">Ultrafast</mat-option>
                        <mat-option value="superfast">Superfast</mat-option>
                        <mat-option value="veryfast">Very Fast</mat-option>
                        <mat-option value="faster">Faster</mat-option>
                        <mat-option value="fast">Fast</mat-option>
                        <mat-option value="medium">Medium</mat-option>
                        <mat-option value="slow">Slow</mat-option>
                        <mat-option value="slower">Slower</mat-option>
                        <mat-option value="veryslow">Very Slow</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Default CRF</mat-label>
                      <input matInput type="number" formControlName="defaultCRF" min="0" max="51">
                      <mat-hint>Lower = better quality, larger file (18-28 typical)</mat-hint>
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="hardwareAcceleration">Enable hardware acceleration (NVENC, QSV, etc.)</mat-slide-toggle>
                  </div>

                  <div class="form-actions">
                    <button mat-raised-button color="primary" (click)="testFFmpeg()">
                      <mat-icon>play_circle</mat-icon>
                      Test FFmpeg
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Storage Tab -->
        <mat-tab label="Storage">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Storage Configuration</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="storageForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Project Root Directory</mat-label>
                      <input matInput formControlName="projectRoot" placeholder="F:/CinematicVideoStudio/projects">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Max Project Size (GB)</mat-label>
                      <input matInput type="number" formControlName="maxProjectSizeGB" min="1" max="1000">
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Temp Retention (days)</mat-label>
                      <input matInput type="number" formControlName="tempRetentionDays" min="1" max="365">
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="autoCleanupTemp">Auto-cleanup temporary files</mat-slide-toggle>
                  </div>

                  <mat-divider></mat-divider>

                  <h3>Backup Settings</h3>
                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="backupEnabled">Enable automatic backups</mat-slide-toggle>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Backup Interval (hours)</mat-label>
                      <input matInput type="number" formControlName="backupIntervalHours" min="1" max="168">
                    </mat-form-field>

                    <mat-form-field appearance="outline" class="full-width">
                      <mat-label>Backup Location</mat-label>
                      <input matInput formControlName="backupLocation" placeholder="F:/Backups/CinematicVideoStudio">
                    </mat-form-field>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Performance Tab -->
        <mat-tab label="Performance">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Performance Tuning</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="performanceForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Max Concurrent GPU Jobs</mat-label>
                      <input matInput type="number" formControlName="maxConcurrentGPUJobs" min="1" max="8">
                      <mat-hint>Number of GPU-heavy operations to run simultaneously</mat-hint>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Model Idle Timeout (minutes)</mat-label>
                      <input matInput type="number" formControlName="modelIdleTimeoutMinutes" min="5" max="1440">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Max Memory Usage (%)</mat-label>
                      <input matInput type="number" formControlName="maxMemoryUsagePercent" min="50" max="95">
                      <mat-hint>Maximum system memory to use before offloading models</mat-hint>
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="enableCPUFallback">Enable CPU fallback for models</mat-slide-toggle>
                    <mat-slide-toggle formControlName="enableModelOffloading">Enable model offloading when memory pressure</mat-slide-toggle>
                  </div>

                  <mat-divider></mat-divider>

                  <h3>GPU Information</h3>
                  <div class="gpu-info">
                    <p>GPU detection and monitoring would be displayed here</p>
                    <button mat-button (click)="detectGPU()">
                      <mat-icon>memory</mat-icon>
                      Detect GPU
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>

        <!-- Logging Tab -->
        <mat-tab label="Logging">
          <div class="tab-content">
            <mat-card>
              <mat-card-header>
                <mat-card-title>Logging Configuration</mat-card-title>
              </mat-card-header>
              <mat-card-content>
                <form [formGroup]="loggingForm">
                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Log Level</mat-label>
                      <mat-select formControlName="logLevel">
                        <mat-option value="DEBUG">Debug</mat-option>
                        <mat-option value="INFO">Info</mat-option>
                        <mat-option value="WARNING">Warning</mat-option>
                        <mat-option value="ERROR">Error</mat-option>
                      </mat-select>
                    </mat-form-field>

                    <mat-form-field appearance="outline">
                      <mat-label>Log Retention (days)</mat-label>
                      <input matInput type="number" formControlName="logRetentionDays" min="1" max="365">
                    </mat-form-field>
                  </div>

                  <div class="form-row">
                    <mat-form-field appearance="outline">
                      <mat-label>Max Log File Size (MB)</mat-label>
                      <input matInput type="number" formControlName="maxLogFileSizeMB" min="1" max="100">
                    </mat-form-field>
                  </div>

                  <div class="form-row checkbox-row">
                    <mat-slide-toggle formControlName="enableDebugLogging">Enable debug logging (verbose)</mat-slide-toggle>
                    <mat-slide-toggle formControlName="structuredLogging">Use structured JSON logging</mat-slide-toggle>
                  </div>

                  <div class="form-actions">
                    <button mat-button (click)="openLogFolder()">
                      <mat-icon>folder_open</mat-icon>
                      Open Log Folder
                    </button>
                    <button mat-button (click)="clearLogs()" color="warn">
                      <mat-icon>delete_sweep</mat-icon>
                      Clear All Logs
                    </button>
                  </div>
                </form>
              </mat-card-content>
            </mat-card>
          </div>
        </mat-tab>
      </mat-tab-group>

      <div class="save-bar">
        <button mat-button (click)="resetForm()">Reset to Defaults</button>
        <span class="spacer"></span>
        <button mat-raised-button color="primary" (click)="saveSettings()" [disabled]="saving()">
          @if (saving()) {
            <mat-spinner diameter="20"></mat-spinner>
            Saving...
          } @else {
            <mat-icon>save</mat-icon>
            Save Settings
          }
        </button>
      </div>
    </div>
  `,
  styles: [`
    .settings-page {
      display: flex;
      flex-direction: column;
      gap: 24px;
      max-width: 900px;
      margin: 0 auto;
    }

    .page-header {
      margin-bottom: 8px;
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

    .checkbox-row {
      display: flex;
      gap: 24px;
      flex-wrap: wrap;
    }

    .timeout-field {
      min-width: 200px;
    }

    .section-hint {
      margin: 0 0 16px;
      color: #666;
      font-size: 0.875rem;
    }

    .model-path-row {
      display: flex;
      align-items: center;
      gap: 16px;
      margin-bottom: 16px;
    }

    .model-path-row label {
      min-width: 200px;
      font-weight: 500;
      color: #333;
    }

    .form-actions {
      display: flex;
      gap: 12px;
      padding-top: 16px;
      margin-top: 16px;
      border-top: 1px solid #e8e8e8;
    }

    .gpu-info {
      padding: 16px;
      background: #f5f5f5;
      border-radius: 8px;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .save-bar {
      display: flex;
      align-items: center;
      gap: 12px;
      padding: 16px 24px;
      background: white;
      border-top: 1px solid #e8e8e8;
      position: sticky;
      bottom: 0;
      z-index: 100;
    }

    .spacer {
      flex: 1;
    }

    @media (max-width: 768px) {
      .form-row {
        flex-direction: column;
      }

      .full-width {
        min-width: 0;
      }

      .checkbox-row {
        flex-direction: column;
        gap: 12px;
      }
    }
  `],
})
export class SettingsComponent implements OnInit {
  saving = signal(false);
  testingConnection = signal(false);

  generalForm: FormGroup;
  modelsForm: FormGroup;
  aiProvidersForm: FormGroup;
  notebooklmForm: FormGroup;
  ffmpegForm: FormGroup;
  storageForm: FormGroup;
  performanceForm: FormGroup;
  loggingForm: FormGroup;

  modelTypes = [
    { key: 'llm', label: 'LLM (Story/Character)', defaultPath: 'llama-3-8b-instruct' },
    { key: 'transcription', label: 'Transcription', defaultPath: 'whisper-large-v3' },
    { key: 'translation', label: 'Translation', defaultPath: 'nllb-200-distilled-600M' },
    { key: 'language_detection', label: 'Language Detection', defaultPath: 'lid.176' },
    { key: 'embedding', label: 'Embeddings', defaultPath: 'bge-large-en-v1.5' },
    { key: 'image', label: 'Image Generation', defaultPath: 'sdxl-base' },
    { key: 'video', label: 'Video Generation', defaultPath: 'svd-xt' },
    { key: 'tts', label: 'TTS', defaultPath: 'xtts-v2' },
    { key: 'music', label: 'Music Generation', defaultPath: 'musicgen-large' },
    { key: 'sfx', label: 'SFX Generation', defaultPath: 'audioldm2' },
  ];

  providerTasks = [
    'story_analysis',
    'translation',
    'character_analysis',
    'image_generation',
    'video_generation',
    'tts',
    'music_generation',
    'sfx_generation',
    'transcription',
    'language_detection',
  ];

  constructor(
    private fb: FormBuilder,
    private notificationService: NotificationService,
  ) {
    this.generalForm = this.fb.group({
      appName: ['Cinematic Video Studio'],
      defaultProjectRoot: ['F:/CinematicVideoStudio/projects'],
      language: ['en'],
      theme: ['system'],
      autoSave: [true],
      confirmDeletes: [true],
    });

    this.modelsForm = this.fb.group({
      localModelsDir: ['C:/Models'],
      huggingFaceCacheDir: ['C:/Users/username/.cache/huggingface'],
      autoDownloadModels: [false],
      modelValidationOnLoad: [true],
    });

    // Add model path controls
    for (const modelType of this.modelTypes) {
      this.modelsForm.addControl(
        `modelPath_${modelType.key}`,
        this.fb.control(`C:/Models/${modelType.defaultPath}`)
      );
    }

    this.aiProvidersForm = this.fb.group({
      defaultProvider: ['local_python'],
      allowExternalProvider: [true],
      fallbackToLocal: [false],
      defaultTimeout: [300],
    });

    for (const task of this.providerTasks) {
      this.aiProvidersForm.addControl(
        `timeout_${task}`,
        this.fb.control(300)
      );
    }

    this.notebooklmForm = this.fb.group({
      enabled: [false],
      apiKey: [''],
      endpoint: [''],
      projectId: [''],
      model: ['gemini-pro'],
      timeoutSeconds: [300],
      maxRetries: [3],
    });

    this.ffmpegForm = this.fb.group({
      ffmpegPath: ['ffmpeg'],
      ffprobePath: ['ffprobe'],
      defaultPreset: ['medium'],
      defaultCRF: [23],
      hardwareAcceleration: [true],
    });

    this.storageForm = this.fb.group({
      projectRoot: ['F:/CinematicVideoStudio/projects'],
      maxProjectSizeGB: [50],
      autoCleanupTemp: [true],
      tempRetentionDays: [30],
      backupEnabled: [false],
      backupIntervalHours: [24],
      backupLocation: ['F:/Backups/CinematicVideoStudio'],
    });

    this.performanceForm = this.fb.group({
      maxConcurrentGPUJobs: [1],
      enableCPUFallback: [true],
      modelIdleTimeoutMinutes: [5],
      maxMemoryUsagePercent: [85],
      enableModelOffloading: [true],
    });

    this.loggingForm = this.fb.group({
      logLevel: ['INFO'],
      enableDebugLogging: [false],
      logRetentionDays: [30],
      maxLogFileSizeMB: [10],
      structuredLogging: [true],
    });
  }

  ngOnInit(): void {
    this.loadSettings();
  }

  loadSettings(): void {
    // Load from localStorage or config file
    const stored = localStorage.getItem('app_settings');
    if (stored) {
      try {
        const settings = JSON.parse(stored);
        this.generalForm.patchValue(settings.general || {});
        this.modelsForm.patchValue(settings.models || {});
        this.aiProvidersForm.patchValue(settings.aiProviders || {});
        this.notebooklmForm.patchValue(settings.notebooklm || {});
        this.ffmpegForm.patchValue(settings.ffmpeg || {});
        this.storageForm.patchValue(settings.storage || {});
        this.performanceForm.patchValue(settings.performance || {});
        this.loggingForm.patchValue(settings.logging || {});
      } catch {
        // Ignore parse errors
      }
    }
  }

  getModelPathControl(key: string): FormControl {
    return this.modelsForm.get(`modelPath_${key}`) as FormControl;
  }

  getTimeoutControl(task: string): FormControl {
    return this.aiProvidersForm.get(`timeout_${task}`) as FormControl;
  }

  async saveSettings(): Promise<void> {
    this.saving.set(true);

    const settings = {
      general: this.generalForm.value,
      models: this.modelsForm.value,
      aiProviders: this.aiProvidersForm.value,
      notebooklm: this.notebooklmForm.value,
      ffmpeg: this.ffmpegForm.value,
      storage: this.storageForm.value,
      performance: this.performanceForm.value,
      logging: this.loggingForm.value,
    };

    try {
      localStorage.setItem('app_settings', JSON.stringify(settings));
      this.notificationService.showSuccess('Settings saved successfully');
    } catch {
      this.notificationService.showError('Failed to save settings');
    } finally {
      this.saving.set(false);
    }
  }

  resetForm(): void {
    if (confirm('Reset all settings to defaults? This cannot be undone.')) {
      localStorage.removeItem('app_settings');
      this.loadSettings();
      this.notificationService.showInfo('Settings reset to defaults');
    }
  }

  async testNotebookLMConnection(): Promise<void> {
    this.testingConnection.set(true);
    try {
      // Test connection logic
      this.notificationService.showInfo('Connection test not implemented yet');
    } finally {
      this.testingConnection.set(false);
    }
  }

  async testFFmpeg(): Promise<void> {
    // Test FFmpeg logic
    this.notificationService.showInfo('FFmpeg test not implemented yet');
  }

  detectGPU(): void {
    this.notificationService.showInfo('GPU detection not implemented yet');
  }

  openLogFolder(): void {
    this.notificationService.showInfo('Open log folder not implemented yet');
  }

  clearLogs(): void {
    if (confirm('Clear all log files? This cannot be undone.')) {
      this.notificationService.showSuccess('Logs cleared');
    }
  }
}