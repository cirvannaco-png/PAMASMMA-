# PAMASMMA Knowledge Training

PAMASMMA has a governed Knowledge Training subsystem separate from ordinary conversational memory.

## Sources

Supported ingestion includes PDF, EPUB, DOCX, TXT/Markdown/CSV/JSON, SRT/VTT subtitles, audio and video.

Documents are extracted into provenance-preserving segments, chunked and embedded. PDF pages, EPUB sections and subtitle timestamps are retained as locators. Audio/video transcription uses the configured transcription adapter; the current built-in adapter uses OpenAI and requires `OPENAI_API_KEY`. Video extraction requires ffmpeg.

## Modes

Uploads default to **knowledge**. **Procedure** mode marks material as procedural guidance and retrieved chunks are represented as procedural memory rather than ordinary semantic memory.

Neither mode silently modifies model weights. Imported material is treated as retrievable evidence with provenance and reliability metadata, not unquestionable truth.

## API

```text
GET    /api/v1/knowledge/sources
GET    /api/v1/knowledge/sources/{source_id}/chunks
POST   /api/v1/knowledge/upload?training_mode=knowledge|procedure
DELETE /api/v1/knowledge/sources/{source_id}
```

All routes use the existing PAMASMMA bearer-authentication boundary and user isolation.

## Ingestion guarantees

- Uploads are size-limited before extraction.
- Archive-backed EPUB ingestion has extracted-size and member-count limits to reduce archive-bomb risk.
- Source filenames are reduced to their basename before temporary-file creation.
- SHA-256 content hashes provide stable provenance identifiers.
- Active duplicate sources are suppressed per user and training mode.
- Failed ingestion is recorded and can be retried after cleanup because only active/ready sources participate in the deduplication constraint.
- Knowledge chunks carry source ID, filename, training mode, memory type and locator metadata.
- Deleting a source cascades to its chunks in durable PostgreSQL mode.
- Chunk ordering is unique per source.

## Cognitive integration

During cognitive context preparation, PAMASMMA retrieves user-owned knowledge chunks alongside ordinary memory. Retrieved knowledge preserves source provenance and participates in the existing critic, evidence gate, metacognitive governor and confidence pipeline.

This is **retrieval-augmented cognition**, not weight training. The uploaded material changes what PAMASMMA can retrieve and reason over; it does not silently fine-tune the underlying model.

## Frontend

The authenticated sidebar provides:

- multi-file source selection
- Knowledge vs Procedure training mode
- ingestion progress and error feedback
- current source inventory
- source deletion

## Operational limits

Configure:

`KNOWLEDGE_MAX_UPLOAD_MB`

`KNOWLEDGE_MAX_ARCHIVE_EXTRACT_MB`

`KNOWLEDGE_MAX_ARCHIVE_FILES`

`KNOWLEDGE_CHUNK_SIZE`

`KNOWLEDGE_CHUNK_OVERLAP`

`KNOWLEDGE_SIMILARITY_THRESHOLD`

`KNOWLEDGE_TRANSCRIPTION_PROVIDER`

`KNOWLEDGE_TRANSCRIPTION_MODEL`

`KNOWLEDGE_MEDIA_TIMEOUT_SECONDS`

The current default transcription adapter is optional; text/document knowledge works without an OpenAI API key when local embeddings are used.

## Future evolution

The next architectural extensions should be asynchronous media jobs, optional local Whisper/faster-whisper transcription, explicit knowledge collections/scopes, richer timestamped media citations, knowledge evaluation suites, and approval workflows for promoting procedural knowledge into durable operating policies.
