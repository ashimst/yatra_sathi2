import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { 
  Sparkles, 
  User as UserIcon, 
  Bookmark,
  ShieldAlert,
  BookOpen,
  Compass,
  ScrollText,
  Calendar,
  Mountain,
  Cpu
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface NavbarProps {
  onOpenAIChat: () => void;
  onOpenSavedTrips?: () => void;
  onOpenAuth?: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenAIChat, onOpenSavedTrips, onOpenAuth }) => {
  const location = useLocation();
  const { user } = useAuth();

  const navLinks = [
    { to: '/', label: 'Home', icon: Compass },
    { to: '/plan', label: 'Plan Yatra', icon: Calendar },
    { to: '/explore', label: 'Explore', icon: Mountain },
    { to: '/trail-watch', label: 'Trail Watch', icon: ShieldAlert },
    { to: '/yatra-smriti', label: 'Yatra Smriti', icon: BookOpen },
    { to: '/cultural-sanctuary', label: 'Sanctuary', icon: ScrollText },
    { to: '/architecture', label: 'Architecture', icon: Cpu },
  ];

  return (
    <header className="sticky top-0 z-40 bg-[#FFF8F6]/85 backdrop-blur-xl border-b border-white/60 shadow-[0_4px_24px_rgba(42,36,33,0.05)]">
      {/* Traditional Himalayan Prayer Flag Harmonic Top Accent (Blue, White, Red, Green, Yellow) */}
      <div className="h-1 w-full flex">
        <div className="flex-1 bg-[#1A73E8]" title="Sky / Space" />
        <div className="flex-1 bg-[#FFFFFF] border-y border-[#E8DDD3]" title="Air / Wind" />
        <div className="flex-1 bg-[#D93025]" title="Fire" />
        <div className="flex-1 bg-[#188038]" title="Water" />
        <div className="flex-1 bg-[#F9AB00]" title="Earth" />
      </div>

      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between gap-4">
        {/* Brand with official YatraSathi Nepal Logo */}
        <div className="flex items-center gap-6">
          <Link to="/" className="flex flex-col group">
            <div className="flex items-baseline gap-1.5">
              <span className="font-serif-yatra font-bold text-2xl text-[#201A18] tracking-tight group-hover:text-[#9D3E19] transition-colors">
                YatraSathi
              </span>
              <span className="font-serif-yatra font-bold text-2xl text-[#9D3E19]">
                यात्रा
              </span>
            </div>
            <span className="text-[10px] uppercase font-bold text-[#8A726A] tracking-widest -mt-0.5">
              Nepal Intelligent Companion
            </span>
          </Link>

          {/* Navigation links */}
          <nav className="hidden xl:flex items-center gap-1">
            {navLinks.map((item) => {
              const isActive = location.pathname === item.to;
              return (
                <Link
                  key={item.to}
                  to={item.to}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    isActive
                      ? 'text-[#9D3E19] font-bold border-b-2 border-[#9D3E19] bg-[#FDF1EC]'
                      : 'text-[#56423B] hover:text-[#201A18] hover:bg-[#F8EBE6]'
                  }`}
                >
                  {item.label}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-2 sm:gap-3">
          {/* Ask AI Pill Button */}
          <button
            onClick={onOpenAIChat}
            className="inline-flex items-center gap-1.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white px-3.5 py-1.5 sm:px-4 sm:py-2 rounded-lg transition-colors text-xs font-bold shadow-[0_2px_8px_-2px_rgba(42,36,33,0.15)] cursor-pointer"
          >
            <Sparkles className="w-3.5 h-3.5" />
            <span>Ask AI</span>
          </button>

          {/* Saved Yatras Button */}
          {onOpenSavedTrips && (
            <button
              onClick={onOpenSavedTrips}
              title="My Saved Yatras"
              className="p-2 rounded-lg bg-white hover:bg-[#FDF1EC] text-[#201A18] border border-[#E8DDD3] transition-all cursor-pointer shadow-2xs"
            >
              <Bookmark className="w-4 h-4 text-[#9D3E19]" />
            </button>
          )}

          {/* User Profile / Auth Button */}
          {onOpenAuth && (
            <button
              onClick={onOpenAuth}
              className="w-8 h-8 rounded-full bg-[#9D3E19] text-white flex items-center justify-center font-bold text-xs hover:bg-[#BD552F] transition-colors cursor-pointer shadow-2xs"
              title={user ? user.username : 'Sign In'}
            >
              {user ? (
                user.full_name?.slice(0, 2).toUpperCase() || <UserIcon className="w-4 h-4" />
              ) : (
                <UserIcon className="w-4 h-4" />
              )}
            </button>
          )}
        </div>
      </div>

      {/* Mobile Navigation bar */}
      <div className="xl:hidden flex overflow-x-auto gap-2 px-4 py-2 border-t border-[#E8DDD3] bg-[#FDF1EC]/80 scrollbar-none">
        {navLinks.map((item) => {
          const isActive = location.pathname === item.to;
          return (
            <Link
              key={item.to}
              to={item.to}
              className={`px-3 py-1 rounded-full text-xs font-semibold whitespace-nowrap shrink-0 transition-colors ${
                isActive
                  ? 'bg-[#9D3E19] text-white'
                  : 'text-[#56423B] bg-white border border-[#E8DDD3]'
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </div>
    </header>
  );
};
