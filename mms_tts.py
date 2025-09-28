# Use a pipeline as a high-level helper
from transformers import pipeline
import torch
pipe = pipeline("text-to-speech", model="facebook/mms-tts-hin")

# Load model directly
from transformers import AutoTokenizer, AutoModelForTextToWaveform

tokenizer = AutoTokenizer.from_pretrained("facebook/mms-tts-hin")
model = AutoModelForTextToWaveform.from_pretrained("facebook/mms-tts-hin")
text = "यह हिंदी भाषा में कुछ उदाहरण पाठ है" # Hindi translation of "some example text in the Hindi language"
inputs = tokenizer(text, return_tensors="pt")

# Ensure input_ids is of type Long
inputs["input_ids"] = inputs["input_ids"].long()

with torch.no_grad():
    output = model(**inputs).waveform
from IPython.display import Audio
import numpy as np
import soundfile as sf

# Assuming 'output' is the waveform tensor from the previous cell
audio_output = Audio(output.squeeze().numpy(), rate=model.config.sampling_rate)

# Save the audio to a file instead of using display()
audio_data = output.squeeze().numpy()
sf.write("output_hindi_audio.wav", audio_data, model.config.sampling_rate)
print(f"Audio saved to: output_hindi_audio.wav")
print(f"Sample rate: {model.config.sampling_rate}")
print(f"Audio duration: {len(audio_data) / model.config.sampling_rate:.2f} seconds")
