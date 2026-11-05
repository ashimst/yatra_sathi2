import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { Footer } from './components/Footer';
import { AIChatDrawer } from './components/AIChatDrawer';
import { AuthModal } from './components/AuthModal';
import { SavedTripsDrawer } from './components/SavedTripsDrawer';
import { HomePage } from './pages/HomePage';
import { PlanPage } from './pages/PlanPage';
import { ExplorePage } from './pages/ExplorePage';
import { MapPage } from './pages/MapPage';
import { ArchitecturePage } from './pages/ArchitecturePage';
import { SharePage } from './pages/SharePage';
import { MemoriesPage } from './pages/MemoriesPage';
import { TrailWatchPage } from './pages/TrailWatchPage';
import { CulturalSanctuaryPage } from './pages/CulturalSanctuaryPage';
import { NotFoundPage } from './pages/NotFoundPage';
import { ErrorBoundary } from './components/ErrorBoundary';

export function AppContent() {
  const [isAIChatOpen, setIsAIChatOpen] = useState(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(false);
  const [isSavedTripsOpen, setIsSavedTripsOpen] = useState(false);

  return (
    <div className="min-h-screen flex flex-col bg-[#F5F0E8] text-[#1A1A1A] font-sans selection:bg-[#CC5200] selection:text-white">
      {/* Navigation Header */}
      <Navbar
        onOpenAIChat={() => setIsAIChatOpen(true)}
        onOpenSavedTrips={() => setIsSavedTripsOpen(true)}
        onOpenAuth={() => setIsAuthModalOpen(true)}
      />

      {/* Routes */}
      <main className="flex-1">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/plan" element={<PlanPage />} />
          <Route path="/explore" element={<ExplorePage />} />
          <Route path="/trail-watch" element={<TrailWatchPage />} />
          <Route path="/memories" element={<MemoriesPage />} />
          <Route path="/yatra-smriti" element={<MemoriesPage />} />
          <Route path="/smriti" element={<MemoriesPage />} />
          <Route path="/cultural-sanctuary" element={<CulturalSanctuaryPage />} />
          <Route path="/map" element={<MapPage />} />
          <Route path="/architecture" element={<ArchitecturePage />} />
          <Route path="/info" element={<ArchitecturePage />} />
          <Route path="/share/:shareId" element={<SharePage />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>

      {/* Global Application Footer */}
      <Footer />

      {/* AI Assistant Drawer */}
      <AIChatDrawer
        isOpen={isAIChatOpen}
        onClose={() => setIsAIChatOpen(false)}
      />

      {/* Auth Modal (Sign In / Register / Guest Explorer / Profile) */}
      <AuthModal
        isOpen={isAuthModalOpen}
        onClose={() => setIsAuthModalOpen(false)}
        onOpenSavedTrips={() => {
          setIsAuthModalOpen(false);
          setIsSavedTripsOpen(true);
        }}
      />

      {/* Saved Yatras Drawer */}
      <SavedTripsDrawer
        isOpen={isSavedTripsOpen}
        onClose={() => setIsSavedTripsOpen(false)}
      />
    </div>
  );
}

export function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <AuthProvider>
          <AppContent />
        </AuthProvider>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
