import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Search, 
  MapPin, 
  Compass, 
  Camera, 
  Sparkles, 
  X, 
  Calendar, 
  ExternalLink, 
  ShieldCheck
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import type { Place } from '../types';
import { getCategoryColor } from '../components/MapView';
import { PhotoUploadModal } from '../components/PhotoUploadModal';
import { apiUrl } from '../api/config';

const getCategoryIcon = (category?: string) => {
  const cat = (category || '').toLowerCase();
  if (cat.includes('trail') || cat.includes('pass') || cat.includes('circuit')) return '🥾';
  if (cat.includes('temple') || cat.includes('religious') || cat.includes('stupa') || cat.includes('monastery') || cat.includes('shrine')) return '🛕';
  if (cat.includes('viewpoint') || cat.includes('peak') || cat.includes('mountain') || cat.includes('ridge')) return '🏔️';
  if (cat.includes('restaurant') || cat.includes('food') || cat.includes('thakali') || cat.includes('kitchen')) return '🍲';
  if (cat.includes('cafe') || cat.includes('coffee') || cat.includes('bakery')) return '☕';
  if (cat.includes('hotel') || cat.includes('lodge') || cat.includes('resort') || cat.includes('guest') || cat.includes('hostel') || cat.includes('teahouse')) return '🏡';
  if (cat.includes('lake') || cat.includes('waterfall') || cat.includes('river') || cat.includes('park')) return '🌊';
  return '🏛️';
};

const getCategorySubtitle = (category?: string) => {
  const cat = (category || '').toLowerCase();
  if (cat.includes('trail') || cat.includes('pass')) return 'Surveyed Alpine Trekking Trail';
  if (cat.includes('temple') || cat.includes('religious') || cat.includes('stupa') || cat.includes('monastery')) return 'Sacred Pilgrimage Sanctuary';
  if (cat.includes('viewpoint') || cat.includes('peak') || cat.includes('mountain')) return 'Himalayan Ridge Viewpoint';
  if (cat.includes('restaurant') || cat.includes('food') || cat.includes('thakali')) return 'Authentic Regional Cuisine';
  if (cat.includes('cafe') || cat.includes('coffee')) return 'Mountain Brew & Pastries';
  if (cat.includes('hotel') || cat.includes('lodge') || cat.includes('resort') || cat.includes('teahouse')) return 'Himalayan Hospitality & Teahouse';
  if (cat.includes('lake') || cat.includes('waterfall') || cat.includes('river')) return 'Tranquil Himalayan Waters';
  return 'Verified Cultural Destination';
};

const getCategoryWatermark = (category?: string) => {
  const cat = (category || '').toLowerCase();
  if (cat.includes('trail') || cat.includes('pass')) return '🥾';
  if (cat.includes('temple') || cat.includes('religious') || cat.includes('stupa') || cat.includes('monastery')) return '🛕';
  if (cat.includes('viewpoint') || cat.includes('peak')) return '🏔️';
  if (cat.includes('restaurant') || cat.includes('food')) return '🍲';
  if (cat.includes('cafe') || cat.includes('coffee')) return '☕';
  if (cat.includes('hotel') || cat.includes('lodge') || cat.includes('teahouse')) return '🏡';
  if (cat.includes('lake') || cat.includes('waterfall')) return '🌊';
  return '🏛️';
};

export const ExplorePage: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All');
  const [places, setPlaces] = useState<Place[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedPlace, setSelectedPlace] = useState<Place | null>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [isPhotoModalOpen, setIsPhotoModalOpen] = useState(false);
  const [photoTarget, setPhotoTarget] = useState<{ name: string; lat?: number; lng?: number }>({ name: '' });

  const categories = [
    'All',
    '💎 Hidden Gems',
    'Trekking Trails & Passes',
    'Sacred Monasteries',
    'Himalayan Viewpoints',
    'Attraction',
    'Teahouses & Lodges',
    'Local Restaurants',
  ];

  const fetchPlaces = async (searchTerm: string = query, cat: string = selectedCategory) => {
    setIsLoading(true);
    try {
      let endpoint = '';
      if (cat === '💎 Hidden Gems') {
        endpoint = `/places?category=hidden_gems&limit=36`;
      } else if (cat === 'Trekking Trails & Passes') {
        endpoint = `/places/search?q=pass&limit=36`;
      } else if (cat === 'Sacred Monasteries') {
        endpoint = `/places/search?q=monastery&limit=36`;
      } else if (cat === 'Himalayan Viewpoints') {
        endpoint = `/places?category=Viewpoint&limit=36`;
      } else if (cat === 'Teahouses & Lodges') {
        endpoint = `/places?category=Accommodation&limit=36`;
      } else if (cat === 'Local Restaurants') {
        endpoint = `/places?category=Restaurant&limit=36`;
      } else if (searchTerm.trim()) {
        endpoint = `/places/search?q=${encodeURIComponent(searchTerm)}&limit=36`;
      } else if (cat !== 'All') {
        endpoint = `/places?category=${encodeURIComponent(cat)}&limit=36`;
      } else {
        endpoint = `/places/search?q=Nepal&limit=36`;
      }

      const res = await fetch(apiUrl(endpoint));
      if (res.ok) {
        const data = await res.json();
        setPlaces(data.places || []);
      }
    } catch (e) {
      console.error('Error fetching places:', e);
    } finally {
      setIsLoading(false);
    }
  };

  const fetchMemories = async () => {
    try {
      const res = await fetch(apiUrl('/memories'));
      if (res.ok) {
        const data = await res.json();
        setMemories(data.memories || []);
      }
    } catch (e) {
      console.error('Error fetching memories:', e);
    }
  };

  useEffect(() => {
    fetchPlaces('Pokhara', 'All');
    fetchMemories();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchPlaces(query, selectedCategory);
  };

  const handleCategorySelect = (cat: string) => {
    setSelectedCategory(cat);
    fetchPlaces(query, cat);
  };

  const handleOpenPhotoModal = (placeName: string, lat?: number, lng?: number) => {
    setPhotoTarget({ name: placeName, lat, lng });
    setIsPhotoModalOpen(true);
  };

  const filteredPlaces = places.filter((p) => {
    if (selectedCategory === 'All') return true;
    if (selectedCategory === '💎 Hidden Gems') return p.is_hidden_gem === true;
    if (selectedCategory === 'Trekking Trails & Passes') {
      const c = (p.category || '').toLowerCase() + (p.name || '').toLowerCase();
      return c.includes('trail') || c.includes('pass') || c.includes('la');
    }
    if (selectedCategory === 'Sacred Monasteries') {
      const c = (p.category || '').toLowerCase() + (p.name || '').toLowerCase();
      return c.includes('monastery') || c.includes('gompa') || c.includes('stupa') || c.includes('temple');
    }
    return p.category?.toLowerCase().includes(selectedCategory.toLowerCase());
  });

  return (
    <div className="min-h-screen bg-[#FFF8F6] text-[#201A18] py-10 antialiased">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* Header */}
        <motion.div 
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="text-center max-w-2xl mx-auto mb-10 space-y-3"
        >
          <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#9D3E19] text-xs font-bold uppercase tracking-wider shadow-2xs">
            <ShieldCheck className="w-4 h-4 text-[#9D3E19]" />
            <span>6,700+ Verified Himalayan Destinations &amp; Trails</span>
          </div>
          <h1 className="text-3xl sm:text-5xl font-serif-yatra font-bold text-[#201A18] tracking-tight">
            Discover Nepal's <span className="italic text-[#9D3E19]">Sacred &amp; Scenic</span> Places
          </h1>
          <p className="text-xs sm:text-sm text-[#56423B] leading-relaxed">
            From the historic shrines of Kathmandu Valley to high-altitude Himalayan passes, authentic sherpa teahouses, and serene mountain lakes.
          </p>
        </motion.div>

        {/* Search Bar */}
        <motion.div 
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5, delay: 0.1 }}
          className="max-w-2xl mx-auto mb-8"
        >
          <form onSubmit={handleSearchSubmit} className="relative flex items-center">
            <Search className="w-5 h-5 text-[#8A726A] absolute left-4 pointer-events-none" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search temple, lake, stupa, pass, viewpoint, or trail..."
              className="w-full pl-12 pr-28 py-3.5 rounded-2xl bg-white/90 backdrop-blur-md border border-[#E8DDD3] shadow-[0_4px_20px_rgba(42,36,33,0.05)] text-[#201A18] text-sm focus:outline-hidden focus:ring-2 focus:ring-[#9D3E19]/30 focus:border-[#9D3E19] transition-all"
            />
            <button
              type="submit"
              className="absolute right-2 px-5 py-2 rounded-xl bg-[#9D3E19] hover:bg-[#BD552F] text-white text-xs font-bold shadow-xs transition-colors cursor-pointer"
            >
              Search
            </button>
          </form>
        </motion.div>

        {/* Community Memories Spotlight */}
        {memories.length > 0 && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.98 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ duration: 0.5, delay: 0.15 }}
            className="max-w-5xl mx-auto mb-10 p-5 rounded-3xl bg-white/85 backdrop-blur-md border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]"
          >
            <div className="flex items-center justify-between mb-3.5">
              <div className="flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-[#D97706]" />
                <h3 className="font-serif-yatra font-bold text-base text-[#201A18]">
                  Yatra Smriti • Traveler Photo Memories
                </h3>
              </div>
              <button
                onClick={() => handleOpenPhotoModal('Nepal')}
                className="text-xs font-bold text-[#9D3E19] hover:underline flex items-center gap-1 cursor-pointer"
              >
                <Camera className="w-3.5 h-3.5" />
                <span>Add Memory</span>
              </button>
            </div>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3.5">
              {memories.slice(0, 4).map((m) => (
                <div
                  key={m.id}
                  className="group relative rounded-xl overflow-hidden aspect-4/3 bg-stone-100 border border-[#E8DDD3] shadow-2xs"
                >
                  <img
                    src={m.image_url}
                    alt={m.place_name}
                    className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300"
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent p-2.5 flex flex-col justify-end text-white">
                    <span className="font-serif-yatra font-bold text-xs truncate">{m.place_name}</span>
                    {m.ai_reflection && (
                      <p className="text-[11px] text-[#FAF7F2]/90 italic line-clamp-1 mt-0.5">
                        "{m.ai_reflection}"
                      </p>
                    )}
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}

        {/* Category Filter Pills */}
        <div className="flex items-center justify-center gap-2 flex-wrap mb-10">
          {categories.map((cat) => (
            <button
              key={cat}
              onClick={() => handleCategorySelect(cat)}
              className={`px-4 py-2 rounded-xl text-xs font-semibold transition-all cursor-pointer ${
                selectedCategory === cat
                  ? 'bg-[#9D3E19] text-white shadow-xs'
                  : 'bg-white border border-[#E8DDD3] text-[#56423B] hover:bg-[#FDF1EC]'
              }`}
            >
              {cat}
            </button>
          ))}
        </div>

        {/* Places Grid */}
        {isLoading ? (
          <div className="text-center py-20 text-[#8A726A] space-y-3">
            <div className="w-8 h-8 rounded-full border-2 border-[#9D3E19] border-t-transparent animate-spin mx-auto" />
            <p className="text-xs">Discovering verified sanctuaries &amp; alpine viewpoints...</p>
          </div>
        ) : filteredPlaces.length === 0 ? (
          <div className="text-center py-20 bg-white rounded-3xl border border-[#E8DDD3] p-8 max-w-md mx-auto shadow-xs">
            <Compass className="w-10 h-10 text-[#8A726A] mx-auto mb-2" />
            <h3 className="font-serif-yatra font-bold text-lg text-[#201A18]">No destinations found</h3>
            <p className="text-xs text-[#56423B] mt-1">Try selecting "💎 Hidden Gems", "Pokhara", or "Trekking Trails &amp; Passes"</p>
          </div>
        ) : (
          <motion.div 
            layout
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6"
          >
            {filteredPlaces.map((place) => {
              const color = getCategoryColor(place.category);
              return (
                <motion.div
                  layout
                  initial={{ opacity: 0, y: 15 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3 }}
                  key={place.id}
                  className="bg-white rounded-2xl border border-[#E8DDD3] shadow-[0_4px_20px_rgba(42,36,33,0.03)] hover:shadow-lg transition-all duration-300 overflow-hidden flex flex-col justify-between group"
                >
                  <div 
                    onClick={() => setSelectedPlace(place)}
                    className="cursor-pointer"
                  >
                    {/* Hero Image Banner */}
                    {place.image_url ? (
                      <div className="relative h-48 w-full overflow-hidden bg-stone-100">
                        <img
                          src={place.image_url}
                          alt={place.name}
                          className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                          loading="lazy"
                          onError={(e) => {
                            const target = e.target as HTMLImageElement;
                            if (!target.dataset.fallback) {
                              target.dataset.fallback = '1';
                              target.src = 'https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800&auto=format&fit=crop&q=80';
                            } else {
                              target.style.display = 'none';
                              target.parentElement?.classList.add('bg-gradient-to-br', 'from-[#2A201A]', 'to-[#4A3222]');
                            }
                          }}
                        />
                        <div className="absolute inset-0 bg-gradient-to-t from-black/70 via-black/15 to-transparent" />

                        {/* Top Badges */}
                        <div className="absolute top-2.5 left-2.5 flex items-center gap-1.5 flex-wrap">
                          <span
                            className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full backdrop-blur-md text-white border border-white/20"
                            style={{ backgroundColor: 'rgba(0,0,0,0.5)' }}
                          >
                            {place.category || 'Attraction'}
                          </span>
                          {place.is_hidden_gem && (
                            <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-600/90 text-white backdrop-blur-md shadow-xs">
                              💎 Hidden Gem
                            </span>
                          )}
                        </div>

                        {place.rating && (
                          <div className="absolute top-2.5 right-2.5 text-xs font-bold text-white bg-black/55 backdrop-blur-md px-2.5 py-1 rounded-full border border-white/20 flex items-center gap-1">
                            ★ {place.rating}
                          </div>
                        )}

                        {place.price_level && (
                          <div className="absolute bottom-2.5 right-2.5 text-[11px] font-bold text-white bg-black/60 backdrop-blur-md px-2 py-0.5 rounded-md border border-white/20">
                            {place.price_level}
                          </div>
                        )}
                      </div>
                    ) : (
                      <div className="relative h-44 w-full p-4 flex flex-col justify-between overflow-hidden bg-gradient-to-br from-[#FAF6F0] via-[#F4ECE3] to-[#EAE0D4] border-b border-[#E8DDD3]">
                        {/* Cultural motif watermark */}
                        <div className="absolute -right-1 -bottom-2 text-6xl opacity-15 select-none pointer-events-none">
                          {getCategoryWatermark(place.category)}
                        </div>
                        
                        {/* Top Badges */}
                        <div className="flex items-center justify-between z-10">
                          <div className="flex items-center gap-1.5 flex-wrap">
                            <span
                              className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full shadow-2xs"
                              style={{ backgroundColor: color + '20', color: color }}
                            >
                              {place.category || 'Attraction'}
                            </span>
                            {place.is_hidden_gem && (
                              <span className="text-[11px] font-bold px-2.5 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                                💎 Hidden Gem
                              </span>
                            )}
                          </div>
                          {place.rating && (
                            <span className="text-xs font-bold text-[#8A726A]">
                              ★ {place.rating}
                            </span>
                          )}
                        </div>

                        <div className="z-10 mt-auto">
                          <span className="text-[11px] text-[#8A726A] font-semibold flex items-center gap-1">
                            <span>{getCategoryIcon(place.category)}</span>
                            <span>{getCategorySubtitle(place.category)}</span>
                          </span>
                        </div>
                      </div>
                    )}

                    {/* Card Content */}
                    <div className="p-5 space-y-2">
                      <div className="flex items-start justify-between gap-2">
                        <h3 className="font-serif-yatra font-bold text-lg text-[#201A18] group-hover:text-[#9D3E19] transition-colors leading-snug">
                          {place.name}
                        </h3>
                      </div>

                      {place.description ? (
                        <p className="text-xs text-[#56423B] line-clamp-2 leading-relaxed">
                          {place.description}
                        </p>
                      ) : (
                        <p className="text-xs text-[#8A726A] italic">
                          Verified Himalayan destination with surveyed topography and route coordinates.
                        </p>
                      )}

                      {/* Insider Tip Badge if available */}
                      {place.must_try && (
                        <div className="mt-2.5 p-2 rounded-lg bg-amber-50/80 border border-amber-200/60 text-[11px] text-amber-950 flex items-start gap-1.5">
                          <span className="text-amber-600 font-bold">✨</span>
                          <span className="line-clamp-1"><strong>Must Experience:</strong> {place.must_try}</span>
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Card Footer */}
                  <div className="px-5 py-3 border-t border-[#E8DDD3] bg-[#FDF1EC]/40 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1 text-[#56423B]">
                      <MapPin className="w-3.5 h-3.5 text-[#1D705C]" />
                      <span className="text-[11px]">
                        {place.latitude != null && place.longitude != null
                          ? `${place.latitude.toFixed(2)}°N, ${place.longitude.toFixed(2)}°E`
                          : (place.district || 'Himalayan Ridge')}
                      </span>
                    </div>

                    <button
                      onClick={() => setSelectedPlace(place)}
                      className="text-xs font-bold text-[#9D3E19] hover:underline cursor-pointer"
                    >
                      View Details &rarr;
                    </button>
                  </div>
                </motion.div>
              );
            })}
          </motion.div>
        )}
      </div>

      {/* Place Details Modal */}
      <AnimatePresence>
        {selectedPlace && (
          <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
            <motion.div 
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
              transition={{ duration: 0.2 }}
              className="bg-white rounded-3xl max-w-xl w-full overflow-hidden shadow-2xl border border-[#E8DDD3] relative max-h-[90vh] flex flex-col"
            >
              {/* Close Button */}
              <button
                onClick={() => setSelectedPlace(null)}
                className="absolute top-4 right-4 z-20 w-8 h-8 rounded-full bg-black/40 hover:bg-black/60 text-white flex items-center justify-center backdrop-blur-md transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>

              {/* Hero Image / Watermark */}
              {selectedPlace.image_url ? (
                <div className="relative h-60 w-full bg-stone-100 shrink-0">
                  <img
                    src={selectedPlace.image_url}
                    alt={selectedPlace.name}
                    className="w-full h-full object-cover"
                    onError={(e) => {
                      const target = e.target as HTMLImageElement;
                      if (!target.dataset.fallback) {
                        target.dataset.fallback = '1';
                        target.src = 'https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800&auto=format&fit=crop&q=80';
                      } else {
                        target.style.display = 'none';
                        target.parentElement?.classList.add('bg-gradient-to-br', 'from-[#2A201A]', 'to-[#4A3222]');
                      }
                    }}
                  />
                  <div className="absolute inset-0 bg-gradient-to-t from-black/85 via-black/25 to-transparent" />
                  <div className="absolute top-4 left-4 flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-black/60 text-white backdrop-blur-md border border-white/20">
                      {selectedPlace.category || 'Attraction'}
                    </span>
                    {selectedPlace.is_hidden_gem && (
                      <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-emerald-600 text-white backdrop-blur-md">
                        💎 Hidden Gem
                      </span>
                    )}
                  </div>
                  {selectedPlace.rating && (
                    <div className="absolute top-4 right-16 text-xs font-bold text-white bg-black/60 backdrop-blur-md px-3 py-1 rounded-full border border-white/20 flex items-center gap-1">
                      ★ {selectedPlace.rating}
                    </div>
                  )}
                  <div className="absolute bottom-4 left-5 right-5 text-white">
                    <h2 className="font-serif-yatra font-bold text-2xl sm:text-3xl text-white drop-shadow-md">
                      {selectedPlace.name}
                    </h2>
                    <div className="flex items-center gap-2 text-xs text-white/90 mt-1">
                      <span>{getCategoryIcon(selectedPlace.category)}</span>
                      <span>{getCategorySubtitle(selectedPlace.category)}</span>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="relative h-44 w-full p-6 bg-gradient-to-br from-[#FAF6F0] via-[#F4ECE3] to-[#EAE0D4] border-b border-[#E8DDD3] flex flex-col justify-between shrink-0">
                  <div className="flex items-center gap-2">
                    <span className="text-[11px] font-bold uppercase tracking-wider px-3 py-1 rounded-full bg-white text-[#9D3E19] border border-[#E8DDD3] shadow-xs">
                      {selectedPlace.category || 'Attraction'}
                    </span>
                    {selectedPlace.is_hidden_gem && (
                      <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200">
                        💎 Hidden Gem
                      </span>
                    )}
                  </div>
                  <div>
                    <h2 className="font-serif-yatra font-bold text-2xl text-[#201A18]">
                      {selectedPlace.name}
                    </h2>
                    <p className="text-xs text-[#56423B] mt-0.5">
                      {getCategorySubtitle(selectedPlace.category)}
                    </p>
                  </div>
                </div>
              )}

              {/* Scrollable Content Body */}
              <div className="p-6 overflow-y-auto space-y-4 text-xs">
                {/* Telemetry info row */}
                <div className="flex items-center justify-between p-3 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] text-[#56423B]">
                  <div className="flex items-center gap-1.5 font-semibold">
                    <MapPin className="w-4 h-4 text-[#1D705C]" />
                    <span>
                      GPS: {selectedPlace.latitude != null && selectedPlace.longitude != null
                        ? `${selectedPlace.latitude.toFixed(4)}° N, ${selectedPlace.longitude.toFixed(4)}° E`
                        : 'Coordinates unavailable'}
                    </span>
                  </div>
                  {selectedPlace.price_level && (
                    <span className="font-bold text-[#9D3E19] bg-white px-2.5 py-0.5 rounded-md border border-[#E8DDD3]">
                      {selectedPlace.price_level}
                    </span>
                  )}
                </div>

                {/* Description */}
                <div>
                  <h4 className="font-serif-yatra text-sm font-bold text-[#201A18] mb-1">
                    Destination Heritage &amp; Context
                  </h4>
                  <p className="text-xs text-[#56423B] leading-relaxed">
                    {selectedPlace.description || "A revered cultural and scenic sanctuary along Nepal's historic routes."}
                  </p>
                </div>

                {/* Insider Tip if available */}
                {selectedPlace.must_try && (
                  <div className="p-3.5 rounded-xl bg-amber-50 border border-amber-200 text-xs text-amber-950 flex items-start gap-2.5">
                    <Sparkles className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                    <div>
                      <span className="font-bold">Insider Tip &amp; Sacred Protocol:</span> {selectedPlace.must_try}
                    </div>
                  </div>
                )}
              </div>

              {/* Bottom Actions Bar */}
              <div className="p-4 sm:p-5 border-t border-[#E8DDD3] bg-[#FDF1EC]/50 flex flex-wrap items-center justify-between gap-3 shrink-0">
                <a
                  href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(selectedPlace.name + ' Nepal')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#56423B] hover:text-[#201A18] transition-colors"
                >
                  <ExternalLink className="w-3.5 h-3.5" />
                  <span>Google Maps</span>
                </a>

                <div className="flex items-center gap-2">
                  <button
                    onClick={() => {
                      const place = selectedPlace;
                      setSelectedPlace(null);
                      handleOpenPhotoModal(place.name, place.latitude, place.longitude);
                    }}
                    className="px-3.5 py-2 rounded-xl bg-white hover:bg-[#FDF1EC] border border-[#E8DDD3] text-xs font-bold text-[#56423B] transition-colors flex items-center gap-1.5 cursor-pointer shadow-2xs"
                  >
                    <Camera className="w-3.5 h-3.5 text-[#9D3E19]" />
                    <span>Log Memory</span>
                  </button>

                  <button
                    onClick={() => {
                      const placeName = selectedPlace.name;
                      setSelectedPlace(null);
                      navigate(`/plan?dest=${encodeURIComponent(placeName)}`);
                    }}
                    className="px-4 py-2 rounded-xl bg-[#9D3E19] hover:bg-[#BD552F] text-white text-xs font-bold transition-colors flex items-center gap-1.5 shadow-xs cursor-pointer"
                  >
                    <Calendar className="w-3.5 h-3.5" />
                    <span>Plan Yatra Here</span>
                  </button>
                </div>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Photo Upload Modal */}
      <PhotoUploadModal
        isOpen={isPhotoModalOpen}
        onClose={() => setIsPhotoModalOpen(false)}
        defaultPlaceName={photoTarget.name}
        defaultLatitude={photoTarget.lat}
        defaultLongitude={photoTarget.lng}
        onMemoryCreated={() => fetchMemories()}
      />
    </div>
  );
};
