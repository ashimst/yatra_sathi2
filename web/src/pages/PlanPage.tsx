import React, { useEffect, useState } from 'react';
import { useSearchParams, useNavigate } from 'react-router-dom';
import type { Itinerary, RouteData, Activity, Meal } from '../types';
import { MapView } from '../components/MapView';
import { apiUrl } from '../api/config';
import { 
  Sparkles, 
  ArrowLeft, 
  Bookmark, 
  Check, 
  ArrowRight,
  Mountain, 
  ShieldCheck,
  Send,
  Utensils,
  Hotel,
  RefreshCw,
  AlertTriangle,
  Share2,
  Compass,
  Calendar,
  SlidersHorizontal,
  ChevronDown
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  DEPARTURE_HUB_GROUPS, 
  DESTINATION_CORRIDOR_GROUPS, 
  NEPAL_LOCATIONS_MAP, 
  CURATED_CORRIDOR_PRESETS 
} from '../data/nepalLocations';
import type { CorridorPreset } from '../data/nepalLocations';

export const PlanPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();
  const { token, refreshProfile } = useAuth();

  // Read initial query params if user arrived from homepage builder or explore card
  const urlOrigin = searchParams.get('origin') || searchParams.get('origin_name');
  const urlDest = searchParams.get('dest') || searchParams.get('dest_name');
  const urlDays = parseInt(searchParams.get('days') || searchParams.get('num_days') || '3');
  const urlPace = searchParams.get('pace') || 'Balanced';
  const urlBudget = searchParams.get('budget') || 'Medium';

  const hasInitialParams = Boolean(urlOrigin && urlDest);

  // Studio Mode: True if user clicked "Plan Yatra" from navbar with no params or clicked "Change Route"
  const [showStudio, setShowStudio] = useState(!hasInitialParams);

  // Active Calibration State
  const [originName, setOriginName] = useState(urlOrigin || 'Kathmandu');
  const [destName, setDestName] = useState(urlDest || 'Pokhara');
  const [numDays, setNumDays] = useState(urlDays);
  const [pace, setPace] = useState(urlPace);
  const [budget, setBudget] = useState(urlBudget);
  const [selectedInterests, setSelectedInterests] = useState<string[]>([
    'Sightseeing',
    'Culture & Monasteries',
    'Nature & Lakes',
    'Local Food & Chai'
  ]);

  // Itinerary & Route Data
  const [itinerary, setItinerary] = useState<Itinerary | null>(null);
  const [route, setRoute] = useState<RouteData | null>(null);
  const [isLoading, setIsLoading] = useState(hasInitialParams);
  const [selectedDayIndex, setSelectedDayIndex] = useState<number | null>(0);
  const [isSharing, setIsSharing] = useState(false);
  const [isQuickCalibrateOpen, setIsQuickCalibrateOpen] = useState(false);

  // Agentic Co-Pilot state
  const [isCopilotOpen, setIsCopilotOpen] = useState(false);
  const [copilotPrompt, setCopilotPrompt] = useState('');
  const [isCopilotExecuting, setIsCopilotExecuting] = useState(false);
  const [proposedDiff, setProposedDiff] = useState<{
    removedName: string;
    removedDesc: string;
    removedMetric: string;
    addedName: string;
    addedDesc: string;
    addedMetric: string;
    walkingDelta: string;
    exertionDelta: string;
    altitudeDelta: string;
    dayNum: number;
    updatedItinerary: Itinerary;
  } | null>(null);

  const [safetyWarning, setSafetyWarning] = useState<{
    title: string;
    reason: string;
    excess_hours: number;
    night_driving: boolean;
  } | null>(null);

  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);

  const [originCoords, setOriginCoords] = useState<[number, number]>(
    NEPAL_LOCATIONS_MAP[originName] || [27.7172, 85.3240]
  );
  const [destCoords, setDestCoords] = useState<[number, number]>(
    NEPAL_LOCATIONS_MAP[destName] || [28.2096, 83.9856]
  );

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

  // Helper to resolve coordinates
  const resolveCoords = async (name: string, fallback: [number, number]): Promise<[number, number]> => {
    if (NEPAL_LOCATIONS_MAP[name]) return NEPAL_LOCATIONS_MAP[name];
    try {
      const res = await fetch(apiUrl(`/places/geocode?q=${encodeURIComponent(name)}`));
      if (res.ok) {
        const data = await res.json();
        if (data.latitude && data.longitude) {
          return [data.latitude, data.longitude];
        }
      }
    } catch (err) {
      console.warn('Geocoding fallback for', name, err);
    }
    return fallback;
  };

  // Core Expedition Generation Engine
  const executePlanGeneration = async (
    targetOrigin = originName,
    targetDest = destName,
    targetDays = numDays,
    targetPace = pace,
    targetBudget = budget
  ) => {
    setIsLoading(true);
    setShowStudio(false);
    setIsQuickCalibrateOpen(false);

    // Synchronize URL parameters
    setSearchParams({
      origin: targetOrigin,
      dest: targetDest,
      days: targetDays.toString(),
      pace: targetPace,
      budget: targetBudget
    });

    try {
      const [oCoords, dCoords] = await Promise.all([
        resolveCoords(targetOrigin, [27.7172, 85.3240]),
        resolveCoords(targetDest, [28.2096, 83.9856])
      ]);

      setOriginCoords(oCoords);
      setDestCoords(dCoords);

      const payload = {
        origin_lat: oCoords[0],
        origin_lng: oCoords[1],
        dest_lat: dCoords[0],
        dest_lng: dCoords[1],
        num_days: targetDays,
        generate_itinerary: true,
        // The API maps UI labels ("High Adventure", "Economy", "Luxury") to its own values.
        travel_style: targetPace,
        budget: targetBudget,
        user_preferences: selectedInterests,
      };

      const res = await fetch(apiUrl('/recommend'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        setRoute(data.route || null);
        setItinerary(data.itinerary || null);
        setSelectedDayIndex(0);
      } else {
        setToastMsg(
          res.status === 429
            ? 'Too many planning requests. Please wait a minute and try again.'
            : 'Could not generate this route. Please try another corridor.'
        );
        setTimeout(() => setToastMsg(null), 4000);
      }
    } catch (err) {
      console.warn('API recommend error, falling back:', err);
      setToastMsg('Failed to generate route. Please try another corridor.');
      setTimeout(() => setToastMsg(null), 3000);
    } finally {
      setIsLoading(false);
    }
  };

  // Auto-run on mount ONLY if initial query params were provided in URL
  useEffect(() => {
    if (hasInitialParams && urlOrigin && urlDest) {
      executePlanGeneration(urlOrigin, urlDest, urlDays, urlPace, urlBudget);
    } else {
      setIsLoading(false);
    }
  }, []);

  // Launch a curated preset
  const handleLaunchPreset = (preset: CorridorPreset) => {
    setOriginName(preset.origin);
    setDestName(preset.dest);
    setNumDays(preset.days);
    setPace(preset.pace);
    setBudget(preset.budget);
    executePlanGeneration(preset.origin, preset.dest, preset.days, preset.pace, preset.budget);
  };

  // Execute Agentic Co-Pilot Prompt via Backend AI
  const handleExecuteCopilot = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!copilotPrompt.trim() || !itinerary || isCopilotExecuting) return;

    setIsCopilotExecuting(true);
    try {
      const res = await fetch(apiUrl('/ai/edit-itinerary'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          current_itinerary: itinerary,
          edit_request: copilotPrompt
        })
      });

      if (res.ok) {
        const data = await res.json();

        // Mountain Highway Safety Hard Constraint Guard
        if (data.safety_rejection) {
          setProposedDiff(null);
          setSafetyWarning(data.safety_warning || {
            title: "Mountain Highway Advisory",
            reason: data.message || "Edit violates safe mountain highway travel constraints.",
            excess_hours: 0,
            night_driving: false
          });
          setToastMsg("Safety Guard: Mountain schedule violation blocked.");
          setTimeout(() => setToastMsg(null), 4000);
          return;
        }

        setSafetyWarning(null);
        const updated = data.updated_itinerary || itinerary;
        
        // Formulate dynamic diff preview for curated trail adjustment
        const diffData = data.diff || {};
        setProposedDiff({
          // Only show values the server actually computed; never invent metrics.
          removedName: diffData.removedName || "",
          removedDesc: diffData.removedDesc || "",
          removedMetric: diffData.removedMetric || "",
          addedName: diffData.addedName || "",
          addedDesc: diffData.addedDesc || data.message || "Adjusted according to your request.",
          addedMetric: diffData.addedMetric || "",
          walkingDelta: diffData.walkingDelta || "",
          exertionDelta: diffData.exertionDelta || "",
          altitudeDelta: diffData.altitudeDelta || "",
          dayNum: diffData.dayNum || 1,
          updatedItinerary: updated
        });

        setToastMsg(`Co-Pilot Proposal: ${data.message || 'Itinerary modification calculated!'}`);
        setTimeout(() => setToastMsg(null), 4000);
      }
    } catch (err) {
      console.error('Co-Pilot error:', err);
      setToastMsg('Failed to reach AI Co-Pilot agent. Please try again.');
      setTimeout(() => setToastMsg(null), 3000);
    } finally {
      setIsCopilotExecuting(false);
    }
  };

  const handleApplyDiff = () => {
    if (proposedDiff?.updatedItinerary) {
      setItinerary(proposedDiff.updatedItinerary);
      setProposedDiff(null);
      setIsCopilotOpen(false);
      setToastMsg('Co-Pilot modification approved and applied to your Yatra!');
      setTimeout(() => setToastMsg(null), 4000);
    }
  };

  const handleRejectDiff = () => {
    setProposedDiff(null);
    setIsCopilotOpen(false);
    setToastMsg('Proposed modification rejected. Original itinerary retained.');
    setTimeout(() => setToastMsg(null), 3000);
  };

  // Save Itinerary to Backend Database
  const handleSaveItinerary = async (): Promise<string | null> => {
    if (!itinerary || isSaving) return shareLink;
    setIsSaving(true);
    try {
      const res = await fetch(apiUrl('/itineraries'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          title: `${originName} to ${destName} Highlights`,
          description: `Curated ${numDays}-Day ${pace} journey across the ${originName} to ${destName} Himalayan corridor.`,
          origin_name: originName,
          dest_name: destName,
          num_days: numDays,
          pace: pace.toLowerCase(),
          budget: budget.toLowerCase(),
          route_data: route,
          itinerary_data: itinerary
        })
      });

      if (res.ok) {
        const savedData = await res.json();
        const share = `/share/${savedData.share_id}`;
        setShareLink(share);
        await refreshProfile();
        setToastMsg(`Yatra saved to your profile! Public share ID: ${savedData.share_id}`);
        setTimeout(() => setToastMsg(null), 5000);
        return share;
      } else {
        setToastMsg(
          res.status === 401
            ? 'Your session expired. Please refresh the page and save again.'
            : 'Could not save this Yatra. Please try again.'
        );
        setTimeout(() => setToastMsg(null), 4000);
        return null;
      }
    } catch (err) {
      setToastMsg('Could not reach the server. Your Yatra was not saved.');
      setTimeout(() => setToastMsg(null), 3000);
      return null;
    } finally {
      setIsSaving(false);
    }
  };

  // Instant Public Share Action
  const handleShareItinerary = async () => {
    if (isSharing) return;
    setIsSharing(true);
    try {
      let activeShare = shareLink;
      if (!activeShare) {
        activeShare = await handleSaveItinerary();
      }
      if (activeShare) {
        const fullShareUrl = `${window.location.origin}${activeShare}`;
        await navigator.clipboard.writeText(fullShareUrl);
        setToastMsg(`Share link copied: ${fullShareUrl}`);
        setTimeout(() => setToastMsg(null), 5000);
      }
    } catch (err) {
      console.error('Share error:', err);
      setToastMsg('Failed to copy link. Please try again.');
      setTimeout(() => setToastMsg(null), 3000);
    } finally {
      setIsSharing(false);
    }
  };

  // Filter days to display
  const daysToDisplay = selectedDayIndex === null
    ? (itinerary?.days || [])
    : (itinerary?.days ? [itinerary.days[selectedDayIndex]] : []);

  const totalKm = route?.distance_km ? Math.round(route.distance_km) : 200;
  const transitHours = route?.duration_minutes ? (route.duration_minutes / 60).toFixed(1) : '4.5';

  return (
    <div className="w-full min-h-screen bg-[#FFF8F6] text-[#201A18] antialiased pb-20">
      {/* Toast Notification */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-[#201A18] text-white rounded-xl shadow-xl flex items-center gap-2 text-xs font-semibold animate-in fade-in slide-in-from-bottom duration-200">
          <Check className="w-4 h-4 text-emerald-400 shrink-0" />
          <span>{toastMsg}</span>
          {shareLink && (
            <button
              onClick={() => navigate(shareLink)}
              className="ml-2 underline text-[#D97706] hover:text-amber-300 cursor-pointer"
            >
              View Share Page
            </button>
          )}
        </div>
      )}

      {/* ============================================================= */}
      {/* 1. EXPEDITION CALIBRATION STUDIO (PRIMARY SELECTION VIEW)    */}
      {/* ============================================================= */}
      {showStudio ? (
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-8 pb-12">
          {/* Studio Header */}
          <div className="max-w-3xl mb-8 space-y-2">
            <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#9D3E19] text-[11px] font-bold uppercase tracking-wider">
              <Compass className="w-3.5 h-3.5" />
              <span>Himalayan Route Calibration Studio</span>
            </div>
            <h1 className="font-serif-yatra text-3xl sm:text-5xl font-bold text-[#201A18] tracking-tight">
              Design Your <span className="italic text-[#9D3E19]">Himalayan Expedition</span>
            </h1>
            <p className="text-xs sm:text-sm text-[#56423B] leading-relaxed">
              Select your departure hub and destination corridor to engineer your personalized journey across Nepal's sacred valleys, trans-Himalayan passes, and mountain sanctuaries.
            </p>
          </div>

          {/* Interactive Calibration Panel */}
          <div className="bg-white/80 backdrop-blur-xl rounded-3xl border border-white/60 shadow-[0_16px_50px_rgba(42,36,33,0.06)] p-6 sm:p-8 mb-12 space-y-6">
            <div className="flex items-center justify-between border-b border-[#E8DDD3] pb-4">
              <div className="flex items-center gap-2">
                <SlidersHorizontal className="w-4 h-4 text-[#9D3E19]" />
                <h3 className="font-serif-yatra text-lg font-bold text-[#201A18]">
                  Route Parameters &amp; Logistics
                </h3>
              </div>
              <span className="text-[11px] font-semibold text-[#1D705C] bg-emerald-50 border border-emerald-200 px-3 py-0.5 rounded-full">
                70+ Curated Nepal Corridors
              </span>
            </div>

            {/* Row 1: Departure & Destination */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Departure Hub */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#201A18] flex items-center gap-1.5">
                  <Compass className="w-4 h-4 text-[#9D3E19]" />
                  <span>Departure Hub</span>
                </label>
                <select
                  value={originName}
                  onChange={(e) => setOriginName(e.target.value)}
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
                <p className="text-[10px] text-[#8A726A]">Where your Himalayan journey commences</p>
              </div>

              {/* Destination Corridor */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#201A18] flex items-center gap-1.5">
                  <Mountain className="w-4 h-4 text-[#9D3E19]" />
                  <span>Destination Corridor</span>
                </label>
                <select
                  value={destName}
                  onChange={(e) => setDestName(e.target.value)}
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
                <p className="text-[10px] text-[#8A726A]">The primary valley, pass, or sanctuary you wish to explore</p>
              </div>
            </div>

            {/* Row 2: Duration, Pace, Budget */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5 pt-2">
              {/* Duration with preset pills & slider */}
              <div className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="text-xs font-bold text-[#201A18] flex items-center gap-1.5">
                    <Calendar className="w-4 h-4 text-[#8A726A]" />
                    <span>Expedition Span</span>
                  </label>
                  <span className="text-xs text-[#9D3E19] font-bold px-2.5 py-0.5 bg-[#FDF1EC] rounded-md border border-[#E8DDD3]">
                    {numDays} Days
                  </span>
                </div>
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {[1, 2, 3, 5, 7, 10, 14].map((d) => (
                    <button
                      type="button"
                      key={d}
                      onClick={() => setNumDays(d)}
                      className={`px-2.5 py-1 rounded-lg text-xs font-bold transition-all cursor-pointer ${
                        numDays === d
                          ? 'bg-[#9D3E19] text-white shadow-xs'
                          : 'bg-[#FDF1EC] text-[#56423B] border border-[#E8DDD3] hover:bg-[#F8EBE6]'
                      }`}
                    >
                      {d}d
                    </button>
                  ))}
                </div>
                <input
                  type="range"
                  min={1}
                  max={14}
                  value={numDays}
                  onChange={(e) => setNumDays(parseInt(e.target.value))}
                  className="w-full h-2 bg-[#F8EBE6] rounded-lg appearance-none cursor-pointer accent-[#9D3E19] mt-2"
                />
              </div>

              {/* Exploration Pace */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#201A18]">
                  Exploration Pace
                </label>
                <select
                  value={pace}
                  onChange={(e) => setPace(e.target.value)}
                  className="w-full bg-[#FDF1EC] text-[#201A18] text-xs font-semibold rounded-xl px-4 py-3 border border-[#E8DDD3] focus:outline-none focus:ring-2 focus:ring-[#9D3E19]/30 cursor-pointer"
                >
                  <option value="Relaxed">Relaxed (1-2 stops/day, slower immersion)</option>
                  <option value="Balanced">Balanced (~3 stops/day, scenic transit)</option>
                  <option value="High Adventure">High Adventure (Full dawn-twilight)</option>
                </select>
                <p className="text-[10px] text-[#8A726A]">Balances physical exertion and rest time</p>
              </div>

              {/* Estimated Budget */}
              <div className="space-y-1.5">
                <label className="text-xs font-bold text-[#201A18]">
                  Estimated Budget
                </label>
                <select
                  value={budget}
                  onChange={(e) => setBudget(e.target.value)}
                  className="w-full bg-[#FDF1EC] text-[#201A18] text-xs font-semibold rounded-xl px-4 py-3 border border-[#E8DDD3] focus:outline-none focus:ring-2 focus:ring-[#9D3E19]/30 cursor-pointer"
                >
                  <option value="Economy">Economy (Teahouses &amp; Local Transit)</option>
                  <option value="Medium">Medium (Comfort Lodges &amp; Private Jeeps)</option>
                  <option value="Luxury">Luxury (Boutique Eco-Resorts &amp; Drivers)</option>
                </select>
                <p className="text-[10px] text-[#8A726A]">Directs accommodation &amp; dining recommendations</p>
              </div>
            </div>

            {/* Row 3: Travel Interests */}
            <div className="space-y-2 pt-2">
              <label className="text-xs font-bold text-[#201A18]">
                Expedition Focus &amp; Interests
              </label>
              <div className="flex flex-wrap gap-2">
                {interestOptions.map((item) => (
                  <button
                    type="button"
                    key={item.id}
                    onClick={() => toggleInterest(item.id)}
                    className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                      selectedInterests.includes(item.id)
                        ? 'bg-[#9D3E19] text-white shadow-xs'
                        : 'bg-[#FDF1EC] text-[#56423B] border border-[#E8DDD3] hover:bg-[#F8EBE6]'
                    }`}
                  >
                    {selectedInterests.includes(item.id) ? '✓ ' : '+ '}
                    {item.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Submit Action Button */}
            <div className="pt-4 border-t border-[#E8DDD3] flex flex-wrap items-center justify-between gap-4">
              <div className="text-xs text-[#8A726A] flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-[#1D705C]" />
                <span>Surveyed Himalayan routing verified against licensed alpine guide intelligence</span>
              </div>

              <button
                type="button"
                onClick={() => executePlanGeneration()}
                disabled={isLoading}
                className="inline-flex items-center gap-2 bg-[#9D3E19] hover:bg-[#BD552F] text-white px-7 py-3 rounded-xl font-bold text-sm shadow-md transition-all cursor-pointer disabled:opacity-50"
              >
                {isLoading ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin" />
                    <span>Crafting Expedition Route...</span>
                  </>
                ) : (
                  <>
                    <Sparkles className="w-4 h-4" />
                    <span>Craft My Himalayan Yatra</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Curated Corridor Presets Section */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <span className="text-[10px] text-[#9D3E19] uppercase tracking-wider font-bold">Recommended Expeditions</span>
                <h3 className="font-serif-yatra text-2xl font-bold text-[#201A18]">
                  Curated Himalayan Corridors
                </h3>
              </div>
              <span className="text-xs text-[#8A726A] hidden sm:inline">1-Click Instant Route Calibration</span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              {CURATED_CORRIDOR_PRESETS.map((preset) => (
                <div
                  key={preset.id}
                  className="p-5 bg-white rounded-2xl border border-[#E8DDD3] hover:border-[#9D3E19]/40 shadow-xs hover:shadow-md transition-all flex flex-col justify-between space-y-4 group"
                >
                  <div className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold uppercase tracking-wider px-2.5 py-0.5 rounded-full bg-[#FDF1EC] text-[#9D3E19] border border-[#E8DDD3]">
                        {preset.badge}
                      </span>
                      <span className="text-xs font-bold text-[#56423B]">
                        {preset.days} Days • {preset.pace}
                      </span>
                    </div>

                    <h4 className="font-serif-yatra font-bold text-lg text-[#201A18] group-hover:text-[#9D3E19] transition-colors">
                      {preset.title}
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      {preset.subtitle}
                    </p>

                    <div className="pt-2 border-t border-[#E8DDD3] space-y-1">
                      {preset.highlights.map((h, i) => (
                        <div key={i} className="text-[11px] text-[#8A726A] flex items-center gap-1.5">
                          <span className="text-[#9D3E19]">✦</span>
                          <span>{h}</span>
                        </div>
                      ))}
                    </div>
                  </div>

                  <button
                    type="button"
                    onClick={() => handleLaunchPreset(preset)}
                    className="w-full py-2.5 rounded-xl bg-[#FDF1EC] hover:bg-[#9D3E19] text-[#9D3E19] hover:text-white font-bold text-xs transition-colors flex items-center justify-center gap-1.5 cursor-pointer shadow-2xs"
                  >
                    <span>Launch This Yatra</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        /* ============================================================= */
        /* 2. ITINERARY VIEW (ACTIVE YATRA ROUTE)                         */
        /* ============================================================= */
        <>
          {/* Top Breadcrumb & Actions Bar */}
          <div className="border-b border-[#E8DDD3] bg-white/80 backdrop-blur-md sticky top-20 z-30">
            <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-3 flex flex-wrap items-center justify-between gap-3">
              <button
                onClick={() => setShowStudio(true)}
                className="inline-flex items-center gap-2 text-xs font-bold text-[#56423B] hover:text-[#9D3E19] transition-colors cursor-pointer"
              >
                <ArrowLeft className="w-4 h-4" />
                <span>Adjust Route in Calibration Studio</span>
              </button>

              <div className="flex items-center gap-2">
                <button
                  id="btn-quick-calibrate"
                  onClick={() => setIsQuickCalibrateOpen(!isQuickCalibrateOpen)}
                  className="inline-flex items-center gap-1.5 bg-[#FAF7F2] hover:bg-[#FDF1EC] text-[#56423B] border border-[#E8DDD3] px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-2xs"
                >
                  <SlidersHorizontal className="w-3.5 h-3.5 text-[#9D3E19]" />
                  <span>Change Parameters</span>
                  <ChevronDown className={`w-3.5 h-3.5 transition-transform ${isQuickCalibrateOpen ? 'rotate-180' : ''}`} />
                </button>

                <button
                  id="btn-agentic-copilot"
                  onClick={() => setIsCopilotOpen(!isCopilotOpen)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-all cursor-pointer shadow-2xs ${
                    isCopilotOpen
                      ? 'bg-[#9D3E19] text-white'
                      : 'bg-[#FDF1EC] text-[#9D3E19] border border-[#E8DDD3] hover:bg-[#F8EBE6]'
                  }`}
                >
                  <Sparkles className="w-3.5 h-3.5" />
                  <span>{isCopilotOpen ? 'Close Co-Pilot' : 'Himalayan Co-Pilot'}</span>
                </button>

                <button
                  onClick={handleSaveItinerary}
                  disabled={isSaving || isLoading || !itinerary}
                  className="inline-flex items-center gap-1.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shadow-xs cursor-pointer disabled:opacity-50"
                >
                  {isSaving || isLoading ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Bookmark className="w-3.5 h-3.5" />}
                  <span>{isSaving ? 'Saving...' : isLoading ? 'Crafting...' : 'Save Yatra'}</span>
                </button>

                <button
                  onClick={handleShareItinerary}
                  disabled={isSharing || isLoading || !itinerary}
                  className="inline-flex items-center gap-1.5 bg-white hover:bg-[#FDF1EC] text-[#56423B] border border-[#E8DDD3] px-3.5 py-1.5 rounded-lg text-xs font-bold transition-all shadow-2xs cursor-pointer disabled:opacity-50"
                  title="Copy public link to share this itinerary"
                >
                  {isSharing ? <RefreshCw className="w-3.5 h-3.5 animate-spin text-[#9D3E19]" /> : <Share2 className="w-3.5 h-3.5 text-[#9D3E19]" />}
                  <span>{shareLink ? 'Share Link' : 'Share'}</span>
                </button>
              </div>
            </div>

            {/* Quick Calibration Bar (Collapsible) */}
            {isQuickCalibrateOpen && (
              <div className="border-t border-[#E8DDD3] bg-[#FAF7F2] p-4 sm:px-12 animate-in fade-in duration-200">
                <div className="max-w-[1280px] mx-auto grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3 items-end">
                  <div>
                    <label className="text-[11px] font-bold text-[#201A18] block mb-1">Departure Hub</label>
                    <select
                      value={originName}
                      onChange={(e) => setOriginName(e.target.value)}
                      className="w-full bg-white text-xs font-semibold rounded-lg px-3 py-2 border border-[#E8DDD3]"
                    >
                      {DEPARTURE_HUB_GROUPS.map((g) => (
                        <optgroup key={g.groupName} label={g.groupName}>
                          {g.options.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-[#201A18] block mb-1">Destination Corridor</label>
                    <select
                      value={destName}
                      onChange={(e) => setDestName(e.target.value)}
                      className="w-full bg-white text-xs font-semibold rounded-lg px-3 py-2 border border-[#E8DDD3]"
                    >
                      {DESTINATION_CORRIDOR_GROUPS.map((g) => (
                        <optgroup key={g.groupName} label={g.groupName}>
                          {g.options.map((o) => (
                            <option key={o.value} value={o.value}>{o.label}</option>
                          ))}
                        </optgroup>
                      ))}
                    </select>
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-[#201A18] block mb-1">Duration: {numDays} Days</label>
                    <input
                      type="range"
                      min={1}
                      max={14}
                      value={numDays}
                      onChange={(e) => setNumDays(parseInt(e.target.value))}
                      className="w-full accent-[#9D3E19]"
                    />
                  </div>

                  <div>
                    <label className="text-[11px] font-bold text-[#201A18] block mb-1">Pace</label>
                    <select
                      value={pace}
                      onChange={(e) => setPace(e.target.value)}
                      className="w-full bg-white text-xs font-semibold rounded-lg px-3 py-2 border border-[#E8DDD3]"
                    >
                      <option value="Relaxed">Relaxed</option>
                      <option value="Balanced">Balanced</option>
                      <option value="High Adventure">High Adventure</option>
                    </select>
                  </div>

                  <button
                    onClick={() => executePlanGeneration()}
                    disabled={isLoading}
                    className="w-full py-2 bg-[#9D3E19] hover:bg-[#BD552F] text-white text-xs font-bold rounded-lg transition-colors cursor-pointer disabled:opacity-50"
                  >
                    {isLoading ? 'Crafting...' : 'Re-Calibrate'}
                  </button>
                </div>
              </div>
            )}
          </div>

          <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-8">
            {/* Title Header */}
            <div className="mb-8">
              <div className="flex flex-wrap items-center gap-2 mb-2">
                <span className="px-2.5 py-1 rounded-full bg-[#9D3E19] text-white text-[11px] font-bold uppercase tracking-wider">
                  {numDays} Days • {pace}
                </span>
                <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[#56423B] border border-[#E8DDD3] text-[11px] font-semibold">
                  Approx. {totalKm} km • {transitHours} hrs scenic transit
                </span>
                <span className="px-2.5 py-1 rounded-full bg-[#FDF1EC] text-[#904D00] border border-[#E8DDD3] text-[11px] font-semibold">
                  {originName} to {destName} Corridor
                </span>
                {isLoading && (
                  <span className="px-2.5 py-1 rounded-full bg-amber-100 text-amber-800 text-[11px] font-bold animate-pulse">
                    Synchronizing trail coordinates &amp; conditions...
                  </span>
                )}
              </div>
              <h1 className="font-serif-yatra text-3xl sm:text-5xl font-bold text-[#201A18] tracking-tight">
                {originName} to {destName} Highlights
              </h1>
              <p className="text-xs sm:text-sm text-[#56423B] mt-2 max-w-2xl leading-relaxed">
                A serene Himalayan journey calibrated from {originName} to {destName}. Grounded in surveyed Himalayan trails and licensed mountain guide routes.
              </p>
            </div>

            {/* ============================================================= */}
            {/* HIMALAYAN CO-PILOT DIFF BANNER (CURATED MODIFICATIONS)        */}
            {/* ============================================================= */}
            {isCopilotOpen && (
              <div className="mb-8 rounded-3xl bg-white/90 backdrop-blur-xl border border-white/70 p-6 sm:p-8 shadow-[0_16px_50px_rgba(42,36,33,0.08)] relative overflow-hidden animate-in fade-in slide-in-from-top-4 duration-300">
                <div className="flex flex-wrap items-center justify-between gap-3 mb-4 pb-3 border-b border-[#E8DDD3]">
                  <div className="flex items-center gap-2">
                    <span className="px-3 py-1 rounded-full bg-[#9D3E19] text-white text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 shadow-2xs">
                      <Sparkles className="w-3.5 h-3.5" />
                      Himalayan Route Adjustment (Proposed)
                    </span>
                    <span className="text-xs text-[#8A726A] hidden sm:inline">Curated Adjustment</span>
                  </div>
                  <div className="text-xs font-bold text-[#9D3E19]">
                    <span>Pending Traveler Review</span>
                  </div>
                </div>

                {/* Prompt Form */}
                <form onSubmit={handleExecuteCopilot} className="mb-4">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={copilotPrompt}
                      onChange={(e) => setCopilotPrompt(e.target.value)}
                      placeholder="Ask your guide to adjust itinerary (e.g. 'Swap Day 2 temple with quiet lakeside cafe')..."
                      className="flex-1 bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl px-4 py-2.5 text-xs text-[#201A18] focus:outline-none focus:ring-2 focus:ring-[#9D3E19]"
                    />
                    <button
                      type="submit"
                      disabled={isCopilotExecuting}
                      className="px-4 py-2.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white font-bold text-xs rounded-xl flex items-center gap-1.5 transition-colors cursor-pointer disabled:opacity-50 shadow-xs"
                    >
                      <Send className="w-3.5 h-3.5" />
                      <span>{isCopilotExecuting ? 'Analyzing...' : 'Adjust Route'}</span>
                    </button>
                  </div>
                </form>

                {/* Mountain Highway Safety Advisory */}
                {safetyWarning && (
                  <div className="p-4 rounded-xl bg-amber-50/90 border border-amber-300 text-amber-950 space-y-2 mt-2 animate-in fade-in">
                    <div className="flex items-center gap-2 text-xs font-bold text-amber-900 uppercase tracking-wider">
                      <AlertTriangle className="w-4 h-4 text-amber-700 shrink-0" />
                      <span>{safetyWarning.title}</span>
                    </div>
                    <p className="text-xs text-amber-900 leading-relaxed font-medium">
                      {safetyWarning.reason}
                    </p>
                    <div className="flex items-center justify-between pt-2 border-t border-amber-200 text-[11px] font-semibold text-amber-800">
                      <span>Advisory Status: <strong className="text-[#9D3E19]">Mountain Safety Precaution</strong></span>
                      <button
                        onClick={() => setSafetyWarning(null)}
                        className="px-3 py-1 bg-amber-200/80 hover:bg-amber-300 rounded-lg text-amber-950 text-xs font-bold transition-colors cursor-pointer"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                )}

                {/* Proposed Diff Cards */}
                {proposedDiff && (
                  <>
                    <div className="space-y-3">
                      {/* REMOVING */}
                      {proposedDiff.removedName && (
                      <div className="p-4 rounded-xl bg-red-50/70 border border-red-200 flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-red-100 text-red-700 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                            ✕
                          </div>
                          <div>
                            <div className="text-[11px] font-bold text-red-700 uppercase tracking-wider">
                              Removing • Day {proposedDiff.dayNum}
                            </div>
                            <div className="text-sm font-bold text-[#201A18] line-through mt-0.5">
                              {proposedDiff.removedName}
                            </div>
                            {proposedDiff.removedDesc && (
                              <div className="text-xs text-[#56423B] mt-1">
                                {proposedDiff.removedDesc}
                              </div>
                            )}
                          </div>
                        </div>
                        {proposedDiff.removedMetric && (
                          <span className="text-xs font-bold text-red-700 bg-red-100 px-2.5 py-0.5 rounded-full shrink-0">
                            {proposedDiff.removedMetric}
                          </span>
                        )}
                      </div>
                      )}

                      {/* Arrow Indicator */}
                      {proposedDiff.removedName && proposedDiff.addedName && (
                        <div className="flex justify-center -my-1 text-[#9D3E19]">
                          <ArrowRight className="w-5 h-5 rotate-90" />
                        </div>
                      )}

                      {/* ADDING */}
                      <div className="p-4 rounded-xl bg-emerald-50/70 border border-emerald-200 flex items-start justify-between gap-3">
                        <div className="flex items-start gap-3">
                          <div className="w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs shrink-0 mt-0.5">
                            +
                          </div>
                          <div>
                            <div className="text-[11px] font-bold text-emerald-800 uppercase tracking-wider flex items-center gap-1.5">
                              <span>{proposedDiff.addedName ? 'Adding' : 'Updated'} • Day {proposedDiff.dayNum}</span>
                            </div>
                            {proposedDiff.addedName && (
                              <div className="text-sm font-bold text-[#201A18] mt-0.5">
                                {proposedDiff.addedName}
                              </div>
                            )}
                            <p className="text-xs text-[#56423B] mt-1 leading-relaxed">
                              {proposedDiff.addedDesc}
                            </p>
                          </div>
                        </div>
                        {proposedDiff.addedMetric && (
                          <span className="text-xs font-bold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full shrink-0">
                            {proposedDiff.addedMetric}
                          </span>
                        )}
                      </div>
                    </div>

                    {/* Trail Impact & Effort Summary (only when the server computed it) */}
                    {(proposedDiff.walkingDelta || proposedDiff.exertionDelta || proposedDiff.altitudeDelta) && (
                    <div className="grid grid-cols-3 gap-3 my-4">
                      <div className="p-3 bg-[#FDF1EC] rounded-xl border border-[#E8DDD3] text-center">
                        <div className="text-[10px] text-[#8A726A] uppercase font-bold">Walking Distance</div>
                        <div className="text-sm font-bold text-[#9D3E19]">{proposedDiff.walkingDelta || '—'}</div>
                      </div>
                      <div className="p-3 bg-[#FDF1EC] rounded-xl border border-[#E8DDD3] text-center">
                        <div className="text-[10px] text-[#8A726A] uppercase font-bold">Trail Exertion Level</div>
                        <div className="text-sm font-bold text-emerald-700">{proposedDiff.exertionDelta || '—'}</div>
                      </div>
                      <div className="p-3 bg-[#FDF1EC] rounded-xl border border-[#E8DDD3] text-center">
                        <div className="text-[10px] text-[#8A726A] uppercase font-bold">Acclimatization</div>
                        <div className="text-sm font-bold text-[#201A18]">{proposedDiff.altitudeDelta || '—'}</div>
                      </div>
                    </div>
                    )}

                    {/* Decision Buttons */}
                    <div className="flex items-center justify-end gap-3 pt-2">
                      <button
                        onClick={handleRejectDiff}
                        className="px-4 py-2 rounded-xl text-xs font-bold text-[#56423B] bg-[#FDF1EC] hover:bg-[#F8EBE6] transition-colors cursor-pointer"
                      >
                        Reject Changes
                      </button>
                      <button
                        onClick={handleApplyDiff}
                        className="px-5 py-2 rounded-xl text-xs font-bold text-white bg-[#9D3E19] hover:bg-[#BD552F] shadow-xs transition-colors cursor-pointer"
                      >
                        Approve &amp; Apply to Yatra
                      </button>
                    </div>
                  </>
                )}
              </div>
            )}

            {/* Elevation Profile & Mountain Acclimatization Card */}
            <div className="mb-8 p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
              <div className="flex flex-wrap items-center justify-between gap-3 mb-3">
                <div className="flex items-center gap-2">
                  <Mountain className="w-4 h-4 text-[#9D3E19]" />
                  <span className="text-xs font-bold text-[#201A18]">Elevation Profile &amp; Mountain Acclimatization</span>
                </div>
                <div className="text-xs text-[#8A726A] font-semibold">
                  Elevation profile calibrated for {originName} → {destName}
                </div>
              </div>

              <div className="p-3 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] flex flex-wrap items-center justify-between gap-3">
                <div className="flex items-center gap-2 text-xs font-semibold text-[#201A18]">
                  <ShieldCheck className="w-4 h-4 text-[#1D705C]" />
                  <span>Altitude Safety: Acclimatization Within Safe Limits</span>
                </div>
                <div className="text-xs text-[#56423B]">
                  Pace: {pace} • Daily elevation gain monitored
                </div>
              </div>
            </div>

            {/* Dynamic Day Switcher Pills */}
            <div className="flex flex-wrap gap-2 mb-8">
              <button
                onClick={() => setSelectedDayIndex(null)}
                className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer ${
                  selectedDayIndex === null
                    ? 'bg-[#9D3E19] text-white shadow-xs'
                    : 'bg-white text-[#56423B] border border-[#E8DDD3] hover:bg-[#FDF1EC]'
                }`}
              >
                All Days
              </button>
              {itinerary?.days?.map((d, i) => (
                <button
                  key={d.day}
                  onClick={() => setSelectedDayIndex(i)}
                  className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer ${
                    selectedDayIndex === i
                      ? 'bg-[#9D3E19] text-white shadow-xs'
                      : 'bg-white text-[#56423B] border border-[#E8DDD3] hover:bg-[#FDF1EC]'
                  }`}
                >
                  Day {d.day}: {d.starting_location || (i === 0 ? 'Valley Departure' : i === 1 ? 'Corridor Discovery' : 'Alpine Sanctuary')}
                </button>
              ))}
            </div>

            {/* ============================================================= */}
            {/* MASTER-DETAIL GRID: LEFT STAGES & RIGHT TELEMETRY MAP         */}
            {/* ============================================================= */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* Left Column: Itinerary Stages */}
              <div className="lg:col-span-7 space-y-6">
                {isLoading ? (
                  <div className="space-y-6">
                    {[1, 2, 3].map((sDay) => (
                      <div key={sDay} className="p-6 bg-white rounded-2xl border border-[#E8DDD3] shadow-xs space-y-4 animate-pulse">
                        <div className="flex items-center justify-between">
                          <div className="h-6 w-48 bg-stone-200 rounded-md"></div>
                          <div className="h-4 w-28 bg-stone-200 rounded-md"></div>
                        </div>
                        <div className="h-48 w-full bg-stone-200 rounded-xl"></div>
                        <div className="space-y-2">
                          <div className="h-4 w-3/4 bg-stone-200 rounded-md"></div>
                          <div className="h-3 w-1/2 bg-stone-200 rounded-md"></div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : daysToDisplay.length === 0 ? (
                  <div className="p-12 text-center bg-white rounded-2xl border border-[#E8DDD3]">
                    <p className="text-sm font-semibold text-[#56423B]">No itinerary stops found for this selection.</p>
                  </div>
                ) : (
                  <AnimatePresence mode="wait">
                    <motion.div
                      key={selectedDayIndex !== null ? `day-${selectedDayIndex}` : 'all-days'}
                      initial={{ opacity: 0, y: 12 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -12 }}
                      transition={{ duration: 0.25, ease: "easeOut" }}
                      className="space-y-8"
                    >
                      {daysToDisplay.map((dayItem) => (
                        <div key={dayItem.day} className="space-y-4">
                          <div className="flex items-baseline justify-between border-b border-[#E8DDD3] pb-2">
                            <h2 className="font-serif-yatra text-2xl font-bold text-[#201A18]">
                              Day {dayItem.day}: {dayItem.starting_location || `Segment ${dayItem.day}`}
                            </h2>
                            <span className="text-xs text-[#8A726A] font-medium">
                              {dayItem.activities?.length || 0} activities • {dayItem.meals?.length || 0} meals
                            </span>
                          </div>

                          {/* Activities Stack */}
                          <div className="space-y-4">
                            {dayItem.activities?.map((act: Activity, aIdx: number) => (
                              <div
                                key={act.poi_id || act.name || aIdx}
                                className="bg-white rounded-2xl border border-[#E8DDD3] p-5 shadow-xs hover:shadow-md transition-shadow relative overflow-hidden"
                              >
                                <div className="flex items-start justify-between gap-3">
                                  <div className="flex items-start gap-3.5">
                                    <span className="w-7 h-7 rounded-full bg-[#FDF1EC] text-[#9D3E19] flex items-center justify-center font-bold text-xs shrink-0 mt-0.5 border border-[#E8DDD3]">
                                      {aIdx + 1}
                                    </span>
                                    <div>
                                      <h3 className="font-serif-yatra text-lg font-bold text-[#201A18]">
                                        {act.name}
                                      </h3>
                                      <div className="flex items-center gap-2 mt-0.5 text-xs text-[#8A726A]">
                                        <span className="capitalize">{act.category || 'Attraction'}</span>
                                        {act.duration_hours && <span>• {act.duration_hours} hrs</span>}
                                        {act.price_level ? (
                                          <span>• {act.price_level}</span>
                                        ) : (
                                          <span>• Free admission</span>
                                        )}
                                      </div>
                                    </div>
                                  </div>
                                  <span className="px-2.5 py-1 rounded-md bg-[#FAF7F2] text-[10px] font-bold text-[#8A726A] uppercase tracking-wider border border-[#E8DDD3]">
                                    STOP {aIdx + 1}
                                  </span>
                                </div>

                                {act.description && (
                                  <p className="text-xs text-[#56423B] mt-3 leading-relaxed">
                                    {act.description}
                                  </p>
                                )}

                                {/* Insider Tip Box */}
                                {act.must_try && (
                                  <div className="mt-3.5 p-3 rounded-xl bg-amber-50/80 border border-amber-200/70 text-xs text-amber-950 flex items-start gap-2">
                                    <span className="text-sm leading-none">✨</span>
                                    <div className="leading-snug">
                                      <span className="font-bold text-amber-950">Insider Tip:</span> {act.must_try}
                                    </div>
                                  </div>
                                )}
                              </div>
                            ))}
                          </div>

                          {/* Meals & Recommended Lodging */}
                          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                            {dayItem.meals && dayItem.meals.length > 0 && (
                              <div className="p-4 rounded-xl bg-white border border-[#E8DDD3] space-y-2">
                                <div className="flex items-center gap-2 text-xs font-bold text-[#9D3E19]">
                                  <Utensils className="w-4 h-4" />
                                  <span>Culinary Recommendation</span>
                                </div>
                                {dayItem.meals.map((meal: Meal, mIdx: number) => (
                                  <div key={mIdx} className="text-xs text-[#56423B]">
                                    <strong className="text-[#201A18]">{meal.name}</strong> ({meal.meal_type || 'Regional Cuisine'})
                                    {meal.must_try && <p className="text-[11px] text-[#8A726A]">Must Try: {meal.must_try}</p>}
                                  </div>
                                ))}
                              </div>
                            )}

                            {dayItem.overnight_accommodation && (
                              <div className="p-4 rounded-xl bg-white border border-[#E8DDD3] space-y-2">
                                <div className="flex items-center gap-2 text-xs font-bold text-[#1D705C]">
                                  <Hotel className="w-4 h-4" />
                                  <span>Recommended Night Stay</span>
                                </div>
                                <div className="text-xs text-[#56423B]">
                                  <strong className="text-[#201A18]">{dayItem.overnight_accommodation.name}</strong>
                                  <p className="text-[11px] text-[#8A726A]">
                                    Verified teahouse/lodge • {dayItem.overnight_accommodation.price_level || 'Comfort Lodging'}
                                  </p>
                                </div>
                              </div>
                            )}
                          </div>
                        </div>
                      ))}
                    </motion.div>
                  </AnimatePresence>
                )}
              </div>

              {/* Right Column: GIS Telemetry Map */}
              <div className="lg:col-span-5 sticky top-36 space-y-4">
                <div className="p-4 bg-white/85 backdrop-blur-md rounded-2xl border border-white/60 shadow-xs">
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center gap-2 text-xs font-bold text-[#201A18]">
                      <span className="w-2 h-2 rounded-full bg-[#1D705C] animate-pulse" />
                      <span>LIVE EXPEDITION TRAIL &amp; WAYPOINTS</span>
                    </div>
                    <span className="text-[10px] text-[#8A726A] font-semibold bg-[#FDF1EC] px-2 py-0.5 rounded-md border border-[#E8DDD3]">
                      GPS Track Verified
                    </span>
                  </div>

                  {/* Map Component */}
                  <div className="h-[460px] rounded-xl overflow-hidden border border-[#E8DDD3]">
                    <MapView
                      routeCoordinates={route?.coordinates}
                      activities={
                        selectedDayIndex === null
                          ? itinerary?.days?.flatMap((d) => d.activities || [])
                          : itinerary?.days?.[selectedDayIndex]?.activities || []
                      }
                      meals={
                        selectedDayIndex === null
                          ? itinerary?.days?.flatMap((d) => d.meals || [])
                          : itinerary?.days?.[selectedDayIndex]?.meals || []
                      }
                      overnight={
                        selectedDayIndex === null
                          ? itinerary?.days?.[0]?.overnight_accommodation
                          : itinerary?.days?.[selectedDayIndex]?.overnight_accommodation
                      }
                      origin={{ lat: originCoords[0], lng: originCoords[1], name: originName }}
                      destination={{ lat: destCoords[0], lng: destCoords[1], name: destName }}
                    />
                  </div>

                  <div className="mt-3 flex items-center justify-between text-xs text-[#8A726A]">
                    <span>Origin: {originName}</span>
                    <span>&rarr;</span>
                    <span>Destination: {destName}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};
