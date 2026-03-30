from faster_whisper import WhisperModel
import time

print("Loading/Downloading base.en model on CPU...")
start = time.time()
model = WhisperModel("base.en", device="cpu", compute_type="int8")
print(f"Model loaded in {time.time() - start:.2f}s!")
