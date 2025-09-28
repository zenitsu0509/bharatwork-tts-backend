const form = document.getElementById("translation-form");
const englishInput = document.getElementById("english-input");
const feedback = document.getElementById("feedback");
const resultBlock = document.getElementById("result");
const hindiOutput = document.getElementById("hindi-output");
const audioPlayer = document.getElementById("tts-audio");
const submitButton = document.getElementById("submit-button");

function setLoading(isLoading) {
  submitButton.disabled = isLoading;
  feedback.classList.remove("error");
  feedback.textContent = isLoading ? "Translating and generating speech…" : "";
}

function resetAudio() {
  if (audioPlayer.src) {
    URL.revokeObjectURL(audioPlayer.src);
    audioPlayer.removeAttribute("src");
  }
  audioPlayer.load();
}

function base64ToBlob(base64, format) {
  const binary = atob(base64);
  const array = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) {
    array[i] = binary.charCodeAt(i);
  }
  return new Blob([array.buffer], { type: `audio/${format}` });
}

async function handleSubmit(event) {
  event.preventDefault();
  const text = englishInput.value.trim();
  if (!text) {
    feedback.classList.add("error");
    feedback.textContent = "Please provide a sentence to translate.";
    return;
  }

  setLoading(true);
  resetAudio();
  resultBlock.classList.add("hidden");

  try {
    const response = await fetch("/api/translate", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });

    if (!response.ok) {
      const errorBody = await response.json().catch(() => ({}));
      const message = errorBody?.detail || "Translation service returned an error.";
      throw new Error(message);
    }

    const { hindi_text: hindiText, audio_base64: audioBase64, audio_format: audioFormat } = await response.json();

    hindiOutput.textContent = hindiText;

    const blob = base64ToBlob(audioBase64, audioFormat || "mp3");
    const url = URL.createObjectURL(blob);
    audioPlayer.src = url;
    audioPlayer.load();

    resultBlock.classList.remove("hidden");
    await audioPlayer.play().catch(() => undefined);
    feedback.textContent = "Done!";
  } catch (error) {
    console.error("Translation failed", error);
    feedback.classList.add("error");
    feedback.textContent = error.message || "Something went wrong while contacting the backend.";
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", handleSubmit);
