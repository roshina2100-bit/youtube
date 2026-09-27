"""
Local Python LLM provider using Hugging Face Transformers.
"""

import asyncio
import time
from typing import Any, AsyncIterator, Dict, List, Optional
from pathlib import Path

from app.models.provider import ProviderMetadata, ProviderCapability, ModelConfig
from app.providers.interfaces import LLMProvider, GenerationResult
from app.core.logging import log_model_load, log_model_unload, log_generation


class TransformersLLMProvider(LLMProvider):
    """Local LLM provider using Hugging Face Transformers."""
    
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
                ProviderCapability(name="generate_text", supported=True, description="Text generation"),
                ProviderCapability(name="structured_output", supported=True, description="JSON output"),
                ProviderCapability(name="chat", supported=True, description="Multi-turn chat"),
            ],
            loaded=self._loaded,
            device=self.config.device,
            memory_usage_mb=None,
            load_time_seconds=self._load_time,
            last_used=self._last_used,
        )
    
    async def load(self) -> None:
        """Load the model and tokenizer."""
        if self._loaded:
            return
        
        start_time = time.time()
        
        try:
            # Import here to avoid dependency if not used
            from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
            import torch
            
            model_path = self.config.model_path
            if not model_path or not Path(model_path).exists():
                raise ValueError(f"Model path not found: {model_path}")
            
            # Load tokenizer
            self._tokenizer = AutoTokenizer.from_pretrained(
                model_path,
                trust_remote_code=self.config.trust_remote_code,
                padding_side="left"
            )
            
            if self._tokenizer.pad_token is None:
                self._tokenizer.pad_token = self._tokenizer.eos_token
            
            # Prepare model kwargs
            model_kwargs = {
                "torch_dtype": getattr(torch, self.config.torch_dtype),
                "trust_remote_code": self.config.trust_remote_code,
            }
            
            # Device mapping
            if self.config.device == "cuda" and torch.cuda.is_available():
                model_kwargs["device_map"] = "auto"
            else:
                model_kwargs["device_map"] = "cpu"
            
            # Quantization
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
            self._model = AutoModelForCausalLM.from_pretrained(
                model_path,
                **model_kwargs
            )
            
            # Create pipeline
            self._pipeline = pipeline(
                "text-generation",
                model=self._model,
                tokenizer=self._tokenizer,
                device_map="auto" if self.config.device == "cuda" else "cpu",
            )
            
            self._loaded = True
            self._load_time = time.time() - start_time
            self._last_used = time.time()
            
            # Log memory usage if on GPU
            vram_mb = None
            if self.config.device == "cuda" and torch.cuda.is_available():
                vram_mb = torch.cuda.memory_allocated() / (1024 * 1024)
            
            log_model_load(
                None,  # logger
                self.metadata.model_name,
                "local_python:transformers",
                self.config.device,
                vram_mb
            )
            
        except Exception as e:
            self._loaded = False
            raise RuntimeError(f"Failed to load LLM model: {str(e)}") from e
    
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
            
        except Exception as e:
            # Log but don't raise
            pass
    
    def is_available(self) -> bool:
        return self._loaded and self._pipeline is not None
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return [
            ProviderCapability(name="generate_text", supported=True, description="Text generation"),
            ProviderCapability(name="structured_output", supported=True, description="JSON output"),
            ProviderCapability(name="chat", supported=True, description="Multi-turn chat"),
        ]
    
    async def generate(self, prompt: str, **kwargs) -> GenerationResult:
        """Generate text from prompt."""
        if not self.is_available():
            await self.load()
        
        if not self.is_available():
            return GenerationResult(success=False, error="Model not loaded")
        
        start_time = time.time()
        self._last_used = time.time()
        
        try:
            # Prepare generation config
            generation_config = {
                "max_new_tokens": kwargs.get("max_tokens", self.config.max_new_tokens),
                "temperature": kwargs.get("temperature", self.config.temperature),
                "top_p": kwargs.get("top_p", self.config.top_p),
                "do_sample": kwargs.get("do_sample", self.config.do_sample),
                "pad_token_id": self._tokenizer.pad_token_id,
                "eos_token_id": self._tokenizer.eos_token_id,
            }
            
            # Add stop sequences if provided
            stop_sequences = kwargs.get("stop_sequences")
            if stop_sequences:
                generation_config["stop_strings"] = stop_sequences
                generation_config["tokenizer"] = self._tokenizer
            
            # Run generation in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            outputs = await loop.run_in_executor(
                None,
                lambda: self._pipeline(prompt, **generation_config)
            )
            
            # Extract generated text
            generated_text = outputs[0]["generated_text"]
            
            # Remove prompt from output if it's included
            if generated_text.startswith(prompt):
                generated_text = generated_text[len(prompt):]
            
            duration = time.time() - start_time
            
            log_generation(
                None,
                "text_generation",
                "local_python:transformers",
                self.metadata.model_name,
                duration
            )
            
            return GenerationResult(
                success=True,
                data=generated_text.strip(),
                metadata={
                    "model": self.metadata.model_name,
                    "tokens_generated": len(self._tokenizer.encode(generated_text)),
                    "duration_seconds": duration,
                },
                duration_seconds=duration
            )
            
        except Exception as e:
            return GenerationResult(
                success=False,
                error=f"Generation failed: {str(e)}",
                duration_seconds=time.time() - start_time
            )
    
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        """Stream text generation (not fully supported by all models)."""
        # For now, generate full and yield in chunks
        result = await self.generate(prompt, **kwargs)
        if result.success and result.data:
            words = result.data.split()
            for i, word in enumerate(words):
                yield word + (" " if i < len(words) - 1 else "")
                await asyncio.sleep(0.01)
    
    async def generate_structured(self, prompt: str, schema: Dict[str, Any], **kwargs) -> GenerationResult:
        """Generate structured JSON output."""
        # Add JSON instruction to prompt
        structured_prompt = f"{prompt}\n\nReturn only valid JSON matching this schema: {json.dumps(schema)}"
        
        result = await self.generate(structured_prompt, **kwargs)
        
        if result.success:
            try:
                import json
                parsed = json.loads(result.data)
                return GenerationResult(
                    success=True,
                    data=parsed,
                    metadata=result.metadata,
                    duration_seconds=result.duration_seconds
                )
            except json.JSONDecodeError as e:
                return GenerationResult(
                    success=False,
                    error=f"Failed to parse JSON: {str(e)}",
                    duration_seconds=result.duration_seconds
                )
        
        return result
    
    async def cancel(self) -> None:
        """Cancel ongoing generation (not easily supported with pipeline)."""
        # Would need to implement custom generation loop for true cancellation
        pass


# Import json at module level
import json