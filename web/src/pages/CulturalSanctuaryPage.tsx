import React, { useState } from 'react';
import { 
  RotateCw, 
  EyeOff, 
  Shirt, 
  Check, 
  Compass, 
  Clock, 
  Download
} from 'lucide-react';

interface SanctuaryItem {
  id: string;
  name: string;
  region: 'kathmandu' | 'khumbu' | 'annapurna' | 'mustang';
  corridor: string;
  tag: string;
  desc: string;
  rules: string[];
  pujaTime: string;
  perimeter: string;
  imgUrl: string;
}

export const CulturalSanctuaryPage: React.FC = () => {
  const [activeRegion, setActiveRegion] = useState<string>('all');
  const [activeChortenTier, setActiveChortenTier] = useState<number>(0);
  const [pledgeChecked, setPledgeChecked] = useState<Record<number, boolean>>(() => {
    try {
      const saved = localStorage.getItem('yatra_sanctuary_pledge');
      return saved ? JSON.parse(saved) : { 0: true, 1: true, 2: true };
    } catch {
      return { 0: true, 1: true, 2: true };
    }
  });
  const [toastMsg, setToastMsg] = useState<string | null>(null);

  const handlePledgeToggle = (idx: number, val: boolean) => {
    const updated = { ...pledgeChecked, [idx]: val };
    setPledgeChecked(updated);
    try {
      localStorage.setItem('yatra_sanctuary_pledge', JSON.stringify(updated));
    } catch {}
  };

  const handleDownloadPocketCard = () => {
    const textContent = `=====================================================
YATRASATHI NEPAL • HIMALAYAN SACRED ETIQUETTE POCKET CARD
=====================================================

THE FOUR GOLDEN PILLARS OF KORA:
1. CLOCKWISE CIRCUMAMBULATION (Pradaksina)
   Always circumambulate stupas, chortens, and mani stone walls keeping
   them to your RIGHT side (kora). Never walk counter-clockwise unless in
   rare Bon tradition corridors.

2. BAREFOOT IN SANCTUMS (Paduka)
   Remove footwear, leather accessories, and head coverings before
   crossing sanctum thresholds. Never point soles of feet directly
   toward statues, monks, or shrines.

3. REVERENT SIGHT & NO FLASH (Dhyana)
   Strictly silence camera lenses in inner deity sanctums, lamp meditation
   recesses, and cremation ghats. Never photograph mourning families at
   Arya Ghat. Ask permission before capturing Sadhus or Lamas.

4. MODEST ATTIRE & SCARF RESPECT (Khata)
   Drape shoulders and knees in loose cottons. Receive sacred white silk
   Khata scarves with both outstretched palms, head bowed gently forward.

HIGH PASS CHORTEN PROTOCOL:
- Shout 3 times at the crest: "Ki Ki So So Lha Gyalo!" (Victory to benevolent spirits).
- Tie wind-horse prayer flag strings high from rock to cairn; never let them touch mud.
- Add a single small pebble to the mountain cairn with a bow of gratitude.

TRAVELER SACRED PLEDGE:
[x] I will never step over prayer flags, mani stones, or monks' robes.
[x] I will consume no meat in sacred inner Beyul zones.
[x] I will carry all personal trash down to the nearest hub (Leave No Trace).

=====================================================
Offline Verified • Emergency VHF 156.800 MHz • CIWEC Pokhara +977 61-532496
=====================================================`;

    const blob = new Blob([textContent], { type: 'text/plain;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'himalayan_etiquette_pocket_card.txt';
    a.click();
    URL.revokeObjectURL(url);
    setToastMsg('Offline Etiquette Pocket Card downloaded to your device!');
    setTimeout(() => setToastMsg(null), 4000);
  };

  const sanctuaries: SanctuaryItem[] = [
    {
      id: 'pashupatinath',
      name: 'Pashupatinath Sacred Temple Complex',
      region: 'kathmandu',
      corridor: 'Bagmati River Corridor',
      tag: 'Hindu Sacred Sanctuary',
      desc: 'One of the holiest abodes of Shiva. The main golden pagoda inner courtyard is strictly open to practicing Hindus only; travelers enjoy panoramic vantage points across the Bagmati terrace.',
      rules: [
        'No Non-Hindu Entry to Garbhagriha: Respect inner gold gates and security sentries without confrontation.',
        'Arya Ghat Cremation Reverence: Stand silently on opposing riverbank. Absolute ban on photographing mourning families or cremation pyres.',
        'Sadhu Etiquette: Ash-smeared holy men expect a modest daksina (NPR 100-200) if posed photography is explicitly invited.'
      ],
      pujaTime: 'Puja: 05:00 – 19:30',
      perimeter: 'Strict Outer Perimeter',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuArp9yq2FNeMp2qwSPa301VTyRz9HQjOBqxO05zIWrCozT3UAfV8FebUsz8eA5sh62zvZd1ph4NzhUts_9S-ZdR-gwK8MweC_AK_uiiB2uv3HkQvT-bL0pZQwCLGxz03f0IwdlHAe5F6BAcDQvbVbTGvg55GrU1GcsVEF_QorlamjYVAk7xdFnD001xKsOo0KuvoIn_W5kjuiiWgp5bwgU6R_Z0dAz_jG7UbWZwOqtokXchtAwaAEvh0Q'
    },
    {
      id: 'boudhanath',
      name: 'Boudhanath Stupa Mandala',
      region: 'kathmandu',
      corridor: 'UNESCO Octagonal Plaza',
      tag: 'Tibetan Buddhist Mandala',
      desc: 'The heart of Tibetan diaspora and meditation in Nepal. Devotees circle the massive relic mound from dawn until the dusk butter-lamp lighting ceremonies.',
      rules: [
        'Clockwise Prayer Wheels: Spin brass wheels solely with your right hand, chanting "Om Mani Padme Hum". Never stop them abruptly.',
        'Butter Lamp Rooms: Remove shoes before entering the enclosed copper butter lamp pavilion; keep quiet voice tone during offerings.',
        'Plinth Etiquette: Ascend upper octagonal terraces with uncovered head; avoid sitting with feet outstretched directly toward eyes of Buddha.'
      ],
      pujaTime: 'Prime Kora: 17:00 – 18:30',
      perimeter: '108 Mani Wheels',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuDAoGxqWL_G9pCW7p-GFHIjFMBNTG0l7WpEBSHMFYLkQ_zGT9EpAHingbjlwXuwkiz13HNVefAAfXAiysXuCzgMqM3xLdOlYz09W1598R3d6TyFpLRcgKWzoguG7Flkls9fzO0YeVcpIvLKnD1dlB2VWLtM8wDvBRQJgVkUsSMio5MCi8_ogPirIj81dEq2sRl4nYcIccE05WEuRYhbXSkX3KHX7lfOvTunxH5X-KtqvajDgAh9JVvISQ'
    },
    {
      id: 'gupteshwor',
      name: 'Gupteshwor Mahadev Cave Shrine',
      region: 'annapurna',
      corridor: 'Chhorepatan, Pokhara',
      tag: 'Subterranean Shaivite Shrine',
      desc: 'A sacred karst cave descending beneath Devi’s Falls, housing a self-manifested (Swayambhu) Shiva lingam surrounded by dripping subterranean mineral waters.',
      rules: [
        'Acoustic Reverence: The cave echoes intensely; maintain whisper-level speech to avoid disturbing deep meditation practitioners.',
        'Strict Camera Ban at Lingam: All photography inside the main subterranean sanctum is banned by the temple committee.',
        'Sacred Droplets: The falling limestone water is considered holy Gangajal; avoid stepping with dirty footwear on wet sacrificial stones.'
      ],
      pujaTime: 'Open: 06:00 – 18:00',
      perimeter: 'Steep Wet Stairs',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuCZ3j1Tkys7oJtjFyFvuCvojJOoMe8LaRIrTCwxON76tUp9JZ9nhIYJGD5CzoKXY9-48RfWXH3dTEZU0bDkzksz1LeOt2R2sq_0qsBnGDA1uoV4co0ukIheqJzHDLv_lGwoIYMpjdVUDXRrQ-DN_e9MgQtrfuXmVyNYi1cjJhlXhN1wvcfQm2pMWHlpS5ur1gY1BiQyv7UrwYqTUVbwsS9gmOgKbze_H5sdniNJqTTtI-LSfjPDg-lxEw'
    },
    {
      id: 'tengboche',
      name: 'Tengboche Monastery (Dawa Choling)',
      region: 'khumbu',
      corridor: '3,867m Khumbu Sanctuary',
      tag: 'Vajrayana Sherpa Monastery',
      desc: 'The spiritual centerpiece of the Khumbu Sherpa community, blessing mountaineers before Everest and Ama Dablam expeditions.',
      rules: [
        'Puja Seating Etiquette: Sit quietly cross-legged along side benches. Never step between seated lamas and the altar during horn or drum recitations.',
        'Total Cellular Silence: Put all devices on airplane mode prior to entering the heated prayer hall carpet.',
        'Donation Protocol: Present cash offerings in envelope or with two hands onto the offering box table near the Rinpoche throne.'
      ],
      pujaTime: 'Daily Chanting: 06:30 • 15:00',
      perimeter: 'High Alpine Sanctuary',
      imgUrl: 'https://lh3.googleusercontent.com/aida-public/AB6AXuAWbp_1aW_l-9Aug9CAH_R2YXjv2eYRoTUu9twH5V-ExmHM6r0ondR9bWzPMclSvvAdEoKr_I3-jyRQwSElubCW87moFmJAyUrZ4tp9OeX4sxfvSqSdUbgc2Z4yMBj84_1dVYQ_4ShsxRpNLaa0Cej3EuBrAkngfpBWQu9asg8H01Lm3eo3mXSgutUHTLYA8jRHmt6n6ZeI6O27YTCkwzLtmQYIKKzXYe3GbaaXoQUyZB2dBX6sLWjSiA'
    }
  ];

  const chortenTiers = [
    { name: 'Earth Element • Prithvi / Bhumi', symbol: 'Square Base Foundation', desc: 'Represents solid ground, ethical conduct, and unshakeable inner steadiness. When walking past, always keep your right shoulder turned toward this stone foundation.' },
    { name: 'Water Element • Apas / Varuna', symbol: 'Hemispherical Relic Dome', desc: 'Represents fluidity, compassion, and cleansing of attachments. The womb containing holy scriptures and relics of compassionate teachers.' },
    { name: 'Fire Element • Agni / Tejas', symbol: '13-Step Conical Spire', desc: 'Represents the thirteen stages of spiritual wisdom burning away ignorance. The golden rings symbolize supreme insight.' },
    { name: 'Air Element • Vayu', symbol: 'Crescent Moon & Parasol', desc: 'Represents universal compassion and shelter for all weary travelers crossing high mountain passes.' },
    { name: 'Space Element • Akasha', symbol: 'Sun & Dissolving Flame', desc: 'Represents ultimate liberation, boundless open sky, and luminous wisdom beyond death.' }
  ];

  const filteredSanctuaries = activeRegion === 'all'
    ? sanctuaries
    : sanctuaries.filter(s => s.region === activeRegion);

  return (
    <div className="w-full min-h-screen bg-[#FFF8F6] text-[#201A18] antialiased pb-24">
      {/* Toast Alert */}
      {toastMsg && (
        <div className="fixed bottom-6 right-6 z-50 px-4 py-3 bg-[#201A18] text-white rounded-xl shadow-xl flex items-center gap-2 text-xs font-semibold animate-in fade-in duration-200">
          <Check className="w-4 h-4 text-emerald-400" />
          <span>{toastMsg}</span>
        </div>
      )}

      {/* Top Banner Header */}
      <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 pt-8 pb-4">
        <div className="flex flex-wrap items-center justify-between gap-4 pb-6 border-b border-[#E8DDD3]">
          <div>
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#9D3E19] text-[11px] font-bold uppercase tracking-wider mb-2">
              <span className="w-1.5 h-1.5 rounded-full bg-[#9D3E19]" />
              Dharma &amp; Himalayan Heritage Etiquette
            </div>
            <h1 className="font-serif-yatra text-3xl sm:text-5xl font-bold text-[#201A18] tracking-tight">
              Sacred Sanctuaries &amp; <span className="italic text-[#9D3E19]">Mountain Protocol</span>
            </h1>
            <p className="text-xs sm:text-sm text-[#56423B] mt-2 max-w-2xl leading-relaxed">
              Walking with reverence through living spiritual corridors. Real-time guidelines for stupas, chortens, carved mani stones, and sacred alpine lakes across Nepal’s sacred topography.
            </p>
          </div>

          <div className="inline-flex items-center gap-2 px-4 py-2 bg-[#FDF1EC] rounded-2xl border border-[#E8DDD3] text-xs font-bold text-[#9D3E19] shadow-2xs">
            <span className="w-2 h-2 rounded-full bg-[#1D705C] animate-pulse" />
            <span>Living Sanctuary Mode Active</span>
          </div>
        </div>
      </div>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* THE FOUR GOLDEN PILLARS OF HIMALAYAN KORA                     */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-8">
        <div className="mb-6">
          <span className="text-[11px] font-bold uppercase tracking-wider text-[#9D3E19]">Foundational Dharma Observances</span>
          <h2 className="font-serif-yatra text-2xl font-bold text-[#201A18] mt-1">The Four Golden Pillars of Himalayan Kora</h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {/* Pillar 1 */}
          <div className="p-6 rounded-2xl bg-white border border-[#E8DDD3] shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#9D3E19] flex items-center justify-center font-bold">
                <RotateCw className="w-5 h-5" />
              </div>
              <div className="text-[10px] text-[#904D00] uppercase font-bold tracking-wider">Rule 01 • Pradaksina</div>
              <h3 className="font-serif-yatra text-base font-bold text-[#201A18]">Clockwise Circumambulation</h3>
              <p className="text-xs text-[#56423B] leading-relaxed">
                Always circumambulate stupas, chortens, and mani stone walls keeping them to your right side (kora). Never walk counter-clockwise unless in rare Bon tradition routes.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-[#E8DDD3] text-[11px] text-[#9D3E19] font-bold flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> Maintain Rightward Path
            </div>
          </div>

          {/* Pillar 2 */}
          <div className="p-6 rounded-2xl bg-white border border-[#E8DDD3] shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#D97706] flex items-center justify-center font-bold">
                <Compass className="w-5 h-5" />
              </div>
              <div className="text-[10px] text-[#904D00] uppercase font-bold tracking-wider">Rule 02 • Paduka</div>
              <h3 className="font-serif-yatra text-base font-bold text-[#201A18]">Barefoot in Sanctums</h3>
              <p className="text-xs text-[#56423B] leading-relaxed">
                Remove footwear, leather accessories, and head coverings before crossing thresholds. Never point soles of feet directly toward statues, monks, or shrines.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-[#E8DDD3] text-[11px] text-[#D97706] font-bold flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> Unclothed Soles &amp; Humility
            </div>
          </div>

          {/* Pillar 3 */}
          <div className="p-6 rounded-2xl bg-white border border-[#E8DDD3] shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#1D705C] flex items-center justify-center font-bold">
                <EyeOff className="w-5 h-5" />
              </div>
              <div className="text-[10px] text-[#904D00] uppercase font-bold tracking-wider">Rule 03 • Dhyana</div>
              <h3 className="font-serif-yatra text-base font-bold text-[#201A18]">Reverent Sight &amp; No Flash</h3>
              <p className="text-xs text-[#56423B] leading-relaxed">
                Strictly silence lenses in inner deity sanctums, lamp meditation recesses, and funeral cremation ghats along the Bagmati. Ask permission before capturing Sadhus or Lamas.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-[#E8DDD3] text-[11px] text-[#1D705C] font-bold flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> Honor Sacred Mystery
            </div>
          </div>

          {/* Pillar 4 */}
          <div className="p-6 rounded-2xl bg-white border border-[#E8DDD3] shadow-xs hover:shadow-md transition-shadow flex flex-col justify-between">
            <div className="space-y-3">
              <div className="w-10 h-10 rounded-xl bg-[#FDF1EC] text-[#625B52] flex items-center justify-center font-bold">
                <Shirt className="w-5 h-5" />
              </div>
              <div className="text-[10px] text-[#904D00] uppercase font-bold tracking-wider">Rule 04 • Khata</div>
              <h3 className="font-serif-yatra text-base font-bold text-[#201A18]">Modest Attire &amp; Scarf Respect</h3>
              <p className="text-xs text-[#56423B] leading-relaxed">
                Drape shoulders and knees in loose cottons. Receive sacred white silk Khata scarves with both outstretched palms, head bowed gently forward.
              </p>
            </div>
            <div className="pt-4 mt-4 border-t border-[#E8DDD3] text-[11px] text-[#625B52] font-bold flex items-center gap-1.5">
              <Check className="w-3.5 h-3.5" /> Two-Handed Devotion
            </div>
          </div>
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* INTERACTIVE SANCTUARY PROTOCOLS WITH REGIONAL FILTERS         */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-8">
        <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-6">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#9D3E19]">Corridor Protocols</span>
            <h2 className="font-serif-yatra text-2xl font-bold text-[#201A18] mt-1">Interactive Sanctuary Protocols</h2>
          </div>

          {/* Region Tabs */}
          <div className="flex flex-wrap gap-1.5 p-1 rounded-full bg-[#F8EBE6] border border-[#E8DDD3]">
            {[
              { id: 'all', label: 'All Sacred Sites' },
              { id: 'kathmandu', label: 'Kathmandu Valley' },
              { id: 'khumbu', label: 'Khumbu Highlands' },
              { id: 'annapurna', label: 'Annapurna & Pokhara' },
              { id: 'mustang', label: 'Mustang Kingdom' },
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveRegion(tab.id)}
                className={`px-3.5 py-1.5 rounded-full text-xs font-bold transition-all cursor-pointer ${
                  activeRegion === tab.id
                    ? 'bg-[#9D3E19] text-white shadow-xs'
                    : 'text-[#56423B] hover:text-[#201A18]'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Guides Grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {filteredSanctuaries.map((site) => (
            <article key={site.id} className="bg-white rounded-2xl overflow-hidden border border-[#E8DDD3] shadow-xs flex flex-col">
              <div className="relative h-56 w-full overflow-hidden bg-[#F8EBE6]">
                <img src={site.imgUrl} alt={site.name} className="w-full h-full object-cover" />
                <div className="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-white/90 backdrop-blur-md text-[11px] font-bold text-[#201A18] shadow-xs">
                  {site.tag}
                </div>
                <div className="absolute bottom-3 right-3 px-2 py-0.5 rounded-lg bg-black/60 text-white text-[10px]">
                  {site.corridor}
                </div>
              </div>

              <div className="p-6 flex-1 flex flex-col justify-between space-y-4">
                <div>
                  <h3 className="font-serif-yatra text-lg font-bold text-[#201A18]">
                    {site.name}
                  </h3>
                  <p className="text-xs text-[#56423B] mt-1.5 leading-relaxed">
                    {site.desc}
                  </p>
                </div>

                <div className="space-y-2 pt-2 border-t border-[#E8DDD3]">
                  {site.rules.map((rule, idx) => (
                    <div key={idx} className="flex items-start gap-2 text-xs text-[#56423B]">
                      <span className="w-1.5 h-1.5 rounded-full bg-[#9D3E19] mt-1.5 shrink-0" />
                      <span className="leading-relaxed">{rule}</span>
                    </div>
                  ))}
                </div>

                <div className="pt-3 border-t border-[#E8DDD3] flex items-center justify-between text-xs font-semibold text-[#8A726A]">
                  <span className="flex items-center gap-1.5">
                    <Clock className="w-3.5 h-3.5 text-[#D97706]" />
                    {site.pujaTime}
                  </span>
                  <span className="px-2.5 py-0.5 rounded-full bg-[#FDF1EC] text-[#9D3E19] text-[11px] font-bold">
                    {site.perimeter}
                  </span>
                </div>
              </div>
            </article>
          ))}
        </div>
      </section>

      {/* ───────────────────────────────────────────────────────────── */}
      {/* ANATOMY OF A MOUNTAIN CHORTEN & PASS PROTOCOLS                */}
      {/* ───────────────────────────────────────────────────────────── */}
      <section className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-12 py-8">
        <div className="bg-white rounded-3xl p-6 sm:p-10 border border-[#E8DDD3] shadow-md space-y-8">
          <div>
            <span className="text-[11px] font-bold uppercase tracking-wider text-[#9D3E19]">Architectural Anatomy • High Alpine Dharma</span>
            <h2 className="font-serif-yatra text-2xl sm:text-3xl font-bold text-[#201A18] mt-1">
              Anatomy of a Mountain Chorten &amp; Pass Protocols
            </h2>
            <p className="text-xs sm:text-sm text-[#56423B] mt-1">
              In the high valleys, every stone, pass (La), and chorten embodies cosmic harmony. Understand the five elemental tiers and the precise liturgy of crossing high Himalayan cols.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            {/* Interactive Chorten Tiers */}
            <div className="lg:col-span-5 flex flex-col gap-2">
              <div className="text-xs font-bold text-[#8A726A] uppercase tracking-wider mb-1">
                Five Elemental Tiers (Click to Inspect)
              </div>
              {chortenTiers.map((tier, idx) => {
                const isActive = activeChortenTier === idx;
                return (
                  <button
                    key={idx}
                    onClick={() => setActiveChortenTier(idx)}
                    className={`p-3.5 rounded-xl border text-left transition-all cursor-pointer ${
                      isActive
                        ? 'bg-[#9D3E19] text-white border-[#9D3E19] shadow-xs'
                        : 'bg-[#FDF1EC] text-[#201A18] border-[#E8DDD3] hover:bg-[#F8EBE6]'
                    }`}
                  >
                    <div className="text-xs font-bold">{tier.name}</div>
                    <div className="text-[11px] opacity-80 mt-0.5">{tier.symbol}</div>
                  </button>
                );
              })}
            </div>

            {/* Selected Element Description & High Pass Ritual */}
            <div className="lg:col-span-7 space-y-5">
              <div className="p-5 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3]">
                <div className="text-[10px] font-bold text-[#9D3E19] uppercase tracking-wider mb-1">
                  Active Tier Correspondence
                </div>
                <h4 className="font-serif-yatra text-lg font-bold text-[#201A18]">
                  {chortenTiers[activeChortenTier].name}
                </h4>
                <p className="text-xs text-[#56423B] mt-2 leading-relaxed">
                  {chortenTiers[activeChortenTier].desc}
                </p>
              </div>

              {/* High Pass Ritual (Thorong La • Cho La • Larkya) */}
              <div className="p-5 rounded-2xl bg-white border border-[#E8DDD3] space-y-3">
                <div className="flex items-center justify-between">
                  <h4 className="font-serif-yatra text-sm font-bold text-[#201A18] flex items-center gap-2">
                    <span>🏔️ High Pass Ritual (La Pass Protocol)</span>
                  </h4>
                  <span className="text-[10px] font-bold text-[#8A726A]">Thorong La • Cho La • Larkya</span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
                  <div className="p-3 bg-[#FDF1EC] rounded-xl border border-[#E8DDD3]">
                    <div className="text-[10px] font-bold text-[#9D3E19]">1. CHANTING AT RIDGE</div>
                    <div className="font-bold text-[#201A18] mt-1">"Ki Ki So So Lha Gyalo!"</div>
                    <div className="text-[10px] text-[#56423B] mt-0.5">Shouted three times at crest to proclaim victory of benevolent spirits.</div>
                  </div>
                  <div className="p-3 bg-[#FDF1EC] rounded-xl border border-[#E8DDD3]">
                    <div className="text-[10px] font-bold text-[#D97706]">2. PRAYER FLAGS (LUNGTA)</div>
                    <div className="font-bold text-[#201A18] mt-1">Tie High, Never Tread</div>
                    <div className="text-[10px] text-[#56423B] mt-0.5">Secure wind-horse strings from rock to cairn; never let mantras touch mud.</div>
                  </div>
                  <div className="p-3 bg-[#FDF1EC] rounded-xl border border-[#E8DDD3]">
                    <div className="text-[10px] font-bold text-[#1D705C]">3. CAIRN STONE ADDITION</div>
                    <div className="font-bold text-[#201A18] mt-1">One Gentle Pebble</div>
                    <div className="text-[10px] text-[#56423B] mt-0.5">Add a single small pebble to the mountain cairn with a bow of gratitude.</div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Sherpa Oral Heritage & Daily Purity Pledge */}
          <div className="bg-[#FDF1EC] rounded-2xl p-6 sm:p-8 border border-[#E8DDD3] flex flex-col lg:flex-row items-center justify-between gap-6">
            <div className="max-w-xl space-y-2">
              <span className="text-[10px] font-bold uppercase tracking-wider text-[#9D3E19]">Sherpa Oral Heritage • Khumbu Wisdom</span>
              <blockquote className="font-serif-yatra italic text-base sm:text-lg text-[#201A18]">
                "The mountains are not stone corpses to be conquered. They are the palaces of protective deities (Yul Lha). Walk as a quiet guest in another being’s temple."
              </blockquote>
            </div>

            {/* Trekker's Daily Purity Pledge */}
            <div className="w-full lg:w-80 bg-white p-4 rounded-xl border border-[#E8DDD3] shadow-xs space-y-2.5">
              <div className="text-xs font-bold text-[#201A18] uppercase tracking-wider border-b border-[#E8DDD3] pb-1.5">
                Trekker's Daily Purity Pledge
              </div>
              {[
                'I will never step over prayer flags, mani stones, or monks’ robes.',
                'I will consume no meat in sacred inner Beyul zones (Namche to Base Camp).',
                'I will carry all personal trash down to Lukla hub.'
              ].map((item, idx) => (
                <label key={idx} className="flex items-start gap-2 text-[11px] text-[#56423B] cursor-pointer">
                  <input
                    type="checkbox"
                    checked={pledgeChecked[idx] || false}
                    onChange={(e) => handlePledgeToggle(idx, e.target.checked)}
                    className="mt-0.5 accent-[#9D3E19]"
                  />
                  <span>{item}</span>
                </label>
              ))}
              <button
                onClick={handleDownloadPocketCard}
                className="w-full mt-2 inline-flex items-center justify-center gap-1.5 bg-[#9D3E19] hover:bg-[#BD552F] text-white py-2 rounded-lg text-xs font-bold transition-all cursor-pointer"
              >
                <Download className="w-3.5 h-3.5" />
                <span>Download Etiquette Pocket Card</span>
              </button>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
};
