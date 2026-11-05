import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Upload, Sparkles, Camera, MapPin, Check, AlertCircle } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { apiUrl } from '../api/config';

interface PhotoUploadModalProps {
  isOpen: boolean;
  onClose: () => void;
  defaultPlaceName?: string;
  defaultLatitude?: number;
  defaultLongitude?: number;
  itineraryId?: string;
  onMemoryCreated?: (memory: any) => void;
}

const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp', 'image/bmp'];
const ALLOWED_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.webp', '.bmp'];

export const PhotoUploadModal: React.FC<PhotoUploadModalProps> = ({
  isOpen,
  onClose,
  defaultPlaceName = '',
  defaultLatitude,
  defaultLongitude,
  itineraryId,
  onMemoryCreated,
}) => {
  const { token, refreshProfile } = useAuth();

  const [placeName, setPlaceName] = useState(defaultPlaceName);
  const [caption, setCaption] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [imagePreview, setImagePreview] = useState<string | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [uploadStage, setUploadStage] = useState<'idle' | 'uploading' | 'processing'>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [createdReflection, setCreatedReflection] = useState<string | null>(null);

  // When props change
  React.useEffect(() => {
    if (defaultPlaceName) {
      setPlaceName(defaultPlaceName);
    }
  }, [defaultPlaceName]);

  const validateAndSetFile = (file: File) => {
    setErrorMessage(null);

    // Validate size limit (10MB)
    if (file.size > MAX_FILE_SIZE) {
      setErrorMessage(`File exceeds 10MB limit (${(file.size / (1024 * 1024)).toFixed(1)}MB). Please choose a smaller image.`);
      return false;
    }

    // Validate MIME type and file extension
    const extension = `.${file.name.split('.').pop()?.toLowerCase()}`;
    const isValidMime = ALLOWED_MIME_TYPES.includes(file.type);
    const isValidExt = ALLOWED_EXTENSIONS.includes(extension);

    if (!isValidMime && !isValidExt) {
      setErrorMessage('Invalid file type. Allowed formats: JPEG, PNG, WebP, and BMP.');
      return false;
    }

    setSelectedFile(file);
    const objectUrl = URL.createObjectURL(file);
    setImagePreview(objectUrl);
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

  const resetForm = () => {
    setImagePreview(null);
    setSelectedFile(null);
    setCaption('');
    setErrorMessage(null);
    setUploadProgress(0);
    setUploadStage('idle');
    setCreatedReflection(null);
  };

  const handleModalClose = () => {
    if (isUploading) return;
    resetForm();
    onClose();
  };

  const uploadPhotoBinary = (file: File): Promise<string> => {
    return new Promise((resolve, reject) => {
      const xhr = new XMLHttpRequest();
      xhr.open('POST', apiUrl('/uploads/photo'));

      if (token) {
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
      }

      xhr.upload.onprogress = (event) => {
        if (event.lengthComputable) {
          const percent = Math.round((event.loaded / event.total) * 100);
          setUploadProgress(percent);
        }
      };

      xhr.onload = () => {
        if (xhr.status >= 200 && xhr.status < 300) {
          try {
            const data = JSON.parse(xhr.responseText);
            if (data.url) {
              resolve(data.url);
            } else {
              reject(new Error('Server did not return a valid photo URL.'));
            }
          } catch {
            reject(new Error('Failed to parse server upload response.'));
          }
        } else {
          try {
            const errData = JSON.parse(xhr.responseText);
            reject(new Error(errData.detail || `Upload failed with HTTP ${xhr.status}`));
          } catch {
            reject(new Error(`Upload failed with HTTP ${xhr.status}: ${xhr.statusText}`));
          }
        }
      };

      xhr.onerror = () => reject(new Error('Network connection error during image upload.'));

      const formData = new FormData();
      formData.append('file', file);
      formData.append('category', 'memories');
      xhr.send(formData);
    });
  };

  const handleUploadSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if ((!imagePreview && !selectedFile) || !placeName.trim() || isUploading) return;

    setIsUploading(true);
    setErrorMessage(null);
    setCreatedReflection(null);
    setUploadProgress(0);
    setUploadStage('uploading');

    try {
      let finalImageUrl = imagePreview || '';

      // Upload binary file using multipart FormData to /uploads/photo
      if (selectedFile) {
        finalImageUrl = await uploadPhotoBinary(selectedFile);
      }

      setUploadStage('processing');

      // Create memory record linking uploaded photo URL
      const res = await fetch(apiUrl('/memories'), {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          place_name: placeName.trim(),
          caption: caption.trim(),
          image_url: finalImageUrl,
          latitude: defaultLatitude,
          longitude: defaultLongitude,
          itinerary_id: itineraryId,
        }),
      });

      if (!res.ok) {
        const errorData = await res.json().catch(() => null);
        throw new Error(errorData?.detail || `Failed to create memory record (HTTP ${res.status})`);
      }

      const data = await res.json();
      setCreatedReflection(data.memory.ai_reflection);
      refreshProfile();
      if (onMemoryCreated) {
        onMemoryCreated(data.memory);
      }

      setTimeout(() => {
        resetForm();
        onClose();
      }, 2200);
    } catch (err: any) {
      console.error('Upload error:', err);
      setErrorMessage(err.message || 'An unexpected error occurred during upload. Please try again.');
    } finally {
      setIsUploading(false);
      setUploadStage('idle');
    }
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
            onClick={handleModalClose}
            className="fixed inset-0 bg-black/45 backdrop-blur-md z-50"
          />

          {/* Modal Card */}
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.95, y: 10 }}
            className="relative w-full max-w-lg bg-white/90 backdrop-blur-xl rounded-3xl border border-white/70 shadow-[0_20px_60px_rgba(42,36,33,0.18)] p-6 sm:p-8 z-10 overflow-hidden"
          >
            {/* Close Button */}
            <button
              onClick={handleModalClose}
              disabled={isUploading}
              className="absolute top-5 right-5 p-2 rounded-xl text-[#6B6B6B] hover:text-[#1A1A1A] hover:bg-[#FAF7F2] transition-colors cursor-pointer disabled:opacity-40"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Header */}
            <div className="text-center mb-6">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#1D705C] px-3 py-1 rounded-full bg-[#1D705C]/10 border border-[#1D705C]/20">
                Yatra Smriti • Travel Journal
              </span>
              <h2 className="font-serif-yatra font-bold text-2xl text-[#1A1A1A] mt-2">
                Capture a Himalayan Memory
              </h2>
              <p className="text-xs text-[#6B6B6B] mt-1">
                Upload a photo from your travels. Our AI companion will craft a cultural reflection for your journal.
              </p>
            </div>

            {/* Error Message Banner */}
            {errorMessage && (
              <div className="mb-4 p-3 rounded-xl bg-red-50 border border-red-200 text-red-800 text-xs flex items-start gap-2.5 animate-in fade-in">
                <AlertCircle className="w-4 h-4 text-red-600 shrink-0 mt-0.5" />
                <div className="flex-1">
                  <span className="font-semibold block">Upload Failed</span>
                  <span>{errorMessage}</span>
                </div>
                <button
                  type="button"
                  onClick={() => setErrorMessage(null)}
                  className="text-red-500 hover:text-red-800 cursor-pointer"
                >
                  <X className="w-3.5 h-3.5" />
                </button>
              </div>
            )}

            {createdReflection ? (
              <div className="text-center py-8 space-y-4 animate-in fade-in zoom-in-95">
                <div className="w-12 h-12 rounded-full bg-emerald-100 text-emerald-600 flex items-center justify-center mx-auto">
                  <Check className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="font-serif-yatra font-bold text-lg text-[#1A1A1A]">Memory Preserved!</h3>
                  <p className="text-xs text-[#CC5200] italic mt-2 font-serif-yatra max-w-sm mx-auto">
                    "{createdReflection}"
                  </p>
                </div>
              </div>
            ) : (
              <form onSubmit={handleUploadSubmit} className="space-y-4">
                {/* Photo Dropzone / Preview */}
                <div>
                  {imagePreview ? (
                    <div className="relative rounded-2xl overflow-hidden border-2 border-[#CC5200]/40 group aspect-video bg-black/5">
                      <img
                        src={imagePreview}
                        alt="Preview"
                        className="w-full h-full object-cover"
                      />
                      {!isUploading && (
                        <button
                          type="button"
                          onClick={() => {
                            setImagePreview(null);
                            setSelectedFile(null);
                          }}
                          className="absolute top-3 right-3 p-1.5 rounded-full bg-black/60 text-white hover:bg-black transition-colors cursor-pointer"
                          title="Remove photo"
                        >
                          <X className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  ) : (
                    <label
                      onDragOver={handleDragOver}
                      onDragEnter={handleDragEnter}
                      onDragLeave={handleDragLeave}
                      onDrop={handleDrop}
                      className={`border-2 border-dashed rounded-2xl p-6 flex flex-col items-center justify-center text-center cursor-pointer transition-all duration-200 ${
                        isDragging
                          ? 'border-[#CC5200] bg-[#FFF3EB] scale-[1.01] shadow-inner'
                          : 'border-[#E0DAD0] hover:border-[#CC5200] bg-[#FAF7F2]'
                      }`}
                    >
                      <div className={`w-12 h-12 rounded-2xl border flex items-center justify-center text-[#CC5200] mb-2 shadow-2xs transition-colors ${
                        isDragging ? 'bg-[#FFE2D1] border-[#CC5200]' : 'bg-white border-[#E0DAD0]'
                      }`}>
                        <Camera className="w-6 h-6" />
                      </div>
                      <span className="text-xs font-bold text-[#1A1A1A]">
                        {isDragging ? 'Drop photo to upload' : 'Upload a photo of this place'}
                      </span>
                      <span className="text-[11px] text-[#6B6B6B] mt-0.5">
                        Click or drag image (JPEG, PNG, WebP, BMP • Max 10MB)
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

                {/* Upload Progress Bar */}
                {isUploading && (
                  <div className="space-y-1.5 p-3 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] animate-in fade-in">
                    <div className="flex items-center justify-between text-xs text-[#6B6B6B]">
                      <span className="font-medium text-[#1A1A1A]">
                        {uploadStage === 'uploading' ? 'Uploading image...' : 'Writing AI Reflection & Saving...'}
                      </span>
                      <span className="font-bold text-[#CC5200]">
                        {uploadStage === 'uploading' ? `${uploadProgress}%` : 'Almost done'}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-[#E0DAD0] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-gradient-to-r from-[#CC5200] to-[#E67E22] transition-all duration-300 rounded-full"
                        style={{
                          width: uploadStage === 'uploading' ? `${Math.max(uploadProgress, 5)}%` : '100%',
                        }}
                      />
                    </div>
                  </div>
                )}

                {/* Place Name */}
                <div>
                  <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <MapPin className="w-3.5 h-3.5 text-[#1D705C]" />
                    Place Name
                  </label>
                  <input
                    type="text"
                    required
                    disabled={isUploading}
                    value={placeName}
                    onChange={(e) => setPlaceName(e.target.value)}
                    placeholder="e.g. Swayambhunath Stupa or Phewa Lake"
                    className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200] disabled:opacity-60"
                  />
                </div>

                {/* Caption / Journal Note */}
                <div>
                  <label className="block text-xs font-bold text-[#1A1A1A] uppercase tracking-wider mb-1 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-[#CC5200]" />
                    Journal Note &amp; Thoughts
                  </label>
                  <textarea
                    rows={2}
                    disabled={isUploading}
                    value={caption}
                    onChange={(e) => setCaption(e.target.value)}
                    placeholder="What did you feel here? The butter lamps, fresh mountain breeze, sound of prayer bells..."
                    className="w-full px-4 py-2.5 rounded-xl bg-[#FAF7F2] border border-[#E0DAD0] text-sm text-[#1A1A1A] focus:outline-hidden focus:ring-2 focus:ring-[#CC5200]/20 focus:border-[#CC5200] leading-relaxed disabled:opacity-60"
                  />
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={!imagePreview || isUploading}
                  className="w-full py-3.5 rounded-xl bg-[#CC5200] hover:bg-[#B34700] disabled:opacity-50 text-white font-bold text-sm shadow-xs transition-all flex items-center justify-center gap-2 cursor-pointer mt-2"
                >
                  {isUploading ? (
                    <>
                      <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                      <span>{uploadStage === 'uploading' ? `Uploading (${uploadProgress}%)...` : 'Writing AI Reflection & Saving...'}</span>
                    </>
                  ) : (
                    <>
                      <Upload className="w-4 h-4" />
                      <span>Pin to My Travel Scrapbook</span>
                    </>
                  )}
                </button>
              </form>
            )}
          </motion.div>
        </div>
      )}
    </AnimatePresence>
  );
};
