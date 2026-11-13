
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
*   **Flexible AI Brains:** Pluggable LLM backends (Ollama default, OpenAI support via `llm_module.py`).
*   **Customizable Voices:** Choose from different Text-to-Speech engines (Kokoro, Coqui, Orpheus via `audio_module.py`).
*   **Web Interface:** Clean and simple UI using Vanilla JS and the Web Audio API.
*   **Dockerized Deployment:** Recommended setup using Docker Compose for easier dependency management.

## Quick Start 🧭

If this is your first time using the project, the easiest path is:

1. Install the dependencies with Docker or the Windows setup script.
2. Start the app with `docker compose up -d` or `python server.py` inside `code/`.
3. Open `http://localhost:8000`, allow microphone access, then press **Start**.

You do not need to change the code to try it out. If the app does not respond, check the browser permission prompt and confirm your model and TTS settings are available.

## Technology Stack 🛠️

*   **Backend:** Python < 3.13, FastAPI
*   **Frontend:** HTML, CSS, JavaScript (Vanilla JS, Web Audio API, AudioWorklets)
*   **Communication:** WebSockets
*   **Containerization:** Docker, Docker Compose
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
    *   The setup assumes **CUDA 12.1**. Adjust PyTorch installation if you have a different CUDA version.
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

Now, choose your adventure:

<details>
<summary><strong>🚀 Option A: Docker Installation (Recommended for Linux/GPU)</strong></summary>

This is the most straightforward method, bundling the application, dependencies, and even Ollama into manageable containers.

1.  **Build the Docker images:**
    *(This takes time! It downloads base images, installs Python/ML dependencies, and pre-downloads the default STT model.)*
    ```bash
    docker compose build
    ```
    *(If you want to customize models/settings in `code/*.py`, do it **before** this step!)*

2.  **Start the services (App & Ollama):**
    *(Runs containers in the background. GPU access is configured in `docker-compose.yml`.)*
    ```bash
    docker compose up -d
    ```
    Give them a minute to initialize.

3.  **(Crucial!) Pull your desired Ollama Model:**
    *(This is done *after* startup to keep the main app image smaller and allow model changes without rebuilding. Execute this command to pull the default model into the running Ollama container.)*
    ```bash
    # Pull the default model (adjust if you configured a different one in server.py)
    docker compose exec ollama ollama pull hf.co/bartowski/huihui-ai_Mistral-Small-24B-Instruct-2501-abliterated-GGUF:Q4_K_M

    # (Optional) Verify the model is available
    docker compose exec ollama ollama list
    ```

4.  **Stopping the Services:**
    ```bash
    docker compose down
    ```

5.  **Restarting:**
    ```bash
    docker compose up -d
    ```

6.  **Viewing Logs / Debugging:**
    *   Follow app logs: `docker compose logs -f app`
    *   Follow Ollama logs: `docker compose logs -f ollama`
    *   Save logs to file: `docker compose logs app > app_logs.txt`

</details>

<details>
<summary><strong>🛠️ Option B: Manual Installation (Windows Script / venv)</strong></summary>

This method requires managing the Python environment yourself. It offers more direct control but can be trickier, especially regarding ML dependencies.

**B1) Using the Server/Client Installer:**

1. Choose **Server** on the computer that will run speech processing and the AI stack. Choose **Client** on other devices; client setup opens the server in a browser and does not install AI dependencies.
2. Server setup creates a private-LAN HTTPS certificate and a one-time access token. Keep the token private. Copy `code/data/server-ca.crt` to each client device and add it to that device's trusted certificate authorities before opening the client URL. On Windows, allow Python through the firewall for private networks if prompted.
3. Use the installer for your platform:
    ```batch
    install.bat
    ```
    ```sh
    bash install.sh
    ```
    The server installer installs the AI dependencies. The client option only needs Python to open the server URL.

**B2) Manual Server Installation (Linux/macOS/Windows):**

1.  **Create & Activate Virtual Environment:**
    ```bash
    python -m venv venv
    # Linux/macOS:
    source venv/bin/activate
    # Windows:
    .\venv\Scripts\activate
    ```

2.  **Upgrade Pip:**
    ```bash
    python -m pip install --upgrade pip
    ```

3.  **Navigate to Code Directory:**
    ```bash
    cd code
    ```

4.  **Install PyTorch (Crucial Step - Match Your Hardware!):**
    *   **With NVIDIA GPU (CUDA 12.1 Example):**
        ```bash
        # Verify your CUDA version! Adjust 'cu121' and the URL if needed.
        pip install torch==2.5.1+cu121 torchaudio==2.5.1+cu121 torchvision --index-url https://download.pytorch.org/whl/cu121
        ```
    *   **CPU Only (Expect Slow Performance):**
        ```bash
        # pip install torch torchaudio torchvision
        ```
    *   *Find other PyTorch versions:* [https://pytorch.org/get-started/previous-versions/](https://pytorch.org/get-started/previous-versions/)

5.  **Install Other Requirements:**
    ```bash
    pip install -r requirements.txt
    ```
    *   **Note on DeepSpeed:** The Windows installer uses the project's Python 3.10/CUDA 12.1 wheel; Linux attempts a normal DeepSpeed install. macOS skips DeepSpeed, and Coqui runs without that optional acceleration when it is unavailable.
6.  **For private-LAN client access**, return to the repository root and run:
    ```bash
    cd ..
    python setup.py --configure-server
    ```
    Follow the prompts, then start the server with HTTPS enabled. Skip this step for a local-only installation.

</details>

---

## Running the Application ▶️

**If using Docker:**
Your application is already running via `docker compose up -d`! Check logs using `docker compose logs -f app`.

**If using Manual/Script Installation:**

1.  **Activate your virtual environment** (if not already active):
    ```bash
    # Linux/macOS: source ../venv/bin/activate
    # Windows: ..\venv\Scripts\activate
    ```
2.  **Navigate to the `code` directory** (if not already there):
    ```bash
    cd code
    ```
3.  **Start the FastAPI server:**
    ```bash
    python server.py
    ```

**Accessing the Client:**

1.  For a local-only installation, open `http://localhost:8000`. For Docker, open `http://localhost:8000` on the host running Docker.
2.  **Grant microphone permissions** when prompted.
3.  Click **"Start"** to begin chatting! Use "Stop" to end and "Reset" to clear the conversation.

For a configured LAN server, use its `https://<server-ip>:8000` URL instead. The server requires the access token generated during setup. Settings can only be changed from the server computer. On the client, the installer asks for the server URL and opens it in your browser; the browser asks for the access token when you start a voice session. The current backend supports one active voice session at a time.

**Trusting the LAN certificate:** Windows clients can open the shared `.crt` file and install it for the current user under **Trusted Root Certification Authorities**. On macOS, import it into Keychain Access and set it to **Always Trust**. On Debian/Ubuntu Linux, copy it to `/usr/local/share/ca-certificates/realtimevoicechat-ca.crt` and run `sudo update-ca-certificates`. Other Linux distributions and some browsers have their own trust-store steps. Restart the browser after importing if it still reports an untrusted certificate. Only share the CA certificate; never share `server.key`.

---

## Application Settings ⚙️

Open **Settings** in the web interface to choose the AI provider and model, configure its endpoint, select the speech engine and voice, adjust speech speed, choose the transcription language and model, and customize the assistant prompt. Local LLM choices include Ollama, LM Studio, and other servers that provide an OpenAI-compatible API, such as llama.cpp server.

Settings are saved locally in `code/data/settings.json` (or in the persistent `app_settings` Docker volume). Changes take effect after restarting the application. For Docker, restart with `docker compose restart app`.

API keys are not stored in the settings file. Set `OPENAI_API_KEY` in the environment before starting the application when using the OpenAI provider. Ollama models must be available to the selected Ollama service; pull any missing model before restarting.

For safety, the settings dashboard is available from the server computer at `http://localhost:8000`. A server configured for LAN access uses its HTTPS URL instead. Settings remain restricted to the server computer.

Advanced internal tuning still requires editing the relevant source files.

LAN setup is configured by `setup.py`; no source edits are required. The server creates a private CA and a server certificate for the chosen LAN IP or hostname. Copy only `code/data/server-ca.crt` to client devices and trust it there. The server access token is stored as a hash; if the token is lost, run `python setup.py --configure-server` again and share the newly generated token and CA certificate.

---

## Contributing 🤝

Got ideas or found a bug? Contributions are welcome! Feel free to open issues or submit pull requests.

## License 📜

The core codebase of this project is released under the **Apache License 2.0** (see the [LICENSE](./LICENSE) and [NOTICE](./NOTICE) files for details). Versions published before 2026-11-10 were made available under the MIT License.

This project relies on external specific TTS engines (like `Coqui XTTSv2`) and LLM providers which have their **own licensing terms**. Please ensure you comply with the licenses of all components you use.
