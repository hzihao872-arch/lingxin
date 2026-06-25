const state = {
  joints: [],
  pose: [],
  defaultPose: [],
  connected: false,
  liveMode: true,
  teachActive: false,
  teachSupported: false,
  sending: false,
  pendingSend: false,
  sendTimer: null,
  teachPollTimer: null,
};

const LIVE_DEBOUNCE_MS = 40;
const MIN_SEND_INTERVAL_MS = 33;
const TEACH_POLL_MS = 100;

const jointGrid = document.getElementById("joint-grid");
const presetList = document.getElementById("preset-list");
const messageEl = document.getElementById("message");
const statusDot = document.getElementById("status-dot");
const statusTitle = document.getElementById("status-title");
const statusDetail = document.getElementById("status-detail");
const presetNameInput = document.getElementById("preset-name");
const speedInput = document.getElementById("speed-input");
const liveModeInput = document.getElementById("live-mode");
const teachNote = document.getElementById("teach-note");
const btnTeachStart = document.getElementById("btn-teach-start");
const btnTeachStop = document.getElementById("btn-teach-stop");

let lastSendTime = 0;

function showMessage(text, type = "info") {
  messageEl.hidden = false;
  messageEl.textContent = text;
  messageEl.className = `message ${type}`;
}

function clearMessage() {
  messageEl.hidden = true;
  messageEl.textContent = "";
}

async function api(path, options = {}) {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) {
    throw new Error(payload.error || `请求失败 (${response.status})`);
  }
  return payload;
}

function updatePoseDisplay(pose) {
  state.pose = [...pose];
  const rows = jointGrid.querySelectorAll(".joint-row");
  rows.forEach((row, index) => {
    const slider = row.querySelector('input[type="range"]');
    const value = row.querySelector(".joint-value");
    if (!slider || !value) return;
    const joint = state.joints[index];
    const clamped = clampJointValue(joint, state.pose[index]);
    state.pose[index] = clamped;
    slider.value = String(clamped);
    value.textContent = String(clamped);
  });
}

function setControlsDisabled(disabled) {
  jointGrid.querySelectorAll('input[type="range"]').forEach((slider) => {
    slider.disabled = disabled;
  });
  liveModeInput.disabled = disabled;
  document.getElementById("btn-apply-pose").disabled = disabled;
  document.getElementById("btn-open-palm").disabled = disabled;
}

function clampJointValue(joint, value) {
  const min = joint.min ?? 0;
  const max = joint.max ?? 255;
  return Math.max(min, Math.min(max, Number(value)));
}

function clampPose(pose) {
  return state.joints.map((joint, index) => clampJointValue(joint, pose[index]));
}

function renderJoints() {
  jointGrid.innerHTML = "";
  state.joints.forEach((joint, index) => {
    const row = document.createElement("div");
    row.className = "joint-row";

    const label = document.createElement("div");
    label.className = "joint-label";
    label.innerHTML = `<strong>${joint.label}</strong><span>${joint.name} (${joint.min}..${joint.max})${joint.hint ? ` · ${joint.hint}` : ""}</span>`;

    const slider = document.createElement("input");
    slider.type = "range";
    slider.min = String(joint.min ?? 0);
    slider.max = String(joint.max ?? 255);
    slider.value = String(state.pose[index]);
    slider.addEventListener("input", () => {
      if (state.teachActive) return;
      state.pose[index] = clampJointValue(joint, slider.value);
      slider.value = String(state.pose[index]);
      value.textContent = String(state.pose[index]);
      scheduleLiveSend();
    });
    slider.addEventListener("change", () => {
      flushLiveSend();
    });

    const value = document.createElement("div");
    value.className = "joint-value";
    value.textContent = String(state.pose[index]);

    row.append(label, slider, value);
    jointGrid.appendChild(row);
  });
}

function setPose(pose, options = {}) {
  const clamped = clampPose(pose);
  if (state.teachActive && options.send !== false) {
    updatePoseDisplay(clamped);
    return;
  }
  state.pose = clamped;
  renderJoints();
  if (options.send !== false && state.liveMode && state.connected) {
    flushLiveSend();
  }
}

function formatPose(pose) {
  return pose.join(", ");
}

function scheduleLiveSend() {
  if (state.teachActive || !state.liveMode || !state.connected) {
    return;
  }
  clearTimeout(state.sendTimer);
  state.sendTimer = setTimeout(flushLiveSend, LIVE_DEBOUNCE_MS);
}

async function flushLiveSend() {
  if (state.teachActive || !state.liveMode || !state.connected) {
    return;
  }

  clearTimeout(state.sendTimer);

  const now = Date.now();
  const wait = MIN_SEND_INTERVAL_MS - (now - lastSendTime);
  if (wait > 0) {
    state.sendTimer = setTimeout(flushLiveSend, wait);
    return;
  }

  if (state.sending) {
    state.pendingSend = true;
    return;
  }

  state.sending = true;
  state.pendingSend = false;
  try {
    await api("/api/pose", {
      method: "POST",
      body: JSON.stringify({ pose: state.pose, live: true }),
    });
    lastSendTime = Date.now();
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    state.sending = false;
    if (state.pendingSend) {
      scheduleLiveSend();
    }
  }
}

async function refreshStatus() {
  try {
    const payload = await api("/api/status");
    state.connected = payload.connected;
    statusDot.className = `status-dot ${payload.connected ? "online" : "offline"}`;
    statusTitle.textContent = payload.connected ? "机械手已连接" : "机械手未连接";
    if (payload.connected) {
      const sdkInfo = payload.sdk_path ? ` | SDK: ${payload.sdk_path}` : "";
      statusDetail.textContent = `后端: ${payload.backend} | ${payload.hand_type}${sdkInfo}`;
    } else {
      statusDetail.textContent = payload.hint || payload.error || "请检查 dashboard 或 SDK 配置";
    }
    if (payload.teach) {
      state.teachSupported = payload.teach.supported;
      updateTeachUi(payload.teach.active, payload.teach.note);
    }
  } catch (error) {
    state.connected = false;
    statusDot.className = "status-dot offline";
    statusTitle.textContent = "状态检查失败";
    statusDetail.textContent = error.message;
  }
}

async function pollTeachPose() {
  if (!state.teachActive) return;
  try {
    const payload = await api("/api/teach/pose");
    updatePoseDisplay(payload.pose);
  } catch (error) {
    showMessage(error.message, "error");
    await stopTeachMode(false);
  }
}

function updateTeachUi(active, note) {
  state.teachActive = active;
  btnTeachStart.disabled = active || !state.teachSupported || !state.connected;
  btnTeachStop.disabled = !active;
  setControlsDisabled(active);
  teachNote.textContent = note || teachNote.textContent;
  teachNote.classList.toggle("active", active);
}

async function startTeachMode() {
  clearMessage();
  try {
    const payload = await api("/api/teach/start", {
      method: "POST",
      body: JSON.stringify({}),
    });
    state.liveMode = false;
    liveModeInput.checked = false;
    updateTeachUi(true, payload.note || "示教中：请用手拨动灵巧手，滑块会实时显示关节值。");
    await pollTeachPose();
    state.teachPollTimer = setInterval(pollTeachPose, TEACH_POLL_MS);
    showMessage("已进入示教模式，可用手拨动灵巧手", "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function stopTeachMode(showSuccess = true) {
  clearInterval(state.teachPollTimer);
  state.teachPollTimer = null;
  try {
    await api("/api/teach/stop", {
      method: "POST",
      body: JSON.stringify({}),
    });
    updateTeachUi(false, "将扭矩置零后，用手拨动灵巧手，滑块会同步显示十个关节自由度。");
    setControlsDisabled(false);
    if (showSuccess) {
      showMessage("已恢复使能，可继续实时调节", "success");
    }
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function sendPose() {
  if (state.sending) return;
  state.sending = true;
  clearMessage();
  try {
    await api("/api/pose", {
      method: "POST",
      body: JSON.stringify({ pose: state.pose, live: false }),
    });
    lastSendTime = Date.now();
    showMessage("姿态已发送到机械手", "success");
  } catch (error) {
    showMessage(error.message, "error");
  } finally {
    state.sending = false;
  }
}

async function sendSpeed() {
  clearMessage();
  try {
    const speed = Number(speedInput.value);
    await api("/api/speed", {
      method: "POST",
      body: JSON.stringify({ speed }),
    });
    showMessage(`速度已设置为 ${speed}`, "success");
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function savePreset() {
  const name = presetNameInput.value.trim();
  if (!name) {
    showMessage("请先输入姿态名称", "error");
    return;
  }
  clearMessage();
  try {
    await api("/api/presets", {
      method: "POST",
      body: JSON.stringify({ name, pose: state.pose }),
    });
    presetNameInput.value = "";
    showMessage(`已保存姿态「${name}」`, "success");
    await loadPresets();
  } catch (error) {
    showMessage(error.message, "error");
  }
}

async function loadPresets() {
  const payload = await api("/api/presets");
  const presets = payload.presets || [];
  if (presets.length === 0) {
    presetList.innerHTML = '<p class="empty">暂无保存的姿态</p>';
    return;
  }

  presetList.innerHTML = "";
  presets
    .slice()
    .reverse()
    .forEach((preset) => {
      const item = document.createElement("div");
      item.className = "preset-item";

      const meta = document.createElement("div");
      meta.className = "preset-meta";
      meta.innerHTML = `
        <strong>${preset.name}</strong>
        <code>${formatPose(preset.pose)}</code>
      `;

      const actions = document.createElement("div");
      actions.className = "preset-actions";

      const applyBtn = document.createElement("button");
      applyBtn.type = "button";
      applyBtn.className = "btn primary";
      applyBtn.textContent = "应用";
      applyBtn.addEventListener("click", async () => {
        clearMessage();
        try {
          const result = await api(`/api/presets/${preset.id}/apply`, {
            method: "POST",
            body: JSON.stringify({}),
          });
          setPose(result.preset.pose);
          showMessage(`已应用姿态「${preset.name}」`, "success");
        } catch (error) {
          showMessage(error.message, "error");
        }
      });

      const loadBtn = document.createElement("button");
      loadBtn.type = "button";
      loadBtn.className = "btn secondary";
      loadBtn.textContent = "载入滑块";
      loadBtn.addEventListener("click", () => {
        setPose(preset.pose, { send: false });
        showMessage(`已载入「${preset.name}」到滑块（未发送）`, "info");
      });

      const deleteBtn = document.createElement("button");
      deleteBtn.type = "button";
      deleteBtn.className = "btn danger";
      deleteBtn.textContent = "删除";
      deleteBtn.addEventListener("click", async () => {
        if (!window.confirm(`确定删除「${preset.name}」吗？`)) return;
        clearMessage();
        try {
          await api(`/api/presets/${preset.id}`, { method: "DELETE" });
          showMessage(`已删除「${preset.name}」`, "success");
          await loadPresets();
        } catch (error) {
          showMessage(error.message, "error");
        }
      });

      actions.append(applyBtn, loadBtn, deleteBtn);
      item.append(meta, actions);
      presetList.appendChild(item);
    });
}

async function bootstrap() {
  const payload = await api("/api/joints");
  state.joints = payload.joints;
  state.defaultPose = clampPose(payload.default_pose);
  state.pose = [...state.defaultPose];
  renderJoints();

  liveModeInput.checked = state.liveMode;
  liveModeInput.addEventListener("change", () => {
    state.liveMode = liveModeInput.checked;
    if (state.liveMode && state.connected) {
      flushLiveSend();
    }
  });

  document.getElementById("btn-apply-pose").addEventListener("click", sendPose);
  document.getElementById("btn-apply-speed").addEventListener("click", sendSpeed);
  document.getElementById("btn-open-palm").addEventListener("click", () => {
    setPose(state.defaultPose);
    showMessage("已载入张开手掌姿态", "info");
  });
  document.getElementById("btn-save-preset").addEventListener("click", savePreset);
  document.getElementById("btn-refresh-presets").addEventListener("click", loadPresets);
  btnTeachStart.addEventListener("click", startTeachMode);
  btnTeachStop.addEventListener("click", () => stopTeachMode(true));

  await Promise.all([refreshStatus(), loadPresets()]);
  const teachInfo = await api("/api/teach");
  state.teachSupported = teachInfo.supported;
  updateTeachUi(teachInfo.active, teachInfo.note);
  setInterval(refreshStatus, 5000);
}

bootstrap().catch((error) => {
  showMessage(`初始化失败: ${error.message}`, "error");
});
