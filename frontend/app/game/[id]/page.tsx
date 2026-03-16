"use client";

import { useEffect, useState, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Image from "next/image";
import { useRouter } from "next/navigation";

export const runtime = "edge";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface Actor {
  name: string;
  id: number;
  profile_url: string | null;
}

interface Move {
  from_actor: string;
  movie: string;
  to_actor: string;
  movie_title: string | null;
  movie_year: string | null;
  poster_url: string | null;
  backdrop_url: string | null;
}

interface GameState {
  id: string;
  start_actor: Actor;
  end_actor: Actor;
  difficulty: string;
  min_moves: number;
  current_actor: Actor;
  moves: Move[];
  status: "in_progress" | "won";
}

function FilmFrame({ children }: { children: React.ReactNode }) {
  return (
    <div className="relative">
      {/* Sprocket holes */}
      <div className="absolute -left-5 top-0 bottom-0 flex flex-col justify-around py-1 gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="w-3 h-3 rounded-sm bg-black border border-white/10" />
        ))}
      </div>
      <div className="absolute -right-5 top-0 bottom-0 flex flex-col justify-around py-1 gap-1">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="w-3 h-3 rounded-sm bg-black border border-white/10" />
        ))}
      </div>
      {children}
    </div>
  );
}

function MoveCard({ move, index }: { move: Move; index: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.05 }}
      className="flex items-center gap-3 bg-cinema-card border border-white/5 p-3 rounded-sm"
    >
      {move.poster_url ? (
        <Image
          src={move.poster_url}
          alt={move.movie_title ?? ""}
          width={36}
          height={54}
          className="object-cover rounded-sm flex-shrink-0"
        />
      ) : (
        <div className="w-9 h-14 bg-white/5 rounded-sm flex-shrink-0 flex items-center justify-center">
          <span className="text-white/20 text-xs">?</span>
        </div>
      )}
      <div className="min-w-0 text-xs leading-relaxed">
        <span className="text-white/50">{move.from_actor}</span>
        <span className="text-cinema-gold mx-1.5">→</span>
        <span className="text-white font-medium italic">
          {move.movie_title ?? move.movie}
        </span>
        {move.movie_year && (
          <span className="text-white/30 ml-1">({move.movie_year})</span>
        )}
        <span className="text-cinema-gold mx-1.5">→</span>
        <span className="text-white/50">{move.to_actor}</span>
      </div>
    </motion.div>
  );
}

export default function GamePage({ params }: { params: { id: string } }) {
  const [game, setGame] = useState<GameState | null>(null);
  const [movie, setMovie] = useState("");
  const [nextActor, setNextActor] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [backdrop, setBackdrop] = useState<string | null>(null);
  const [flashTitle, setFlashTitle] = useState<string | null>(null);
  const movieRef = useRef<HTMLInputElement>(null);
  const router = useRouter();

  useEffect(() => {
    fetch(`${API}/game/${params.id}`)
      .then((r) => r.json())
      .then(setGame);
  }, [params.id]);

  // Focus movie input when game loads
  useEffect(() => {
    if (game?.status === "in_progress") movieRef.current?.focus();
  }, [game?.id, game?.status]);

  async function submitMove(e: React.FormEvent) {
    e.preventDefault();
    if (!game || loading) return;
    setLoading(true);
    setError(null);

    try {
      const res = await fetch(`${API}/game/${params.id}/move`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ movie, next_actor: nextActor }),
      });
      const data = await res.json();

      if (!data.valid) {
        setError(data.explanation);
      } else {
        // Reveal backdrop
        if (data.backdrop_url) {
          setBackdrop(data.backdrop_url);
          setFlashTitle(data.movie_title ?? movie);
        }

        const move: Move = {
          from_actor: game.current_actor.name,
          movie,
          to_actor: nextActor,
          movie_title: data.movie_title,
          movie_year: data.movie_year,
          poster_url: data.poster_url,
          backdrop_url: data.backdrop_url,
        };

        setGame((g) =>
          g
            ? {
                ...g,
                current_actor: data.current_actor,
                moves: [...g.moves, move],
                status: data.game_status,
              }
            : g
        );
        setMovie("");
        setNextActor("");
        setTimeout(() => movieRef.current?.focus(), 50);
      }
    } finally {
      setLoading(false);
    }
  }

  if (!game) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <motion.p
          animate={{ opacity: [0.3, 1, 0.3] }}
          transition={{ repeat: Infinity, duration: 1.5 }}
          className="text-cinema-silver/50 text-xs tracking-[0.4em] uppercase"
        >
          Loading...
        </motion.p>
      </div>
    );
  }

  const won = game.status === "won";

  return (
    <main className="min-h-screen flex flex-col">
      {/* Backdrop */}
      <AnimatePresence mode="wait">
        {backdrop && (
          <motion.div
            key={backdrop}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 1.4 }}
            className="fixed inset-0 z-0"
          >
            <Image
              src={backdrop}
              alt=""
              fill
              className="object-cover"
              priority
            />
            <div className="absolute inset-0 bg-gradient-to-t from-cinema-black via-cinema-black/85 to-cinema-black/60" />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Movie title flash on correct move */}
      <AnimatePresence>
        {flashTitle && (
          <motion.div
            key={flashTitle}
            initial={{ opacity: 0, y: -8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.4 }}
            onAnimationComplete={() => setTimeout(() => setFlashTitle(null), 2000)}
            className="fixed top-16 left-0 right-0 z-30 flex justify-center"
          >
            <span className="bg-cinema-gold text-black text-xs font-bold px-4 py-1.5 tracking-widest uppercase">
              ✓ {flashTitle}
            </span>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Letterbox */}
      <div className="fixed top-0 left-0 right-0 h-12 bg-black z-20 flex items-center px-5">
        <button
          onClick={() => router.push("/")}
          className="text-cinema-silver/40 text-xs tracking-widest hover:text-cinema-silver transition-colors uppercase"
        >
          ← Exit
        </button>
        <div className="ml-auto flex items-center gap-4 text-xs text-cinema-silver/40 uppercase tracking-widest">
          <span>{game.difficulty}</span>
          <span>{game.moves.length} move{game.moves.length !== 1 ? "s" : ""}</span>
        </div>
      </div>
      <div className="fixed bottom-0 left-0 right-0 h-12 bg-black z-20" />

      {/* Scanlines */}
      <div className="fixed inset-0 pointer-events-none z-10 scanlines" />

      <div className="relative z-10 flex flex-col px-8 pt-20 pb-20 max-w-xl mx-auto w-full">

        {/* Objective card */}
        <motion.div
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="mb-8"
        >
          <FilmFrame>
            <div className="border border-white/10 bg-cinema-card/80 backdrop-blur-sm px-6 py-5 mx-6">
              <p className="text-cinema-silver/40 text-xs tracking-[0.3em] uppercase text-center mb-4">
                Connect
              </p>
              <div className="flex items-center justify-between gap-3">
                <div className="text-center flex-1">
                  <p className="text-cinema-gold font-bold text-base leading-tight">
                    {game.start_actor.name}
                  </p>
                  <p className="text-white/30 text-xs mt-0.5">Start</p>
                </div>
                <div className="flex flex-col items-center gap-1">
                  {Array.from({ length: game.min_moves }).map((_, i) => (
                    <div
                      key={i}
                      className={`w-5 h-px ${
                        i < game.moves.length ? "bg-cinema-gold" : "bg-white/20"
                      }`}
                    />
                  ))}
                  <p className="text-white/20 text-xs mt-1">
                    {game.min_moves} hop{game.min_moves !== 1 ? "s" : ""}
                  </p>
                </div>
                <div className="text-center flex-1">
                  <p className="text-white font-bold text-base leading-tight">
                    {game.end_actor.name}
                  </p>
                  <p className="text-white/30 text-xs mt-0.5">End</p>
                </div>
              </div>
            </div>
          </FilmFrame>
        </motion.div>

        {/* Move chain */}
        <AnimatePresence>
          {game.moves.length > 0 && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="mb-6 space-y-2"
            >
              {game.moves.map((m, i) => (
                <MoveCard key={i} move={m} index={i} />
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Win state */}
        {won ? (
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 20 }}
            className="text-center py-8"
          >
            <motion.p
              animate={{ opacity: [0.7, 1, 0.7] }}
              transition={{ repeat: Infinity, duration: 2 }}
              className="text-cinema-gold text-3xl font-bold tracking-tight mb-2"
            >
              ★ Scene Complete ★
            </motion.p>
            <p className="text-cinema-silver/60 text-sm mb-1">
              {game.moves.length} move{game.moves.length !== 1 ? "s" : ""} &nbsp;·&nbsp;{" "}
              {game.difficulty}
            </p>
            <p className="text-white/40 text-xs mb-8">
              {game.start_actor.name} → {game.end_actor.name}
            </p>
            <motion.button
              whileHover={{ scale: 1.03 }}
              whileTap={{ scale: 0.97 }}
              onClick={() => router.push("/")}
              className="px-8 py-3 border border-cinema-gold text-cinema-gold text-xs uppercase tracking-widest hover:bg-cinema-gold hover:text-black transition-all"
            >
              New Film
            </motion.button>
          </motion.div>
        ) : (
          <>
            {/* Current actor indicator */}
            <motion.div
              key={game.current_actor.name}
              initial={{ opacity: 0, x: -8 }}
              animate={{ opacity: 1, x: 0 }}
              className="mb-5"
            >
              <p className="text-white/30 text-xs tracking-widest uppercase mb-1">Now with</p>
              <p className="text-cinema-gold text-xl font-bold">{game.current_actor.name}</p>
            </motion.div>

            {/* Move form */}
            <form onSubmit={submitMove} className="space-y-3">
              <div>
                <label className="block text-xs text-white/30 tracking-widest uppercase mb-1.5">
                  A movie featuring {game.current_actor.name.split(" ")[0]}
                </label>
                <input
                  ref={movieRef}
                  type="text"
                  value={movie}
                  onChange={(e) => setMovie(e.target.value)}
                  placeholder="e.g. The Dark Knight"
                  className="w-full bg-cinema-card border border-white/10 px-4 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-cinema-gold/60 transition-colors"
                  required
                  disabled={loading}
                />
              </div>

              <div>
                <label className="block text-xs text-white/30 tracking-widest uppercase mb-1.5">
                  A co-star in that movie
                </label>
                <input
                  type="text"
                  value={nextActor}
                  onChange={(e) => setNextActor(e.target.value)}
                  placeholder="e.g. Heath Ledger"
                  className="w-full bg-cinema-card border border-white/10 px-4 py-3 text-sm text-white placeholder-white/20 focus:outline-none focus:border-cinema-gold/60 transition-colors"
                  required
                  disabled={loading}
                />
              </div>

              <AnimatePresence>
                {error && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    className="overflow-hidden"
                  >
                    <p className="text-red-400/80 text-xs leading-relaxed py-1 border-l-2 border-red-500/40 pl-3">
                      {error}
                    </p>
                  </motion.div>
                )}
              </AnimatePresence>

              <motion.button
                whileHover={{ scale: 1.01 }}
                whileTap={{ scale: 0.99 }}
                type="submit"
                disabled={loading || !movie.trim() || !nextActor.trim()}
                className="w-full py-4 bg-cinema-gold text-black font-bold text-xs uppercase tracking-[0.3em] disabled:opacity-30 transition-opacity"
              >
                {loading ? (
                  <span className="flex items-center justify-center gap-2">
                    <span className="animate-spin inline-block w-3 h-3 border border-black border-t-transparent rounded-full" />
                    Checking...
                  </span>
                ) : (
                  "Submit Move"
                )}
              </motion.button>
            </form>
          </>
        )}
      </div>
    </main>
  );
}
