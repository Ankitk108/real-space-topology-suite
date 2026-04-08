const canvas = document.getElementById("task9-canvas");
const interpolationSlider = document.getElementById("task9-interpolation-slider");
const interpolationReadoutNode = document.getElementById("task9-interpolation-readout");
const haldaneBottNode = document.getElementById("task9-haldane-bott");
const chernBottNode = document.getElementById("task9-chern-bott");
const deformationBottNode = document.getElementById("task9-deformation-bott");
const invariantMatchNode = document.getElementById("task9-invariant-match");
const hoverPanelNode = document.getElementById("task9-hover-panel");
const hoverSiteNode = document.getElementById("task9-hover-site");
const hoverDensityNode = document.getElementById("task9-hover-density");
const exportJsonButton = document.getElementById("task9-export-json");
const exportPngButton = document.getElementById("task9-export-png");
const exportSvgButton = document.getElementById("task9-export-svg");

if (
  !canvas ||
  !interpolationSlider ||
  !interpolationReadoutNode ||
  !haldaneBottNode ||
  !chernBottNode ||
  !deformationBottNode ||
  !invariantMatchNode ||
  !hoverPanelNode ||
  !hoverSiteNode ||
  !hoverDensityNode ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton
) {
  throw new Error("Comparative topology UI is missing required elements.");
}

const context = canvas.getContext("2d");
const VIRIDIS_STOPS = [
  { t: 0.0, color: [68, 1, 84] },
  { t: 0.14, color: [72, 39, 119] },
  { t: 0.28, color: [62, 73, 137] },
  { t: 0.43, color: [49, 104, 142] },
  { t: 0.57, color: [38, 130, 142] },
  { t: 0.71, color: [31, 157, 138] },
  { t: 0.86, color: [108, 206, 90] },
  { t: 1.0, color: [253, 231, 37] },
];

let latestPayload = null;
let latestLayout = null;
let currentFrameIndex = 0;

function formatFloat(value, digits = 3) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "--";
}

function interpolateViridis(normalized) {
  const clamped = Math.max(0, Math.min(1, normalized));
  for (let index = 0; index < VIRIDIS_STOPS.length - 1; index += 1) {
    const left = VIRIDIS_STOPS[index];
    const right = VIRIDIS_STOPS[index + 1];
    if (clamped >= left.t && clamped <= right.t) {
      const alpha = (clamped - left.t) / Math.max(right.t - left.t, 1.0e-12);
      const color = left.color.map((channel, channelIndex) =>
        Math.round(channel + alpha * (right.color[channelIndex] - channel))
      );
      return `rgb(${color[0]}, ${color[1]}, ${color[2]})`;
    }
  }
  const finalColor = VIRIDIS_STOPS[VIRIDIS_STOPS.length - 1].color;
  return `rgb(${finalColor[0]}, ${finalColor[1]}, ${finalColor[2]})`;
}

function resizeCanvas() {
  const rect = canvas.getBoundingClientRect();
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  canvas.width = Math.round(rect.width * ratio);
  canvas.height = Math.round(rect.height * ratio);
  context.setTransform(ratio, 0, 0, ratio, 0, 0);
  if (latestPayload) {
    draw(latestPayload);
  }
}

function drawWrappedText(text, x, y, maxWidth, lineHeight, maxLines, color) {
  const words = text.split(/\s+/);
  const lines = [];
  let currentLine = "";

  for (const word of words) {
    const trial = currentLine ? `${currentLine} ${word}` : word;
    if (context.measureText(trial).width <= maxWidth || currentLine === "") {
      currentLine = trial;
    } else {
      lines.push(currentLine);
      currentLine = word;
    }
  }
  if (currentLine) {
    lines.push(currentLine);
  }

  const visibleLines = lines.slice(0, maxLines);
  context.fillStyle = color;
  visibleLines.forEach((line, index) => {
    const suffix = index === maxLines - 1 && lines.length > maxLines ? "..." : "";
    context.fillText(`${line}${suffix}`, x, y + index * lineHeight);
  });
}

function drawViridisLegend(x, y, width, height) {
  for (let step = 0; step < width; step += 1) {
    const normalized = step / Math.max(width - 1, 1);
    context.fillStyle = interpolateViridis(normalized);
    context.fillRect(x + step, y, 1, height);
  }
  context.strokeStyle = "rgba(255,255,255,0.14)";
  context.lineWidth = 1;
  context.strokeRect(x, y, width, height);

  context.fillStyle = "#9fb3c8";
  context.font = "600 10px 'Segoe UI'";
  context.fillText("low density", x, y + height + 14);
  context.textAlign = "right";
  context.fillText("high density", x + width, y + height + 14);
  context.textAlign = "left";
}

function drawGridPanel(frame, title, subtitle, densityGrid, accentColor) {
  const rows = densityGrid.length;
  const cols = densityGrid[0].length;
  const innerPadding = 20;
  const headerHeight = 58;
  const footerHeight = 82;
  const maxValue = Math.max(...densityGrid.flat(), 1.0e-12);
  const cellSize = Math.max(
    16,
    Math.floor(
      Math.min(
        (frame.width - (2 * innerPadding)) / cols,
        (frame.height - headerHeight - footerHeight - (2 * innerPadding)) / rows
      )
    )
  );
  const gridWidth = cols * cellSize;
  const gridHeight = rows * cellSize;
  const gridX = frame.x + Math.floor((frame.width - gridWidth) / 2);
  const gridY = frame.y + headerHeight;
  const footerY = gridY + gridHeight + 10;

  context.fillStyle = "rgba(18, 22, 37, 0.88)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(frame.x, frame.y, frame.width, frame.height, 24);
  context.fill();
  context.stroke();

  context.fillStyle = "#f3fbff";
  context.font = "700 18px 'Segoe UI'";
  context.textAlign = "center";
  context.fillText(title, frame.x + frame.width * 0.5, frame.y + 30);
  context.textAlign = "right";
  context.fillStyle = "#f7f9ff";
  context.font = "700 10px 'Segoe UI'";
  context.fillText(`Peak ${formatFloat(maxValue, 4)}`, frame.x + frame.width - 80, frame.y + 45);
  context.textAlign = "left";

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const x = gridX + col * cellSize;
      const y = gridY + row * cellSize;
      const normalized = densityGrid[row][col] / maxValue;
      context.fillStyle = interpolateViridis(normalized);
      context.fillRect(x, y, cellSize - 1, cellSize - 1);
    }
  }

  context.strokeStyle = "rgba(255,255,255,0.08)";
  for (let row = 0; row <= rows; row += 1) {
    const y = gridY + row * cellSize;
    context.beginPath();
    context.moveTo(gridX, y);
    context.lineTo(gridX + gridWidth, y);
    context.stroke();
  }
  for (let col = 0; col <= cols; col += 1) {
    const x = gridX + col * cellSize;
    context.beginPath();
    context.moveTo(x, gridY);
    context.lineTo(x, gridY + gridHeight);
    context.stroke();
  }

  drawViridisLegend(gridX, footerY, gridWidth, 8);
  context.font = "600 10px 'Segoe UI'";
  drawWrappedText(subtitle, gridX, footerY + 48, gridWidth, 14, 3, accentColor);

  return { gridX, gridY, gridWidth, gridHeight, cellSize, rows, cols };
}

function drawBottRibbon(frame, bottTrace, lambdaValue) {
  context.fillStyle = "rgba(18, 22, 37, 0.88)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(frame.x, frame.y, frame.width, frame.height, 24);
  context.fill();
  context.stroke();

  const centerY = frame.y + frame.height * 0.48;
  context.fillStyle = "#f3fbff";
  context.font = "700 26px 'Segoe UI'";
  context.fillText(`Bott = ${bottTrace[0] ?? 0}`, frame.x + 22, centerY - 6);

  context.fillStyle = "#bfd0e4";
  context.font = "600 14px 'Segoe UI'";
  context.fillText("Haldane endpoint and disordered Chern endpoint remain in the same sector.", frame.x + 22, centerY + 24);

  context.fillStyle = "#22d3ee";
  context.font = "700 13px 'Segoe UI'";
  context.fillText("Left panel", frame.x + 22, frame.y + frame.height - 24);

  context.fillStyle = "#ff9a42";
  context.fillText("Right panel", frame.x + frame.width - 92, frame.y + frame.height - 24);
}

function draw(payload) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#0a1320";
  context.fillRect(0, 0, width, height);

  const margin = 26;
  const gap = 20;
  const topHeight = height - (2 * margin);
  const panelWidth = Math.floor((width - (2 * margin) - (2 * gap)) / 3);
  const panelY = margin;
  const haldaneFrame = { x: margin, y: panelY, width: panelWidth, height: topHeight };
  const middleFrame = { x: margin + panelWidth + gap, y: panelY, width: panelWidth, height: topHeight };
  const chernFrame = { x: margin + 2 * (panelWidth + gap), y: panelY, width: panelWidth, height: topHeight };

  const haldane = payload.metadata.comparison.haldane;
  const chern = payload.metadata.comparison.chern;
  const deformationFrame = payload.metadata.comparison.deformation_frames[currentFrameIndex];

  const haldaneLayout = drawGridPanel(
    haldaneFrame,
    "Haldane Model",
    "Honeycomb edge density in the topological phase",
    haldane.density_grid,
    "#22d3ee",
  );
  const middleLayout = drawGridPanel(
    middleFrame,
    "Deformation",
    `Interpolated signature at λ = ${formatFloat(deformationFrame.lambda, 3)}`,
    deformationFrame.density_grid,
    "#b9c2ff",
  );
  const chernLayout = drawGridPanel(
    chernFrame,
    "Disordered Chern",
    "Square-lattice real-space density with disorder",
    chern.density_grid,
    "#ff9a42",
  );

  latestLayout = {
    haldane: haldaneLayout,
    deformation: middleLayout,
    chern: chernLayout,
  };
}

function hitTest(event) {
  if (!latestLayout) {
    return null;
  }
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;
  for (const [panelName, layout] of Object.entries(latestLayout)) {
    if (
      x >= layout.gridX &&
      x <= layout.gridX + layout.gridWidth &&
      y >= layout.gridY &&
      y <= layout.gridY + layout.gridHeight
    ) {
      const col = Math.min(layout.cols - 1, Math.max(0, Math.floor((x - layout.gridX) / layout.cellSize)));
      const row = Math.min(layout.rows - 1, Math.max(0, Math.floor((y - layout.gridY) / layout.cellSize)));
      return { panelName, row, col };
    }
  }
  return null;
}

function clearHover() {
  hoverPanelNode.textContent = "Hover a map";
  hoverSiteNode.textContent = "--";
  hoverDensityNode.textContent = "--";
}

function buildSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1400" height="900" viewBox="0 0 1400 900">
  <rect width="100%" height="100%" fill="#0a1320" />
  <text x="40" y="52" fill="#eff7ff" font-size="30" font-weight="700">Comparative Topological Analysis</text>
  <text x="40" y="86" fill="#c4d2e1" font-size="15">Use PNG export for the fully rendered comparison canvas.</text>
</svg>`;
}

async function loadData() {
  const response = await fetch("../../data/exports/task9.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load task9.json: ${response.status}`);
  }
  return response.json();
}

loadData()
  .then((payload) => {
    latestPayload = payload;
    const comparison = payload.metadata.comparison;
    haldaneBottNode.textContent = `${comparison.haldane.bott_index}`;
    chernBottNode.textContent = `${comparison.chern.bott_index}`;
    deformationBottNode.textContent = `${comparison.bott_trace[0] ?? 0}`;
    invariantMatchNode.textContent = comparison.invariant_match ? "Stable" : "Mismatch";
    interpolationSlider.max = `${Math.max(comparison.deformation_frames.length - 1, 0)}`;
    interpolationSlider.value = "0";
    interpolationReadoutNode.textContent = formatFloat(comparison.deformation_frames[0]?.lambda ?? 0, 3);
    draw(payload);
  })
  .catch((error) => {
    context.fillStyle = "#f2f7ff";
    context.font = "600 24px 'Segoe UI'";
    context.fillText(error.message, 32, 48);
  });

interpolationSlider.addEventListener("input", (event) => {
  if (!latestPayload) {
    return;
  }
  currentFrameIndex = Number.parseInt(event.target.value || "0", 10) || 0;
  const frame = latestPayload.metadata.comparison.deformation_frames[currentFrameIndex];
  interpolationReadoutNode.textContent = formatFloat(frame.lambda, 3);
  deformationBottNode.textContent = `${frame.bott_index}`;
  draw(latestPayload);
});

canvas.addEventListener("mousemove", (event) => {
  if (!latestPayload) {
    return;
  }
  const hit = hitTest(event);
  if (!hit) {
    clearHover();
    return;
  }
  const comparison = latestPayload.metadata.comparison;
  const densityGrid = hit.panelName === "deformation"
    ? comparison.deformation_frames[currentFrameIndex].density_grid
    : comparison[hit.panelName].density_grid;
  hoverPanelNode.textContent =
    hit.panelName === "haldane" ? "Haldane model" : hit.panelName === "chern" ? "Disordered Chern" : "Deformation";
  hoverSiteNode.textContent = `(${hit.col}, ${hit.row})`;
  hoverDensityNode.textContent = formatFloat(densityGrid[hit.row][hit.col], 6);
});

canvas.addEventListener("mouseleave", clearHover);

exportJsonButton.addEventListener("click", () => {
  if (!latestPayload) {
    return;
  }
  const blob = new Blob([JSON.stringify(latestPayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "comparative_topological_analysis.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

exportPngButton.addEventListener("click", () => {
  const anchor = document.createElement("a");
  anchor.href = canvas.toDataURL("image/png");
  anchor.download = "comparative_topological_analysis.png";
  anchor.click();
});

exportSvgButton.addEventListener("click", () => {
  const blob = new Blob([buildSvg()], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "comparative_topological_analysis.svg";
  anchor.click();
  URL.revokeObjectURL(url);
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
