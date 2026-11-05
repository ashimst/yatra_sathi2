import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, MapPin, Share2, Trash2, ArrowRight, Compass, Check, Image as ImageIcon } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../api/config';

interface SavedTripsDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenMemoriesModal?: () => void;
}

interface SavedItineraryItem {
  id: string;
  share_id: string;
  title: string;
  description?: string;
  origin_name?: string;
  dest_name?: string;
  num_days: number;
  pace: string;
  budget: string;
  created_at?: string;
  share_url: string;
}

export const SavedTripsDrawer: React.FC<SavedTripsDrawerProps> = ({ isOpen, onClose, onOpenMemoriesModal }) => {
  const { user, token, refreshProfile } = useAuth();
  const navigate = useNavigate();

  const [trips, setTrips] = useState<SavedItineraryItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [copiedShareId, setCopiedShareId] = useState<string | null>(null);

  const fetchSavedTrips = async () => {
    if (!token) return;
    setIsLoading(true);
    try {
      const res = await fetch(apiUrl('/itineraries'), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setTrips(data.itineraries || []);
      }
    } catch (e) {
      console.error('Error fetching trips:', e);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchSavedTrips();
      refreshProfile();
    }
  }, [isOpen]);

  const handleDeleteTrip = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    if (!token) return;
    try {
      const res = await fetch(apiUrl(`/itineraries/${id}`), {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setTrips((prev) => prev.filter((t) => t.id !== id));
        refreshProfile();
      }
    } catch (err) {
      console.error('Delete error:', err);
    }
  };

  const handleShareClick = (shareId: string, e: React.MouseEvent) => {
    e.stopPropagation();
    const fullUrl = `${window.location.origin}/share/${shareId}`;
    navigator.clipboard.writeText(fullUrl);
    setCopiedShareId(shareId);
    setTimeout(() => setCopiedShareId(null), 2500);
  };

  const handleOpenTrip = (trip: SavedItineraryItem) => {
    onClose();
    navigate(`/share/${trip.share_id}`);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/45 backdrop-blur-md z-50"
          />

          {/* Drawer Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 200 }}
            className="fixed top-0 right-0 h-full w-full max-w-md bg-white/95 backdrop-blur-xl z-50 shadow-2xl flex flex-col border-l border-white/60"
          >
            {/* Header */}
            <div className="p-5 border-b border-[#E0DAD0] flex items-center justify-between bg-[#FAF7F2]/90 backdrop-blur-md">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-2xl bg-[#CC5200] text-white flex items-center justify-center font-bold text-sm shadow-xs font-serif-yatra">
                  {user?.full_name?.slice(0, 2).toUpperCase() || 'EX'}
                </div>
                <div>
                  <h3 className="font-serif-yatra font-bold text-[#1A1A1A] text-lg leading-tight">
                    {user?.full_name || 'Traveler'}
                  </h3>
                  <div className="flex items-center gap-2 text-[11px] text-[#6B6B6B] mt-0.5">
                    <span>{trips.length} Yatras Saved</span>
                    <span>•</span>
                    <span>{user?.memory_count || 0} Memories</span>
                  </div>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-xl text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#EAE4D9] transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Content List */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3.5 bg-[#FDFBF7]">
              {isLoading ? (
                <div className="text-center py-20 text-[#6B6B6B] space-y-2">
                  <div className="w-7 h-7 rounded-full border-2 border-[#CC5200] border-t-transparent animate-spin mx-auto" />
                  <p className="text-xs">Loading saved Yatras...</p>
                </div>
              ) : trips.length === 0 ? (
                <div className="text-center py-20 px-6 bg-white rounded-3xl border border-[#E0DAD0] p-8 space-y-3">
                  <Compass className="w-10 h-10 text-[#CC5200] mx-auto opacity-70" />
                  <h4 className="font-serif-yatra font-bold text-lg text-[#1A1A1A]">No Saved Yatras Yet</h4>
                  <p className="text-xs text-[#6B6B6B] leading-relaxed">
                    When you craft an itinerary, click "Save to My Yatras" to access your trips here anytime.
                  </p>
                </div>
              ) : (
                trips.map((trip) => (
                  <div
                    key={trip.id}
                    onClick={() => handleOpenTrip(trip)}
                    className="p-4 rounded-2xl bg-white border border-[#E0DAD0] hover:border-[#CC5200]/50 transition-all shadow-2xs cursor-pointer group space-y-2.5"
                  >
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-full bg-[#1D705C]/10 text-[#1D705C]">
                        {trip.num_days} Days • {trip.pace}
                      </span>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={(e) => handleShareClick(trip.share_id, e)}
                          title="Copy Public Share Link"
                          className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#CC5200] hover:bg-[#FAF7F2] transition-colors"
                        >
                          {copiedShareId === trip.share_id ? (
                            <Check className="w-3.5 h-3.5 text-emerald-600" />
                          ) : (
                            <Share2 className="w-3.5 h-3.5" />
                          )}
                        </button>
                        <button
                          onClick={(e) => handleDeleteTrip(trip.id, e)}
                          title="Delete Yatra"
                          className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-red-600 hover:bg-red-50 transition-colors"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div>
                      <h4 className="font-serif-yatra font-bold text-base text-[#1A1A1A] group-hover:text-[#CC5200] transition-colors">
                        {trip.title}
                      </h4>
                      <p className="text-xs text-[#6B6B6B] line-clamp-2 mt-0.5 leading-relaxed">
                        {trip.description || 'Curated journey through Nepal.'}
                      </p>
                    </div>

                    <div className="pt-2 border-t border-[#E0DAD0] flex items-center justify-between text-xs text-[#6B6B6B]">
                      <span className="flex items-center gap-1 font-medium">
                        <MapPin className="w-3.5 h-3.5 text-[#CC5200]" />
                        {trip.origin_name} &rarr; {trip.dest_name}
                      </span>
                      <span className="text-[#CC5200] font-bold text-xs flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                        <span>Open</span>
                        <ArrowRight className="w-3 h-3" />
                      </span>
                    </div>
                  </div>
                ))
              )}
            </div>

            {/* Footer with Photo Memories shortcut */}
            <div className="p-4 border-t border-[#E0DAD0] bg-[#FAF7F2]">
              <button
                onClick={() => {
                  onClose();
                  if (onOpenMemoriesModal) onOpenMemoriesModal();
                  else navigate('/yatra-smriti');
                }}
                className="w-full py-2.5 rounded-xl bg-white hover:bg-[#EAE4D9] border border-[#E0DAD0] text-[#1A1A1A] text-xs font-bold transition-all flex items-center justify-center gap-2 cursor-pointer shadow-2xs"
              >
                <ImageIcon className="w-4 h-4 text-[#CC5200]" />
                <span>View Field Photo Scrapbook ({user?.memory_count || 0})</span>
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
