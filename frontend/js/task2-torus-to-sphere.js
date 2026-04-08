import * as THREE from "https://unpkg.com/three@0.164.1/build/three.module.js";
import { OrbitControls } from "https://unpkg.com/three@0.164.1/examples/jsm/controls/OrbitControls.js?module";

const sceneHost = document.getElementById("task2-scene");
const slider = document.getElementById("deformation-slider");
const deformationValue = document.getElementById("deformation-value");
const rotationToggle = document.getElementById("rotation-toggle");
const exportJsonButton = document.getElementById("export-json");
const exportPngButton = document.getElementById("export-png");
const exportSvgButton = document.getElementById("export-svg");
const statusNode = document.getElementById("task2-status");
const readoutCanvas = document.getElementById("task2-readout");
const sceneOverlayCanvas = document.getElementById("task2-scene-overlay");

if (
  !sceneHost ||
  !slider ||
  !deformationValue ||
  !rotationToggle ||
  !exportJsonButton ||
  !exportPngButton ||
  !exportSvgButton ||
  !statusNode ||
  !readoutCanvas ||
  !sceneOverlayCanvas
) {
  throw new Error("Task 2 UI is missing required elements.");
}

const state = {
  interpolation: Number.parseFloat(slider.value || "0") || 0,
  autoRotate: true,
  fps: 0,
  frameCounter: 0,
  frameAccumulator: 0,
  renderVersion: 0,
};

let pretextModulePromise = null;
let overlayStatusText = "Geometry ready.";

async function loadPretextModule() {
  if (pretextModulePromise) {
    return pretextModulePromise;
  }

  pretextModulePromise = (async () => {
    try {
      const module = await import("https://esm.sh/@chenglou/pretext");
      if (typeof module.prepare === "function" && typeof module.layout === "function") {
        return module;
      }
    } catch (error) {
      console.warn("Pretext.js failed to load, using canvas fallback.", error);
    }

    return {
      async prepare(line) {
        return line;
      },
      layout() {
        return { height: 22 };
      },
    };
  })();

  return pretextModulePromise;
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value));
}

function setStatus(message) {
  statusNode.textContent = `${message || " "}`;
  overlayStatusText = `${message || " "}`;
}

function smoothstep(value) {
  return value * value * (3.0 - 2.0 * value);
}

function triangularOddFourier(phi) {
  let total = 0.0;
  const terms = 7;
  for (let index = 0; index < terms; index += 1) {
    const harmonic = (2 * index) + 1;
    const sign = index % 2 === 0 ? 1.0 : -1.0;
    total += sign * Math.sin(harmonic * phi) / (harmonic * harmonic);
  }
  return (8.0 / (Math.PI * Math.PI)) * total;
}

function torusPosition(theta, phi) {
  const majorRadius = 1.65;
  const minorRadius = 0.66;
  const radial = majorRadius + (minorRadius * Math.cos(phi));
  return new THREE.Vector3(
    radial * Math.cos(theta),
    minorRadius * Math.sin(phi),
    radial * Math.sin(theta)
  );
}

function wrappedSpherePosition(theta, phi) {
  const fPhi = clamp(triangularOddFourier(phi), -1.0, 1.0);
  const radialEnvelope = Math.sqrt(Math.max(0.0, 1.0 - (fPhi * fPhi)));
  const gPhi = 0.35 * Math.cos(phi) * radialEnvelope;
  const hPhi = Math.max(0.06, radialEnvelope * (0.82 + 0.18 * Math.sin(phi) * Math.sin(phi)));
  return new THREE.Vector3(
    gPhi + (hPhi * Math.cos(theta)),
    fPhi,
    hPhi * Math.sin(theta)
  ).multiplyScalar(1.78);
}

function mixedPosition(theta, phi, interpolation) {
  return torusPosition(theta, phi).lerp(
    wrappedSpherePosition(theta, phi),
    smoothstep(interpolation)
  );
}

const renderer = new THREE.WebGLRenderer({
  antialias: true,
  alpha: true,
  preserveDrawingBuffer: true,
});
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
sceneHost.appendChild(renderer.domElement);

const scene = new THREE.Scene();
scene.fog = new THREE.Fog("#4b5077", 7, 18);

const camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
camera.position.set(0, 0, 7.2);

const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
controls.enablePan = false;
controls.minDistance = 2.9;
controls.maxDistance = 12;
controls.rotateSpeed = 0.78;
controls.touches.ONE = THREE.TOUCH.ROTATE;
controls.touches.TWO = THREE.TOUCH.DOLLY_PAN;
controls.target.set(0, 0, 0);

scene.add(new THREE.AmbientLight("#f7fbff", 1.75));

const keyLight = new THREE.DirectionalLight("#fafdff", 2.45);
keyLight.position.set(3.8, 5.4, 6.4);
scene.add(keyLight);

const fillLight = new THREE.DirectionalLight("#4bd8ff", 1.2);
fillLight.position.set(-5.6, 1.8, -2.4);
scene.add(fillLight);

const rimLight = new THREE.DirectionalLight("#866dff", 1.15);
rimLight.position.set(3.1, -2.2, -5.6);
scene.add(rimLight);

const surfaceGeometry = new THREE.BufferGeometry();
const surfaceMaterial = new THREE.MeshPhysicalMaterial({
  color: "#7acfff",
  roughness: 0.2,
  metalness: 0.05,
  clearcoat: 0.46,
  clearcoatRoughness: 0.24,
  side: THREE.DoubleSide,
  transparent: true,
  opacity: 0.96,
  vertexColors: true,
});
const surfaceMesh = new THREE.Mesh(surfaceGeometry, surfaceMaterial);
scene.add(surfaceMesh);

const wireMaterial = new THREE.LineBasicMaterial({
  color: "#dcf6ff",
  transparent: true,
  opacity: 0.18,
});
let wireframe = new THREE.LineSegments(new THREE.BufferGeometry(), wireMaterial);
scene.add(wireframe);

const guideRing = new THREE.Mesh(
  new THREE.TorusGeometry(1.65, 0.024, 18, 160),
  new THREE.MeshBasicMaterial({ color: "#7c73ff", transparent: true, opacity: 0.18 })
);
guideRing.rotation.x = Math.PI / 2;
scene.add(guideRing);

const segmentsU = 144;
const segmentsV = 88;
let latestVertices = [];
let latestIndices = [];
let animationFrameId = 0;
let fpsLogIntervalId = 0;
let resizeHandler = null;
const surfaceCenter = new THREE.Vector3();
const sphereBounds = new THREE.Sphere();

function pointColor(point) {
  const t = clamp(0.5 + (point.y / 3.8), 0.0, 1.0);
  const low = new THREE.Color("#4c63e8");
  const mid = new THREE.Color("#37d7ff");
  const high = new THREE.Color("#eefcff");
  return low.lerp(mid, Math.min(t * 1.3, 1.0)).lerp(high, Math.max(0.0, (t - 0.45) / 0.55));
}

function buildSurface(interpolation) {
  const vertices = [];
  const indices = [];
  const colors = [];

  for (let vIndex = 0; vIndex <= segmentsV; vIndex += 1) {
    const phi = (vIndex / segmentsV) * Math.PI * 2.0;
    for (let uIndex = 0; uIndex <= segmentsU; uIndex += 1) {
      const theta = (uIndex / segmentsU) * Math.PI * 2.0;
      const point = mixedPosition(theta, phi, interpolation);
      const color = pointColor(point);
      vertices.push(point.x, point.y, point.z);
      colors.push(color.r, color.g, color.b);
    }
  }

  for (let vIndex = 0; vIndex < segmentsV; vIndex += 1) {
    for (let uIndex = 0; uIndex < segmentsU; uIndex += 1) {
      const a = vIndex * (segmentsU + 1) + uIndex;
      const b = a + 1;
      const c = a + segmentsU + 1;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  latestVertices = vertices;
  latestIndices = indices;
  surfaceGeometry.setIndex(indices);
  surfaceGeometry.setAttribute("position", new THREE.Float32BufferAttribute(vertices, 3));
  surfaceGeometry.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
  surfaceGeometry.computeVertexNormals();

  scene.remove(wireframe);
  wireframe.geometry.dispose();
  wireframe = new THREE.LineSegments(new THREE.WireframeGeometry(surfaceGeometry), wireMaterial);
  scene.add(wireframe);
  state.renderVersion += 1;
  centerCameraOnSurface();
}

function centerCameraOnSurface() {
  surfaceGeometry.computeBoundingSphere();
  if (!surfaceGeometry.boundingSphere) {
    return;
  }

  sphereBounds.copy(surfaceGeometry.boundingSphere);
  surfaceCenter.copy(sphereBounds.center);

  const fitHeightDistance = sphereBounds.radius / Math.tan(THREE.MathUtils.degToRad(camera.fov * 0.5));
  const fitWidthDistance = fitHeightDistance / Math.max(camera.aspect, 0.7);
  const distance = 1.4 * Math.max(fitHeightDistance, fitWidthDistance);

  const offsetDirection = new THREE.Vector3(0.0, 0.05, 1.0).normalize();
  const nextPosition = surfaceCenter.clone().add(offsetDirection.multiplyScalar(distance));

  camera.position.copy(nextPosition);
  camera.near = Math.max(0.1, distance / 40);
  camera.far = Math.max(100, distance * 12);
  camera.lookAt(surfaceCenter);
  camera.updateProjectionMatrix();

  controls.target.copy(surfaceCenter);
  controls.update();
}

function resize() {
  const width = Math.max(sceneHost.clientWidth || 320, 320);
  const height = Math.max(sceneHost.clientHeight || 420, 420);
  renderer.setSize(width, height, false);
  const overlayRatio = Math.min(window.devicePixelRatio || 1, 2);
  sceneOverlayCanvas.width = Math.round(width * overlayRatio);
  sceneOverlayCanvas.height = Math.round(height * overlayRatio);
  camera.aspect = width / height;
  camera.updateProjectionMatrix();
  centerCameraOnSurface();
  drawSceneOverlay();
}

function formatFloat(value, digits = 3) {
  return Number.isFinite(value) ? value.toFixed(digits) : "--";
}

async function drawReadout() {
  const context = readoutCanvas.getContext("2d");
  const width = readoutCanvas.width;
  const height = readoutCanvas.height;
  context.clearRect(0, 0, width, height);
  context.fillStyle = "#1a3348";

  const lines = [
    `Interpolation ${formatFloat(state.interpolation, 3)}`,
    `FPS ${formatFloat(state.fps, 1)}`,
    `Vertices ${latestVertices.length / 3}`,
    `Truncation terms 7`,
    `Render version ${state.renderVersion}`,
  ];

  const pretext = await loadPretextModule();
  context.font = "600 18px 'Segoe UI'";
  let yCursor = 28;
  for (const line of lines) {
    const prepared = await pretext.prepare(line, context.font);
    const layout = pretext.layout(prepared, width - 28);
    context.fillText(line, 14, yCursor);
    yCursor += Math.max(26, Number(layout?.height || 22));
  }
}

function currentModeLabel() {
  if (state.interpolation <= 0.15) {
    return "Torus-biased";
  }
  if (state.interpolation >= 0.85) {
    return "Sphere-biased";
  }
  return "Mixed deformation";
}

function drawSceneOverlay() {
  const context = sceneOverlayCanvas.getContext("2d");
  if (!context) {
    return;
  }

  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  const width = sceneOverlayCanvas.width;
  const height = sceneOverlayCanvas.height;
  context.setTransform(1, 0, 0, 1, 0, 0);
  context.clearRect(0, 0, width, height);
  context.scale(pixelRatio, pixelRatio);

  const cardX = 24;
  const cardY = 24;
  const cardWidth = Math.min(280, Math.max(220, (width / pixelRatio) * 0.28));
  const cardHeight = 150;

  context.fillStyle = "rgba(14, 20, 36, 0.62)";
  context.strokeStyle = "rgba(130, 214, 255, 0.28)";
  context.lineWidth = 1.25;
  context.beginPath();
  context.roundRect(cardX, cardY, cardWidth, cardHeight, 18);
  context.fill();
  context.stroke();

  context.fillStyle = "#26dbff";
  context.font = "700 12px 'Segoe UI'";
  context.fillText("LIVE STATUS", cardX + 18, cardY + 26);

  context.fillStyle = "#f4fbff";
  context.font = "700 22px 'Segoe UI'";
  context.fillText(currentModeLabel(), cardX + 18, cardY + 58);

  context.fillStyle = "#c9d4ea";
  context.font = "600 14px 'Segoe UI'";
  context.fillText(`Deformation ${formatFloat(state.interpolation, 3)}`, cardX + 18, cardY + 88);
  context.fillText(`FPS ${formatFloat(state.fps, 1)}`, cardX + 18, cardY + 110);
  context.fillText(overlayStatusText, cardX + 18, cardY + 134, cardWidth - 36);

  context.strokeStyle = "rgba(124, 115, 255, 0.45)";
  context.lineWidth = 2;
  context.beginPath();
  context.moveTo(cardX + 18, cardY + cardHeight - 18);
  context.lineTo(cardX + cardWidth - 18, cardY + cardHeight - 18);
  context.stroke();
}

function updateReadout() {
  deformationValue.textContent = formatFloat(state.interpolation, 3);
  guideRing.material.opacity = THREE.MathUtils.lerp(0.24, 0.04, state.interpolation);
  void drawReadout();
  drawSceneOverlay();
}

function debounce(callback, waitMs) {
  let timeoutId = 0;
  return (...args) => {
    window.clearTimeout(timeoutId);
    timeoutId = window.setTimeout(() => callback(...args), waitMs);
  };
}

const debouncedSliderUpdate = debounce((nextValue) => {
  state.interpolation = clamp(nextValue, 0.0, 1.0);
  buildSurface(state.interpolation);
  updateReadout();
  setStatus(`Deformation updated to ${formatFloat(state.interpolation, 3)}.`);
}, 18);

slider.addEventListener("input", (event) => {
  const nextValue = Number.parseFloat(event.target.value || "0");
  if (!Number.isFinite(nextValue)) {
    return;
  }
  debouncedSliderUpdate(nextValue);
});

rotationToggle.addEventListener("click", () => {
  state.autoRotate = !state.autoRotate;
  rotationToggle.textContent = state.autoRotate ? "On" : "Off";
  rotationToggle.setAttribute("aria-pressed", state.autoRotate ? "true" : "false");
  setStatus(state.autoRotate ? "Auto rotation enabled." : "Auto rotation paused.");
});

function exportJson() {
  const payload = {
    task: "task2-torus-to-sphere",
    interpolation: state.interpolation,
    truncation_terms: 7,
    geometry: {
      major_radius: 1.65,
      minor_radius: 0.66,
      segments_u: segmentsU,
      segments_v: segmentsV,
    },
    sample_points: latestVertices.slice(0, 180),
    frame_rate_fps: state.fps,
  };
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "task2_torus_to_sphere.json";
  anchor.click();
  URL.revokeObjectURL(url);
  setStatus("JSON export completed.");
}

function exportPng() {
  renderer.render(scene, camera);
  const anchor = document.createElement("a");
  anchor.href = renderer.domElement.toDataURL("image/png");
  anchor.download = "task2_torus_to_sphere.png";
  anchor.click();
  setStatus("PNG export completed.");
}

function projectedSvg() {
  const width = renderer.domElement.width;
  const height = renderer.domElement.height;
  const lines = [];
  const position = surfaceGeometry.getAttribute("position");
  const lineEvery = 9;

  for (let vIndex = 0; vIndex <= segmentsV; vIndex += lineEvery) {
    const path = [];
    for (let uIndex = 0; uIndex <= segmentsU; uIndex += 1) {
      const index = vIndex * (segmentsU + 1) + uIndex;
      const point = new THREE.Vector3(
        position.getX(index),
        position.getY(index),
        position.getZ(index)
      );
      point.project(camera);
      const xCoord = (point.x * 0.5 + 0.5) * width;
      const yCoord = (-point.y * 0.5 + 0.5) * height;
      path.push(`${uIndex === 0 ? "M" : "L"} ${xCoord.toFixed(2)} ${yCoord.toFixed(2)}`);
    }
    lines.push(`<path d="${path.join(" ")}" fill="none" stroke="#4c7d94" stroke-width="1.2" stroke-opacity="0.7"/>`);
  }

  for (let uIndex = 0; uIndex <= segmentsU; uIndex += 12) {
    const path = [];
    for (let vIndex = 0; vIndex <= segmentsV; vIndex += 1) {
      const index = vIndex * (segmentsU + 1) + uIndex;
      const point = new THREE.Vector3(
        position.getX(index),
        position.getY(index),
        position.getZ(index)
      );
      point.project(camera);
      const xCoord = (point.x * 0.5 + 0.5) * width;
      const yCoord = (-point.y * 0.5 + 0.5) * height;
      path.push(`${vIndex === 0 ? "M" : "L"} ${xCoord.toFixed(2)} ${yCoord.toFixed(2)}`);
    }
    lines.push(`<path d="${path.join(" ")}" fill="none" stroke="#8ebfcb" stroke-width="0.9" stroke-opacity="0.55"/>`);
  }

  return `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="${width}" height="${height}" viewBox="0 0 ${width} ${height}">
  <rect width="100%" height="100%" fill="#eef3f7"/>
  ${lines.join("\n  ")}
</svg>`;
}

function exportSvg() {
  renderer.render(scene, camera);
  const blob = new Blob([projectedSvg()], { type: "image/svg+xml;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = "task2_torus_to_sphere.svg";
  anchor.click();
  URL.revokeObjectURL(url);
  setStatus("SVG export completed.");
}

exportJsonButton.addEventListener("click", exportJson);
exportPngButton.addEventListener("click", exportPng);
exportSvgButton.addEventListener("click", exportSvg);

const clock = new THREE.Clock();

function animate() {
  animationFrameId = window.requestAnimationFrame(animate);
  const delta = clock.getDelta();
  state.frameAccumulator += delta;
  state.frameCounter += 1;
  if (state.frameAccumulator >= 0.5) {
    state.fps = state.frameCounter / state.frameAccumulator;
    state.frameAccumulator = 0.0;
    state.frameCounter = 0;
    updateReadout();
  }

  const elapsed = clock.getElapsedTime();
  if (state.autoRotate) {
    surfaceMesh.rotation.y = elapsed * 0.18;
    wireframe.rotation.y = elapsed * 0.18;
    guideRing.rotation.z = elapsed * 0.18;
  }

  controls.update();
  renderer.render(scene, camera);
  drawSceneOverlay();
}

function startPerformanceLogging() {
  fpsLogIntervalId = window.setInterval(() => {
    const payload = {
      task: "task2",
      fps: Number(formatFloat(state.fps, 2)),
      interpolation: state.interpolation,
      memory_mb: performance.memory
        ? Number((performance.memory.usedJSHeapSize / (1024 * 1024)).toFixed(2))
        : 0.0,
    };
    console.info("task2_performance", payload);
  }, 5000);
}

export function cleanup() {
  window.cancelAnimationFrame(animationFrameId);
  window.clearInterval(fpsLogIntervalId);
  if (resizeHandler) {
    window.removeEventListener("resize", resizeHandler);
  }
  controls.dispose();
  surfaceGeometry.dispose();
  wireframe.geometry.dispose();
  wireMaterial.dispose();
  surfaceMaterial.dispose();
  guideRing.geometry.dispose();
  guideRing.material.dispose();
  renderer.dispose();
  if (renderer.domElement.parentNode === sceneHost) {
    sceneHost.removeChild(renderer.domElement);
  }
}

window.task2Cleanup = cleanup;

buildSurface(state.interpolation);
updateReadout();
resizeHandler = () => resize();
window.addEventListener("resize", resizeHandler);
resize();
startPerformanceLogging();
animate();
setStatus("Interactive deformation ready.");
