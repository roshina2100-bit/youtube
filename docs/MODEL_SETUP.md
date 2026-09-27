# Model Setup Guide

This guide covers configuring local AI models for the Cinematic Multi-Language Video Studio.

## Model Configuration File

The backend uses `backend/config/models.yaml` for model configuration:

```yaml
models:
  llm:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/llama-3-8b-instruct"
    device: "cuda"
    torch_dtype: "float16"
    load_in_8bit: false
    load_in_4bit: true
    max_memory: null
    offload_folder: null
    trust_remote_code: false
    generation_config:
      max_new_tokens: 4096
      temperature: 0.7
      top_p: 0.9
      do_sample: true
  
  transcription:
    provider: local_python
    backend: faster_whisper
    model_path: "C:/Models/whisper-large-v3"
    device: "cuda"
    compute_type: "float16"
    cpu_threads: 4
    num_workers: 1
    download_root: null
  
  translation:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/nllb-200-distilled-600M"
    device: "cuda"
    torch_dtype: "float16"
    src_lang: "auto"
    tgt_lang: "eng_Latn"
  
  language_detection:
    provider: local_python
    backend: fasttext
    model_path: "C:/Models/lid.176.bin"
  
  embedding:
    provider: local_python
    backend: sentence_transformers
    model_path: "C:/Models/bge-large-en-v1.5"
    device: "cuda"
  
  image:
    provider: local_python
    backend: diffusers
    model_path: "C:/Models/sdxl-base"
    refiner_path: "C:/Models/sdxl-refiner"
    device: "cuda"
    torch_dtype: "float16"
    variant: "fp16"
    use_safetensors: true
    enable_xformers: true
    enable_cpu_offload: false
    enable_sequential_cpu_offload: false
    vae_path: null
    scheduler: "euler_ancestral"
    default_steps: 30
    default_guidance_scale: 7.5
    default_width: 1024
    default_height: 1024
  
  video:
    provider: local_python
    backend: diffusers
    model_path: "C:/Models/svd-xt"
    device: "cuda"
    torch_dtype: "float16"
    variant: "fp16"
    use_safetensors: true
    enable_xformers: true
    enable_cpu_offload: false
    num_frames: 25
    fps: 7
    motion_bucket_id: 127
    noise_aug_strength: 0.02
    decode_chunk_size: 8
  
  tts:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/xtts-v2"
    device: "cuda"
    torch_dtype: "float16"
    speaker_wav: null
    language: "en"
    speed: 1.0
  
  music:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/musicgen-large"
    device: "cuda"
    torch_dtype: "float16"
    max_duration: 30
  
  sfx:
    provider: local_python
    backend: transformers
    model_path: "C:/Models/audioldm2"
    device: "cuda"
    torch_dtype: "float16"
    max_duration: 10
```

## Recommended Models

### LLM (Story Analysis, Character Generation, Prompt Engineering)

| Model | Size | VRAM (4bit) | Quality | License |
|-------|------|-------------|---------|---------|
| Llama 3 8B Instruct | 4.7 GB | ~6 GB | Excellent | Llama 3 Community |
| Llama 3.1 8B Instruct | 4.7 GB | ~6 GB | Excellent | Llama 3.1 Community |
| Mistral 7B Instruct v0.3 | 4.1 GB | ~5 GB | Very Good | Apache 2.0 |
| Qwen 2.5 7B Instruct | 4.4 GB | ~5.5 GB | Excellent | Apache 2.0 |
| Phi 3 Mini 4K Instruct | 2.3 GB | ~3 GB | Good | MIT |

**Download:**
```bash
huggingface-cli download meta-llama/Meta-Llama-3-8B-Instruct --local-dir C:/Models/llama-3-8b-instruct
huggingface-cli download mistralai/Mistral-7B-Instruct-v0.3 --local-dir C:/Models/mistral-7b-instruct
huggingface-cli download Qwen/Qwen2.5-7B-Instruct --local-dir C:/Models/qwen2.5-7b-instruct
```

### Transcription (Speech-to-Text)

| Model | Size | VRAM | Languages | Speed |
|-------|------|------|-----------|-------|
| Whisper Large v3 | 1.5 GB | ~2 GB | 99 | Fast |
| Whisper Large v2 | 1.5 GB | ~2 GB | 99 | Fast |
| Faster-Whisper Distil Large v3 | 756 MB | ~1 GB | 99 | Very Fast |

**Download:**
```bash
huggingface-cli download Systran/faster-whisper-large-v3 --local-dir C:/Models/whisper-large-v3
huggingface-cli download Systran/faster-distil-whisper-large-v3 --local-dir C:/Models/distil-whisper-large-v3
```

### Translation

| Model | Size | VRAM (4bit) | Languages | Quality |
|-------|------|-------------|-----------|---------|
| NLLB-200 3.3B | 6.6 GB | ~8 GB | 200 | Excellent |
| NLLB-200 Distilled 600M | 1.2 GB | ~2 GB | 200 | Very Good |
| M2M100 1.2B | 2.4 GB | ~3 GB | 100 | Good |
| SeamlessM4T v2 Large | 4.5 GB | ~6 GB | 100+ | Excellent |

**Download:**
```bash
huggingface-cli download facebook/nllb-200-distilled-600M --local-dir C:/Models/nllb-200-distilled-600M
huggingface-cli download facebook/nllb-200-3.3B --local-dir C:/Models/nllb-200-3.3B
```

### Language Detection

| Model | Size | Languages | Speed |
|-------|------|-----------|-------|
| FastText lid.176 | 126 MB | 176 | Very Fast |
| FastText lid.176.ftz | 917 MB | 176 | Fast |

**Download:**
```bash
# FastText models
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.bin -O C:/Models/lid.176.bin
wget https://dl.fbaipublicfiles.com/fasttext/supervised-models/lid.176.ftz -O C:/Models/lid.176.ftz
```

### Embeddings

| Model | Size | VRAM | Dimensions | Quality |
|-------|------|------|------------|---------|
| BGE Large EN v1.5 | 1.3 GB | ~2 GB | 1024 | Excellent |
| BGE Base EN v1.5 | 440 MB | ~1 GB | 768 | Very Good |
| E5 Large v2 | 1.3 GB | ~2 GB | 1024 | Excellent |
| Multilingual E5 Large | 2.2 GB | ~3 GB | 1024 | Excellent |

**Download:**
```bash
huggingface-cli download BAAI/bge-large-en-v1.5 --local-dir C:/Models/bge-large-en-v1.5
huggingface-cli download intfloat/multilingual-e5-large --local-dir C:/Models/multilingual-e5-large
```

### Image Generation

| Model | Size | VRAM (fp16) | Resolution | Quality |
|-------|------|-------------|------------|---------|
| SDXL Base 1.0 | 6.9 GB | ~8 GB | 1024x1024 | Excellent |
| SDXL Refiner 1.0 | 6.9 GB | ~8 GB | 1024x1024 | Excellent |
| SD 1.5 | 2.1 GB | ~3 GB | 512x512 | Good |
| SD 2.1 | 2.1 GB | ~3 GB | 768x768 | Good |
| Playground v2.5 | 6.9 GB | ~8 GB | 1024x1024 | Excellent |

**Download:**
```bash
huggingface-cli download stabilityai/stable-diffusion-xl-base-1.0 --local-dir C:/Models/sdxl-base
huggingface-cli download stabilityai/stable-diffusion-xl-refiner-1.0 --local-dir C:/Models/sdxl-refiner
huggingface-cli download runwayml/stable-diffusion-v1-5 --local-dir C:/Models/sd15
```

### Video Generation

| Model | Size | VRAM (fp16) | Frames | Duration |
|-------|------|-------------|--------|----------|
| SVD XT | 5.2 GB | ~7 GB | 25 | ~3.5s @ 7fps |
| SVD | 5.2 GB | ~7 GB | 14 | ~2s @ 7fps |
| I2VGen-XL | 6.5 GB | ~8 GB | 16 | ~2.6s @ 6fps |
| AnimateDiff | 1.5 GB | ~3 GB | 16 | ~2s @ 8fps |

**Download:**
```bash
huggingface-cli download stabilityai/stable-video-diffusion-img2vid-xt --local-dir C:/Models/svd-xt
huggingface-cli download stabilityai/stable-video-diffusion-img2vid --local-dir C:/Models/svd
```

### TTS (Text-to-Speech)

| Model | Size | VRAM | Languages | Quality |
|-------|------|------|-----------|---------|
| XTTS v2 | 1.8 GB | ~3 GB | 17 | Excellent |
| VITS (Coqui) | 500 MB | ~1 GB | 17 | Very Good |
| Bark | 2.5 GB | ~4 GB | 100+ | Good |
| Tortoise TTS | 2.5 GB | ~4 GB | English | Excellent |

**Download:**
```bash
huggingface-cli download coqui/XTTS-v2 --local-dir C:/Models/xtts-v2
```

### Music Generation

| Model | Size | VRAM | Duration | Quality |
|-------|------|------|----------|---------|
| MusicGen Large | 3.3 GB | ~5 GB | 30s | Excellent |
| MusicGen Medium | 1.5 GB | ~3 GB | 30s | Very Good |
| MusicGen Small | 300 MB | ~1 GB | 30s | Good |
| AudioLDM 2 | 2.5 GB | ~4 GB | 10s | Good |

**Download:**
```bash
huggingface-cli download facebook/musicgen-large --local-dir C:/Models/musicgen-large
huggingface-cli download facebook/musicgen-medium --local-dir C:/Models/musicgen-medium
```

### Sound Effects

| Model | Size | VRAM | Duration | Quality |
|-------|------|------|----------|---------|
| AudioLDM 2 | 2.5 GB | ~4 GB | 10s | Good |
| AudioGen | 1.5 GB | ~3 GB | 5s | Good |
| Make-An-Audio 2 | 2.5 GB | ~4 GB | 10s | Good |

**Download:**
```bash
huggingface-cli download cvssp/audioldm2 --local-dir C:/Models/audioldm2
```

## Memory Optimization

### 4-bit Quantization (BitsAndBytes)
```yaml
llm:
  load_in_4bit: true
  bnb_4bit_compute_dtype: "float16"
  bnb_4bit_quant_type: "nf4"
  bnb_4bit_use_double_quant: true
```

### 8-bit Quantization
```yaml
llm:
  load_in_8bit: true
```

### CPU Offloading
```yaml
image:
  enable_cpu_offload: true          # Offload to CPU when not in use
  enable_sequential_cpu_offload: true  # Sequential offload for very low VRAM
```

### Model Unloading
The system automatically unloads models after `MODEL_IDLE_TIMEOUT` (default 300s).

Manual unload via API:
```bash
POST /api/v1/models/{model_id}/unload
```

## Model Validation

Test model loading:
```bash
cd backend
.venv\Scripts\Activate.ps1
python -c "
from app.providers.local.llm import TransformersLLMProvider
from app.config import get_settings

settings = get_settings()
provider = TransformersLLMProvider(settings.models.llm)
provider.load()
print('Model loaded:', provider.is_available())
result = provider.generate('Test prompt', max_tokens=50)
print('Generation:', result)
provider.unload()
"
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| CUDA OOM | Enable 4-bit, reduce batch size, enable CPU offload |
| Model not found | Check path in models.yaml, use forward slashes |
| Slow inference | Use GPU, enable xformers, use fp16/bf16 |
| Import errors | Install correct transformers/diffusers version |
| Version conflicts | Check compatibility matrix, use venv |

## Compatibility Matrix

| Component | Transformers | Diffusers | Torch | Accelerate |
|-----------|--------------|-----------|-------|------------|
| LLM | ≥4.40 | - | ≥2.3 | ≥0.30 |
| Image | - | ≥0.28 | ≥2.3 | ≥0.30 |
| Video | - | ≥0.28 | ≥2.3 | ≥0.30 |
| TTS | ≥4.40 | - | ≥2.3 | ≥0.30 |
| Music | ≥4.40 | - | ≥2.3 | ≥0.30 |

Check versions:
```bash
python -c "import transformers, diffusers, torch, accelerate; print(f'transformers={transformers.__version__}, diffusers={diffusers.__version__}, torch={torch.__version__}, accelerate={accelerate.__version__}')"
```

## Model Licensing

**Important**: Check model licenses before commercial use.

| Model | License | Commercial Use |
|-------|---------|----------------|
| Llama 3/3.1 | Llama Community | Yes (with restrictions) |
| Mistral | Apache 2.0 | Yes |
| Qwen | Apache 2.0 | Yes |
| Phi 3 | MIT | Yes |
| Whisper | MIT | Yes |
| NLLB | CC-BY-NC 4.0 | Non-commercial only |
| SDXL | OpenRAIL++ | Yes (with restrictions) |
| SVD | OpenRAIL++ | Yes (with restrictions) |
| XTTS v2 | Coqui Public Model License | Yes (with attribution) |
| MusicGen | CC-BY-NC 4.0 | Non-commercial only |

For commercial projects, use Apache 2.0 / MIT licensed models or obtain commercial licenses.