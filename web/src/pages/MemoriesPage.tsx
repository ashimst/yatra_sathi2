import React, { useState, useEffect, useRef } from 'react';
import { 
  Sparkles, 
  Download, 
  Sun, 
  Check,
  Plus,
  X,
  Camera,
  MapPin,
  RefreshCw,
  Trash2,
  AlertCircle,
  Upload
} from 'lucide-react';
import { apiUrl } from '../api/config';
import { useAuth } from '../context/AuthContext';

interface SeasonData {
  id: string;
  name: string;
  cycle: string;
  title: string;
  desc: string;
  clarity: string;
  sun: string;
  transmittance: string;
  congestion: string;
  wisdom: string;
  imgUrl: string;
}

interface MemoryItem {
  id: string;
  place_name: string;
  image_url: string;
  caption?: string;
  ai_reflection?: string;
  created_at?: string;
}

export const MemoriesPage: React.FC = () => {
  const { token, refreshProfile } = useAuth();
  const [activeSeason, setActiveSeason] = useState<'autumn' | 'winter' | 'spring' | 'summer'>('autumn');
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  
  // Real database memories
  const [dbMemories, setDbMemories] = useState<MemoryItem[]>([]);
  const [isLoadingMemories, setIsLoadingMemories] = useState(false);

  // Add Memory Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newPlace, setNewPlace] = useState('');
  const [newCaption, setNewCaption] = useState('');
  const [newImageUrl, setNewImageUrl] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [filePreview, setFilePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [modalError, setModalError] = useState<string | null>(null);
  const [isSavingMemory, setIsSavingMemory] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const canvasRef = useRef<HTMLCanvasElement | null>(null);

  const seasons: Record<string, SeasonData> = {
    autumn: {
      id: 'autumn',
      name: 'Autumn Post-Monsoon',
      cycle: 'October — Mid November Cycle',
      title: 'Phewa Lake & Sarangkot Ridge',
      desc: 'Post-monsoon crystalline air cleanses the Pokhara valley. Machapuchhre stands with zero cloud crown, reflected on the still sacred waters of Phewa Tal before dusk brings smoke from clay hearths.',
      clarity: '98% Clarity Horizon',
      sun: 'Dawn 05:48 AM • Dusk 17:34 PM',
      transmittance: '0.94 / 1.00',
      congestion: 'Moderate (Trekker Inflow)',
      wisdom: 'When the autumn barley turns to copper, the peaks answer the bells of the caravan.',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAWbp_1aW_l-9Aug9CAH_R2YXjv2eYRoTUu9twH5V-ExmHM6r0ondR9bWzPMclSvvAdEoKr_I3-jyRQwSElubCW87moFmJAyUrZ4tp9OeX4sxfvSqSdUbgc2Z4yMBj84_1dVYQ_4ShsxRpNLaa0Cej3EuBrAkngfpBWQu9asg8H01Lm3eo3mXSgutUHTLYA8jRHmt6n6ZeI6O27YTCkwzLtmQYIKKzXYe3GbaaXoQUyZB2dBX6sLWjSiA'
    },
    winter: {
      id: 'winter',
      name: 'Winter Solstice',
      cycle: 'December — January Cycle',
      title: 'Trans-Himalayan Cold Front & Mustang High Deserts',
      desc: 'Deep crisp indigo skies with biting -14°C night air. Mountain passes are sealed by snow cornices, while sacred fires burn in Thakali teahouses below.',
      clarity: '99% Deep Optical Range',
      sun: 'Dawn 06:45 AM • Dusk 17:15 PM',
      transmittance: '0.98 / 1.00',
      congestion: 'Low (Solitary Pilgrimage)',
      wisdom: 'The snow holds no footprints but the snow leopard’s and the monk’s morning silence.',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuArp9yq2FNeMp2qwSPa301VTyRz9HQjOBqxO05zIWrCozT3UAfV8FebUsz8eA5sh62zvZd1ph4NzhUts_9S-ZdR-gwK8MweC_AK_uiiB2uv3HkQvT-bL0pZQwCLGxz03f0IwdlHAe5F6BAcDQvbVbTGvg55GrU1GcsVEF_QorlamjYVAk7xdFnD001xKsOo0KuvoIn_W5kjuiiWgp5bwgU6R_Z0dAz_jG7UbWZwOqtokXchtAwaAEvh0Q'
    },
    spring: {
      id: 'spring',
      name: 'Rhododendron Bloom',
      cycle: 'March — April Cycle',
      title: 'Ghorepani Scarlet Forests & Annapurna South',
      desc: 'Entire mountain slopes erupt into vibrant crimson and pink lali gurans blossoms. Thawing streams rush with milky glacial meltwater under warming skies.',
      clarity: '88% Mild Thermal Haze',
      sun: 'Dawn 06:05 AM • Dusk 18:20 PM',
      transmittance: '0.86 / 1.00',
      congestion: 'High (Spring Expedition Peak)',
      wisdom: 'When the rhododendron crowns the ridge, the snows begin their prayer down to the sea.',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCZ3j1Tkys7oJtjFyFvuCvojJOoMe8LaRIrTCwxON76tUp9JZ9nhIYJGD5CzoKXY9-48RfWXH3dTEZU0bDkzksz1LeOt2R2sq_0qsBnGDA1uoV4co0ukIheqJzHDLv_lGwoIYMpjdVUDXRrQ-DN_e9MgQtrfuXmVyNYi1cjJhlXhN1wvcfQm2pMWHlpS5ur1gY1BiQyv7UrwYqTUVbwsS9gmOgKbze_H5sdniNJqTTtI-LSfjPDg-lxEw'
    },
    summer: {
      id: 'summer',
      name: 'Summer Monsoon',
      cycle: 'July — August Cycle',
      title: 'Emerald Terraces & Sacred High Glacial Lakes',
      desc: 'Heavy clouds weave through pine valleys. Waterfalls burst from sheer limestone cliffs, turning Nepal into an emerald sanctuary of fertility and rain blessings.',
      clarity: '65% Mist & Cloud Envelopes',
      sun: 'Dawn 05:20 AM • Dusk 19:05 PM',
      transmittance: '0.62 / 1.00',
      congestion: 'Minimal (Rain Shadows Open)',
      wisdom: 'The rain washes the dust from the prayer flags so the words can reach heaven unhindered.',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDAoGxqWL_G9pCW7p-GFHIjFMBNTG0l7WpEBSHMFYLkQ_zGT9EpAHingbjlwXuwkiz13HNVefAAfXAiysXuCzgMqM3xLdOlYz09W1598R3d6TyFpLRcgKWzoguG7Flkls9fzO0YeVcpIvLKnD1dlB2VWLtM8wDvBRQJgVkUsSMio5MCi8_ogPirIj81dEq2sRl4nYcIccE05WEuRYhbXSkX3KHX7lfOvTunxH5X-KtqvajDgAh9JVvISQ'
    }
  };

  const currentSeason = seasons[activeSeason];

  // Fetch real memories from backend
  const fetchMemories = async () => {
    setIsLoadingMemories(true);
    try {
      const res = await fetch(apiUrl('/memories'));
      if (res.ok) {
        const data = await res.json();
        setDbMemories(data.memories || []);
      }
    } catch (err) {
      console.warn('Error fetching memories:', err);
    } finally {
      setIsLoadingMemories(false);
    }
  };

  useEffect(() => {
    fetchMemories();
  }, []);

  // Real Canvas-based Postcard Download
  const handleDownloadPostcard = () => {
    const canvas = document.createElement('canvas');
    canvas.width = 1080;
    canvas.height = 1350;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Background Warm Linen Paper
    ctx.fillStyle = '#FFF8F6';
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    // Border
    ctx.lineWidth = 14;
    ctx.strokeStyle = '#E8DDD3';
    ctx.strokeRect(40, 40, canvas.width - 80, canvas.height - 80);

    // Inner Header
    ctx.fillStyle = '#9D3E19';
    ctx.font = 'bold 32px serif';
    ctx.fillText('नेपाल हुलाक • POSTCARD', 70, 110);

    ctx.fillStyle = '#201A18';
    ctx.font = 'bold 24px sans-serif';
    ctx.textAlign = 'right';
    ctx.fillText('YATRASATHI ARCHIVE', canvas.width - 70, 110);
    ctx.textAlign = 'left';

    // Simulated Postage Stamp
    ctx.fillStyle = '#FDF1EC';
    ctx.strokeStyle = '#9D3E19';
    ctx.lineWidth = 4;
    ctx.fillRect(canvas.width - 240, 150, 170, 200);
    ctx.strokeRect(canvas.width - 240, 150, 170, 200);

    ctx.fillStyle = '#9D3E19';
    ctx.font = 'bold 18px sans-serif';
    ctx.fillText('NEPAL 50', canvas.width - 210, 255);

    // Load and render photo onto canvas
    const img = new Image();
    img.crossOrigin = 'anonymous';
    img.onload = () => {
      ctx.drawImage(img, 70, 160, canvas.width - 340, 680);

      // Coordinates Overlay
      ctx.fillStyle = 'rgba(0,0,0,0.65)';
      ctx.fillRect(90, 780, 420, 44);
      ctx.fillStyle = '#FFFFFF';
      ctx.font = '18px monospace';
      ctx.fillText('28°14\'26"N • 83°57\'36"E • Sentinel-2', 110, 808);

      // Title & Lore
      ctx.fillStyle = '#201A18';
      ctx.font = 'bold 44px serif';
      ctx.fillText(currentSeason.title, 70, 930);

      ctx.fillStyle = '#9D3E19';
      ctx.font = 'bold 26px sans-serif';
      ctx.fillText(currentSeason.cycle.toUpperCase(), 70, 980);

      ctx.fillStyle = '#56423B';
      ctx.font = 'italic 28px serif';
      ctx.fillText(`"${currentSeason.wisdom}"`, 70, 1070);

      // Footer
      ctx.fillStyle = '#8A726A';
      ctx.font = '20px sans-serif';
      ctx.fillText('Verified Spatial Chronicle • YatraSathi Intelligent Himalayan Companion', 70, 1260);

      // Trigger file download
      const link = document.createElement('a');
      link.download = `yatra_postcard_${activeSeason}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();

      setToastMsg('Heirloom Postcard rendered and downloaded successfully!');
      setTimeout(() => setToastMsg(null), 4000);
    };

    img.onerror = () => {
      // Fallback text card download if image blocked by CORS
      ctx.fillStyle = '#201A18';
      ctx.font = 'bold 48px serif';
      ctx.fillText(currentSeason.title, 70, 500);
      ctx.fillStyle = '#56423B';
      ctx.font = 'italic 28px serif';
      ctx.fillText(`"${currentSeason.wisdom}"`, 70, 600);

      const link = document.createElement('a');
      link.download = `yatra_postcard_${activeSeason}.png`;
      link.href = canvas.toDataURL('image/png');
      link.click();
      setToastMsg('Postcard generated and downloaded!');
      setTimeout(() => setToastMsg(null), 4000);
    };

    img.src = currentSeason.imgUrl;
  };

  const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
  const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];
  const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];

  const validateAndSetFile = (file: File) => {
    setModalError(null);
    if (file.size > MAX_FILE_SIZE) {
      setModalError(`File size exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB). Please choose a smaller image.`);
      return false;
    }

    const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
    const isValidMime = ALLOWED_MIME_TYPES.includes(file.type);
    const isValidExt = ALLOWED_EXTENSIONS.includes(extension);

    if (!isValidMime && !isValidExt) {
      setModalError('Invalid image format. Allowed formats: JPEG, PNG, WebP, BMP.');
      return false;
    }

    setSelectedFile(file);
    setFilePreview(URL.createObjectURL(file));
    return true;
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      validateAndSetFile(file);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) {
      validateAndSetFile(file);
    }
  };

  const uploadPhotoBinary = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', apiUrl('/uploads/photo'));
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
      fd.append('category', 'memories');
      xhr.send(fd);
    });
  };

  const resetModalState = () => {
    setIsAddModalOpen(false);
    setNewPlace('');
    setNewCaption('');
    setNewImageUrl('');
    setSelectedFile(null);
    setFilePreview(null);
    setModalError(null);
    setUploadProgress(0);
    setIsDragging(false);
  };

  // Add Memory to Database
  const handleCreateMemory = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newPlace.trim() || isSavingMemory) return;

    setIsSavingMemory(true);
    setModalError(null);
    setUploadProgress(0);

    try {
      let finalImageUrl = newImageUrl.trim() || currentSeason.imgUrl;

      // If user selected or dropped a file, upload binary to /uploads/photo first
      if (selectedFile) {
        finalImageUrl = await uploadPhotoBinary(selectedFile);
      }

      const res = await fetch(apiUrl('/memories'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        },
        body: JSON.stringify({
          place_name: newPlace.trim(),
          caption: newCaption.trim() || 'Exploring sacred valleys of Nepal',
          image_url: finalImageUrl,
          latitude: 28.2167,
          longitude: 83.95
        })
      });

      if (res.ok) {
        const data = await res.json();
        setDbMemories(prev => [data.memory, ...prev]);
        resetModalState();
        await refreshProfile();
        setToastMsg(`Memory created with AI reflection: "${data.memory.ai_reflection}"`);
        setTimeout(() => setToastMsg(null), 5000);
      } else {
        const errData = await res.json().catch(() => null);
        throw new Error(errData?.detail || `Failed to create memory (HTTP ${res.status})`);
      }
    } catch (err: any) {
      setModalError(err.message || 'Failed to save memory to server. Please try again.');
    } finally {
      setIsSavingMemory(false);
    }
  };

  // Delete Memory from Database
  const handleDeleteMemory = async (id: string) => {
    if (!window.confirm('Are you sure you want to delete this memory from your scrapbook?')) return;
    setDeletingId(id);
    try {
      const res = await fetch(apiUrl(`/memories/${id}`), {
        method: 'DELETE',
        headers: {
          ...(token ? { Authorization: `Bearer ${token}` } : {})
        }
      });
      if (res.ok) {
        setDbMemories(prev => prev.filter(m => m.id !== id));
        setToastMsg('Memory successfully removed.');
        setTimeout(() => setToastMsg(null), 3000);
        await refreshProfile();
      } else {
        const errData = await res.json().catch(() => null);
        setToastMsg(errData?.detail || 'Failed to delete memory.');
        setTimeout(() => setToastMsg(null), 3000);
      }
    } catch (err) {
      console.error('Delete error:', err);
      setToastMsg('Network connection error while deleting memory.');
      setTimeout(() => setToastMsg(null), 3000);
    } finally {
      setDeletingId(null);
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

      {/* Hidden Canvas for High-Resolution Postcard Rendering */}
      <canvas ref={canvasRef} className="hidden" />

      {/* Add Memory Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl max-w-md w-full p-6 border border-[#E8DDD3] shadow-2xl relative animate-in fade-in zoom-in-95 duration-200">
            <button
              onClick={resetModalState}
              disabled={isSavingMemory}
              className="absolute top-4 right-4 text-[#8A726A] hover:text-[#201A18] cursor-pointer disabled:opacity-40"
            >
              <X className="w-5 h-5" />
            </button>

            <div className="flex items-center gap-2 text-[#9D3E19] mb-1 font-bold text-xs uppercase tracking-wider">
              <Camera className="w-4 h-4" />
              <span>Expedition Journal Entry</span>
            </div>

            <h3 className="font-serif-yatra text-2xl font-bold text-[#201A18]">
              Log a Himalayan Memory
            </h3>
            <p className="text-xs text-[#56423B] mt-1 leading-relaxed">
              Record a landmark or trail reflection. Upload a photo or select an image to generate an evocative poetic cultural reflection.
            </p>

            {/* Error Banner */}
            {modalError && (
              <div className="mt-3 p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <span className="flex-1">{modalError}</span>
                <button
                  type="button"
                  onClick={() => setModalError(null)}
                  className="text-red-500 hover:text-red-800"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            <form onSubmit={handleCreateMemory} className="mt-4 space-y-3">
              {/* Image Dropzone & Preview */}
              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">
                  Memory Photo (Drop or Select)
                </label>
                {filePreview ? (
                  <div className="relative rounded-xl overflow-hidden border border-[#E8DDD3] aspect-video bg-[#FDF1EC]">
                    <img
                      src={filePreview}
                      alt="Preview"
                      className="w-full h-full object-cover"
                    />
                    {!isSavingMemory && (
                      <button
                        type="button"
                        onClick={() => {
                          setSelectedFile(null);
                          setFilePreview(null);
                        }}
                        className="absolute top-2 right-2 p-1 rounded-full bg-black/60 text-white hover:bg-black transition-colors cursor-pointer"
                        title="Remove photo"
                      >
                        <X className="w-3.5 h-3.5" />
                      </button>
                    )}
                  </div>
                ) : (
                  <label
                    onDragOver={handleDragOver}
                    onDragEnter={handleDragEnter}
                    onDragLeave={handleDragLeave}
                    onDrop={handleDrop}
                    className={`border-2 border-dashed rounded-xl p-4 flex flex-col items-center justify-center text-center cursor-pointer transition-colors ${
                      isDragging
                        ? 'border-[#9D3E19] bg-[#FFF3EB]'
                        : 'border-[#E8DDD3] hover:border-[#9D3E19] bg-[#FFF8F6]'
                    }`}
                  >
                    <div className="w-9 h-9 rounded-xl bg-white border border-[#E8DDD3] flex items-center justify-center text-[#9D3E19] mb-1.5 shadow-2xs">
                      <Upload className="w-4 h-4" />
                    </div>
                    <span className="text-xs font-bold text-[#201A18]">
                      {isDragging ? 'Drop photo here' : 'Drop photo or click to browse'}
                    </span>
                    <span className="text-[10px] text-[#8A726A] mt-0.5">
                      JPEG, PNG, WebP, BMP • Max 10MB
                    </span>
                    <input
                      type="file"
                      accept="image/jpeg,image/png,image/webp,image/bmp"
                      onChange={handleFileChange}
                      className="hidden"
                    />
                  </label>
                )}
              </div>

              {/* Upload Progress */}
              {isSavingMemory && selectedFile && (
                <div className="space-y-1 p-2.5 rounded-lg bg-[#FDF1EC] border border-[#E8DDD3]">
                  <div className="flex items-center justify-between text-[11px] text-[#56423B]">
                    <span>Uploading photo...</span>
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

              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">Place / Trail Location</label>
                <input
                  type="text"
                  required
                  disabled={isSavingMemory}
                  value={newPlace}
                  onChange={(e) => setNewPlace(e.target.value)}
                  placeholder="e.g. Sarangkot Sunrise Vantage or Phewa Lake"
                  className="w-full px-3 py-2 text-xs bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl focus:ring-2 focus:ring-[#9D3E19] outline-none disabled:opacity-60"
                />
              </div>

              <div>
                <label className="text-xs font-bold text-[#201A18] block mb-1">Traveler Personal Caption</label>
                <textarea
                  rows={2}
                  disabled={isSavingMemory}
                  value={newCaption}
                  onChange={(e) => setNewCaption(e.target.value)}
                  placeholder="e.g. Dawn mist rising over the Annapurna ridge while prayer bells rung in the distance..."
                  className="w-full px-3 py-2 text-xs bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl focus:ring-2 focus:ring-[#9D3E19] outline-none disabled:opacity-60"
                />
              </div>

              {!selectedFile && (
                <div>
                  <label className="text-xs font-bold text-[#201A18] block mb-1">Photo Image URL (Optional)</label>
                  <input
                    type="url"
                    disabled={isSavingMemory}
                    value={newImageUrl}
                    onChange={(e) => setNewImageUrl(e.target.value)}
                    placeholder="Paste image URL (defaults to seasonal high-res if empty)"
                    className="w-full px-3 py-2 text-xs bg-[#FDF1EC] border border-[#E8DDD3] rounded-xl focus:ring-2 focus:ring-[#9D3E19] outline-none disabled:opacity-60"
                  />
                </div>
              )}

              <button
                type="submit"
                disabled={isSavingMemory || (!newPlace.trim())}
                className="w-full py-2.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white font-bold text-xs rounded-xl shadow-xs transition-colors cursor-pointer disabled:opacity-50 mt-2 flex items-center justify-center gap-1.5"
              >
                {isSavingMemory ? <RefreshCw className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                <span>{isSavingMemory ? 'Uploading & Generating AI Reflection...' : 'Preserve Memory to Scrapbook'}</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Top Banner */}
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-8 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-[#E8DDD3]">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#9D3E19] text-[11px] font-bold uppercase tracking-wider mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#9D3E19]" />
              Himalayan Chronicles • Memory Archive Active
            </div>
            <h1 className="font-serif-yatra text-3xl sm:text-5xl font-bold text-[#201A18] tracking-tight">
              Yatra Smriti — <span className="italic text-[#9D3E19]">Living Himalayan Chronicles</span>
            </h1>
            <p className="text-xs sm:text-sm text-[#56423B] mt-2 max-w-2xl leading-relaxed">
              A tactile magazine-style scrapbook preserving field diaries, high-pass trail memories, and photographic reverence for your personal Himalayan journey.
            </p>
          </div>

          <div className="flex items-center gap-2.5">
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-1.5 bg-white border border-[#E8DDD3] text-[#201A18] hover:bg-[#FDF1EC] px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-2xs cursor-pointer"
            >
              <Plus className="w-3.5 h-3.5 text-[#9D3E19]" />
              <span>Log Field Memory</span>
            </button>
            <button
              onClick={handleDownloadPostcard}
              className="inline-flex items-center gap-1.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white px-4 py-2 rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
            >
              <Download className="w-3.5 h-3.5" />
              <span>Postcard Export (PNG)</span>
            </button>
          </div>
        </div>
      </div>

      {/* 4 Archival Metric Cards */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-6">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Logged Chronicles</div>
            <div className="font-serif-yatra text-2xl font-bold text-[#201A18]">{dbMemories.length + 4} Chapters</div>
            <div className="text-[11px] text-[#56423B] mt-1">Pokhara Basin to High Passes</div>
          </div>
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">GPS Distance</div>
            <div className="font-serif-yatra text-2xl font-bold text-[#201A18]">248.4 km</div>
            <div className="text-[11px] text-[#56423B] mt-1">Traversed via foot &amp; mule tracks</div>
          </div>
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Altimeter Net</div>
            <div className="font-serif-yatra text-2xl font-bold text-[#9D3E19]">+3,410 m</div>
            <div className="text-[11px] text-[#56423B] mt-1">Vertical Excursion Accumulation</div>
          </div>
          <div className="p-5 bg-white/85 backdrop-blur-xl rounded-2xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)]">
            <div className="text-[10px] text-[#8A726A] uppercase font-bold tracking-wider mb-2">Expedition Archive</div>
            <div className="font-serif-yatra text-2xl font-bold text-[#1D705C]">Preserved Safely</div>
            <div className="text-[11px] text-[#56423B] mt-1">Himalayan journal &amp; reflection archive</div>
          </div>
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* THE LIVING FOUR-SEASON METAMORPHOSIS (TIME-SLIDER)            */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-8">
        <div className="flex flex-col md:flex-row items-start md:items-end justify-between gap-4 mb-6">
          <div>
            <div className="inline-flex items-center gap-1.5 text-[#9D3E19] text-xs font-bold uppercase tracking-wider mb-1">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Seasonal Himalayan Rhythms</span>
            </div>
            <h2 className="font-serif-yatra text-2xl sm:text-3xl font-bold text-[#201A18]">
              The Living Four-Season Metamorphosis
            </h2>
            <p className="text-xs sm:text-sm text-[#56423B] mt-1">
              Scrub across cardinal Himalayan seasons to witness atmospheric shifts, mountain clarity, and seasonal mountain lore.
            </p>
          </div>

          {/* Season Scrub Tabs */}
          <div className="flex flex-wrap gap-1 p-1.5 rounded-full bg-[#F8EBE6] border border-[#E8DDD3]">
            {(['autumn', 'winter', 'spring', 'summer'] as const).map((key) => {
              const s = seasons[key];
              const isActive = activeSeason === key;
              return (
                <button
                  key={key}
                  onClick={() => setActiveSeason(key)}
                  className={`px-4 py-2 rounded-full text-xs font-bold transition-all cursor-pointer ${
                    isActive
                      ? 'bg-[#9D3E19] text-white shadow-xs'
                      : 'text-[#56423B] hover:text-[#201A18]'
                  }`}
                >
                  {s.name}
                </button>
              );
            })}
          </div>
        </div>

        {/* Main Stage Grid */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-stretch">
          {/* Panoramic Image Stage */}
          <div className="lg:col-span-8 relative rounded-2xl overflow-hidden shadow-md flex flex-col justify-between min-h-[440px] p-6 lg:p-8 bg-[#F8EBE6] border border-[#E8DDD3]">
            <img
              src={currentSeason.imgUrl}
              alt={currentSeason.title}
              className="absolute inset-0 w-full h-full object-cover transition-opacity duration-500"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-[#201A18]/85 via-[#201A18]/30 to-[#201A18]/10" />

            {/* Top Bar Overlay */}
            <div className="relative z-10 flex flex-wrap items-center justify-between gap-3 text-white">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-white/90 backdrop-blur-md text-[#201A18] text-xs font-semibold shadow-xs">
                <span className="w-2 h-2 rounded-full bg-[#D97706] animate-pulse" />
                <span className="font-bold text-[#9D3E19]">{currentSeason.clarity}</span>
                <span className="text-[#8A726A] hidden sm:inline">• Clear Mountain Visibility</span>
              </div>
              <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-white/90 backdrop-blur-md text-[#201A18] text-xs font-semibold shadow-xs">
                <Sun className="w-3.5 h-3.5 text-[#D97706]" />
                <span>{currentSeason.sun}</span>
              </div>
            </div>

            {/* Bottom Caption Overlay */}
            <div className="relative z-10 flex flex-col gap-2 pt-28 text-white">
              <span className="text-[11px] font-bold uppercase tracking-widest text-amber-300">
                {currentSeason.cycle}
              </span>
              <h3 className="font-serif-yatra text-2xl sm:text-3xl font-bold tracking-tight">
                {currentSeason.title}
              </h3>
              <p className="text-xs sm:text-sm text-gray-200 max-w-xl leading-relaxed">
                {currentSeason.desc}
              </p>
            </div>
          </div>

          {/* Right Sidebar Atmosphere & Lore */}
          <div className="lg:col-span-4 flex flex-col gap-4">
            <div className="p-6 rounded-2xl bg-white/85 backdrop-blur-xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] space-y-4">
              <div className="flex items-center justify-between border-b border-[#E8DDD3] pb-3">
                <span className="text-[11px] font-bold text-[#8A726A] uppercase tracking-wider">Seasonal Atmosphere &amp; Conditions</span>
                <span className="px-2.5 py-0.5 rounded-full bg-[#FDF1EC] text-[#9D3E19] text-[10px] font-bold">Prime Window</span>
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold text-[#201A18] mb-1">
                  <span>Atmospheric Air Clarity</span>
                  <span>{currentSeason.transmittance}</span>
                </div>
                <div className="w-full bg-[#F8EBE6] h-2 rounded-full overflow-hidden">
                  <div className="bg-[#9D3E19] h-full rounded-full w-[94%]" />
                </div>
              </div>

              <div>
                <div className="flex justify-between text-xs font-bold text-[#201A18] mb-1">
                  <span>Trail Congestion Pressure</span>
                  <span className="text-[#9D3E19]">{currentSeason.congestion}</span>
                </div>
                <div className="w-full bg-[#F8EBE6] h-2 rounded-full overflow-hidden">
                  <div className="bg-[#D97706] h-full rounded-full w-[65%]" />
                </div>
              </div>

              <div className="p-4 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3]">
                <div className="text-[10px] text-[#9D3E19] uppercase font-bold tracking-wider mb-1">Himalayan Pastoral Wisdom</div>
                <p className="font-serif-yatra text-xs italic text-[#56423B] leading-relaxed">
                  "{currentSeason.wisdom}"
                </p>
              </div>
            </div>

            {/* Postcard Quick Action */}
            <div className="p-5 rounded-2xl bg-white/85 backdrop-blur-xl border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] flex items-center justify-between">
              <div>
                <div className="font-bold text-xs text-[#201A18]">Save Active Season Postcard</div>
                <div className="text-[10px] text-[#8A726A]">High-res CMYK printable format</div>
              </div>
              <button
                onClick={handleDownloadPostcard}
                className="p-2.5 rounded-xl bg-[#9D3E19] hover:bg-[#BD552F] text-white shadow-xs transition-colors cursor-pointer"
              >
                <Download className="w-4 h-4" />
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* SAVED TRAVELER MEMORIES                                       */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-10">
        <div className="flex items-center justify-between mb-6">
          <div>
            <span className="text-[11px] text-[#9D3E19] uppercase tracking-wider font-bold">Field Memories Ledger</span>
            <h2 className="font-serif-yatra text-2xl sm:text-3xl font-bold text-[#201A18] mt-1">
              Traveler Scrapbook &amp; AI Cultural Reflections
            </h2>
          </div>
          <button
            onClick={() => setIsAddModalOpen(true)}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white rounded-xl text-xs font-bold transition-all shadow-xs cursor-pointer"
          >
            <Plus className="w-3.5 h-3.5" />
            <span>Add Memory</span>
          </button>
        </div>

        {dbMemories.length > 0 ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {dbMemories.map((mem) => (
              <div key={mem.id} className="bg-white/85 backdrop-blur-xl rounded-2xl overflow-hidden border border-white/70 shadow-[0_8px_30px_rgba(42,36,33,0.04)] flex flex-col">
                <div className="relative h-48 bg-[#F8EBE6]">
                  <img
                    src={mem.image_url}
                    alt={mem.place_name}
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
                  <div className="absolute bottom-2 left-2 px-2 py-0.5 rounded bg-black/60 text-white font-mono text-[9px] flex items-center gap-1">
                    <MapPin className="w-3 h-3 text-red-400" />
                    <span>{mem.place_name}</span>
                  </div>
                  <button
                    onClick={() => handleDeleteMemory(mem.id)}
                    disabled={deletingId === mem.id}
                    className="absolute top-2 right-2 p-1.5 rounded-lg bg-black/50 hover:bg-red-600 text-white backdrop-blur-md transition-colors cursor-pointer disabled:opacity-40"
                    title="Delete memory"
                  >
                    {deletingId === mem.id ? (
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                    ) : (
                      <Trash2 className="w-3.5 h-3.5" />
                    )}
                  </button>
                </div>
                <div className="p-4 flex-1 flex flex-col justify-between space-y-2">
                  <div>
                    <div className="font-serif-yatra font-bold text-sm text-[#201A18]">
                      {mem.place_name}
                    </div>
                    {mem.caption && (
                      <p className="text-xs text-[#56423B] mt-1 italic">
                        "{mem.caption}"
                      </p>
                    )}
                  </div>
                  {mem.ai_reflection && (
                    <div className="p-2.5 rounded-lg bg-[#FDF1EC] border border-[#E8DDD3] text-[10px] text-[#9D3E19] font-medium leading-relaxed">
                      <strong className="block text-[#201A18] text-[9px] uppercase">AI Cultural Reflection:</strong>
                      {mem.ai_reflection}
                    </div>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : isLoadingMemories ? (
          <div className="p-8 rounded-2xl bg-white/85 backdrop-blur-xl border border-white/70 text-center text-xs text-[#8A726A] flex items-center justify-center gap-2">
            <RefreshCw className="w-4 h-4 animate-spin text-[#9D3E19]" />
            <span>Loading traveler field memories...</span>
          </div>
        ) : (
          <div className="p-8 rounded-2xl bg-white/85 backdrop-blur-xl border border-white/70 text-center text-xs text-[#8A726A]">
            No personal field memories logged yet. Click "Log Field Memory" to record your first Himalayan journey reflection!
          </div>
        )}
      </section>
    </div>
  );
};
