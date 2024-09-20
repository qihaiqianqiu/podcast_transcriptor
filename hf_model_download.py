import os
os.environ["HF_ENDPOINT"] = "https://hf-mirror.com"
from pyannote.audio import Pipeline
access_token = "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"
pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization-3.1", use_auth_token=access_token)