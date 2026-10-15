# Sensitivity to the ASR scorer (Whisper model size)

Run: `outputs` (gTTS, English voice, isolated names). Each row re-scores the **same audio** with a different faster-whisper model size, so only the recognizer varies.

| Whisper model | n | English CER | African CER | gap | gap 95% CI | Cliff's δ | p |
|---------------|--:|------------:|------------:|----:|-----------|----------|---|
| tiny | 80 | 0.00 | 0.35 | **+0.35** | [0.28, 0.44] | +0.83 (large) | 5.8e-09 |
| base | 80 | 0.01 | 0.38 | **+0.38** | [0.30, 0.46] | +0.84 (large) | 5.0e-09 |
| small | 80 | 0.01 | 0.26 | **+0.25** | [0.20, 0.31] | +0.75 (large) | 9.3e-08 |

**Takeaway:** the African–English gap stays positive with a 95% CI clear of zero at *every* model size tested — the result is robust to the choice of recognizer, not an artefact of one ASR model.

