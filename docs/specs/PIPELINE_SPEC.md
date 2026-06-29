# Video Pipeline Specification

## Goal

Convert one uploaded Chinese video into a Vietnamese hardsub MP4.

## Pipeline Steps

```text
1. Validate input
2. Extract audio
3. Chunk audio
4. Transcribe Chinese
5. Merge transcript
6. Translate to Vietnamese
7. Generate SRT
8. Burn hardsub
9. Verify output
10. Cleanup intermediate files when safe
```

## Artifacts

For each job:

```text
/var/lib/reup-agent/jobs/{job_id}/
  input.mp4
  metadata.json
  audio/
    full_audio.mp3
    chunks/
      chunk_000.mp3
      chunk_001.mp3
  transcript/
    chunk_000.json
    chunk_001.json
    transcript.json
  translation/
    checkpoint.json
    translated.json
  subtitle/
    subtitle.srt
  output/
    output.mp4
  logs/
    ffmpeg_extract.log
    transcribe.log
    translate.log
    ffmpeg_render.log
```

## Input Validation

Use ffprobe to get:

```text
duration
video codec
audio stream exists
resolution
container format
```

Reject if:
```text
file > 500MB
no audio stream
unsupported container
duration too long for MVP
disk free too low
```

## Extract Audio

Recommended:

```bash
ffmpeg -y -i input.mp4   -vn   -ac 1   -ar 16000   -b:a 64k   audio/full_audio.mp3
```

## Chunk Audio

Why:
- Free transcription APIs often limit audio file size.
- Long videos need chunking.

MVP strategy:

```text
target chunk duration: 5 minutes
max chunk file size: configurable, default 20MB
overlap: optional 0.5–1 second later
```

Each chunk must store:

```json
{
  "chunk_index": 0,
  "start_offset_seconds": 0,
  "duration_seconds": 300,
  "path": "audio/chunks/chunk_000.mp3"
}
```

## Transcription

Input:
```text
audio chunk
language = zh
```

Output per chunk:
```json
{
  "segments": [
    {
      "id": 0,
      "start": 1.23,
      "end": 3.45,
      "text": "Chinese text"
    }
  ]
}
```

When merging chunks:
- Add `start_offset_seconds` to each segment start/end.
- Generate globally unique segment IDs.
- Preserve ordering.

## Translation

Input:
```json
[
  {"id": 1, "text": "..."},
  {"id": 2, "text": "..."}
]
```

Output:
```json
[
  {"id": 1, "translation": "..."},
  {"id": 2, "translation": "..."}
]
```

Rules:
- Preserve id.
- Preserve count.
- Preserve order.
- Never summarize.
- Retry validation failures.
- Checkpoint after every batch.

Reuse legacy `translate.py` logic, but make it importable and configurable.

## SRT Generation

Each segment with translation becomes:

```text
1
00:00:01,230 --> 00:00:03,450
Vietnamese text
```

Rules:
- Escape invalid characters.
- Wrap long lines if needed.
- Skip empty translation only if segment is empty.
- Preserve timing.

## Render Hardsub

Recommended low-resource command:

```bash
ffmpeg -y   -i input.mp4   -vf "subtitles=subtitle/subtitle.srt:force_style='FontName=Arial,FontSize=22,Outline=2,Shadow=1,MarginV=30'"   -c:v libx264   -preset ultrafast   -crf 28   -threads 1   -c:a aac   -b:a 128k   -progress logs/ffmpeg_progress.txt   output/output.mp4
```

## Progress Mapping

Approximate job progress:

```text
validate input:      0–5%
extract audio:       5–10%
chunk audio:         10–15%
transcribe:          15–45%
translate:           45–65%
generate srt:        65–70%
render:              70–98%
verify output:       98–100%
```

## Failure Behavior

Every failure must create:

```json
{
  "step": "TRANSCRIBING",
  "error_code": "TRANSCRIBE_FAILED",
  "message": "...",
  "stderr_tail": "...",
  "retryable": true
}
```

## Resume Behavior

MVP:
- If job fails, mark failed and release node.

Later:
- Resume from saved artifacts and checkpoints.
