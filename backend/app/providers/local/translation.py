"""
Local Python translation provider using Hugging Face Transformers (NLLB, M2M100, etc.).
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import TranslationProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class TransformersTranslationProvider(TranslationProvider):
    """Local translation provider using Hugging Face Transformers."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self._model = None
        self._tokenizer = None
        self._pipeline = None
        self._loaded = False
        self._load_time = 0.0
        self._last_used = None
    
    @property
    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name="local_python",
            model_name=Path(self.config.model_path).name if self.config.model_path else "unknown",
            version="1.0.0",
            capabilities=[
                ProviderCapability(name="translate", supported=True, description="Simple translation"),
                ProviderCapability(name="translate_with_context", supported=True, description="Context-aware translation"),
                ProviderCapability(name="translate_batch", supported=True, description="Batch translation"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the translation model."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            from transformers import AutoModelForSeq2SeqLM, AutoTokenizer, pipeline
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=self.config.trust_remote_code,
            )
            
            # Prepare model kwargs
            model_kwargs = {
                "torch_dtype": getattr(torch, self.config.torch_dtype),
                "trust_remote_code": self.config.trust_remote_code,
            }
            
            if self.config.device == "cuda" and torch.cuda.is_available():
                model_kwargs["device_map"] = "auto"
            else:
                model_kwargs["device_map"] = "cpu"
            
            if self.config.load_in_4bit:
                from transformers import BitsAndBytesConfig
                model_kwargs["quantization_config"] = BitsAndBytesConfig(
                    load_in_4bit=True,
                    bnb_4bit_compute_dtype=getattr(torch, self.config.get("bnb_4bit_compute_dtype", "float16")),
                    bnb_4bit_quant_type=self.config.get("bnb_4bit_quant_type", "nf4"),
                    bnb_4bit_use_double_quant=self.config.get("bnb_4bit_use_double_quant", True),
                )
            elif self.config.load_in_8bit:
                model_kwargs["load_in_8bit"] = True
            
            # Load model
            self._model = AutoModelForSeq2SeqLM.from_pretrained(
                model_path,
                **model_kwargs
            )
            
            # Create pipeline
            self._pipeline = pipeline(
                "translation",
                model=self._model,
                tokenizer=self._tokenizer,
                device_map="auto" if self.config.device == "cuda" else "cpu",
            )
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            log_model_load(
                None,
                self.metadata.model_name,
                "local_python:transformers",
                self.config.device
            )
            
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load translation model: {str(e)}") from e
    
    async def unload(self) -> None:
        """Unload the model."""
        if not self._loaded:
            return
        
        try:
            if self._pipeline:
                del self._pipeline
            if self._model:
                del self._model
            if self._tokenizer:
                del self._tokenizer
            
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            
            self._pipeline = None
            self._model = None
            self._tokenizer = None
            self._loaded = False
            
            log_model_unload(None, self.metadata.model_name, "local_python:transformers")
            
        except Exception:
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._pipeline is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="translate", supported=True, description="Simple translation"),
            ProviderCapability(name="translate_with_context", supported=True, description="Context-aware translation"),
            ProviderCapability(name="translate_batch", supported=True, description="Batch translation"),
        ]
    
    def _get_lang_code(self, lang: str) -> str:
        """Convert language code to model-specific format."""
        # NLLB uses codes like "eng_Latn", "hin_Deva", etc.
        lang_map = {
            "en": "eng_Latn",
            "te": "tel_Telu",
            "hi": "hin_Deva",
            "kn": "kan_Knda",
            "ta": "tam_Taml",
            "ml": "mal_Mlym",
            "bn": "ben_Beng",
            "fr": "fra_Latn",
            "de": "deu_Latn",
            "pt": "por_Latn",
            "nl": "nld_Latn",
            "es": "spa_Latn",
            "auto": "auto",
        }
        return lang_map.get(lang.lower(), lang)
    
    async def translate(self, text: str, source_lang: str, target_lang: str, **kwargs) -> GenerationResult:
        """Translate text from source to target language."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            src_code = self._get_lang_code(source_lang)
            tgt_code = self._get_lang_code(target_lang)
            
            # Run translation in thread pool
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                lambda: self._pipeline(
                    text,
                    src_lang=src_code if src_code != "auto" else None,
                    tgt_lang=tgt_code,
                    max_length=kwargs.get("max_length", 512),
                )
            )
            
            translated_text = result[0]["translation_text"]
            duration = time.time() - start_time
            
            log_generation(
                None,
                "translation",
                "local_python:transformers",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data=translated_text,
                metadata={
                    "model": self.metadata.model_name,
                    "source_lang": source_lang,
                    "target_lang": target_lang,
                    "duration_seconds": duration,
                },
                duration_seconds=duration
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Translation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def translate_with_context(
        self, 
        text: str, 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> GenerationResult:
        """Translate with full context (scene, characters, etc.)."""
        # Build context-aware prompt for models that support it
        # For NLLB/M2M100, we just use the standard translation
        # but could prepend context for better results
        
        context_parts = []
        if context.get("scene_description"):
            context_parts.append(f"Scene: {context['scene_description']}")
        if context.get("characters"):
            context_parts.append(f"Characters: {', '.join(context['characters'])}")
        if context.get("previous_scene"):
            context_parts.append(f"Previous: {context['previous_scene']}")
        if context.get("emotion"):
            context_parts.append(f"Tone: {context['emotion']}")
        
        if context_parts:
            # For some models, prepending context helps
            contextualized_text = f"[{' | '.join(context_parts)}] {text}"
        else:
            contextualized_text = text
        
        return await self.translate(contextualized_text, source_lang, target_lang, **kwargs)
    
    async def translate_batch(
        self, 
        texts: List[str], 
        source_lang: str, 
        target_lang: str, 
        context: Dict[str, Any],
        **kwargs
    ) -> List[GenerationResult]:
        """Translate multiple texts with shared context."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return [GenerationResult(success=False, error="Model not loaded") for _ in texts]
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            src_code = self._get_lang_code(source_lang)
            tgt_code = self._get_lang_code(target_lang)
            
            # Build contextualized texts
            contextualized_texts = []
            for text in texts:
                if context.get("scene_description") or context.get("characters"):
                    context_parts = []
                    if context.get("scene_description"):
                        context_parts.append(f"Scene: {context['scene_description']}")
                    if context.get("characters"):
                        context_parts.append(f"Characters: {', '.join(context['characters'])}")
                    if context.get("emotion"):
                        context_parts.append(f"Tone: {context['emotion']}")
                    contextualized_texts.append(f"[{' | '.join(context_parts)}] {text}")
                else:
                    contextualized_texts.append(text)
            
            # Run batch translation
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self._pipeline(
                    contextualized_texts,
                    src_lang=src_code if src_code != "auto" else None,
                    tgt_lang=tgt_code,
                    max_length=kwargs.get("max_length", 512),
                    batch_size=kwargs.get("batch_size", 8),
                )
            )
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "batch_translation",
                "local_python:transformers",
                self.metadata.model_name,
                duration
            )
            
            return [
                GenerationResult(
                    success=True,
                    data=r["translation_text"],
                    metadata={
                        "model": self.metadata.model_name,
                        "source_lang": source_lang,
                        "target_lang": target_lang,
                    },
                    duration_seconds=duration / len(texts)
                )
                for r in results
            ]
            
        except Exception as e:
            return [
                GenerationResult(
                    success=False,
                    error=f"Batch translation failed: {str(e)}",
                    duration_seconds=time.time() - start_time
                )
                for _ in texts
            ]
    
    async def cancel(self) -> None:
        """Cancel ongoing translation."""
        pass