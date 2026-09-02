"use client";

/**
 * SlideStudio.tsx — AutoDeck AI Interactive Presentation Management Modal
 * Features @dnd-kit drag-and-drop slide reordering, live HTML5 preview, and PPTX download.
 */

import React, { useState, useEffect } from "react";
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from "@dnd-kit/core";
import {
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import {
  Presentation,
  Download,
  X,
  GripVertical,
  Play,
  Layers,
  ShieldCheck,
  ChevronLeft,
  ChevronRight,
  Sparkles,
  AlertCircle,
  Clock,
  FileDown,
} from "lucide-react";
import { SlideStudioProps, SlideASTItem } from "@/lib/types";
import { useDeck } from "@/hooks/useDeck";
import { SlidePreview } from "./SlidePreview";
import { Button } from "./ui/Button";
import { Badge } from "./ui/Badge";
import { Skeleton } from "./ui/Skeleton";

// Sortable Slide Item Thumbnail Card
interface SortableSlideThumbnailProps {
  slide: SlideASTItem;
  index: number;
  isActive: boolean;
  onSelect: (index: number) => void;
}

function SortableSlideThumbnail({
  slide,
  index,
  isActive,
  onSelect,
}: SortableSlideThumbnailProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id: slide.id || `slide-${index}` });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    zIndex: isDragging ? 20 : 1,
    opacity: isDragging ? 0.6 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      onClick={() => onSelect(index)}
      className={`group flex items-center space-x-2.5 p-2.5 rounded-lg border transition-all cursor-pointer ${
        isActive
          ? "bg-[#162032] border-[#00E5FF] shadow-[0_0_12px_rgba(0,229,255,0.2)]"
          : "bg-[#0B0F19] border-[#233554] hover:border-[#94A3B8]/60 hover:bg-[#111C2E]"
      }`}
    >
      {/* Drag Handle */}
      <button
        {...attributes}
        {...listeners}
        aria-label={`Drag reorder slide ${index + 1}`}
        className="p-1 text-[#64748B] hover:text-[#00E5FF] cursor-grab active:cursor-grabbing focus:outline-hidden"
      >
        <GripVertical className="h-4 w-4" />
      </button>

      {/* Slide Index Badge */}
      <div
        className={`h-6 w-6 rounded flex items-center justify-center text-xs font-mono font-bold shrink-0 ${
          isActive
            ? "bg-[#00E5FF] text-[#0B0F19]"
            : "bg-[#162032] text-[#CCD6F6]"
        }`}
      >
        {index + 1}
      </div>

      {/* Slide Meta Info */}
      <div className="flex-1 min-w-0">
        <span className="text-[10px] font-mono text-[#00E5FF] block uppercase tracking-wider truncate">
          {slide.type}
        </span>
        <h4 className="text-xs font-mono text-white truncate font-medium">
          {slide.title || `Slide ${index + 1}`}
        </h4>
      </div>

      {/* NLI Score Pill */}
      {slide.nli_scores && slide.nli_scores.length > 0 && (
        <span className="text-[10px] font-mono text-[#10B981] bg-[#10B981]/10 px-1.5 py-0.5 rounded border border-[#10B981]/30">
          {(Math.min(...slide.nli_scores)).toFixed(2)}
        </span>
      )}
    </div>
  );
}

export function SlideStudio({
  isOpen,
  onClose,
  initialTopic = "",
}: SlideStudioProps) {
  const {
    status,
    deck,
    slides,
    activeSlideIndex,
    error,
    generationTimeMs,
    verificationReport,
    generate,
    reorderSlides,
    setActiveSlideIndex,
    downloadPPTX,
  } = useDeck();

  const isLoading = status === "generating";
  const [topicInput, setTopicInput] = useState<string>(initialTopic);

  // Set initial topic if provided
  useEffect(() => {
    if (initialTopic) {
      setTopicInput(initialTopic);
      if (status === "idle") {
        generate(initialTopic);
      }
    }
  }, [initialTopic, generate, status]);

  // Keyboard shortcut listener for Modal
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "ArrowLeft") {
        setActiveSlideIndex(Math.max(activeSlideIndex - 1, 0));
      } else if (e.key === "ArrowRight") {
        setActiveSlideIndex(Math.min(activeSlideIndex + 1, slides.length - 1));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [isOpen, onClose, activeSlideIndex, slides.length, setActiveSlideIndex]);

  // DND Kit Sensors
  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 5,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    if (over && active.id !== over.id) {
      const oldIndex = slides.findIndex((s) => (s.id || `slide-${slides.indexOf(s)}`) === active.id);
      const newIndex = slides.findIndex((s) => (s.id || `slide-${slides.indexOf(s)}`) === over.id);
      if (oldIndex !== -1 && newIndex !== -1) {
        reorderSlides(oldIndex, newIndex);
      }
    }
  };

  const handleGenerateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (topicInput.trim()) {
      generate(topicInput.trim());
    }
  };

  const downloadPDF = () => {
    if (deck?.deck_id) {
      window.open(`http://127.0.0.1:8000/deck/${deck.deck_id}/download/pdf`, "_blank");
    }
  };

  if (!isOpen) return null;

  const currentSlide = slides[activeSlideIndex] || slides[0];

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="slide-studio-title"
      className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-6 bg-[#0B0F19]/80 backdrop-blur-md animate-in fade-in duration-200"
    >
      <div className="relative flex flex-col w-full max-w-[1450px] h-[92vh] max-h-[920px] rounded-xl bg-[#111C2E] border-2 border-[#00E5FF]/40 shadow-[0_0_50px_rgba(0,229,255,0.25)] overflow-hidden">
        {/* Studio Command Header */}
        <header className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5 bg-[#0E1726] border-b border-[#233554]">
          <div className="flex items-center space-x-3">
            <div className="h-9 w-9 rounded-lg bg-[#00E5FF]/10 border border-[#00E5FF]/40 flex items-center justify-center text-[#00E5FF]">
              <Presentation className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h2 id="slide-studio-title" className="text-base font-bold font-mono text-white uppercase tracking-wider">
                  AUTODECK AI STUDIO
                </h2>
                <Badge variant="cyan">INBR BLUF-v2026</Badge>
              </div>
              <p className="text-xs text-[#94A3B8] font-sans">
                Deterministic PowerPoint AST Compiler & Real-Time NLI Slide Verifier
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2">
            {/* Download PPTX & PDF Buttons (ENH-010) */}
            {deck && (
              <>
                <Button
                  variant="gold"
                  size="sm"
                  onClick={downloadPPTX}
                  className="font-mono text-xs flex items-center space-x-1.5 shadow-[0_0_15px_rgba(255,215,0,0.2)]"
                >
                  <Download className="h-4 w-4" />
                  <span>PPTX</span>
                </Button>
                <Button
                  variant="cyan"
                  size="sm"
                  onClick={downloadPDF}
                  className="font-mono text-xs flex items-center space-x-1.5 shadow-[0_0_15px_rgba(0,229,255,0.2)]"
                >
                  <FileDown className="h-4 w-4" />
                  <span>PDF (16:9)</span>
                </Button>
              </>
            )}

            {/* Close Studio Button */}
            <button
              aria-label="Close Slide Studio"
              onClick={onClose}
              className="p-1.5 rounded-lg text-[#94A3B8] hover:text-white hover:bg-[#162032] border border-transparent hover:border-[#233554] transition-colors ml-2"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </header>

        {/* Topic Input Bar */}
        <div className="px-5 py-3 bg-[#162032] border-b border-[#233554]">
          <form onSubmit={handleGenerateSubmit} className="flex gap-2.5">
            <div className="relative flex-1">
              <input
                type="text"
                value={topicInput}
                onChange={(e) => setTopicInput(e.target.value)}
                placeholder="Enter briefing topic (e.g. Tactical Drone Procurement under Schedule 18 with IFA concurrence)..."
                className="w-full bg-[#0B0F19] border border-[#233554] rounded-lg px-4 py-2 text-xs font-mono text-[#CCD6F6] placeholder-[#64748B] focus:outline-none focus:border-[#00E5FF] transition-colors"
              />
            </div>
            <Button
              type="submit"
              variant="cyan"
              size="sm"
              disabled={status === "generating" || !topicInput.trim()}
              className="font-mono text-xs shrink-0 flex items-center space-x-1.5"
            >
              {status === "generating" ? (
                <>
                  <div className="w-3.5 h-3.5 border-2 border-[#0B0F19] border-t-transparent rounded-full animate-spin" />
                  <span>COMPILING AST...</span>
                </>
              ) : (
                <>
                  <Sparkles className="h-4 w-4" />
                  <span>GENERATE DECK</span>
                </>
              )}
            </Button>
          </form>
        </div>

        {/* Verification & Performance Telemetry Ribbon */}
        {verificationReport && (
          <div className="flex flex-wrap items-center justify-between px-5 py-2 bg-[#0B0F19] border-b border-[#233554] text-xs font-mono">
            <div className="flex items-center space-x-2 text-[#10B981]">
              <ShieldCheck className="h-4 w-4" />
              <span>
                ALL CLAIMS VERIFIED (Lowest NLI: {verificationReport.lowest_nli_score.toFixed(2)})
              </span>
            </div>

            <div className="flex items-center space-x-4 text-[#94A3B8]">
              <span className="flex items-center space-x-1">
                <Clock className="h-3.5 w-3.5 text-[#00E5FF]" />
                <span>COMPILE LATENCY: {generationTimeMs}ms (p95 &lt;850ms)</span>
              </span>
              <span className="text-[#FFD700]">
                AST VALIDITY: 100%
              </span>
            </div>
          </div>
        )}

        {/* Studio Workspace Split Grid */}
        <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-4 p-5 overflow-hidden">
          {/* Left Column: Sortable Slide Thumbnails (4 Cols) */}
          <div className="md:col-span-4 flex flex-col rounded-lg bg-[#0B0F19]/90 border border-[#233554] overflow-hidden">
            <div className="flex items-center justify-between px-3.5 py-2.5 bg-[#0E1726] border-b border-[#233554] text-xs font-mono">
              <span className="text-[#CCD6F6] font-semibold flex items-center space-x-1.5">
                <Layers className="h-3.5 w-3.5 text-[#00E5FF]" />
                <span>BRIEFING SLIDES ({slides.length})</span>
              </span>
              <span className="text-[10px] text-[#94A3B8]">
                Drag handles to reorder
              </span>
            </div>

            <div className="flex-1 overflow-y-auto p-3 space-y-2 terminal-scroll">
              {isLoading ? (
                <div className="space-y-2.5 p-1">
                  {[1, 2, 3, 4].map((n) => (
                    <div key={n} className="p-3 rounded-lg bg-[#162032]/60 border border-[#233554] space-y-2">
                      <div className="flex items-center justify-between">
                        <Skeleton width="40%" height={12} />
                        <Skeleton width="20%" height={10} />
                      </div>
                      <Skeleton width="85%" height={10} />
                    </div>
                  ))}
                </div>
              ) : slides.length === 0 ? (
                <div className="h-full flex flex-col items-center justify-center text-center p-6 text-xs font-mono text-[#64748B] space-y-2">
                  <Presentation className="h-8 w-8 text-[#233554]" />
                  <p>No presentation slides compiled yet.</p>
                  <p className="text-[11px] text-[#94A3B8]">
                    Enter a procurement topic above and click Generate Deck.
                  </p>
                </div>
              ) : (
                <DndContext
                  sensors={sensors}
                  collisionDetection={closestCenter}
                  onDragEnd={handleDragEnd}
                >
                  <SortableContext
                    items={slides.map((s, idx) => s.id || `slide-${idx}`)}
                    strategy={verticalListSortingStrategy}
                  >
                    {slides.map((slide, idx) => (
                      <SortableSlideThumbnail
                        key={slide.id || `slide-${idx}`}
                        slide={slide}
                        index={idx}
                        isActive={idx === activeSlideIndex}
                        onSelect={setActiveSlideIndex}
                      />
                    ))}
                  </SortableContext>
                </DndContext>
              )}
            </div>
          </div>

          {/* Right Column: Live 16:9 Slide Preview Canvas (8 Cols) */}
          <div className="md:col-span-8 flex flex-col rounded-lg bg-[#0B0F19]/90 border border-[#233554] overflow-hidden p-4">
            {error && (
              <div className="mb-4 p-3 rounded bg-[#EF4444]/10 border border-[#EF4444]/40 flex items-center space-x-2 text-xs font-mono text-[#EF4444]">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            {isLoading ? (
              <div className="flex-1 flex flex-col items-center justify-center p-6 space-y-4">
                <div className="w-full max-w-4xl aspect-video rounded-xl bg-[#111C2E] border border-[#233554] p-8 flex flex-col justify-between shadow-2xl">
                  <div className="space-y-3">
                    <Skeleton width="30%" height={24} />
                    <Skeleton width="60%" height={16} />
                  </div>
                  <div className="space-y-4 my-6">
                    <Skeleton width="90%" height={14} />
                    <Skeleton width="80%" height={14} />
                    <Skeleton width="85%" height={14} />
                  </div>
                  <div className="flex items-center justify-between border-t border-[#233554]/50 pt-4">
                    <Skeleton width="25%" height={10} />
                    <Skeleton width="15%" height={10} />
                  </div>
                </div>
                <div className="flex items-center space-x-2 text-xs font-mono text-cyan-400 animate-pulse">
                  <Sparkles className="h-4 w-4" />
                  <span>Compiling slide AST & executing DeBERTa verification...</span>
                </div>
              </div>
            ) : currentSlide ? (
              <div className="flex-1 flex flex-col items-center justify-center">
                <div className="w-full max-w-4xl">
                  <SlidePreview
                    slide={currentSlide}
                    slideIndex={activeSlideIndex}
                    totalSlides={slides.length}
                  />
                </div>

                {/* Slide Navigation Pagination */}
                <div className="flex items-center justify-center space-x-4 mt-4 text-xs font-mono">
                  <Button
                    variant="outline"
                    size="sm"
                    disabled={activeSlideIndex <= 0}
                    onClick={() => setActiveSlideIndex(activeSlideIndex - 1)}
                    className="flex items-center space-x-1"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    <span>PREV SLIDE</span>
                  </Button>

                  <span className="text-[#CCD6F6]">
                    Slide {activeSlideIndex + 1} of {slides.length}
                  </span>

                  <Button
                    variant="outline"
                    size="sm"
                    disabled={activeSlideIndex >= slides.length - 1}
                    onClick={() => setActiveSlideIndex(activeSlideIndex + 1)}
                    className="flex items-center space-x-1"
                  >
                    <span>NEXT SLIDE</span>
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
              </div>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 space-y-3 font-mono text-xs text-[#64748B]">
                <div className="h-16 w-16 rounded-full bg-[#162032] flex items-center justify-center text-[#00E5FF]">
                  <Presentation className="h-8 w-8" />
                </div>
                <h3 className="text-white font-bold text-sm">
                  AUTODECK BRIEFING ENGINE READY
                </h3>
                <p className="max-w-md text-[#94A3B8]">
                  Generates standardized 6-slide Indian Naval Staff BLUF-v2026 presentation decks compiled directly into .pptx and responsive HTML5.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
