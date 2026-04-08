const plotNode = document.getElementById("bonus-plot");
const thresholdSlider = document.getElementById("bonus-threshold-slider");
const thresholdReadoutNode = document.getElementById("bonus-threshold-readout");
const bottNode = document.getElementById("bonus-bott");
const thresholdGapNode = document.getElementById("bonus-threshold-gap");
const pointCountNode = document.getElementById("bonus-point-count");
const kappaNode = document.getElementById("bonus-kappa");
const minPositionNode = document.getElementById("bonus-min-position");
const minEnergyNode = document.getElementById("bonus-min-energy");
const minGapNode = document.getElementById("bonus-min-gap");
const exportJsonButton = document.getElementById("bonus-export-json");
const exportPngButton = document.getElementById("bonus-export-png");
const exportSvgButton = document.getElementById("bonus-export-svg");

if (
  !plotNode ||
  !thresholdSlider ||
  !thresholdReadoutNode ||
  !bottNode ||
  !thresholdGapNode ||
  !pointCountNode ||
  !kappaNode ||
  !minPositionNode ||
  !minEnergyNode ||
  !minGapNode ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton
) {
  throw new Error("Clifford spectrum UI is missing required elements.");
}

let payload = null;
let currentLevelIndex = 0;

function formatFloat(value, digits = 3) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "--";
}

function updateReadouts(level) {
  thresholdReadoutNode.textContent = `${formatFloat(level.percentile, 1)}%`;
  thresholdGapNode.textContent = formatFloat(level.threshold_gap, 4);
  pointCountNode.textContent = `${level.point_count}`;
}

function renderPlot() {
  if (!payload || !window.Plotly) {
    return;
  }

  const minimum = payload.metadata.scalar_field.global_minimum;
  const level = payload.metadata.point_cloud.threshold_levels[currentLevelIndex];
  const x = level.points.map((point) => point.x);
  const y = level.points.map((point) => point.y);
  const z = level.points.map((point) => point.energy);
  const color = level.points.map((point) => point.closeness);
  const gap = level.points.map((point) => point.gap);

  const traces = [
    {
      type: "scatter3d",
      mode: "markers",
      x,
      y,
      z,
      marker: {
        size: 5,
        color,
        colorscale: "Plasma",
        cmin: 0,
        cmax: 1,
        opacity: 0.9,
        colorbar: {
          title: { text: "closeness", side: "right" },
          tickfont: { color: "#e7f2ff" },
          titlefont: { color: "#e7f2ff" },
          outlinecolor: "rgba(255,255,255,0.18)",
        },
      },
      text: gap.map((value) => formatFloat(value, 4)),
      hovertemplate: "x=%{x:.2f}<br>y=%{y:.2f}<br>E=%{z:.3f}<br>gap=%{text}<extra></extra>",
      name: "Near-zero cloud",
    },
    {
      type: "scatter3d",
      mode: "markers",
      x: [minimum.x],
      y: [minimum.y],
      z: [minimum.energy],
      marker: {
        size: 8,
        color: "#7ce7ff",
        line: { color: "#ffffff", width: 1.2 },
      },
      hovertemplate: "Global minimum<br>x=%{x:.2f}<br>y=%{y:.2f}<br>E=%{z:.3f}<extra></extra>",
      name: "Minimum",
    },
  ];

  const layout = {
    paper_bgcolor: "#07111a",
    plot_bgcolor: "#07111a",
    margin: { l: 0, r: 0, t: 0, b: 0 },
    showlegend: true,
    legend: {
      bgcolor: "rgba(10, 19, 32, 0.68)",
      bordercolor: "rgba(255,255,255,0.12)",
      borderwidth: 1,
      font: { color: "#eff7ff", size: 12 },
      x: 0.02,
      y: 0.98,
    },
    scene: {
      bgcolor: "#07111a",
      camera: {
        eye: { x: 1.55, y: 1.25, z: 1.2 },
      },
      xaxis: {
        title: "Lattice x",
        color: "#d7e4f3",
        gridcolor: "rgba(255,255,255,0.12)",
        zerolinecolor: "rgba(255,255,255,0.12)",
      },
      yaxis: {
        title: "Lattice y",
        color: "#d7e4f3",
        gridcolor: "rgba(255,255,255,0.12)",
        zerolinecolor: "rgba(255,255,255,0.12)",
      },
      zaxis: {
        title: "Energy E",
        color: "#d7e4f3",
        gridcolor: "rgba(255,255,255,0.12)",
        zerolinecolor: "rgba(255,255,255,0.12)",
      },
      aspectmode: "cube",
    },
    annotations: [
      {
        x: 0.02,
        y: 0.04,
        xref: "paper",
        yref: "paper",
        showarrow: false,
        align: "left",
        bgcolor: "rgba(10,19,32,0.72)",
        bordercolor: "rgba(255,255,255,0.12)",
        borderwidth: 1,
        font: { color: "#e7f2ff", size: 12 },
        text: `Percentile: ${formatFloat(level.percentile, 1)}%<br>Threshold gap: ${formatFloat(level.threshold_gap, 4)}`,
      },
    ],
  };

  window.Plotly.react(plotNode, traces, layout, {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso3d", "select2d", "resetCameraDefault3d"],
  });
}

function cleanup() {
  if (window.Plotly && plotNode) {
    window.Plotly.purge(plotNode);
  }
}

async function loadPayload() {
  const response = await fetch("../../data/exports/bonus_task.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load bonus_task.json: ${response.status}`);
  }
  return response.json();
}

loadPayload()
  .then((nextPayload) => {
    payload = nextPayload;
    currentLevelIndex = payload.metadata.point_cloud.default_index;
    const levels = payload.metadata.point_cloud.threshold_levels;
    thresholdSlider.max = `${Math.max(levels.length - 1, 0)}`;
    thresholdSlider.value = `${currentLevelIndex}`;
    bottNode.textContent = `${payload.bott_index}`;
    kappaNode.textContent = formatFloat(payload.metadata.kappa, 3);
    minPositionNode.textContent = `(${formatFloat(payload.metadata.scalar_field.global_minimum.x, 2)}, ${formatFloat(payload.metadata.scalar_field.global_minimum.y, 2)})`;
    minEnergyNode.textContent = formatFloat(payload.metadata.scalar_field.global_minimum.energy, 3);
    minGapNode.textContent = formatFloat(payload.metadata.scalar_field.global_minimum.gap, 5);
    updateReadouts(levels[currentLevelIndex]);
    renderPlot();
  })
  .catch((error) => {
    plotNode.textContent = error.message;
    plotNode.style.display = "grid";
    plotNode.style.placeItems = "center";
    plotNode.style.color = "#eff7ff";
  });

thresholdSlider.addEventListener("input", (event) => {
  if (!payload) {
    return;
  }
  currentLevelIndex = Number.parseInt(event.target.value || "0", 10) || 0;
  updateReadouts(payload.metadata.point_cloud.threshold_levels[currentLevelIndex]);
  renderPlot();
});

exportJsonButton.addEventListener("click", () => {
  if (!payload) {
    return;
  }
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "clifford_spectrum_point_cloud.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

exportPngButton.addEventListener("click", () => {
  if (!window.Plotly) {
    return;
  }
  window.Plotly.downloadImage(plotNode, {
    format: "png",
    filename: "clifford_spectrum_point_cloud",
    width: 1600,
    height: 960,
  });
});

exportSvgButton.addEventListener("click", () => {
  if (!window.Plotly) {
    return;
  }
  window.Plotly.downloadImage(plotNode, {
    format: "svg",
    filename: "clifford_spectrum_point_cloud",
    width: 1600,
    height: 960,
  });
});

window.addEventListener("beforeunload", cleanup);
window.cliffordSpectrumCleanup = cleanup;
