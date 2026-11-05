import React, { useEffect } from 'react';
import { MapContainer, TileLayer, Marker, Popup, Polyline, useMap } from 'react-leaflet';
import L from 'leaflet';
import type { Activity, OvernightAccommodation, Meal } from '../types';

// Category color resolver matching mobile Flutter constants
export const getCategoryColor = (category?: string): string => {
  const cat = category?.toLowerCase() || '';
  if (cat.includes('temple') || cat.includes('worship') || cat.includes('pilgrimage') || cat.includes('monastery') || cat.includes('stupa')) {
    return '#CC5200'; // Warm Nepali Terracotta
  }
  if (cat.includes('mountain') || cat.includes('peak') || cat.includes('hiking') || cat.includes('trek')) {
    return '#E53935'; // Himalayan Red
  }
  if (cat.includes('museum') || cat.includes('landmark') || cat.includes('heritage') || cat.includes('square')) {
    return '#7B1FA2'; // Cultural Purple
  }
  if (cat.includes('lake') || cat.includes('river') || cat.includes('park') || cat.includes('nature') || cat.includes('preserve')) {
    return '#1D705C'; // Forest Teal
  }
  if (cat.includes('hotel') || cat.includes('resort') || cat.includes('lodge')) {
    return '#B45309'; // Warm Amber
  }
  return '#E87340'; // Warm Coral
};

// Create custom pin icons matching the mobile app aesthetic
const createPinIcon = (color: string, label?: string) => {
  return L.divIcon({
    className: 'custom-yatra-pin',
    html: `
      <div style="
        position: relative;
        display: flex;
        align-items: center;
        justify-content: center;
        width: 32px;
        height: 32px;
        background: ${color};
        color: white;
        border-radius: 50% 50% 50% 4px;
        transform: rotate(-45deg);
        border: 2.5px solid white;
        box-shadow: 0 4px 12px rgba(26,26,26,0.3);
      ">
        <div style="
          transform: rotate(45deg);
          font-size: 11px;
          font-weight: 700;
          font-family: 'Inter', sans-serif;
        ">
          ${label ? label.slice(0, 1) : '•'}
        </div>
      </div>
    `,
    iconSize: [32, 32],
    iconAnchor: [16, 32],
    popupAnchor: [0, -32],
  });
};

const startIcon = createPinIcon('#1D705C', 'S'); // Start (Teal)
const endIcon = createPinIcon('#E53935', 'E');   // End (Red)
const hotelIcon = createPinIcon('#B45309', 'H'); // Hotel (Amber)
const mealIcon = createPinIcon('#D97706', 'M');  // Meal (Orange)

export interface MapMemoryItem {
  id: string;
  place_name?: string;
  image_url: string;
  caption?: string;
  ai_reflection?: string;
  latitude?: number;
  longitude?: number;
}

const createPhotoPinIcon = (thumbnailUrl: string) => {
  return L.divIcon({
    className: 'custom-photo-pin',
    html: `
      <div style="
        position: relative;
        width: 38px;
        height: 44px;
        background: #FFFFFF;
        padding: 2.5px;
        padding-bottom: 8px;
        border-radius: 5px;
        box-shadow: 0 4px 14px rgba(26,26,26,0.35);
        border: 2px solid #CC5200;
        cursor: pointer;
      ">
        <img src="${thumbnailUrl}" style="width: 100%; height: 29px; object-fit: cover; border-radius: 2px; display: block;" />
        <div style="
          position: absolute;
          bottom: -7px;
          left: 50%;
          transform: translateX(-50%);
          width: 0;
          height: 0;
          border-left: 5px solid transparent;
          border-right: 5px solid transparent;
          border-top: 6px solid #CC5200;
        "></div>
      </div>
    `,
    iconSize: [38, 44],
    iconAnchor: [19, 44],
    popupAnchor: [0, -44],
  });
};

interface MapViewProps {
  routeCoordinates?: [number, number][]; // [lat, lng]
  activities?: Activity[];
  meals?: Meal[];
  overnight?: OvernightAccommodation | null;
  origin?: { lat: number; lng: number; name: string };
  destination?: { lat: number; lng: number; name: string };
  memories?: MapMemoryItem[];
  center?: [number, number];
  zoom?: number;
}

// Auto-fit bounds component
const BoundsFitter: React.FC<{ points: [number, number][] }> = ({ points }) => {
  const map = useMap();
  useEffect(() => {
    if (points.length > 0) {
      const bounds = L.latLngBounds(points);
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14 });
    }
  }, [points, map]);
  return null;
};

export const MapView: React.FC<MapViewProps> = ({
  routeCoordinates = [],
  activities = [],
  meals = [],
  overnight,
  origin,
  destination,
  memories = [],
  center = [28.3949, 84.1240], // Central Nepal default
  zoom = 7.5,
}) => {
  // Collect all points to fit map bounds
  const allPoints: [number, number][] = [];
  if (origin) allPoints.push([origin.lat, origin.lng]);
  if (destination) allPoints.push([destination.lat, destination.lng]);
  if (overnight?.latitude && overnight?.longitude) {
    allPoints.push([overnight.latitude, overnight.longitude]);
  }
  activities.forEach((a) => {
    if (a.latitude && a.longitude) allPoints.push([a.latitude, a.longitude]);
  });
  meals.forEach((m) => {
    if (m.latitude && m.longitude) allPoints.push([m.latitude, m.longitude]);
  });
  memories.forEach((mem) => {
    if (mem.latitude && mem.longitude) allPoints.push([mem.latitude, mem.longitude]);
  });

  // Normalize OSRM GeoJSON [longitude, latitude] into Leaflet [latitude, longitude]
  const normalizedRouteCoords: [number, number][] = (routeCoordinates || []).map((pt) => {
    if (!pt || pt.length < 2) return [0, 0];
    // In Nepal / South Asia, longitude is ~80-88, latitude is ~26-31.
    // If pt[0] > 45, it is GeoJSON [lng, lat], so swap to [lat, lng].
    if (pt[0] > 45 && pt[1] < 45) {
      return [pt[1], pt[0]];
    }
    return [pt[0], pt[1]];
  });

  return (
    <div className="w-full h-full relative rounded-2xl overflow-hidden shadow-sm border border-[#E0DAD0] bg-[#F5F0E8]">
      <MapContainer
        center={center}
        zoom={zoom}
        scrollWheelZoom={true}
        className="w-full h-full"
      >
        {/* Clean, beautiful standard OpenStreetMap tiles matching Flutter mobile app (Zero API Keys required) */}
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
          url="https://tile.openstreetmap.org/{z}/{x}/{y}.png"
          maxZoom={19}
        />

        {/* Fit Bounds */}
        <BoundsFitter points={allPoints.length > 0 ? allPoints : normalizedRouteCoords} />

        {/* Route Polyline in warm Nepal Terracotta (#CC5200) matching Flutter */}
        {normalizedRouteCoords.length > 1 && (
          <>
            <Polyline
              positions={normalizedRouteCoords}
              pathOptions={{ color: '#FFFFFF', weight: 8, opacity: 0.9 }}
            />
            <Polyline
              positions={normalizedRouteCoords}
              pathOptions={{ color: '#CC5200', weight: 5, opacity: 1.0 }}
            />
          </>
        )}

        {/* Origin Marker */}
        {origin && (
          <Marker position={[origin.lat, origin.lng]} icon={startIcon}>
            <Popup>
              <div className="font-sans p-1">
                <span className="text-[10px] font-bold text-[#1D705C] uppercase tracking-wider">
                  Journey Origin
                </span>
                <p className="font-bold text-[#1A1A1A] text-sm font-serif-yatra mt-0.5">{origin.name}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Destination Marker */}
        {destination && (
          <Marker position={[destination.lat, destination.lng]} icon={endIcon}>
            <Popup>
              <div className="font-sans p-1">
                <span className="text-[10px] font-bold text-[#E53935] uppercase tracking-wider">
                  Destination
                </span>
                <p className="font-bold text-[#1A1A1A] text-sm font-serif-yatra mt-0.5">{destination.name}</p>
              </div>
            </Popup>
          </Marker>
        )}

        {/* Overnight Hotel Marker */}
        {overnight?.latitude && overnight?.longitude && (
          <Marker position={[overnight.latitude, overnight.longitude]} icon={hotelIcon}>
            <Popup>
              <div className="font-sans p-1 max-w-xs">
                {overnight.image_url && (
                  <div className="h-24 w-full rounded-lg overflow-hidden bg-stone-100 mb-1.5">
                    <img src={overnight.image_url} alt={overnight.name} className="w-full h-full object-cover" />
                  </div>
                )}
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold text-[#B45309] uppercase tracking-wider">
                    Night Stay Lodge
                  </span>
                  {overnight.price_level && (
                    <span className="text-[10px] font-bold text-[#8A726A]">{overnight.price_level}</span>
                  )}
                </div>
                <p className="font-bold text-[#1A1A1A] text-sm font-serif-yatra mt-0.5">{overnight.name}</p>
                {overnight.description && (
                  <p className="text-xs text-[#6B6B6B] mt-1 line-clamp-2 leading-relaxed">{overnight.description}</p>
                )}
                {overnight.must_try && (
                  <p className="text-[10px] text-[#9D3E19] font-medium mt-1">✨ {overnight.must_try}</p>
                )}
              </div>
            </Popup>
          </Marker>
        )}

        {/* Activities Markers */}
        {activities.map((act, idx) => {
          if (!act.latitude || !act.longitude) return null;
          const markerColor = getCategoryColor(act.category);
          const icon = createPinIcon(markerColor, `${idx + 1}`);

          return (
            <Marker key={`act-${idx}`} position={[act.latitude, act.longitude]} icon={icon}>
              <Popup>
                <div className="font-sans max-w-xs p-1">
                  {act.image_url && (
                    <div className="h-24 w-full rounded-lg overflow-hidden bg-stone-100 mb-1.5 relative">
                      <img src={act.image_url} alt={act.name} className="w-full h-full object-cover" />
                      {act.is_hidden_gem && (
                        <span className="absolute top-1 left-1 text-[9px] font-bold bg-emerald-600/90 text-white px-1.5 py-0.5 rounded-full backdrop-blur-xs">
                          💎 Hidden Gem
                        </span>
                      )}
                    </div>
                  )}
                  <div className="flex items-center gap-2">
                    <span
                      className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full"
                      style={{ backgroundColor: `${markerColor}18`, color: markerColor }}
                    >
                      {act.category || 'Spot'} {act.start_time ? `• ${act.start_time}` : ''}
                    </span>
                  </div>
                  <p className="font-bold text-[#1A1A1A] text-sm font-serif-yatra mt-1">{act.name}</p>
                  {act.description && (
                    <p className="text-xs text-[#6B6B6B] mt-1 line-clamp-2 leading-relaxed">
                      {act.description}
                    </p>
                  )}
                  {act.must_try && (
                    <p className="text-[10px] text-[#9D3E19] font-medium mt-1">✨ {act.must_try}</p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}

        {/* Meals Markers */}
        {meals.map((meal, idx) => {
          if (!meal.latitude || !meal.longitude) return null;
          return (
            <Marker key={`meal-${idx}`} position={[meal.latitude, meal.longitude]} icon={mealIcon}>
              <Popup>
                <div className="font-sans p-1 max-w-xs">
                  {meal.image_url && (
                    <div className="h-20 w-full rounded-lg overflow-hidden bg-stone-100 mb-1.5">
                      <img src={meal.image_url} alt={meal.name} className="w-full h-full object-cover" />
                    </div>
                  )}
                  <div className="flex items-center justify-between">
                    <span className="text-[10px] font-bold text-[#D97706] uppercase tracking-wider">
                      {meal.meal_type.toUpperCase()} STOP
                    </span>
                    {meal.price_level && (
                      <span className="text-[10px] font-bold text-[#8A726A]">{meal.price_level}</span>
                    )}
                  </div>
                  <p className="font-bold text-[#1A1A1A] text-sm font-serif-yatra mt-0.5">{meal.name}</p>
                  {meal.must_try && (
                    <p className="text-[10px] text-[#9D3E19] font-medium mt-1">🍽️ {meal.must_try}</p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
        {/* Memories / Photo Scrapbook Pins */}
        {memories.map((mem) => {
          if (!mem.latitude || !mem.longitude) return null;
          return (
            <Marker
              key={`mem-${mem.id}`}
              position={[mem.latitude, mem.longitude]}
              icon={createPhotoPinIcon(mem.image_url)}
            >
              <Popup>
                <div className="font-sans max-w-xs p-1">
                  <span className="text-[10px] font-bold text-[#CC5200] uppercase tracking-wider bg-[#CC5200]/10 px-2 py-0.5 rounded-full">
                    Travel Memory
                  </span>
                  <div className="mt-1.5 aspect-video w-full rounded-lg overflow-hidden bg-black/10">
                    <img
                      src={mem.image_url}
                      alt={mem.place_name || 'Memory'}
                      className="w-full h-full object-cover"
                    />
                  </div>
                  {mem.place_name && (
                    <p className="font-bold text-[#1A1A1A] text-sm font-serif-yatra mt-1.5">
                      {mem.place_name}
                    </p>
                  )}
                  {mem.caption && (
                    <p className="text-xs text-[#6B6B6B] mt-0.5 leading-relaxed">
                      {mem.caption}
                    </p>
                  )}
                  {mem.ai_reflection && (
                    <p className="text-[11px] text-[#CC5200] italic font-serif-yatra mt-1.5 leading-snug">
                      "{mem.ai_reflection}"
                    </p>
                  )}
                </div>
              </Popup>
            </Marker>
          );
        })}
      </MapContainer>

      {/* Clean Homely Legend Floating Badge (Bottom-Left) */}
      <div className="absolute bottom-4 left-4 z-[400] bg-white/95 backdrop-blur-md px-3.5 py-2.5 rounded-xl shadow-md border border-[#E0DAD0] text-xs flex flex-wrap gap-3 items-center">
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#CC5200]"></span>
          <span className="text-[#1A1A1A] text-[11px] font-medium">Temples</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#E53935]"></span>
          <span className="text-[#1A1A1A] text-[11px] font-medium">Peaks / Trails</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#1D705C]"></span>
          <span className="text-[#1A1A1A] text-[11px] font-medium">Lakes / Parks</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#7B1FA2]"></span>
          <span className="text-[#1A1A1A] text-[11px] font-medium">Heritage</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-2.5 h-2.5 rounded-full bg-[#B45309]"></span>
          <span className="text-[#1A1A1A] text-[11px] font-medium">Stay</span>
        </div>
        {memories.length > 0 && (
          <div className="flex items-center gap-1.5">
            <span className="w-2.5 h-2.5 rounded-full bg-[#CC5200] border border-white ring-1 ring-[#CC5200]"></span>
            <span className="text-[#CC5200] text-[11px] font-bold">Photos ({memories.length})</span>
          </div>
        )}
      </div>
    </div>
  );
};
