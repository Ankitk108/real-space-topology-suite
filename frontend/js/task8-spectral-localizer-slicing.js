const plotNode = document.getElementById("task8-plot");
const energySlider = document.getElementById("task8-energy-slider");
const energyReadoutNode = document.getElementById("task8-energy-readout");
const bottNode = document.getElementById("task8-bott");
const kappaNode = document.getElementById("task8-kappa");
const globalGapNode = document.getElementById("task8-global-gap");
const sliceMeanNode = document.getElementById("task8-slice-mean");
const minPositionNode = document.getElementById("task8-min-position");
const minEnergyNode = document.getElementById("task8-min-energy");
const computeSecondsNode = document.getElementById("task8-compute-seconds");
const exportJsonButton = document.getElementById("task8-export-json");
const exportPngButton = document.getElementById("task8-export-png");
const exportSvgButton = document.getElementById("task8-export-svg");

if (
  !plotNode ||
  !energySlider ||
  !energyReadoutNode ||
  !bottNode ||
  !kappaNode ||
  !globalGapNode ||
  !sliceMeanNode ||
  !minPositionNode ||
  !minEnergyNode ||
  !computeSecondsNode ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton
) {
  throw new Error("Spectral localizer slicing UI is missing required elements.");
}

let payload = null;
let flattenedField = null;
let currentSliceIndex = 0;

function formatFloat(value, digits = 3) {
  return Number.isFinite(value) ? Number(value).toFixed(digits) : "--";
}

function flattenScalarField(field) {
  const x = [];
  const y = [];
  const z = [];
  const value = [];
  const xAxis = field.x_axis;
  const yAxis = field.y_axis;
  const energyAxis = field.energy_axis;

  for (let energyIndex = 0; energyIndex < energyAxis.length; energyIndex += 1) {
    for (let yIndex = 0; yIndex < yAxis.length; yIndex += 1) {
      for (let xIndex = 0; xIndex < xAxis.length; xIndex += 1) {
        x.push(xAxis[xIndex]);
        y.push(yAxis[yIndex]);
        z.push(energyAxis[energyIndex]);
        value.push(field.field_grid[energyIndex][yIndex][xIndex]);
      }
    }
  }

  return { x, y, z, value };
}

function buildSliceSurface(field, sliceIndex) {
  const energy = field.energy_axis[sliceIndex];
  const z = field.y_axis.map(() => field.x_axis.map(() => energy));
  return {
    x: field.x_axis,
    y: field.y_axis,
    z,
    surfacecolor: field.field_grid[sliceIndex],
  };
}

function updateReadouts(field, sliceIndex) {
  const sliceSummary = field.slice_summaries[sliceIndex];
  const globalMinimum = field.global_minimum;
  energyReadoutNode.textContent = formatFloat(sliceSummary.energy, 3);
  sliceMeanNode.textContent = formatFloat(sliceSummary.mean_gap, 4);
  globalGapNode.textContent = formatFloat(globalMinimum.gap, 4);
  minPositionNode.textContent = `(${formatFloat(globalMinimum.x, 2)}, ${formatFloat(globalMinimum.y, 2)})`;
  minEnergyNode.textContent = formatFloat(globalMinimum.energy, 3);
}

function renderPlot() {
  if (!payload || !window.Plotly) {
    return;
  }

  const field = payload.metadata.scalar_field;
  const slice = buildSliceSurface(field, currentSliceIndex);
  const minimum = field.global_minimum;

  const traces = [
    {
      type: "volume",
      x: flattenedField.x,
      y: flattenedField.y,
      z: flattenedField.z,
      value: flattenedField.value,
      isomin: field.minimum_gap,
      isomax: field.maximum_gap,
      opacity: 0.12,
      surface: { count: 14 },
      colorscale: "Cividis",
      showscale: false,
      caps: { x: { show: false }, y: { show: false }, z: { show: false } },
      hovertemplate: "x=%{x:.2f}<br>y=%{y:.2f}<br>E=%{z:.3f}<br>|L<sup>-1</sup>|<sup>-1</sup>=%{value:.4f}<extra></extra>",
      name: "Volume",
    },
    {
      type: "surface",
      x: slice.x,
      y: slice.y,
      z: slice.z,
      surfacecolor: slice.surfacecolor,
      cmin: field.minimum_gap,
      cmax: field.maximum_gap,
      colorscale: "Cividis",
      opacity: 0.95,
      showscale: true,
      colorbar: {
        title: { text: "|L<sub>λ</sub><sup>-1</sup>|<sup>-1</sup>", side: "right" },
        tickfont: { color: "#e7f2ff" },
        titlefont: { color: "#e7f2ff" },
        outlinecolor: "rgba(255,255,255,0.18)",
      },
      hovertemplate: "Slice E=%{z:.3f}<br>x=%{x:.2f}<br>y=%{y:.2f}<br>gap=%{surfacecolor:.4f}<extra></extra>",
      name: "Slice",
    },
    {
      type: "scatter3d",
      mode: "markers",
      x: [minimum.x],
      y: [minimum.y],
      z: [minimum.energy],
      marker: {
        size: 8,
        color: "#ff9a42",
        line: { color: "#fff4dc", width: 1.2 },
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
        eye: { x: 1.55, y: 1.45, z: 1.15 },
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
        text: `Slice energy: ${formatFloat(field.slice_summaries[currentSliceIndex].energy, 3)}<br>Slice min gap: ${formatFloat(field.slice_summaries[currentSliceIndex].minimum_gap, 4)}`,
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
  const response = await fetch("../../data/exports/task8.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error(`Failed to load task8.json: ${response.status}`);
  }
  return response.json();
}

loadPayload()
  .then((nextPayload) => {
    payload = nextPayload;
    const field = payload.metadata.scalar_field;
    flattenedField = flattenScalarField(field);
    currentSliceIndex = Math.floor(field.energy_axis.length / 2);
    energySlider.max = `${Math.max(field.energy_axis.length - 1, 0)}`;
    energySlider.value = `${currentSliceIndex}`;
    bottNode.textContent = `${payload.bott_index}`;
    kappaNode.textContent = formatFloat(payload.metadata.kappa, 3);
    computeSecondsNode.textContent = `${formatFloat(field.compute_seconds, 2)} s`;
    updateReadouts(field, currentSliceIndex);
    renderPlot();
  })
  .catch((error) => {
    plotNode.textContent = error.message;
    plotNode.style.display = "grid";
    plotNode.style.placeItems = "center";
    plotNode.style.color = "#eff7ff";
  });

energySlider.addEventListener("input", (event) => {
  if (!payload) {
    return;
  }
  currentSliceIndex = Number.parseInt(event.target.value || "0", 10) || 0;
  updateReadouts(payload.metadata.scalar_field, currentSliceIndex);
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
  anchor.download = "spectral_localizer_slicing.json";
  anchor.click();
  URL.revokeObjectURL(url);
});

exportPngButton.addEventListener("click", () => {
  if (!window.Plotly) {
    return;
  }
  window.Plotly.downloadImage(plotNode, {
    format: "png",
    filename: "spectral_localizer_slicing",
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
    filename: "spectral_localizer_slicing",
    width: 1600,
    height: 960,
  });
});

window.addEventListener("beforeunload", cleanup);
window.spectralLocalizerCleanup = cleanup;
