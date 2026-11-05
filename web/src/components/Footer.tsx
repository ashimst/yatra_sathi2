import React from 'react';
import { Link } from 'react-router-dom';
import { 
  Compass, 
  BookOpen, 
  Cpu, 
  ExternalLink, 
  ArrowUpRight
} from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="w-full bg-[#FAF4ED]/90 backdrop-blur-md border-t border-[#E8DDD3] mt-auto">
      {/* Traditional Himalayan Prayer Flag Harmonic Ribbon */}
      <div className="h-1 w-full flex">
        <div className="flex-1 bg-[#1A73E8]" title="Sky / Space" />
        <div className="flex-1 bg-[#FFFFFF] border-y border-[#E8DDD3]" title="Air / Wind" />
        <div className="flex-1 bg-[#D93025]" title="Fire" />
        <div className="flex-1 bg-[#188038]" title="Water" />
        <div className="flex-1 bg-[#F9AB00]" title="Earth" />
      </div>

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-14 pb-8 space-y-12">
        {/* Main Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-8 lg:gap-10">
          
          {/* Col 1 & 2: Brand & Mission */}
          <div className="lg:col-span-2 space-y-4">
            <Link to="/" className="inline-flex flex-col group">
              <div className="flex items-baseline gap-2">
                <span className="font-serif-yatra font-bold text-2xl text-[#201A18] tracking-tight group-hover:text-[#9D3E19] transition-colors">
                  YatraSathi
                </span>
                <span className="font-serif-yatra font-bold text-2xl text-[#9D3E19]">
                  यात्रा साथी
                </span>
              </div>
              <span className="text-[10px] uppercase font-bold text-[#8A726A] tracking-widest mt-0.5">
                Verified Himalayan Expedition &amp; Cultural Platform
              </span>
            </Link>

            <p className="text-xs text-[#56423B] leading-relaxed max-w-sm">
              Empowering mindful exploration across Nepal’s high-altitude corridors. Curated in collaboration with licensed alpine guides, local sherpa teahouse collectives, and cultural heritage guardians.
            </p>

            {/* Live Field Status Badge */}
            <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/80 backdrop-blur-sm border border-white/60 shadow-xs text-[11px] text-[#201A18]">
              <span className="w-2 h-2 rounded-full bg-[#1D705C] animate-pulse" />
              <span className="font-semibold text-[#1D705C]">Live Field Sentinel Active</span>
              <span className="text-[#8A726A]">• 14 Mountain Passes</span>
            </div>
          </div>

          {/* Col 3: Expeditions & Navigation */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-[#201A18] uppercase tracking-wider flex items-center gap-1.5">
              <Compass className="w-3.5 h-3.5 text-[#9D3E19]" />
              <span>Expeditions</span>
            </h4>
            <ul className="space-y-2 text-xs text-[#56423B]">
              <li>
                <Link to="/plan" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Custom Itinerary Planner</span>
                </Link>
              </li>
              <li>
                <Link to="/explore" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Himalayan Sanctuaries &amp; Trails</span>
                </Link>
              </li>
              <li>
                <Link to="/trail-watch" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Trail Watch &amp; Hazard Radar</span>
                </Link>
              </li>
              <li>
                <Link to="/map" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Interactive Nepal Atlas</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 4: Culture & Field Archives */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-[#201A18] uppercase tracking-wider flex items-center gap-1.5">
              <BookOpen className="w-3.5 h-3.5 text-[#D97706]" />
              <span>Heritage &amp; Lore</span>
            </h4>
            <ul className="space-y-2 text-xs text-[#56423B]">
              <li>
                <Link to="/cultural-sanctuary" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Cultural Sanctuary Directory</span>
                </Link>
              </li>
              <li>
                <Link to="/yatra-smriti" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Yatra Smriti (Field Scrapbook)</span>
                </Link>
              </li>
              <li>
                <Link to="/trail-watch" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Porter Welfare &amp; Safety Protocol</span>
                </Link>
              </li>
              <li>
                <Link to="/trail-watch" className="hover:text-[#9D3E19] transition-colors flex items-center gap-1">
                  <span>Leave No Trace Charter</span>
                </Link>
              </li>
            </ul>
          </div>

          {/* Col 5: Engineering & Dedicated Architecture Link */}
          <div className="space-y-3">
            <h4 className="text-xs font-bold text-[#201A18] uppercase tracking-wider flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-[#1D705C]" />
              <span>Technical Whitepaper</span>
            </h4>
            <div className="p-3.5 rounded-xl bg-white/70 backdrop-blur-md border border-white/60 shadow-xs space-y-2">
              <div className="text-[11px] font-bold text-[#201A18]">
                Underlying Systems
              </div>
              <p className="text-[11px] text-[#56423B] leading-relaxed">
                Curious about how YatraSathi is engineered under the hood? Explore our comprehensive system architecture whitepaper and engineering design.
              </p>
              <Link
                to="/architecture"
                className="inline-flex items-center gap-1 text-xs font-bold text-[#9D3E19] hover:text-[#BD552F] group pt-1"
              >
                <span>System Architecture &amp; Whitepaper</span>
                <ArrowUpRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Link>
            </div>
          </div>
        </div>

        {/* Company Attribution & Noesis Frameworks Feature Box */}
        <div className="p-5 sm:p-6 rounded-2xl bg-white/80 backdrop-blur-md border border-white/60 shadow-sm flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-3.5 text-center md:text-left">
            <div className="w-10 h-10 rounded-xl bg-[#201A18] text-white flex items-center justify-center font-mono font-bold text-sm shrink-0 shadow-xs">
              NF
            </div>
            <div>
              <div className="text-xs font-bold text-[#201A18] flex items-center gap-2 justify-center md:justify-start">
                <span>Crafted under Noesis Frameworks</span>
                <span className="px-2 py-0.5 rounded-md bg-[#FDF1EC] text-[#9D3E19] text-[10px] font-extrabold uppercase">
                  noesisframeworks.com
                </span>
              </div>
              <div className="text-[11px] text-[#56423B] mt-0.5">
                A Noesis Frameworks Company • Pioneering Intelligent Spatial &amp; Autonomous Agent Infrastructures
              </div>
            </div>
          </div>

          <a
            href="https://noesisframeworks.com"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#201A18] hover:bg-[#382D2A] text-white text-xs font-bold transition-all shadow-sm group whitespace-nowrap cursor-pointer"
          >
            <span>Visit noesisframeworks.com</span>
            <ExternalLink className="w-3.5 h-3.5 text-amber-300 group-hover:scale-110 transition-transform" />
          </a>
        </div>

        {/* Bottom Legal / Copyright Bar */}
        <div className="pt-6 border-t border-[#E8DDD3] flex flex-col sm:flex-row items-center justify-between gap-3 text-[11px] text-[#8A726A]">
          <div>
            © 2026 YatraSathi Nepal (यात्रा साथी) • Engineered by Noesis Frameworks. All rights reserved.
          </div>
          <div className="flex flex-wrap items-center gap-4">
            <Link to="/architecture" className="hover:text-[#9D3E19] transition-colors">
              Engineering Specs
            </Link>
            <Link to="/cultural-sanctuary" className="hover:text-[#9D3E19] transition-colors">
              Heritage Rights
            </Link>
            <Link to="/trail-watch" className="hover:text-[#9D3E19] transition-colors">
              Field Safety
            </Link>
            <a
              href="https://noesisframeworks.com"
              target="_blank"
              rel="noopener noreferrer"
              className="text-[#9D3E19] hover:underline font-semibold"
            >
              Noesis Frameworks
            </a>
          </div>
        </div>
      </div>
    </footer>
  );
};
