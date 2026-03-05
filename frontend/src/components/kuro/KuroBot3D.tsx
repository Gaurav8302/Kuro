import { useRef, useEffect, useState, forwardRef } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { Environment, Float, MeshDistortMaterial } from "@react-three/drei";
import * as THREE from "three";

// ═══════════════════════════════════════════════════════════════════════════
// TYPES
// ═══════════════════════════════════════════════════════════════════════════

type ProximityZone = 'idle' | 'near' | 'close';

interface BotBehavior {
  zone: ProximityZone;
  glowIntensity: number;
}

interface BotProps {
  mousePosition: { x: number; y: number };
  behavior?: BotBehavior;
}

const Bot = ({ mousePosition, behavior }: BotProps) => {
  const headRef = useRef<THREE.Group>(null);
  const bodyRef = useRef<THREE.Group>(null);
  const targetRotation = useRef({ x: 0, y: 0 });
  
  // Refs for animated glow values (no re-renders)
  const glowRef = useRef({ 
    chest: 3, 
    ring: 2, 
    eyes: 4,
    targetChest: 3,
    targetRing: 2,
    targetEyes: 4,
  });

  useFrame(() => {
    // ─────────────────────────────────────────────────────────────────────
    // HEAD TRACKING (follows cursor/firefly)
    // ─────────────────────────────────────────────────────────────────────
    
    if (headRef.current) {
      // Subtle tracking intensity variation based on proximity
      const trackingMultiplier = behavior?.zone === 'close' ? 1.1 :
                                  behavior?.zone === 'near' ? 1.0 : 0.9;
      
      targetRotation.current.x = mousePosition.y * 0.4 * trackingMultiplier;
      targetRotation.current.y = mousePosition.x * 0.5 * trackingMultiplier;

      // Consistent smooth lerp
      const lerpSpeed = 0.08;

      headRef.current.rotation.x = THREE.MathUtils.lerp(
        headRef.current.rotation.x,
        targetRotation.current.x,
        lerpSpeed
      );
      headRef.current.rotation.y = THREE.MathUtils.lerp(
        headRef.current.rotation.y,
        targetRotation.current.y,
        lerpSpeed
      );
    }

    // ─────────────────────────────────────────────────────────────────────
    // BODY LEAN (subtle anticipatory motion)
    // ─────────────────────────────────────────────────────────────────────
    
    if (bodyRef.current) {
      const baseLean = mousePosition.x * 0.1;
      
      bodyRef.current.rotation.y = THREE.MathUtils.lerp(
        bodyRef.current.rotation.y,
        baseLean,
        0.03
      );
    }

    // ─────────────────────────────────────────────────────────────────────
    // GLOW INTENSITY (zone-based)
    // ─────────────────────────────────────────────────────────────────────
    
    const glow = glowRef.current;
    const zone = behavior?.zone ?? 'idle';
    
    // Set targets based on proximity zone
    if (zone === 'close') {
      // Slightly brighter when cursor is very close
      glow.targetChest = 4;
      glow.targetRing = 2.5;
      glow.targetEyes = 5;
    } else if (zone === 'near') {
      // Subtle awareness glow
      glow.targetChest = 3.5;
      glow.targetRing = 2.2;
      glow.targetEyes = 4.5;
    } else {
      // Default idle glow
      glow.targetChest = 3;
      glow.targetRing = 2;
      glow.targetEyes = 4;
    }
    
    // Smooth interpolation
    glow.chest = THREE.MathUtils.lerp(glow.chest, glow.targetChest, 0.05);
    glow.ring = THREE.MathUtils.lerp(glow.ring, glow.targetRing, 0.05);
    glow.eyes = THREE.MathUtils.lerp(glow.eyes, glow.targetEyes, 0.05);
  });

  return (
    <Float speed={2} rotationIntensity={0.2} floatIntensity={0.5}>
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
        <mesh position={[0, 0.2, 0]} rotation={[Math.PI / 2, 0, 0]}>
          <torusGeometry args={[0.65, 0.03, 16, 32]} />
          <meshStandardMaterial
            color="#00d4ff"
            emissive="#00d4ff"
            emissiveIntensity={2}
          />
        </mesh>

        {/* Chest light */}
        <mesh position={[0, 0.1, 0.55]}>
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
          {/* Arm joint glow */}
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
          {/* Arm joint glow */}
          <mesh position={[0, 0.3, 0]}>
            <sphereGeometry args={[0.08, 16, 16]} />
            <meshStandardMaterial
              color="#a855f7"
              emissive="#a855f7"
              emissiveIntensity={2}
            />
          </mesh>
        </group>

        {/* Head group - follows cursor */}
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

// Pre-generated particle data to avoid re-randomizing on each render
const PARTICLE_DATA = [...Array(12)].map((_, i) => {
  const angle = (i / 12) * Math.PI * 2;
  const radius = 2 + Math.random() * 0.5;
  const y = (Math.random() - 0.5) * 2;
  const size = 0.03 + Math.random() * 0.03;
  return { angle, radius, y, size };
});

// Floating particles around the bot - stable idle animation unaffected by cursor
const Particles = () => {
  const particlesRef = useRef<THREE.Group>(null);

  useFrame(({ clock }) => {
    if (particlesRef.current) {
      // Slow, consistent orbital rotation
      particlesRef.current.rotation.y = clock.getElapsedTime() * 0.1;
    }
  });

  return (
    <group ref={particlesRef}>
      {PARTICLE_DATA.map((p, i) => (
        <mesh 
          key={i} 
          position={[
            Math.cos(p.angle) * p.radius, 
            p.y, 
            Math.sin(p.angle) * p.radius
          ]}
        >
          <sphereGeometry args={[p.size, 8, 8]} />
          <meshStandardMaterial
            color={i % 2 === 0 ? "#00d4ff" : "#a855f7"}
            emissive={i % 2 === 0 ? "#00d4ff" : "#a855f7"}
            emissiveIntensity={2}
          />
        </mesh>
      ))}
    </group>
  );
};

interface KuroBot3DProps {
  className?: string;
  behavior?: BotBehavior;
  enableFirefly?: boolean;
}

const KuroBot3D = forwardRef<HTMLDivElement, KuroBot3DProps>(
  ({ className = "", behavior, enableFirefly = false }, ref) => {
  const containerRef = useRef<HTMLDivElement>(null);
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 });

  // Forward ref
  useEffect(() => {
    if (ref && typeof ref === 'object' && containerRef.current) {
      ref.current = containerRef.current;
    }
  }, [ref]);

  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!containerRef.current) return;

      const rect = containerRef.current.getBoundingClientRect();
      const centerX = rect.left + rect.width / 2;
      const centerY = rect.top + rect.height / 2;

      // Normalize mouse position to -1 to 1 range
      const x = (e.clientX - centerX) / (window.innerWidth / 2);
      const y = (e.clientY - centerY) / (window.innerHeight / 2);

      setMousePosition({ x: Math.max(-1, Math.min(1, x)), y: Math.max(-1, Math.min(1, y)) });
    };

    window.addEventListener("mousemove", handleMouseMove);
    return () => window.removeEventListener("mousemove", handleMouseMove);
  }, []);

  return (
    <div ref={containerRef} className={`${className}`} style={{ minHeight: '200px' }}>
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
        
        <Bot mousePosition={mousePosition} behavior={behavior} />
        <Particles />
        
        <Environment preset="night" />
      </Canvas>
    </div>
  );
});

KuroBot3D.displayName = 'KuroBot3D';

export default KuroBot3D;
export type { BotBehavior, ProximityZone };
