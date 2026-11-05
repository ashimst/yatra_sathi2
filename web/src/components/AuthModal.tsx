import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  X, 
  Sparkles, 
  User, 
  Lock, 
  Mail, 
  ArrowRight, 
  ShieldCheck, 
  LogOut, 
  Bookmark, 
  Camera, 
  Check, 
  KeyRound,
  RefreshCw
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';

interface AuthModalProps {
  isOpen: boolean;
  onClose: () => void;
  onOpenSavedTrips?: () => void;
}

export const AuthModal: React.FC<AuthModalProps> = ({ isOpen, onClose, onOpenSavedTrips }) => {
  const { user, login, register, upgradeGuest, loginAsGuest, logout, refreshProfile } = useAuth();
  const navigate = useNavigate();

  // Mode: 'profile' (if user exists), 'login', 'register', or 'upgrade'
  const [viewMode, setViewMode] = useState<'profile' | 'login' | 'register' | 'upgrade'>('profile');

  // Form states
  const [usernameOrEmail, setUsernameOrEmail] = useState('');
  const [password, setPassword] = useState('');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [fullName, setFullName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Sync mode with user existence on modal open
  useEffect(() => {
    if (isOpen) {
      setError(null);
      setSuccessMsg(null);
      refreshProfile();
      if (user) {
        setViewMode('profile');
      } else {
        setViewMode('login');
      }
    }
  }, [isOpen, user?.id]);

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const success = await login(usernameOrEmail, password);
    setIsSubmitting(false);
    if (success) {
      setViewMode('profile');
      onClose();
    } else {
      setError('Invalid username or password. Please try again.');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const res = await register(email, username, password, fullName);
    setIsSubmitting(false);
    if (res.success) {
      setViewMode('profile');
      onClose();
    } else {
      setError(res.error || 'Registration failed. Username or email may already be in use.');
    }
  };

  const handleUpgradeSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);
    const res = await upgradeGuest(email, username, password, fullName);
    setIsSubmitting(false);
    if (res.success) {
      setSuccessMsg('Account upgraded! Your Himalayan yatras and memories are permanently preserved.');
      setTimeout(() => {
        setSuccessMsg(null);
        setViewMode('profile');
      }, 2000);
    } else {
      setError(res.error || 'Failed to upgrade account. Please try a different username or email.');
    }
  };

  const handleGuestClick = async () => {
    setIsSubmitting(true);
    await loginAsGuest();
    setIsSubmitting(false);
    setViewMode('profile');
    onClose();
  };

  const handleLogoutClick = () => {
    logout();
    setViewMode('login');
    onClose();
  };

  const handleNavigateMemories = () => {
    onClose();
    navigate('/yatra-smriti');
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/45 backdrop-blur-md"
          />

          {/* Modal Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="relative w-full max-w-md bg-white/90 backdrop-blur-xl rounded-3xl border border-white/70 shadow-[0_20px_60px_rgba(42,36,33,0.18)] p-6 sm:p-8 z-10 overflow-hidden"
          >
            {/* Top Close Button */}
            <button
              onClick={onClose}
              className="absolute top-5 right-5 p-2 rounded-xl text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#FAF7F2] transition-colors cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header with Logo */}
            <div className="text-center mb-6">
              <div className="w-14 h-14 rounded-2xl bg-white border border-[#E0DAD0] shadow-xs p-1.5 mx-auto mb-3">
                <img src="/logo.png" alt="YatraSathi" className="w-full h-full object-contain rounded-xl" />
              </div>
              <h2 className="font-serif-yatra font-bold text-2xl text-[#1A1A1A]">
                {viewMode === 'profile'
                  ? 'Traveler Profile'
                  : viewMode === 'upgrade'
                  ? 'Upgrade Your Journey'
                  : viewMode === 'login'
                  ? 'Namaste, Welcome Back'
                  : 'Join YatraSathi Nepal'}
              </h2>
              <p className="text-xs text-[#6B6B6B] mt-1">
                {viewMode === 'profile'
                  ? 'Your authenticated Himalayan expedition records and community contributions.'
                  : viewMode === 'upgrade'
                  ? 'Upgrade from Guest Explorer to a permanent account while keeping all saved trips.'
                  : 'Save your Himalayan itineraries, upload travel photos, and share with fellow explorers.'}
              </p>
            </div>

            {/* Error or Success Alerts */}
            {error && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-xs text-red-700">
                {error}
              </div>
            )}
            {successMsg && (
              <div className="mb-4 p-3 rounded-xl bg-emerald-50 border border-emerald-200 text-xs text-emerald-800 flex items-center gap-1.5">
                <Check className="w-4 h-4 text-emerald-600 shrink-0" />
                <span>{successMsg}</span>
              </div>
            )}

            {/* ======================================================== */}
            {/* 1. AUTHENTICATED PROFILE VIEW                             */}
            {/* ======================================================== */}
            {viewMode === 'profile' && user && (
              <div className="space-y-5">
                {/* Profile Badge Card */}
                <div className="p-4 rounded-2xl bg-[#FAF7F2] border border-[#E0DAD0] flex items-center gap-3.5">
                  <div className="w-12 h-12 rounded-full bg-[#CC5200] text-white flex items-center justify-center font-bold text-base shadow-xs shrink-0">
                    {user.full_name?.slice(0, 2).toUpperCase() || user.username?.slice(0, 2).toUpperCase()}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="font-serif-yatra font-bold text-base text-[#1A1A1A] truncate">
                        {user.full_name || user.username}
                      </h3>
                      {user.is_guest ? (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 border border-amber-200 shrink-0">
                          Guest Explorer
                        </span>
                      ) : (
                        <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200 flex items-center gap-1 shrink-0">
                          <ShieldCheck className="w-3 h-3 text-emerald-600" />
                          Verified
                        </span>
                      )}
                    </div>
                    <p className="text-xs text-[#6B6B6B] truncate">@{user.username} • {user.email}</p>
                  </div>
                </div>

                {/* Live Stats Grid */}
                <div className="grid grid-cols-2 gap-3">
                  <div 
                    onClick={() => {
                      if (onOpenSavedTrips) onOpenSavedTrips();
                      else onClose();
                    }}
                    className="p-3.5 rounded-2xl bg-white border border-[#E0DAD0] hover:border-[#CC5200]/40 transition-all cursor-pointer group shadow-2xs"
                  >
                    <div className="flex items-center justify-between text-[#CC5200] mb-1">
                      <Bookmark className="w-4 h-4" />
                      <span className="text-[10px] uppercase font-bold text-[#6B6B6B] group-hover:text-[#CC5200] transition-colors">View Library &rarr;</span>
                    </div>
                    <div className="font-serif-yatra text-2xl font-bold text-[#1A1A1A]">
                      {user.trip_count || 0}
                    </div>
                    <div className="text-[11px] text-[#6B6B6B]">Saved Yatras</div>
                  </div>

                  <div 
                    onClick={handleNavigateMemories}
                    className="p-3.5 rounded-2xl bg-white border border-[#E0DAD0] hover:border-[#1D705C]/40 transition-all cursor-pointer group shadow-2xs"
                  >
                    <div className="flex items-center justify-between text-[#1D705C] mb-1">
                      <Camera className="w-4 h-4" />
                      <span className="text-[10px] uppercase font-bold text-[#6B6B6B] group-hover:text-[#1D705C] transition-colors">Scrapbook &rarr;</span>
                    </div>
                    <div className="font-serif-yatra text-2xl font-bold text-[#1A1A1A]">
                      {user.memory_count || 0}
                    </div>
                    <div className="text-[11px] text-[#6B6B6B]">Field Memories</div>
                  </div>
                </div>

                {/* If guest: Upgrade callout banner */}
                {user.is_guest && (
                  <div className="p-3.5 rounded-2xl bg-amber-50/80 border border-amber-200/80 text-xs text-amber-900 flex flex-col gap-2">
                    <div className="flex items-center gap-1.5 font-bold text-amber-950">
                      <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                      <span>Guest Session Active</span>
                    </div>
                    <p className="text-[11px] text-amber-800 leading-relaxed">
                      Upgrade to a permanent verified account to secure your saved routes and memories across devices.
                    </p>
                    <button
                      onClick={() => {
                        setError(null);
                        setViewMode('upgrade');
                      }}
                      className="inline-flex items-center justify-center gap-1.5 bg-[#CC5200] hover:bg-[#B34700] text-white py-2 rounded-xl text-xs font-bold transition-all cursor-pointer shadow-xs"
                    >
                      <KeyRound className="w-3.5 h-3.5" />
                      <span>Upgrade to Permanent Account</span>
                    </button>
                  </div>
                )}

                {/* Action links */}
                <div className="pt-2 border-t border-[#E0DAD0] flex items-center justify-between">
                  <button
                    onClick={() => {
                      setError(null);
                      setViewMode('login');
                    }}
                    className="text-xs font-semibold text-[#6B6B6B] hover:text-[#1A1A1A] transition-colors cursor-pointer"
                  >
                    Switch Account
                  </button>

                  <button
                    onClick={handleLogoutClick}
                    className="inline-flex items-center gap-1 text-xs font-bold text-red-600 hover:text-red-700 transition-colors cursor-pointer"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    <span>Log Out</span>
                  </button>
                </div>
              </div>
            )}

            {/* ======================================================== */}
            {/* 2. UPGRADE GUEST ACCOUNT VIEW                             */}
            {/* ======================================================== */}
            {viewMode === 'upgrade' && (
              <form onSubmit={handleUpgradeSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <User className="w-3.5 h-3.5 text-[#1D705C]" />
                    Full Name
                  </label>
                  <input
                    type="text"
                    value={fullName}
                    onChange={(e) => setFullName(e.target.value)}
                    placeholder="e.g. Maya Gurung"
                    className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Mail className="w-3.5 h-3.5 text-[#CC5200]" />
                    Permanent Email Address
                  </label>
                  <input
                    type="email"
                    required
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="traveler@yatra.org"
                    className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <ShieldCheck className="w-3.5 h-3.5 text-[#1D705C]" />
                    Permanent Username
                  </label>
                  <input
                    type="text"
                    required
                    value={username}
                    onChange={(e) => setUsername(e.target.value)}
                    placeholder="Choose your handle"
                    className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-[#CC5200]" />
                    Choose Password
                  </label>
                  <input
                    type="password"
                    required
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                  />
                </div>

                <div className="flex gap-2 pt-2">
                  <button
                    type="button"
                    onClick={() => {
                      setError(null);
                      setViewMode('profile');
                    }}
                    className="flex-1 py-2.5 rounded-xl bg-[#FAF7F2] hover:bg-[#EAE4D9] text-[#1A1A1A] font-semibold text-xs border border-[#E0DAD0] transition-all cursor-pointer"
                  >
                    Cancel
                  </button>

                  <button
                    type="submit"
                    disabled={isSubmitting}
                    className="flex-2 py-2.5 rounded-xl bg-[#CC5200] hover:bg-[#B34700] text-white font-bold text-xs shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer disabled:opacity-50"
                  >
                    {isSubmitting ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <KeyRound className="w-3.5 h-3.5" />}
                    <span>Save &amp; Upgrade</span>
                  </button>
                </div>
              </form>
            )}

            {/* ======================================================== */}
            {/* 3. SIGN IN / CREATE ACCOUNT TABS                          */}
            {/* ======================================================== */}
            {(viewMode === 'login' || viewMode === 'register') && (
              <>
                {/* Tab Switcher */}
                <div className="flex bg-[#FAF7F2] p-1 rounded-2xl border border-[#E0DAD0] mb-5">
                  <button
                    onClick={() => { setViewMode('login'); setError(null); }}
                    className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      viewMode === 'login' ? 'bg-[#CC5200] text-white shadow-xs' : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
                    }`}
                  >
                    Sign In
                  </button>
                  <button
                    onClick={() => { setViewMode('register'); setError(null); }}
                    className={`flex-1 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                      viewMode === 'register' ? 'bg-[#CC5200] text-white shadow-xs' : 'text-[#6B6B6B] hover:text-[#1A1A1A]'
                    }`}
                  >
                    Create Account
                  </button>
                </div>

                {/* Login Form */}
                {viewMode === 'login' ? (
                  <form onSubmit={handleLoginSubmit} className="space-y-4">
                    <div>
                      <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-[#1D705C]" />
                        Username or Email
                      </label>
                      <input
                        type="text"
                        required
                        value={usernameOrEmail}
                        onChange={(e) => setUsernameOrEmail(e.target.value)}
                        placeholder="Enter your username or email"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-[#CC5200]" />
                        Password
                      </label>
                      <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        minLength={8}
                        maxLength={72}
                        placeholder="••••••••"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-3 rounded-xl bg-[#CC5200] hover:bg-[#B34700] text-white font-bold text-sm shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer mt-2 disabled:opacity-50"
                    >
                      {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                      <span>Sign In</span>
                    </button>
                  </form>
                ) : (
                  /* Register Form */
                  <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
                    <div>
                      <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <User className="w-3.5 h-3.5 text-[#1D705C]" />
                        Full Name
                      </label>
                      <input
                        type="text"
                        value={fullName}
                        onChange={(e) => setFullName(e.target.value)}
                        placeholder="e.g. Maya Gurung"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <Mail className="w-3.5 h-3.5 text-[#CC5200]" />
                        Email Address
                      </label>
                      <input
                        type="email"
                        required
                        value={email}
                        onChange={(e) => setEmail(e.target.value)}
                        placeholder="explorer@himalaya.org"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <ShieldCheck className="w-3.5 h-3.5 text-[#1D705C]" />
                        Username
                      </label>
                      <input
                        type="text"
                        required
                        value={username}
                        onChange={(e) => setUsername(e.target.value)}
                        placeholder="Choose a username"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                      />
                    </div>

                    <div>
                      <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1.5 flex items-center gap-1.5">
                        <Lock className="w-3.5 h-3.5 text-[#CC5200]" />
                        Password
                      </label>
                      <input
                        type="password"
                        required
                        value={password}
                        onChange={(e) => setPassword(e.target.value)}
                        minLength={8}
                        maxLength={72}
                        placeholder="Create a password"
                        className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200]"
                      />
                    </div>

                    <button
                      type="submit"
                      disabled={isSubmitting}
                      className="w-full py-3 rounded-xl bg-[#CC5200] hover:bg-[#B34700] text-white font-bold text-sm shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer mt-2 disabled:opacity-50"
                    >
                      {isSubmitting ? <RefreshCw className="w-4 h-4 animate-spin" /> : <ArrowRight className="w-4 h-4" />}
                      <span>Create Account</span>
                    </button>
                  </form>
                )}

                {/* Divider */}
                <div className="relative my-5 text-center">
                  <div className="absolute inset-0 flex items-center">
                    <div className="w-full border-t border-[#E0DAD0]" />
                  </div>
                  <span className="relative bg-white px-3 text-[11px] font-bold text-[#6B6B6B] uppercase tracking-wider">
                    Instant Explorer
                  </span>
                </div>

                {/* 1-Click Guest Button */}
                <button
                  type="button"
                  onClick={handleGuestClick}
                  disabled={isSubmitting}
                  className="w-full py-2.5 rounded-xl bg-[#FAF7F2] hover:bg-[#EAE4D9] text-[#1A1A1A] font-semibold text-xs border border-[#E0DAD0] transition-all flex items-center justify-center gap-2 cursor-pointer"
                >
                  <Sparkles className="w-4 h-4 text-amber-500" />
                  <span>Continue as Instant Guest Explorer</span>
                </button>

                {/* Back to Profile if logged in */}
                {user && (
                  <div className="mt-3 text-center">
                    <button
                      onClick={() => setViewMode('profile')}
                      className="text-xs text-[#CC5200] hover:underline font-semibold cursor-pointer"
                    >
                      &larr; Back to my Traveler Profile
                    </button>
                  </div>
                )}
              </>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
