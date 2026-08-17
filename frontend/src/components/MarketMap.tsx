import { useEffect, useMemo, useRef } from "react";
import mapboxgl from "mapbox-gl";
import "mapbox-gl/dist/mapbox-gl.css";

import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from "react-leaflet";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

import type { GeospatialMarketContext } from "@/services/api";

type Props = {
  geoContext: GeospatialMarketContext;
  className?: string;
};

type NormalizedMarker = {
  id: string;
  label: string;
  type: string;
  latitude: number;
  longitude: number;
  credibility?: string;
  source?: string;
  address?: string | null;
  category?: string | null;
  intensity?: number;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
}

function isTransitMarker(type?: string): boolean {
  return (type || "").toLowerCase().includes("transit");
}

function isCompetitorMarker(type?: string): boolean {
  return (type || "").toLowerCase().includes("competitor");
}

// Honest centre: use exactly what the backend anchored the analysis on (an address
// or the city centre). No hardcoded Kitchener fallback — a missing centre must not
// silently masquerade as Kitchener. Ontario's rough geographic centre is only used
// if the backend somehow sends no coordinate at all.
function getCenter(geoContext: GeospatialMarketContext): [number, number] {
  const lat = geoContext.center?.latitude;
  const lng = geoContext.center?.longitude;

  if (isFiniteNumber(lat) && isFiniteNumber(lng)) {
    return [lat, lng];
  }

  return [44.0, -79.5];
}

function markerColor(type?: string): string {
  const normalized = (type || "").toLowerCase();

  if (normalized.includes("competitor")) return "#d93025";
  if (normalized.includes("transit")) return "#1a73e8";

  return "#d93025";
}

function escapeHtml(value: unknown): string {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function normalizeMarkers(geoContext: GeospatialMarketContext): NormalizedMarker[] {
  const center = getCenter(geoContext);
  const radiusKm = Number.isFinite(geoContext.radius_km) ? geoContext.radius_km : 5;
  const markers = Array.isArray(geoContext.markers) ? geoContext.markers : [];

  return markers
    .map((marker: any, index: number): NormalizedMarker | null => {
      const rawLat = marker.latitude ?? marker.lat ?? marker.coordinates?.latitude;
      const rawLng = marker.longitude ?? marker.lng ?? marker.coordinates?.longitude;

      let latitude = isFiniteNumber(rawLat) ? rawLat : null;
      let longitude = isFiniteNumber(rawLng) ? rawLng : null;

      if (latitude === null || longitude === null) {
        const xOffsetPct = Number(marker.x_offset_pct ?? 0);
        const yOffsetPct = Number(marker.y_offset_pct ?? 0);
        const kmEast = ((Number.isFinite(xOffsetPct) ? xOffsetPct : 0) / 100) * radiusKm;
        const kmNorth = ((Number.isFinite(yOffsetPct) ? yOffsetPct : 0) / 100) * radiusKm;

        latitude = center[0] + kmNorth / 111.32;
        longitude =
          center[1] +
          kmEast / (111.32 * Math.max(0.15, Math.cos((center[0] * Math.PI) / 180)));
      }

      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

      return {
        id: String(marker.marker_id ?? marker.id ?? `marker-${index}`),
        label: String(marker.label ?? marker.title ?? marker.name ?? "Market evidence"),
        type: String(marker.marker_type ?? marker.type ?? "evidence"),
        latitude,
        longitude,
        credibility: marker.credibility,
        source: marker.source ?? marker.source_name ?? marker.source_method,
        address: marker.address,
        category: marker.category ?? marker.business_category ?? marker.subcategory,
        intensity: marker.intensity,
      };
    })
    .filter((marker): marker is NormalizedMarker => {
      if (!marker) return false;
      return isCompetitorMarker(marker.type);
    });
}

function circlePolygon(center: [number, number], radiusKm: number, points = 96) {
  const [lat, lng] = center;
  const coordinates: number[][] = [];
  const safeRadius = Number.isFinite(radiusKm) && radiusKm > 0 ? radiusKm : 5;

  for (let i = 0; i <= points; i += 1) {
    const angle = (i / points) * Math.PI * 2;
    const dx = Math.cos(angle) * safeRadius;
    const dy = Math.sin(angle) * safeRadius;
    const pointLat = lat + dy / 111.32;
    const pointLng = lng + dx / (111.32 * Math.max(0.15, Math.cos((lat * Math.PI) / 180)));
    coordinates.push([pointLng, pointLat]);
  }

  return {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        properties: {},
        geometry: {
          type: "Polygon",
          coordinates: [coordinates],
        },
      },
    ],
  } as any;
}

type FootfallPoint = {
  id: string;
  latitude: number;
  longitude: number;
  intensity: number;
  evidenceType?: string;
  source?: string;
  label?: string | null;
  category?: string | null;
  observedCount: number;
  observedUnit: string;
  observationPeriod: string;
  sourceUrl?: string | null;
};

function normalizeFootfallPoints(geoContext: GeospatialMarketContext): FootfallPoint[] {
  const points = geoContext.footfall_heatmap_points ?? [];

  return points
    .map((point, index): FootfallPoint | null => {
      const latitude = Number(point.latitude);
      const longitude = Number(point.longitude);
      const rawIntensity = Number(point.intensity ?? 0);
      const observedCount = Number(point.observed_count);

      if (!Number.isFinite(latitude) || !Number.isFinite(longitude) || !Number.isFinite(observedCount)) return null;

      return {
        id: String(point.point_id ?? point.id ?? `footfall-${index}`),
        latitude,
        longitude,
        intensity: Math.max(0, Math.min(1, Number.isFinite(rawIntensity) ? rawIntensity : 0)),
        evidenceType: point.evidence_type,
        source: point.source,
        label: point.label,
        category: point.category,
        observedCount,
        observedUnit: point.observed_unit,
        observationPeriod: point.observation_period,
        sourceUrl: point.source_url,
      };
    })
    .filter((point): point is FootfallPoint => Boolean(point));
}

function footfallHeatmapGeoJson(geoContext: GeospatialMarketContext) {
  const points = normalizeFootfallPoints(geoContext);

  return {
    type: "FeatureCollection",
    features: points.map((point) => ({
      type: "Feature",
      properties: {
        id: point.id,
        intensity: point.intensity,
        label: point.label ?? "Pedestrian counter",
        evidenceType: point.evidenceType ?? "observed_pedestrian_count",
        source: point.source ?? "Municipal pedestrian counter",
        category: point.category ?? null,
        observedCount: point.observedCount,
        observedUnit: point.observedUnit,
        observationPeriod: point.observationPeriod,
        sourceUrl: point.sourceUrl ?? null,
      },
      geometry: {
        type: "Point",
        coordinates: [point.longitude, point.latitude],
      },
    })),
  } as any;
}

function FootfallLegend({ geoContext }: { geoContext: GeospatialMarketContext }) {
  const points = normalizeFootfallPoints(geoContext);
  const counts = points.map((point) => point.observedCount);
  const countRange = counts.length
    ? `${Math.round(Math.min(...counts)).toLocaleString()}–${Math.round(Math.max(...counts)).toLocaleString()} avg/day`
    : null;

  return (
    <div className="pointer-events-none absolute bottom-4 right-4 z-[500] w-[290px] rounded-xl border border-border bg-card/95 p-3 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-foreground">Observed foot traffic</p>
          <p className="mt-0.5 text-[10px] text-muted-foreground">Municipal pedestrian counters</p>
        </div>
        <span className="rounded-full border border-border px-2 py-0.5 text-[9px] font-mono uppercase text-muted-foreground">
          {points.length} site{points.length === 1 ? "" : "s"}
        </span>
      </div>

      <div className="mt-3 h-3 rounded-full border border-border bg-[linear-gradient(90deg,#2563eb_0%,#22c55e_38%,#fde047_68%,#ef4444_100%)] shadow-[0_0_12px_rgba(239,68,68,.18)]" />
      <div className="mt-1 flex justify-between text-[9px] font-mono uppercase text-muted-foreground">
        <span>Lower</span>
        <span>Medium</span>
        <span>Higher</span>
      </div>

      <p className="mt-2 text-[10px] leading-snug text-muted-foreground">
        {countRange
          ? `Heat interpolates an observed range of ${countRange}.`
          : "No observed municipal counter data is available."}
      </p>
    </div>
  );
}

function popupHtmlForMarker(marker: NormalizedMarker): string {
  if (isTransitMarker(marker.type)) {
    return `
      <div style="min-width:180px;max-width:250px;font-family:Inter,Arial,sans-serif;line-height:1.45;">
        <div style="font-weight:700;font-size:13px;color:#111827;">${escapeHtml(marker.label)}</div>
      </div>
    `;
  }

  return `
    <div style="min-width:220px;max-width:280px;font-family:Inter,Arial,sans-serif;line-height:1.45;">
      <div style="font-weight:700;font-size:13px;color:#111827;">${escapeHtml(marker.label)}</div>
      <div style="margin-top:5px;font-size:12px;color:#374151;">${escapeHtml(marker.address || "Address not available")}</div>
    </div>
  `;
}

function createMapboxPinElement(color: string, size = 34): HTMLDivElement {
  const el = document.createElement("div");
  el.className = "zonalyze-mapbox-marker";
  el.style.width = `${size}px`;
  el.style.height = `${size}px`;
  el.style.cursor = "pointer";
  el.style.filter = "drop-shadow(0 3px 7px rgba(0,0,0,.45))";
  el.innerHTML = `
    <svg width="${size}" height="${size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg">
      <path fill="${color}" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
      <circle cx="12" cy="9" r="2.7" fill="white"/>
    </svg>
  `;
  return el;
}

function createMapboxBusStopElement(size = 30): HTMLDivElement {
  const el = document.createElement("div");
  el.className = "zonalyze-mapbox-bus-marker";
  el.style.width = `${size}px`;
  el.style.height = `${size}px`;
  el.style.display = "flex";
  el.style.alignItems = "center";
  el.style.justifyContent = "center";
  el.style.borderRadius = "999px";
  el.style.background = "#1a73e8";
  el.style.border = "2px solid white";
  el.style.boxShadow = "0 3px 8px rgba(0,0,0,.45)";
  el.style.cursor = "pointer";
  el.innerHTML = `
    <svg width="${Math.round(size * 0.62)}" height="${Math.round(size * 0.62)}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <rect x="5" y="3" width="14" height="15" rx="3" fill="white"/>
      <path d="M7.5 7.5H16.5" stroke="#1a73e8" stroke-width="1.8" stroke-linecap="round"/>
      <path d="M7.5 11H16.5" stroke="#1a73e8" stroke-width="1.8" stroke-linecap="round"/>
      <circle cx="8.5" cy="15" r="1.2" fill="#1a73e8"/>
      <circle cx="15.5" cy="15" r="1.2" fill="#1a73e8"/>
    </svg>
  `;
  return el;
}

function fitMapboxToRadius(map: mapboxgl.Map, center: [number, number], radiusKm: number) {
  const [lat, lng] = center;
  const safeRadiusKm = Number.isFinite(radiusKm) && radiusKm > 0 ? radiusKm : 5;
  const latPadding = safeRadiusKm / 111.32;
  const lngPadding = safeRadiusKm / (111.32 * Math.max(0.15, Math.cos((lat * Math.PI) / 180)));

  map.fitBounds(
    [
      [lng - lngPadding, lat - latPadding],
      [lng + lngPadding, lat + latPadding],
    ],
    {
      padding: 42,
      maxZoom: safeRadiusKm <= 2 ? 14 : safeRadiusKm <= 5 ? 13 : 12,
      duration: 700,
    },
  );
}

function createLeafletPinIcon(color: string, size = 34) {
  return L.divIcon({
    className: "zonalyze-map-pin",
    html: `
      <div style="width:${size}px;height:${size}px;position:relative;">
        <svg width="${size}" height="${size}" viewBox="0 0 24 24" xmlns="http://www.w3.org/2000/svg" style="filter: drop-shadow(0 3px 6px rgba(0,0,0,.45));">
          <path fill="${color}" d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7z"/>
          <circle cx="12" cy="9" r="2.7" fill="white"/>
        </svg>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size],
    popupAnchor: [0, -size],
  });
}

function createLeafletBusStopIcon(size = 30) {
  return L.divIcon({
    className: "zonalyze-bus-stop-icon",
    html: `
      <div style="
        width:${size}px;
        height:${size}px;
        display:flex;
        align-items:center;
        justify-content:center;
        border-radius:999px;
        background:#1a73e8;
        border:2px solid white;
        box-shadow:0 3px 8px rgba(0,0,0,.45);
      ">
        <svg width="${Math.round(size * 0.62)}" height="${Math.round(size * 0.62)}" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <rect x="5" y="3" width="14" height="15" rx="3" fill="white"/>
          <path d="M7.5 7.5H16.5" stroke="#1a73e8" stroke-width="1.8" stroke-linecap="round"/>
          <path d="M7.5 11H16.5" stroke="#1a73e8" stroke-width="1.8" stroke-linecap="round"/>
          <circle cx="8.5" cy="15" r="1.2" fill="#1a73e8"/>
          <circle cx="15.5" cy="15" r="1.2" fill="#1a73e8"/>
        </svg>
      </div>
    `,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

function leafletIconForMarker(marker: NormalizedMarker) {
  if (isTransitMarker(marker.type)) {
    return createLeafletBusStopIcon(30);
  }

  return createLeafletPinIcon(markerColor(marker.type), isCompetitorMarker(marker.type) ? 30 : 32);
}

function FitLeafletToRadius({ center, radiusKm }: { center: [number, number]; radiusKm: number }) {
  const map = useMap();

  useEffect(() => {
    const safeRadiusKm = Number.isFinite(radiusKm) && radiusKm > 0 ? radiusKm : 5;
    const [lat, lng] = center;

    if (!Number.isFinite(lat) || !Number.isFinite(lng)) return;

    const latPadding = safeRadiusKm / 111.32;
    const lngPadding = safeRadiusKm / (111.32 * Math.max(0.15, Math.cos((lat * Math.PI) / 180)));

    const bounds = L.latLngBounds(
      [lat - latPadding, lng - lngPadding],
      [lat + latPadding, lng + lngPadding],
    );

    const timeout = window.setTimeout(() => {
      map.invalidateSize();
      map.fitBounds(bounds, {
        padding: [34, 34],
        maxZoom: safeRadiusKm <= 2 ? 14 : safeRadiusKm <= 5 ? 13 : 12,
      });
    }, 180);

    return () => window.clearTimeout(timeout);
  }, [map, center[0], center[1], radiusKm]);

  return null;
}

function LeafletFootfallHeatmap({ points }: { points: FootfallPoint[] }) {
  const map = useMap();

  useEffect(() => {
    const canvas = document.createElement("canvas");
    canvas.className = "leaflet-footfall-heatmap";
    Object.assign(canvas.style, {
      position: "absolute",
      inset: "0",
      pointerEvents: "none",
      zIndex: "350",
    });
    map.getContainer().appendChild(canvas);

    const palette = document.createElement("canvas");
    palette.width = 256;
    palette.height = 1;
    const paletteContext = palette.getContext("2d");
    const paletteGradient = paletteContext?.createLinearGradient(0, 0, 256, 0);
    paletteGradient?.addColorStop(0, "rgba(37,99,235,0)");
    paletteGradient?.addColorStop(0.16, "#2563eb");
    paletteGradient?.addColorStop(0.38, "#22c55e");
    paletteGradient?.addColorStop(0.62, "#fde047");
    paletteGradient?.addColorStop(0.82, "#f97316");
    paletteGradient?.addColorStop(1, "#ef4444");
    if (paletteContext && paletteGradient) {
      paletteContext.fillStyle = paletteGradient;
      paletteContext.fillRect(0, 0, 256, 1);
    }
    const palettePixels = paletteContext?.getImageData(0, 0, 256, 1).data;

    const draw = () => {
      const size = map.getSize();
      canvas.width = size.x;
      canvas.height = size.y;
      const context = canvas.getContext("2d", { willReadFrequently: true });
      if (!context || !palettePixels || !points.length) return;

      const radius = Math.max(42, Math.min(105, 42 + (map.getZoom() - 10) * 16));
      for (const point of points) {
        const pixel = map.latLngToContainerPoint([point.latitude, point.longitude]);
        const gradient = context.createRadialGradient(pixel.x, pixel.y, 0, pixel.x, pixel.y, radius);
        gradient.addColorStop(0, `rgba(0,0,0,${0.34 + point.intensity * 0.36})`);
        gradient.addColorStop(0.45, `rgba(0,0,0,${0.2 + point.intensity * 0.2})`);
        gradient.addColorStop(1, "rgba(0,0,0,0)");
        context.fillStyle = gradient;
        context.fillRect(pixel.x - radius, pixel.y - radius, radius * 2, radius * 2);
      }

      const image = context.getImageData(0, 0, canvas.width, canvas.height);
      for (let index = 0; index < image.data.length; index += 4) {
        const density = image.data[index + 3];
        if (density < 8) {
          image.data[index + 3] = 0;
          continue;
        }
        const paletteIndex = Math.min(255, density) * 4;
        image.data[index] = palettePixels[paletteIndex];
        image.data[index + 1] = palettePixels[paletteIndex + 1];
        image.data[index + 2] = palettePixels[paletteIndex + 2];
        image.data[index + 3] = Math.min(205, Math.round(density * 1.25));
      }
      context.putImageData(image, 0, 0);
    };

    draw();
    map.on("moveend zoomend resize", draw);
    return () => {
      map.off("moveend zoomend resize", draw);
      canvas.remove();
    };
  }, [map, points]);

  return null;
}

function MapHeader({ geoContext, radiusKm, mode }: { geoContext: GeospatialMarketContext; radiusKm: number; mode: "mapbox" | "openstreetmap" }) {
  return (
    <div className="flex flex-col gap-2 border-b border-border px-5 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 shadow-[0_0_14px_rgba(239,68,68,.8)]" />
          <h3 className="text-sm font-semibold tracking-wide text-foreground">Market Map</h3>
        </div>
        <p className="mt-1 text-[11px] font-mono text-muted-foreground">
          {geoContext.municipality_name} · {geoContext.business_subcategory} · {radiusKm} km radius
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        <span className="rounded-full border border-red-400/30 px-2.5 py-1 text-[10px] font-mono uppercase text-red-300">
          selected area
        </span>
        <span className="rounded-full border border-primary/30 px-2.5 py-1 text-[10px] font-mono uppercase text-primary">
          {mode === "mapbox" ? "mapbox streets" : geoContext.map_credibility ?? "open map"}
        </span>
      </div>
    </div>
  );
}

function MapFooter({ geoContext, radiusKm, markerCount, mode }: { geoContext: GeospatialMarketContext; radiusKm: number; markerCount: number; mode: "mapbox" | "openstreetmap" }) {
  return (
    <div className="grid gap-3 border-t border-border px-5 py-4 text-[11px] text-muted-foreground md:grid-cols-3">
      <div>
        <p className="font-mono uppercase tracking-widest text-muted-foreground">Coverage</p>
        <p className="mt-1 text-muted-foreground">{geoContext.radius_label ?? `${radiusKm} km analysis radius`}</p>
      </div>
      <div>
        <p className="font-mono uppercase tracking-widest text-muted-foreground">Evidence</p>
        <p className="mt-1 text-muted-foreground">{markerCount} map evidence marker(s)</p>
      </div>
      <div>
        <p className="font-mono uppercase tracking-widest text-muted-foreground">Map source</p>
        <p className="mt-1 text-muted-foreground">
          {mode === "mapbox"
            ? "Mapbox GL JS. Uses your free-tier public token."
            : "OpenStreetMap/CARTO tiles, free for demo use."}
        </p>
      </div>
    </div>
  );
}

function MapboxRenderer({ geoContext, center, radiusKm, markers }: { geoContext: GeospatialMarketContext; center: [number, number]; radiusKm: number; markers: NormalizedMarker[] }) {
  const mapContainerRef = useRef<HTMLDivElement | null>(null);
  const mapRef = useRef<mapboxgl.Map | null>(null);
  const markerRefs = useRef<mapboxgl.Marker[]>([]);
  const mapboxToken = import.meta.env.VITE_MAPBOX_TOKEN?.trim();

  useEffect(() => {
    if (!mapboxToken || !mapContainerRef.current || mapRef.current) return;

    mapboxgl.accessToken = mapboxToken;

    const map = new mapboxgl.Map({
      container: mapContainerRef.current,
      style: "mapbox://styles/mapbox/light-v11",
      center: [center[1], center[0]],
      zoom: 12,
      pitch: 0,
      bearing: 0,
      attributionControl: true,
    });

    map.addControl(new mapboxgl.NavigationControl({ visualizePitch: true }), "top-right");
    map.addControl(new mapboxgl.ScaleControl({ unit: "metric" }), "bottom-left");

    map.on("load", () => {
      map.addSource("analysis-radius", {
        type: "geojson",
        data: circlePolygon(center, radiusKm),
      });

      map.addLayer({
        id: "analysis-radius-fill",
        type: "fill",
        source: "analysis-radius",
        paint: {
          "fill-color": "#d93025",
          "fill-opacity": 0.14,
        },
      });

      map.addLayer({
        id: "analysis-radius-line",
        type: "line",
        source: "analysis-radius",
        paint: {
          "line-color": "#d93025",
          "line-opacity": 0.95,
          "line-width": 2.5,
        },
      });

      map.addSource("footfall-evidence-heatmap", {
        type: "geojson",
        data: footfallHeatmapGeoJson(geoContext),
      });

      map.addLayer({
        id: "footfall-evidence-heatmap-layer",
        type: "heatmap",
        source: "footfall-evidence-heatmap",
        maxzoom: 18,
        paint: {
          "heatmap-weight": [
            "interpolate",
            ["linear"],
            ["get", "intensity"],
            0,
            0.12,
            0.35,
            0.42,
            0.7,
            0.75,
            1,
            1,
          ],
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 10, 0.85, 13, 1.25, 16, 1.55],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 10, 34, 12, 58, 14, 88, 16, 118],
          "heatmap-opacity": 0.68,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(37,99,235,0)",
            0.16,
            "rgba(37,99,235,0.38)",
            0.38,
            "rgba(34,197,94,0.52)",
            0.62,
            "rgba(253,224,71,0.65)",
            0.82,
            "rgba(249,115,22,0.72)",
            1,
            "rgba(239,68,68,0.78)",
          ],
        },
      });
      map.moveLayer("analysis-radius-line");

      fitMapboxToRadius(map, center, radiusKm);
    });

    mapRef.current = map;

    return () => {
      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current = [];
      map.remove();
      mapRef.current = null;
    };
    // Create the map once. Scenario updates are handled in the next effect.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mapboxToken]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !mapboxToken) return;

    const updateMap = () => {
      map.resize();
      map.setCenter([center[1], center[0]]);

      const radiusSource = map.getSource("analysis-radius") as mapboxgl.GeoJSONSource | undefined;
      if (radiusSource) {
        radiusSource.setData(circlePolygon(center, radiusKm));
      }

      const footfallSource = map.getSource("footfall-evidence-heatmap") as mapboxgl.GeoJSONSource | undefined;
      if (footfallSource) {
        footfallSource.setData(footfallHeatmapGeoJson(geoContext));
      }

      markerRefs.current.forEach((marker) => marker.remove());
      markerRefs.current = [];

      const centerMarker = new mapboxgl.Marker({
        element: createMapboxPinElement("#d93025", 44),
        anchor: "bottom",
      })
        .setLngLat([center[1], center[0]])
        .addTo(map);

      markerRefs.current.push(centerMarker);

      markers.forEach((marker) => {
        const element = isTransitMarker(marker.type)
          ? createMapboxBusStopElement(30)
          : createMapboxPinElement(markerColor(marker.type), isCompetitorMarker(marker.type) ? 30 : 32);

        const mapMarker = new mapboxgl.Marker({
          element,
          anchor: isTransitMarker(marker.type) ? "center" : "bottom",
        })
          .setLngLat([marker.longitude, marker.latitude])
          .setPopup(new mapboxgl.Popup({ offset: 24 }).setHTML(popupHtmlForMarker(marker)))
          .addTo(map);

        markerRefs.current.push(mapMarker);
      });

      fitMapboxToRadius(map, center, radiusKm);
    };

    if (map.isStyleLoaded()) {
      updateMap();
    } else {
      map.once("load", updateMap);
    }
  }, [mapboxToken, center[0], center[1], radiusKm, geoContext, markers]);

  return (
    <div className="relative h-[460px] w-full bg-card">
      <div ref={mapContainerRef} className="h-full w-full" />
      <FootfallLegend geoContext={geoContext} />
    </div>
  );
}

function LeafletRenderer({ geoContext, center, radiusKm, markers }: { geoContext: GeospatialMarketContext; center: [number, number]; radiusKm: number; markers: NormalizedMarker[] }) {
  const mapKey = `${geoContext.municipality_name}-${geoContext.business_subcategory}-${radiusKm}-${center[0]}-${center[1]}`;
  const footfallPoints = normalizeFootfallPoints(geoContext);

  return (
    <div className="relative h-[460px] w-full bg-card">
      <MapContainer
        key={mapKey}
        center={center}
        zoom={13}
        scrollWheelZoom
        className="z-0 h-full w-full"
        style={{ height: "100%", width: "100%" }}
      >
        <TileLayer
          attribution='&copy; OpenStreetMap contributors &copy; CARTO'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />

        <FitLeafletToRadius center={center} radiusKm={radiusKm} />
        <LeafletFootfallHeatmap points={footfallPoints} />

        <Circle
          center={center}
          radius={radiusKm * 1000}
          pathOptions={{
            color: "#d93025",
            weight: 2,
            opacity: 0.95,
            fillColor: "#d93025",
            fillOpacity: 0.13,
          }}
        />

        <Marker position={center} icon={createLeafletPinIcon("#d93025", 44)} />

        {markers.map((marker) => (
          <Marker
            key={marker.id}
            position={[marker.latitude, marker.longitude]}
            icon={leafletIconForMarker(marker)}
          >
            <Popup>
              <div style={{ minWidth: 220, lineHeight: 1.5 }}>
                <strong>{marker.label}</strong>

                {isCompetitorMarker(marker.type) ? (
                  <>
                    <br />
                    {marker.address ? marker.address : "Address not available"}
                  </>
                ) : null}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
      <FootfallLegend geoContext={geoContext} />
    </div>
  );
}

export default function MarketMap({ geoContext, className = "" }: Props) {
  const center = getCenter(geoContext);
  const radiusKm = Number.isFinite(geoContext.radius_km) && geoContext.radius_km > 0 ? geoContext.radius_km : 5;
  const markers = useMemo(() => normalizeMarkers(geoContext), [geoContext]);
  const hasMapboxToken = Boolean(import.meta.env.VITE_MAPBOX_TOKEN?.trim());
  const mode = hasMapboxToken ? "mapbox" : "openstreetmap";

  return (
    <div className={`overflow-hidden rounded-lg border bg-card ${className}`}>
      <MapHeader geoContext={geoContext} radiusKm={radiusKm} mode={mode} />

      {hasMapboxToken ? (
        <MapboxRenderer geoContext={geoContext} center={center} radiusKm={radiusKm} markers={markers} />
      ) : (
        <LeafletRenderer geoContext={geoContext} center={center} radiusKm={radiusKm} markers={markers} />
      )}

      <MapFooter geoContext={geoContext} radiusKm={radiusKm} markerCount={markers.length} mode={mode} />
    </div>
  );
}
