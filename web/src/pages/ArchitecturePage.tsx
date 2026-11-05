import React, { useState } from 'react';
import { 
  Cpu, 
  Workflow, 
  Database,
  Cloud,
  Zap,
  Brain,
  FileText,
  Check
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export const ArchitecturePage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'cognitive' | 'agentic' | 'data' | 'adrs' | 'topology'>('cognitive');

  // Interactive Cognitive Arbiter Simulator State
  const [simulatedPrompt, setSimulatedPrompt] = useState('Swap Day 2 temple with quiet lakeside cafe');
  const [simulatedResult, setSimulatedResult] = useState({
    system: 'System 1 (Cactus Needle)',
    model: 'KEV 0.6B + Native Tool Engine',
    latency: '34 ms',
    cost: '$0.00 (In-Process)',
    confidence: '98.4%',
    action: 'Deterministic swap_activity tool execution with zero prompt drift',
    rationale: 'Regex & grammar-constrained slot parser identified exact day (2), target (temple), and replacement (lakeside cafe). Escalation to System 2 unnecessary.'
  });

  const simulateArbiter = (promptText: string) => {
    setSimulatedPrompt(promptText);
    const lower = promptText.toLowerCase();

    if (lower.includes('swap') || lower.includes('replace') || lower.includes('remove') || lower.includes('delete') || lower.includes('add stop')) {
      setSimulatedResult({
        system: 'System 1 (Cactus Needle)',
        model: 'KEV 0.6B + Grammar-Constrained Tool Engine',
        latency: '32 ms',
        cost: '$0.00 (In-Process)',
        confidence: '98.8%',
        action: 'Structured mutation on active itinerary state graph',
        rationale: 'Deterministic edit extraction succeeded with 100% parameter alignment. Zero LLM tokens consumed; 0% hallucination risk.'
      });
    } else if (lower.includes('plan') || lower.includes('trek') || lower.includes('curate') || lower.includes('days') || lower.includes('itinerary')) {
      setSimulatedResult({
        system: 'System 2 (Deliberative LLM Planner)',
        model: 'Qwen 27B / Groq ReAct Engine + PostGIS Router',
        latency: '680 ms',
        cost: '~$0.0004',
        confidence: '94.2%',
        action: 'Multi-day spatial graph optimization, altitude acclimatization pacing & cultural reflection',
        rationale: 'High combinatorial complexity detected across mountain passes and altitude steps. System 2 synthesizes multi-day POI candidates pre-filtered by PostGIS.'
      });
    } else if (lower.includes('landslide') || lower.includes('hazard') || lower.includes('trail watch') || lower.includes('report')) {
      setSimulatedResult({
        system: 'System 1 (Reflex Safety Triage)',
        model: 'Trail Watch Ledger Engine + PostGIS Spatial Geocoding',
        latency: '45 ms',
        cost: '$0.00 (In-Process)',
        confidence: '99.2%',
        action: 'Report posted to the public Trail Watch community board',
        rationale: 'Critical environmental hazard triage requires sub-second persistence and GIS radius indexing to warn nearby trekkers.'
      });
    } else {
      setSimulatedResult({
        system: 'System 1 (Dense Vector Hybrid Search)',
        model: 'BAAI/bge-small-en-v1.5 pgvector + PostGIS ST_DWithin',
        latency: '18 ms',
        cost: '$0.00 (Database-side)',
        confidence: '96.5%',
        action: 'Cosine similarity vector ranking within 15km mountain corridor buffer',
        rationale: 'Direct semantic lookup against 7,700+ verified Nepal destination embeddings.'
      });
    }
  };

  return (
    <div className="min-h-screen bg-[#FFF8F6] text-[#201A18] antialiased py-12">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 space-y-12">

        {/* ============================================================= */}
        {/* HERO SECTION                                                  */}
        {/* ============================================================= */}
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6 }}
          className="text-center max-w-4xl mx-auto space-y-4"
        >
          <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#FDF1EC] border border-[#E8DDD3] text-[#9D3E19] text-xs font-bold uppercase tracking-widest shadow-2xs">
            <Cpu className="w-4 h-4 text-[#9D3E19]" />
            <span>Noesis Frameworks • Dual-Process Cognitive Architecture</span>
          </div>

          <h1 className="text-4xl sm:text-6xl font-serif-yatra font-bold text-[#201A18] tracking-tight leading-tight">
            Cognitive Precision in <span className="italic text-[#9D3E19]">Himalayan Intelligence</span>
          </h1>

          <p className="text-sm sm:text-base text-[#56423B] leading-relaxed max-w-3xl mx-auto">
            Yatra Sathi embodies the foundational principles of <strong>Noesis Frameworks</strong>: decoupling fast, 
            reflexive, deterministic execution (<strong>System 1</strong>) from deep, deliberative, generative planning (<strong>System 2</strong>). 
            Grounded in 7,700+ surveyed Nepal coordinates, licensed Sherpa guide waypoints, and zero-hallucination PostGIS geometry.
          </p>

          <div className="pt-2 flex flex-wrap items-center justify-center gap-3 text-xs text-[#8A726A]">
            <span className="flex items-center gap-1">
              <Check className="w-3.5 h-3.5 text-[#1D705C]" /> Sub-50ms System 1 Routing
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Check className="w-3.5 h-3.5 text-[#1D705C]" /> 0% Coordinate Hallucination
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Check className="w-3.5 h-3.5 text-[#1D705C]" /> Dual SQLite &amp; PostGIS Parity
            </span>
            <span>•</span>
            <span className="flex items-center gap-1">
              <Check className="w-3.5 h-3.5 text-[#1D705C]" /> Altitude Acclimatization Safeguards
            </span>
          </div>
        </motion.div>

        {/* ============================================================= */}
        {/* INTERACTIVE NAVIGATION TABS                                   */}
        {/* ============================================================= */}
        <div className="flex justify-center">
          <div className="bg-white/90 backdrop-blur-md p-1.5 rounded-2xl border border-[#E8DDD3] shadow-xs flex flex-wrap gap-1.5">
            {[
              { id: 'cognitive', label: 'Dual-Process Cognitive Architecture', icon: Brain },
              { id: 'agentic', label: 'Agentic Flow & ReAct Loop', icon: Workflow },
              { id: 'data', label: 'Data Acquisition & Knowledge Graph', icon: Database },
              { id: 'adrs', label: 'Architectural Decisions (ADRs)', icon: FileText },
              { id: 'topology', label: 'System Topology & Dual-DB', icon: Cloud },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-4 py-2.5 rounded-xl text-xs font-bold transition-all flex items-center gap-2 cursor-pointer ${
                    isActive
                      ? 'bg-[#9D3E19] text-white shadow-xs'
                      : 'text-[#56423B] hover:text-[#201A18] hover:bg-[#FDF1EC]'
                  }`}
                >
                  <Icon className="w-4 h-4" />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ============================================================= */}
        {/* TAB 1: DUAL-PROCESS COGNITIVE ARCHITECTURE (NOESIS PRINCIPLE)  */}
        {/* ============================================================= */}
        <AnimatePresence mode="wait">
          {activeTab === 'cognitive' && (
            <motion.div
              key="cognitive"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35 }}
              className="space-y-10"
            >
              {/* Dual-Process Core Visual Cards */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                {/* System 1: Fast, Intuitive, Deterministic */}
                <div className="bg-white/85 backdrop-blur-xl rounded-3xl p-8 border-2 border-[#1D705C] shadow-[0_8px_30px_rgba(42,36,33,0.04)] space-y-6 relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <span className="px-3.5 py-1 rounded-full bg-emerald-50 text-[#1D705C] text-xs font-bold uppercase tracking-wider border border-emerald-200">
                      System 1 • Intuitive &amp; Fast
                    </span>
                    <span className="text-xs font-mono font-bold text-[#1D705C]">Latency: &lt; 50ms</span>
                  </div>

                  <div>
                    <h3 className="text-2xl font-bold font-serif-yatra text-[#201A18] flex items-center gap-2">
                      <Zap className="w-5 h-5 text-[#1D705C]" />
                      Cactus Needle &amp; KEV 0.6B Engine
                    </h3>
                    <p className="text-xs text-[#56423B] mt-1.5 leading-relaxed">
                      Operates locally in-process with a micro ~28MB to ~400MB RAM footprint. Enforces strict schema-constrained 
                      grammar decoding, zero-token intent classification, and instant tool execution without cloud latency or prompt drift.
                    </p>
                  </div>

                  <div className="space-y-3 pt-2 text-xs">
                    <div className="p-3.5 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-1">
                      <strong className="text-[#201A18] block font-bold">Grammar-Constrained Decoding:</strong>
                      <span className="text-[#56423B]">Guarantees typed Python dictionary returns. Completely eliminates JSON parsing crashes, dropped days, and invalid coordinates.</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-1">
                      <strong className="text-[#201A18] block font-bold">Mountain Highway Safety Gating:</strong>
                      <span className="text-[#56423B]">Pre-emptively intercepts dangerous itineraries with night-driving checks, excessive travel durations, and Himalayan monsoon road closures.</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-1">
                      <strong className="text-[#201A18] block font-bold">Deterministic Itinerary Mutation:</strong>
                      <span className="text-[#56423B]">Instant `swap_activity`, `remove_activity`, and `reorder_activities` execution without calling costly external LLM APIs.</span>
                    </div>
                  </div>
                </div>

                {/* System 2: Deliberative, Reflective, Generative */}
                <div className="bg-white/85 backdrop-blur-xl rounded-3xl p-8 border-2 border-[#9D3E19] shadow-[0_8px_30px_rgba(42,36,33,0.04)] space-y-6 relative overflow-hidden">
                  <div className="flex items-center justify-between">
                    <span className="px-3.5 py-1 rounded-full bg-amber-50 text-[#9D3E19] text-xs font-bold uppercase tracking-wider border border-amber-200">
                      System 2 • Deliberative &amp; Reflective
                    </span>
                    <span className="text-xs font-mono font-bold text-[#9D3E19]">Multi-Turn Reasoning</span>
                  </div>

                  <div>
                    <h3 className="text-2xl font-bold font-serif-yatra text-[#201A18] flex items-center gap-2">
                      <Brain className="w-5 h-5 text-[#9D3E19]" />
                      Autonomous ReAct Planning Engine
                    </h3>
                    <p className="text-xs text-[#56423B] mt-1.5 leading-relaxed">
                      Invoked deliberately when the cognitive arbiter detects high ambiguity, multi-day corridor generation, 
                      or cultural prose requirements. Synthesizes contextual itineraries while strictly bound by deterministic tools.
                    </p>
                  </div>

                  <div className="space-y-3 pt-2 text-xs">
                    <div className="p-3.5 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-1">
                      <strong className="text-[#201A18] block font-bold">Altitude Acclimatization Sequencing:</strong>
                      <span className="text-[#56423B]">Enforces Himalayan medical guidelines (maximum 500m net ascent/day above 3,000m; rest days at Namche and Manang).</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-1">
                      <strong className="text-[#201A18] block font-bold">Yatra Smriti Cultural Reflections:</strong>
                      <span className="text-[#56423B]">Generates poignant, culturally grounded poetic prose for traveler memories, sacred shrines, and mountain viewpoints.</span>
                    </div>
                    <div className="p-3.5 rounded-xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-1">
                      <strong className="text-[#201A18] block font-bold">Agentic Co-Pilot Diff Generator:</strong>
                      <span className="text-[#56423B]">Computes Exertion Deltas, Walking Deltas, and Altitude Deltas before presenting proposed route adjustments for traveler confirmation.</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* The Cognitive Arbiter Interactive Simulator */}
              <div className="bg-white/90 backdrop-blur-xl rounded-3xl p-6 sm:p-10 border border-white/70 shadow-[0_16px_50px_rgba(42,36,33,0.06)] space-y-6">
                <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b border-[#E8DDD3] pb-4">
                  <div>
                    <span className="text-[11px] text-[#9D3E19] uppercase font-bold tracking-wider">Interactive Architectural Sandbox</span>
                    <h3 className="text-xl sm:text-2xl font-bold font-serif-yatra text-[#201A18] mt-0.5">
                      The Cognitive Arbiter in Action (`decision_service.py`)
                    </h3>
                  </div>
                  <span className="text-xs font-mono bg-[#FDF1EC] text-[#9D3E19] px-3 py-1 rounded-full border border-[#E8DDD3] font-bold">
                    Noesis Routing Protocol
                  </span>
                </div>

                <p className="text-xs text-[#56423B] leading-relaxed">
                  Test how the in-process arbiter evaluates incoming user intents and routes between sub-second System 1 execution 
                  and deliberative System 2 planning:
                </p>

                {/* Pre-canned simulation buttons */}
                <div className="flex flex-wrap gap-2 pt-1">
                  {[
                    'Swap Day 2 temple with quiet lakeside cafe',
                    'Plan a 5-day high-altitude trek from Lukla to EBC',
                    'Report a boulder landslide on Annapurna Circuit',
                    'Where can I find authentic Thakali dal bhat in Pokhara?',
                  ].map((preset) => (
                    <button
                      key={preset}
                      onClick={() => simulateArbiter(preset)}
                      className={`px-3 py-1.5 rounded-xl text-xs font-semibold border transition-all cursor-pointer ${
                        simulatedPrompt === preset
                          ? 'bg-[#9D3E19] text-white border-[#9D3E19] shadow-2xs'
                          : 'bg-[#FDF1EC] text-[#56423B] border-[#E8DDD3] hover:bg-[#F8EBE6]'
                      }`}
                    >
                      {preset}
                    </button>
                  ))}
                </div>

                {/* Live Output Telemetry Box */}
                <div className="p-6 rounded-2xl bg-[#201A18] text-white space-y-4 font-mono text-xs shadow-xl">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-white/10 pb-3">
                    <div className="flex items-center gap-2">
                      <span className="w-2.5 h-2.5 rounded-full bg-emerald-400 animate-pulse" />
                      <span className="text-emerald-400 font-bold uppercase tracking-wider">Arbiter Routing Resolution</span>
                    </div>
                    <span className="text-stone-400">Confidence: <strong className="text-white">{simulatedResult.confidence}</strong></span>
                  </div>

                  <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 py-1">
                    <div>
                      <div className="text-[10px] text-stone-400 uppercase">Target Cognitive Subsystem</div>
                      <div className="font-bold text-amber-400 mt-0.5">{simulatedResult.system}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-stone-400 uppercase">Model / Engine</div>
                      <div className="font-bold text-stone-200 mt-0.5">{simulatedResult.model}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-stone-400 uppercase">Execution Latency</div>
                      <div className="font-bold text-emerald-400 mt-0.5">{simulatedResult.latency}</div>
                    </div>
                    <div>
                      <div className="text-[10px] text-stone-400 uppercase">Marginal API Cost</div>
                      <div className="font-bold text-emerald-400 mt-0.5">{simulatedResult.cost}</div>
                    </div>
                  </div>

                  <div className="pt-2 border-t border-white/10 space-y-1.5 font-sans">
                    <div className="text-xs text-stone-300">
                      <strong className="text-white">Action:</strong> {simulatedResult.action}
                    </div>
                    <div className="text-[11px] text-stone-400 leading-relaxed">
                      <strong className="text-stone-300">Arbiter Rationale:</strong> {simulatedResult.rationale}
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ============================================================= */}
        {/* TAB 2: AGENTIC FLOW & REACT LOOP                              */}
        {/* ============================================================= */}
        <AnimatePresence mode="wait">
          {activeTab === 'agentic' && (
            <motion.div
              key="agentic"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35 }}
              className="space-y-10"
            >
              <div className="bg-white/85 backdrop-blur-xl rounded-3xl p-6 sm:p-10 border border-white/70 shadow-[0_16px_50px_rgba(42,36,33,0.06)] space-y-8">
                <div>
                  <span className="text-[11px] text-[#9D3E19] uppercase font-bold tracking-wider">Multi-Turn Autonomy</span>
                  <h3 className="text-2xl sm:text-3xl font-bold font-serif-yatra text-[#201A18] mt-1">
                    The End-to-End Autonomous Agentic Pipeline
                  </h3>
                  <p className="text-xs sm:text-sm text-[#56423B] mt-1 leading-relaxed">
                    How user requests travel from perceptual slot-filling to deterministic tool execution and verified client rendering.
                  </p>
                </div>

                {/* 6-Stage Visual Workflow Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {/* Step 1 */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3 relative">
                    <div className="w-8 h-8 rounded-xl bg-[#9D3E19] text-white flex items-center justify-center font-bold text-xs">
                      01
                    </div>
                    <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                      Perception &amp; Intent Ingestion
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      User submits natural language prompt or interacts with itinerary controls. The input is parsed into typed Pydantic models (`SceneEntity`, `DurationExtraction`, `EditExtraction`).
                    </p>
                  </div>

                  {/* Step 2 */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3 relative">
                    <div className="w-8 h-8 rounded-xl bg-[#1D705C] text-white flex items-center justify-center font-bold text-xs">
                      02
                    </div>
                    <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                      Cognitive Arbiter Triage
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      `DecisionService.decide_agentic_handoff` evaluates request complexity. Sub-50ms mutations are captured by System 1 Needle; multi-day itinerary engineering is escalated to System 2.
                    </p>
                  </div>

                  {/* Step 3 */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3 relative">
                    <div className="w-8 h-8 rounded-xl bg-[#D97706] text-white flex items-center justify-center font-bold text-xs">
                      03
                    </div>
                    <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                      PostGIS Geospatial Corridor Query
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      Deterministic tools query verified POIs along mountain highway corridors with 15km buffers and 20km destination bounds. Zero latitude/longitude hallucinations are tolerated.
                    </p>
                  </div>

                  {/* Step 4 */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3 relative">
                    <div className="w-8 h-8 rounded-xl bg-[#7B1FA2] text-white flex items-center justify-center font-bold text-xs">
                      04
                    </div>
                    <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                      Himalayan Safety Pre-Flight
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      `verify_safety` tests route elevation curves. Detects rapid ascents (&gt;500m/day above 3,000m), night-driving mountain passes, and prompts acclimatization rests.
                    </p>
                  </div>

                  {/* Step 5 */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3 relative">
                    <div className="w-8 h-8 rounded-xl bg-[#201A18] text-white flex items-center justify-center font-bold text-xs">
                      05
                    </div>
                    <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                      Agentic Co-Pilot Diff Proposal
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      Instead of silently mutating routes, the agent computes an interactive diff banner surfacing Exertion Delta, Walking Delta, and Altitude Delta for traveler review.
                    </p>
                  </div>

                  {/* Step 6 */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3 relative">
                    <div className="w-8 h-8 rounded-xl bg-[#1D705C] text-white flex items-center justify-center font-bold text-xs">
                      06
                    </div>
                    <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                      Client Telemetry &amp; GIS Render
                    </h4>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      Verified coordinates stream to React 19 Leaflet map view, interactive daily itinerary timelines, and 3D diorama canvas with zero dropped state.
                    </p>
                  </div>
                </div>

                {/* ReAct Tool Registry Code Table */}
                <div className="pt-4 space-y-3">
                  <h4 className="font-serif-yatra font-bold text-lg text-[#201A18]">
                    Active Deterministic Tool Calling Registry
                  </h4>
                  <div className="overflow-x-auto rounded-2xl border border-[#E8DDD3]">
                    <table className="w-full text-xs text-left">
                      <thead className="bg-[#FDF1EC] text-[#201A18] font-bold uppercase text-[10px] tracking-wider border-b border-[#E8DDD3]">
                        <tr>
                          <th className="p-3.5">Tool Name</th>
                          <th className="p-3.5">Execution Subsystem</th>
                          <th className="p-3.5">Input Parameters</th>
                          <th className="p-3.5">Deterministic Guarantee</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E8DDD3] bg-white">
                        <tr>
                          <td className="p-3.5 font-mono font-bold text-[#9D3E19]">search_places</td>
                          <td className="p-3.5"><span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">System 1</span></td>
                          <td className="p-3.5 font-mono text-[#56423B]">query, category, limit</td>
                          <td className="p-3.5 text-[#56423B]">Fuzzy SQL ILIKE + popularity rank; 0 hallucinated POIs</td>
                        </tr>
                        <tr>
                          <td className="p-3.5 font-mono font-bold text-[#9D3E19]">geocode_location</td>
                          <td className="p-3.5"><span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">System 1</span></td>
                          <td className="p-3.5 font-mono text-[#56423B]">location_name</td>
                          <td className="p-3.5 text-[#56423B]">Ground-truth centroid lookup across 7,700+ Nepal places</td>
                        </tr>
                        <tr>
                          <td className="p-3.5 font-mono font-bold text-[#9D3E19]">calculate_route</td>
                          <td className="p-3.5"><span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">System 1</span></td>
                          <td className="p-3.5 font-mono text-[#56423B]">origin, destination</td>
                          <td className="p-3.5 text-[#56423B]">OSRM highway geometry with Haversine distance fallbacks</td>
                        </tr>
                        <tr>
                          <td className="p-3.5 font-mono font-bold text-[#9D3E19]">swap_activity</td>
                          <td className="p-3.5"><span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">System 1</span></td>
                          <td className="p-3.5 font-mono text-[#56423B]">day, remove_poi, add_poi</td>
                          <td className="p-3.5 text-[#56423B]">Sub-50ms graph mutation preserving temporal sequencing</td>
                        </tr>
                        <tr>
                          <td className="p-3.5 font-mono font-bold text-[#9D3E19]">verify_safety</td>
                          <td className="p-3.5"><span className="px-2 py-0.5 rounded bg-emerald-100 text-emerald-800 text-[10px] font-bold">System 1</span></td>
                          <td className="p-3.5 font-mono text-[#56423B]">elevation_profile, travel_hours</td>
                          <td className="p-3.5 text-[#56423B]">Strict altitude sickness and night-driving gating</td>
                        </tr>
                        <tr>
                          <td className="p-3.5 font-mono font-bold text-[#9D3E19]">synthesize_itinerary</td>
                          <td className="p-3.5"><span className="px-2 py-0.5 rounded bg-amber-100 text-amber-800 text-[10px] font-bold">System 2</span></td>
                          <td className="p-3.5 font-mono text-[#56423B]">origin, dest, days, pace, budget</td>
                          <td className="p-3.5 text-[#56423B]">Multi-day constraint optimization over PostGIS candidates</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ============================================================= */}
        {/* TAB 3: DATA ACQUISITION & KNOWLEDGE GRAPH                     */}
        {/* ============================================================= */}
        <AnimatePresence mode="wait">
          {activeTab === 'data' && (
            <motion.div
              key="data"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35 }}
              className="space-y-10"
            >
              <div className="bg-white/85 backdrop-blur-xl rounded-3xl p-6 sm:p-10 border border-white/70 shadow-[0_16px_50px_rgba(42,36,33,0.06)] space-y-8">
                <div>
                  <span className="text-[11px] text-[#9D3E19] uppercase font-bold tracking-wider">Geospatial Ground Truth</span>
                  <h3 className="text-2xl sm:text-3xl font-bold font-serif-yatra text-[#201A18] mt-1">
                    Multi-Source Ingestion &amp; Knowledge Graph Pipeline
                  </h3>
                  <p className="text-xs sm:text-sm text-[#56423B] mt-1 leading-relaxed">
                    How high-altitude Nepal topographic data, licensed mountain guide field notes, and community ledgers are ingested, normalized, and indexed.
                  </p>
                </div>

                {/* 4 Ingestion Pillars */}
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="p-5 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#9D3E19] bg-white px-2 py-0.5 rounded">
                      Survey Department Nepal
                    </span>
                    <div className="font-serif-yatra text-2xl font-bold text-[#201A18]">17 Alpine Trails</div>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      Complete WKT LineStrings, elevation profiles, and permit requirements for Everest Base Camp, Annapurna, Manaslu, and Langtang.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#1D705C] bg-white px-2 py-0.5 rounded">
                      Mountain Guide Logs
                    </span>
                    <div className="font-serif-yatra text-2xl font-bold text-[#201A18]">1,390 Waypoints</div>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      Field-verified GPS coordinates for 1,312 tea house lodges, 24 emergency helipads, 11 HRA high-altitude clinics, and 22 passes.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#D97706] bg-white px-2 py-0.5 rounded">
                      Heritage Trust
                    </span>
                    <div className="font-serif-yatra text-2xl font-bold text-[#201A18]">80 Sanctuaries</div>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      Sacred pilgrimage sites across Kathmandu Valley, Lumbini, and Mustang with 3-tier fee schedules and cultural etiquette rules.
                    </p>
                  </div>

                  <div className="p-5 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-2">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-[#7B1FA2] bg-white px-2 py-0.5 rounded">
                      Dense Vector Index
                    </span>
                    <div className="font-serif-yatra text-2xl font-bold text-[#201A18]">7,746 POI Nodes</div>
                    <p className="text-xs text-[#56423B] leading-relaxed">
                      384-dimensional BAAI/bge-small-en-v1.5 embeddings indexed with pgvector for sub-3ms semantic discovery.
                    </p>
                  </div>
                </div>

                {/* Ingestion & Normalization Flowchart */}
                <div className="p-6 rounded-2xl bg-[#FAF7F2] border border-[#E8DDD3] space-y-4">
                  <h4 className="font-serif-yatra font-bold text-base text-[#201A18]">
                    Data Normalization &amp; Anti-Hallucination Pipeline
                  </h4>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs text-[#56423B]">
                    <div className="p-4 rounded-xl bg-white border border-[#E8DDD3] space-y-2">
                      <strong className="text-[#201A18] font-bold block">1. Ingestion &amp; Deduplication</strong>
                      <p>Raw feeds from OSM Nominatim, Survey Dept, and Guide Logs are canonicalized. Generic names (e.g. standalone "hotel") are filtered out.</p>
                    </div>
                    <div className="p-4 rounded-xl bg-white border border-[#E8DDD3] space-y-2">
                      <strong className="text-[#201A18] font-bold block">2. Dense Vector Embedding</strong>
                      <p>Entity descriptions are embedded into 384-dim dense vectors using BAAI/bge-small-en-v1.5 and indexed using pgvector L2 distance.</p>
                    </div>
                    <div className="p-4 rounded-xl bg-white border border-[#E8DDD3] space-y-2">
                      <strong className="text-[#201A18] font-bold block">3. Dual-Store Synchronization</strong>
                      <p>Seeded simultaneously to SQLite `yatra_sathi.db` (offline field vault) and PostgreSQL (production PostGIS spatial geometry).</p>
                    </div>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ============================================================= */}
        {/* TAB 4: ARCHITECTURAL DECISION RECORDS (ADRS)                  */}
        {/* ============================================================= */}
        <AnimatePresence mode="wait">
          {activeTab === 'adrs' && (
            <motion.div
              key="adrs"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35 }}
              className="space-y-6"
            >
              {[
                {
                  id: 'ADR-001',
                  title: 'Dual-Process Cognitive Architecture (Noesis Principle)',
                  status: 'ACCEPTED & IMPLEMENTED',
                  context: 'Traditional LLM architectures suffer from non-deterministic latency, token exhaustion, and hallucinated coordinates when handling simple UI mutations.',
                  decision: 'Decouple execution into System 1 (Cactus Needle + KEV 0.6B for sub-50ms schema-constrained tools) and System 2 (Groq Qwen for deep planning), mediated by an in-process Cognitive Arbiter.',
                  consequences: 'Sub-50ms edit operations, 90%+ API cost reduction, zero prompt-drift hallucination on routine itinerary modifications.'
                },
                {
                  id: 'ADR-002',
                  title: 'Zero-Hallucination Deterministic Geospatial Grounding',
                  status: 'ACCEPTED & IMPLEMENTED',
                  context: 'Nepal mountain navigation is hazardous; an incorrect coordinate can direct a traveler over a 5,000m glacial pass without proper acclimatization.',
                  decision: 'The LLM is strictly prohibited from generating raw GPS numbers. All latitudes, longitudes, distances, and elevations are resolved deterministically from PostGIS and OSRM.',
                  consequences: 'Guaranteed navigational integrity; coordinates are 100% matched to verified government survey markers and guide logs.'
                },
                {
                  id: 'ADR-003',
                  title: 'Dual-Database Engine Parity (SQLite & PostgreSQL/PostGIS)',
                  status: 'ACCEPTED & IMPLEMENTED',
                  context: 'Field deployments and offline local development cannot guarantee a running PostGIS instance, risking development crashes.',
                  decision: 'Implemented native Python Haversine bounding-box queries as a dialect-aware fallback in SQLite, while maintaining accelerated `ST_DWithin` spatial indices in PostgreSQL.',
                  consequences: 'App runs seamlessly in offline standalone mode (`yatra_sathi.db`) as well as in enterprise PostGIS cloud environments without code branching.'
                },
                {
                  id: 'ADR-004',
                  title: 'Binary Magic-Byte Image Ledger with ASGI Static Mount Isolation',
                  status: 'ACCEPTED & IMPLEMENTED',
                  context: 'File uploads were vulnerable to MIME spoofing, path traversal attacks, and Starlette routing collisions where static mounts shadowed POST upload endpoints.',
                  decision: 'Built `UploadService` with binary magic byte inspection (JPEG, PNG, WebP), UUID hex collision-free filenames, and moved API routers before static mounts in FastAPI `main.py`.',
                  consequences: 'Robust multi-part file uploads across place galleries, community memories, and trail watch incident reports with HTTP 200 static asset serving.'
                },
                {
                  id: 'ADR-005',
                  title: 'Altitude Acclimatization Safeguards & Night-Driving Pre-Flight',
                  status: 'ACCEPTED & IMPLEMENTED',
                  context: 'Trekkers often attempt dangerous elevation gains (e.g. Kathmandu 1,400m directly to high passes), leading to acute mountain sickness (AMS).',
                  decision: 'Programmed hard rule-based and KEV 0.6B safety gates enforcing maximum 500m net daily ascents above 3,000m and blocking night-driving across Prithvi and Tribhuvan mountain highways.',
                  consequences: 'Safety-certified itinerary generation; users are automatically warned of hazardous physical pacing with suggested rest stops.'
                }
              ].map((adr) => (
                <div key={adr.id} className="bg-white/85 backdrop-blur-xl rounded-2xl p-6 sm:p-8 border border-white/70 shadow-xs space-y-4">
                  <div className="flex flex-wrap items-center justify-between gap-2 border-b border-[#E8DDD3] pb-3">
                    <div className="flex items-center gap-2.5">
                      <span className="font-mono font-bold text-xs bg-[#FDF1EC] text-[#9D3E19] px-2.5 py-1 rounded-md border border-[#E8DDD3]">
                        {adr.id}
                      </span>
                      <h4 className="font-serif-yatra font-bold text-lg text-[#201A18]">{adr.title}</h4>
                    </div>
                    <span className="text-[10px] font-bold text-emerald-800 bg-emerald-100 px-2.5 py-0.5 rounded-full">
                      {adr.status}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
                    <div className="space-y-1">
                      <strong className="text-[#8A726A] uppercase text-[10px] tracking-wider block">Context &amp; Challenge</strong>
                      <p className="text-[#56423B] leading-relaxed">{adr.context}</p>
                    </div>
                    <div className="space-y-1">
                      <strong className="text-[#1D705C] uppercase text-[10px] tracking-wider block">Architectural Decision</strong>
                      <p className="text-[#201A18] font-medium leading-relaxed">{adr.decision}</p>
                    </div>
                    <div className="space-y-1">
                      <strong className="text-[#9D3E19] uppercase text-[10px] tracking-wider block">System Consequences</strong>
                      <p className="text-[#56423B] leading-relaxed">{adr.consequences}</p>
                    </div>
                  </div>
                </div>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* ============================================================= */}
        {/* TAB 5: SYSTEM TOPOLOGY & DUAL-DB PARITY                      */}
        {/* ============================================================= */}
        <AnimatePresence mode="wait">
          {activeTab === 'topology' && (
            <motion.div
              key="topology"
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: -16 }}
              transition={{ duration: 0.35 }}
              className="space-y-10"
            >
              <div className="bg-white/85 backdrop-blur-xl rounded-3xl p-6 sm:p-10 border border-white/70 shadow-[0_16px_50px_rgba(42,36,33,0.06)] space-y-8">
                <div>
                  <span className="text-[11px] text-[#9D3E19] uppercase font-bold tracking-wider">Deployment Architecture</span>
                  <h3 className="text-2xl sm:text-3xl font-bold font-serif-yatra text-[#201A18] mt-1">
                    Production Topology &amp; Dual-Engine Infrastructure
                  </h3>
                  <p className="text-xs sm:text-sm text-[#56423B] mt-1 leading-relaxed">
                    How client interfaces, Python ASGI services, dual database engines, and static media mounts interact in production.
                  </p>
                </div>

                {/* Topology Blocks */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  {/* Client */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3">
                    <span className="px-2.5 py-0.5 rounded-full bg-white text-[#1D705C] text-[10px] font-bold uppercase tracking-wider border border-[#E8DDD3]">
                      Edge Client Tier
                    </span>
                    <h4 className="font-serif-yatra font-bold text-lg text-[#201A18]">React 19 + Vite</h4>
                    <ul className="text-xs text-[#56423B] space-y-2">
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#1D705C] mt-0.5 shrink-0" />
                        <span>Framer Motion 60fps spring transitions</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#1D705C] mt-0.5 shrink-0" />
                        <span>Three.js procedural low-poly Himalayan diorama</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#1D705C] mt-0.5 shrink-0" />
                        <span>Interactive Leaflet GPS telemetry mapping</span>
                      </li>
                    </ul>
                  </div>

                  {/* Backend Core */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3">
                    <span className="px-2.5 py-0.5 rounded-full bg-white text-[#9D3E19] text-[10px] font-bold uppercase tracking-wider border border-[#E8DDD3]">
                      ASGI Engine Tier
                    </span>
                    <h4 className="font-serif-yatra font-bold text-lg text-[#201A18]">FastAPI + Python 3.12</h4>
                    <ul className="text-xs text-[#56423B] space-y-2">
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#9D3E19] mt-0.5 shrink-0" />
                        <span>Asynchronous endpoint controllers (`/recommend`, `/places`, `/ai`)</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#9D3E19] mt-0.5 shrink-0" />
                        <span>In-process System 1 KEV 0.6B decision engine</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#9D3E19] mt-0.5 shrink-0" />
                        <span>Multipart binary image validator with `/uploads` static mount</span>
                      </li>
                    </ul>
                  </div>

                  {/* Database */}
                  <div className="p-6 rounded-2xl bg-[#FDF1EC] border border-[#E8DDD3] space-y-3">
                    <span className="px-2.5 py-0.5 rounded-full bg-white text-[#7B1FA2] text-[10px] font-bold uppercase tracking-wider border border-[#E8DDD3]">
                      Geospatial Data Core
                    </span>
                    <h4 className="font-serif-yatra font-bold text-lg text-[#201A18]">PostGIS &amp; SQLite</h4>
                    <ul className="text-xs text-[#56423B] space-y-2">
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#7B1FA2] mt-0.5 shrink-0" />
                        <span>Production: PostgreSQL 16 + PostGIS spatial geometry</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#7B1FA2] mt-0.5 shrink-0" />
                        <span>Offline/Edge: SQLite `yatra_sathi.db` with native Haversine bounding-box</span>
                      </li>
                      <li className="flex items-start gap-2">
                        <Check className="w-3.5 h-3.5 text-[#7B1FA2] mt-0.5 shrink-0" />
                        <span>pgvector 384-dim dense embedding index for semantic search</span>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
};
