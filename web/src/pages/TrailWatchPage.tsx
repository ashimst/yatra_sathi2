import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  Camera, 
  Satellite, 
  Users, 
  Check, 
  Send,
  X,
  Award,
  RefreshCw,
  AlertCircle
} from 'lucide-react';
import { apiUrl } from '../api/config';
import { useAuth } from '../context/AuthContext';

interface TrailReportItem {
  id: string;
  hazard_type: string;
  urgency: string;
  description: string;
  location_name: string;
  altitude: number;
  image_url?: string;
  status: string;
  assigned_guild: string;
  created_at: string;
}

export const TrailWatchPage: React.FC = () => {
  const { user, token } = useAuth();
  const [selectedHazard, setSelectedHazard] = useState('Waste & Plastic Accumulation');
  const [urgency, setUrgency] = useState<'Low' | 'Moderate' | 'Urgent'>('Moderate');
  const [locationSector, setLocationSector] = useState('Annapurna Circuit & Sanctuary');
  const [description, setDescription] = useState('');
  const [evidenceFile, setEvidenceFile] = useState<File | null>(null);
  const [evidencePreview, setEvidencePreview] = useState<string | null>(null);
  const [isDraggingEvidence, setIsDraggingEvidence] = useState(false);
  const [evidenceError, setEvidenceError] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const sectorCoords: Record<string, { lat: number; lng: number; alt: number }> = {
    'Annapurna Circuit & Sanctuary': { lat: 28.539, lng: 83.652, alt: 2810 },
    'Khumbu & Everest High Trail': { lat: 27.805, lng: 86.714, alt: 3440 },
    'Langtang Valley & Gosainkunda': { lat: 28.082, lng: 85.342, alt: 3120 },
    'Kathmandu Valley Rim Trails': { lat: 27.717, lng: 85.324, alt: 1400 },
    'Pokhara Lakeshore & Ridge': { lat: 28.216, lng: 83.950, alt: 822 },
    'Trisuli Gorge Sector': { lat: 27.988, lng: 86.825, alt: 2400 },
  };
  
  // Real database reports & stats
  const [reports, setReports] = useState<TrailReportItem[]>([]);
  // Counts come from /trail-watch/stats; null until loaded (no placeholder numbers).
  const [stats, setStats] = useState<{
    active_trail_reports: number | null;
    cleanups_completed: number | null;
    registered_stewards: number | null;
    total_reports: number | null;
    resolution_rate: number | null;
  }>({
    active_trail_reports: null,
    cleanups_completed: null,
    registered_stewards: null,
    total_reports: null,
    resolution_rate: null,
  });
  const fmt = (v: number | null) => (v === null || v === undefined ? '—' : v.toLocaleString());

  // Steward Signup Modal
  const [isStewardModalOpen, setIsStewardModalOpen] = useState(false);
  const [stewardName, setStewardName] = useState('');
  const [stewardEmail, setStewardEmail] = useState('');
  const [isSubmittingSteward, setIsSubmittingSteward] = useState(false);
  const [stewardCredential, setStewardCredential] = useState<string | null>(
    localStorage.getItem('yatra_steward_credential') || null
  );

  const hazardCategories = [
    { id: 'Waste & Plastic Accumulation', label: 'Waste & Plastic Accumulation' },
    { id: 'Trail Obstruction / Landslide', label: 'Trail Obstruction / Landslide' },
    { id: 'Suspension Bridge / Cable Wear', label: 'Suspension Bridge / Cable Wear' },
    { id: 'Wildlife Corridor Sighting', label: 'Wildlife Corridor Sighting' },
    { id: 'Heritage Shrine & Mani Wall Damage', label: 'Heritage Shrine & Mani Wall Damage' },
  ];

  // Fetch real reports and stats
  const fetchReports = async () => {
    try {
      const res = await fetch(apiUrl('/trail-watch/reports'));
      if (res.ok) {
        const data = await res.json();
        setReports(data.reports || []);
      }
      const sRes = await fetch(apiUrl('/trail-watch/stats'));
      if (sRes.ok) {
        const sData = await sRes.json();
        setStats(sData);
      }
    } catch (err) {
      console.warn('Error fetching trail watch reports:', err);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];
  const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];

  const validateAndSetEvidence = (file: File) => {
    setEvidenceError(null);
    if (file.size > MAX_FILE_SIZE) {
      setEvidenceError(`Image exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB). Please choose a smaller file.`);
      return false;
    }
    const ext = `.${file.name.split('.').pop()?.toLowerCase()}`;
    const isValidMime = ALLOWED_MIME_TYPES.includes(file.type);
    const isValidExt = ALLOWED_EXTENSIONS.includes(ext);

    if (!isValidMime && !isValidExt) {
      setEvidenceError('Invalid image format. Allowed formats: JPEG, PNG, WebP, BMP.');
      return false;
    }

    setEvidenceFile(file);
    setEvidencePreview(URL.createObjectURL(file));
    return true;
  };

  const uploadEvidenceBinary = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', apiUrl('/uploads/photo?category=trail_reports'));
      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }
      xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) {
          setUploadProgress(Math.round((e.loaded / e.total) * 100));
        }
      };
      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            if (data.url) resolve(data.url);
            else reject(new Error('Server did not return a valid photo URL.'));
          } catch {
            reject(new Error('Failed to parse server upload response.'));
          }
        } else {
          try {
            const err = JSON.parse(xhr.responseText);
            reject(new Error(err.detail || `Upload failed with HTTP ${xhr.status}`));
          } catch {
            reject(new Error(`Upload failed with HTTP ${xhr.status}`));
          }
        }
      };
      xhr.onerror = () => reject(new Error('Network error during image upload.'));
      const fd = new FormData();
      fd.append('file', file);
      fd.append('category', 'trail_reports');
      xhr.send(fd);
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!description.trim() || isSubmitting) return;

    setIsSubmitting(true);
    setEvidenceError(null);
    setUploadProgress(0);

    try {
      let finalImageUrl: string | undefined = undefined;

      // Upload field evidence binary to /uploads/photo?category=trail_reports
      if (evidenceFile) {
        finalImageUrl = await uploadEvidenceBinary(evidenceFile);
      }

      const coords = sectorCoords[locationSector] || { lat: 28.539, lng: 83.652, alt: 2810 };
      const res = await fetch(apiUrl('/trail-watch/reports'), {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          hazard_type: selectedHazard,
          urgency,
          description: description.trim(),
          location_name: locationSector,
          latitude: coords.lat,
          longitude: coords.lng,
          altitude: coords.alt,
          image_url: finalImageUrl
        })
      });

      if (res.ok) {
        const data = await res.json();
        if (data.report) {
          setReports(prev => [data.report, ...prev]);
        }
        setDescription('');
        setEvidenceFile(null);
        setEvidencePreview(null);
        setUploadProgress(0);
        setToastMsg('Thanks! Your report is now visible to other travelers on the Trail Watch board.');
        setTimeout(() => setToastMsg(null), 4000);
      } else {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to register report (HTTP ${res.status})`);
      }
    } catch (err: any) {
      setToastMsg(err.message || 'Could not submit your report. Please try again.');
      setTimeout(() => setToastMsg(null), 3500);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleRegisterSteward = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!stewardName.trim() || !stewardEmail.trim() || isSubmittingSteward) return;

    setIsSubmittingSteward(true);
    try {
      const res = await fetch(apiUrl('/trail-watch/stewards'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name: stewardName,
          email: stewardEmail,
          preferred_region: "Annapurna & Khumbu Sanctuary"
        })
      });

      if (res.ok) {
        const data = await res.json();
        const cred = `#YS-${data.steward_id.slice(0, 8).toUpperCase()}`;
        setStewardCredential(cred);
        localStorage.setItem('yatra_steward_credential', cred);
        setIsStewardModalOpen(false);
        setToastMsg(`Welcome! You're registered as a community steward (member ${cred}).`);
        setTimeout(() => setToastMsg(null), 5000);
      }
    } catch (err) {
      setToastMsg('Failed to register steward. Please verify connection.');
      setTimeout(() => setToastMsg(null), 3000);
    } finally {
      setIsSubmittingSteward(false);
    }
  };

  return (
    <div className="w-full min-h-screen bg-[#FFF8F6] text-[#201A18] antialiased pb-24">
      {/* Toast Alert */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-[#201A18] text-white rounded-xl shadow-xl flex items-center gap-2 text-xs font-semibold animate-in fade-in duration-200">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Steward Registration Modal */}
      {isStewardModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 border border-[#E8DDD3] shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={() => setIsStewardModalOpen(false)}
              className="absolute top-4 right-4 text-[#8A726A] hover:text-[#201A18] cursor-pointer"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 text-[#1D705C] mb-2 font-bold text-xs uppercase tracking-wider">
              <Award className="w-4 h-4" />
              <span>YatraSathi Community Stewards</span>
            </div>

            <h3 className="font-serif-yatra text-2xl font-bold text-[#201A18]">
              Sign Up as Volunteer Steward
            </h3>
            <p className="text-xs text-[#56423B] mt-1 leading-relaxed">
              Join travelers who help keep trails clean and report hazards. We'll email you occasional updates about community clean-up efforts. YatraSathi is an independent platform and is not affiliated with any government or conservation body.
            </p>

            <form onSubmit={handleRegisterSteward} className="mt-5 space-y-3">
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">Full Legal Name</label>
                <input
                  type="text"
                  required
                  value={stewardName}
                  onChange={(e) => setStewardName(e.target.value)}
                  placeholder="e.g. Tenzing Norbu"
                  className="w-full px-3 py-2 text-xs bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl focus:ring-2 focus:ring-[#9D3E19] outline-none"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">Email Address</label>
                <input
                  type="email"
                  required
                  value={stewardEmail}
                  onChange={(e) => setStewardEmail(e.target.value)}
                  placeholder="e.g. steward@himalayas.org"
                  className="w-full px-3 py-2 text-xs bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl focus:ring-2 focus:ring-[#9D3E19] outline-none"
                />
              </div>

              <div className="p-3 bg-[#FDF1EC] rounded-xl text-[11px] text-[#56423B] space-y-1">
                <div className="font-bold text-[#1D705C]">As a community steward you can:</div>
                <div>✓ Carry out what you carry in, and pick up litter you pass</div>
                <div>✓ Report trail hazards so other travelers are warned</div>
                <div>✓ Show your YatraSathi steward badge on your profile</div>
              </div>

              <button
                type="submit"
                disabled={isSubmittingSteward}
                className="w-full py-2.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50 mt-2"
              >
                {isSubmittingSteward ? 'Registering...' : 'Join as Community Steward'}
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Top Banner Header */}
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-8 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-[#E8DDD3]">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#1D705C] text-[11px] font-bold uppercase tracking-wider mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#1D705C]" />
              Community Trail Board
            </div>
            <h1 className="font-serif-yatra text-3xl sm:text-5xl font-bold text-[#201A18] tracking-tight">
              Trail Watch &amp; <span className="italic text-[#9D3E19]">Ecological Stewardship</span>
            </h1>
            <p className="text-xs sm:text-sm text-[#56423B] mt-2 max-w-2xl leading-relaxed">
              Traveler-reported trail conditions and hazards, shared so others can plan safely. Reports are not sent to any authority. In an emergency, call Nepal Police (100) or the Tourist Police (1144).
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            {stewardCredential && (
              <span className="px-3 py-1.5 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 text-xs font-bold flex items-center gap-1.5">
                <Award className="w-4 h-4 text-emerald-600" />
                <span>{stewardCredential}</span>
              </span>
            )}
            <button
              onClick={() => {
                document.getElementById('report-panel')?.scrollIntoView({ behavior: 'smooth' });
              }}
              className="inline-flex items-center gap-1.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white px-4 py-2.5 rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
            >
              <ShieldAlert className="w-4 h-4" />
              <span>Log Field Report</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Trail Status Metrics */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Trail Watch</div>
            <div className="font-serif-yatra text-3xl font-bold text-[#201A18]">{fmt(stats.active_trail_reports)}</div>
            <div className="text-[11px] text-[#56423B] mt-1">Open Trail Reports</div>
          </div>
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Alpine Restoration</div>
            <div className="font-serif-yatra text-3xl font-bold text-[#1D705C]">{fmt(stats.cleanups_completed)}</div>
            <div className="text-[11px] text-[#56423B] mt-1">Reports Resolved</div>
          </div>
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Community Stewards</div>
            <div className="font-serif-yatra text-3xl font-bold text-[#201A18]">{fmt(stats.registered_stewards)}</div>
            <div className="text-[11px] text-[#56423B] mt-1">Registered Volunteers</div>
          </div>
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Resolution Rate</div>
            <div className="font-serif-yatra text-3xl font-bold text-[#9D3E19]">
              {stats.resolution_rate === null || stats.resolution_rate === undefined ? '—' : `${Math.round(stats.resolution_rate * 100)}%`}
            </div>
            <div className="text-[11px] text-[#56423B] mt-1">Of {fmt(stats.total_reports)} reports filed</div>
          </div>
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* FIELD REPORT INTAKE & LIVE DISPATCH                           */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section id="report-panel" className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* Left Form: Log a Hazard */}
          <div className="lg:col-span-7 bg-white/85 backdrop-blur-xl rounded-2xl p-6 sm:p-8 border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] space-y-6">
            <div className="flex items-center justify-between border-b border-[#E8DDD3] pb-4">
              <div>
                <span className="text-[10px] text-[#9D3E19] uppercase font-bold tracking-wider">Community Field Report</span>
                <h2 className="font-serif-yatra text-xl sm:text-2xl font-bold text-[#201A18] mt-0.5">
                  Log a Trail Hazard or Impact
                </h2>
              </div>
              <div className="flex items-center gap-1.5 text-xs font-semibold text-[#1D705C] bg-[#FDF1EC] px-3 py-1 rounded-full">
                <span className="w-2 h-2 rounded-full bg-[#1D705C] animate-pulse" />
                <span>GPS Live</span>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-5">
              {/* Photo Evidence Box */}
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-2">Field Photographic Evidence</label>
                {evidenceError && (
                  <div className="mb-2 p-2.5 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <AlertCircle className="w-4 h-4 text-red-600 shrink-0" />
                      <span>{evidenceError}</span>
                    </div>
                    <button
                      type="button"
                      onClick={() => setEvidenceError(null)}
                      className="text-red-500 hover:text-red-800 cursor-pointer"
                    >
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                )}

                {evidencePreview ? (
                  <div className="relative rounded-2xl overflow-hidden border border-[#E8DDD3] aspect-video bg-[#FDF1EC]">
                    <img
                      src={evidencePreview}
                      alt="Field Evidence"
                      className="w-full h-full object-cover"
                    />
                    {!isSubmitting && (
                      <button
                        type="button"
                        onClick={() => {
                          setEvidenceFile(null);
                          setEvidencePreview(null);
                        }}
                        className="absolute top-3 right-3 p-1.5 rounded-full bg-black/60 text-white hover:bg-black transition-colors cursor-pointer"
                        title="Remove photo"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    )}
                    <div className="absolute bottom-2 left-2 px-2.5 py-1 rounded-md bg-black/60 text-white font-mono text-[10px] flex items-center gap-1.5">
                      <Satellite className="w-3 h-3 text-[#9D3E19]" />
                      <span>Photo attached</span>
                    </div>
                  </div>
                ) : (
                  <label
                    onDragOver={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsDraggingEvidence(true);
                    }}
                    onDragEnter={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsDraggingEvidence(true);
                    }}
                    onDragLeave={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsDraggingEvidence(false);
                    }}
                    onDrop={(e) => {
                      e.preventDefault();
                      e.stopPropagation();
                      setIsDraggingEvidence(false);
                      const file = e.dataTransfer.files?.[0];
                      if (file) validateAndSetEvidence(file);
                    }}
                    className={`border-2 border-dashed rounded-2xl p-6 text-center transition-colors cursor-pointer block group ${
                      isDraggingEvidence
                        ? 'border-[#9D3E19] bg-[#FFF3EB]'
                        : 'border-[#E8DDD3] bg-[#FFF8F6] hover:border-[#9D3E19]'
                    }`}
                  >
                    <div className="w-12 h-12 rounded-full bg-[#FDF1EC] text-[#9D3E19] flex items-center justify-center mx-auto mb-2 group-hover:scale-105 transition-transform">
                      <Camera className="w-5 h-5" />
                    </div>
                    <div className="text-xs font-bold text-[#201A18]">
                      {isDraggingEvidence ? 'Drop incident photo here' : 'Drop incident photo or capture from device'}
                    </div>
                    <div className="text-[10px] text-[#8A726A] mt-1">
                      JPEG, PNG, WebP, BMP • Max 10MB
                    </div>
                    <div className="mt-3 inline-flex items-center gap-1 text-[10px] font-mono text-[#56423B] bg-white px-2.5 py-1 rounded-md border border-[#E8DDD3]">
                      <Satellite className="w-3 h-3 text-[#9D3E19]" />
                      <span>Altitude: {sectorCoords[locationSector]?.alt || 2810}m • 27°59'17" N 86°49'32" E</span>
                    </div>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp,image/bmp"
                      onChange={(e) => {
                        const file = e.target.files?.[0];
                        if (file) validateAndSetEvidence(file);
                      }}
                      className="hidden"
                    />
                  </label>
                )}

                {isSubmitting && evidenceFile && (
                  <div className="mt-2 space-y-1 p-2.5 rounded-lg bg-[#FDF1EC] border border-[#E8DDD3]">
                    <div className="flex items-center justify-between text-[11px] text-[#56423B]">
                      <span>Uploading incident photo to field ledger...</span>
                      <span className="font-bold text-[#9D3E19]">{uploadProgress}%</span>
                    </div>
                    <div className="w-full h-1.5 bg-[#E8DDD3] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#9D3E19] transition-all duration-200"
                        style={{ width: `${Math.max(uploadProgress, 5)}%` }}
                      />
                    </div>
                  </div>
                )}
              </div>

              {/* Hazard Category */}
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-2">Select Hazard Domain</label>
                <div className="flex flex-wrap gap-2">
                  {hazardCategories.map(cat => (
                    <button
                      type="button"
                      key={cat.id}
                      onClick={() => setSelectedHazard(cat.id)}
                      className={`px-3 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                        selectedHazard === cat.id
                          ? 'bg-[#9D3E19] text-white shadow-xs'
                          : 'bg-[#FDF1EC] text-[#56423B] border border-[#E8DDD3] hover:bg-[#F8EBE6]'
                      }`}
                    >
                      {cat.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* Urgency */}
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-2">Field Urgency Calibration</label>
                <div className="grid grid-cols-3 gap-2">
                  {(['Low', 'Moderate', 'Urgent'] as const).map(level => (
                    <button
                      type="button"
                      key={level}
                      onClick={() => setUrgency(level)}
                      className={`p-2.5 rounded-xl text-center text-xs font-bold border transition-all cursor-pointer ${
                        urgency === level
                          ? level === 'Urgent'
                            ? 'bg-red-700 text-white border-red-800'
                            : level === 'Moderate'
                            ? 'bg-[#9D3E19] text-white border-[#9D3E19]'
                            : 'bg-[#1D705C] text-white border-[#1D705C]'
                          : 'bg-[#FDF1EC] text-[#56423B] border-[#E8DDD3] hover:bg-[#F8EBE6]'
                      }`}
                    >
                      <div>{level}</div>
                      <div className="text-[9px] font-normal opacity-85 mt-0.5">
                        {level === 'Urgent' ? 'Immediate pass block' : level === 'Moderate' ? '4-12hr attention' : 'Routine audit'}
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {/* Corridor Sector */}
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">Corridor Sector &amp; Trail Region</label>
                <select
                  value={locationSector}
                  onChange={(e) => setLocationSector(e.target.value)}
                  className="w-full p-2.5 text-xs bg-[#FFF8F6] border border-[#E8DDD3] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9D3E19] text-[#201A18] font-semibold cursor-pointer"
                >
                  {Object.keys(sectorCoords).map(sector => (
                    <option key={sector} value={sector}>{sector}</option>
                  ))}
                </select>
              </div>

              {/* Description */}
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">Field Observations &amp; Mile Marker Context</label>
                <textarea
                  required
                  rows={3}
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="e.g. Discarded polypropylene packaging and empty beverage cans spotted 250m past the rhododendron grove, near Trisuli suspension stanchion..."
                  className="w-full p-3 text-xs bg-[#FFF8F6] border border-[#E8DDD3] rounded-xl focus:outline-none focus:ring-2 focus:ring-[#9D3E19] text-[#201A18]"
                />
              </div>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isSubmitting}
                className="w-full py-3 bg-[#9D3E19] hover:bg-[#BD552F] text-white font-bold text-xs rounded-xl shadow-xs flex items-center justify-center gap-2 transition-all cursor-pointer disabled:opacity-50"
              >
                <Send className="w-3.5 h-3.5" />
                <span>{isSubmitting ? 'Posting report...' : 'Post Report to Trail Board'}</span>
              </button>
            </form>
          </div>

          {/* Right Column: Live Radar & Rapid Community Response Loop */}
          <div className="lg:col-span-5 space-y-6">
            {/* Live Geographic Trail Radar */}
            <div className="p-6 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-[#E8DDD3] pb-3">
                <div>
                  <span className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider">Live Alpine Trail Radar</span>
                  <div className="font-serif-yatra text-base font-bold text-[#201A18]">Trisuli Gorge Sector</div>
                </div>
                <span className="text-[10px] font-bold text-[#1D705C] bg-[#FDF1EC] px-2 py-0.5 rounded-full">
                  Active Sweep
                </span>
              </div>

              {/* Simulated Map View of incidents */}
              <div className="h-56 rounded-xl bg-[#F8EBE6] border border-[#E8DDD3] p-4 relative overflow-hidden flex flex-col justify-between">
                <div className="space-y-2 z-10">
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white/90 rounded-full text-[10px] font-bold text-red-700 shadow-2xs">
                    <span className="w-2 h-2 rounded-full bg-red-600 animate-pulse" />
                    <span>Pass Boulder Slide (#TR-402)</span>
                  </div>
                  <div className="inline-flex items-center gap-1.5 px-2.5 py-1 bg-white/90 rounded-full text-[10px] font-bold text-amber-700 shadow-2xs block">
                    <span className="w-2 h-2 rounded-full bg-amber-500" />
                    <span>Plastic Waste Alert (#TR-403)</span>
                  </div>
                </div>

                <div className="flex justify-between items-end z-10 text-[10px] text-[#8A726A] font-mono bg-white/80 p-2 rounded-lg backdrop-blur-sm">
                  <span>Community-reported locations</span>
                  <span className="text-[#9D3E19] font-bold">Trisuli Gorge Waypoint</span>
                </div>
              </div>
            </div>

            {/* How Trail Watch works + emergency contacts */}
            <div className="p-6 bg-[#FDF1EC]/90 backdrop-blur-md rounded-2xl border border-[#E8DDD3] shadow-xs space-y-4">
              <div>
                <span className="text-[10px] text-[#9D3E19] uppercase font-bold tracking-wider">How It Works</span>
                <h3 className="font-serif-yatra text-base font-bold text-[#201A18] mt-0.5">
                  A Community Board, Not an Emergency Service
                </h3>
                <p className="text-xs text-[#56423B] mt-1 leading-relaxed">
                  Reports you post appear on this page for other travelers. YatraSathi does not forward them to
                  authorities, lodges or rescue services, and is not affiliated with any government or conservation body.
                </p>
              </div>

              <div className="grid grid-cols-2 gap-3 text-center">
                <div className="p-3 bg-white rounded-xl border border-[#E8DDD3]">
                  <div className="text-lg font-serif-yatra font-bold text-[#9D3E19]">100</div>
                  <div className="text-[10px] text-[#8A726A] font-semibold">Nepal Police</div>
                </div>
                <div className="p-3 bg-white rounded-xl border border-[#E8DDD3]">
                  <div className="text-lg font-serif-yatra font-bold text-[#D97706]">1144</div>
                  <div className="text-[10px] text-[#8A726A] font-semibold">Tourist Police</div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* RECENT FIELD AUDITS & RESOLVED INCIDENTS                      */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-10">
        <div className="flex items-center justify-between mb-6">
          <div>
            <span className="text-[11px] text-[#9D3E19] uppercase tracking-wider font-bold">Civic Verification Log</span>
            <h2 className="font-serif-yatra text-2xl sm:text-3xl font-bold text-[#201A18] mt-1">
              Recent Field Audits &amp; Resolved Incidents
            </h2>
          </div>
          <button
            onClick={fetchReports}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-white border border-[#E8DDD3] rounded-xl text-xs font-bold text-[#56423B] hover:text-[#9D3E19] transition-colors cursor-pointer shadow-2xs"
          >
            <RefreshCw className="w-3.5 h-3.5" />
            <span>Sync Live Feed</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {reports.map((item) => (
            <div key={item.id} className="bg-white/85 backdrop-blur-xl rounded-2xl overflow-hidden border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] flex flex-col">
              <div className="relative h-48 bg-[#F8EBE6]">
                <img
                  src={item.image_url || "https://images.unsplash.com/photo-1544735716-392fe2489ffa?w=800&auto=format&fit=crop&q=80"}
                  alt={item.hazard_type}
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
                <div className={`absolute top-3 left-3 px-2.5 py-1 rounded-full text-[10px] font-bold ${
                  item.status?.includes('Resolved')
                    ? 'bg-emerald-700 text-white'
                    : 'bg-amber-600 text-white'
                }`}>
                  {item.status || 'Open'}
                </div>
                <div className="absolute bottom-3 right-3 px-2 py-0.5 rounded bg-black/60 text-white text-[10px]">
                  {item.altitude || 2800}m Elev
                </div>
              </div>
              <div className="p-5 flex-1 flex flex-col justify-between">
                <div>
                  <div className="text-[10px] text-[#8A726A] uppercase font-bold">{item.location_name}</div>
                  <h3 className="font-serif-yatra text-base font-bold text-[#201A18] mt-1">
                    {item.hazard_type}
                  </h3>
                  <p className="text-xs text-[#56423B] mt-2 leading-relaxed">
                    {item.description}
                  </p>
                </div>
                <div className="mt-4 pt-3 border-t border-[#E8DDD3] text-[11px] text-[#1D705C] font-semibold">
                  Category: {item.assigned_guild || 'General Trail Condition'}
                </div>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* VOLUNTEER FELLOWSHIP CALL TO ACTION                           */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-6">
        <div className="p-8 rounded-3xl bg-gradient-to-br from-[#FDF1EC] to-[#F8EBE6] border border-[#E8DDD3] flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
          <div>
            <span className="text-[10px] text-[#9D3E19] uppercase font-bold tracking-wider">Community Stewards</span>
            <h3 className="font-serif-yatra text-2xl font-bold text-[#201A18] mt-1">
              Leave the Trail Better Than You Found It
            </h3>
            <p className="text-xs sm:text-sm text-[#56423B] mt-2 max-w-xl leading-relaxed">
              Sign up as a YatraSathi community steward: pack out your waste, pick up litter along the way, and report hazards so fellow travelers stay safe.
            </p>
            <div className="flex flex-wrap gap-4 mt-4 text-xs font-semibold text-[#1D705C]">
              <span>✓ Pack it in, pack it out</span>
              <span>✓ Report hazards for others</span>
              <span>✓ Community steward badge</span>
            </div>
          </div>

          <button
            onClick={() => {
              if (user) {
                if (user.full_name) setStewardName(user.full_name);
                if (user.email && !user.email.includes('@yatrasathi.local')) setStewardEmail(user.email);
              }
              setIsStewardModalOpen(true);
            }}
            className="bg-[#9D3E19] hover:bg-[#BD552F] text-white px-6 py-3 rounded-xl font-bold text-xs shadow-xs transition-colors shrink-0 cursor-pointer flex items-center gap-2"
          >
            <Users className="w-4 h-4" />
            <span>{stewardCredential ? 'View Steward Badge' : 'Sign Up as Community Steward'}</span>
          </button>
        </div>
      </section>
    </div>
  );
};
