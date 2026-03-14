"use client";

import { useState } from "react";
import { motion } from "framer-motion";
import { useRouter } from "next/navigation";

export const runtime = "edge";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

const DIFFICULTY_DESCRIPTIONS = {
  easy: "2 hops",
  medium: "3–5 hops",
  hard: "6+ hops",
};

export default function Home() {
  const [difficulty, setDifficulty] = useState<"easy" | "medium" | "hard">("medium");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  async function startGame() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API}/game/new?difficulty=${difficulty}`, { method: "POST" });
      if (!res.ok) throw new Error("Failed to generate puzzle");
      const data = await res.json();
      router.push(`/game/${data.game_id}`);
    } catch {
      setError("Couldn't load a puzzle. Please try again.");
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen flex flex-col items-center justify-center px-4 overflow-hidden">
      {/* Letterbox */}
      <div className="fixed top-0 left-0 right-0 h-14 bg-black z-20" />
      <div className="fixed bottom-0 left-0 right-0 h-14 bg-black z-20" />

      {/* Scanline overlay */}
      <div className="fixed inset-0 pointer-events-none z-10 scanlines" />

      <motion.div
        initial={{ opacity: 0, y: 24 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.9, ease: "easeOut" }}
        className="text-center w-full max-w-sm"
      >
        {/* Title */}
        <h1 className="text-6xl font-bold tracking-tighter mb-1 leading-none">
          CINEMA
        </h1>
        <h2 className="text-6xl font-bold tracking-tighter text-cinema-gold leading-none mb-6">
          GAME
        </h2>

        <p className="text-cinema-silver text-xs leading-relaxed mb-10 max-w-xs mx-auto">
          Connect two actors through shared movies.
          <br />
          Name the film, then name a co-star.
        </p>

        {/* Difficulty */}
        <div className="mb-8">
          <p className="text-cinema-silver/50 text-xs tracking-widest uppercase mb-3">Select difficulty</p>
          <div className="flex gap-2 justify-center">
            {(["easy", "medium", "hard"] as const).map((d) => (
              <button
                key={d}
                onClick={() => setDifficulty(d)}
                className={`flex-1 py-3 px-2 text-xs uppercase tracking-widest border transition-all duration-200 ${
                  difficulty === d
                    ? "border-cinema-gold text-cinema-gold bg-cinema-gold/10"
                    : "border-white/10 text-cinema-silver/60 hover:border-white/30 hover:text-cinema-silver"
                }`}
              >
                <span className="block">{d}</span>
                <span className="block text-[9px] mt-0.5 opacity-60 normal-case">
                  {DIFFICULTY_DESCRIPTIONS[d]}
                </span>
              </button>
            ))}
          </div>
        </div>

        {error && (
          <p className="text-red-400 text-xs mb-4">{error}</p>
        )}

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.97 }}
          onClick={startGame}
          disabled={loading}
          className="w-full py-4 bg-cinema-gold text-black font-bold text-sm uppercase tracking-[0.3em] disabled:opacity-40 transition-opacity"
        >
          {loading ? (
            <span className="flex items-center justify-center gap-2">
              <span className="animate-spin inline-block w-3 h-3 border border-black border-t-transparent rounded-full" />
              Casting...
            </span>
          ) : (
            "Roll Film"
          )}
        </motion.button>

        <p className="text-cinema-silver/30 text-xs mt-6 tracking-wider">
          Powered by TMDb &amp; Claude
        </p>
      </motion.div>
    </main>
  );
}
