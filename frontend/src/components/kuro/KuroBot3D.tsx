import { useRef, useEffect, useState, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

// ---------- Types ----------

interface BotProps {
  mousePosition: { x: number; y: number };
  interactive: boolean;
}

type BotSize = "small" | "medium" | "large";

export interface KuroBot3DProps {
  className?: string;
  interactive?: boolean;
  size?: BotSize;
}

// ---------- Size presets ----------

const SIZE_CONFIG: Record<BotSize, { width: string; height: string; minHeight: string }> = {
  small:  { width: "w-48 md:w-64",       height: "h-48 md:h-64",       minHeight: "150px" },
  medium: { width: "w-64 md:w-80",       height: "h-64 md:h-80",       minHeight: "200px" },
  large:  { width: "w-80 md:w-96 h-80",  height: "md:h-96",            minHeight: "200px" },
};

// ---------- Bot (inner Three.js scene) ----------

const Bot = ({ mousePosition, interactive }: BotProps) => {
  const headRef = useRef<THREE.Group>(null);
  const bodyRef = useRef<THREE.Group>(null);
  const glowRingRef = useRef<THREE.Mesh>(null);
  const chestLightRef = useRef<THREE.Mesh>(null);
  const targetRotation = useRef({ x: 0, y: 0 });

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    if (headRef.current) {
      if (interactive) {
        // Cursor-following head rotation
        targetRotation.current.x = mousePosition.y * 0.4;
        targetRotation.current.y = mousePosition.x * 0.5;
      } else {
        // Subtle breathing rotation when idle
        targetRotation.current.x = Math.sin(t * 0.4) * 0.035;
        targetRotation.current.y = Math.sin(t * 0.3) * 0.035;
      }

      headRef.current.rotation.x = THREE.MathUtils.lerp(
        headRef.current.rotation.x,
        targetRotation.current.x,
        0.08
      );
      headRef.current.rotation.y = THREE.MathUtils.lerp(
        headRef.current.rotation.y,
        targetRotation.current.y,
        0.08
      );
    }

    // Body sway
    if (bodyRef.current) {
      if (interactive) {
        bodyRef.current.rotation.y = THREE.MathUtils.lerp(
          bodyRef.current.rotation.y,
          mousePosition.x * 0.15,
          0.03
        );
      } else {
        bodyRef.current.rotation.y = THREE.MathUtils.lerp(
          bodyRef.current.rotation.y,
          Math.sin(t * 0.25) * 0.04,
          0.03
        );
      }
    }

    // Glow ring pulse (scale + emissive intensity)
    if (glowRingRef.current) {
      const pulse = 1 + Math.sin(t * 2.1) * 0.05; // scale 1 -> 1.05 -> 1
      glowRingRef.current.scale.set(pulse, pulse, 1);
      const mat = glowRingRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 2 + Math.sin(t * 2.1) * 0.6; // 1.4 -> 2.6
    }

    // Chest light pulse
    if (chestLightRef.current) {
      const mat = chestLightRef.current.material as THREE.MeshStandardMaterial;
      mat.emissiveIntensity = 3 + Math.sin(t * 1.8) * 0.8;
    }
  });

  // Idle mode gets stronger float to compensate for no cursor interaction
  const floatSpeed = interactive ? 2 : 1.5;
  const floatRotation = interactive ? 0.2 : 0.15;
  const floatIntensity = interactive ? 0.5 : 0.8;

  return (
    <Float speed={floatSpeed} rotationIntensity={floatRotation} floatIntensity={floatIntensity}>
      <group ref={bodyRef} position={[0, -0.8, 0]}>
        {/* Body */}
        <mesh position={[0, 0, 0]}>
          <capsuleGeometry args={[0.6, 0.8, 16, 32]} />
          <meshStandardMaterial
            color="#1a1a2e"
            metalness={0.8}
            roughness={0.2}
          />
        </mesh>

        {/* Body glow ring */}
        <mesh ref={glowRingRef} position={[0, 0.2, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.65, 0.03, 16, 32]} />
          <meshStandardMaterial
            color="#00d4ff"
            emissive="#00d4ff"
            emissiveIntensity={2}
          />
        </mesh>

        {/* Chest light */}
        <mesh ref={chestLightRef} position={[0, 0.1, 0.55]}>
          <circleGeometry args={[0.15, 32]} />
          <meshStandardMaterial
            color="#00d4ff"
            emissive="#00d4ff"
            emissiveIntensity={3}
          />
        </mesh>

        {/* Arms */}
        <group position={[-0.75, 0.2, 0]}>
          <mesh>
            <capsuleGeometry args={[0.12, 0.5, 8, 16]} />
            <meshStandardMaterial
              color="#1a1a2e"
              metalness={0.8}
              roughness={0.2}
            />
          </mesh>
          <mesh position={[0, 0.3, 0]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshStandardMaterial
              color="#a855f7"
              emissive="#a855f7"
              emissiveIntensity={2}
            />
          </mesh>
        </group>

        <group position={[0.75, 0.2, 0]}>
          <mesh>
            <capsuleGeometry args={[0.12, 0.5, 8, 16]} />
            <meshStandardMaterial
              color="#1a1a2e"
              metalness={0.8}
              roughness={0.2}
            />
          </mesh>
          <mesh position={[0, 0.3, 0]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshStandardMaterial
              color="#a855f7"
              emissive="#a855f7"
              emissiveIntensity={2}
            />
          </mesh>
        </group>

        {/* Head group */}
        <group ref={headRef} position={[0, 1.1, 0]}>
          {/* Helmet/Head base */}
          <mesh>
            <sphereGeometry args={[0.55, 32, 32]} />
            <meshStandardMaterial
              color="#1a1a2e"
              metalness={0.9}
              roughness={0.1}
            />
          </mesh>

          {/* Visor/Face plate with glow */}
          <mesh position={[0, 0, 0.35]}>
            <sphereGeometry args={[0.4, 32, 32, 0, Math.PI * 2, 0, Math.PI / 2]} />
            <MeshDistortMaterial
              color="#ff1493"
              emissive="#ff1493"
              emissiveIntensity={0.8}
              transparent
              opacity={0.9}
              metalness={0.3}
              roughness={0.1}
              distort={0.1}
              speed={2}
            />
          </mesh>

          {/* Eye glow - left */}
          <mesh position={[-0.15, 0.05, 0.5]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshStandardMaterial
              color="#00ffff"
              emissive="#00ffff"
              emissiveIntensity={4}
            />
          </mesh>

          {/* Eye glow - right */}
          <mesh position={[0.15, 0.05, 0.5]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshStandardMaterial
              color="#00ffff"
              emissive="#00ffff"
              emissiveIntensity={4}
            />
          </mesh>

          {/* Antenna */}
          <group position={[0, 0.5, 0]}>
            <mesh>
              <cylinderGeometry args={[0.02, 0.02, 0.3, 8]} />
              <meshStandardMaterial
                color="#1a1a2e"
                metalness={0.8}
                roughness={0.2}
              />
            </mesh>
            <mesh position={[0, 0.2, 0]}>
              <sphereGeometry args={[0.06, 16, 16]} />
              <meshStandardMaterial
                color="#00d4ff"
                emissive="#00d4ff"
                emissiveIntensity={3}
              />
            </mesh>
          </group>

          {/* Ear pieces */}
          <mesh position={[-0.55, 0, 0]}>
            <boxGeometry args={[0.1, 0.2, 0.15]} />
            <meshStandardMaterial
              color="#a855f7"
              emissive="#a855f7"
              emissiveIntensity={1}
            />
          </mesh>
          <mesh position={[0.55, 0, 0]}>
            <boxGeometry args={[0.1, 0.2, 0.15]} />
            <meshStandardMaterial
              color="#a855f7"
              emissive="#a855f7"
              emissiveIntensity={1}
            />
          </mesh>
        </group>
      </group>
    </Float>
  );
};

// ---------- Particles ----------

// Pre-generated particle data (stable across renders)
const PARTICLE_DATA = [...Array(16)].map((_, i) => {
  const angle = (i / 16) * Math.PI * 2;
  const radius = 1.8 + Math.random() * 0.7;
  const y = (Math.random() - 0.5) * 2;
  const size = 0.025 + Math.random() * 0.03;
  const speedMult = 0.7 + Math.random() * 0.6; // randomize orbital speed
  const phaseOffset = Math.random() * Math.PI * 2; // randomize fade phase
  const yDrift = 0.15 + Math.random() * 0.2; // vertical drift amplitude
  return { angle, radius, y, size, speedMult, phaseOffset, yDrift };
});

const Particles = () => {
  const refs = useRef<(THREE.Mesh | null)[]>([]);

  useFrame(({ clock }) => {
    const t = clock.getElapsedTime();

    refs.current.forEach((mesh, i) => {
      if (!mesh) return;
      const p = PARTICLE_DATA[i];

      // Individual orbital rotation at slightly different speeds
      const currentAngle = p.angle + t * 0.1 * p.speedMult;
      mesh.position.x = Math.cos(currentAngle) * p.radius;
      mesh.position.z = Math.sin(currentAngle) * p.radius;

      // Gentle vertical drift
      mesh.position.y = p.y + Math.sin(t * 0.5 + p.phaseOffset) * p.yDrift;

      // Fade in/out
      const mat = mesh.material as THREE.MeshStandardMaterial;
      const fade = 0.5 + Math.sin(t * 0.8 + p.phaseOffset) * 0.5; // 0 -> 1
      mat.opacity = fade;
      mat.emissiveIntensity = 1 + fade * 2;
    });
  });

  return (
    <group>
      {PARTICLE_DATA.map((p, i) => (
        <mesh
          key={i}
          ref={(el) => { refs.current[i] = el; }}
          position={[
            Math.cos(p.angle) * p.radius,
            p.y,
            Math.sin(p.angle) * p.radius,
          ]}
        >
          <sphereGeometry args={[p.size, 8, 8]} />
          <meshStandardMaterial
            color={i % 2 === 0 ? "#00d4ff" : "#a855f7"}
            emissive={i % 2 === 0 ? "#00d4ff" : "#a855f7"}
            emissiveIntensity={2}
            transparent
            opacity={1}
          />
        </mesh>
      ))}
    </group>
  );
};

// ---------- Main component ----------

const KuroBot3D = ({
  className = "",
  interactive = true,
  size = "large",
}: KuroBot3DProps) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });
  const [visible, setVisible] = useState(false);

  // Only register mouse listener when interactive
  useEffect(() => {
    if (!interactive) return;

    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      const x = (e.clientX - centerX) / (window.innerWidth / 2);
      const y = (e.clientY - centerY) / (window.innerHeight / 2);

      setMousePosition({
        x: Math.max(-1, Math.min(1, x)),
        y: Math.max(-1, Math.min(1, y)),
      });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, [interactive]);

  // Entrance animation trigger
  useEffect(() => {
    const raf = requestAnimationFrame(() => setVisible(true));
    return () => cancelAnimationFrame(raf);
  }, []);

  const sizeClasses = SIZE_CONFIG[size];

  return (
    <div
      ref={containerRef}
      className={`${sizeClasses.width} ${sizeClasses.height} ${className}`}
      style={{
        minHeight: sizeClasses.minHeight,
        // Entrance animation via CSS transform (GPU-accelerated)
        transform: visible ? "scale(1) translateY(0)" : "scale(0.7) translateY(20px)",
        opacity: visible ? 1 : 0,
        transition: "transform 0.7s cubic-bezier(0.22, 1, 0.36, 1), opacity 0.7s cubic-bezier(0.22, 1, 0.36, 1)",
        willChange: "transform, opacity",
      }}
    >
      <Canvas
        camera={{ position: [0, 0.3, 4.5], fov: 50 }}
        style={{ background: "transparent", width: "100%", height: "100%" }}
        gl={{ alpha: true, antialias: true }}
      >
        <ambientLight intensity={0.3} />
        <pointLight position={[5, 5, 5]} intensity={1} color="#00d4ff" />
        <pointLight position={[-5, 3, 5]} intensity={0.8} color="#a855f7" />
        <spotLight
          position={[0, 5, 0]}
          intensity={0.5}
          angle={0.5}
          penumbra={1}
          color="#ffffff"
        />

        <Bot mousePosition={mousePosition} interactive={interactive} />
        <Particles />

        <Environment preset="night" />
      </Canvas>
    </div>
  );
};

export default KuroBot3D;
