const canvas = document.getElementById("task7-canvas");
const playToggleButton = document.getElementById("task7-play-toggle");
const stepButton = document.getElementById("task7-step-button");
const frameSlider = document.getElementById("task7-frame-slider");
const frameReadoutNode = document.getElementById("task7-frame-readout");
const massNode = document.getElementById("task7-mass");
const disorderNode = document.getElementById("task7-disorder");
const bottNode = document.getElementById("task7-bott");
const windingNode = document.getElementById("task7-winding");
const consistencyNode = document.getElementById("task7-consistency");
const exportJsonButton = document.getElementById("task7-export-json");
const exportPngButton = document.getElementById("task7-export-png");
const exportSvgButton = document.getElementById("task7-export-svg");

if (
  !canvas ||
  !playToggleButton ||
  !stepButton ||
  !frameSlider ||
  !frameReadoutNode ||
  !massNode ||
  !disorderNode ||
  !bottNode ||
  !windingNode ||
  !consistencyNode ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton
) {
  throw new Error("Eigenvalue flow UI is missing required elements.");
}

const context = canvas.getContext("2d");
let latestPayload = null;
let currentFrameIndex = 0;
let isPlaying = true;
let animationFrameId = 0;
let lastTickMs = 0;
const frameIntervalMs = 180;

function formatFloat(value, digits = 3) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "--";
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(rect.width * ratio);
  canvas.height = Math.round(rect.height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  if (latestPayload) {
    drawFrame();
  }
}

function setPlaying(nextPlaying) {
  isPlaying = Boolean(nextPlaying);
  playToggleButton.textContent = isPlaying ? "Pause" : "Play";
  playToggleButton.setAttribute("aria-pressed", isPlaying ? "true" : "false");
}

function setFrame(index) {
  if (!latestPayload) {
    return;
  }
  const frames = latestPayload.metadata.flow.frames;
  currentFrameIndex = Math.min(frames.length - 1, Math.max(0, index));
  frameSlider.value = `${currentFrameIndex}`;
  drawFrame();
}

function updateReadout(frame, totalFrames) {
  frameReadoutNode.textContent = `${frame.frame_index + 1} / ${totalFrames}`;
  massNode.textContent = formatFloat(frame.mass, 3);
  disorderNode.textContent = formatFloat(frame.disorder, 3);
  bottNode.textContent = `${frame.bott_index}`;
  windingNode.textContent = `${frame.winding_number}`;
}

function drawCircleStage(stage, frame) {
  const centerX = stage.x + stage.width * 0.38;
  const centerY = stage.y + stage.height * 0.53;
  const radius = Math.min(stage.width * 0.34, stage.height * 0.36);

  context.fillStyle = "rgba(18, 22, 37, 0.88)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(stage.x, stage.y, stage.width, stage.height, 28);
  context.fill();
  context.stroke();

  context.fillStyle = "#f3fbff";
  context.font = "700 26px 'Segoe UI'";
  context.fillText("Unit-Circle Eigenvalue Flow", stage.x + 26, stage.y + 36);
  context.fillStyle = "#bfd0e4";
  context.font = "600 13px 'Segoe UI'";
  context.fillText("Each point is an eigenvalue of W moving around the complex unit circle.", stage.x + 26, stage.y + 58);

  context.strokeStyle = "rgba(255,255,255,0.12)";
  context.lineWidth = 1;
  context.beginPath();
  context.arc(centerX, centerY, radius, 0, Math.PI * 2);
  context.stroke();

  context.beginPath();
  context.moveTo(centerX - radius - 20, centerY);
  context.lineTo(centerX + radius + 20, centerY);
  context.moveTo(centerX, centerY - radius - 20);
  context.lineTo(centerX, centerY + radius + 20);
  context.stroke();

  context.fillStyle = "#d8e4f2";
  context.font = "600 12px 'Segoe UI'";
  context.fillText("Re", centerX + radius + 26, centerY + 4);
  context.fillText("Im", centerX - 8, centerY - radius - 26);
  context.fillText("1", centerX + radius - 4, centerY + 18);
  context.fillText("-1", centerX - radius - 16, centerY + 18);
  context.fillText("i", centerX + 8, centerY - radius + 6);
  context.fillText("-i", centerX + 8, centerY + radius + 4);

  frame.eigenvalues.forEach((pair, index) => {
    const re = pair[0];
    const im = pair[1];
    const x = centerX + re * radius;
    const y = centerY - im * radius;
    const hue = 190 + (220 * (index / Math.max(frame.eigenvalues.length - 1, 1)));
    context.fillStyle = `hsl(${hue}, 88%, 64%)`;
    context.beginPath();
    context.arc(x, y, 5.5, 0, Math.PI * 2);
    context.fill();
    context.strokeStyle = "rgba(255,255,255,0.22)";
    context.stroke();
  });

  const panelX = stage.x + stage.width * 0.72;
  const panelY = stage.y + 88;
  const panelWidth = stage.width * 0.22;
  const panelHeight = stage.height - 130;
  context.fillStyle = "rgba(11, 17, 30, 0.76)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.beginPath();
  context.roundRect(panelX, panelY, panelWidth, panelHeight, 22);
  context.fill();
  context.stroke();

  context.fillStyle = "#22d3ee";
  context.font = "700 13px 'Segoe UI'";
  context.fillText("PHASE TRACE", panelX + 18, panelY + 24);
  context.fillStyle = "#eff7ff";
  context.font = "600 12px 'Segoe UI'";
  const phases = frame.phases;
  const rowStartY = panelY + 50;
  const rowStep = 19;
  const footerReserve = 24;
  const maxRows = Math.max(1, Math.min(phases.length, Math.floor((panelHeight - (rowStartY - panelY) - footerReserve) / rowStep)));
  for (let index = 0; index < maxRows; index += 1) {
    const y = rowStartY + index * rowStep;
    context.fillText(`φ${index + 1}`, panelX + 18, y);
    context.fillText(formatFloat(phases[index], 3), panelX + 78, y);
  }
  if (phases.length > maxRows) {
    context.fillStyle = "#9fb3c8";
    context.font = "600 11px 'Segoe UI'";
    context.fillText(`+${phases.length - maxRows} more`, panelX + 18, panelY + panelHeight - 12);
  }
}

function drawFrame() {
  if (!latestPayload) {
    return;
  }
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#0a1320";
  context.fillRect(0, 0, width, height);

  const frames = latestPayload.metadata.flow.frames;
  const frame = frames[currentFrameIndex];
  updateReadout(frame, frames.length);

  drawCircleStage({ x: 26, y: 26, width: width - 52, height: height - 52 }, frame);
}

function tick(timestampMs) {
  animationFrameId = window.requestAnimationFrame(tick);
  if (!latestPayload) {
    return;
  }
  if (isPlaying && timestampMs - lastTickMs >= frameIntervalMs) {
    lastTickMs = timestampMs;
    const frames = latestPayload.metadata.flow.frames;
    currentFrameIndex = (currentFrameIndex + 1) % frames.length;
    frameSlider.value = `${currentFrameIndex}`;
    drawFrame();
  }
}

function buildSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
  <rect width="100%" height="100%" fill="#0a1320" />
  <text x="40" y="52" fill="#eff7ff" font-size="30" font-weight="700">Eigenvalue Flow</text>
  <text x="40" y="86" fill="#c4d2e1" font-size="15">Use PNG export for the full animated frame view.</text>
</svg>`;
}

async function loadData() {
  const response = await fetch("../../data/exports/task7.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load task7.json: ${response.status}`);
  }
  return response.json();
}

loadData()
  .then((payload) => {
    latestPayload = payload;
    const frames = payload.metadata.flow.frames;
    frameSlider.max = `${Math.max(frames.length - 1, 0)}`;
    frameSlider.value = "0";
    consistencyNode.textContent = payload.metadata.flow.bott_matches_winding_all_frames
      ? "Winding number matches the Bott index on every exported frame."
      : "At least one frame breaks the Bott/winding match.";
    setFrame(0);
  })
  .catch((error) => {
    consistencyNode.textContent = error.message;
    context.fillStyle = "#f2f7ff";
    context.font = "600 24px 'Segoe UI'";
    context.fillText(error.message, 32, 48);
  });

playToggleButton.addEventListener("click", () => {
  setPlaying(!isPlaying);
});

stepButton.addEventListener("click", () => {
  if (!latestPayload) {
    return;
  }
  setPlaying(false);
  setFrame(currentFrameIndex + 1);
});

frameSlider.addEventListener("input", (event) => {
  setPlaying(false);
  setFrame(Number.parseInt(event.target.value || "0", 10) || 0);
});

exportJsonButton.addEventListener("click", () => {
  if (!latestPayload) {
    return;
  }
  const blob = new Blob([JSON.stringify(latestPayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "eigenvalue_flow.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

exportPngButton.addEventListener("click", () => {
  const anchor = document.createElement("a");
  anchor.href = canvas.toDataURL("image/png");
  anchor.download = "eigenvalue_flow.png";
  anchor.click();
});

exportSvgButton.addEventListener("click", () => {
  const blob = new Blob([buildSvg()], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "eigenvalue_flow.svg";
  anchor.click();
  URL.revokeObjectURL(url);
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
animationFrameId = window.requestAnimationFrame(tick);
