# PAMASMMA Knowledge Training

PAMASMMA has a governed Knowledge Training subsystem separate from ordinary conversational memory.

## Sources

Supported ingestion includes PDF, EPUB, DOCX, TXT/Markdown/CSV/JSON, SRT/VTT subtitles, audio and video. Documents are parsed into chunks and embedded. Audio/video transcription uses the optional OpenAI transcription adapter and requires OPENAI_API_KEY; video extraction requires ffmpeg.

## Modes

Uploads default to knowledge. Procedure mode marks material as procedural guidance. Neither mode silently modifies model weights. Imported material is treated as retrievable context with provenance rather than unquestionable truth.

## API

GET /api/v1/knowledge/sources

POST /api/v1/knowledge/upload?training_mode=knowledge|procedure using multipart file

DELETE /api/v1/knowledge/sources/{source_id}

All routes use existing PAMASMMA bearer authentication.

## Governance

Uploads are size-limited and user-isolated. Source hashes provide provenance. Failed ingestion is recorded as failed. Deleting a source cascades to its chunks. Retrieved material carries filename and locator metadata so the cognitive engine can distinguish imported knowledge from ordinary memory.

## Future evolution

A later phase can add local Whisper/faster-whisper, source deduplication, user-visible chunk inspection, citation rendering, knowledge evaluation suites and explicit approval workflows for promoting procedural knowledge into the procedural memory class.
