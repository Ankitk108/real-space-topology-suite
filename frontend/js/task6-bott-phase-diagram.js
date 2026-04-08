const canvas = document.getElementById("task6-canvas");
const massCountNode = document.getElementById("task6-mass-count");
const disorderCountNode = document.getElementById("task6-disorder-count");
const selectedDisorderNode = document.getElementById("task6-selected-disorder");
const collapseMassNode = document.getElementById("task6-collapse-mass");
const realizationsNode = document.getElementById("task6-realizations");
const sliderReadoutNode = document.getElementById("task6-slider-readout");
const hoverMassNode = document.getElementById("task6-hover-mass");
const hoverDisorderNode = document.getElementById("task6-hover-disorder");
const hoverBottNode = document.getElementById("task6-hover-bott");
const hoverGapNode = document.getElementById("task6-hover-gap");
const hoverFractionNode = document.getElementById("task6-hover-fraction");
const disorderSlider = document.getElementById("task6-disorder-slider");
const heatmapButton = document.getElementById("task6-view-heatmap");
const collapseButton = document.getElementById("task6-view-collapse");
const exportJsonButton = document.getElementById("task6-export-json");
const exportPngButton = document.getElementById("task6-export-png");
const exportSvgButton = document.getElementById("task6-export-svg");

if (
  !canvas ||
  !massCountNode ||
  !disorderCountNode ||
  !selectedDisorderNode ||
  !collapseMassNode ||
  !realizationsNode ||
  !sliderReadoutNode ||
  !hoverMassNode ||
  !hoverDisorderNode ||
  !hoverBottNode ||
  !hoverGapNode ||
  !hoverFractionNode ||
  !disorderSlider ||
  !heatmapButton ||
  !collapseButton ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton
) {
  throw new Error("Phase diagram UI is missing required elements.");
}

const context = canvas.getContext("2d");
let latestPayload = null;
let latestLayout = null;
let currentView = "heatmap";
let selectedDisorderIndex = 0;

const BOTT_COLORS = {
  "-2": "#ff6b6b",
  "-1": "#ff9a42",
  "0": "#243147",
  "1": "#22d3ee",
  "2": "#8cf26b",
};

function formatFloat(value, digits = 3) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "--";
}

function bottColor(value) {
  const key = `${Math.round(value)}`;
  return BOTT_COLORS[key] || "#c4b5fd";
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
  currentView = viewName === "collapse" ? "collapse" : "heatmap";
  heatmapButton.classList.toggle("is-active", currentView === "heatmap");
  collapseButton.classList.toggle("is-active", currentView === "collapse");
  heatmapButton.setAttribute("aria-pressed", currentView === "heatmap" ? "true" : "false");
  collapseButton.setAttribute("aria-pressed", currentView === "collapse" ? "true" : "false");
  if (latestPayload) {
    draw(latestPayload);
  }
}

function updateHover(mass, disorder, bott, gap, fraction = null) {
  hoverMassNode.textContent = formatFloat(mass, 3);
  hoverDisorderNode.textContent = formatFloat(disorder, 3);
  hoverBottNode.textContent = formatFloat(bott, 3);
  hoverGapNode.textContent = formatFloat(gap, 4);
  hoverFractionNode.textContent = fraction == null ? "--" : formatFloat(fraction, 3);
}

function clearHover() {
  hoverMassNode.textContent = "--";
  hoverDisorderNode.textContent = "--";
  hoverBottNode.textContent = "--";
  hoverGapNode.textContent = "--";
  hoverFractionNode.textContent = "--";
}

function drawHeatmap(frame, phaseData) {
  const massAxis = phaseData.mass_axis;
  const disorderAxis = phaseData.disorder_axis;
  const bottGrid = phaseData.bott_grid;
  const gapGrid = phaseData.gap_grid;
  const rows = disorderAxis.length;
  const cols = massAxis.length;
  const innerPadding = 30;
  const titleHeight = 66;
  const legendWidth = 160;
  const plotWidth = frame.width - (2 * innerPadding) - legendWidth;
  const plotHeight = frame.height - titleHeight - (2 * innerPadding);
  const cellSize = Math.min(plotWidth / cols, plotHeight / rows);
  const gridWidth = cellSize * cols;
  const gridHeight = cellSize * rows;
  const gridX = frame.x + innerPadding;
  const gridY = frame.y + titleHeight;
  const legendX = gridX + gridWidth + 30;

  context.fillStyle = "rgba(18, 22, 37, 0.86)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(frame.x, frame.y, frame.width, frame.height, 28);
  context.fill();
  context.stroke();

  context.fillStyle = "#f3fbff";
  context.font = "700 26px 'Segoe UI'";
  context.fillText("Bott Plateau Map", frame.x + innerPadding, frame.y + 34);
  context.fillStyle = "#bfd0e4";
  context.font = "600 13px 'Segoe UI'";
  context.fillText("Discrete Bott index across mass-disorder space", frame.x + innerPadding, frame.y + 56);

  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      const x = gridX + col * cellSize;
      const y = gridY + row * cellSize;
      context.fillStyle = bottColor(bottGrid[row][col]);
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

  context.strokeStyle = "rgba(255,255,255,0.16)";
  context.strokeRect(gridX, gridY, gridWidth, gridHeight);

  const selectedY = gridY + selectedDisorderIndex * cellSize;
  context.strokeStyle = "#ffe08a";
  context.lineWidth = 2;
  context.strokeRect(gridX, selectedY, gridWidth, cellSize - 1);

  context.fillStyle = "#d8e4f2";
  context.font = "600 13px 'Segoe UI'";
  context.fillText("Mass", gridX + gridWidth - 24, gridY + gridHeight + 30);
  context.save();
  context.translate(gridX - 42, gridY + gridHeight * 0.5);
  context.rotate(-Math.PI / 2);
  context.fillText("Disorder", 0, 0);
  context.restore();

  context.font = "600 11px 'Segoe UI'";
  massAxis.forEach((mass, index) => {
    if (index % 2 !== 0 && index !== cols - 1) {
      return;
    }
    const x = gridX + index * cellSize;
    context.fillText(formatFloat(mass, 1), x - 8, gridY + gridHeight + 16);
  });
  disorderAxis.forEach((disorder, index) => {
    if (index % 2 !== 0 && index !== rows - 1) {
      return;
    }
    const y = gridY + index * cellSize + 4;
    context.fillText(formatFloat(disorder, 1), gridX - 28, y);
  });

  const legendItems = [-1, 0, 1];
  context.fillStyle = "#eff7ff";
  context.font = "700 13px 'Segoe UI'";
  context.fillText("Plateaus", legendX, gridY + 18);
  legendItems.forEach((value, index) => {
    const y = gridY + 36 + index * 30;
    context.fillStyle = bottColor(value);
    context.fillRect(legendX, y, 18, 18);
    context.fillStyle = "#d7e4f1";
    context.fillText(`Bott ${value}`, legendX + 28, y + 14);
  });

  context.fillStyle = "#eff7ff";
  context.fillText("Selected Slice", legendX, gridY + 150);
  context.fillStyle = "#ffe08a";
  context.fillText(`w = ${formatFloat(disorderAxis[selectedDisorderIndex], 3)}`, legendX, gridY + 174);

  latestLayout = {
    type: "heatmap",
    gridX,
    gridY,
    gridWidth,
    gridHeight,
    cellSize,
    rows,
    cols,
    massAxis,
    disorderAxis,
    bottGrid,
    gapGrid,
  };
}

function drawCollapse(frame, collapseData) {
  const disorderAxis = collapseData.disorder_axis;
  const meanBott = collapseData.mean_bott_magnitude;
  const stdBott = collapseData.std_bott_magnitude;
  const meanGap = collapseData.mean_gap;
  const topologicalFraction = collapseData.topological_fraction;
  const realizationCurves = collapseData.bott_magnitude_realizations;
  const maxDisorder = Math.max(...disorderAxis, 1.0e-12);
  const criticalDisorder = collapseData.critical_disorder_estimate;

  context.fillStyle = "rgba(18, 22, 37, 0.86)";
  context.strokeStyle = "rgba(255,255,255,0.08)";
  context.lineWidth = 1.2;
  context.beginPath();
  context.roundRect(frame.x, frame.y, frame.width, frame.height, 28);
  context.fill();
  context.stroke();

  context.fillStyle = "#f3fbff";
  context.font = "700 26px 'Segoe UI'";
  context.fillText("Disorder Collapse", frame.x + 30, frame.y + 34);
  context.fillStyle = "#bfd0e4";
  context.font = "600 13px 'Segoe UI'";
  context.fillText(`Mass fixed deep in the topological phase at m = ${formatFloat(collapseData.mass, 3)}`, frame.x + 30, frame.y + 56);

  const left = frame.x + 66;
  const right = frame.x + frame.width - 32;
  const top = frame.y + 94;
  const bottom = frame.y + frame.height - 96;
  const plotWidth = right - left;
  const plotHeight = bottom - top;
  const legendX = left + 10;
  const legendY = top + 14;
  const legendWidth = 188;
  const legendHeight = 98;

  context.strokeStyle = "rgba(255,255,255,0.10)";
  context.lineWidth = 1;
  for (let guide = 0; guide <= 4; guide += 1) {
    const y = bottom - (guide / 4) * plotHeight;
    context.beginPath();
    context.moveTo(left, y);
    context.lineTo(right, y);
    context.stroke();

    const tickValue = guide / 4;
    context.fillStyle = "#9fb3c8";
    context.font = "600 11px 'Segoe UI'";
    context.fillText(formatFloat(tickValue, tickValue === 0 || tickValue === 1 ? 0 : 2), left - 30, y + 4);
  }

  realizationCurves.forEach((curve) => {
    context.strokeStyle = "rgba(124, 211, 238, 0.10)";
    context.lineWidth = 1.1;
    context.beginPath();
    curve.forEach((bott, index) => {
      const x = left + (disorderAxis[index] / maxDisorder) * plotWidth;
      const y = bottom - (bott / 1.05) * plotHeight;
      if (index === 0) {
        context.moveTo(x, y);
      } else {
        context.lineTo(x, y);
      }
    });
    context.stroke();
  });

  const upperBand = [];
  const lowerBand = [];
  disorderAxis.forEach((disorder, index) => {
    const x = left + (disorder / maxDisorder) * plotWidth;
    upperBand.push({ x, y: bottom - (Math.min(1.02, meanBott[index] + stdBott[index]) / 1.05) * plotHeight });
    lowerBand.push({ x, y: bottom - (Math.max(0.0, meanBott[index] - stdBott[index]) / 1.05) * plotHeight });
  });

  context.fillStyle = "rgba(34, 211, 238, 0.12)";
  context.beginPath();
  upperBand.forEach((point, index) => {
    if (index === 0) {
      context.moveTo(point.x, point.y);
    } else {
      context.lineTo(point.x, point.y);
    }
  });
  lowerBand.slice().reverse().forEach((point) => {
    context.lineTo(point.x, point.y);
  });
  context.closePath();
  context.fill();

  context.strokeStyle = "#22d3ee";
  context.lineWidth = 3.5;
  context.beginPath();
  meanBott.forEach((bott, index) => {
    const x = left + (disorderAxis[index] / maxDisorder) * plotWidth;
    const y = bottom - (bott / 1.05) * plotHeight;
    if (index === 0) {
      context.moveTo(x, y);
    } else {
      context.lineTo(x, y);
    }
  });
  context.stroke();

  context.strokeStyle = "#ff9a42";
  context.lineWidth = 2.4;
  context.beginPath();
  topologicalFraction.forEach((fraction, index) => {
    const x = left + (disorderAxis[index] / maxDisorder) * plotWidth;
    const y = bottom - (fraction / 1.05) * plotHeight;
    if (index === 0) {
      context.moveTo(x, y);
    } else {
      context.lineTo(x, y);
    }
  });
  context.stroke();

  if (criticalDisorder != null) {
    const criticalX = left + (criticalDisorder / maxDisorder) * plotWidth;
    context.setLineDash([6, 6]);
    context.strokeStyle = "#ffe08a";
    context.lineWidth = 2;
    context.beginPath();
    context.moveTo(criticalX, top);
    context.lineTo(criticalX, bottom);
    context.stroke();
    context.setLineDash([]);
    context.fillStyle = "#ffe08a";
    context.font = "700 12px 'Segoe UI'";
    context.fillText(`Wc ~ ${formatFloat(criticalDisorder, 2)}`, Math.min(criticalX + 8, right - 56), top + 16);
  }

  context.fillStyle = "#d8e4f2";
  context.font = "600 13px 'Segoe UI'";
  context.fillText("Normalized response", left, top - 16);
  context.fillText("Disorder strength W", right - 106, bottom + 30);

  context.font = "600 11px 'Segoe UI'";
  disorderAxis.forEach((disorder, index) => {
    if (index % 2 !== 0 && index !== disorderAxis.length - 1) {
      return;
    }
    const x = left + (disorder / maxDisorder) * plotWidth;
    context.fillText(formatFloat(disorder, 1), x - 8, bottom + 16);
  });

  context.fillStyle = "rgba(12, 18, 31, 0.84)";
  context.strokeStyle = "rgba(255,255,255,0.10)";
  context.lineWidth = 1.1;
  context.beginPath();
  context.roundRect(legendX, legendY, legendWidth, legendHeight, 16);
  context.fill();
  context.stroke();

  context.fillStyle = "#eff7ff";
  context.font = "700 12px 'Segoe UI'";
  context.fillText("Legend", legendX + 14, legendY + 20);

  context.strokeStyle = "#22d3ee";
  context.lineWidth = 3.5;
  context.beginPath();
  context.moveTo(legendX + 14, legendY + 40);
  context.lineTo(legendX + 42, legendY + 40);
  context.stroke();
  context.fillStyle = "#22d3ee";
  context.font = "700 11px 'Segoe UI'";
  context.fillText("Mean |Bott|", legendX + 52, legendY + 44);

  context.fillStyle = "rgba(34, 211, 238, 0.12)";
  context.fillRect(legendX + 14, legendY + 54, 28, 10);
  context.fillStyle = "#9fe8f7";
  context.font = "700 11px 'Segoe UI'";
  context.fillText("Realization spread", legendX + 52, legendY + 63);

  context.strokeStyle = "#ff9a42";
  context.lineWidth = 2.4;
  context.beginPath();
  context.moveTo(legendX + 14, legendY + 80);
  context.lineTo(legendX + 42, legendY + 80);
  context.stroke();
  context.fillStyle = "#ffb36e";
  context.fillText("Topological fraction", legendX + 52, legendY + 84);

  const insightX = left;
  const insightY = bottom + 34;
  const insightWidth = Math.min(480, right - left - 130);
  const insightHeight = 44;
  context.fillStyle = "rgba(124,58,237,0.08)";
  context.strokeStyle = "rgba(124,58,237,0.22)";
  context.lineWidth = 1;
  context.beginPath();
  context.roundRect(insightX, insightY, insightWidth, insightHeight, 14);
  context.fill();
  context.stroke();

  context.fillStyle = "#d8e4f2";
  context.font = "700 11px 'Segoe UI'";
  context.fillText("Insight", insightX + 12, insightY + 16);
  context.font = "600 11px 'Segoe UI'";
  context.fillText("Flat near 1 means the topological phase survives disorder.", insightX + 64, insightY + 16);
  context.fillText("The sharp drop near Wc marks disorder-driven collapse of quantization.", insightX + 12, insightY + 33);

  latestLayout = {
    type: "collapse",
    left,
    right,
    top,
    bottom,
    plotWidth,
    plotHeight,
    disorderAxis,
    meanBott,
    meanGap,
    topologicalFraction,
    maxDisorder,
  };
}

function draw(payload) {
  const ratio = Math.min(window.devicePixelRatio || 1, 2);
  const width = canvas.width / ratio;
  const height = canvas.height / ratio;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#0a1320";
  context.fillRect(0, 0, width, height);

  const frame = { x: 26, y: 26, width: width - 52, height: height - 52 };
  if (currentView === "collapse") {
    drawCollapse(frame, payload.metadata.disorder_collapse);
  } else {
    drawHeatmap(frame, payload.metadata.phase_diagram);
  }
}

function hitTest(event) {
  if (!latestLayout) {
    return null;
  }
  const rect = canvas.getBoundingClientRect();
  const x = event.clientX - rect.left;
  const y = event.clientY - rect.top;

  if (latestLayout.type === "heatmap") {
    if (
      x < latestLayout.gridX ||
      x > latestLayout.gridX + latestLayout.gridWidth ||
      y < latestLayout.gridY ||
      y > latestLayout.gridY + latestLayout.gridHeight
    ) {
      return null;
    }
    const col = Math.min(latestLayout.cols - 1, Math.max(0, Math.floor((x - latestLayout.gridX) / latestLayout.cellSize)));
    const row = Math.min(latestLayout.rows - 1, Math.max(0, Math.floor((y - latestLayout.gridY) / latestLayout.cellSize)));
    return {
      mass: latestLayout.massAxis[col],
      disorder: latestLayout.disorderAxis[row],
      bott: latestLayout.bottGrid[row][col],
      gap: latestLayout.gapGrid[row][col],
    };
  }

  if (latestLayout.type === "collapse") {
    if (
      x < latestLayout.left ||
      x > latestLayout.right ||
      y < latestLayout.top ||
      y > latestLayout.bottom
    ) {
      return null;
    }
    const index = Math.min(
      latestLayout.disorderAxis.length - 1,
      Math.max(0, Math.round(((x - latestLayout.left) / Math.max(latestLayout.plotWidth, 1)) * (latestLayout.disorderAxis.length - 1))),
    );
    return {
      mass: latestPayload.metadata.disorder_collapse.mass,
      disorder: latestLayout.disorderAxis[index],
      bott: latestLayout.meanBott[index],
      gap: latestLayout.meanGap[index],
      fraction: latestLayout.topologicalFraction[index],
    };
  }

  return null;
}

function buildSvg() {
  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="760" viewBox="0 0 1200 760">
  <rect width="100%" height="100%" fill="#0a1320" />
  <text x="40" y="52" fill="#eff7ff" font-size="30" font-weight="700">Bott Phase Diagram</text>
  <text x="40" y="86" fill="#c4d2e1" font-size="15">Use PNG export for the plateau heatmap or disorder-collapse plot.</text>
</svg>`;
}

async function loadData() {
  const response = await fetch("../../data/exports/task6.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load task6.json: ${response.status}`);
  }
  return response.json();
}

loadData()
  .then((payload) => {
    latestPayload = payload;
    const phaseData = payload.metadata.phase_diagram;
    const collapseData = payload.metadata.disorder_collapse;
    massCountNode.textContent = `${phaseData.mass_axis.length}`;
    disorderCountNode.textContent = `${phaseData.disorder_axis.length}`;
    collapseMassNode.textContent = formatFloat(collapseData.mass, 3);
    realizationsNode.textContent = `${collapseData.realizations}`;
    disorderSlider.max = `${Math.max(phaseData.disorder_axis.length - 1, 0)}`;
    disorderSlider.value = "0";
    selectedDisorderIndex = 0;
    sliderReadoutNode.textContent = formatFloat(phaseData.disorder_axis[selectedDisorderIndex], 3);
    selectedDisorderNode.textContent = formatFloat(phaseData.disorder_axis[selectedDisorderIndex], 3);
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
  updateHover(hit.mass, hit.disorder, hit.bott, hit.gap, hit.fraction);
});

canvas.addEventListener("mouseleave", clearHover);
heatmapButton.addEventListener("click", () => setView("heatmap"));
collapseButton.addEventListener("click", () => setView("collapse"));
disorderSlider.addEventListener("input", (event) => {
  if (!latestPayload) {
    return;
  }
  selectedDisorderIndex = Number.parseInt(event.target.value || "0", 10) || 0;
  const disorder = latestPayload.metadata.phase_diagram.disorder_axis[selectedDisorderIndex];
  sliderReadoutNode.textContent = formatFloat(disorder, 3);
  selectedDisorderNode.textContent = formatFloat(disorder, 3);
  draw(latestPayload);
});

exportJsonButton.addEventListener("click", () => {
  if (!latestPayload) {
    return;
  }
  const blob = new Blob([JSON.stringify(latestPayload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "bott_phase_diagram.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

exportPngButton.addEventListener("click", () => {
  const anchor = document.createElement("a");
  anchor.href = canvas.toDataURL("image/png");
  anchor.download = "bott_phase_diagram.png";
  anchor.click();
});

exportSvgButton.addEventListener("click", () => {
  const blob = new Blob([buildSvg()], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "bott_phase_diagram.svg";
  anchor.click();
  URL.revokeObjectURL(url);
});

window.addEventListener("resize", resizeCanvas);
resizeCanvas();
