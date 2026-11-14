
# Real-Time AI Voice Chat 🎤💬🧠🔊

<a href="https://hackergit.org/r/KoljaB/RealtimeVoiceChat"><img src="https://hackergit.org/badge/KoljaB/RealtimeVoiceChat.svg?style=rank" alt="Hacker News rank via HackerGit" width="250" height="55"></a>

**Have a natural, spoken conversation with an AI!**  

This project lets you chat with a Large Language Model (LLM) using just your voice, receiving spoken responses in near real-time. Think of it as your own digital conversation partner.

https://github.com/user-attachments/assets/16cc29a7-bec2-4dd0-a056-d213db798d8f

*(early preview - first reasonably stable version)*

> ❗ **Project Status: Community-Driven**
> 
> This project is no longer being actively maintained by me due to time constraints. I've taken on too many projects and I have to step back. I will no longer be implementing new features or providing user support.
>
> I will continue to review and merge high-quality, well-written Pull Requests from the community from time to time. Your contributions are welcome and appreciated!

## What's Under the Hood?

A sophisticated client-server system built for low-latency interaction:

1.  🎙️ **Capture:** Your voice is captured by your browser.
2.  ➡️ **Stream:** Audio chunks are whisked away via WebSockets to a Python backend.
3.  ✍️ **Transcribe:** `RealtimeSTT` rapidly converts your speech to text.
4.  🤔 **Think:** The text is sent to an LLM (like Ollama or OpenAI) for processing.
5.  🗣️ **Synthesize:** The AI's text response is turned back into speech using `RealtimeTTS`.
6.  ⬅️ **Return:** The generated audio is streamed back to your browser for playback.
7.  🔄 **Interrupt:** Jump in anytime! The system handles interruptions gracefully.

## Key Features ✨

*   **Fluid Conversation:** Speak and listen, just like a real chat.
*   **Real-Time Feedback:** See partial transcriptions and AI responses as they happen.
*   **Low Latency Focus:** Optimized architecture using audio chunk streaming.
*   **Smart Turn-Taking:** Dynamic silence detection (`turndetect.py`) adapts to the conversation pace.
*   **Flexible AI Brains:** Choose between Ollama, LM Studio, OpenAI, or a custom OpenAI-compatible local server.
*   **Customizable Voices:** Choose from different Text-to-Speech engines (Kokoro, Coqui, Orpheus via `audio_module.py`).
*   **Web Interface:** Clean and simple UI using Vanilla JS and the Web Audio API.
*   **App-First Setup:** One local app, multiple AI backends, no forced Docker or installer-first workflow.

## Technology Stack 🛠️

*   **Backend:** Python < 3.13, FastAPI
*   **Frontend:** HTML, CSS, JavaScript (Vanilla JS, Web Audio API, AudioWorklets)
*   **Communication:** WebSockets
*   **Core AI/ML Libraries:**
    *   `RealtimeSTT` (Speech-to-Text)
    *   `RealtimeTTS` (Text-to-Speech)
    *   `transformers` (Turn detection, Tokenization)
    *   `torch` / `torchaudio` (ML Framework)
    *   `ollama` / `openai` (LLM Clients)
*   **Audio Processing:** `numpy`, `scipy`

## Before You Dive In: Prerequisites 🏊‍♀️

This project leverages powerful AI models, which have some requirements:

*   **Operating System:**
    *   **Docker:** Linux is recommended for the best GPU integration with Docker.
    *   **Manual:** The provided script (`install.bat`) is for Windows. Manual steps are possible on Linux/macOS but may require more troubleshooting (especially for DeepSpeed).
*   **🐍 Python:** 3.9 or higher (if setting up manually).
*   **🚀 GPU:** **A powerful CUDA-enabled NVIDIA GPU is *highly recommended***, especially for faster STT (Whisper) and TTS (Coqui). Performance on CPU-only or weaker GPUs will be significantly slower.
    *   The Windows installer uses the project's Python requirements without assuming a specific CUDA version. GPU acceleration may require installing a PyTorch build that matches your hardware.
    *   **Docker (Linux):** Requires [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/install-guide.html).
*   **🐳 Docker (Optional but Recommended):** Docker Engine and Docker Compose v2+ for the containerized setup.
*   **🧠 Ollama (Optional):** If using the Ollama backend *without* Docker, install it separately and pull your desired models. The Docker setup includes an Ollama service.
*   **🔑 OpenAI API Key (Optional):** If using the OpenAI backend, set the `OPENAI_API_KEY` environment variable (e.g., in a `.env` file or passed to Docker).

---

## Getting Started: Installation & Setup ⚙️

**Clone the repository first:**

```bash
git clone https://github.com/KoljaB/RealtimeVoiceChat.git
cd RealtimeVoiceChat
```

On Windows, run `install.bat` once to create a private Python environment and install the app dependencies. Then run `start_venv.bat` and start the app from that terminal with `python code\server.py`.

For a manual setup (including other platforms), install the Python dependencies and run the app as a single local client:

```bash
python -m pip install -r requirements.txt
python code/server.py
```

Open the local app in your browser. In Settings, use **Find models on this computer** to detect Ollama or LM Studio, or select a provider manually. No provider address is needed for the usual local setup. **Test connection** checks the selected provider before you save. Advanced connection settings remain available for custom model servers. This project is intentionally app-first: the app should work as one local interface with several supported backends instead of forcing a separate installer or server/client split.

---

## Running the Application ▶️

1. Activate your environment if needed.
2. Start the server:
   ```bash
   python code/server.py
   ```
3. Open `http://localhost:8000` in a browser.
4. Grant microphone access when prompted.
5. Click **Start** to begin chatting. Use **Stop** to end and **Reset** to clear the conversation.

---

## Configuration Deep Dive 🔧

Want to tweak the AI's voice, brain, or how it listens? Modify the Python files in the `code/` directory.

**⚠️ Important Docker Note:** If using Docker, make any configuration changes *before* running `docker compose build` to ensure they are included in the image.

*   **TTS Engine & Voice (`server.py`, `audio_module.py`):**
    *   Change `START_ENGINE` in `server.py` to `"coqui"`, `"kokoro"`, or `"orpheus"`.
    *   Adjust engine-specific settings (e.g., voice model path for Coqui, speaker ID for Orpheus, speed) within `AudioProcessor.__init__` in `audio_module.py`.
*   **LLM Backend & Model (`server.py`, `llm_module.py`):**
    *   Set `LLM_START_PROVIDER` (`"ollama"` or `"openai"`) and `LLM_START_MODEL` (e.g., `"hf.co/..."` for Ollama, model name for OpenAI) in `server.py`. Remember to pull the Ollama model if using Docker (see Installation Step A3).
    *   Customize the AI's personality by editing `system_prompt.txt`.
*   **STT Settings (`transcribe.py`):**
    *   Modify `DEFAULT_RECORDER_CONFIG` to change the Whisper model (`model`), language (`language`), silence thresholds (`silence_limit_seconds`), etc. The default `base.en` model is pre-downloaded during the Docker build.
*   **Turn Detection Sensitivity (`turndetect.py`):**
    *   Adjust pause duration constants within the `TurnDetector.update_settings` method.
*   **SSL/HTTPS (`server.py`):**
    *   Set `USE_SSL = True` and provide paths to your certificate (`SSL_CERT_PATH`) and key (`SSL_KEY_PATH`) files.
    *   **Docker Users:** You'll need to adjust `docker-compose.yml` to map the SSL port (e.g., 443) and potentially mount your certificate files as volumes.
    <details>
    <summary><strong>Generating Local SSL Certificates (Windows Example w/ mkcert)</strong></summary>

    1.  Install Chocolatey package manager if you haven't already.
    2.  Install mkcert: `choco install mkcert`
    3.  Run Command Prompt *as Administrator*.
    4.  Install a local Certificate Authority: `mkcert -install`
    5.  Generate certs (replace `your.local.ip`): `mkcert localhost 127.0.0.1 ::1 your.local.ip`
        *   This creates `.pem` files (e.g., `localhost+3.pem` and `localhost+3-key.pem`) in the current directory. Update `SSL_CERT_PATH` and `SSL_KEY_PATH` in `server.py` accordingly. Remember to potentially mount these into your Docker container.
    </details>

---

## Contributing 🤝

Got ideas or found a bug? Contributions are welcome! Feel free to open issues or submit pull requests.

## License 📜

The core codebase of this project is released under the **Apache License 2.0** (see the [LICENSE](./LICENSE) and [NOTICE](./NOTICE) files for details). Versions published before 2026-11-10 were made available under the MIT License.

This project relies on external specific TTS engines (like `Coqui XTTSv2`) and LLM providers which have their **own licensing terms**. Please ensure you comply with the licenses of all components you use.
