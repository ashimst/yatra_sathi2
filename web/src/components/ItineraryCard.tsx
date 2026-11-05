import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import type { ItineraryDay } from '../types';
import { getCategoryColor } from './MapView';
import { 
  ChevronDown, 
  Clock, 
  Utensils, 
  Bed, 
  Compass, 
  Trash2, 
  Sparkles,
  Camera,
  Navigation
} from 'lucide-react';

interface ItineraryCardProps {
  day: ItineraryDay;
  isExpandedDefault?: boolean;
  onRemoveActivity?: (dayNum: number, activityName: string) => void;
  onSwapActivity?: (dayNum: number, oldName: string) => void;
  onAddPhoto?: (placeName: string, lat?: number, lng?: number) => void;
}

export const ItineraryCard: React.FC<ItineraryCardProps> = ({
  day,
  isExpandedDefault = true,
  onRemoveActivity,
  onSwapActivity,
  onAddPhoto,
}) => {
  const [isOpen, setIsOpen] = useState(isExpandedDefault);

  const totalStops = day.activities.length + day.meals.length + (day.overnight_accommodation ? 1 : 0);

  return (
    <div className="bg-white rounded-2xl border border-[#E0DAD0] shadow-sm overflow-hidden transition-all hover:shadow-md">
      {/* Day Accordion Header */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-5 py-4 flex items-center justify-between text-left bg-[#FAF7F2] hover:bg-[#F2ECE1] transition-colors cursor-pointer"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#CC5200] text-white font-bold flex items-center justify-center text-sm shadow-xs font-serif-yatra">
            D{day.day}
          </div>
          <div>
            <h3 className="font-bold text-[#1A1A1A] text-base flex items-center gap-2 font-serif-yatra">
              Day {day.day}
              <span className="text-xs font-normal font-sans px-2.5 py-0.5 rounded-full bg-[#EAE4D9] text-[#1A1A1A]">
                {totalStops} experiences planned
              </span>
            </h3>
            <p className="text-xs text-[#6B6B6B] mt-0.5">
              {day.starting_location || 'Scenic journey through valleys and trails'}
            </p>
          </div>
        </div>

        <motion.div
          animate={{ rotate: isOpen ? 180 : 0 }}
          transition={{ duration: 0.2 }}
          className="text-[#6B6B6B] hover:text-[#1A1A1A] p-1"
        >
          <ChevronDown className="w-5 h-5" />
        </motion.div>
      </button>

      {/* Accordion Content */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: 'easeInOut' }}
            className="border-t border-[#E0DAD0]"
          >
            <div className="p-5 space-y-4">
              {/* Overnight Hotel Card */}
              {day.overnight_accommodation && (
                <div className="p-3.5 rounded-xl bg-[#FAF7F2] border border-[#B45309]/30 flex items-start gap-3">
                  <div className="p-2 rounded-lg bg-[#B45309]/15 text-[#B45309] mt-0.5">
                    <Bed className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between">
                      <span className="text-[10px] font-bold text-[#B45309] uppercase tracking-wider">
                        Night Stay Lodge
                      </span>
                      <span className="text-xs text-[#B45309] font-medium">Overnight</span>
                    </div>
                    <h4 className="font-bold text-[#1A1A1A] text-sm mt-0.5 font-serif-yatra">
                      {day.overnight_accommodation.name}
                    </h4>
                    {day.overnight_accommodation.description && (
                      <p className="text-xs text-[#6B6B6B] mt-1 line-clamp-2 leading-relaxed">
                        {day.overnight_accommodation.description}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* Activities Timeline */}
              <div className="space-y-3">
                <h4 className="text-[11px] font-bold text-[#1D705C] uppercase tracking-wider flex items-center gap-1.5">
                  <Compass className="w-3.5 h-3.5" />
                  Daytime Exploration
                </h4>

                {day.activities.length === 0 ? (
                  <p className="text-xs text-[#6B6B6B] italic py-2">
                    Open travel or relaxed exploration day along the scenic Himalayan corridor.
                  </p>
                ) : (
                  day.activities.map((activity, idx) => {
                    const color = getCategoryColor(activity.category);
                    return (
                      <div
                        key={`act-${idx}`}
                        className="group p-3.5 rounded-xl bg-white border border-[#E0DAD0] hover:border-[#CC5200]/40 transition-all flex items-start justify-between gap-3 shadow-2xs"
                      >
                        <div className="flex items-start gap-3">
                          <div
                            className="w-8 h-8 rounded-lg text-white font-bold text-xs flex items-center justify-center shrink-0 mt-0.5"
                            style={{ backgroundColor: color }}
                          >
                            {idx + 1}
                          </div>
                          <div>
                            <div className="flex flex-wrap items-center gap-2">
                              <span
                                className="text-[10px] font-bold uppercase tracking-wider px-2 py-0.5 rounded-md"
                                style={{ backgroundColor: `${color}15`, color }}
                              >
                                {activity.category || 'Sightseeing'}
                              </span>
                              {activity.start_time && (
                                <span className="text-[11px] text-[#6B6B6B] flex items-center gap-1">
                                  <Clock className="w-3 h-3 text-[#6B6B6B]" />
                                  {activity.start_time} - {activity.end_time || 'Next spot'}
                                </span>
                              )}
                            </div>
                            <h5 className="font-bold text-[#1A1A1A] text-sm mt-1 font-serif-yatra">
                              {activity.name}
                            </h5>
                            {activity.description && (
                              <p className="text-xs text-[#6B6B6B] mt-1 leading-relaxed">
                                {activity.description}
                              </p>
                            )}
                          </div>
                        </div>

                        {/* Action buttons (Agentic tools & Companion Navigation) */}
                        <div className="flex items-center gap-1 opacity-80 sm:opacity-0 sm:group-hover:opacity-100 transition-opacity">
                          {activity.latitude && activity.longitude && (
                            <a
                              href={`https://www.google.com/maps/dir/?api=1&destination=${activity.latitude},${activity.longitude}`}
                              target="_blank"
                              rel="noopener noreferrer"
                              title="Navigate with GPS"
                              className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#1D705C] hover:bg-[#1D705C]/10 cursor-pointer"
                            >
                              <Navigation className="w-3.5 h-3.5" />
                            </a>
                          )}
                          {onAddPhoto && (
                            <button
                              onClick={() => onAddPhoto(activity.name, activity.latitude, activity.longitude)}
                              title="Capture memory / photo"
                              className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#1D705C] hover:bg-[#1D705C]/10 cursor-pointer"
                            >
                              <Camera className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {onSwapActivity && (
                            <button
                              onClick={() => onSwapActivity(day.day, activity.name)}
                              title="Swap this place with AI"
                              className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#CC5200] hover:bg-[#FAF7F2] cursor-pointer"
                            >
                              <Sparkles className="w-3.5 h-3.5" />
                            </button>
                          )}
                          {onRemoveActivity && (
                            <button
                              onClick={() => onRemoveActivity(day.day, activity.name)}
                              title="Remove stop"
                              className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-red-600 hover:bg-red-50 cursor-pointer"
                            >
                              <Trash2 className="w-3.5 h-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>

              {/* Meals Section */}
              {day.meals.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-[#E0DAD0]">
                  <h4 className="text-[11px] font-bold text-[#D97706] uppercase tracking-wider flex items-center gap-1.5">
                    <Utensils className="w-3.5 h-3.5" />
                    Authentic Meal Stops
                  </h4>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                    {day.meals.map((meal, idx) => (
                      <div
                        key={`meal-${idx}`}
                        className="p-2.5 rounded-lg bg-[#FAF7F2] border border-[#D97706]/30 flex items-center gap-2.5"
                      >
                        <div className="p-1.5 rounded-md bg-[#D97706]/15 text-[#D97706]">
                          <Utensils className="w-3.5 h-3.5" />
                        </div>
                        <div className="min-w-0 flex-1">
                          <span className="text-[10px] font-bold text-[#D97706] uppercase block">
                            {meal.meal_type} {meal.time ? `• ${meal.time}` : ''}
                          </span>
                          <span className="text-xs font-bold text-[#1A1A1A] truncate block font-serif-yatra">
                            {meal.name}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};
