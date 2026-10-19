# LumaRead reference comparison

WavLM-Large by Microsoft and its listed authors; unmodified model weights:
https://huggingface.co/microsoft/wavlm-large/tree/c1423ed94bb01d80a3f5ce5bc39f6026a0f4828c

The model card links CC BY-SA 3.0 (full upstream text in LICENSE-WavLM.txt).
No model weights are committed. PyTorch uses BSD-style licensing; Transformers and
Accelerate Apache-2.0; NumPy BSD-3-Clause; Numba BSD-2-Clause; FastAPI/Uvicorn MIT.
Installed distributions retain their licenses. This implementation does not copy a paper's code.

Model binary SHA256: fdee460e529396ddb2f8c8e8ce0ad74cfb747b726bc6f612e666c7c1e1963c9d
Place config.json, preprocessor_config.json, pytorch_model.bin and a REVISION file
containing the pinned commit under models/wavlm-large. Mount it read-only.

Start with `docker compose -f compose.yml -f compose.scoring.yml up -d scorer`.
Use `python probe.py` in a separate container with the same limits before activation.
Set LUMA_SPEECH_PROVIDER=reference_similarity only after resource checks and real
recording smoke tests. LUMA_REFERENCE_URL defaults to http://scorer:8000.
If safety tests fail, leave provider disabled. Do not increase resource limits on a
shared server without checking the other applications' headroom.

The model runs FP32, last layer, full sequence, 16 kHz. The comparison index is
100*clip(1-path_mean_cosine_distance,0,1). No ASR, fabricated phoneme metrics,
pass threshold, model quantization or segmented model inference is used.
Two-second result bins are visualization only. They do not change model inference.
Energy checks reject silence/very quiet/clipped recordings but do not establish
that a recording contains speech; noise and speaker effects remain limitations.
Cache is bounded to 512 MiB and can be removed safely; models are persistent.

Child/adult cross-speaker and omission/substitution tests require real samples.
All results remain experimental until that validation has been performed.
