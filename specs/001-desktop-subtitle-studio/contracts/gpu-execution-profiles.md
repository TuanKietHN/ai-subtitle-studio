# Contract: GPU Detection and Execution Profiles

## Purpose

Define how AI Subtitle Studio detects NVIDIA hardware, selects a safe WhisperX
execution profile and handles low-VRAM failures without hard-coding a developer
GPU model. This contract supplements `stt-engine-contract.md`; all mandatory
WhisperX/Pyannote VAD and single-GPU-job invariants remain unchanged.

## GPU Inventory Contract

The system MUST collect, per detected NVIDIA GPU:

- CUDA-visible GPU id;
- device name and driver version;
- total VRAM and currently free VRAM;
- compute capability when Torch can query it;
- Torch CUDA initialization status;
- CTranslate2 supported compute types.

`nvidia-smi` MAY provide name/driver/memory diagnostics, but successful
`nvidia-smi` execution MUST NOT by itself make a GPU STT-capable. STT preflight
MUST require `torch.cuda.is_available()` and successful initialization of the
selected CUDA device.

The selected numeric id MUST be applied with `torch.cuda.set_device()` and
passed to WhisperX/Faster-Whisper as `device_index`; setting or assuming a GPU
marketing name is forbidden. Torch inventory collection MUST restore the
previous CUDA device after probing so diagnostics cannot silently change the
execution target.

The Settings GPU selector MUST be populated from this inventory. No branch may
depend on a marketing-name literal such as `RTX 2050` or the developer's GPU.

## Model Catalog Contract

- `resources/models.json` remains the source of model options.
- `large-v3` remains the only default model.
- RC5 adds enabled entries for `small.en` and `small` with config-driven VRAM
  compatibility metadata.
- UI and STT code MUST NOT hard-code the full list of model ids.
- The catalog validator MUST reject duplicate ids, an absent/non-unique default,
  invalid VRAM metadata and an execution profile referencing an unknown model.

## Effective Transcription Request

An effective GPU transcription request contains:

```text
job_id
audio_path
model_id
gpu_id
device = "cuda"
compute_type
batch_size
model_cache_dir
language_hint
```

It MUST NOT contain a public VAD option. The WhisperX wrapper MUST continue to
call `load_model(..., vad_method="pyannote")` for every profile.

`batch_size` MUST be passed to `model.transcribe()` and MUST be a positive
integer. `compute_type` MUST be checked against the selected device's
CTranslate2 supported types before model load.

## RC5 Low-VRAM Profile

For a compatible NVIDIA GPU with approximately 4 GiB total VRAM:

- profile id: `low-vram-4gb`;
- recommended English model: `small.en`;
- multilingual alternative: `small`;
- preferred compute type: `int8_float16` when reported supported;
- transcription batch size: `1`;
- diarization: disabled/out of RC5 scope;
- GPU STT concurrency: exactly one;
- mandatory Pyannote VAD: unchanged.

If the selected model is incompatible with detected VRAM, the UI MUST explain
the risk and offer a one-click profile/model change. It MUST NOT silently
replace the model or redefine the catalog default.

## Phase Memory Contract

WhisperX execution is split into memory phases:

1. Load ASR/VAD model.
2. Transcribe with the effective compute type and batch size.
3. Release all ASR model references.
4. Synchronize only when required, collect unreachable Python objects, then
   release unused CUDA cache.
5. Load and run alignment.
6. Release alignment model/tensors and unused cache.

Calling `torch.cuda.empty_cache()` while live model tensors remain does not
satisfy this contract. Tests MUST prove the ASR model is no longer referenced
before alignment model load.

## CUDA OOM Contract

- CUDA out-of-memory MUST map to a stable `gpu_out_of_memory` error category.
- The engine MUST release phase resources before any retry.
- At most one automatic retry is allowed, using the same selected model and a
  smaller/equal effective batch size (RC5 low-VRAM is already batch 1).
- The engine MUST NOT silently switch models during retry.
- A second OOM MUST stop the job with detected VRAM, effective model/profile and
  an actionable recommendation; other queued jobs remain intact.

## Diagnostics Contract

System Info and non-secret logs MUST expose:

- selected GPU id/name, total/free VRAM and driver;
- Torch CUDA readiness and CUDA runtime version;
- selected/effective model, compute type and batch size;
- CTranslate2 compute-type support;
- peak allocated/reserved VRAM for acceptance runs;
- cleanup/retry outcome when OOM occurs.

No API key, subtitle content or credential value may be added to these logs.

## Acceptance Contract

Automated coverage MUST include mocked 4 GiB and 8+ GiB devices, false-positive
`nvidia-smi`, unsupported compute type, batch propagation, phase resource
release and bounded OOM retry.

RC5 manual acceptance MUST run on an RTX 2050 4 GiB or another NVIDIA CUDA GPU
with 4 GiB total VRAM:

1. Detect the correct GPU name and capacity.
2. Apply `low-vram-4gb` after user confirmation.
3. Process at least two owned/licensed English MP4 samples sequentially.
4. Complete ASR, forced alignment and English SRT export without CUDA OOM.
5. Record peak VRAM and effective profile in the acceptance evidence.
6. Verify UI responsiveness, cancel/retry behavior and the global one-GPU-job
   lock.

Support for 4 GiB MUST NOT be advertised as validated until this real-hardware
gate passes.
