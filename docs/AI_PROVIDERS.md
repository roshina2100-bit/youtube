# AI Providers Architecture

## Provider Interface Design

All AI providers implement a common interface pattern:

```python
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Optional
from pydantic import BaseModel

class ProviderMetadata(BaseModel):
    provider_name: str
    model_name: str
    version: str
    capabilities: list[str]
    loaded: bool
    device: str
    memory_usage_mb: Optional[float] = None

class ProviderCapability(BaseModel):
    name: str
    supported: bool
    description: str
    parameters: dict[str, Any] = {}

class BaseProvider(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ProviderMetadata: ...
    
    @abstractmethod
    async def load(self) -> None: ...
    
    @abstractmethod
    async def unload(self) -> None: ...
    
    @abstractmethod
    def is_available(self) -> bool: ...
    
    @abstractmethod
    def get_capabilities(self) -> list[ProviderCapability]: ...
    
    @abstractmethod
    async def generate(self, **kwargs) -> Any: ...
    
    @abstractmethod
    async def stream(self, **kwargs) -> AsyncIterator[Any]: ...
    
    @abstractmethod
    async def cancel(self) -> None: ...
```

## Provider Types

### 1. LLMProvider
Text generation for story analysis, character creation, prompt engineering.

**Capabilities:**
- `generate_text` - Free-form text generation
- `structured_output` - JSON/schema-constrained output
- `chat` - Multi-turn conversation
- `embedding` - Text embeddings (if supported)

**Parameters:**
- `prompt`: str
- `system_prompt`: str (optional)
- `max_tokens`: int
- `temperature`: float
- `top_p`: float
- `stop_sequences`: list[str]
- `response_format`: dict (for structured output)

### 2. TranslationProvider
Context-aware translation with semantic preservation.

**Capabilities:**
- `translate` - Single text translation
- `translate_batch` - Multiple texts with shared context
- `translate_with_context` - Full scene translation with context

**Parameters:**
- `text`: str
- `source_language`: str
- `target_language`: str
- `context`: dict (scene, characters, previous/next scenes)
- `preserve_formatting`: bool
- `glossary`: dict (term mappings)

### 3. TranscriptionProvider
Speech-to-text with speaker diarization.

**Capabilities:**
- `transcribe` - Audio file to text
- `transcribe_stream` - Streaming transcription
- `diarize` - Speaker separation

**Parameters:**
- `audio_path`: Path
- `language`: str (optional, auto-detect)
- `word_timestamps`: bool
- `speaker_diarization`: bool

### 4. LanguageDetectionProvider
Identify language of text or audio.

**Capabilities:**
- `detect_text` - Language from text
- `detect_audio` - Language from audio
- `detect_batch` - Multiple texts

**Parameters:**
- `text`: str
- `audio_path`: Path
- `top_k`: int (number of candidates)

### 5. EmbeddingProvider
Vector embeddings for semantic search, similarity.

**Capabilities:**
- `embed` - Single text embedding
- `embed_batch` - Multiple texts
- `similarity` - Cosine similarity between embeddings

**Parameters:**
- `texts`: list[str]
- `normalize`: bool

### 6. ImageGenerationProvider
Text-to-image generation.

**Capabilities:**
- `generate` - Text to image
- `generate_with_reference` - Image-to-image (IP-Adapter, ControlNet)
- `inpaint` - Inpainting
- `outpaint` - Outpainting

**Parameters:**
- `prompt`: str
- `negative_prompt`: str
- `width`: int
- `height`: int
- `steps`: int
- `guidance_scale`: float
- `seed`: int (optional)
- `reference_image`: Path (optional)
- `controlnet_image`: Path (optional)
- `controlnet_type`: str (optional)

### 7. VideoGenerationProvider
Image-to-video, text-to-video generation.

**Capabilities:**
- `generate` - Image to video
- `generate_text_to_video` - Text to video (if supported)
- `interpolate` - Frame interpolation

**Parameters:**
- `image_path`: Path
- `prompt`: str
- `negative_prompt`: str
- `num_frames`: int
- `fps`: int
- `motion_bucket_id`: int
- `noise_aug_strength`: float
- `seed`: int (optional)

### 8. TTSProvider
Text-to-speech with voice cloning.

**Capabilities:**
- `synthesize` - Text to speech
- `synthesize_stream` - Streaming synthesis
- `clone_voice` - Voice cloning from reference
- `list_voices` - Available voices

**Parameters:**
- `text`: str
- `voice_id`: str (or reference audio path)
- `language`: str
- `speed`: float
- `pitch`: float
- `emotion`: str (optional)

### 9. MusicGenerationProvider
Music generation from text prompts.

**Capabilities:**
- `generate` - Text to music
- `generate_with_melody` - Melody-conditioned
- `continue` - Continue existing music

**Parameters:**
- `prompt`: str
- `duration`: float
- `melody_path`: Path (optional)
- `temperature`: float
- `top_k`: int
- `top_p`: float

### 10. SoundEffectProvider
Sound effect generation.

**Capabilities:**
- `generate` - Text to SFX
- `generate_variations` - Multiple variations

**Parameters:**
- `prompt`: str
- `duration`: float
- `num_variations`: int

## Provider Registry

```python
class ProviderRegistry:
    def __init__(self):
        self._providers: dict[str, BaseProvider] = {}
        self._capabilities_cache: dict[str, list[ProviderCapability]] = {}
    
    def register(self, provider_type: str, provider: BaseProvider) -> None:
        key = f"{provider_type}:{provider.metadata.provider_name}:{provider.metadata.model_name}"
        self._providers[key] = provider
    
    def get(self, provider_type: str, provider_name: str, model_name: str) -> BaseProvider:
        key = f"{provider_type}:{provider_name}:{model_name}"
        return self._providers[key]
    
    def list_providers(self, provider_type: str) -> list[ProviderMetadata]:
        return [
            p.metadata for p in self._providers.values()
            if p.metadata.provider_name.startswith(provider_type)
        ]
    
    def get_capability_matrix(self) -> dict[str, dict[str, bool]]:
        """Returns matrix of provider_type -> provider_name -> capability_supported"""
        matrix = {}
        for provider in self._providers.values():
            ptype = provider.metadata.provider_name.split(':')[0]
            if ptype not in matrix:
                matrix[ptype] = {}
            matrix[ptype][provider.metadata.model_name] = {
                cap.name: cap.supported for cap in provider.get_capabilities()
            }
        return matrix
```

## Capability Matrix Example

| Capability | Local Python (LLM) | NotebookLM | Local Python (Image) | NotebookLM (Image) |
|------------|-------------------|------------|---------------------|-------------------|
| generate_text | ✓ | ✓ | ✗ | ✗ |
| structured_output | ✓ | ✓ | ✗ | ✗ |
| translate | ✓ | ✓ | ✗ | ✗ |
| translate_with_context | ✓ | ✓ | ✗ | ✗ |
| transcribe | ✓ | ✗ | ✗ | ✗ |
| detect_language | ✓ | ✓ | ✗ | ✗ |
| generate_image | ✗ | ✗ | ✓ | ✗ |
| generate_video | ✗ | ✗ | ✓ | ✗ |
| synthesize_speech | ✓ | ✗ | ✗ | ✗ |
| generate_music | ✓ | ✗ | ✗ | ✗ |
| generate_sfx | ✓ | ✗ | ✗ | ✗ |

## Local Python Providers

### TransformersLLMProvider
```python
class TransformersLLMProvider(LLMProvider):
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._tokenizer = None
        self._pipeline = None
    
    async def load(self):
        from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
        import torch
        
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_path,
            trust_remote_code=self.config.trust_remote_code
        )
        
        model_kwargs = {
            "torch_dtype": getattr(torch, self.config.torch_dtype),
            "device_map": "auto" if self.config.device == "cuda" else "cpu",
            "trust_remote_code": self.config.trust_remote_code,
        }
        
        if self.config.load_in_4bit:
            from transformers import BitsAndBytesConfig
            model_kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=getattr(torch, self.config.bnb_4bit_compute_dtype),
                bnb_4bit_quant_type=self.config.bnb_4bit_quant_type,
                bnb_4bit_use_double_quant=self.config.bnb_4bit_use_double_quant,
            )
        elif self.config.load_in_8bit:
            model_kwargs["load_in_8bit"] = True
        
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.model_path,
            **model_kwargs
        )
        
        self._pipeline = pipeline(
            "text-generation",
            model=self._model,
            tokenizer=self._tokenizer,
            device_map="auto" if self.config.device == "cuda" else "cpu"
        )
    
    async def generate(self, prompt: str, **kwargs) -> str:
        generation_config = self.config.generation_config.model_dump()
        generation_config.update(kwargs)
        
        outputs = self._pipeline(prompt, **generation_config)
        return outputs[0]["generated_text"][len(prompt):]
```

### FasterWhisperTranscriptionProvider
```python
class FasterWhisperTranscriptionProvider(TranscriptionProvider):
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
    
    async def load(self):
        from faster_whisper import WhisperModel
        
        self._model = WhisperModel(
            self.config.model_path,
            device=self.config.device,
            compute_type=self.config.compute_type,
            cpu_threads=self.config.cpu_threads,
            num_workers=self.config.num_workers,
            download_root=self.config.download_root
        )
    
    async def transcribe(self, audio_path: Path, **kwargs) -> TranscriptionResult:
        segments, info = self._model.transcribe(
            str(audio_path),
            language=kwargs.get("language"),
            word_timestamps=kwargs.get("word_timestamps", True),
            vad_filter=True
        )
        
        return TranscriptionResult(
            text=" ".join(s.text for s in segments),
            language=info.language,
            language_probability=info.language_probability,
            segments=[Segment(start=s.start, end=s.end, text=s.text) for s in segments]
        )
```

### DiffusersImageProvider
```python
class DiffusersImageProvider(ImageGenerationProvider):
    def __init__(self, config: ModelConfig):
        self.config = config
        self._pipeline = None
        self._refiner = None
    
    async def load(self):
        from diffusers import StableDiffusionXLPipeline, StableDiffusionXLImg2ImgPipeline
        import torch
        
        self._pipeline = StableDiffusionXLPipeline.from_pretrained(
            self.config.model_path,
            torch_dtype=getattr(torch, self.config.torch_dtype),
            variant=self.config.variant,
            use_safetensors=self.config.use_safetensors,
        ).to(self.config.device)
        
        if self.config.enable_xformers:
            self._pipeline.enable_xformers_memory_efficient_attention()
        
        if self.config.enable_cpu_offload:
            self._pipeline.enable_model_cpu_offload()
        elif self.config.enable_sequential_cpu_offload:
            self._pipeline.enable_sequential_cpu_offload()
        
        if self.config.refiner_path:
            self._refiner = StableDiffusionXLImg2ImgPipeline.from_pretrained(
                self.config.refiner_path,
                torch_dtype=getattr(torch, self.config.torch_dtype),
                variant=self.config.variant,
                use_safetensors=self.config.use_safetensors,
            ).to(self.config.device)
    
    async def generate(self, prompt: str, **kwargs) -> ImageResult:
        width = kwargs.get("width", self.config.default_width)
        height = kwargs.get("height", self.config.default_height)
        steps = kwargs.get("steps", self.config.default_steps)
        guidance = kwargs.get("guidance_scale", self.config.default_guidance_scale)
        seed = kwargs.get("seed")
        negative = kwargs.get("negative_prompt", "")
        
        generator = torch.Generator(device=self.config.device).manual_seed(seed) if seed else None
        
        image = self._pipeline(
            prompt=prompt,
            negative_prompt=negative,
            width=width,
            height=height,
            num_inference_steps=steps,
            guidance_scale=guidance,
            generator=generator,
        ).images[0]
        
        # Refine if refiner available
        if self._refiner:
            image = self._refiner(
                prompt=prompt,
                negative_prompt=negative,
                image=image,
                num_inference_steps=steps // 2,
                guidance_scale=guidance,
                generator=generator,
            ).images[0]
        
        return ImageResult(image=image, seed=seed or torch.seed())
```

## NotebookLM/API Adapter

```python
class NotebookLMProvider(LLMProvider, TranslationProvider):
    """Adapter for NotebookLM or compatible API endpoints."""
    
    def __init__(self, config: NotebookLMConfig):
        self.config = config
        self._client = None
        self._capabilities = self._detect_capabilities()
    
    def _detect_capabilities(self) -> list[ProviderCapability]:
        # Probe API for supported capabilities
        caps = [
            ProviderCapability(name="generate_text", supported=True, description="Text generation"),
            ProviderCapability(name="structured_output", supported=True, description="JSON output"),
            ProviderCapability(name="translate", supported=True, description="Translation"),
            ProviderCapability(name="translate_with_context", supported=True, description="Context-aware translation"),
        ]
        # Image/video/audio typically not supported
        for cap in ["generate_image", "generate_video", "synthesize_speech", "generate_music", "generate_sfx"]:
            caps.append(ProviderCapability(name=cap, supported=False, description=f"{cap} not supported by NotebookLM"))
        return caps
    
    async def load(self):
        import httpx
        self._client = httpx.AsyncClient(
            base_url=self.config.endpoint,
            headers={"Authorization": f"Bearer {self.config.api_key}"},
            timeout=self.config.timeout_seconds
        )
        # Test connection
        await self.test_connection()
    
    async def generate(self, prompt: str, **kwargs) -> str:
        response = await self._client.post(
            "/v1/completions",
            json={
                "model": self.config.model,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", 4096),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 0.9),
            }
        )
        response.raise_for_status()
        return response.json()["choices"][0]["text"]
    
    async def translate_with_context(self, text: str, source_lang: str, target_lang: str, context: dict) -> str:
        # Build context-aware prompt
        context_prompt = self._build_translation_prompt(text, source_lang, target_lang, context)
        return await self.generate(context_prompt)
    
    def _build_translation_prompt(self, text: str, source: str, target: str, context: dict) -> str:
        return f"""Translate the following {source} text to {target}.

Context:
- Scene: {context.get('scene_description', 'Unknown')}
- Characters: {', '.join(context.get('characters', []))}
- Previous scene: {context.get('previous_scene', 'None')}
- Next scene: {context.get('next_scene', 'None')}
- Emotional tone: {context.get('emotion', 'Neutral')}

Text to translate:
{text}

Translation:"""
```

## Mock Providers (Testing)

```python
class MockLLMProvider(LLMProvider):
    """Deterministic mock for testing without models."""
    
    def __init__(self):
        self._loaded = False
        self._call_log = []
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="mock",
            model_name="mock-llm",
            version="1.0.0",
            capabilities=["generate_text", "structured_output", "chat"],
            loaded=self._loaded,
            device="cpu"
        )
    
    async def load(self):
        self._loaded = True
    
    async def unload(self):
        self._loaded = False
    
    def is_available(self) -> bool:
        return True
    
    async def generate(self, prompt: str, **kwargs) -> str:
        self._call_log.append({"prompt": prompt, "kwargs": kwargs})
        
        # Return deterministic responses based on prompt content
        if "character" in prompt.lower():
            return json.dumps({
                "name": "Test Character",
                "role": "protagonist",
                "appearance": "Test appearance",
                "personality": "Test personality"
            })
        elif "scene" in prompt.lower():
            return json.dumps({
                "scene_id": "scene_001",
                "description": "Test scene",
                "duration": 10.0
            })
        elif "translate" in prompt.lower():
            return "Translated text"
        else:
            return "Mock response for: " + prompt[:50]
```

## Configuration

### Environment Variables (.env)
```env
# Provider defaults
AI_DEFAULT_PROVIDER=local_python
AI_ALLOW_EXTERNAL_PROVIDER=true
AI_FALLBACK_TO_LOCAL=false

# NotebookLM
NOTEBOOKLM_ENABLED=false
NOTEBOOKLM_API_KEY=
NOTEBOOKLM_ENDPOINT=
NOTEBOOKLM_PROJECT_ID=
NOTEBOOKLM_MODEL=
NOTEBOOKLM_TIMEOUT_SECONDS=300
NOTEBOOKLM_MAX_RETRIES=3
```

### Model Config (models.yaml)
See [MODEL_SETUP.md](MODEL_SETUP.md) for full configuration.

## Adding New Providers

1. Create provider class implementing appropriate interface(s)
2. Add to `ProviderRegistry` in `backend/app/providers/registry.py`
3. Add configuration to `models.yaml`
4. Add capability detection
5. Create mock version for testing
6. Update capability matrix documentation
7. Add tests

## Provider Selection in UI

The frontend displays provider selection per operation:

```typescript
interface ProviderSelection {
  operation: 'story_analysis' | 'translation' | 'character_analysis' | 
             'image_generation' | 'video_generation' | 'tts' | 'music' | 'sfx';
  provider: 'local_python' | 'notebooklm';
  model: string;
  status: 'available' | 'loading' | 'unavailable' | 'error';
  capabilities: string[];
  estimated_memory_mb?: number;
}
```

Users can configure per-project in `project.json`:
```json
{
  "providers": {
    "story_analysis": {"provider": "local_python", "model": "llama-3-8b-instruct"},
    "translation": {"provider": "notebooklm", "model": "gemini-pro"},
    "character_analysis": {"provider": "local_python", "model": "llama-3-8b-instruct"},
    "image_generation": {"provider": "local_python", "model": "sdxl-base"},
    "video_generation": {"provider": "local_python", "model": "svd-xt"},
    "tts": {"provider": "local_python", "model": "xtts-v2"}
  }
}
```