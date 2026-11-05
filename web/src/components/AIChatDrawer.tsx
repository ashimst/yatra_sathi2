import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Send, Bot, User } from 'lucide-react';
import type { Itinerary } from '../types';
import { apiUrl } from '../api/config';
import { useAuth } from '../context/AuthContext';

// One conversation id per browser tab; the server scopes it to the signed-in user.
const CHAT_SESSION_ID =
  typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `web-${Date.now()}-${Math.random().toString(36).slice(2)}`;

interface Message {
  role: 'user' | 'assistant';
  content: string;
  places?: any[];
  visual_url?: string;
}

interface AIChatDrawerProps {
  isOpen: boolean;
  onClose: () => void;
  itineraryContext?: Itinerary | null;
  onItineraryUpdated?: (updatedItinerary: Itinerary) => void;
}

export const AIChatDrawer: React.FC<AIChatDrawerProps> = ({
  isOpen,
  onClose,
  itineraryContext,
  onItineraryUpdated,
}) => {
  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'assistant',
      content:
        'Namaste! I am your YatraSathi AI companion. You can ask me about sacred sites, mountain viewpoints, road conditions, or ask me to modify your itinerary.',
    },
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const { token } = useAuth();

  const quickPrompts = [
    'Explore places in Pokhara',
    'What are the best viewpoints?',
    'Show me hidden gems in Nepal',
    'Generate a scenic view of Machapuchare',
  ];

  const handleSend = async (messageText?: string) => {
    const textToSend = messageText || input;
    if (!textToSend.trim() || isLoading) return;

    const userMsg: Message = { role: 'user', content: textToSend };
    setMessages((prev) => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
      const res = await fetch(apiUrl('/ai/chat'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          session_id: CHAT_SESSION_ID,
          message: textToSend,
          itinerary_context: itineraryContext,
        }),
      });

      if (!res.ok) {
        const detail = res.status === 429
          ? 'You are sending messages too quickly. Please wait a moment and try again.'
          : res.status === 401
            ? 'Your session has expired. Please refresh the page to continue.'
            : 'The AI companion is unavailable right now. Please try again shortly.';
        setMessages((prev) => [...prev, { role: 'assistant', content: detail }]);
        return;
      }

      const data = await res.json();
      const botMsg: Message = {
        role: 'assistant',
        content: data.response || 'I have processed your request.',
        places: data.places || [],
        visual_url: data.visual_url,
      };

      setMessages((prev) => [...prev, botMsg]);

      // If itinerary was edited via tool, notify parent page
      if (data.updated_itinerary && onItineraryUpdated) {
        onItineraryUpdated(data.updated_itinerary);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Sorry, I had trouble reaching the Nepal travel server. Please try again.',
        },
      ]);
    } finally {
      setIsLoading(false);
    }
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
            <div className="p-4 border-b border-[#E0DAD0] flex items-center justify-between bg-[#FAF7F2]/90 backdrop-blur-md">
              <div className="flex items-center gap-3">
                <img src="/logo.png" alt="YatraSathi" className="w-8 h-8 rounded-lg object-contain shadow-2xs border border-[#E0DAD0]" />
                <div>
                  <h3 className="font-serif-yatra font-bold text-[#1A1A1A] text-base leading-none">YatraSathi AI</h3>
                  <span className="text-[10px] text-[#1D705C] font-semibold uppercase flex items-center gap-1 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-[#1D705C] animate-pulse"></span>
                    Himalayan Travel Co-Pilot
                  </span>
                </div>
              </div>
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#EAE4D9] transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-[#FDFBF7]">
              {messages.map((m, idx) => (
                <div
                  key={idx}
                  className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  {m.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-[#CC5200]/15 text-[#CC5200] flex items-center justify-center shrink-0 mt-0.5">
                      <Bot className="w-4 h-4" />
                    </div>
                  )}

                  <div
                    className={`max-w-[85%] rounded-2xl p-3.5 text-sm ${
                      m.role === 'user'
                        ? 'bg-[#CC5200] text-white shadow-xs rounded-br-xs'
                        : 'bg-white border border-[#E0DAD0] text-[#1A1A1A] shadow-2xs rounded-bl-xs'
                    }`}
                  >
                    <p className="whitespace-pre-wrap leading-relaxed">{m.content}</p>

                    {/* AI Scenic Visual Generated */}
                    {m.visual_url && (
                      <div className="mt-3 rounded-xl overflow-hidden border border-[#E0DAD0] bg-stone-100 shadow-xs relative">
                        <img
                          src={m.visual_url}
                          alt="AI Scenic Preview"
                          className="w-full h-44 object-cover"
                          loading="lazy"
                        />
                        <div className="absolute bottom-2 left-2 px-2.5 py-0.5 rounded-md bg-black/60 text-white text-[10px] font-bold backdrop-blur-xs flex items-center gap-1 border border-white/20">
                          <span>✨</span> AI Scenic Preview
                        </div>
                      </div>
                    )}

                    {/* Discovered Places Cards */}
                    {m.places && m.places.length > 0 && (
                      <div className="mt-3 space-y-2">
                        <span className="text-[10px] uppercase font-bold text-[#6B6B6B] tracking-wider block">
                          Discovered Places ({m.places.length})
                        </span>
                        {m.places.map((place: any, pIdx: number) => (
                          <div
                            key={pIdx}
                            className="p-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-xs shadow-2xs flex gap-2.5 items-start"
                          >
                            {place.image_url ? (
                              <img
                                src={place.image_url}
                                alt={place.name}
                                className="w-14 h-14 rounded-lg object-cover shrink-0 bg-stone-200 border border-[#E0DAD0]"
                                onError={(e) => {
                                  (e.target as HTMLElement).style.display = 'none';
                                }}
                              />
                            ) : (
                              <div className="w-14 h-14 rounded-lg bg-[#FAF5F0] border border-[#E0DAD0] flex items-center justify-center shrink-0 text-xl shadow-2xs">
                                {place.category?.toLowerCase().includes('temple') || place.category?.toLowerCase().includes('religious') ? '🛕' :
                                 place.category?.toLowerCase().includes('viewpoint') || place.category?.toLowerCase().includes('peak') ? '🏔️' :
                                 place.category?.toLowerCase().includes('restaurant') || place.category?.toLowerCase().includes('food') ? '🍲' :
                                 place.category?.toLowerCase().includes('cafe') || place.category?.toLowerCase().includes('coffee') ? '☕' :
                                 place.category?.toLowerCase().includes('hotel') || place.category?.toLowerCase().includes('lodge') ? '🏡' : '🏛️'}
                              </div>
                            )}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center justify-between gap-1">
                                <span className="font-serif-yatra font-bold text-[#1A1A1A] truncate">{place.name}</span>
                                <div className="flex items-center gap-1 shrink-0">
                                  {place.is_hidden_gem && (
                                    <span className="text-[9px] px-1 py-0.2 rounded bg-emerald-100 text-emerald-800 font-bold">
                                      💎
                                    </span>
                                  )}
                                  {place.rating && (
                                    <span className="text-[10px] text-amber-700 font-bold">
                                      ★ {place.rating}
                                    </span>
                                  )}
                                </div>
                              </div>
                              <div className="flex items-center gap-1.5 mt-0.5 text-[10px]">
                                <span className="text-[#1D705C] font-semibold">{place.category}</span>
                                {place.price_level && <span className="text-[#8A726A]">• {place.price_level}</span>}
                              </div>
                              {place.must_try ? (
                                <p className="text-[10px] text-[#9D3E19] font-medium line-clamp-1 mt-0.5">
                                  ✨ {place.must_try}
                                </p>
                              ) : place.description ? (
                                <p className="text-[10px] text-[#6B6B6B] mt-0.5 line-clamp-2 leading-tight">
                                  {place.description}
                                </p>
                              ) : null}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>

                  {m.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-[#EAE4D9] text-[#1A1A1A] flex items-center justify-center shrink-0 mt-0.5">
                      <User className="w-4 h-4" />
                    </div>
                  )}
                </div>
              ))}

              {isLoading && (
                <div className="flex gap-3 items-center">
                  <div className="w-7 h-7 rounded-full bg-[#CC5200]/15 text-[#CC5200] flex items-center justify-center">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="p-3 rounded-2xl bg-white border border-[#E0DAD0] text-xs text-[#6B6B6B] flex items-center gap-1.5 shadow-2xs">
                    <span className="w-2 h-2 rounded-full bg-[#CC5200] animate-bounce"></span>
                    <span className="w-2 h-2 rounded-full bg-[#CC5200] animate-bounce delay-100"></span>
                    <span className="w-2 h-2 rounded-full bg-[#CC5200] animate-bounce delay-200"></span>
                    <span className="ml-1">Checking tools &amp; spatial routing...</span>
                  </div>
                </div>
              )}
            </div>

            {/* Quick Prompts */}
            <div className="p-3 border-t border-[#E0DAD0] bg-[#FAF7F2] flex gap-1.5 overflow-x-auto text-xs no-scrollbar">
              {quickPrompts.map((qp, qIdx) => (
                <button
                  key={qIdx}
                  onClick={() => handleSend(qp)}
                  className="px-3 py-1.5 rounded-full bg-white border border-[#E0DAD0] text-[#1A1A1A] hover:border-[#CC5200] hover:text-[#CC5200] shrink-0 transition-colors cursor-pointer text-xs"
                >
                  {qp}
                </button>
              ))}
            </div>

            {/* Input Bar */}
            <div className="p-3 border-t border-[#E0DAD0] bg-white flex items-center gap-2">
              <input
                type="text"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSend()}
                placeholder="Ask a question or adjust your route..."
                className="flex-1 px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
              />
              <button
                onClick={() => handleSend()}
                disabled={!input.trim() || isLoading}
                className="p-2.5 rounded-xl bg-[#CC5200] text-white disabled:opacity-50 hover:bg-[#B34700] transition-colors cursor-pointer"
              >
                <Send className="w-4 h-4" />
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
};
