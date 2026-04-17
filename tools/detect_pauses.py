import librosa
import numpy as np

# ==== CONFIG ====
AUDIO_FILE = ""
TOP_DB = 10                # sensitivity (lower = stricter silence)
MIN_SILENCE_SEC = 0.2      # minimum pause length
HOP_LENGTH = 512

# ==== LOAD AUDIO ====
y, sr = librosa.load(AUDIO_FILE)

# ==== FIND NON-SILENT INTERVALS ====
intervals = librosa.effects.split(
    y,
    top_db=TOP_DB,
    hop_length=HOP_LENGTH
)

# ==== CONVERT TO SILENCE INTERVALS ====
silences = []

prev_end = 0

for start, end in intervals:
    # gap between last sound and next sound = silence
    silence_start = prev_end
    silence_end = start

    duration = (silence_end - silence_start) / sr

    if duration >= MIN_SILENCE_SEC:
        silences.append((silence_start / sr, silence_end / sr))

    prev_end = end

# check trailing silence
final_duration = (len(y) - prev_end) / sr
if final_duration >= MIN_SILENCE_SEC:
    silences.append((prev_end / sr, len(y) / sr))

# ==== OUTPUT ====
print("Detected pauses:\n")

for start, end in silences:
    print(f"{start:.2f} sec  →  {end:.2f} sec  (duration: {end - start:.2f}s)")