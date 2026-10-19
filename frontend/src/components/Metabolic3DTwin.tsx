import { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { RotateCw, ShieldAlert, CheckCircle2 } from 'lucide-react';
import type { TwinSnapshot } from '../types';

interface Metabolic3DTwinProps {
  snapshot?: TwinSnapshot | null;
}

export function Metabolic3DTwin({ snapshot }: Metabolic3DTwinProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [autoRotate, setAutoRotate] = useState(true);

  const highRisk = snapshot?.prediction?.high_glucose_risk ?? false;
  const trend = snapshot?.dynamic?.glucose_trend ?? 'Stable';
  const currentGlucose = snapshot?.dynamic?.current_glucose ?? 0;
  const predictedGlucose = snapshot?.prediction?.predicted_glucose_120m ?? 0;

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    // 1. Scene, Camera, Renderer
    const width = container.clientWidth || 300;
    const height = container.clientHeight || 450;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(45, width / height, 0.1, 100);
    camera.position.set(0, 0.5, 4.2);

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    container.innerHTML = '';
    container.appendChild(renderer.domElement);

    // 2. Lighting
    const ambientLight = new THREE.AmbientLight(0x404d6b, 1.5);
    scene.add(ambientLight);

    const keyLight = new THREE.DirectionalLight(0x88c0d0, 2.0);
    keyLight.position.set(3, 4, 3);
    scene.add(keyLight);

    const backLight = new THREE.DirectionalLight(0xb48ead, 1.2);
    backLight.position.set(-3, -2, -2);
    scene.add(backLight);

    const organLight = new THREE.PointLight(0xff6b6b, 2.0, 5);
    organLight.position.set(0, 0, 1);
    scene.add(organLight);

    // Group for whole model to rotate
    const modelGroup = new THREE.Group();
    scene.add(modelGroup);

    // 3. Holographic Body Torso
    const bodyGeo = new THREE.CylinderGeometry(0.8, 0.65, 2.6, 24, 8, true);
    const bodyMat = new THREE.MeshStandardMaterial({
      color: 0x38bdf8,
      wireframe: true,
      transparent: true,
      opacity: 0.12,
      roughness: 0.3,
    });
    const bodyMesh = new THREE.Mesh(bodyGeo, bodyMat);
    modelGroup.add(bodyMesh);

    // Torso outer subtle glow
    const torsoGlowGeo = new THREE.CapsuleGeometry(0.75, 1.3, 16, 24);
    const torsoGlowMat = new THREE.MeshBasicMaterial({
      color: 0x0284c7,
      transparent: true,
      opacity: 0.05,
      side: THREE.BackSide,
    });
    const torsoGlowMesh = new THREE.Mesh(torsoGlowGeo, torsoGlowMat);
    modelGroup.add(torsoGlowMesh);

    // 4. Organs
    // A. Pancreas (Elongated curved organ with reactive emission)
    const pancreasCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.4, 0.0, 0.1),
      new THREE.Vector3(-0.1, 0.1, 0.15),
      new THREE.Vector3(0.2, 0.05, 0.1),
      new THREE.Vector3(0.45, -0.05, 0.05),
    ]);
    const pancreasGeo = new THREE.TubeGeometry(pancreasCurve, 32, 0.12, 12, false);
    const pancreasMat = new THREE.MeshStandardMaterial({
      color: 0xf59e0b,
      emissive: 0xf59e0b,
      emissiveIntensity: 0.5,
      roughness: 0.3,
      metalness: 0.2,
    });
    const pancreasMesh = new THREE.Mesh(pancreasGeo, pancreasMat);
    pancreasMesh.name = 'Pancreas';
    modelGroup.add(pancreasMesh);

    // B. Stomach (J-shaped anatomical reservoir)
    const stomachGeo = new THREE.SphereGeometry(0.35, 24, 24);
    stomachGeo.scale(1.1, 1.4, 0.9);
    const stomachMat = new THREE.MeshStandardMaterial({
      color: 0x10b981,
      emissive: 0x059669,
      emissiveIntensity: 0.3,
      roughness: 0.4,
      metalness: 0.1,
    });
    const stomachMesh = new THREE.Mesh(stomachGeo, stomachMat);
    stomachMesh.position.set(-0.32, 0.35, 0.05);
    stomachMesh.rotation.z = 0.25;
    stomachMesh.name = 'Stomach';
    modelGroup.add(stomachMesh);

    // C. Intestines (Folded lower abdominal digestive loops)
    const intestineCurve = new THREE.CatmullRomCurve3([
      new THREE.Vector3(-0.3, -0.2, 0.1),
      new THREE.Vector3(0.25, -0.3, 0.15),
      new THREE.Vector3(-0.25, -0.45, 0.12),
      new THREE.Vector3(0.2, -0.6, 0.14),
      new THREE.Vector3(-0.15, -0.75, 0.1),
      new THREE.Vector3(0.1, -0.9, 0.08),
    ]);
    const intestineGeo = new THREE.TubeGeometry(intestineCurve, 48, 0.1, 10, false);
    const intestineMat = new THREE.MeshStandardMaterial({
      color: 0xd97706,
      emissive: 0x92400e,
      emissiveIntensity: 0.25,
      roughness: 0.5,
    });
    const intestineMesh = new THREE.Mesh(intestineGeo, intestineMat);
    intestineMesh.name = 'Intestine';
    modelGroup.add(intestineMesh);

    // 5. Circulatory Bloodstream Particles
    const particleCount = 280;
    const bloodPath = new THREE.EllipseCurve(
      0, 0, // ax, aY
      1.15, 1.35, // xRadius, yRadius
      0, 2 * Math.PI, // aStartAngle, aEndAngle
      false, // aClockwise
      0 // aRotation
    );
    const pathPoints = bloodPath.getPoints(particleCount);

    const particlePositions = new Float32Array(particleCount * 3);
    const particleColors = new Float32Array(particleCount * 3);
    const particleOffsets = new Float32Array(particleCount);

    for (let i = 0; i < particleCount; i++) {
      const pt = pathPoints[i];
      particlePositions[i * 3] = pt.x + (Math.random() - 0.5) * 0.08;
      particlePositions[i * 3 + 1] = pt.y + (Math.random() - 0.5) * 0.08;
      particlePositions[i * 3 + 2] = (Math.random() - 0.5) * 0.15;
      particleOffsets[i] = i / particleCount;

      // Crimson / red-orange particle colors
      particleColors[i * 3] = 0.9 + Math.random() * 0.1;
      particleColors[i * 3 + 1] = 0.2 + Math.random() * 0.2;
      particleColors[i * 3 + 2] = 0.2;
    }

    const bloodGeo = new THREE.BufferGeometry();
    bloodGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));
    bloodGeo.setAttribute('color', new THREE.BufferAttribute(particleColors, 3));

    const bloodMat = new THREE.PointsMaterial({
      size: 0.045,
      vertexColors: true,
      transparent: true,
      opacity: 0.85,
      blending: THREE.AdditiveBlending,
    });
    const bloodParticles = new THREE.Points(bloodGeo, bloodMat);
    modelGroup.add(bloodParticles);

    // 6. Interaction: Orbit Drag
    let isDragging = false;
    let prevMouseX = 0;
    let prevMouseY = 0;

    const onMouseDown = (e: MouseEvent) => {
      isDragging = true;
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseMove = (e: MouseEvent) => {
      if (!isDragging) return;
      const deltaX = e.clientX - prevMouseX;
      const deltaY = e.clientY - prevMouseY;
      modelGroup.rotation.y += deltaX * 0.01;
      modelGroup.rotation.x = Math.max(-0.4, Math.min(0.4, modelGroup.rotation.x + deltaY * 0.01));
      prevMouseX = e.clientX;
      prevMouseY = e.clientY;
    };

    const onMouseUp = () => {
      isDragging = false;
    };

    const domElement = renderer.domElement;
    domElement.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);

    // 7. Animation Loop
    let animationFrameId: number;
    let clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const time = clock.getElapsedTime();

      // Slow auto rotation
      if (autoRotate && !isDragging) {
        modelGroup.rotation.y += 0.006;
      }

      // Reactive Pancreas Glow
      if (highRisk) {
        const pulse = 0.8 + 0.6 * Math.sin(time * 6);
        pancreasMat.color.setHex(0xef4444);
        pancreasMat.emissive.setHex(0xef4444);
        pancreasMat.emissiveIntensity = pulse;
        organLight.color.setHex(0xef4444);
        organLight.intensity = pulse * 2.5;
      } else if (trend === 'Rising') {
        pancreasMat.color.setHex(0xf59e0b);
        pancreasMat.emissive.setHex(0xf59e0b);
        pancreasMat.emissiveIntensity = 0.7 + 0.3 * Math.sin(time * 3);
        organLight.color.setHex(0xf59e0b);
        organLight.intensity = 1.8;
      } else {
        pancreasMat.color.setHex(0x10b981);
        pancreasMat.emissive.setHex(0x10b981);
        pancreasMat.emissiveIntensity = 0.4 + 0.2 * Math.sin(time * 1.5);
        organLight.color.setHex(0x10b981);
        organLight.intensity = 1.0;
      }

      // Circulate bloodstream particles
      const positions = bloodGeo.attributes.position.array as Float32Array;
      const speed = highRisk ? 0.35 : 0.18;
      for (let i = 0; i < particleCount; i++) {
        let t = (particleOffsets[i] + time * speed) % 1;
        const pt = bloodPath.getPoint(t);
        positions[i * 3] = pt.x + Math.sin(time * 2 + i) * 0.02;
        positions[i * 3 + 1] = pt.y + Math.cos(time * 2 + i) * 0.02;
      }
      bloodGeo.attributes.position.needsUpdate = true;

      renderer.render(scene, camera);
    };

    animate();

    // Resize Observer
    const resizeObserver = new ResizeObserver((entries) => {
      for (let entry of entries) {
        const newW = entry.contentRect.width;
        const newH = entry.contentRect.height;
        if (newW > 0 && newH > 0) {
          camera.aspect = newW / newH;
          camera.updateProjectionMatrix();
          renderer.setSize(newW, newH);
        }
      }
    });
    resizeObserver.observe(container);

    // Cleanup
    return () => {
      cancelAnimationFrame(animationFrameId);
      resizeObserver.disconnect();
      domElement.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      renderer.dispose();
      bodyGeo.dispose();
      pancreasGeo.dispose();
      stomachGeo.dispose();
      intestineGeo.dispose();
      bloodGeo.dispose();
    };
  }, [highRisk, trend, autoRotate]);

  return (
    <div className="p-4 bg-gray-900 border border-gray-800 rounded-xl shadow-lg h-full min-h-[460px] flex flex-col relative overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between mb-2 z-10">
        <div>
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
            <h3 className="text-sm font-semibold tracking-wide text-gray-200 uppercase">
              3D Metabolic Twin
            </h3>
          </div>
          <p className="text-xs text-gray-400 mt-0.5">
            Real-time organ & circulatory telemetry
          </p>
        </div>

        {/* Controls */}
        <div className="flex items-center gap-1.5 bg-gray-800/80 backdrop-blur p-1 rounded-lg border border-gray-700/60">
          <button
            onClick={() => setAutoRotate(!autoRotate)}
            title={autoRotate ? "Pause Rotation" : "Auto Rotate"}
            className={`p-1.5 rounded text-xs transition ${
              autoRotate ? 'bg-sky-500/20 text-sky-400' : 'text-gray-400 hover:text-white'
            }`}
          >
            <RotateCw className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* 3D WebGL Canvas Viewport */}
      <div 
        ref={containerRef} 
        className="flex-1 w-full min-h-[300px] cursor-grab active:cursor-grabbing rounded-lg relative overflow-hidden bg-radial from-gray-950 to-gray-900"
      />

      {/* Interactive Telemetry Overlay Cards */}
      <div className="mt-3 grid grid-cols-2 gap-2 z-10 text-xs">
        {/* Pancreas State */}
        <div className={`p-2.5 rounded-lg border transition ${
          highRisk 
            ? 'bg-rose-950/40 border-rose-600/60 text-rose-300' 
            : 'bg-gray-800/60 border-gray-700 text-gray-300'
        }`}>
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-400">Pancreas:</span>
            {highRisk ? (
              <span className="flex items-center gap-1 text-rose-400 font-semibold">
                <ShieldAlert className="w-3 h-3" /> ALERT
              </span>
            ) : (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <CheckCircle2 className="w-3 h-3" /> Normal
              </span>
            )}
          </div>
          <p className="text-[11px] text-gray-400 mt-1 truncate">
            {highRisk ? "High excursion stress" : "Endocrine balance active"}
          </p>
        </div>

        {/* Circulatory Velocity */}
        <div className="p-2.5 bg-gray-800/60 border border-gray-700 rounded-lg text-gray-300">
          <div className="flex items-center justify-between">
            <span className="font-medium text-gray-400">Vascular Flow:</span>
            <span className="font-semibold text-sky-400">
              {currentGlucose > 0 ? `${currentGlucose.toFixed(0)} mg/dL` : '--'}
            </span>
          </div>
          <p className="text-[11px] text-gray-400 mt-1 truncate">
            Forecast (+120m): <span className="text-gray-200">{predictedGlucose > 0 ? `${predictedGlucose.toFixed(0)} mg/dL` : 'Warming up'}</span>
          </p>
        </div>
      </div>

      {/* Footer Status Pill */}
      <div className="mt-2 text-[11px] text-center text-gray-400 flex items-center justify-center gap-2">
        <span className="inline-block w-1.5 h-1.5 rounded-full bg-emerald-400" />
        Synchronized with Unity 3D Desktop Engine
      </div>
    </div>
  );
}
