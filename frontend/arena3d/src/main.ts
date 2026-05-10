import * as THREE from "three";

type CardView = {
  id: string;
  name: string;
  type: string;
  element: string;
  playable?: boolean;
  colors?: {
    primary?: string;
    secondary?: string;
    accent?: string;
  };
};

type NormalizedArenaState = {
  round: number;
  phase: string;
  message: string;
  me: {
    hp: number;
    energy: number;
    maxEnergy: number;
    ambition: number;
    hand: CardView[];
    field: Record<string, CardView | null>;
  };
  enemy: {
    hp: number;
    energy: number;
    maxEnergy: number;
    handCount: number;
    field: Record<string, CardView | null>;
  };
};

type Adapter = {
  normalizeArenaState: (payload: unknown) => NormalizedArenaState;
  boardSlots: (state: unknown) => Array<{
    owner: "me" | "enemy";
    slot: string;
    card: CardView | null;
  }>;
};

declare global {
  interface Window {
    AmbitionzArenaRendererAdapter?: Adapter;
    __ambitionzArena48State?: unknown;
    __ambitionzArenaNormalizedState?: NormalizedArenaState;
    __ambitionzArena3d?: Arena3D;
    __ambitionzArena3dManifest?: unknown;
  }
}

const ENABLED =
  document.body?.dataset.arenaRenderer === "3d" ||
  new URLSearchParams(window.location.search).get("renderer") === "3d";

class Arena3D {
  private readonly root: HTMLElement;
  private readonly status: HTMLElement;
  private readonly scene = new THREE.Scene();
  private readonly camera = new THREE.PerspectiveCamera(42, 1, 0.1, 100);
  private readonly renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  private readonly boardGroup = new THREE.Group();
  private readonly cardMeshes = new Map<string, THREE.Mesh>();
  private readonly orbMeshes = new Map<string, THREE.Mesh>();
  private readonly clock = new THREE.Clock();
  private frame = 0;
  private disposed = false;

  constructor() {
    this.root = document.createElement("section");
    this.root.className = "az3d-stage";
    this.root.setAttribute("aria-hidden", "true");

    this.status = document.createElement("div");
    this.status.className = "az3d-status";
    this.status.innerHTML = "<b>3D</b><span>Waiting for arena state...</span>";

    document.body.prepend(this.root);
    document.body.appendChild(this.status);
    this.root.appendChild(this.renderer.domElement);

    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    this.scene.fog = new THREE.Fog("#05050b", 10, 28);
    this.camera.position.set(0, 7.2, 8.4);
    this.camera.lookAt(0, 0, 0);

    this.createLights();
    this.createTable();
    this.scene.add(this.boardGroup);

    window.addEventListener("resize", this.resize);
    this.resize();
    this.loadManifest();
    this.tick();
  }

  renderArenaState(payload: unknown) {
    const adapter = window.AmbitionzArenaRendererAdapter;
    if (!adapter) return;

    const state = adapter.normalizeArenaState(payload);
    const slots = adapter.boardSlots(state);
    const liveKeys = new Set<string>();

    slots.forEach((slot, index) => {
      const key = `${slot.owner}-${slot.slot}`;
      liveKeys.add(key);
      const mesh = this.cardMeshes.get(key) || this.createCardMesh(key);
      const orb = this.orbMeshes.get(key) || this.createOrbMesh(key);
      const x = (index % 3 - 1) * 1.75;
      const z = slot.owner === "enemy" ? -1.55 : 1.55;

      mesh.position.set(x, slot.card ? 0.22 : 0.08, z);
      mesh.rotation.set(-Math.PI / 2.25, 0, slot.owner === "enemy" ? Math.PI : 0);
      mesh.scale.setScalar(slot.card ? 1 : 0.88);
      mesh.userData.targetY = slot.card ? 0.22 : 0.08;

      const material = mesh.material as THREE.MeshStandardMaterial;
      const color = slot.card?.colors?.primary || (slot.owner === "enemy" ? "#46506a" : "#d6a84c");
      material.color.set(color);
      material.emissive.set(slot.card ? color : "#111827");
      material.emissiveIntensity = slot.card ? 0.18 : 0.05;
      material.opacity = slot.card ? 0.96 : 0.28;

      orb.position.set(x, slot.card ? 0.55 : 0.26, z);
      orb.scale.setScalar(slot.card ? 1 : 0.45);
      orb.userData.targetY = slot.card ? 0.55 : 0.26;
      orb.userData.active = Boolean(slot.card);

      const orbMaterial = orb.material as THREE.MeshStandardMaterial;
      orbMaterial.color.set(slot.card?.colors?.accent || color);
      orbMaterial.emissive.set(slot.card?.colors?.secondary || color);
      orbMaterial.emissiveIntensity = slot.card ? 0.55 : 0.08;
      orbMaterial.opacity = slot.card ? 0.82 : 0.18;
    });

    for (const [key, mesh] of this.cardMeshes.entries()) {
      if (!liveKeys.has(key)) {
        mesh.removeFromParent();
        this.cardMeshes.delete(key);
      }
    }

    for (const [key, mesh] of this.orbMeshes.entries()) {
      if (!liveKeys.has(key)) {
        mesh.removeFromParent();
        this.orbMeshes.delete(key);
      }
    }

    this.status.innerHTML = [
      "<b>3D</b>",
      `<span>Round ${state.round} · ${state.phase} · HP ${state.me.hp}/${state.enemy.hp}</span>`,
    ].join("");
  }

  dispose() {
    this.disposed = true;
    window.removeEventListener("resize", this.resize);
    this.renderer.dispose();
    this.root.remove();
    this.status.remove();
  }

  private createLights() {
    const ambient = new THREE.HemisphereLight("#fff4d0", "#141827", 1.3);
    const key = new THREE.DirectionalLight("#fff0bf", 2.2);
    const rim = new THREE.PointLight("#6dc9ff", 2.4, 16);

    key.position.set(-3, 8, 4);
    rim.position.set(4, 2.8, -3);
    this.scene.add(ambient, key, rim);
  }

  private createTable() {
    const table = new THREE.Mesh(
      new THREE.BoxGeometry(7.2, 0.26, 5.4),
      new THREE.MeshStandardMaterial({
        color: "#171018",
        roughness: 0.82,
        metalness: 0.2,
      }),
    );
    table.position.y = -0.08;
    this.scene.add(table);

    const laneMaterial = new THREE.MeshStandardMaterial({
      color: "#d6a84c",
      emissive: "#d6a84c",
      emissiveIntensity: 0.12,
      transparent: true,
      opacity: 0.42,
      roughness: 0.7,
    });

    [-1.55, 1.55].forEach((z) => {
      const lane = new THREE.Mesh(new THREE.BoxGeometry(6.1, 0.035, 1.25), laneMaterial.clone());
      lane.position.set(0, 0.08, z);
      this.scene.add(lane);
    });

    const divider = new THREE.Mesh(
      new THREE.BoxGeometry(6.7, 0.05, 0.08),
      new THREE.MeshStandardMaterial({ color: "#fff1bb", emissive: "#d6a84c", emissiveIntensity: 0.38 }),
    );
    divider.position.set(0, 0.12, 0);
    this.scene.add(divider);
  }

  private createCardMesh(key: string) {
    const mesh = new THREE.Mesh(
      new THREE.BoxGeometry(1.08, 0.07, 1.48),
      new THREE.MeshStandardMaterial({
        color: "#d6a84c",
        roughness: 0.46,
        metalness: 0.12,
        transparent: true,
        opacity: 0.92,
      }),
    );

    mesh.name = key;
    mesh.userData.targetY = 0.1;
    this.boardGroup.add(mesh);
    this.cardMeshes.set(key, mesh);
    return mesh;
  }

  private createOrbMesh(key: string) {
    const mesh = new THREE.Mesh(
      new THREE.SphereGeometry(0.16, 24, 12),
      new THREE.MeshStandardMaterial({
        color: "#fff1bb",
        emissive: "#d6a84c",
        emissiveIntensity: 0.45,
        roughness: 0.32,
        metalness: 0.08,
        transparent: true,
        opacity: 0.78,
      }),
    );

    mesh.name = `${key}-orb`;
    mesh.userData.targetY = 0.26;
    this.boardGroup.add(mesh);
    this.orbMeshes.set(key, mesh);
    return mesh;
  }

  private resize = () => {
    const width = window.innerWidth || 1;
    const height = window.innerHeight || 1;
    this.camera.aspect = width / height;
    this.camera.updateProjectionMatrix();
    this.renderer.setSize(width, height, false);
  };

  private tick = () => {
    if (this.disposed) return;

    const t = this.clock.getElapsedTime();
    this.boardGroup.rotation.y = Math.sin(t * 0.25) * 0.035;

    for (const mesh of this.cardMeshes.values()) {
      const targetY = Number(mesh.userData.targetY || 0.1);
      mesh.position.y += (targetY + Math.sin(t * 2.4 + mesh.position.x) * 0.018 - mesh.position.y) * 0.08;
    }

    for (const mesh of this.orbMeshes.values()) {
      const targetY = Number(mesh.userData.targetY || 0.25);
      const pulse = mesh.userData.active ? Math.sin(t * 4 + mesh.position.x) * 0.035 : 0;
      mesh.position.y += (targetY + pulse - mesh.position.y) * 0.10;
      mesh.rotation.y += 0.012;
    }

    this.renderer.render(this.scene, this.camera);
    this.frame = window.requestAnimationFrame(this.tick);
  };

  private loadManifest() {
    fetch("/static/assets/arena3d/manifest.json")
      .then((response) => (response.ok ? response.json() : null))
      .then((manifest) => {
        window.__ambitionzArena3dManifest = manifest;
      })
      .catch(() => {
        window.__ambitionzArena3dManifest = null;
      });
  }
}

if (ENABLED) {
  const boot = () => {
    const arena = new Arena3D();
    window.__ambitionzArena3d = arena;

    window.addEventListener("ambitionz:arena_state_rendered", (event) => {
      const detail = (event as CustomEvent).detail || {};
      arena.renderArenaState(detail.payload || detail.state);
    });

    if (window.__ambitionzArena48State) {
      arena.renderArenaState(window.__ambitionzArena48State);
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot, { once: true });
  } else {
    boot();
  }
}
