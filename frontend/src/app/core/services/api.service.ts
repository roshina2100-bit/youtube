import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { map } from 'rxjs/operators';
import { environment } from '@environments/environment';

import { ProjectManifest, ProjectCreate, ProjectUpdate, ProjectSummary, ProjectStatus } from '@shared/models/project.model';
import { Job, JobType, JobStatus, JobStep } from '@shared/models/job.model';
import { ModelInfo, ModelTestRequest, ModelTestResponse } from '@shared/models/model.model';
import { ProviderInfo, CapabilityMatrixResponse } from '@shared/models/provider.model';

@Injectable({
  providedIn: 'root',
})
export class ApiService {
  private http = inject(HttpClient);
  private baseUrl = environment.apiUrl;

  // Projects
  getProjects(status?: ProjectStatus, limit = 50, offset = 0): Observable<{ projects: ProjectSummary[]; total: number }> {
    let params = new HttpParams()
      .set('limit', limit)
      .set('offset', offset);
    if (status) params = params.set('status', status);
    return this.http.get<{ projects: ProjectSummary[]; total: number }>(`${this.baseUrl}/projects`, { params });
  }

  getProject(projectId: string): Observable<ProjectManifest> {
    return this.http.get<ProjectManifest>(`${this.baseUrl}/projects/${projectId}`);
  }

  createProject(project: ProjectCreate): Observable<ProjectManifest> {
    return this.http.post<ProjectManifest>(`${this.baseUrl}/projects`, project);
  }

  updateProject(projectId: string, project: ProjectUpdate): Observable<ProjectManifest> {
    return this.http.patch<ProjectManifest>(`${this.baseUrl}/projects/${projectId}`, project);
  }

  deleteProject(projectId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/projects/${projectId}`);
  }

  // Jobs
  getJobs(projectId: string, status?: JobStatus, jobType?: JobType, limit = 50, offset = 0): Observable<{ jobs: Job[]; total: number }> {
    let params = new HttpParams()
      .set('limit', limit)
      .set('offset', offset);
    if (status) params = params.set('status', status);
    if (jobType) params = params.set('job_type', jobType);
    return this.http.get<{ jobs: Job[]; total: number }>(`${this.baseUrl}/projects/${projectId}/jobs`, { params });
  }

  getJob(projectId: string, jobId: string): Observable<Job> {
    return this.http.get<Job>(`${this.baseUrl}/projects/${projectId}/jobs/${jobId}`);
  }

  createJob(projectId: string, job: { type: JobType; input: any; provider?: string; priority?: number; depends_on?: string[] }): Observable<Job> {
    return this.http.post<Job>(`${this.baseUrl}/projects/${projectId}/jobs`, job);
  }

  cancelJob(projectId: string, jobId: string, reason?: string): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/jobs/${jobId}/cancel`, { reason });
  }

  retryJob(projectId: string, jobId: string): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/jobs/${jobId}/retry`, {});
  }

  recoverJobs(projectId: string): Observable<{ message: string; recovered_job_ids: string[] }> {
    return this.http.post<{ message: string; recovered_job_ids: string[] }>(`${this.baseUrl}/projects/${projectId}/recover`, {});
  }

  getQueueStatus(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/queue/status`);
  }

  // Models
  getModels(providerType?: string): Observable<ModelInfo[]> {
    let params = new HttpParams();
    if (providerType) params = params.set('provider_type', providerType);
    return this.http.get<ModelInfo[]>(`${this.baseUrl}/models`, { params });
  }

  getModel(providerType: string, providerName: string, modelName: string): Observable<ModelInfo> {
    return this.http.get<ModelInfo>(`${this.baseUrl}/models/${providerType}/${providerName}/${modelName}`);
  }

  testModel(request: ModelTestRequest): Observable<ModelTestResponse> {
    return this.http.post<ModelTestResponse>(`${this.baseUrl}/models/test`, request);
  }

  loadModel(providerType: string, providerName: string, modelName: string): Observable<{ message: string; model: string }> {
    return this.http.post<{ message: string; model: string }>(`${this.baseUrl}/models/${providerType}/${providerName}/${modelName}/load`, {});
  }

  unloadModel(providerType: string, providerName: string, modelName: string): Observable<{ message: string; model: string }> {
    return this.http.post<{ message: string; model: string }>(`${this.baseUrl}/models/${providerType}/${providerName}/${modelName}/unload`, {});
  }

  getCapabilityMatrix(): Observable<CapabilityMatrixResponse> {
    return this.http.get<CapabilityMatrixResponse>(`${this.baseUrl}/models/capabilities/matrix`);
  }

  checkCapability(providerType: string, providerName: string, capability: string): Observable<{ supported: boolean }> {
    return this.http.get<{ supported: boolean }>(`${this.baseUrl}/models/capabilities/check`, {
      params: { provider_type: providerType, provider_name: providerName, capability }
    });
  }

  getSupportedProviders(providerType: string, capability: string): Observable<{ providers: string[] }> {
    return this.http.get<{ providers: string[] }>(`${this.baseUrl}/models/capabilities/supported`, {
      params: { provider_type: providerType, capability }
    });
  }

  // Providers
  getProviders(providerType?: string): Observable<{ providers: ProviderInfo[]; total: number }> {
    let params = new HttpParams();
    if (providerType) params = params.set('provider_type', providerType);
    return this.http.get<{ providers: ProviderInfo[]; total: number }>(`${this.baseUrl}/providers`, { params });
  }

  getProviderCapabilities(): Observable<CapabilityMatrixResponse> {
    return this.http.get<CapabilityMatrixResponse>(`${this.baseUrl}/providers/capabilities`);
  }

  checkProviderCapability(providerType: string, providerName: string, capability: string): Observable<{ supported: boolean }> {
    return this.http.get<{ supported: boolean }>(`${this.baseUrl}/providers/capabilities/check`, {
      params: { provider_type: providerType, provider_name: providerName, capability }
    });
  }

  getSupportedProvidersForCapability(providerType: string, capability: string): Observable<{ providers: string[] }> {
    return this.http.get<{ providers: string[] }>(`${this.baseUrl}/providers/supported`, {
      params: { provider_type: providerType, capability }
    });
  }

  getProviderInfo(providerType: string, providerName: string, modelName: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/providers/${providerType}/${providerName}/${modelName}`);
  }

  // Health
  healthCheck(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/health`);
  }

  detailedHealth(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/health/detailed`);
  }

  // Audio Generation
  generateTTS(projectId: string, input: { language: string; text?: string; voice?: string }): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/audio/tts`, input);
  }

  generateMusic(projectId: string, input: { language: string; prompt?: string; duration?: number }): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/audio/music`, input);
  }

  generateSFX(projectId: string, input: { language: string; prompt?: string; duration?: number }): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/audio/sfx`, input);
  }

  generateAllAudio(projectId: string, input: { language: string }): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/audio/generate-all`, input);
  }

  mixAudio(projectId: string, input: { language: string }): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/audio/mix`, input);
  }

  getAudioFiles(projectId: string, language: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/audio/${language}`);
  }

  // Transcript
  getTranscript(projectId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/transcript`);
  }

  normalizeTranscript(projectId: string, input: any): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/transcript/normalize`, input);
  }

  detectLanguage(projectId: string): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/transcript/detect-language`, {});
  }

  importTranscript(projectId: string, formData: FormData): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/transcript/import`, formData);
  }

  // Source
  getSource(projectId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/source`);
  }

  getSourceInfo(projectId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/source`);
  }

  deleteSource(projectId: string): Observable<void> {
    return this.http.delete<void>(`${this.baseUrl}/projects/${projectId}/source`);
  }

  importSource(projectId: string, formData: FormData): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/source/import`, formData);
  }

  getLanguageDetection(projectId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/transcript/language-detection`);
  }

  // Settings
  getSettings(): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/settings`);
  }

  updateSettings(settings: any): Observable<any> {
    return this.http.put<any>(`${this.baseUrl}/settings`, settings);
  }

  getLanguages(projectId: string): Observable<string[]> {
    return this.http.get<string[]>(`${this.baseUrl}/projects/${projectId}/languages`);
  }

  getLanguageWorkspace(projectId: string, language: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/languages/${language}`);
  }

  translateProject(projectId: string, targetLanguages: string[]): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/translate`, {
      target_languages: targetLanguages,
    });
  }

  reviewTranslation(projectId: string, language: string, sceneId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/languages/${language}/scenes/${sceneId}/review`, {});
  }

  approveTranslation(projectId: string, language: string, sceneId: string, approved: boolean): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/languages/${language}/scenes/${sceneId}/approve`, {}, {
      params: { approved: String(approved) },
    });
  }

  getLanguageAudio(projectId: string, language: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/audio/${language}`);
  }

  getCharacters(projectId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/projects/${projectId}/characters`);
  }

  extractCharacters(projectId: string, options: Record<string, unknown> = {}): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/story/extract-characters`, options);
  }

  generateCharacterPrompt(projectId: string, characterId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/characters/${characterId}/generate-prompt`, {});
  }

  generateCharacterImage(projectId: string, characterId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/characters/${characterId}/generate-image`, { prompt: '' });
  }

  getScenes(projectId: string): Observable<any[]> {
    return this.http.get<any[]>(`${this.baseUrl}/projects/${projectId}/scenes`);
  }

  getSilentMaster(_projectId: string): Observable<string | null> {
    return of(null);
  }

  getStory(projectId: string): Observable<any> {
    return this.http.get<any>(`${this.baseUrl}/projects/${projectId}/story`);
  }

  analyzeStory(projectId: string, options: Record<string, unknown> = {}): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/analyze-story`, options);
  }

  getOutputs(projectId: string): Observable<any[]> {
    return this.http.get<{ outputs: any[] }>(`${this.baseUrl}/projects/${projectId}/output`)
      .pipe(map(response => response.outputs));
  }

  getExports(projectId: string): Observable<any[]> {
    return this.http.get<{ exports: any[] }>(`${this.baseUrl}/projects/${projectId}/exports`)
      .pipe(map(response => response.exports));
  }

  renderFinalVideo(projectId: string, input: { language: string; includeSubtitles?: boolean }): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/render`, {
      language: input.language,
      include_subtitles: input.includeSubtitles ?? true,
    });
  }

  renderAllLanguages(projectId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/render/all`, {});
  }

  exportProject(projectId: string, input: Record<string, unknown>): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/export`, input);
  }

  generateScenePrompts(projectId: string, sceneId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/scenes/${sceneId}/generate-prompts`, {});
  }

  generateSceneImage(projectId: string, sceneId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/scenes/${sceneId}/generate-image`, {});
  }

  generateSceneVideo(projectId: string, sceneId: string): Observable<any> {
    return this.http.post<any>(`${this.baseUrl}/projects/${projectId}/scenes/${sceneId}/generate-video`, {}, {
      params: { image_path: '' },
    });
  }

  // Scene Generation
  generateScenes(projectId: string, input: any): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/scenes/generate`, input);
  }

  generateSilentMaster(projectId: string): Observable<{ message: string; job_id: string }> {
    return this.http.post<{ message: string; job_id: string }>(`${this.baseUrl}/projects/${projectId}/scenes/generate-silent-master`, {});
  }
}