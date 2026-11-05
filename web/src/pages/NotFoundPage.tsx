import type { FC } from 'react';
import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Compass, Home, Map, Route, Cpu, ShieldAlert, ArrowLeft } from 'lucide-react';

export const NotFoundPage: FC = () => {
  return (
    <div className="min-h-[82vh] flex items-center justify-center px-4 py-16 bg-[#FFF8F6]">
      <motion.div 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="max-w-2xl w-full text-center space-y-8"
      >
        {/* Status Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#9D3E19] text-xs font-bold uppercase tracking-widest shadow-2xs">
          <ShieldAlert className="w-4 h-4 text-[#9D3E19]" />
          <span>Error 404 • Uncharted Elevation</span>
        </div>

        {/* Hero Title */}
        <div className="space-y-3">
          <div className="text-7xl sm:text-8xl font-serif-yatra font-bold text-[#9D3E19] tracking-tighter opacity-90">
            404
          </div>
          <h1 className="text-3xl sm:text-4xl font-serif-yatra font-bold text-[#201A18] tracking-tight">
            You've Ventured <span className="italic text-[#9D3E19]">Beyond the Trail</span>
          </h1>
          <p className="text-sm sm:text-base text-[#56423B] leading-relaxed max-w-lg mx-auto">
            The path or waypoint you are seeking is not recorded in our surveyed GIS ledgers. 
            It might be blocked by a high pass closure or moved to a different coordinate.
          </p>
        </div>

        {/* Action Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-3 pt-2">
          <Link
            to="/"
            className="px-6 py-3 rounded-xl bg-[#9D3E19] text-white font-bold text-sm shadow-md hover:bg-[#803012] transition-all flex items-center gap-2 cursor-pointer"
          >
            <Home className="w-4 h-4" />
            <span>Return to Basecamp (Home)</span>
          </Link>
          <Link
            to="/plan"
            className="px-6 py-3 rounded-xl bg-[#FDF1EC] text-[#56423B] font-bold text-sm border border-[#E8DDD3] hover:bg-[#F8EBE6] hover:text-[#201A18] transition-all flex items-center gap-2 cursor-pointer"
          >
            <Compass className="w-4 h-4 text-[#9D3E19]" />
            <span>Plan an Expedition</span>
          </Link>
        </div>

        {/* Waypoint Recovery Cards */}
        <div className="pt-6 border-t border-[#E8DDD3]/80">
          <div className="text-xs uppercase font-bold tracking-wider text-[#8A726A] mb-4">
            Established Basecamp Waypoints
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-left">
            <Link
              to="/explore"
              className="p-4 rounded-2xl bg-white/80 border border-[#E8DDD3] hover:border-[#9D3E19] hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2 text-xs font-bold text-[#201A18] group-hover:text-[#9D3E19]">
                <Route className="w-4 h-4 text-[#9D3E19]" />
                <span>Explore 7,700+ POIs</span>
              </div>
              <p className="text-[11px] text-[#56423B] mt-1">
                Verified tea houses, viewpoints, and lodges across Nepal.
              </p>
            </Link>

            <Link
              to="/map"
              className="p-4 rounded-2xl bg-white/80 border border-[#E8DDD3] hover:border-[#9D3E19] hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2 text-xs font-bold text-[#201A18] group-hover:text-[#9D3E19]">
                <Map className="w-4 h-4 text-[#1D705C]" />
                <span>Interactive GIS Map</span>
              </div>
              <p className="text-[11px] text-[#56423B] mt-1">
                Topographic Leaflet corridor routing and elevation profiles.
              </p>
            </Link>

            <Link
              to="/info"
              className="p-4 rounded-2xl bg-white/80 border border-[#E8DDD3] hover:border-[#9D3E19] hover:shadow-xs transition-all group cursor-pointer"
            >
              <div className="flex items-center gap-2 text-xs font-bold text-[#201A18] group-hover:text-[#9D3E19]">
                <Cpu className="w-4 h-4 text-[#D97706]" />
                <span>System Architecture</span>
              </div>
              <p className="text-[11px] text-[#56423B] mt-1">
                Noesis dual-process cognitive pipeline and ADRs.
              </p>
            </Link>
          </div>
        </div>

        <div className="text-xs text-[#8A726A] flex items-center justify-center gap-1">
          <ArrowLeft className="w-3.5 h-3.5" />
          <button 
            onClick={() => window.history.back()} 
            className="hover:underline font-medium text-[#56423B] cursor-pointer"
          >
            Go back to your previous page
          </button>
        </div>
      </motion.div>
    </div>
  );
};
