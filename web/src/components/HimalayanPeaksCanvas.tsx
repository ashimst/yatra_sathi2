import React, { useEffect, useRef, useState } from 'react';
import * as THREE from 'three';
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js';
import { RotateCcw, Play, Pause, Mountain } from 'lucide-react';

export interface HimalayanPeaksCanvasProps {
  className?: string;
  interactive?: boolean;
}

export const HimalayanPeaksCanvas: React.FC<HimalayanPeaksCanvasProps> = ({
  className = '',
  interactive = true,
}) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const resetCameraRef = useRef<(() => void) | null>(null);
  const [isRotating, setIsRotating] = useState(true);
  const isRotatingRef = useRef(isRotating);

  useEffect(() => {
    isRotatingRef.current = isRotating;
  }, [isRotating]);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 480;

    // ── 1. SCENE SETUP ───────────────────────────────────────────────
    const scene = new THREE.Scene();

    // Warm golden hour sunset sky gradient
    const createSkyTexture = () => {
      const canvas = document.createElement('canvas');
      canvas.width = 512;
      canvas.height = 1024;
      const ctx = canvas.getContext('2d');
      if (!ctx) return null;
      const grad = ctx.createLinearGradient(0, 0, 0, 1024);
      grad.addColorStop(0.0, '#FFB050');   // Warm golden sky
      grad.addColorStop(0.25, '#FFA058');  // Peachy alpine glow
      grad.addColorStop(0.5, '#FF8D62');   // Coral sunset
      grad.addColorStop(0.72, '#FFB084');  // Soft rosy orange
      grad.addColorStop(0.88, '#FFD2B0');  // Peach horizon
      grad.addColorStop(1.0, '#FFE6D2');   // Warm valley haze
      ctx.fillStyle = grad;
      ctx.fillRect(0, 0, 512, 1024);
      const texture = new THREE.CanvasTexture(canvas);
      texture.colorSpace = THREE.SRGBColorSpace;
      return texture;
    };

    const skyTexture = createSkyTexture();
    if (skyTexture) {
      scene.background = skyTexture;
    } else {
      scene.background = new THREE.Color('#FFB890');
    }

    scene.fog = new THREE.Fog('#FFD2B0', 12, 54);

    // ── 2. CAMERA SETUP ──────────────────────────────────────────────
    // Balanced perspective showcasing:
    // Mountain Range (top) -> High Sacred Stupas & Flags (upper ridge) -> Low Pagoda Temples (foothills) -> Green Terraces
    const camera = new THREE.PerspectiveCamera(38, width / height, 0.1, 160);
    const defaultCamPos = new THREE.Vector3(0.0, 4.8, 16.5);
    const defaultTarget = new THREE.Vector3(0.0, 3.2, 0.4);
    camera.position.copy(defaultCamPos);
    camera.lookAt(defaultTarget);

    // ── 3. WEBGL RENDERER ─────────────────────────────────────────────
    let renderer: THREE.WebGLRenderer;
    try {
      renderer = new THREE.WebGLRenderer({
        antialias: true,
        alpha: false,
        powerPreference: 'high-performance',
      });
    } catch (e) {
      console.warn('WebGL initialization failed:', e);
      return;
    }
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    renderer.shadowMap.enabled = true;
    renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    renderer.toneMapping = THREE.ACESFilmicToneMapping;
    renderer.toneMappingExposure = 1.25;
    renderer.outputColorSpace = THREE.SRGBColorSpace;
    container.appendChild(renderer.domElement);

    // ── 4. WARM ALPINE LIGHTING ───────────────────────────────────────
    const ambientLight = new THREE.AmbientLight('#FFE8D6', 1.85);
    scene.add(ambientLight);

    // Golden Himalayan sun striking from the east
    const sunLight = new THREE.DirectionalLight('#FFD090', 2.8);
    sunLight.position.set(13.0, 16.0, 8.0);
    sunLight.castShadow = true;
    sunLight.shadow.mapSize.width = 2048;
    sunLight.shadow.mapSize.height = 2048;
    sunLight.shadow.camera.near = 0.5;
    sunLight.shadow.camera.far = 50;
    sunLight.shadow.camera.left = -16;
    sunLight.shadow.camera.right = 16;
    sunLight.shadow.camera.top = 16;
    sunLight.shadow.camera.bottom = -16;
    sunLight.shadow.bias = -0.0002;
    sunLight.shadow.radius = 2.5;
    scene.add(sunLight);

    // Warm mountain fill light
    const fillLight = new THREE.DirectionalLight('#FFAE85', 1.4);
    fillLight.position.set(-10.0, 8.0, -4.0);
    scene.add(fillLight);

    // Soft upward bounce from the green alpine slopes
    const groundBounce = new THREE.HemisphereLight('#FFF5E8', '#6A8050', 0.65);
    scene.add(groundBounce);

    // Root Group
    const worldGroup = new THREE.Group();
    scene.add(worldGroup);

    // ── 5. TOPOGRAPHIC HIERARCHY ─────────────────────────────────────
    const mountainGridX = 180;
    const mountainGridZ = 180;
    const mountainWidth = 30.0;
    const mountainDepth = 26.0;

    const mountainGeo = new THREE.PlaneGeometry(
      mountainWidth,
      mountainDepth,
      mountainGridX - 1,
      mountainGridZ - 1
    );
    mountainGeo.rotateX(-Math.PI / 2);

    const posAttr = mountainGeo.attributes.position as THREE.BufferAttribute;
    const vertexColors = new Float32Array(posAttr.count * 3);

    // Procedural Elevation: Towering Alpine Range -> Stupa Ridge -> Lower Temple Foothills -> Rolling Green Terraces
    const getElevation = (x: number, z: number): number => {
      let h = 0.2;

      // 1. HORIZON HIMALAYAN MOUNTAIN RANGE (z < 0.6) - MAJESTIC TOWERING PEAKS
      if (z < 0.6) {
        // Peak A: Central Grand Pyramid (Everest / Machhapuchhre scale summit)
        const p1Dist = Math.hypot(x - 1.2, z - (-5.2));
        const p1 = 14.0 * Math.exp(-p1Dist * 0.35);

        // Peak B: Western Soaring Horn
        const p2Dist = Math.hypot(x - (-5.6), z - (-5.6));
        const p2 = 13.0 * Math.exp(-p2Dist * 0.34);

        // Peak C: Eastern Twin Massif
        const p3Dist = Math.hypot(x - 6.2, z - (-5.0));
        const p3 = 12.5 * Math.exp(-p3Dist * 0.35);

        // Peak D: Far Western Needle
        const p4Dist = Math.hypot(x - (-10.2), z - (-6.2));
        const p4 = 11.2 * Math.exp(-p4Dist * 0.38);

        // Peak E: Far Eastern Ridge
        const p5Dist = Math.hypot(x - 10.0, z - (-5.8));
        const p5 = 10.8 * Math.exp(-p5Dist * 0.38);

        // Alpine Connecting Ridges
        const ridgeZ = -5.4 + Math.sin(x * 0.45) * 0.8;
        const distToRidge = Math.abs(z - ridgeZ);
        const ridgeSpine = 8.8 * Math.exp(-distToRidge * distToRidge / 3.0) * (1.0 + 0.22 * Math.cos(x * 0.85));

        // Couloirs & Fluting
        const flutes = Math.sin(x * 2.4 + z * 1.8) * 0.45 * Math.exp(-(z + 3.2) * 0.18);
        const microFlutes = Math.cos(x * 6.5) * 0.18 * Math.exp(-(z + 3.2) * 0.25);

        const mountainMass = Math.max(p1, p2, p3, p4, p5, ridgeSpine) + flutes + microFlutes;
        h = Math.max(h, mountainMass);
      }

      // 2. MIDGROUND ALPINE STUPA RIDGE (z between -1.2 and 1.4)
      // Elevated scenic ridge for stupas, kept comfortably below the towering mountains
      if (z >= -1.2 && z < 1.4) {
        const stupaRidgeProgress = (z - (-1.2)) / 2.6;
        const ridgeBase = 2.7 - stupaRidgeProgress * 0.8; // Reaches ~1.9
        const spurWave = Math.sin(x * 0.55 + z * 0.7) * 0.32 + Math.cos(x * 1.1) * 0.16;
        h = Math.max(h, ridgeBase + spurWave);
      }

      // 3. LOWER TEMPLE FOOTHILLS (z between 1.4 and 4.2) - LOWER ELEVATION
      if (z >= 1.4 && z < 4.2) {
        const foothillProgress = (z - 1.4) / 2.8;
        const foothillBase = 1.6 - foothillProgress * 0.7; // Reaches ~0.9
        const terraces = Math.sin(x * 0.75) * 0.18 + Math.cos(z * 1.2) * 0.12;
        h = Math.max(h, foothillBase + terraces);
      }

      // 4. FOREGROUND SERENE ALPINE MEADOWS (z >= 4.0) - NO CITY, PURE ROLLING MEADOWS
      if (z >= 4.0) {
        const meadowProgress = (z - 4.0) / 8.0;
        const meadowBase = 0.8 - meadowProgress * 0.45;
        const rollingHills = Math.sin(x * 0.65 + z * 0.45) * 0.14 + Math.cos(x * 1.3 - z * 0.6) * 0.08;
        h = Math.max(h, meadowBase + rollingHills);
      }

      return Math.max(0.12, h);
    };

    // Apply Elevation to Vertices
    for (let i = 0; i < posAttr.count; i++) {
      const vx = posAttr.getX(i);
      const vz = posAttr.getZ(i);
      const vy = getElevation(vx, vz);
      posAttr.setY(i, vy);
    }
    mountainGeo.computeVertexNormals();

    // ── 6. PAINTERLY HIMALAYAN COLOR PALETTE ─────────────────────────
    const normAttr = mountainGeo.attributes.normal as THREE.BufferAttribute;

    const colorSnowWarm = new THREE.Color('#FFF8EE');      // Luminous summit snow
    const colorSnowGolden = new THREE.Color('#FFECD5');    // Morning light snow
    const colorRockWarm = new THREE.Color('#785848');      // Slate granite
    const colorRockDeep = new THREE.Color('#50382E');      // Shadow crags
    const colorTundraGold = new THREE.Color('#A89368');    // High moraine
    const colorHighMeadow = new THREE.Color('#6E8E50');    // Stupa ridge grass
    const colorLushMeadow = new THREE.Color('#50783E');    // Temple slope grass
    const colorValleyMeadow = new THREE.Color('#466E38');  // Foreground lush meadow
    const colorTrailSoil = new THREE.Color('#8F6246');     // Mountain trail earth

    for (let i = 0; i < posAttr.count; i++) {
      const vx = posAttr.getX(i);
      const vy = posAttr.getY(i);
      const vz = posAttr.getZ(i);
      const ny = normAttr.getY(i);

      const finalColor = new THREE.Color();

      if (vy > 4.4) {
        // Snowbound Summits (Majestic towering peaks)
        const isGentleSlope = ny > 0.48;
        const isHighestPeak = vy > 9.5;

        if (isHighestPeak) {
          finalColor.lerpColors(colorSnowWarm, colorSnowGolden, 0.4);
        } else if (isGentleSlope) {
          finalColor.lerpColors(colorSnowWarm, colorSnowGolden, 0.7);
        } else {
          const rockMix = (Math.sin(vx * 3.5 + vy * 2.0) + 1.0) * 0.5;
          finalColor.lerpColors(colorRockWarm, colorRockDeep, rockMix);
        }
      } else if (vy > 2.1) {
        // High Stupa Ridge (Alpine tundra, rocky outcrops & golden moss)
        if (ny > 0.60 && vy > 2.8) {
          finalColor.lerpColors(colorHighMeadow, colorTundraGold, 0.4);
        } else if (ny > 0.40) {
          finalColor.lerpColors(colorHighMeadow, colorRockWarm, 0.35);
        } else {
          finalColor.lerpColors(colorRockWarm, colorRockDeep, 0.65);
        }
      } else if (vy > 1.1) {
        // Lower Temple Foothills (Lush alpine hillside & pine soil)
        const grassVar = (Math.sin(vx * 1.6 + vz * 1.8) + 1.0) * 0.5;
        finalColor.lerpColors(colorHighMeadow, colorLushMeadow, grassVar);
      } else {
        // Foreground Gentle Meadows (Serene green valley, no city)
        const meadowVar = (Math.sin(vx * 1.8 + vz * 1.2) + 1.0) * 0.5;
        finalColor.lerpColors(colorLushMeadow, colorValleyMeadow, meadowVar);

        // Subtle mountain dirt path
        const pathDist = Math.abs(vx - Math.sin(vz * 0.8) * 1.4);
        if (pathDist < 0.35) {
          finalColor.lerp(colorTrailSoil, (1.0 - pathDist / 0.35) * 0.55);
        }
      }

      vertexColors[i * 3] = finalColor.r;
      vertexColors[i * 3 + 1] = finalColor.g;
      vertexColors[i * 3 + 2] = finalColor.b;
    }

    mountainGeo.setAttribute('color', new THREE.BufferAttribute(vertexColors, 3));

    const mountainMat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      roughness: 0.8,
      metalness: 0.04,
      flatShading: false,
      emissive: new THREE.Color('#FFECD4'),
      emissiveIntensity: 0.12,
    });

    const mountainMesh = new THREE.Mesh(mountainGeo, mountainMat);
    mountainMesh.castShadow = true;
    mountainMesh.receiveShadow = true;
    worldGroup.add(mountainMesh);

    // ── 7. REUSABLE ARCHITECTURAL MATERIALS ───────────────────────────
    const whitewashMat = new THREE.MeshStandardMaterial({ color: 0xFDFBF7, roughness: 0.55 });
    const goldMat = new THREE.MeshStandardMaterial({ color: 0xF5BA42, roughness: 0.28, metalness: 0.88 });
    const stonePlinthMat = new THREE.MeshStandardMaterial({ color: 0x988A7A, roughness: 0.9 });
    const terracottaBrickMat = new THREE.MeshStandardMaterial({ color: 0x9E4326, roughness: 0.85 });
    const pagodaRoofTileMat = new THREE.MeshStandardMaterial({ color: 0x8C371E, roughness: 0.65 });
    const carvedWoodMat = new THREE.MeshStandardMaterial({ color: 0x3A2417, roughness: 0.9 });
    const sanctumGlowMat = new THREE.MeshStandardMaterial({
      color: 0xFFE082,
      emissive: 0xFFA000,
      emissiveIntensity: 0.65,
      roughness: 0.35
    });
    const pineGreenMat = new THREE.MeshStandardMaterial({ color: 0x2A4C25, roughness: 0.8 });
    const pineTrunkMat = new THREE.MeshStandardMaterial({ color: 0x3E291C, roughness: 0.95 });

    // ── 8. SACRED BUDDHIST STUPAS (ON MIDGROUND ALPINE RIDGES) ─────
    const stupaTopPoints: THREE.Vector3[] = [];

    const createStupa = (x: number, z: number, scale = 1.0) => {
      const stupaGroup = new THREE.Group();
      const y = getElevation(x, z);

      // Build stupa components with exact, gap-free relative coordinates in unit scale:

      // Tier 1: Lower Stepped Square Plinth
      const plinth1 = new THREE.Mesh(new THREE.BoxGeometry(1.5, 0.22, 1.5), whitewashMat);
      plinth1.position.y = 0.11;
      plinth1.castShadow = true;
      plinth1.receiveShadow = true;
      stupaGroup.add(plinth1);

      // Tier 2: Upper Stepped Square Plinth
      const plinth2 = new THREE.Mesh(new THREE.BoxGeometry(1.2, 0.18, 1.2), whitewashMat);
      plinth2.position.y = 0.22 + 0.09; // 0.31
      plinth2.castShadow = true;
      stupaGroup.add(plinth2);

      // Tier 3: Circular Lotus Molded Base
      const plinth3 = new THREE.Mesh(new THREE.CylinderGeometry(0.56, 0.58, 0.10, 16), whitewashMat);
      plinth3.position.y = 0.40 + 0.05; // 0.45
      plinth3.castShadow = true;
      stupaGroup.add(plinth3);

      // White Hemispherical Dome (Garbha / Bumpa)
      // Standard half-sphere from equator to top pole
      const domeR = 0.52;
      const domeGeo = new THREE.SphereGeometry(domeR, 18, 14, 0, Math.PI * 2, 0, Math.PI * 0.5);
      const dome = new THREE.Mesh(domeGeo, whitewashMat);
      dome.position.y = 0.50; // Sits flush on plinth3; dome top at 0.50 + 0.52 = 1.02
      dome.castShadow = true;
      stupaGroup.add(dome);

      // Square Base Collar below Harmika
      const harmikaBaseH = 0.06;
      const harmikaBase = new THREE.Mesh(new THREE.BoxGeometry(0.36, harmikaBaseH, 0.36), goldMat);
      harmikaBase.position.y = 1.02 + harmikaBaseH * 0.5; // 1.05
      harmikaBase.castShadow = true;
      stupaGroup.add(harmikaBase);
      // Top of harmika base is at 1.08

      // Square Golden Harmika (Cube of Wisdom & All-Seeing Eyes)
      const harmikaH = 0.28;
      const harmika = new THREE.Mesh(new THREE.BoxGeometry(0.33, harmikaH, 0.33), goldMat);
      harmika.position.y = 1.08 + harmikaH * 0.5; // 1.22
      harmika.castShadow = true;
      stupaGroup.add(harmika);
      // Top of harmika is at 1.08 + 0.28 = 1.36

      // Red Wisdom Eyes of Buddha Band
      const eyeBand = new THREE.Mesh(
        new THREE.BoxGeometry(0.34, 0.08, 0.34),
        new THREE.MeshBasicMaterial({ color: 0x9D3E19 })
      );
      eyeBand.position.y = harmika.position.y;
      stupaGroup.add(eyeBand);

      // Lotus Collar / Stepped Spire Tray directly capping Harmika (Eliminates any gap)
      const spireTrayH = 0.06;
      const spireTray = new THREE.Mesh(new THREE.CylinderGeometry(0.24, 0.28, spireTrayH, 12), goldMat);
      spireTray.position.y = 1.36 + spireTrayH * 0.5; // 1.39
      spireTray.castShadow = true;
      stupaGroup.add(spireTray);
      // Top of spire tray is at 1.36 + 0.06 = 1.42

      // 13-Tiered Golden Conical Spire (Chudamani)
      // Cone sits seamlessly on top of the spire tray
      const spireH = 0.82;
      const spire = new THREE.Mesh(new THREE.ConeGeometry(0.22, spireH, 14), goldMat);
      spire.position.y = 1.42 + spireH * 0.5; // 1.83
      spire.castShadow = true;
      stupaGroup.add(spire);
      // Top apex of cone is at 1.42 + 0.82 = 2.24

      // Golden Lotus Parasol (Chattra)
      const umbrellaH = 0.04;
      const umbrella = new THREE.Mesh(new THREE.CylinderGeometry(0.14, 0.12, umbrellaH, 12), goldMat);
      umbrella.position.y = 2.24 + umbrellaH * 0.5; // 2.26
      umbrella.castShadow = true;
      stupaGroup.add(umbrella);

      // Sun, Moon & Flaming Jewel Pinnacle (Gajur Finial)
      const finialR = 0.08;
      const finial = new THREE.Mesh(new THREE.SphereGeometry(finialR, 8, 8), goldMat);
      finial.position.y = 2.28 + finialR; // 2.36
      finial.castShadow = true;
      stupaGroup.add(finial);

      // Uniform group scaling ensures 100% gap-free cohesion at any scale
      stupaGroup.scale.set(scale, scale, scale);
      stupaGroup.position.set(x, y, z);
      worldGroup.add(stupaGroup);

      const topPos = new THREE.Vector3(x, y + 2.36 * scale, z);
      stupaTopPoints.push(topPos);
      return topPos;
    };

    // Stupas positioned on the midground alpine ridge, comfortably below the towering mountain range:
    // 1. Central Ridge Stupa (Majestic lookout)
    createStupa(-1.8, -0.4, 0.95);
    // 2. High Eastern Ridge Stupa
    createStupa(2.8, -0.3, 0.88);
    // 3. Western Mountain Pass Stupa
    createStupa(-5.4, -0.6, 0.80);
    // 4. Trailside Chorten on the descent spur
    createStupa(0.6, 0.6, 0.68);

    // ── 9. MULTI-COLORED TIBETAN PRAYER FLAGS ─────────────────────────
    const flagMaterials = [
      new THREE.MeshStandardMaterial({ color: 0x1E40AF, roughness: 0.5, side: THREE.DoubleSide }), // Blue (Sky)
      new THREE.MeshStandardMaterial({ color: 0xF8FAFC, roughness: 0.45, side: THREE.DoubleSide }), // White (Air)
      new THREE.MeshStandardMaterial({ color: 0xDC2626, roughness: 0.5, side: THREE.DoubleSide }), // Red (Fire)
      new THREE.MeshStandardMaterial({ color: 0x16A34A, roughness: 0.5, side: THREE.DoubleSide }), // Green (Water)
      new THREE.MeshStandardMaterial({ color: 0xCA8A04, roughness: 0.5, side: THREE.DoubleSide }), // Yellow (Earth)
    ];

    interface AnimatedFlag {
      mesh: THREE.Mesh;
      baseRot: THREE.Euler;
      phase: number;
    }
    const animatedFlags: AnimatedFlag[] = [];

    const createTimberPole = (x: number, z: number, h: number) => {
      const y = getElevation(x, z);
      const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.03, 0.04, h, 6), carvedWoodMat);
      pole.position.set(x, y + h / 2, z);
      worldGroup.add(pole);
      return new THREE.Vector3(x, y + h * 0.95, z);
    };

    // Flag line with realistic wind-catching catenary sag
    const createFlagLine = (pStart: THREE.Vector3, pEnd: THREE.Vector3, count: number, sag: number) => {
      const curvePts: THREE.Vector3[] = [];
      const steps = 14;
      for (let s = 0; s <= steps; s++) {
        const t = s / steps;
        const pt = new THREE.Vector3().lerpVectors(pStart, pEnd, t);
        pt.y -= Math.sin(t * Math.PI) * sag;
        curvePts.push(pt);
      }
      const curve = new THREE.CatmullRomCurve3(curvePts);

      const rope = new THREE.Mesh(
        new THREE.TubeGeometry(curve, 18, 0.007, 4, false),
        new THREE.MeshStandardMaterial({ color: 0xC2A47F, roughness: 0.9 })
      );
      worldGroup.add(rope);

      for (let f = 0; f < count; f++) {
        const t = (f + 0.5) / count;
        const pos = curve.getPoint(t);
        const tangent = curve.getTangent(t);

        const flagW = 0.13;
        const flagH = 0.095;
        const fGeo = new THREE.PlaneGeometry(flagW, flagH);
        const fMat = flagMaterials[f % 5];
        const fMesh = new THREE.Mesh(fGeo, fMat);
        fMesh.position.set(pos.x, pos.y - flagH * 0.5, pos.z);

        const angleY = Math.atan2(tangent.x, tangent.z);
        fMesh.rotation.y = angleY;
        worldGroup.add(fMesh);

        animatedFlags.push({
          mesh: fMesh,
          baseRot: fMesh.rotation.clone(),
          phase: f * 0.5 + pStart.x * 2.0,
        });
      }
    };

    // Wooden ridge poles set along the high stupa spurs
    const poleA = createTimberPole(-3.8, -0.6, 1.8);
    const poleB = createTimberPole(0.2, -0.7, 1.8);
    const poleC = createTimberPole(4.5, -0.5, 1.7);
    const poleD = createTimberPole(-6.8, -0.8, 1.6);
    const poleE = createTimberPole(1.6, 0.8, 1.5);
    const poleF = createTimberPole(-2.2, 1.0, 1.6);

    // Strings of prayer flags connecting high stupas and timber poles
    if (stupaTopPoints.length >= 3) {
      // From Great Central Stupa top down to surrounding ridge poles
      createFlagLine(stupaTopPoints[0], poleA, 12, 0.28);
      createFlagLine(stupaTopPoints[0], poleB, 11, 0.27);
      createFlagLine(stupaTopPoints[0], poleF, 10, 0.24);

      // Between Great Stupa and Eastern Stupa across the ridge
      createFlagLine(stupaTopPoints[0], stupaTopPoints[1], 16, 0.35);

      // From Eastern Stupa down to poles
      createFlagLine(stupaTopPoints[1], poleC, 11, 0.25);
      createFlagLine(stupaTopPoints[1], poleE, 10, 0.22);

      // From Western Stupa down to poles
      createFlagLine(stupaTopPoints[2], poleD, 11, 0.24);
      createFlagLine(stupaTopPoints[2], poleA, 11, 0.26);
    }

    // ── 10. AUTHENTIC, SHORTER, LOWER NEPALI PAGODA TEMPLES ───────────
    // Crafted with classic low proportions: broad flared terracotta roofs,
    // carved dark wooden bracket eaves, stone plinths, and warm sanctum lanterns
    const createPagodaTemple = (x: number, z: number, scale = 1.0, tiers = 2) => {
      const templeGroup = new THREE.Group();
      const y = getElevation(x, z);

      // 1. Broad Stepped Stone Plinth
      const plinthH = 0.22 * scale;
      const plinthW = 2.4 * scale;
      const plinth = new THREE.Mesh(new THREE.BoxGeometry(plinthW, plinthH, plinthW), stonePlinthMat);
      plinth.position.y = plinthH * 0.5;
      plinth.castShadow = true;
      plinth.receiveShadow = true;
      templeGroup.add(plinth);

      // Stone steps extending toward front
      const stepW = 0.7 * scale;
      const stepD = 0.45 * scale;
      const steps = new THREE.Mesh(new THREE.BoxGeometry(stepW, 0.12 * scale, stepD), stonePlinthMat);
      steps.position.set(0, 0.06 * scale, plinthW * 0.5 + stepD * 0.4);
      templeGroup.add(steps);

      // 2. Compact, Short Brick Sanctum Body (Garbhagriha)
      // Kept deliberately low and wide for authentic pagoda proportions
      const bodyH = 0.62 * scale;
      const bodyW = 1.35 * scale;
      const body = new THREE.Mesh(new THREE.BoxGeometry(bodyW, bodyH, bodyW), terracottaBrickMat);
      body.position.y = plinthH + bodyH * 0.5;
      body.castShadow = true;
      templeGroup.add(body);

      // Carved Wooden Door Portal with glowing oil lantern interior
      const doorH = 0.45 * scale;
      const doorW = 0.32 * scale;
      const door = new THREE.Mesh(new THREE.BoxGeometry(doorW, doorH, 0.05 * scale), carvedWoodMat);
      door.position.set(0, plinthH + doorH * 0.5, bodyW * 0.5 + 0.01);
      templeGroup.add(door);

      const lanternGlow = new THREE.Mesh(new THREE.BoxGeometry(doorW * 0.65, doorH * 0.7, 0.02 * scale), sanctumGlowMat);
      lanternGlow.position.set(0, plinthH + doorH * 0.5, bodyW * 0.5 + 0.03);
      templeGroup.add(lanternGlow);

      let curY = plinthH + bodyH;

      // 3. Wide, Elegantly Flared Pagoda Roof Tiers
      for (let t = 0; t < tiers; t++) {
        const tierFactor = 1.0 - t * 0.32;
        const roofBaseW = 2.5 * scale * tierFactor; // Generous overhanging eaves
        const roofTopW = 1.0 * scale * tierFactor;
        const roofH = 0.32 * scale * tierFactor;   // Low, gentle pitch

        // Overhanging pagoda roof (frustum pyramid)
        const roofGeo = new THREE.CylinderGeometry(roofTopW * 0.5, roofBaseW * 0.5, roofH, 4);
        roofGeo.rotateY(Math.PI / 4);
        const roof = new THREE.Mesh(roofGeo, pagodaRoofTileMat);
        roof.position.y = curY + roofH * 0.5;
        roof.castShadow = true;
        templeGroup.add(roof);

        // Dark carved timber eave brackets under the roof
        const eaveTrim = new THREE.Mesh(
          new THREE.BoxGeometry(roofBaseW * 0.88, 0.04 * scale, roofBaseW * 0.88),
          carvedWoodMat
        );
        eaveTrim.position.y = curY + 0.02 * scale;
        templeGroup.add(eaveTrim);

        curY += roofH;

        // Intermediate wooden colonnade for multi-tier roofs
        if (t < tiers - 1) {
          const midH = 0.28 * scale * tierFactor;
          const midW = 0.82 * scale * tierFactor;
          const midBody = new THREE.Mesh(new THREE.BoxGeometry(midW, midH, midW), carvedWoodMat);
          midBody.position.y = curY + midH * 0.5;
          midBody.castShadow = true;
          templeGroup.add(midBody);
          curY += midH;
        }
      }

      // 4. Slender Golden Gajur (Pinnacle) on Top Roof
      const pinnacleH = 0.42 * scale;
      const pinnacle = new THREE.Mesh(new THREE.ConeGeometry(0.09 * scale, pinnacleH, 8), goldMat);
      pinnacle.position.y = curY + pinnacleH * 0.5;
      pinnacle.castShadow = true;
      templeGroup.add(pinnacle);

      templeGroup.position.set(x, y, z);
      worldGroup.add(templeGroup);
    };

    // Shorter, lower temples placed in the foothills (elevation ~1.2 to 1.6, well below stupas):
    // 1. Central Two-Tiered Pagoda Shrine (Shorter, broad eaves at elevation ~1.4)
    createPagodaTemple(0.2, 2.6, 1.05, 2);
    // 2. Western Foothill Temple (Charming, low pagoda at elevation ~1.3)
    createPagodaTemple(-3.2, 3.0, 0.95, 2);
    // 3. Eastern Hillside Shrine (Nestled among deodars at elevation ~1.3)
    createPagodaTemple(3.4, 2.8, 0.95, 2);
    // 4. Trailside Stone Sanctuary (Small single-roof shrine at elevation ~1.0)
    createPagodaTemple(-1.2, 3.8, 0.75, 1);

    // ── 11. SCENIC ALPINE PINE & DEODAR TREES ─────────────────────────
    const createPineTree = (x: number, z: number, scale = 1.0) => {
      const treeGroup = new THREE.Group();
      const y = getElevation(x, z);

      // Trunk
      const trunkH = 0.5 * scale;
      const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.04 * scale, 0.07 * scale, trunkH, 5), pineTrunkMat);
      trunk.position.y = trunkH * 0.5;
      trunk.castShadow = true;
      treeGroup.add(trunk);

      // 3 Tiers of Conical Evergreen Needles
      for (let t = 0; t < 3; t++) {
        const coneH = (0.7 - t * 0.12) * scale;
        const coneR = (0.45 - t * 0.08) * scale;
        const foliage = new THREE.Mesh(new THREE.ConeGeometry(coneR, coneH, 6), pineGreenMat);
        foliage.position.y = trunkH + (t * 0.35 + coneH * 0.5) * scale;
        foliage.castShadow = true;
        treeGroup.add(foliage);
      }

      treeGroup.position.set(x, y, z);
      worldGroup.add(treeGroup);
    };

    // Naturally dispersed evergreen groves along temple slopes and foothills (framing the sacred architecture)
    const treePositions = [
      { x: -2.0, z: 2.2, s: 1.15 },
      { x: -1.0, z: 2.0, s: 0.95 },
      { x: 1.8, z: 2.3, s: 1.05 },
      { x: 2.3, z: 2.6, s: 1.2 },
      { x: -4.2, z: 2.7, s: 1.1 },
      { x: 4.6, z: 2.6, s: 1.15 },
      { x: -5.4, z: 3.5, s: 1.25 },
      { x: 5.2, z: 3.4, s: 1.2 },
      { x: -0.4, z: 3.4, s: 0.9 },
      { x: 1.4, z: 3.6, s: 0.95 },
      { x: -2.8, z: 4.4, s: 1.1 },
      { x: 2.8, z: 4.6, s: 1.15 },
      { x: -4.5, z: 5.2, s: 1.2 },
      { x: 4.2, z: 5.4, s: 1.15 },
      { x: -0.8, z: 5.8, s: 0.95 },
      { x: 1.0, z: 6.2, s: 1.0 },
    ];

    treePositions.forEach((tp) => {
      createPineTree(tp.x, tp.z, tp.s);
    });

    // ── 12. ATMOSPHERIC SUNSET MIST PARTICLES ─────────────────────────
    const particleCount = 260;
    const particleGeo = new THREE.BufferGeometry();
    const particlePositions = new Float32Array(particleCount * 3);
    const particleVelocities: number[] = [];

    for (let i = 0; i < particleCount; i++) {
      const i3 = i * 3;
      particlePositions[i3] = (Math.random() - 0.5) * 32;
      particlePositions[i3 + 1] = Math.random() * 12 + 1.5;
      particlePositions[i3 + 2] = (Math.random() - 0.5) * 28;

      particleVelocities.push((Math.random() - 0.5) * 0.01);
      particleVelocities.push(-Math.random() * 0.004);
      particleVelocities.push((Math.random() - 0.5) * 0.008);
    }

    particleGeo.setAttribute('position', new THREE.BufferAttribute(particlePositions, 3));

    const particleMat = new THREE.PointsMaterial({
      size: 0.14,
      color: '#FFFFFF',
      transparent: true,
      opacity: 0.36,
      sizeAttenuation: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false,
    });

    const particleSystem = new THREE.Points(particleGeo, particleMat);
    worldGroup.add(particleSystem);

    // ── 13. INTERACTIVE ORBIT CONTROLS ────────────────────────────────
    const controls = new OrbitControls(camera, renderer.domElement);
    controls.enableDamping = true;
    controls.dampingFactor = 0.06;
    controls.enableRotate = interactive;
    controls.enableZoom = interactive;
    controls.enablePan = interactive;
    controls.target.copy(defaultTarget);

    controls.minDistance = 7.0;
    controls.maxDistance = 28.0;
    controls.maxPolarAngle = Math.PI / 2 - 0.03;
    controls.minPolarAngle = 0.15;

    const preventContextMenu = (e: MouseEvent) => e.preventDefault();
    renderer.domElement.addEventListener('contextmenu', preventContextMenu);

    resetCameraRef.current = () => {
      camera.position.copy(defaultCamPos);
      controls.target.copy(defaultTarget);
      controls.update();
    };

    let isUserInteracting = false;
    controls.addEventListener('start', () => {
      isUserInteracting = true;
    });
    controls.addEventListener('end', () => {
      isUserInteracting = false;
    });

    // ── 14. ANIMATION LOOP ────────────────────────────────────────────
    let animationFrameId: number;
    const clock = new THREE.Clock();

    const animate = () => {
      animationFrameId = requestAnimationFrame(animate);
      const elapsed = clock.getElapsedTime();

      // Gentle ambient camera/world sway
      if (isRotatingRef.current && !isUserInteracting) {
        worldGroup.rotation.y = Math.sin(elapsed * 0.10) * 0.035;
      }

      // Animate atmospheric golden mist
      const positions = particleGeo.attributes.position.array as Float32Array;
      for (let i = 0; i < particleCount; i++) {
        const i3 = i * 3;

        positions[i3] += particleVelocities[i3];
        positions[i3 + 1] += particleVelocities[i3 + 1];
        positions[i3 + 2] += particleVelocities[i3 + 2];

        // Wrap around boundary
        if (positions[i3 + 1] < 0.5) {
          positions[i3 + 1] = 13;
          positions[i3] = (Math.random() - 0.5) * 32;
          positions[i3 + 2] = (Math.random() - 0.5) * 28;
        }

        // Gentle breeze drift
        positions[i3] += Math.sin(elapsed * 0.35 + i) * 0.0015;
      }
      particleGeo.attributes.position.needsUpdate = true;

      // Fluttering Himalayan prayer flags in the mountain wind
      animatedFlags.forEach((item) => {
        const windFlap = Math.sin(elapsed * 4.2 + item.phase) * 0.22;
        const windSide = Math.cos(elapsed * 2.8 + item.phase) * 0.09;
        item.mesh.rotation.x = item.baseRot.x + 0.16 + windFlap;
        item.mesh.rotation.z = item.baseRot.z + windSide;
      });

      controls.update();
      renderer.render(scene, camera);
    };

    animate();

    // ── 15. WINDOW RESIZE ─────────────────────────────────────────────
    const handleResize = () => {
      if (!container) return;
      const newW = container.clientWidth;
      const newH = container.clientHeight;
      camera.aspect = newW / newH;
      camera.updateProjectionMatrix();
      renderer.setSize(newW, newH);
    };

    window.addEventListener('resize', handleResize);

    // ── 16. CLEANUP ───────────────────────────────────────────────────
    return () => {
      cancelAnimationFrame(animationFrameId);
      window.removeEventListener('resize', handleResize);
      renderer.domElement.removeEventListener('contextmenu', preventContextMenu);
      controls.dispose();

      if (container.contains(renderer.domElement)) {
        container.removeChild(renderer.domElement);
      }

      skyTexture?.dispose();
      mountainGeo.dispose();
      mountainMat.dispose();
      whitewashMat.dispose();
      goldMat.dispose();
      stonePlinthMat.dispose();
      terracottaBrickMat.dispose();
      pagodaRoofTileMat.dispose();
      carvedWoodMat.dispose();
      sanctumGlowMat.dispose();
      pineGreenMat.dispose();
      pineTrunkMat.dispose();
      particleGeo.dispose();
      particleMat.dispose();
      flagMaterials.forEach((m) => m.dispose());
      renderer.dispose();
    };
  }, [interactive]);

  return (
    <div
      ref={containerRef}
      className={`relative w-full h-full overflow-hidden select-none ${className}`}
      style={{ touchAction: 'none' }}
      role="region"
      aria-label="Himalayan Sanctuary Diorama - Mountains, Stupas, Flags, Temples, and Alpine Meadows"
    >
      {/* Controls overlay */}
      <div className="absolute top-3 right-3 sm:top-4 sm:right-4 z-20 flex items-center gap-2 pointer-events-auto">
        <button
          onClick={() => setIsRotating(!isRotating)}
          title={isRotating ? 'Pause drift' : 'Resume drift'}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-full text-xs font-medium backdrop-blur-xl bg-white/85 border border-white/70 text-[#201A18] shadow-xs hover:bg-white transition-all cursor-pointer"
        >
          {isRotating ? (
            <>
              <Pause className="w-3.5 h-3.5 text-[#9D3E19]" />
              <span>Drift</span>
            </>
          ) : (
            <>
              <Play className="w-3.5 h-3.5 text-[#1D705C]" />
              <span>Resume</span>
            </>
          )}
        </button>

        <button
          onClick={() => resetCameraRef.current?.()}
          title="Reset viewpoint"
          className="p-1.5 rounded-full bg-white/85 backdrop-blur-xl border border-white/70 text-[#201A18] hover:bg-white shadow-xs transition-all cursor-pointer"
        >
          <RotateCcw className="w-3.5 h-3.5 text-[#56423B]" />
        </button>
      </div>

      {/* Storytelling caption */}
      <div className="absolute bottom-3 left-4 sm:bottom-4 sm:left-5 z-20 pointer-events-none text-left">
        <div className="flex items-center gap-2">
          <Mountain className="w-4 h-4 text-[#9D3E19]" />
          <span className="font-serif-yatra text-xs sm:text-sm font-semibold text-[#201A18]/90">
            Himalayan Panorama • High Stupas &amp; Flags • Alpine Temples &amp; Terraces
          </span>
        </div>
      </div>
    </div>
  );
};
