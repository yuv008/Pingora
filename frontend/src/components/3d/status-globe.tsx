'use client';

import { useRef, useMemo, useEffect } from 'react';
import { Canvas, useFrame } from '@react-three/fiber';
import { OrbitControls, Sphere, Html } from '@react-three/drei';
import * as THREE from 'three';

interface Monitor {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  status: 'up' | 'down' | 'degraded' | 'paused' | 'unknown';
}

interface GlobeProps {
  monitors: Monitor[];
}

function Globe({ monitors }: GlobeProps) {
  const globeRef = useRef<THREE.Mesh>(null);
  const markersRef = useRef<THREE.Group>(null);

  // Auto-rotate the globe
  useFrame(() => {
    if (globeRef.current) {
      globeRef.current.rotation.y += 0.001;
    }
    if (markersRef.current) {
      markersRef.current.rotation.y += 0.001;
    }
  });

  // Convert lat/lon to 3D position
  const latLonToVector3 = (lat: number, lon: number, radius: number) => {
    const phi = (90 - lat) * (Math.PI / 180);
    const theta = (lon + 180) * (Math.PI / 180);

    const x = -(radius * Math.sin(phi) * Math.cos(theta));
    const y = radius * Math.cos(phi);
    const z = radius * Math.sin(phi) * Math.sin(theta);

    return new THREE.Vector3(x, y, z);
  };

  // Get color based on status
  const getStatusColor = (status: string) => {
    switch (status) {
      case 'up':
        return '#22c55e'; // green
      case 'down':
        return '#ef4444'; // red
      case 'degraded':
        return '#f59e0b'; // yellow
      case 'paused':
        return '#64748b'; // gray
      default:
        return '#94a3b8'; // light gray
    }
  };

  return (
    <group>
      {/* Earth Globe */}
      <Sphere ref={globeRef} args={[2, 64, 64]}>
        <meshStandardMaterial
          color="#1e293b"
          roughness={0.9}
          metalness={0.1}
          wireframe={false}
        />
      </Sphere>

      {/* Wireframe overlay */}
      <Sphere args={[2.01, 32, 32]}>
        <meshBasicMaterial color="#334155" wireframe={true} opacity={0.3} transparent />
      </Sphere>

      {/* Monitor markers */}
      <group ref={markersRef}>
        {monitors.map((monitor) => {
          const position = latLonToVector3(monitor.latitude, monitor.longitude, 2.05);
          return (
            <group key={monitor.id} position={position}>
              {/* Marker sphere */}
              <Sphere args={[0.03, 16, 16]}>
                <meshStandardMaterial
                  color={getStatusColor(monitor.status)}
                  emissive={getStatusColor(monitor.status)}
                  emissiveIntensity={0.5}
                />
              </Sphere>

              {/* Pulsing ring effect */}
              {monitor.status !== 'paused' && (
                <PulsingRing color={getStatusColor(monitor.status)} />
              )}

              {/* Tooltip on hover */}
              <Html distanceFactor={8}>
                <div className="pointer-events-none rounded-lg bg-black/80 px-2 py-1 text-xs text-white opacity-0 transition-opacity hover:opacity-100">
                  {monitor.name}
                </div>
              </Html>
            </group>
          );
        })}
      </group>
    </group>
  );
}

function PulsingRing({ color }: { color: string }) {
  const ringRef = useRef<THREE.Mesh>(null);

  useFrame(({ clock }) => {
    if (ringRef.current) {
      const scale = 1 + Math.sin(clock.getElapsedTime() * 2) * 0.3;
      ringRef.current.scale.set(scale, scale, scale);
      ringRef.current.material.opacity = 0.5 - Math.sin(clock.getElapsedTime() * 2) * 0.3;
    }
  });

  return (
    <mesh ref={ringRef}>
      <ringGeometry args={[0.04, 0.06, 32]} />
      <meshBasicMaterial color={color} transparent opacity={0.5} side={THREE.DoubleSide} />
    </mesh>
  );
}

export function StatusGlobe({ monitors }: GlobeProps) {
  return (
    <div className="h-full w-full">
      <Canvas camera={{ position: [0, 0, 5], fov: 50 }}>
        <ambientLight intensity={0.5} />
        <pointLight position={[10, 10, 10]} intensity={1} />
        <pointLight position={[-10, -10, -10]} intensity={0.5} />
        <Globe monitors={monitors} />
        <OrbitControls
          enableZoom={true}
          enablePan={false}
          minDistance={3}
          maxDistance={8}
          autoRotate={false}
        />
      </Canvas>
    </div>
  );
}

// Helper function to generate random coordinates for demo
export function generateDemoMonitors(count: number = 20): Monitor[] {
  const statuses: Array<'up' | 'down' | 'degraded' | 'paused'> = [
    'up',
    'up',
    'up',
    'up',
    'up',
    'down',
    'degraded',
    'paused',
  ];

  return Array.from({ length: count }, (_, i) => ({
    id: `monitor-${i}`,
    name: `API ${i + 1}`,
    latitude: Math.random() * 180 - 90,
    longitude: Math.random() * 360 - 180,
    status: statuses[Math.floor(Math.random() * statuses.length)],
  }));
}
