# PAMASMMA Knowledge Training

PAMASMMA can learn from founder-provided books, notes, transcripts, audio and video through a governed knowledge fabric.

## Training is not blind fine-tuning

Uploaded material is stored as source-backed knowledge rather than silently modifying model weights. This preserves provenance, lets PAMASMMA distinguish evidence from instructions, and lets a source be deleted without contaminating unrelated memory.

Training modes:

- reference — factual/reference material that can be retrieved as evidence.
- behavioral — procedures, preferences and reasoning guidance that may shape execution while remaining subordinate to PAMASMMA security and governance controls.
- domain_playbook — domain-specific methods, rules and repeatable playbooks.

## Pipeline

Upload → Validate → Extract → Chunk → Embed → Index → Retrieve → Govern → Use → Evaluate

Supported source families include PDF, DOCX, EPUB, TXT/Markdown, SRT/VTT, common audio formats and common video formats. Videos can use embedded subtitles, a user-supplied transcript, or optional OpenAI transcription through the existing provider-neutral credential boundary.

Every chunk retains the source ID, filename, title, ordinal and citation label. Retrieved knowledge therefore remains attributable rather than becoming anonymous text in the context window.

## Safety boundaries

1. Uploaded knowledge is user-isolated.
2. Duplicate content is detected using SHA-256.
3. Upload sizes and extracted text are bounded.
4. Original binary files are temporary processing artifacts; PAMASMMA persists extracted knowledge, not unrestricted upload blobs.
5. Behavioral knowledge cannot override security, authentication or system-governance directives.
6. When transcription is unavailable, PAMASMMA reports awaiting_transcription instead of pretending the video was learned.

## API

- GET /api/v1/knowledge
- POST /api/v1/knowledge/upload multipart form: file, optional title, training_mode, optional scope_system_id, optional transcript
- DELETE /api/v1/knowledge/{source_id}

## Production note

Durable operation requires PAMASMMA's isolated PostgreSQL + pgvector infrastructure. In-memory mode is intentionally bounded and suitable for tests/demos only.
