import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { MapView } from '../components/MapView';
import { ItineraryCard } from '../components/ItineraryCard';
import { ArrowLeft, Share2, Printer, Check, MapPin, Compass, Camera } from 'lucide-react';
import type { Itinerary, RouteData } from '../types';
import { apiUrl } from '../api/config';

export const SharePage: React.FC = () => {
  const { shareId } = useParams<{ shareId: string }>();
  const navigate = useNavigate();

  const [tripData, setTripData] = useState<any | null>(null);
  const [memories, setMemories] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => {
    const fetchSharedTrip = async () => {
      setIsLoading(true);
      setError(null);
      try {
        const res = await fetch(apiUrl(`/itineraries/share/${shareId}`));
        if (!res.ok) {
          throw new Error('This shared Yatra was not found or has expired.');
        }
        const data = await res.json();
        setTripData(data);

        // Fetch any memories attached to this itinerary
        if (data.id) {
          try {
            const mRes = await fetch(apiUrl(`/memories?itinerary_id=${data.id}`));
            if (mRes.ok) {
              const mData = await mRes.json();
              setMemories(mData.memories || []);
            }
          } catch (mErr) {
            console.error('Memories load error:', mErr);
          }
        }
      } catch (e: any) {
        setError(e.message || 'Error loading shared trip');
      } finally {
        setIsLoading(false);
      }
    };

    if (shareId) {
      fetchSharedTrip();
    }
  }, [shareId]);

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href);
    setCopied(true);
    setTimeout(() => setCopied(false), 2500);
  };

  const handlePrint = () => {
    window.print();
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#F5F0E8] flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <div className="w-10 h-10 rounded-full border-3 border-[#CC5200] border-t-transparent animate-spin mx-auto" />
          <h3 className="font-serif-yatra font-bold text-lg text-[#1A1A1A]">Opening Shared Yatra...</h3>
        </div>
      </div>
    );
  }

  if (error || !tripData) {
    return (
      <div className="min-h-screen bg-[#F5F0E8] flex items-center justify-center p-6">
        <div className="text-center max-w-md bg-white rounded-3xl border border-[#E0DAD0] p-8 shadow-sm space-y-4">
          <Compass className="w-12 h-12 text-[#CC5200] mx-auto" />
          <h3 className="font-serif-yatra font-bold text-xl text-[#1A1A1A]">Shared Yatra Not Found</h3>
          <p className="text-xs text-[#6B6B6B] leading-relaxed">{error}</p>
          <button
            onClick={() => navigate('/')}
            className="px-5 py-2.5 rounded-xl bg-[#CC5200] text-white text-xs font-bold hover:bg-[#B34700] transition-colors cursor-pointer"
          >
            Plan Your Own Yatra
          </button>
        </div>
      </div>
    );
  }

  const itinerary: Itinerary = tripData.itinerary;
  const route: RouteData | null = tripData.route;

  // Flatten points for MapView
  const allActivities: any[] = [];
  const allMeals: any[] = [];
  itinerary?.days?.forEach((d) => {
    allActivities.push(...(d.activities || []));
    allMeals.push(...(d.meals || []));
  });

  return (
    <div className="min-h-screen bg-[#F5F0E8] flex flex-col">
      {/* Top Bar */}
      <header className="bg-white border-b border-[#E0DAD0] px-4 sm:px-6 py-4 shadow-2xs print:hidden">
        <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate('/')}
              className="p-2 rounded-xl text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#FAF7F2] transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-5 h-5" />
            </button>
            <div>
              <span className="text-[10px] uppercase font-bold text-[#1D705C] tracking-wider block">
                Shared Himalayan Yatra
              </span>
              <h1 className="font-serif-yatra font-bold text-xl text-[#1A1A1A]">
                {tripData.title}
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#FAF7F2] hover:bg-[#EAE4D9] text-[#1A1A1A] text-xs font-bold border border-[#E0DAD0] transition-all cursor-pointer"
            >
              {copied ? <Check className="w-4 h-4 text-emerald-600" /> : <Share2 className="w-4 h-4 text-[#CC5200]" />}
              <span>{copied ? 'Link Copied!' : 'Copy Link'}</span>
            </button>
            <button
              onClick={handlePrint}
              className="flex items-center gap-1.5 px-3.5 py-2 rounded-xl bg-[#CC5200] hover:bg-[#B34700] text-white text-xs font-bold transition-all cursor-pointer shadow-xs"
            >
              <Printer className="w-4 h-4" />
              <span>Print Brief</span>
            </button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Column: Itinerary Details */}
        <div className="lg:col-span-7 space-y-6">
          {/* Summary Card */}
          <div className="p-6 rounded-2xl bg-white border border-[#E0DAD0] shadow-2xs space-y-3">
            <div className="flex items-center justify-between">
              <span className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-[#CC5200]/10 text-[#CC5200]">
                {tripData.num_days} Days • {tripData.pace?.toUpperCase()}
              </span>
              <span className="text-xs text-[#6B6B6B] flex items-center gap-1">
                <MapPin className="w-3.5 h-3.5 text-[#1D705C]" />
                {tripData.origin_name} &rarr; {tripData.dest_name}
              </span>
            </div>
            {itinerary?.summary && (
              <p className="text-sm text-[#1A1A1A] leading-relaxed font-normal pt-1">
                {itinerary.summary}
              </p>
            )}
          </div>

          {/* Days Accordion */}
          <div className="space-y-4">
            {itinerary?.days?.map((day) => (
              <ItineraryCard key={day.day} day={day} />
            ))}
          </div>

          {/* Travel Memories Section */}
          {memories.length > 0 && (
            <div className="p-6 rounded-2xl bg-white border border-[#E0DAD0] shadow-2xs space-y-4">
              <div className="flex items-center gap-2">
                <Camera className="w-5 h-5 text-[#CC5200]" />
                <h3 className="font-serif-yatra font-bold text-lg text-[#1A1A1A]">
                  Traveler Memories • Yatra Smriti
                </h3>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                {memories.map((m) => (
                  <div
                    key={m.id}
                    className="p-3 bg-[#FAF7F2] rounded-2xl border border-[#E0DAD0] shadow-2xs space-y-2"
                  >
                    <div className="aspect-video w-full rounded-xl overflow-hidden bg-black/10">
                      <img
                        src={m.image_url}
                        alt={m.place_name}
                        className="w-full h-full object-cover"
                      />
                    </div>
                    <div>
                      <h4 className="font-serif-yatra font-bold text-sm text-[#1A1A1A]">
                        {m.place_name}
                      </h4>
                      {m.caption && (
                        <p className="text-xs text-[#6B6B6B] mt-0.5">{m.caption}</p>
                      )}
                      {m.ai_reflection && (
                        <p className="text-[11px] text-[#CC5200] italic font-serif-yatra mt-1 leading-snug">
                          "{m.ai_reflection}"
                        </p>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right Column: OpenStreetMap View */}
        <div className="lg:col-span-5 h-[500px] lg:h-[calc(100vh-140px)] sticky top-20 print:hidden">
          <MapView
            routeCoordinates={route?.coordinates || []}
            activities={allActivities}
            meals={allMeals}
            overnight={itinerary?.days?.[0]?.overnight_accommodation}
            origin={allActivities[0] ? { lat: allActivities[0].latitude, lng: allActivities[0].longitude, name: tripData.origin_name } : undefined}
            destination={allActivities[allActivities.length - 1] ? { lat: allActivities[allActivities.length - 1].latitude, lng: allActivities[allActivities.length - 1].longitude, name: tripData.dest_name } : undefined}
            memories={memories}
          />
        </div>
      </main>
    </div>
  );
};
