# Project Format Specification

## Overview

Every project is a self-contained folder with a standardized structure. The filesystem is the persistence layer - no databases required.

## Root Structure

```
ProjectName/
├── project.json              # Project manifest (REQUIRED)
├── README.md                 # Human-readable project info
├── source/                   # Source media & metadata
├── transcript/               # Transcript files
├── story/                    # Story intelligence
├── characters/               # Character bible & assets
├── locations/                # Location references
├── scenes/                   # Cinematic scenes
├── languages/                # Per-language workspaces
├── prompts/                  # All generated prompts (versioned)
├── images/                   # Generated images (versioned)
├── video/                    # Video assets
├── audio/                    # Audio assets
├── output/                   # Final rendered videos
├── approvals/                # Approval records
├── logs/                     # Project-specific logs
├── exports/                  # Export packages
└── jobs/                     # Job state persistence
```

## project.json (Manifest)

```json
{
  "project_id": "uuid-v4",
  "name": "My Cinematic Project",
  "description": "Optional description",
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T14:22:00Z",
  "version": 1,
  "status": "draft",
  "source_language": "te",
  "source_language_confidence": 0.98,
  "source_language_detector": "local_python:faster_whisper",
  "target_languages": [
    "en", "te", "hi", "kn", "ta", "ml", "bn", "fr", "de", "pt", "nl", "es"
  ],
  "providers": {
    "story_analysis": {
      "provider": "local_python",
      "model": "llama-3-8b-instruct",
      "config": {}
    },
    "translation": {
      "provider": "notebooklm",
      "model": "gemini-pro",
      "config": {}
    },
    "character_analysis": {
      "provider": "local_python",
      "model": "llama-3-8b-instruct",
      "config": {}
    },
    "image_generation": {
      "provider": "local_python",
      "model": "sdxl-base",
      "config": {}
    },
    "video_generation": {
      "provider": "local_python",
      "model": "svd-xt",
      "config": {}
    },
    "tts": {
      "provider": "local_python",
      "model": "xtts-v2",
      "config": {}
    },
    "music_generation": {
      "provider": "local_python",
      "model": "musicgen-large",
      "config": {}
    },
    "sfx_generation": {
      "provider": "local_python",
      "model": "audioldm2",
      "config": {}
    }
  },
  "model_configuration": {
    "llm": {"device": "cuda", "torch_dtype": "float16", "load_in_4bit": true},
    "transcription": {"device": "cuda", "compute_type": "float16"},
    "image": {"device": "cuda", "torch_dtype": "float16", "enable_xformers": true}
  },
  "workflow": {
    "current_stage": "character_approval",
    "completed_stages": [
      "source_import",
      "transcript_processing",
      "language_detection",
      "story_analysis",
      "character_extraction",
      "character_prompt_generation",
      "character_image_generation"
    ],
    "pending_stages": [
      "character_approval",
      "scene_generation",
      "prompt_generation",
      "translation",
      "image_generation",
      "video_generation",
      "audio_generation",
      "rendering"
    ],
    "auto_approve": false,
    "fallback_to_local": false
  },
  "active_versions": {
    "character_001": "v003",
    "character_002": "v001",
    "scene_0001": "v002",
    "scene_0002": "v001",
    "translation_te": "v001",
    "translation_hi": "v001"
  },
  "statistics": {
    "total_characters": 5,
    "approved_characters": 2,
    "total_scenes": 12,
    "completed_scenes": 0,
    "total_duration_seconds": 1200,
    "languages_completed": 0,
    "languages_total": 12
  },
  "source": {
    "type": "local_file",
    "path": "source/source_media/video.mp4",
    "original_filename": "mahabharata_ep1.mp4",
    "duration_seconds": 1200,
    "metadata": {
      "width": 1920,
      "height": 1080,
      "fps": 30,
      "codec": "h264",
      "audio_codec": "aac"
    }
  }
}
```

## Source Folder

```
source/
├── source.json               # Source metadata
├── source_media/             # Original media files
│   ├── video.mp4
│   └── audio.wav
└── metadata.json             # FFprobe output
```

### source.json
```json
{
  "source_id": "uuid",
  "type": "local_file",
  "original_path": "/User/Videos/mahabharata_ep1.mp4",
  "imported_at": "2024-01-15T10:30:00Z",
  "media_files": [
    {
      "path": "source_media/video.mp4",
      "role": "primary",
      "duration_seconds": 1200,
      "width": 1920,
      "height": 1080,
      "fps": 30,
      "video_codec": "h264",
      "audio_codec": "aac",
      "file_size_bytes": 104857600,
      "sha256": "abc123..."
    }
  ],
  "metadata": {
    "title": "Mahabharata Episode 1",
    "author": "Unknown",
    "description": "First episode of Mahabharata series",
    "tags": ["mythology", "indian", "epic"]
  }
}
```

## Transcript Folder

```
transcript/
├── original.txt              # Raw transcript (as imported)
├── original.json             # Structured original (if SRT/VTT/JSON)
├── normalized.txt            # Cleaned, normalized text
├── normalized.json           # Structured normalized
├── segments.json             # Timestamped segments with speakers
└── language_detection.json   # Detection results
```

### segments.json
```json
{
  "segments": [
    {
      "id": "seg_001",
      "start": 0.0,
      "end": 5.5,
      "text": "In the beginning, there was only darkness.",
      "speaker": "narrator",
      "language": "te",
      "confidence": 0.99
    },
    {
      "id": "seg_002",
      "start": 5.5,
      "end": 12.3,
      "text": "Then Lord Brahma created the universe.",
      "speaker": "narrator",
      "language": "te",
      "confidence": 0.98
    }
  ],
  "speakers": [
    {"id": "speaker_001", "name": "narrator", "gender": "unknown"}
  ],
  "total_duration": 1200.0,
  "language": "te",
  "normalized": true
}
```

### language_detection.json
```json
{
  "detected_language": "te",
  "confidence": 0.98,
  "detector": "local_python:faster_whisper",
  "alternatives": [
    {"language": "hi", "confidence": 0.01},
    {"language": "en", "confidence": 0.01}
  ],
  "manual_override": false,
  "detected_at": "2024-01-15T10:35:00Z"
}
```

## Story Folder

```
story/
├── story.json                # Complete story graph
├── acts.json                 # Act breakdown
├── events.json               # Event timeline
├── themes.json               # Thematic analysis
├── relationships.json        # Character relationships
└── cultural_context.json     # Historical/cultural notes
```

### story.json (Story Graph)
```json
{
  "story_id": "uuid",
  "title": "The Birth of the Universe",
  "summary": "Lord Brahma creates the universe from the cosmic egg...",
  "source_language": "te",
  "acts": [
    {
      "act_id": "act_1",
      "title": "Creation",
      "order": 1,
      "summary": "Brahma emerges from the cosmic egg and creates the world",
      "scenes": ["scene_001", "scene_002", "scene_003"],
      "characters": ["char_001", "char_002"],
      "locations": ["loc_001"],
      "themes": ["creation", "divine_power", "cosmic_order"]
    }
  ],
  "characters": [
    {
      "character_id": "char_001",
      "canonical_name": "Brahma",
      "aliases": ["Creator", "Grandfather", "Prajapati"],
      "role": "protagonist",
      "importance": "major",
      "first_appearance": "scene_001",
      "description": "Four-faced creator god, seated on lotus emerging from Vishnu's navel"
    }
  ],
  "locations": [
    {
      "location_id": "loc_001",
      "name": "Cosmic Ocean",
      "description": "Primordial waters before creation",
      "type": "cosmic",
      "scenes": ["scene_001", "scene_002"]
    }
  ],
  "themes": [
    {"name": "creation", "prominence": 0.9, "description": "Divine creation of universe"},
    {"name": "dharma", "prominence": 0.7, "description": "Cosmic order and duty"}
  ],
  "timeline": [
    {"event_id": "evt_001", "time": "t=0", "description": "Cosmic egg appears", "scene": "scene_001"},
    {"event_id": "evt_002", "time": "t=1", "description": "Brahma emerges", "scene": "scene_001"}
  ]
}
```

## Characters Folder

```
characters/
├── characters.json           # Master character index
├── approved.json             # Approved character versions
├── character_001/
│   ├── character.json        # Character bible
│   ├── versions/
│   │   ├── v001/
│   │   │   ├── character.json
│   │   │   ├── prompt.txt
│   │   │   ├── negative_prompt.txt
│   │   │   ├── image.png
│   │   │   └── metadata.json
│   │   └── v002/
│   ├── prompts/
│   │   ├── prompt_v001.txt
│   │   │   ├── prompt_v002.txt
│   │   └── negative_prompt_v001.txt
│   ├── references/
│   │   ├── ref_v001.png
│   │   └── ref_v002.png
│   └── approved/
│       ├── character.json    # Locked approved version
│       └── reference.png     # Canonical reference image
└── character_002/
    ...
```

### characters.json (Master Index)
```json
{
  "characters": [
    {
      "character_id": "char_001",
      "canonical_name": "Brahma",
      "status": "approved",
      "current_version": "v003",
      "approved_version": "v003",
      "approved_at": "2024-01-15T12:00:00Z",
      "approved_by": "user",
      "reference_image": "characters/character_001/approved/reference.png",
      "scenes": ["scene_001", "scene_002", "scene_003"]
    },
    {
      "character_id": "char_002",
      "canonical_name": "Vishnu",
      "status": "draft",
      "current_version": "v001",
      "approved_version": null,
      "scenes": ["scene_001"]
    }
  ]
}
```

### character.json (Character Bible)
```json
{
  "character_id": "char_001",
  "version": "v003",
  "canonical_name": "Brahma",
  "aliases": ["Creator", "Grandfather", "Prajapati", "Hiranyagarbha"],
  "role": "protagonist",
  "importance": "major",
  "age_range": "ageless",
  "physical_appearance": {
    "face": "Serene, wise, four faces looking in four directions",
    "hair": "Matted locks (jata), white as snow",
    "skin": "Golden-red complexion (like molten gold)",
    "body": "Four arms, seated in lotus position",
    "eyes": "Half-closed in meditation, radiant"
  },
  "clothing": {
    "upper": "White silk dhoti, deer skin upper garment",
    "lower": "Traditional dhoti",
    "accessories": [
      "Sacred thread (yajnopavita)",
      "Kamandalu (water pot)",
      "Akshamala (prayer beads)",
      "Vedas in one hand"
    ],
    "jewelry": "Minimal - simple gold ornaments",
    "headwear": "Crown of matted locks (jatamukuta)"
  },
  "personality": {
    "traits": ["wise", "creative", "meditative", "benevolent", "patient"],
    "emotions": ["serenity", "compassion", "cosmic_awareness"],
    "motivations": ["maintain_cosmic_order", "create_life", "teach_dharma"]
  },
  "relationships": [
    {"character_id": "char_002", "type": "emanation", "description": "Vishnu is Brahma's source"},
    {"character_id": "char_003", "type": "consort", "description": "Saraswati, goddess of knowledge"}
  ],
  "story_role": "Creator of the universe, establishes dharma",
  "character_arc": "From solitary meditation to active creation",
  "visual_identity": "Four-faced, golden-red, seated on lotus, four arms holding Vedas/beads/water pot",
  "negative_prompt": "ugly, deformed, extra limbs, missing faces, modern clothing, angry expression, dark colors, low quality, blurry, cartoon, anime",
  "continuity_rules": {
    "locked_features": ["four_faces", "golden_skin", "four_arms", "lotus_seat", "matted_hair"],
    "variable_features": ["background", "lighting", "camera_angle", "hand_positions"],
    "forbidden_changes": ["face_structure", "skin_color", "arm_count", "head_count"]
  },
  "prompt_template": "Cinematic portrait of {canonical_name}, {physical_appearance}, {clothing}, {visual_identity}, {lighting}, {camera}, {lens}, {composition}, {atmosphere}, 8k, masterpiece, highly detailed",
  "metadata": {
    "created_at": "2024-01-15T11:00:00Z",
    "updated_at": "2024-01-15T12:00:00Z",
    "created_by": "local_python:llama-3-8b-instruct",
    "approved_by": "user",
    "approved_at": "2024-01-15T12:00:00Z",
    "image_model": "sdxl-base",
    "image_seed": 123456789
  }
}
```

### approved.json
```json
{
  "approvals": [
    {
      "character_id": "char_001",
      "version": "v003",
      "approved": true,
      "approved_by": "user",
      "approved_at": "2024-01-15T12:00:00Z",
      "asset_hash": "sha256:abc123...",
      "notes": "Perfect match to description"
    }
  ]
}
```

## Scenes Folder

```
scenes/
├── scenes.json               # Master scene index
├── scene_0001/
│   ├── scene.json            # Scene details
│   ├── prompts/
│   │   ├── master_prompt_v001.txt
│   │   ├── character_prompt_v001.txt
│   │   ├── environment_prompt_v001.txt
│   │   ├── camera_prompt_v001.txt
│   │   ├── lighting_prompt_v001.txt
│   │   ├── motion_prompt_v001.txt
│   │   ├── image_prompt_v001.txt
│   │   ├── i2v_prompt_v001.txt
│   │   ├── voice_prompt_v001.txt
│   │   ├── music_prompt_v001.txt
│   │   ├── sfx_prompt_v001.txt
│   │   └── negative_prompt_v001.txt
│   ├── images/
│   │   ├── keyframe_v001.png
│   │   └── keyframe_v002.png
│   └── video/
│       ├── scene_v001.mp4
│       └── scene_v002.mp4
└── scene_0002/
    ...
```

### scenes.json (Master Index)
```json
{
  "scenes": [
    {
      "scene_id": "scene_0001",
      "act_id": "act_1",
      "order": 1,
      "title": "The Cosmic Egg",
      "duration_seconds": 15.5,
      "source_segments": ["seg_001", "seg_002"],
      "status": "draft",
      "current_version": "v001",
      "approved_version": null,
      "characters": ["char_001"],
      "location_id": "loc_001",
      "visual_style": "cosmic, ethereal, divine light",
      "has_video": false,
      "has_audio": false
    }
  ]
}
```

### scene.json
```json
{
  "scene_id": "scene_0001",
  "version": "v001",
  "act_id": "act_1",
  "order": 1,
  "title": "The Cosmic Egg",
  "duration_seconds": 15.5,
  "source_segments": ["seg_001", "seg_002"],
  "narration": "In the beginning, there was only darkness. Then Lord Brahma created the universe.",
  "dialogue": [],
  "characters": [
    {
      "character_id": "char_001",
      "character_version": "v003",
      "reference_image": "characters/character_001/approved/reference.png",
      "canonical_description": "Four-faced creator god, golden-red skin, seated on lotus...",
      "screen_time_seconds": 15.5,
      "emotion": "serene_meditative"
    }
  ],
  "location": {
    "location_id": "loc_001",
    "name": "Cosmic Ocean",
    "description": "Primordial waters, infinite darkness with single golden egg",
    "time_of_day": "timeless",
    "weather": "none",
    "atmosphere": "mystical, primordial, silent"
  },
  "action": "Camera slowly pushes toward the cosmic egg floating in primordial waters. Golden light begins to emanate from within.",
  "emotion": "awe, anticipation, sacred",
  "camera": {
    "type": "slow_push_in",
    "movement": "dolly_forward",
    "speed": "very_slow",
    "start_frame": "wide_establishing",
    "end_frame": "medium_close_egg"
  },
  "lens": {
    "focal_length": "35mm",
    "aperture": "f/2.8",
    "focus": "egg_then_brahma"
  },
  "framing": "rule_of_thirds, egg_centered_then_brahma_emerging",
  "lighting": {
    "type": "divine_emanation",
    "key_light": "golden_glow_from_egg",
    "fill": "subtle_ambient_starlight",
    "mood": "sacred, mysterious"
  },
  "atmosphere": "primordial, silent, heavy_with_potential",
  "props": ["cosmic_egg", "primordial_waters"],
  "environment": "infinite_dark_ocean",
  "visual_style": "cinematic, epic, mythological, golden_hour_eternal",
  "music": {
    "style": "ambient_drone, tanpura, subtle_choir",
    "mood": "sacred, building_tension",
    "instruments": ["tanpura", "choir", "singing_bowls"],
    "tempo": "very_slow"
  },
  "sound_effects": [
    {"type": "ambient", "description": "Deep cosmic hum", "timing": "continuous"},
    {"type": "event", "description": "Egg cracking resonance", "timing": "12.0s"}
  ],
  "prompts": {
    "master": "Cinematic wide shot of primordial cosmic ocean...",
    "character": "Brahma emerging from cosmic egg, four faces...",
    "environment": "Infinite dark primordial waters, single golden egg...",
    "camera": "Slow dolly push from wide to medium close...",
    "lens": "35mm cinematic lens, f/2.8, shallow depth...",
    "lighting": "Divine golden emanation from within egg...",
    "composition": "Rule of thirds, egg centered, vertical symmetry...",
    "motion": "Very slow forward movement, 15 second duration...",
    "image": "Master cinematic frame: cosmic egg in primordial waters...",
    "i2v": "Camera slowly pushes toward cosmic egg, golden light intensifies...",
    "voice": "Deep, resonant, ancient narrator voice, Sanskrit-inflected...",
    "music": "Ambient drone with tanpura, subtle choir swelling...",
    "sfx": "Deep cosmic hum, subtle water movement, egg resonance...",
    "negative": "modern, technology, bright colors, cartoon, anime, low quality..."
  },
  "metadata": {
    "created_at": "2024-01-15T11:30:00Z",
    "updated_at": "2024-01-15T11:30:00Z",
    "created_by": "local_python:llama-3-8b-instruct",
    "prompt_model": "llama-3-8b-instruct",
    "image_model": "sdxl-base",
    "video_model": "svd-xt"
  }
}
```

## Languages Folder

```
languages/
├── en/
│   ├── scenes/
│   │   ├── scene_0001.json
│   │   └── scene_0002.json
│   ├── translation.json
│   ├── semantic_review.json
│   ├── audio/
│   │   ├── narration/
│   │   ├── dialogue/
│   │   ├── music/
│   │   ├── sfx/
│   │   └── master_audio.wav
│   └── prompts/
│       ├── voice_prompts.json
│       └── music_prompts.json
├── te/
│   ...
└── hi/
    ...
```

### Scene Translation (languages/{lang}/scenes/scene_0001.json)
```json
{
  "scene_id": "scene_0001",
  "language": "en",
  "version": "v001",
  "source_language": "te",
  "translation": {
    "narration": "In the beginning, there was only darkness. Then Lord Brahma created the universe.",
    "dialogue": [],
    "character_names": {
      "char_001": "Brahma"
    },
    "location_name": "Cosmic Ocean",
    "cultural_notes": "Brahma is the creator god in Hindu cosmology"
  },
  "semantic_review": {
    "reviewed": true,
    "reviewed_at": "2024-01-15T13:00:00Z",
    "reviewed_by": "user",
    "issues": [],
    "flags": [],
    "approved": true
  },
  "voice_prompts": {
    "narrator": "Deep, resonant, ancient storyteller voice, measured pace",
    "char_001": "Divine, authoritative yet compassionate, Sanskrit-inflected English"
  },
  "metadata": {
    "translated_by": "notebooklm:gemini-pro",
    "translated_at": "2024-01-15T12:30:00Z",
    "reviewed_by": "user",
    "reviewed_at": "2024-01-15T13:00:00Z"
  }
}
```

### Semantic Review (languages/{lang}/semantic_review.json)
```json
{
  "language": "en",
  "reviews": [
    {
      "scene_id": "scene_0001",
      "checks": {
        "events_preserved": true,
        "characters_preserved": true,
        "relationships_preserved": true,
        "emotion_preserved": true,
        "intent_preserved": true,
        "facts_preserved": true,
        "cultural_meaning_preserved": true,
        "timing_preserved": true
      },
      "issues": [],
      "flags": [],
      "status": "approved"
    }
  ],
  "summary": {
    "total_scenes": 12,
    "approved": 12,
    "flagged": 0,
    "pending": 0
  }
}
```

## Prompts Folder

```
prompts/
├── story/
│   ├── story_analysis_v001.txt
│   └── story_analysis_v002.txt
├── characters/
│   ├── char_001_prompt_v001.txt
│   ├── char_001_negative_v001.txt
│   ├── char_001_prompt_v002.txt
│   └── char_001_negative_v002.txt
├── scenes/
│   ├── scene_0001_master_v001.txt
│   ├── scene_0001_character_v001.txt
│   ├── scene_0001_environment_v001.txt
│   ├── scene_0001_camera_v001.txt
│   ├── scene_0001_lighting_v001.txt
│   ├── scene_0001_motion_v001.txt
│   ├── scene_0001_image_v001.txt
│   ├── scene_0001_i2v_v001.txt
│   ├── scene_0001_voice_v001.txt
│   ├── scene_0001_music_v001.txt
│   ├── scene_0001_sfx_v001.txt
│   └── scene_0001_negative_v001.txt
├── images/
├── video/
├── audio/
├── music/
└── sfx/
```

## Images Folder

```
images/
├── characters/
│   ├── char_001_v001.png
│   ├── char_001_v002.png
│   ├── char_001_v003.png (approved)
│   └── char_002_v001.png
├── locations/
│   ├── loc_001_v001.png
│   └── loc_002_v001.png
└── scenes/
    ├── scene_0001_v001.png
    ├── scene_0001_v002.png
    └── scene_0002_v001.png
```

### Image Metadata (adjacent .json files)
```json
{
  "image_id": "img_001",
  "source": "characters/char_001_v003.png",
  "type": "character_reference",
  "prompt": "Cinematic portrait of Brahma...",
  "negative_prompt": "ugly, deformed...",
  "seed": 123456789,
  "model": "sdxl-base",
  "parameters": {
    "width": 1024,
    "height": 1024,
    "steps": 30,
    "guidance_scale": 7.5,
    "scheduler": "euler_ancestral"
  },
  "dimensions": {"width": 1024, "height": 1024},
  "file_size_bytes": 2048576,
  "sha256": "abc123...",
  "created_at": "2024-01-15T11:45:00Z",
  "created_by": "local_python:sdxl-base",
  "version": "v003",
  "approved": true
}
```

## Video Folder

```
video/
├── scenes/
│   ├── scene_0001_v001.mp4
│   ├── scene_0001_v002.mp4
│   └── scene_0002_v001.mp4
├── silent_master/
│   ├── master_v001.mp4
│   └── master_v002.mp4
└── previews/
    ├── preview_en.mp4
    └── preview_te.mp4
```

## Audio Folder

```
audio/
├── narration/
│   ├── en/
│   │   ├── scene_0001_narration.wav
│   │   └── scene_0002_narration.wav
│   └── te/
│       └── ...
├── dialogue/
│   ├── en/
│   │   ├── scene_0001_char_001.wav
│   │   └── scene_0001_char_002.wav
│   └── te/
│       └── ...
├── music/
│   ├── en/
│   │   ├── scene_0001_music.wav
│   │   └── scene_0002_music.wav
│   └── te/
│       └── ...
├── sfx/
│   ├── en/
│   │   ├── scene_0001_sfx.wav
│   │   └── scene_0002_sfx.wav
│   └── te/
│       └── ...
└── master/
    ├── en_master_audio.wav
    ├── te_master_audio.wav
    └── hi_master_audio.wav
```

## Output Folder

```
output/
├── en/
│   └── final.mp4
├── te/
│   └── final.mp4
├── hi/
│   └── final.mp4
├── kn/
│   └── final.mp4
├── ta/
│   └── final.mp4
├── ml/
│   └── final.mp4
├── bn/
│   └── final.mp4
├── fr/
│   └── final.mp4
├── de/
│   └── final.mp4
├── pt/
│   └── final.mp4
├── nl/
│   └── final.mp4
└── es/
    └── final.mp4
```

## Approvals Folder

```
approvals/
├── character_001.json
├── character_002.json
├── scene_0001.json
├── scene_0002.json
├── translation_en.json
├── translation_te.json
├── final_video_en.json
└── final_video_te.json
```

### Approval Record
```json
{
  "approval_id": "uuid",
  "asset_type": "character",
  "asset_id": "char_001",
  "asset_version": "v003",
  "asset_path": "characters/character_001/approved/reference.png",
  "asset_hash": "sha256:abc123...",
  "approved": true,
  "approved_by": "user",
  "approved_at": "2024-01-15T12:00:00Z",
  "notes": "Perfect match to canonical description",
  "previous_version": "v002",
  "changes": "Improved facial details, better lighting"
}
```

## Logs Folder

```
logs/
├── 2024-01-15.jsonl
├── 2024-01-16.jsonl
└── errors.jsonl
```

### Log Entry (JSONL)
```json
{"timestamp": "2024-01-15T11:30:00Z", "level": "INFO", "component": "StoryService", "message": "Story analysis started", "project_id": "uuid", "job_id": "job_001"}
{"timestamp": "2024-01-15T11:30:05Z", "level": "INFO", "component": "LLMProvider", "message": "Model loaded", "model": "llama-3-8b-instruct", "device": "cuda", "vram_mb": 5120}
{"timestamp": "2024-01-15T11:35:00Z", "level": "INFO", "component": "StoryService", "message": "Story analysis completed", "duration_seconds": 300, "characters_found": 5, "scenes_found": 12}
```

## Jobs Folder

```
jobs/
├── job_001.json
├── job_002.json
└── job_003.json
```

### Job State
```json
{
  "job_id": "job_001",
  "project_id": "uuid",
  "type": "story_analysis",
  "status": "completed",
  "created_at": "2024-01-15T11:30:00Z",
  "started_at": "2024-01-15T11:30:00Z",
  "completed_at": "2024-01-15T11:35:00Z",
  "progress": 100,
  "current_step": "save_results",
  "total_steps": 5,
  "steps": [
    {"name": "load_transcript", "status": "completed", "duration_seconds": 0.5},
    {"name": "detect_language", "status": "completed", "duration_seconds": 1.2},
    {"name": "analyze_story", "status": "completed", "duration_seconds": 280},
    {"name": "extract_characters", "status": "completed", "duration_seconds": 15},
    {"name": "save_results", "status": "completed", "duration_seconds": 2}
  ],
  "provider": "local_python:llama-3-8b-instruct",
  "input": {"transcript_path": "transcript/normalized.json"},
  "output": {"story_path": "story/story.json", "characters_path": "characters/characters.json"},
  "error": null,
  "retry_count": 0,
  "cancel_requested": false
}
```

## Exports Folder

```
exports/
├── project_backup_20240115_143000.zip
├── prompt_package_20240115_143000.zip
├── character_package_20240115_143000.zip
├── storyboard_20240115_143000.json
├── transcript_20240115_143000.txt
├── translations_20240115_143000.json
└── final_videos_20240115_143000.zip
```

## File Integrity

Every important file has an adjacent `.meta.json`:
```json
{
  "file_path": "characters/character_001/approved/reference.png",
  "sha256": "abc123...",
  "file_size_bytes": 2048576,
  "created_at": "2024-01-15T11:45:00Z",
  "modified_at": "2024-01-15T11:45:00Z",
  "version": "v003",
  "generator": "local_python:sdxl-base",
  "generation_params": {...}
}
```

## Versioning Rules

1. **Never overwrite** - Always create new version
2. **Naming**: `{base}_v{number:03d}.{ext}` (v001, v002, v003)
3. **Active version** tracked in `project.json.active_versions`
4. **Approved version** locked in `approved/` subfolder
5. **Maximum versions** configurable (default 10, then auto-clean oldest drafts)

## Language Codes

| Code | Language | Native Name |
|------|----------|-------------|
| en | English | English |
| te | Telugu | తెలుగు |
| hi | Hindi | हिन्दी |
| kn | Kannada | ಕನ್ನಡ |
| ta | Tamil | தமிழ் |
| ml | Malayalam | മലയാളം |
| bn | Bengali | বাংলা |
| fr | French | Français |
| de | German | Deutsch |
| pt | Portuguese | Português |
| nl | Dutch | Nederlands |
| es | Spanish | Español |

## Status Values

| Entity | Status Values |
|--------|---------------|
| Project | draft, in_progress, review, completed, archived |
| Character | draft, generated, review_required, approved, locked |
| Scene | draft, prompts_generated, images_generated, video_generated, approved, rendered |
| Translation | draft, translated, review_required, approved |
| Job | queued, running, paused, cancel_requested, cancelled, failed, completed |
| Approval | pending, approved, rejected, changes_requested |

## Recovery & Portability

- Copy entire project folder to another machine → works immediately
- No absolute paths in project files (all relative to project root)
- `project.json` contains all metadata needed to reconstruct state
- Models and application config live outside project folder