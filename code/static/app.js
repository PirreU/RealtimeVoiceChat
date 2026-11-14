(function() {
  const originalLog = console.log.bind(console);
  console.log = (...args) => {
    const now = new Date();
    const hh = String(now.getHours()).padStart(2, '0');
    const mm = String(now.getMinutes()).padStart(2, '0');
    const ss = String(now.getSeconds()).padStart(2, '0');
    const ms = String(now.getMilliseconds()).padStart(3, '0');
    originalLog(
      `[${hh}:${mm}:${ss}.${ms}]`,
      ...args
    );
  };
})();

const statusDiv = document.getElementById("status");
const messagesDiv = document.getElementById("messages");
const speedSlider = document.getElementById("speedSlider");
const settingsBtn = document.getElementById("settingsBtn");
const settingsOverlay = document.getElementById("settingsOverlay");
const settingsForm = document.getElementById("settingsForm");
const settingsFeedback = document.getElementById("settingsFeedback");
const llmProviderSelect = document.getElementById("llmProvider");
const llmBaseUrlInput = document.getElementById("llmBaseUrl");
const ttsEngineSelect = document.getElementById("ttsEngine");
const ttsSpeedInput = document.getElementById("ttsSpeed");
const turnSpeedInput = document.getElementById("turnSpeed");
const providerStatus = document.getElementById("providerStatus");
const detectedProviders = document.getElementById("detectedProviders");

const PROVIDER_HELP = {
  ollama: "Use this if Ollama is running on your computer. It usually listens on http://localhost:11434.",
  openai: "Use this for OpenAI or Microsoft Azure OpenAI. Set OPENAI_API_KEY in the server environment first.",
  lmstudio: "Use this if LM Studio is running locally and exposing an OpenAI-compatible endpoint.",
  openai_compatible: "Use this for llama.cpp, custom local servers, or any OpenAI-compatible endpoint running on your machine."
};

speedSlider.disabled = true;  // start disabled

let socket = null;
let audioContext = null;
let mediaStream = null;
let micWorkletNode = null;
let ttsWorkletNode = null;

let isTTSPlaying = false;
let ignoreIncomingTTS = false;

let chatHistory = [];
let typingUser = "";
let typingAssistant = "";

// --- batching + fixed 8‑byte header setup ---
const BATCH_SAMPLES = 2048;
const HEADER_BYTES  = 8;
const FRAME_BYTES   = BATCH_SAMPLES * 2;
const MESSAGE_BYTES = HEADER_BYTES + FRAME_BYTES;

const bufferPool = [];
let batchBuffer = null;
let batchView = null;
let batchInt16 = null;
let batchOffset = 0;

function initBatch() {
  if (!batchBuffer) {
    batchBuffer = bufferPool.pop() || new ArrayBuffer(MESSAGE_BYTES);
    batchView   = new DataView(batchBuffer);
    batchInt16  = new Int16Array(batchBuffer, HEADER_BYTES);
    batchOffset = 0;
  }
}

function flushBatch() {
  const ts = Date.now() & 0xFFFFFFFF;
  batchView.setUint32(0, ts, false);
  const flags = isTTSPlaying ? 1 : 0;
  batchView.setUint32(4, flags, false);

  socket.send(batchBuffer);

  bufferPool.push(batchBuffer);
  batchBuffer = null;
}

function flushRemainder() {
  if (batchOffset > 0) {
    for (let i = batchOffset; i < BATCH_SAMPLES; i++) {
      batchInt16[i] = 0;
    }
    flushBatch();
  }
}

function initAudioContext() {
  if (!audioContext) {
    audioContext = new AudioContext();
  }
}

function base64ToInt16Array(b64) {
  const raw = atob(b64);
  const buf = new ArrayBuffer(raw.length);
  const view = new Uint8Array(buf);
  for (let i = 0; i < raw.length; i++) {
    view[i] = raw.charCodeAt(i);
  }
  return new Int16Array(buf);
}

async function startRawPcmCapture() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: {
        sampleRate: { ideal: 24000 },
        channelCount: 1,
        echoCancellation: true,
        // autoGainControl: true,
        noiseSuppression: true
      }
    });
    mediaStream = stream;
    initAudioContext();
    await audioContext.audioWorklet.addModule('/static/pcmWorkletProcessor.js');
    micWorkletNode = new AudioWorkletNode(audioContext, 'pcm-worklet-processor');

    micWorkletNode.port.onmessage = ({ data }) => {
      const incoming = new Int16Array(data);
      let read = 0;
      while (read < incoming.length) {
        initBatch();
        const toCopy = Math.min(
          incoming.length - read,
          BATCH_SAMPLES - batchOffset
        );
        batchInt16.set(
          incoming.subarray(read, read + toCopy),
          batchOffset
        );
        batchOffset += toCopy;
        read       += toCopy;
        if (batchOffset === BATCH_SAMPLES) {
          flushBatch();
        }
      }
    };

    const source = audioContext.createMediaStreamSource(stream);
    source.connect(micWorkletNode);
    statusDiv.textContent = "Recording...";
  } catch (err) {
    statusDiv.textContent = "Mic access denied.";
    console.error(err);
  }
}

async function setupTTSPlayback() {
  await audioContext.audioWorklet.addModule('/static/ttsPlaybackProcessor.js');
  ttsWorkletNode = new AudioWorkletNode(
    audioContext,
    'tts-playback-processor'
  );

  ttsWorkletNode.port.onmessage = (event) => {
    const { type } = event.data;
    if (type === 'ttsPlaybackStarted') {
      if (!isTTSPlaying && socket && socket.readyState === WebSocket.OPEN) {
        isTTSPlaying = true;
        console.log(
          "TTS playback started. Reason: ttsWorkletNode Event ttsPlaybackStarted."
        );
        socket.send(JSON.stringify({ type: 'tts_start' }));
      }
    } else if (type === 'ttsPlaybackStopped') {
      if (isTTSPlaying && socket && socket.readyState === WebSocket.OPEN) {
        isTTSPlaying = false;
        console.log(
          "TTS playback stopped. Reason: ttsWorkletNode Event ttsPlaybackStopped."
        );
        socket.send(JSON.stringify({ type: 'tts_stop' }));
      }
    }
  };
  ttsWorkletNode.connect(audioContext.destination);
}

function cleanupAudio() {
  if (micWorkletNode) {
    micWorkletNode.disconnect();
    micWorkletNode = null;
  }
  if (ttsWorkletNode) {
    ttsWorkletNode.disconnect();
    ttsWorkletNode = null;
  }
  if (audioContext) {
    audioContext.close();
    audioContext = null;
  }
  if (mediaStream) {
    mediaStream.getAudioTracks().forEach(track => track.stop());
    mediaStream = null;
  }
}

function setSettingsFeedback(message, state = "") {
  settingsFeedback.textContent = message;
  settingsFeedback.className = state ? `settings-feedback ${state}` : "settings-feedback";
}

function updateProviderHelp() {
  const help = PROVIDER_HELP[llmProviderSelect.value] || "Choose the model service you want to use.";
  document.getElementById("llmProviderHelp").textContent = help;
  const baseUrlPlaceholder = {
    ollama: "Leave blank to use the default local Ollama endpoint.",
    openai: "Optional: only use this for a custom OpenAI-compatible proxy.",
    lmstudio: "Leave blank to use the default local LM Studio endpoint.",
    openai_compatible: "Required. Enter the base URL for your local OpenAI-compatible API, commonly ending in /v1."
  }[llmProviderSelect.value] || "Use the address reachable from this app.";
  llmBaseUrlInput.placeholder = baseUrlPlaceholder;
  const isGenericLocal = llmProviderSelect.value === "openai_compatible";
  llmBaseUrlInput.required = isGenericLocal;
  document.getElementById("llmBaseUrlHelp").textContent = isGenericLocal
    ? "Required. Enter the OpenAI-compatible API base URL reachable from this app, commonly ending in /v1. Works with llama.cpp and similar local servers."
    : "For local providers, leave this blank to use the default endpoint. For cloud APIs, set it only if you need a custom proxy.";
}

function updateSettingsFields(settings) {
  llmProviderSelect.value = settings.llm_provider;
  document.getElementById("llmModel").value = settings.llm_model || "";
  llmBaseUrlInput.value = settings.llm_base_url || "";
  ttsEngineSelect.value = settings.tts_engine;
  document.getElementById("ttsModel").value = settings.tts_model || "";
  document.getElementById("ttsVoice").value = settings.tts_voice || "";
  ttsSpeedInput.value = settings.tts_speed ?? 1.1;
  document.getElementById("sttLanguage").value = settings.stt_language || "en";
  document.getElementById("sttModel").value = settings.stt_model || "base.en";
  turnSpeedInput.value = settings.turn_speed ?? 0;
  document.getElementById("systemPrompt").value = settings.system_prompt || "";
  updateProviderHelp();
}

function showDetectedProviders(providers) {
  detectedProviders.replaceChildren();
  providerStatus.className = "settings-help";
  if (!providers.length) {
    providerStatus.textContent = "No local providers were found. Start Ollama or LM Studio and try again.";
    return;
  }

  providerStatus.textContent = "Local providers found. Select one to use it.";
  providers.forEach((provider) => {
    const button = document.createElement("button");
    const providerName = provider.provider === "ollama" ? "Ollama" : "LM Studio";
    const modelSummary = provider.models.length ? ` — ${provider.models.join(", ")}` : "";
    button.type = "button";
    button.className = "secondary";
    button.textContent = `${providerName}${modelSummary}`;
    button.addEventListener("click", () => {
      llmProviderSelect.value = provider.provider;
      llmBaseUrlInput.value = provider.base_url;
      if (provider.models.length) {
        document.getElementById("llmModel").value = provider.models[0];
      }
      updateProviderHelp();
      providerStatus.textContent = `${providerName} selected. Save settings to keep this choice.`;
    });
    detectedProviders.appendChild(button);
  });
}

async function openSettings() {
  settingsOverlay.hidden = false;
  setSettingsFeedback("Loading settings...");
  try {
    const response = await fetch("/api/settings");
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Could not load settings.");
    }
    updateSettingsFields(data.settings);
    detectedProviders.replaceChildren();
    providerStatus.textContent = "";
    setSettingsFeedback("");
  } catch (error) {
    setSettingsFeedback(error.message || "Could not load settings.", "error");
  }
}

async function detectLocalProviders() {
  const button = document.getElementById("detectProvidersBtn");
  button.disabled = true;
  detectedProviders.replaceChildren();
  providerStatus.className = "settings-help";
  providerStatus.textContent = "Checking the usual local Ollama and LM Studio addresses...";
  try {
    const response = await fetch("/api/providers/detect", { method: "POST" });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Could not check for local providers.");
    }
    showDetectedProviders(data.providers);
  } catch (error) {
    providerStatus.textContent = error.message || "Could not check for local providers.";
    providerStatus.className = "settings-help error";
  } finally {
    button.disabled = false;
  }
}

async function testProviderConnection() {
  const button = document.getElementById("testProviderBtn");
  button.disabled = true;
  providerStatus.className = "settings-help";
  providerStatus.textContent = "Testing provider connection...";
  try {
    const response = await fetch("/api/providers/test", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        llm_provider: llmProviderSelect.value,
        llm_model: document.getElementById("llmModel").value.trim(),
        llm_base_url: llmBaseUrlInput.value.trim()
      })
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(error => error.msg).join(" ")
        : data.detail;
      throw new Error(detail || "Could not test the provider connection.");
    }
    const models = Array.isArray(data.models) ? data.models : [];
    const modelListed = models.includes(document.getElementById("llmModel").value.trim());
    providerStatus.textContent = data.ok
      ? `${data.message}${models.length && !modelListed ? " The selected model was not listed by the provider." : ""}`
      : data.message;
    providerStatus.className = data.ok ? "settings-help success" : "settings-help error";
  } catch (error) {
    providerStatus.textContent = error.message || "Could not test the provider connection.";
    providerStatus.className = "settings-help error";
  } finally {
    button.disabled = false;
  }
}

function closeSettings() {
  settingsOverlay.hidden = true;
  setSettingsFeedback("");
  providerStatus.textContent = "";
  providerStatus.className = "settings-help";
}

settingsBtn.addEventListener("click", openSettings);
llmProviderSelect.addEventListener("change", updateProviderHelp);
document.getElementById("detectProvidersBtn").addEventListener("click", detectLocalProviders);
document.getElementById("testProviderBtn").addEventListener("click", testProviderConnection);
settingsOverlay.addEventListener("click", (event) => {
  if (event.target === settingsOverlay) {
    closeSettings();
  }
});

document.getElementById("closeSettingsBtn").addEventListener("click", closeSettings);
document.getElementById("cancelSettingsBtn").addEventListener("click", closeSettings);

document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !settingsOverlay.hidden) {
    closeSettings();
  }
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = document.getElementById("saveSettingsBtn");
  saveButton.disabled = true;
  const settingsPayload = {
    llm_provider: llmProviderSelect.value,
    llm_model: document.getElementById("llmModel").value.trim(),
    llm_base_url: llmBaseUrlInput.value.trim(),
    tts_engine: ttsEngineSelect.value,
    tts_model: document.getElementById("ttsModel").value.trim(),
    tts_voice: document.getElementById("ttsVoice").value.trim(),
    tts_speed: Number(ttsSpeedInput.value),
    turn_speed: Number(turnSpeedInput.value),
    stt_language: document.getElementById("sttLanguage").value.trim(),
    stt_model: document.getElementById("sttModel").value.trim(),
    system_prompt: document.getElementById("systemPrompt").value
  };

  setSettingsFeedback("Saving settings...");
  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settingsPayload)
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.detail || "Could not save settings.");
    }
    updateSettingsFields(data.settings);
    setSettingsFeedback(
      data.restart_required ? "Settings saved. Restart the app to apply them." : "Settings saved.",
      data.restart_required ? "notice" : "success"
    );
  } catch (error) {
    setSettingsFeedback(error.message || "Could not save settings.", "error");
  } finally {
    saveButton.disabled = false;
  }
});

function renderMessages() {
  messagesDiv.innerHTML = "";
  chatHistory.forEach(msg => {
    const bubble = document.createElement("div");
    bubble.className = `bubble ${msg.role}`;
    bubble.textContent = msg.content;
    messagesDiv.appendChild(bubble);
  });
  if (typingUser) {
    const typing = document.createElement("div");
    typing.className = "bubble user typing";
    typing.innerHTML = typingUser + '<span style="opacity:.6;">✏️</span>';
    messagesDiv.appendChild(typing);
  }
  if (typingAssistant) {
    const typing = document.createElement("div");
    typing.className = "bubble assistant typing";
    typing.innerHTML = typingAssistant + '<span style="opacity:.6;">✏️</span>';
    messagesDiv.appendChild(typing);
  }
  messagesDiv.scrollTop = messagesDiv.scrollHeight;
}

function handleJSONMessage({ type, content }) {
  if (type === "partial_user_request") {
    typingUser = content?.trim() ? escapeHtml(content) : "";
    renderMessages();
    return;
  }
  if (type === "final_user_request") {
    if (content?.trim()) {
      chatHistory.push({ role: "user", content, type: "final" });
    }
    typingUser = "";
    renderMessages();
    return;
  }
  if (type === "partial_assistant_answer") {
    typingAssistant = content?.trim() ? escapeHtml(content) : "";
    renderMessages();
    return;
  }
  if (type === "final_assistant_answer") {
    if (content?.trim()) {
      chatHistory.push({ role: "assistant", content, type: "final" });
    }
    typingAssistant = "";
    renderMessages();
    return;
  }
  if (type === "tts_chunk") {
    if (ignoreIncomingTTS) return;
    const int16Data = base64ToInt16Array(content);
    if (ttsWorkletNode) {
      ttsWorkletNode.port.postMessage(int16Data);
    }
    return;
  }
  if (type === "tts_interruption") {
    if (ttsWorkletNode) {
      ttsWorkletNode.port.postMessage({ type: "clear" });
    }
    isTTSPlaying = false;
    ignoreIncomingTTS = false;
    return;
  }
  if (type === "stop_tts") {
    if (ttsWorkletNode) {
      ttsWorkletNode.port.postMessage({ type: "clear" });
    }
    isTTSPlaying = false;
    ignoreIncomingTTS = true;
    console.log("TTS playback stopped. Reason: tts_interruption.");
    socket.send(JSON.stringify({ type: 'tts_stop' }));
    return;
  }
}

function escapeHtml(str) {
  return (str ?? '')
    .replace(/&/g, "&amp;")
    .replace(/</g, "<")
    .replace(/>/g, ">")
    .replace(/"/g, "&quot;");
}

// UI Controls

document.getElementById("clearBtn").onclick = () => {
  chatHistory = [];
  typingUser = typingAssistant = "";
  renderMessages();
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'clear_history' }));
  }
};

speedSlider.addEventListener("input", (e) => {
  const speedValue = parseInt(e.target.value);
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: 'set_speed',
      speed: speedValue
    }));
  }
  console.log("Speed setting changed to:", speedValue);
});

document.getElementById("startBtn").onclick = async () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    statusDiv.textContent = "Already recording.";
    return;
  }
  statusDiv.textContent = "Initializing connection...";

  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${wsProto}//${location.host}/ws`);

  socket.onopen = async () => {
    statusDiv.textContent = "Connected. Activating mic and TTS…";
    await startRawPcmCapture();
    await setupTTSPlayback();
    speedSlider.disabled = false; 
  };

  socket.onmessage = (evt) => {
    if (typeof evt.data === "string") {
      try {
        const msg = JSON.parse(evt.data);
        handleJSONMessage(msg);
      } catch (e) {
        console.error("Error parsing message:", e);
      }
    }
  };

  socket.onclose = () => {
    statusDiv.textContent = "Connection closed.";
    flushRemainder();
    cleanupAudio();
    speedSlider.disabled = true;
  };

  socket.onerror = (err) => {
    statusDiv.textContent = "Connection error.";
    cleanupAudio();
    console.error(err);
    speedSlider.disabled = true; 
  };
};

document.getElementById("stopBtn").onclick = () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    flushRemainder();
    socket.close();
  }
  cleanupAudio();
  statusDiv.textContent = "Stopped.";
};

document.getElementById("copyBtn").onclick = () => {
  const text = chatHistory
    .map(msg => `${msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}: ${msg.content}`)
    .join('\n');
  
  navigator.clipboard.writeText(text)
    .then(() => console.log("Conversation copied to clipboard"))
    .catch(err => console.error("Copy failed:", err));
};

// First render
renderMessages();
