import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Sparkles, 
  Calendar, 
  Compass, 
  ArrowRight, 
  ShieldCheck, 
  Mountain
} from 'lucide-react';
import { motion } from 'framer-motion';
import { apiUrl } from '../api/config';
import { DEPARTURE_HUB_GROUPS, DESTINATION_CORRIDOR_GROUPS } from '../data/nepalLocations';
import { HimalayanPeaksCanvas } from '../components/HimalayanPeaksCanvas';

export const HomePage: React.FC = () => {
  const navigate = useNavigate();

  // Live Telemetry State
  const [telemetry, setTelemetry] = useState<any>(null);

  useEffect(() => {
    fetch(apiUrl('/telemetry'))
      .then(res => res.json())
      .then(data => setTelemetry(data))
      .catch(err => console.warn('Telemetry fetch error:', err));
  }, []);

  // Expedition Builder State
  const [startingPoint, setStartingPoint] = useState('Kathmandu');
  const [destination, setDestination] = useState('Pokhara');
  const [duration, setDuration] = useState(3);
  const [pace, setPace] = useState('Balanced (~3 stops/day)');
  const [selectedInterests, setSelectedInterests] = useState<string[]>([
    'Sightseeing',
    'Culture & Monasteries',
    'Nature & Lakes',
    'Local Food & Chai'
  ]);

  const interestOptions = [
    { id: 'Sightseeing', label: 'Sightseeing' },
    { id: 'Culture & Monasteries', label: 'Culture & Monasteries' },
    { id: 'Nature & Lakes', label: 'Nature & Lakes' },
    { id: 'Alpine Hiking', label: 'Alpine Hiking' },
    { id: 'Local Food & Chai', label: 'Local Food & Chai' },
    { id: 'Ayurveda & Sound Healing', label: 'Ayurveda & Sound Healing' }
  ];

  const toggleInterest = (id: string) => {
    setSelectedInterests(prev => 
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  const handleCraftYatra = () => {
    navigate(`/plan?origin=${encodeURIComponent(startingPoint)}&dest=${encodeURIComponent(destination)}&days=${duration}&pace=${encodeURIComponent(pace)}`);
  };

  return (
    <div className="w-full bg-[#FFF8F6] text-[#201A18] antialiased">
      {/* ───────────────────────────────────────────────────────────── */}
      {/* 1. HERO SECTION & HIMALAYAN INTELLIGENCE                      */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="relative w-full max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-8 pb-10">
        <motion.div 
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="flex flex-col items-center text-center space-y-4 max-w-4xl mx-auto"
        >
          {/* Verified Badge */}
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/80 backdrop-blur-md border border-white/60 shadow-xs">
            <span className="inline-block w-2 h-2 rounded-full bg-[#D97706] animate-pulse" />
            <span className="text-[11px] text-[#9D3E19] tracking-widest uppercase font-bold">
              Namaste &amp; Tashi Delek • Verified Himalayan Expedition Intelligence
            </span>
          </div>

          {/* Main Editorial Headline */}
          <h1 className="font-serif-yatra text-4xl sm:text-6xl text-[#201A18] tracking-tight leading-tight">
            Journey Through the <span className="italic text-[#9D3E19]">Heart</span> of the Himalayas
          </h1>

          {/* Subtitle */}
          <p className="text-base sm:text-lg text-[#56423B] max-w-2xl leading-relaxed">
            Thoughtfully curated Himalayan journeys, sacred temples, and timeless trails. Grounded in surveyed Himalayan topography, licensed mountain guide routes, and crafted with warmth for every traveler.
          </p>

          {/* 3D Himalayan Journey Diorama */}
          <div className="w-full flex items-center justify-between px-2 pt-2 text-xs text-[#8A726A]">
            <div className="flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-[#EA580C] animate-pulse" />
              <span className="font-semibold text-[#201A18]">Himalayan Sanctuary Diorama</span>
              <span className="hidden sm:inline text-[#8A726A]">• Majestic Mountain Range • High Stupas &amp; Prayer Flags • Alpine Temples</span>
            </div>
            <div className="text-[11px] text-[#8A726A] hidden md:flex items-center gap-1.5">
              <span>Drag to orbit • Scroll to zoom</span>
            </div>
          </div>

          <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.8, delay: 0.15 }}
            className="w-full relative h-[400px] sm:h-[480px] lg:h-[520px] rounded-3xl overflow-hidden border border-white/70 bg-gradient-to-b from-[#FAF4EE] via-[#F5ECE2] to-[#EFE2D4] backdrop-blur-xl shadow-[0_16px_50px_rgba(42,36,33,0.09)] my-3 group"
          >
            <HimalayanPeaksCanvas className="w-full h-full" interactive={true} />
          </motion.div>

          {/* Himalayan Intelligence Ribbon */}
          <div className="w-full mt-2 p-4 sm:p-5 rounded-2xl bg-white/80 backdrop-blur-md border border-white/60 shadow-[0_4px_24px_rgba(42,36,33,0.04)] flex flex-wrap items-center justify-around gap-4 text-left">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] flex items-center justify-center text-[#9D3E19] shrink-0 shadow-2xs">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-[#201A18]">Verified Alpine Mapping</div>
                <div className="text-[11px] text-[#56423B]">
                  {telemetry?.total_verified_places 
                    ? `${telemetry.total_verified_places.toLocaleString()} Curated Places` 
                    : '6,700+ Curated Places'}
                </div>
              </div>
            </div>

            <div className="h-8 w-px bg-[#E8DDD3] hidden md:block" />

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] flex items-center justify-center text-[#D97706] shrink-0 shadow-2xs">
                <Mountain className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-[#201A18]">Personalized Itineraries</div>
                <div className="text-[11px] text-[#56423B]">Optimal Elevation &amp; Pace</div>
              </div>
            </div>

            <div className="h-8 w-px bg-[#E8DDD3] hidden md:block" />

            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] flex items-center justify-center text-[#1D705C] shrink-0 shadow-2xs">
                <Sparkles className="w-5 h-5" />
              </div>
              <div>
                <div className="text-xs font-bold text-[#201A18]">Himalayan Travel Co-Pilot</div>
                <div className="text-[11px] text-[#56423B]">Interactive Route Assistance</div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 2. EXPEDITION QUICK BUILDER (INTERACTIVE)                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="relative w-full max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pb-14">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
          className="bg-white/85 backdrop-blur-xl rounded-3xl shadow-[0_16px_45px_rgba(42,36,33,0.06)] border border-white/60 p-6 sm:p-8 lg:p-10"
        >
          <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-3 mb-8">
            <div>
              <span className="text-[11px] text-[#9D3E19] uppercase tracking-widest font-bold">
                Himalayan Expedition Studio
              </span>
              <h2 className="font-serif-yatra text-2xl sm:text-3xl font-bold text-[#201A18] mt-1">
                Expedition Quick Builder
              </h2>
              <p className="text-xs sm:text-sm text-[#56423B]">
                Calibrate your preferred route, sanctuary category, and physical pace.
              </p>
            </div>
            <div className="inline-flex items-center gap-2 px-3.5 py-1.5 bg-[#FDF1EC] border border-[#E8DDD3] rounded-full text-[#9D3E19] text-xs font-bold shadow-2xs">
              <ShieldCheck className="w-4 h-4 text-[#9D3E19]" />
              <span>Surveyed Himalayan Trails</span>
            </div>
          </div>

          {/* Controls Form Grid */}
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
            {/* Starting Point */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-[#201A18] flex items-center gap-1.5">
                <Compass className="w-4 h-4 text-[#8A726A]" />
                Departure Hub
              </label>
              <select
                value={startingPoint}
                onChange={(e) => setStartingPoint(e.target.value)}
                className="w-full bg-[#FDF1EC] text-[#201A18] text-xs font-semibold rounded-xl px-4 py-3 border border-[#E8DDD3] focus:outline-none focus:ring-2 focus:ring-[#9D3E19]/30 cursor-pointer"
              >
                {DEPARTURE_HUB_GROUPS.map((group) => (
                  <optgroup key={group.groupName} label={group.groupName}>
                    {group.options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.icon} {opt.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            {/* Destination */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-[#201A18] flex items-center gap-1.5">
                <Mountain className="w-4 h-4 text-[#8A726A]" />
                Destination Corridor
              </label>
              <select
                value={destination}
                onChange={(e) => setDestination(e.target.value)}
                className="w-full bg-[#FDF1EC] text-[#201A18] text-xs font-semibold rounded-xl px-4 py-3 border border-[#E8DDD3] focus:outline-none focus:ring-2 focus:ring-[#9D3E19]/30 cursor-pointer"
              >
                {DESTINATION_CORRIDOR_GROUPS.map((group) => (
                  <optgroup key={group.groupName} label={group.groupName}>
                    {group.options.map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.icon} {opt.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
              </select>
            </div>

            {/* Duration Slider */}
            <div className="flex flex-col gap-2">
              <div className="flex justify-between items-center">
                <label className="text-xs font-bold text-[#201A18] flex items-center gap-1.5">
                  <Calendar className="w-4 h-4 text-[#8A726A]" />
                  Expedition Span
                </label>
                <span className="text-xs text-[#9D3E19] font-bold px-2 py-0.5 bg-[#FDF1EC] rounded-md">
                  {duration} Days
                </span>
              </div>
              <div className="pt-2">
                <input
                  type="range"
                  min={1}
                  max={14}
                  value={duration}
                  onChange={(e) => setDuration(parseInt(e.target.value))}
                  className="w-full h-2 bg-[#F8EBE6] rounded-lg appearance-none cursor-pointer accent-[#9D3E19]"
                />
                <div className="flex justify-between text-[11px] text-[#8A726A] mt-1">
                  <span>1 Day</span>
                  <span>7 Days</span>
                  <span>14 Days</span>
                </div>
              </div>
            </div>

            {/* Pace Selector */}
            <div className="flex flex-col gap-2">
              <label className="text-xs font-bold text-[#201A18]">
                Exploration Pace
              </label>
              <select
                value={pace}
                onChange={(e) => setPace(e.target.value)}
                className="w-full bg-[#FDF1EC] text-[#201A18] text-xs font-semibold rounded-xl px-4 py-3 border border-[#E8DDD3] focus:outline-none focus:ring-2 focus:ring-[#9D3E19]/30 cursor-pointer"
              >
                <option>Balanced (~3 stops/day)</option>
                <option>Relaxed (1-2 stops/day)</option>
                <option>High Adventure (Full dawn-twilight)</option>
              </select>
            </div>
          </div>

          {/* Passions & Focal Points Chips */}
          <div className="mt-6 pt-5 bg-[#FDF1EC]/60 rounded-xl p-4 sm:p-5 border border-[#E8DDD3]">
            <label className="text-xs font-bold text-[#201A18] block mb-3">
              Expedition Passions &amp; Focal Points
            </label>
            <div className="flex flex-wrap gap-2">
              {interestOptions.map((opt) => {
                const isActive = selectedInterests.includes(opt.id);
                return (
                  <button
                    key={opt.id}
                    type="button"
                    onClick={() => toggleInterest(opt.id)}
                    className={`px-3.5 py-2 rounded-full text-xs font-bold transition-all flex items-center gap-1.5 cursor-pointer ${
                      isActive
                        ? 'bg-[#9D3E19] text-white shadow-xs'
                        : 'bg-white text-[#56423B] border border-[#E8DDD3] hover:bg-[#F8EBE6]'
                    }`}
                  >
                    <span>{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Action Area */}
          <div className="mt-6 flex flex-col sm:flex-row items-center justify-between gap-4 pt-2">
            <div className="flex items-center gap-2 text-[#56423B] text-xs">
              <Sparkles className="w-4 h-4 text-[#D97706] shrink-0" />
              <span>Instantly maps trail stages, elevation profiles, permit regulations, and trusted sherpa teahouses.</span>
            </div>
            <button
              onClick={handleCraftYatra}
              className="w-full sm:w-auto inline-flex items-center justify-center gap-2 bg-[#9D3E19] hover:bg-[#BD552F] text-white px-8 py-3.5 rounded-xl font-bold text-sm shadow-md transition-all duration-200 hover:scale-[1.01] active:scale-[0.99] cursor-pointer"
            >
              <Sparkles className="w-4 h-4" />
              <span>Craft Your Himalayan Yatra ✨</span>
            </button>
          </div>
        </motion.div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 3. POPULAR JOURNEYS ACROSS NEPAL (EDITORIAL CARDS)            */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="relative w-full max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pb-16">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.5 }}
        >
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
            <div>
              <span className="text-[11px] text-[#9D3E19] uppercase tracking-widest font-bold">
                Handcrafted Experiences • Authentic Journeys
              </span>
              <h2 className="font-serif-yatra text-2xl sm:text-4xl font-bold text-[#201A18] mt-1">
                Popular Journeys Across Nepal
              </h2>
              <p className="text-xs sm:text-sm text-[#56423B] mt-1">
                Pre-verified routes calibrated with accurate waypoint GPS and daily elevation gain limits.
              </p>
            </div>
            <button
              onClick={() => navigate('/explore')}
              className="inline-flex items-center gap-1.5 text-[#9D3E19] hover:text-[#BD552F] text-xs font-bold transition-colors group cursor-pointer"
            >
              <span>View All Expeditions</span>
              <ArrowRight className="w-4 h-4 group-hover:translate-x-1 transition-transform" />
            </button>
          </div>

          {/* 3 Editorial Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {/* Card 1 */}
            <div className="group bg-white/85 backdrop-blur-xl rounded-2xl overflow-hidden shadow-[0_8px_30px_rgba(42,36,33,0.04)] hover:shadow-xl transition-all duration-300 flex flex-col border border-white/70 hover:border-[#9D3E19]/30">
            <div className="relative h-60 w-full overflow-hidden bg-[#F8EBE6]">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuDAoGxqWL_G9pCW7p-GFHIjFMBNTG0l7WpEBSHMFYLkQ_zGT9EpAHingbjlwXuwkiz13HNVefAAfXAiysXuCzgMqM3xLdOlYz09W1598R3d6TyFpLRcgKWzoguG7Flkls9fzO0YeVcpIvLKnD1dlB2VWLtM8wDvBRQJgVkUsSMio5MCi8_ogPirIj81dEq2sRl4nYcIccE05WEuRYhbXSkX3KHX7lfOvTunxH5X-KtqvajDgAh9JVvISQ"
                alt="Phewa Lake in Pokhara"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3 flex gap-2">
                <span className="px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[#201A18] text-[11px] font-bold shadow-xs">
                  3 Days
                </span>
                <span className="px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[#D97706] text-[11px] font-bold shadow-xs">
                  Balanced
                </span>
              </div>
              <div className="absolute bottom-3 right-3 px-2 py-0.5 rounded-lg bg-white/90 backdrop-blur-sm text-[#56423B] text-[11px] font-semibold">
                Max: 1,592m
              </div>
            </div>
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#9D3E19]" />
                  <span className="text-[11px] text-[#8A726A] uppercase tracking-wider font-bold">
                    Corridor: Central Valleys
                  </span>
                </div>
                <h3 className="font-serif-yatra text-lg font-bold text-[#201A18] group-hover:text-[#9D3E19] transition-colors">
                  Classic Yatra: Kathmandu to Pokhara Highlights
                </h3>
                <p className="text-xs text-[#56423B] mt-2 leading-relaxed">
                  Ancient heritage stupas in Patan, scenic Prithvi highway traverse alongside Trishuli River, followed by tranquil Phewa Lake boat blessings.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#E8DDD3] flex items-center justify-between">
                <div className="flex gap-2">
                  <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[11px] font-semibold text-[#56423B]">Boutique</span>
                  <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[11px] font-semibold text-[#56423B]">Lakeside</span>
                </div>
                <button
                  onClick={() => navigate('/plan?origin=Kathmandu&dest=Pokhara&days=3')}
                  className="inline-flex items-center gap-1 text-xs text-[#9D3E19] font-bold hover:underline cursor-pointer"
                >
                  <span>View Plan</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Card 2 */}
          <div className="group bg-white/85 backdrop-blur-xl rounded-2xl overflow-hidden shadow-[0_8px_30px_rgba(42,36,33,0.04)] hover:shadow-xl transition-all duration-300 flex flex-col border border-white/70 hover:border-[#9D3E19]/30">
            <div className="relative h-60 w-full overflow-hidden bg-[#F8EBE6]">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuCZ3j1Tkys7oJtjFyFvuCvojJOoMe8LaRIrTCwxON76tUp9JZ9nhIYJGD5CzoKXY9-48RfWXH3dTEZU0bDkzksz1LeOt2R2sq_0qsBnGDA1uoV4co0ukIheqJzHDLv_lGwoIYMpjdVUDXRrQ-DN_e9MgQtrfuXmVyNYi1cjJhlXhN1wvcfQm2pMWHlpS5ur1gY1BiQyv7UrwYqTUVbwsS9gmOgKbze_H5sdniNJqTTtI-LSfjPDg-lxEw"
                alt="Chitwan National Park"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3 flex gap-2">
                <span className="px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[#201A18] text-[11px] font-bold shadow-xs">
                  3 Days
                </span>
                <span className="px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[#D97706] text-[11px] font-bold shadow-xs">
                  Relaxed
                </span>
              </div>
              <div className="absolute bottom-3 right-3 px-2 py-0.5 rounded-lg bg-white/90 backdrop-blur-sm text-[#56423B] text-[11px] font-semibold">
                Subtropical Terai
              </div>
            </div>
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#D97706]" />
                  <span className="text-[11px] text-[#8A726A] uppercase tracking-wider font-bold">
                    Corridor: Southern Wilderness
                  </span>
                </div>
                <h3 className="font-serif-yatra text-lg font-bold text-[#201A18] group-hover:text-[#9D3E19] transition-colors">
                  Wildlife &amp; Nature: Pokhara to Chitwan Safari
                </h3>
                <p className="text-xs text-[#56423B] mt-2 leading-relaxed">
                  From alpine vistas to the rich subtropical biodiversity of Sauraha. Encounter greater one-horned rhinos, gharial crocodiles, and Tharu indigenous culture.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#E8DDD3] flex items-center justify-between">
                <div className="flex gap-2">
                  <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[11px] font-semibold text-[#56423B]">Eco Safari</span>
                  <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[11px] font-semibold text-[#56423B]">Canoe</span>
                </div>
                <button
                  onClick={() => navigate('/plan?origin=Pokhara&dest=Chitwan&days=3')}
                  className="inline-flex items-center gap-1 text-xs text-[#9D3E19] font-bold hover:underline cursor-pointer"
                >
                  <span>View Plan</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>

          {/* Card 3 */}
          <div className="group bg-white/85 backdrop-blur-xl rounded-2xl overflow-hidden shadow-[0_8px_30px_rgba(42,36,33,0.04)] hover:shadow-xl transition-all duration-300 flex flex-col border border-white/70 hover:border-[#9D3E19]/30">
            <div className="relative h-60 w-full overflow-hidden bg-[#F8EBE6]">
              <img
                src="https://lh3.googleusercontent.com/aida-public/AB6AXuArp9yq2FNeMp2qwSPa301VTyRz9HQjOBqxO05zIWrCozT3UAfV8FebUsz8eA5sh62zvZd1ph4NzhUts_9S-ZdR-gwK8MweC_AK_uiiB2uv3HkQvT-bL0pZQwCLGxz03f0IwdlHAe5F6BAcDQvbVbTGvg55GrU1GcsVEF_QorlamjYVAk7xdFnD001xKsOo0KuvoIn_W5kjuiiWgp5bwgU6R_Z0dAz_jG7UbWZwOqtokXchtAwaAEvh0Q"
                alt="Nagarkot Sunrise"
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
              <div className="absolute top-3 left-3 flex gap-2">
                <span className="px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[#201A18] text-[11px] font-bold shadow-xs">
                  2 Days
                </span>
                <span className="px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[#D97706] text-[11px] font-bold shadow-xs">
                  Relaxed
                </span>
              </div>
              <div className="absolute bottom-3 right-3 px-2 py-0.5 rounded-lg bg-white/90 backdrop-blur-sm text-[#56423B] text-[11px] font-semibold">
                Max: 2,175m
              </div>
            </div>
            <div className="p-5 flex-1 flex flex-col justify-between">
              <div>
                <div className="flex items-center gap-2 mb-2">
                  <span className="inline-block w-1.5 h-1.5 rounded-full bg-[#1D705C]" />
                  <span className="text-[11px] text-[#8A726A] uppercase tracking-wider font-bold">
                    Corridor: Valley Rim
                  </span>
                </div>
                <h3 className="font-serif-yatra text-lg font-bold text-[#201A18] group-hover:text-[#9D3E19] transition-colors">
                  Culture &amp; Sunrise: Kathmandu Valley &amp; Nagarkot
                </h3>
                <p className="text-xs text-[#56423B] mt-2 leading-relaxed">
                  Bhaktapur Durbar Square pottery workshops, sacred Changu Narayan hilltop shrines, and dawn panoramic views of 8 Himalayan mountain ranges.
                </p>
              </div>
              <div className="mt-5 pt-3 border-t border-[#E8DDD3] flex items-center justify-between">
                <div className="flex gap-2">
                  <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[11px] font-semibold text-[#56423B]">Heritage</span>
                  <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[11px] font-semibold text-[#56423B]">Panoramas</span>
                </div>
                <button
                  onClick={() => navigate('/plan?origin=Kathmandu&dest=Nagarkot&days=2')}
                  className="inline-flex items-center gap-1 text-xs text-[#9D3E19] font-bold hover:underline cursor-pointer"
                >
                  <span>View Plan</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          </div>
        </div>
        </motion.div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* 4. EXPEDITION VALUE PILLARS                                   */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="relative w-full max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pb-16">
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true }}
          transition={{ duration: 0.6 }}
          className="grid grid-cols-1 md:grid-cols-3 gap-6"
        >
          <div className="p-6 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] hover:shadow-md transition-shadow">
            <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#9D3E19] flex items-center justify-center font-bold text-base mb-4 shadow-2xs">
              01
            </div>
            <h3 className="font-serif-yatra text-base font-bold text-[#201A18] mb-2">
              Surveyed Mountain Trail Intelligence
            </h3>
            <p className="text-xs text-[#56423B] leading-relaxed">
              Every teahouse, suspension bridge, and mountain pass is verified against ground truth GPS waypoints recorded by licensed local mountain guides and Survey Department Nepal.
            </p>
          </div>

          <div className="p-6 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] hover:shadow-md transition-shadow">
            <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#D97706] flex items-center justify-center font-bold text-base mb-4 shadow-2xs">
              02
            </div>
            <h3 className="font-serif-yatra text-base font-bold text-[#201A18] mb-2">
              Cultural &amp; Sacred Etiquette
            </h3>
            <p className="text-xs text-[#56423B] leading-relaxed">
              Automated contextual reminders for clockwise circumambulation around sacred mani stones, prayer wheel respect, and holy monastery photography protocol.
            </p>
          </div>

          <div className="p-6 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] hover:shadow-md transition-shadow">
            <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#1D705C] flex items-center justify-center font-bold text-base mb-4 shadow-2xs">
              03
            </div>
            <h3 className="font-serif-yatra text-base font-bold text-[#201A18] mb-2">
              Fair Porter &amp; Lodge Stewardship
            </h3>
            <p className="text-xs text-[#56423B] leading-relaxed">
              Supporting the Himalayan Porter Protection Protocol. Direct lodging verification ensures fair rates go straight to local families and community teahouse cooperatives.
            </p>
          </div>
        </motion.div>
      </section>
    </div>
  );
};
