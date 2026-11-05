import React, { useState } from 'react';
import { MapView } from '../components/MapView';
import { Navigation } from 'lucide-react';

const POPULAR_PINS = [
  { name: 'Kathmandu Durbar Square', category: 'Heritage', latitude: 27.7042, longitude: 85.3068 },
  { name: 'Swayambhunath Stupa', category: 'Religious Site', latitude: 27.7149, longitude: 85.2904 },
  { name: 'Boudhanath Stupa', category: 'Religious Site', latitude: 27.7215, longitude: 85.3620 },
  { name: 'Phewa Lake', category: 'Lake', latitude: 28.2167, longitude: 83.9500 },
  { name: 'Sarangkot Viewpoint', category: 'Viewpoint', latitude: 28.2458, longitude: 83.9486 },
  { name: 'Peace Pagoda Pokhara', category: 'Monastery', latitude: 28.2006, longitude: 83.9442 },
  { name: 'Chitwan National Park', category: 'Wildlife', latitude: 27.5291, longitude: 84.3542 },
];

export const MapPage: React.FC = () => {
  const [center, setCenter] = useState<[number, number]>([28.0, 84.5]);
  const [zoom, setZoom] = useState(8);

  const jumpTo = (lat: number, lng: number, zoomLevel = 13) => {
    setCenter([lat, lng]);
    setZoom(zoomLevel);
  };

  return (
    <div className="h-[calc(100vh-72px)] w-full flex flex-col relative bg-[#F5F0E8]">
      {/* Quick Jump Bar */}
      <div className="absolute top-4 left-4 z-[400] bg-white/85 backdrop-blur-xl p-2.5 rounded-2xl shadow-[0_8px_30px_rgba(42,36,33,0.08)] border border-white/70 flex items-center gap-1.5 overflow-x-auto text-xs max-w-[90vw]">
        <div className="px-2 text-[#6B6B6B] font-bold uppercase text-[10px] flex items-center gap-1">
          <Navigation className="w-3.5 h-3.5 text-[#CC5200]" />
          <span>Quick Region:</span>
        </div>
        <button
          onClick={() => jumpTo(27.7172, 85.3240, 12)}
          className="px-3.5 py-1.5 rounded-xl bg-[#FAF7F2] hover:bg-[#CC5200] hover:text-white font-semibold text-[#1A1A1A] transition-all cursor-pointer border border-[#E0DAD0]"
        >
          Kathmandu Valley
        </button>
        <button
          onClick={() => jumpTo(28.2096, 83.9856, 12)}
          className="px-3.5 py-1.5 rounded-xl bg-[#FAF7F2] hover:bg-[#CC5200] hover:text-white font-semibold text-[#1A1A1A] transition-all cursor-pointer border border-[#E0DAD0]"
        >
          Pokhara &amp; Lakes
        </button>
        <button
          onClick={() => jumpTo(27.5291, 84.3542, 11)}
          className="px-3.5 py-1.5 rounded-xl bg-[#FAF7F2] hover:bg-[#CC5200] hover:text-white font-semibold text-[#1A1A1A] transition-all cursor-pointer border border-[#E0DAD0]"
        >
          Chitwan Jungle
        </button>
        <button
          onClick={() => jumpTo(28.0, 84.5, 8)}
          className="px-3.5 py-1.5 rounded-xl bg-[#FAF7F2] hover:bg-[#CC5200] hover:text-white font-semibold text-[#1A1A1A] transition-all cursor-pointer border border-[#E0DAD0]"
        >
          Reset All Nepal
        </button>
      </div>

      {/* Map View */}
      <div className="flex-1 w-full h-full p-2">
        <MapView
          center={center}
          zoom={zoom}
          activities={POPULAR_PINS as any}
        />
      </div>
    </div>
  );
};
