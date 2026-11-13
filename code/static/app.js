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
const startBtn = document.getElementById("startBtn");
const stopBtn = document.getElementById("stopBtn");
const clearBtn = document.getElementById("clearBtn");
const copyBtn = document.getElementById("copyBtn");
const settingsBtn = document.getElementById("settingsBtn");
const settingsOverlay = document.getElementById("settingsOverlay");
const settingsForm = document.getElementById("settingsForm");
const settingsFeedback = document.getElementById("settingsFeedback");
const settingsRestartNotice = document.getElementById("settingsRestartNotice");
const themePreferenceSelect = document.getElementById("themePreference");
const themeFeedback = document.getElementById("themeFeedback");
const ttsEngineSelect = document.getElementById("ttsEngine");
const ttsVoiceInput = document.getElementById("ttsVoice");
const ttsSpeedInput = document.getElementById("ttsSpeed");
const turnSpeedInput = document.getElementById("turnSpeed");
const llmProviderSelect = document.getElementById("llmProvider");
const llmBaseUrlInput = document.getElementById("llmBaseUrl");

const THEME_STORAGE_KEY = "rvchatThemePreference";
const THEME_PREFERENCES = ["system", "light", "dark"];
let themePreference = "system";

function getSavedThemePreference() {
  try {
    const savedPreference = localStorage.getItem(THEME_STORAGE_KEY);
    return THEME_PREFERENCES.includes(savedPreference) ? savedPreference : "system";
  } catch (error) {
    console.error("Could not read the saved theme preference:", error);
    return "system";
  }
}

function applyThemePreference(preference) {
  const useDarkTheme = preference === "dark"
    || (preference === "system" && window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.dataset.theme = useDarkTheme ? "dark" : "light";
}

themePreference = getSavedThemePreference();
themePreferenceSelect.value = themePreference;
applyThemePreference(themePreference);
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => {
  if (themePreference === "system") {
    applyThemePreference(themePreference);
  }
});

themePreferenceSelect.addEventListener("change", () => {
  themePreference = themePreferenceSelect.value;
  applyThemePreference(themePreference);
  try {
    localStorage.setItem(THEME_STORAGE_KEY, themePreference);
    themeFeedback.textContent = "Theme saved in this browser.";
  } catch (error) {
    themeFeedback.textContent = "Theme changed, but could not be saved in this browser.";
    console.error("Could not save the theme preference:", error);
  }
});

function setStatus(message, state = "idle") {
  statusDiv.textContent = message;
  statusDiv.dataset.state = state;
}

function setSettingsFeedback(message, state = "") {
  settingsFeedback.textContent = message;
  settingsFeedback.className = state ? `settings-${state}` : "";
}

function updateTtsVoiceHelp() {
  const help = document.getElementById("ttsVoiceHelp");
  if (ttsEngineSelect.value === "coqui") {
    help.textContent = "Reference audio path relative to the code folder (default: reference_audio.wav).";
  } else if (ttsEngineSelect.value === "kokoro") {
    help.textContent = "Kokoro voice ID (default: af_heart).";
  } else {
    help.textContent = "Orpheus voice name (default: tara).";
  }
}

function updateProviderHelp() {
  const isGenericLocal = llmProviderSelect.value === "openai_compatible";
  llmBaseUrlInput.required = isGenericLocal;
  document.getElementById("llmBaseUrlHelp").textContent = isGenericLocal
    ? "Required. Enter the OpenAI-compatible API base URL reachable from this app, commonly ending in /v1. Works with llama.cpp server and similar tools."
    : "Use the address reachable from the app server. For Ollama or LM Studio, leave blank to use its default address.";
}

function updateSettingsFields(settings) {
  llmProviderSelect.value = settings.llm_provider;
  document.getElementById("llmModel").value = settings.llm_model;
  llmBaseUrlInput.value = settings.llm_base_url;
  ttsEngineSelect.value = settings.tts_engine;
  ttsEngineSelect.dataset.previousEngine = settings.tts_engine;
  document.getElementById("ttsModel").value = settings.tts_model;
  ttsVoiceInput.value = settings.tts_voice;
  ttsSpeedInput.value = settings.tts_speed;
  ttsSpeedInput.disabled = settings.tts_engine === "orpheus";
  document.getElementById("ttsSpeedValue").textContent = `${Number(settings.tts_speed).toFixed(2)}x`;
  document.getElementById("sttLanguage").value = settings.stt_language;
  document.getElementById("sttModel").value = settings.stt_model;
  speedSlider.value = settings.turn_speed;
  turnSpeedInput.value = settings.turn_speed;
  document.getElementById("turnSpeedValue").textContent = settings.turn_speed < 50 ? "Faster replies" : "Longer pauses";
  document.getElementById("systemPrompt").value = settings.system_prompt;
  document.getElementById("apiKeyStatus").textContent = settings.openai_api_key_configured
    ? "OpenAI API key is configured in the server environment. Keys are not stored in this settings file."
    : "OpenAI API key is not configured. Set OPENAI_API_KEY in the server environment if you choose OpenAI.";
  updateTtsVoiceHelp();
  updateProviderHelp();
}

async function openSettings() {
  settingsOverlay.hidden = false;
  document.getElementById("closeSettingsBtn").focus();
  settingsRestartNotice.hidden = true;
  setSettingsFeedback("Loading saved settings...");
  try {
    const response = await fetch("/api/settings");
    const data = await response.json();
    if (!response.ok) {
      const message = response.status === 403
        ? "Settings can only be changed from the server computer."
        : data.detail || "Could not load settings.";
      throw new Error(message);
    }
    updateSettingsFields(data.settings);
    settingsRestartNotice.hidden = !data.restart_required;
    setSettingsFeedback("");
  } catch (error) {
    setSettingsFeedback(error.message || "Could not load settings. Check the server and try again.", "error");
  }
}

function closeSettings() {
  settingsOverlay.hidden = true;
  settingsBtn.focus();
}

function updateControls() {
  const connected = !!(socket && socket.readyState === WebSocket.OPEN);
  startBtn.disabled = connected;
  stopBtn.disabled = !connected;
  speedSlider.disabled = !connected;
  copyBtn.disabled = chatHistory.length === 0;
}

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
let isStoppingSession = false;
let voiceSessionStarted = false;

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
    setStatus("Microphone access was blocked. Please allow access and try again.", "error");
    isStoppingSession = true;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.close();
    }
    console.error(err);
    updateControls();
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

settingsBtn.onclick = openSettings;
llmProviderSelect.addEventListener("change", updateProviderHelp);
document.getElementById("closeSettingsBtn").onclick = closeSettings;
document.getElementById("cancelSettingsBtn").onclick = closeSettings;
settingsOverlay.addEventListener("click", (event) => {
  if (event.target === settingsOverlay) {
    closeSettings();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !settingsOverlay.hidden) {
    closeSettings();
  }
});

ttsEngineSelect.addEventListener("change", (event) => {
  const defaults = {
    coqui: "reference_audio.wav",
    kokoro: "af_heart",
    orpheus: "tara"
  };
  const previousDefault = defaults[event.target.dataset.previousEngine];
  if (!ttsVoiceInput.value || ttsVoiceInput.value === previousDefault) {
    ttsVoiceInput.value = defaults[event.target.value];
  }
  event.target.dataset.previousEngine = event.target.value;
  ttsSpeedInput.disabled = event.target.value === "orpheus";
  updateTtsVoiceHelp();
});

settingsForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const saveButton = document.getElementById("saveSettingsBtn");
  const settings = {
    llm_provider: document.getElementById("llmProvider").value,
    llm_model: document.getElementById("llmModel").value.trim(),
    llm_base_url: document.getElementById("llmBaseUrl").value.trim(),
    tts_engine: ttsEngineSelect.value,
    tts_model: document.getElementById("ttsModel").value.trim(),
    tts_voice: ttsVoiceInput.value.trim(),
    tts_speed: Number(ttsSpeedInput.value),
    turn_speed: Number(turnSpeedInput.value),
    stt_language: document.getElementById("sttLanguage").value.trim(),
    stt_model: document.getElementById("sttModel").value.trim(),
    system_prompt: document.getElementById("systemPrompt").value
  };

  saveButton.disabled = true;
  setSettingsFeedback("Saving settings...");
  try {
    const response = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(settings)
    });
    const data = await response.json();
    if (!response.ok) {
      const detail = Array.isArray(data.detail)
        ? data.detail.map(error => error.msg).join(" ")
        : data.detail;
      throw new Error(detail || "Could not save settings.");
    }
    updateSettingsFields(data.settings);
    settingsRestartNotice.hidden = !data.restart_required;
    setSettingsFeedback(
      data.restart_required ? "Settings saved. Restart the app to apply them." : "Settings saved; they are already active.",
      data.restart_required ? "notice" : "success"
    );
  } catch (error) {
    setSettingsFeedback(error.message || "Could not save settings. Check the server and try again.", "error");
  } finally {
    saveButton.disabled = false;
  }
});

// UI Controls

clearBtn.onclick = () => {
  chatHistory = [];
  typingUser = typingAssistant = "";
  renderMessages();
  setStatus("Conversation reset.", "idle");
  updateControls();
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({ type: 'clear_history' }));
  }
};

speedSlider.addEventListener("input", (e) => {
  const speedValue = parseInt(e.target.value);
  turnSpeedInput.value = speedValue;
  document.getElementById("turnSpeedValue").textContent = speedValue < 50 ? "Faster replies" : "Longer pauses";
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: 'set_speed',
      speed: speedValue
    }));
  }
  console.log("Speed setting changed to:", speedValue);
});

turnSpeedInput.addEventListener("input", (e) => {
  const speedValue = parseInt(e.target.value);
  speedSlider.value = speedValue;
  document.getElementById("turnSpeedValue").textContent = speedValue < 50 ? "Faster replies" : "Longer pauses";
  if (socket && socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify({
      type: 'set_speed',
      speed: speedValue
    }));
  }
});

startBtn.onclick = async () => {
  if (socket && socket.readyState === WebSocket.OPEN) {
    setStatus("Already recording.", "recording");
    return;
  }
  setStatus("Initializing connection...", "idle");
  voiceSessionStarted = false;

  const wsProto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  socket = new WebSocket(`${wsProto}//${location.host}/ws`);

  const startVoiceSession = async () => {
    if (voiceSessionStarted) {
      return;
    }
    voiceSessionStarted = true;
    setStatus("Connected. Activating mic and TTS…", "recording");
    try {
      await startRawPcmCapture();
      await setupTTSPlayback();
      updateControls();
    } catch (err) {
      console.error("Failed to initialize voice session:", err);
      setStatus("Voice setup failed. Please try again.", "error");
      if (socket && socket.readyState === WebSocket.OPEN) {
        socket.close();
      }
    }
  };

  socket.onopen = () => {
    setStatus("Connected. Securing the session…", "idle");
  };

  socket.onmessage = (evt) => {
    if (typeof evt.data === "string") {
      try {
        const msg = JSON.parse(evt.data);
        if (msg.type === "auth_required") {
          const token = (
            sessionStorage.getItem("rvchatServerToken")
            || window.prompt("Enter the server access token:")
            || ""
          ).trim();
          if (!token) {
            setStatus("A server access token is required.", "error");
            socket.close();
            return;
          }
          sessionStorage.setItem("rvchatServerToken", token);
          socket.send(JSON.stringify({ type: "authenticate", token }));
          return;
        }
        if (msg.type === "authentication_failed") {
          sessionStorage.removeItem("rvchatServerToken");
          setStatus("Authentication failed. Check the server access token.", "error");
          return;
        }
        if (msg.type === "server_busy") {
          setStatus("The server is already handling a voice session. Try again later.", "warning");
          return;
        }
        if (msg.type === "ready") {
          void startVoiceSession();
          return;
        }
        handleJSONMessage(msg);
      } catch (e) {
        console.error("Error parsing message:", e);
      }
    }
  };

  socket.onclose = () => {
    if (isStoppingSession) {
      setStatus("Stopped.", "idle");
    } else if (statusDiv.dataset.state !== "error" && statusDiv.dataset.state !== "warning") {
      setStatus("Session ended. Start again when you're ready.", "idle");
    }
    isStoppingSession = false;
    flushRemainder();
    cleanupAudio();
    updateControls();
  };

  socket.onerror = (err) => {
    setStatus("Connection error. Please check your setup and try again.", "error");
    cleanupAudio();
    console.error(err);
    updateControls();
  };
};

stopBtn.onclick = () => {
  isStoppingSession = true;
  if (socket && socket.readyState === WebSocket.OPEN) {
    flushRemainder();
    socket.close();
  }
  cleanupAudio();
  setStatus("Stopped.", "idle");
  updateControls();
};

copyBtn.onclick = async () => {
  const text = chatHistory
    .map(msg => `${msg.role.charAt(0).toUpperCase() + msg.role.slice(1)}: ${msg.content}`)
    .join('\n');

  if (!text) {
    setStatus("Nothing to copy yet.", "warning");
    return;
  }

  try {
    if (navigator.clipboard && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
    } else {
      const temp = document.createElement('textarea');
      temp.value = text;
      document.body.appendChild(temp);
      temp.select();
      document.execCommand('copy');
      document.body.removeChild(temp);
    }
    setStatus("Conversation copied.", "idle");
    console.log("Conversation copied to clipboard");
  } catch (err) {
    setStatus("Copy failed. Please select text manually.", "warning");
    console.error("Copy failed:", err);
  }
};

// First render
renderMessages();
updateControls();
