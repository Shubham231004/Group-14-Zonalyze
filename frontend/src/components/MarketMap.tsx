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
      return isCompetitorMarker(marker.type) || isTransitMarker(marker.type);
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

function heatmapGeoJson(geoContext: GeospatialMarketContext) {
  const cells = Array.isArray(geoContext.heatmap_cells) ? geoContext.heatmap_cells : [];

  return {
    type: "FeatureCollection",
    features: cells
      .filter((cell: any) => isFiniteNumber(cell.latitude) && isFiniteNumber(cell.longitude))
      .map((cell: any, index: number) => ({
        type: "Feature",
        properties: {
          id: cell.cell_id ?? `heat-${index}`,
          label: cell.label ?? "Demand/risk cell",
          demand: Number(cell.demand_intensity ?? 50),
          risk: Number(cell.risk_intensity ?? 50),
        },
        geometry: {
          type: "Point",
          coordinates: [cell.longitude, cell.latitude],
        },
      })),
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
};

function normalizeFootfallPoints(geoContext: GeospatialMarketContext): FootfallPoint[] {
  const points = Array.isArray((geoContext as any).footfall_heatmap_points)
    ? ((geoContext as any).footfall_heatmap_points as any[])
    : [];

  return points
    .map((point: any, index: number): FootfallPoint | null => {
      const latitude = Number(point.latitude);
      const longitude = Number(point.longitude);
      const rawIntensity = Number(point.intensity ?? 0);

      if (!Number.isFinite(latitude) || !Number.isFinite(longitude)) return null;

      return {
        id: String(point.point_id ?? point.id ?? `footfall-${index}`),
        latitude,
        longitude,
        intensity: Math.max(0, Math.min(1, Number.isFinite(rawIntensity) ? rawIntensity : 0)),
        evidenceType: point.evidence_type,
        source: point.source,
        label: point.label,
        category: point.category,
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
        label: point.label ?? "Footfall evidence point",
        evidenceType: point.evidenceType ?? "public_activity_evidence",
        source: point.source ?? "OpenStreetMap / public map evidence",
        category: point.category ?? null,
      },
      geometry: {
        type: "Point",
        coordinates: [point.longitude, point.latitude],
      },
    })),
  } as any;
}

function footfallColor(intensity: number): string {
  // Soft, map-friendly palette: teal → warm amber → soft coral.
  // Avoids harsh red blobs while still showing relative footfall potential.
  if (intensity >= 0.78) return "#fb7185";
  if (intensity >= 0.58) return "#fbbf24";
  if (intensity >= 0.35) return "#fde68a";
  return "#5eead4";
}

function FootfallLegend({ geoContext }: { geoContext: GeospatialMarketContext }) {
  const points = normalizeFootfallPoints(geoContext);
  const status = (geoContext as any).footfall_heatmap_status || (points.length ? "available" : "not_available");
  const sources = Array.isArray((geoContext as any).footfall_heatmap_sources)
    ? ((geoContext as any).footfall_heatmap_sources as string[])
    : [];

  return (
    <div className="pointer-events-none absolute bottom-4 right-4 z-[5] w-[245px] rounded-xl border border-white/15 bg-slate-950/82 p-3 shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="text-[11px] font-semibold uppercase tracking-widest text-white/80">Footfall evidence</p>
          <p className="mt-0.5 text-[10px] text-white/45">Public activity-signal density</p>
        </div>
        <span className="rounded-full border border-white/15 px-2 py-0.5 text-[9px] font-mono uppercase text-white/65">
          {points.length} pts
        </span>
      </div>

      <div className="mt-3 h-3 rounded-full border border-white/20 bg-[linear-gradient(90deg,#5eead4_0%,#fde68a_42%,#fbbf24_70%,#fb7185_100%)] shadow-[0_0_12px_rgba(251,191,36,.18)]" />
      <div className="mt-1 flex justify-between text-[9px] font-mono uppercase text-white/55">
        <span>Lower</span>
        <span>Medium</span>
        <span>Higher</span>
      </div>

      <div className="mt-2 grid grid-cols-4 gap-1 text-[9px] font-mono uppercase text-white/70">
        <span className="rounded bg-teal-300/18 px-1.5 py-1 text-center text-teal-100">Low</span>
        <span className="rounded bg-amber-100/18 px-1.5 py-1 text-center text-amber-50">Med</span>
        <span className="rounded bg-amber-400/18 px-1.5 py-1 text-center text-amber-100">High</span>
        <span className="rounded bg-rose-300/18 px-1.5 py-1 text-center text-rose-100">Peak</span>
      </div>

      <p className="mt-2 text-[10px] leading-snug text-white/50">
        {points.length
          ? "Heat is generated from real public map evidence such as business POIs, transit points, and commercial activity clusters."
          : "No footfall evidence points were returned for this scenario."}
      </p>

      {sources.length ? (
        <p className="mt-1 truncate text-[9px] text-white/35">Sources: {sources.slice(0, 3).join(", ")}</p>
      ) : null}
      <p className="mt-1 text-[9px] text-white/35">Status: {String(status).replaceAll("_", " ")}</p>
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

function MapHeader({ geoContext, radiusKm, mode }: { geoContext: GeospatialMarketContext; radiusKm: number; mode: "mapbox" | "openstreetmap" }) {
  return (
    <div className="flex flex-col gap-2 border-b border-white/10 px-5 py-4 md:flex-row md:items-center md:justify-between">
      <div>
        <div className="flex items-center gap-2">
          <span className="h-2.5 w-2.5 rounded-full bg-red-500 shadow-[0_0_14px_rgba(239,68,68,.8)]" />
          <h3 className="text-sm font-semibold tracking-wide text-white/90">Market Map</h3>
        </div>
        <p className="mt-1 text-[11px] font-mono text-white/50">
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
    <div className="grid gap-3 border-t border-white/10 px-5 py-4 text-[11px] text-white/55 md:grid-cols-3">
      <div>
        <p className="font-mono uppercase tracking-widest text-white/35">Coverage</p>
        <p className="mt-1 text-white/70">{geoContext.radius_label ?? `${radiusKm} km analysis radius`}</p>
      </div>
      <div>
        <p className="font-mono uppercase tracking-widest text-white/35">Evidence</p>
        <p className="mt-1 text-white/70">{markerCount} map evidence marker(s)</p>
      </div>
      <div>
        <p className="font-mono uppercase tracking-widest text-white/35">Map source</p>
        <p className="mt-1 text-white/70">
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
      style: "mapbox://styles/mapbox/streets-v12",
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

      map.addSource("heatmap-cells", {
        type: "geojson",
        data: heatmapGeoJson(geoContext),
      });

      map.addLayer({
        id: "heatmap-cells-layer",
        type: "circle",
        source: "heatmap-cells",
        paint: {
          "circle-radius": 18,
          "circle-color": [
            "case",
            [">", ["get", "risk"], 70],
            "#d93025",
            [">", ["get", "demand"], 65],
            "#188038",
            "#f9ab00",
          ],
          "circle-opacity": 0.14,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 1,
          "circle-stroke-opacity": 0.25,
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
        maxzoom: 16,
        paint: {
          "heatmap-weight": [
            "interpolate",
            ["linear"],
            ["get", "intensity"],
            0,
            0.18,
            0.35,
            0.42,
            0.7,
            0.75,
            1,
            0.95,
          ],
          "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 10, 0.72, 13, 1.05, 15, 1.35],
          "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 10, 18, 12, 34, 14, 54, 16, 74],
          "heatmap-opacity": 0.48,
          "heatmap-color": [
            "interpolate",
            ["linear"],
            ["heatmap-density"],
            0,
            "rgba(94,234,212,0)",
            0.22,
            "rgba(94,234,212,0.32)",
            0.46,
            "rgba(253,230,138,0.46)",
            0.7,
            "rgba(251,191,36,0.52)",
            1,
            "rgba(251,113,133,0.58)",
          ],
        },
      });

      map.addLayer({
        id: "footfall-evidence-point-glow",
        type: "circle",
        source: "footfall-evidence-heatmap",
        minzoom: 10,
        paint: {
          "circle-radius": ["interpolate", ["linear"], ["get", "intensity"], 0, 5, 0.5, 8, 1, 12],
          "circle-color": [
            "interpolate",
            ["linear"],
            ["get", "intensity"],
            0,
            "#5eead4",
            0.38,
            "#fde68a",
            0.65,
            "#fbbf24",
            1,
            "#fb7185",
          ],
          "circle-opacity": 0.28,
          "circle-stroke-color": "#ffffff",
          "circle-stroke-width": 0.6,
          "circle-stroke-opacity": 0.38,
        },
      });

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

      const heatmapSource = map.getSource("heatmap-cells") as mapboxgl.GeoJSONSource | undefined;
      if (heatmapSource) {
        heatmapSource.setData(heatmapGeoJson(geoContext));
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
    <div className="relative h-[460px] w-full bg-slate-900">
      <div ref={mapContainerRef} className="h-full w-full" />
      <FootfallLegend geoContext={geoContext} />
    </div>
  );
}

function LeafletRenderer({ geoContext, center, radiusKm, markers }: { geoContext: GeospatialMarketContext; center: [number, number]; radiusKm: number; markers: NormalizedMarker[] }) {
  const mapKey = `${geoContext.municipality_name}-${geoContext.business_subcategory}-${radiusKm}-${center[0]}-${center[1]}`;
  const footfallPoints = normalizeFootfallPoints(geoContext);

  return (
    <div className="relative h-[460px] w-full bg-slate-900">
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

        {footfallPoints.map((point) => (
          <Circle
            key={point.id}
            center={[point.latitude, point.longitude]}
            radius={75 + point.intensity * 190}
            pathOptions={{
              color: footfallColor(point.intensity),
              weight: 1,
              opacity: 0.46,
              fillColor: footfallColor(point.intensity),
              fillOpacity: 0.16 + point.intensity * 0.16,
            }}
          >
            <Popup>
              <div style={{ minWidth: 200, lineHeight: 1.5 }}>
                <strong>{point.label || "Footfall evidence"}</strong>
                <br />
                Intensity: {Math.round(point.intensity * 100)}%
                <br />
                Source: {point.source || "OpenStreetMap / public map evidence"}
              </div>
            </Popup>
          </Circle>
        ))}

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
    <div className={`overflow-hidden rounded-lg border bg-slate-950 ${className}`}>
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
