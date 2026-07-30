# Output Files Contract

## Output Naming

For a source video `Lecture 01.mp4`, default outputs are placed under the configured output directory using a collision-safe base name derived from the video file name:

- `Lecture 01.en.srt`
- `Lecture 01.vi.srt`
- `Lecture 01.bilingual.srt`

If a file already exists, the app must avoid silent overwrite. Default behavior is automatic unique-name generation using suffixes such as `(1)`, `(2)`, and so on. Overwrite is allowed only when the user explicitly chooses an overwrite action in the UI.

US1 creates the English `.en.srt` output. Vietnamese `.vi.srt` and bilingual `.bilingual.srt` outputs are produced by the translation/export workflow in US3.

## SRT Cue Rules

- Cue numbering starts at 1 and increments by 1.
- Cue timestamps use SRT `HH:MM:SS,mmm --> HH:MM:SS,mmm` format.
- Cue boundaries are sentence/cue-level and refined from word-level alignment.
- Default export must not produce one cue per word.
- Vietnamese and bilingual outputs preserve cue count, order and timestamps from English source cues.

## Bilingual Cue Rules

Each cue contains source English and Vietnamese translation for the same sequence number. Default layout:

```text
English sentence or phrase
Vietnamese sentence or phrase
```

## Partial Output Rules

- Intermediate files may be written to temp paths during processing.
- Final output paths must only be promoted when validation succeeds.
- Canceled or failed jobs must not overwrite a previous valid final output.
