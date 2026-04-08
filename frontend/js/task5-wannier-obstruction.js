const canvas = document.getElementById("task5-canvas");
const trivialBottNode = document.getElementById("task5-trivial-bott");
const topologicalBottNode = document.getElementById("task5-topological-bott");
const centerRatioNode = document.getElementById("task5-center-ratio");
const hoverPanelNode = document.getElementById("task5-hover-panel");
const hoverSiteNode = document.getElementById("task5-hover-site");
const hoverDensityNode = document.getElementById("task5-hover-density");
const exportJsonButton = document.getElementById("task5-export-json");
const exportPngButton = document.getElementById("task5-export-png");
const exportSvgButton = document.getElementById("task5-export-svg");
const viewLatticeButton = document.getElementById("task5-view-lattice");
const viewRadialButton = document.getElementById("task5-view-radial");

if (
  !canvas ||
  !trivialBottNode ||
  !topologicalBottNode ||
  !centerRatioNode ||
  !hoverPanelNode ||
  !hoverSiteNode ||
  !hoverDensityNode ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton ||
  !viewLatticeButton ||
  !viewRadialButton
) {
  throw new Error("Wannier obstruction UI is missing required elements.");
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
let currentView = "lattice";

function formatFloat(value, digits = 4) {
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

function setView(viewName) {
  currentView = viewName === "radial" ? "radial" : "lattice";
  viewLatticeButton.classList.toggle("is-active", currentView === "lattice");
  viewRadialButton.classList.toggle("is-active", currentView === "radial");
  viewLatticeButton.setAttribute("aria-pressed", currentView === "lattice" ? "true" : "false");
  viewRadialButton.setAttribute("aria-pressed", currentView === "radial" ? "true" : "false");
  if (currentView !== "lattice") {
    clearHover();
  }
  if (latestPayload) {
    draw(latestPayload);
  }
}

function findPeak(densityGrid) {
  let peakRow = 0;
  let peakCol = 0;
  let peakValue = -Infinity;
  for (let row = 0; row < densityGrid.length; row += 1) {
    for (let col = 0; col < densityGrid[0].length; col += 1) {
      if (densityGrid[row][col] > peakValue) {
        peakValue = densityGrid[row][col];
        peakRow = row;
        peakCol = col;
      }
    }
  }
  return { row: peakRow, col: peakCol, value: peakValue };
}

function drawHeatmapPanel(frame, title, annotation, densityGrid, accentColor) {
  const rows = densityGrid.length;
  const cols = densityGrid[0].length;
  const innerPadding = 24;
  const headerHeight = 82;
  const colorbarWidth = 18;
  const colorbarGap = 14;
  const maxValue = Math.max(...densityGrid.flat(), 1.0e-12);
  const cellSize = Math.max(
    12,
    Math.floor(
      Math.min(
        (frame.width - (2 * innerPadding) - colorbarGap - colorbarWidth) / cols,
        (frame.height - headerHeight - (2 * innerPadding)) / rows
      )
    )
  );
  const gridWidth = cols * cellSize;
  const gridHeight = rows * cellSize;
  const gridX = frame.x + innerPadding;
  const gridY = frame.y + headerHeight;
  const colorbarX = gridX + gridWidth + colorbarGap;
  const colorbarY = gridY;
  const peak = findPeak(densityGrid);
  const centerCol = Math.floor(cols / 2);
  const centerRow = Math.floor(rows / 2);

  context.fillStyle = "rgba(18, 22, 37, 0.86)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(frame.x, frame.y, frame.width, frame.height, 26);
  context.fill();
  context.stroke();

  context.fillStyle = "#f3fbff";
  context.font = "700 25px 'Segoe UI'";
  context.fillText(title, frame.x + innerPadding, frame.y + 34);
  context.fillStyle = accentColor;
  context.font = "600 13px 'Segoe UI'";
  context.fillText(annotation, frame.x + innerPadding, frame.y + 56);
  context.fillStyle = "#d7e4f1";
  context.font = "700 13px 'Segoe UI'";
  context.fillText(`Peak: ${formatFloat(maxValue, 3)}`, colorbarX - 6, frame.y + 32);

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const normalized = densityGrid[row][col] / maxValue;
      const x = gridX + col * cellSize;
      const y = gridY + row * cellSize;
      context.fillStyle = interpolateViridis(normalized);
      context.fillRect(x, y, cellSize - 1, cellSize - 1);
    }
  }

  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1;
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

  context.strokeStyle = accentColor;
  context.lineWidth = 2;
  context.strokeRect(
    gridX + centerCol * cellSize,
    gridY + centerRow * cellSize,
    cellSize - 1,
    cellSize - 1
  );

  const peakX = gridX + (peak.col + 0.5) * cellSize;
  const peakY = gridY + (peak.row + 0.5) * cellSize;
  context.strokeStyle = "#fff8de";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(peakX - 0.34 * cellSize, peakY);
  context.lineTo(peakX + 0.34 * cellSize, peakY);
  context.moveTo(peakX, peakY - 0.34 * cellSize);
  context.lineTo(peakX, peakY + 0.34 * cellSize);
  context.stroke();

  for (let step = 0; step < 140; step += 1) {
    const alpha = step / 139;
    context.fillStyle = interpolateViridis(1.0 - alpha);
    context.fillRect(colorbarX, colorbarY + alpha * gridHeight, colorbarWidth, (gridHeight / 139) + 1);
  }
  context.strokeStyle = "rgba(255,255,255,0.16)";
  context.strokeRect(colorbarX, colorbarY, colorbarWidth, gridHeight);
  context.fillStyle = "#dce8f4";
  context.font = "700 12px 'Segoe UI'";
  context.fillText(formatFloat(maxValue, 3), colorbarX - 2, colorbarY - 8);
  context.fillText("0.000", colorbarX - 2, colorbarY + gridHeight + 18);

  return {
    gridX,
    gridY,
    cellSize,
    rows,
    cols,
    gridWidth,
    gridHeight,
  };
}

function normalizedRadialCurve(profile) {
  const maxValue = Math.max(...profile.map((entry) => entry.mean_density), 1.0e-12);
  return profile.map((entry) => ({
    radius: Number(entry.radius),
    value: entry.mean_density / maxValue,
  }));
}

function findObstructionRadius(trivialCurve, topologicalCurve) {
  const length = Math.min(trivialCurve.length, topologicalCurve.length);
  for (let index = 0; index < length; index += 1) {
    if (topologicalCurve[index].value > trivialCurve[index].value) {
      return topologicalCurve[index].radius;
    }
  }
  return topologicalCurve[Math.min(topologicalCurve.length - 1, 3)]?.radius ?? 3;
}

function drawRadialChart(frame, trivialProfile, topologicalProfile) {
  const trivialCurve = normalizedRadialCurve(trivialProfile);
  const topologicalCurve = normalizedRadialCurve(topologicalProfile);
  const maxRadius = Math.max(
    trivialCurve[trivialCurve.length - 1]?.radius ?? 1,
    topologicalCurve[topologicalCurve.length - 1]?.radius ?? 1,
  );
  const obstructionRadius = findObstructionRadius(trivialCurve, topologicalCurve);

  context.fillStyle = "rgba(18, 22, 37, 0.86)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(frame.x, frame.y, frame.width, frame.height, 26);
  context.fill();
  context.stroke();

  context.fillStyle = "#f3fbff";
  context.font = "700 23px 'Segoe UI'";
  context.fillText("Radial Mean Density", frame.x + 24, frame.y + 34);
  context.fillStyle = "#c7d7e8";
  context.font = "600 13px 'Segoe UI'";
  context.fillText("Radius (lattice sites)", frame.x + frame.width - 176, frame.y + frame.height - 16);

  const left = frame.x + 58;
  const right = frame.x + frame.width - 24;
  const top = frame.y + 56;
  const bottom = frame.y + frame.height - 44;
  const plotWidth = right - left;
  const plotHeight = bottom - top;

  context.strokeStyle = "rgba(255,255,255,0.10)";
  context.lineWidth = 1;
  for (let guide = 0; guide <= 4; guide += 1) {
    const y = bottom - (guide / 4) * plotHeight;
    context.beginPath();
    context.moveTo(left, y);
    context.lineTo(right, y);
    context.stroke();
  }
  for (let tick = 0; tick <= maxRadius; tick += 1) {
    const x = left + (tick / Math.max(maxRadius, 1)) * plotWidth;
    context.beginPath();
    context.moveTo(x, bottom);
    context.lineTo(x, bottom + 6);
    context.stroke();
    context.fillStyle = "#9fb3c8";
    context.font = "600 11px 'Segoe UI'";
    context.fillText(`${tick}`, x - 3, bottom + 20);
  }

  const obstructionX = left + (obstructionRadius / Math.max(maxRadius, 1)) * plotWidth;
  context.setLineDash([6, 6]);
  context.strokeStyle = "rgba(255, 221, 110, 0.85)";
  context.beginPath();
  context.moveTo(obstructionX, top);
  context.lineTo(obstructionX, bottom);
  context.stroke();
  context.setLineDash([]);
  context.fillStyle = "#ffe08a";
  context.font = "700 12px 'Segoe UI'";
  context.fillText("Obstruction radius", Math.min(obstructionX + 8, right - 120), top + 16);

  function drawCurve(curve, strokeStyle) {
    context.strokeStyle = strokeStyle;
    context.lineWidth = 3.2;
    context.beginPath();
    curve.forEach((entry, index) => {
      const x = left + (entry.radius / Math.max(maxRadius, 1)) * plotWidth;
      const y = bottom - entry.value * plotHeight;
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });
    context.stroke();
  }

  drawCurve(trivialCurve, "#22d3ee");
  drawCurve(topologicalCurve, "#f97316");

  context.fillStyle = "#22d3ee";
  context.font = "700 12px 'Segoe UI'";
  context.fillText("Trivial", frame.x + 26, frame.y + 58);
  context.fillStyle = "#f97316";
  context.fillText("Topological", frame.x + 92, frame.y + 58);
}

function draw(payload) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#0a1320";
  context.fillRect(0, 0, width, height);

  const margin = 26;
  const gap = 24;
  const trivialMeta = payload.metadata.comparison.trivial;
  const topologicalMeta = payload.metadata.comparison.topological;
  if (currentView === "radial") {
    const radialFrame = {
      x: margin,
      y: margin,
      width: width - (2 * margin),
      height: height - (2 * margin),
    };
    drawRadialChart(radialFrame, trivialMeta.radial_profile, topologicalMeta.radial_profile);
    latestLayout = null;
    return;
  }

  const panelWidth = (width - (2 * margin) - gap) / 2;
  const frameHeight = height - (2 * margin);
  const trivialFrame = { x: margin, y: margin, width: panelWidth, height: frameHeight };
  const topologicalFrame = { x: margin + panelWidth + gap, y: margin, width: panelWidth, height: frameHeight };

  const trivialLayout = drawHeatmapPanel(
    trivialFrame,
    "Trivial Phase",
    trivialMeta.annotation,
    trivialMeta.density_grid,
    "#22d3ee",
  );
  const topologicalLayout = drawHeatmapPanel(
    topologicalFrame,
    "Topological Phase",
    topologicalMeta.annotation,
    topologicalMeta.density_grid,
    "#f97316",
  );

  latestLayout = { trivial: trivialLayout, topological: topologicalLayout };
}

function updateHover(panelName, row, col, density) {
  hoverPanelNode.textContent = panelName;
  hoverSiteNode.textContent = `(${col}, ${row})`;
  hoverDensityNode.textContent = formatFloat(density, 6);
}

function clearHover() {
  hoverPanelNode.textContent = "Hover a map";
  hoverSiteNode.textContent = "--";
  hoverDensityNode.textContent = "--";
}

function hitTest(event) {
  if (!latestLayout || currentView !== "lattice") {
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

function buildSvg(payload) {
  const width = 1600;
  const height = 980;
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const tempCanvas = document.createElement("canvas");
  tempCanvas.width = width * ratio;
  tempCanvas.height = height * ratio;
  tempCanvas.style.width = `${width}px`;
  tempCanvas.style.height = `${height}px`;
  const previousCanvas = {
    width: canvas.width,
    height: canvas.height,
    latestPayload,
    latestLayout,
  };
  const previousContext = context;
  const oldCanvas = canvas;
  void previousContext;
  void oldCanvas;

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#0a1320" />
  <text x="44" y="48" fill="#f3fbff" font-size="30" font-weight="700">Wannier Function Obstruction</text>
  <text x="44" y="82" fill="#c3d2e0" font-size="15">Open-boundary projected-state comparison in real space</text>
  <text x="44" y="122" fill="#9fb3c8" font-size="13">Use the PNG export for the full rendered view.</text>
</svg>`;
}

async function loadData() {
  const response = await fetch("../../data/exports/task5.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load task5.json: ${response.status}`);
  }
  return response.json();
}

loadData()
  .then((payload) => {
    latestPayload = payload;
    trivialBottNode.textContent = `${payload.metadata.comparison.trivial.bott_index}`;
    topologicalBottNode.textContent = `${payload.metadata.comparison.topological.bott_index}`;
    const ratio = payload.metadata.comparison.trivial.center_to_mean_ratio /
      Math.max(payload.metadata.comparison.topological.center_to_mean_ratio, 1.0e-12);
    centerRatioNode.textContent = formatFloat(ratio, 3);
    draw(payload);
  })
  .catch((error) => {
    context.fillStyle = "#f2f7ff";
    context.font = "600 24px 'Segoe UI'";
    context.fillText(error.message, 32, 48);
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
  const density = latestPayload.metadata.comparison[hit.panelName].density_grid[hit.row][hit.col];
  updateHover(
    hit.panelName === "trivial" ? "Trivial phase" : "Topological phase",
    hit.row,
    hit.col,
    density,
  );
});

canvas.addEventListener("mouseleave", clearHover);
viewLatticeButton.addEventListener("click", () => setView("lattice"));
viewRadialButton.addEventListener("click", () => setView("radial"));

exportJsonButton.addEventListener("click", () => {
  if (!latestPayload) {
    return;
  }
  const blob = new Blob([JSON.stringify(latestPayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "wannier_obstruction.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

exportPngButton.addEventListener("click", () => {
  const anchor = document.createElement("a");
  anchor.href = canvas.toDataURL("image/png");
  anchor.download = "wannier_obstruction.png";
  anchor.click();
});

exportSvgButton.addEventListener("click", () => {
  if (!latestPayload) {
    return;
  }
  const blob = new Blob([buildSvg(latestPayload)], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "wannier_obstruction.svg";
  anchor.click();
  URL.revokeObjectURL(url);
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
setView("lattice");
