"use client";

import { useState, useRef, useEffect } from "react";
import { Send, User, Loader2, Sparkles, Activity } from "lucide-react";
import { cn } from "@/lib/utils";
import { motion, AnimatePresence } from "framer-motion";
import { sendMessage } from "@/actions/chat";
import { MarkdownRenderer } from "./markdown-renderer";

type Message = {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
};

export default function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: "1",
      role: "assistant",
      content: "Welcome to Aether. How can I assist with your clinical data analysis today?",
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages, isLoading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      const result = await sendMessage(userMessage.content);
      const assistantMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: result.response,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error("Failed to fetch:", error);
      const errorMessage: Message = {
        id: Date.now().toString(),
        role: "assistant",
        content: "I'm sorry, I'm having trouble reaching the clinical data server.",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-screen max-w-3xl mx-auto w-full px-6 transition-all duration-500 bg-transparent">
      {/* Header */}
      <header className="flex items-center justify-between py-12 shrink-0">
        <div className="flex items-center gap-5">
          <div className="w-10 h-10 rounded-full bg-indigo-50 flex items-center justify-center">
            <Activity className="text-indigo-600 w-5 h-5 stroke-[1.5]" />
          </div>
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-xl font-bold tracking-tight text-slate-900">Aether</h1>
              <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-600 text-[10px] font-bold uppercase tracking-widest">
                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse" />
                <span>Live</span>
              </span>
            </div>
            <p className="text-[10px] text-slate-600 font-bold uppercase tracking-[0.2em] mt-1.5">
              Clinical Intelligence OS
            </p>
          </div>
        </div>
      </header>

      {/* Chat Area - No Container box, just messages floating */}
      <main className="flex-1 overflow-hidden relative">
        <div 
          ref={scrollRef}
          className="h-full overflow-y-auto pb-10 space-y-12 scroll-smooth scrollbar-hide"
        >
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <motion.div
                key={msg.id}
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0 }}
                transition={{ duration: 0.5, ease: [0.19, 1, 0.22, 1] }}
                className={cn(
                  "flex w-full gap-6",
                  msg.role === "user" ? "flex-row-reverse" : "flex-row"
                )}
              >
                <div className={cn(
                  "w-8 h-8 rounded-full flex items-center justify-center shrink-0",
                  msg.role === "user" ? "bg-slate-100/80" : "bg-transparent"
                )}>
                  {msg.role === "user" ? <User className="w-4 h-4 text-slate-500" /> : <Sparkles className="w-4 h-4 text-indigo-500" />}
                </div>
                
                <div className={cn(
                  "max-w-[85%] text-[15px] leading-relaxed text-slate-900",
                  msg.role === "user" 
                    ? "font-medium bg-slate-100/50 px-6 py-4 rounded-[1.5rem]" 
                    : ""
                )}>
                  {msg.role === "assistant" ? (
                    <MarkdownRenderer content={msg.content} />
                  ) : (
                    <p>{msg.content}</p>
                  )}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>
          
          {isLoading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex gap-6"
            >
              <div className="w-8 h-8 rounded-full bg-transparent flex items-center justify-center shrink-0">
                <Loader2 className="w-4 h-4 text-indigo-500 animate-spin" />
              </div>
              <div className="text-[14px] text-slate-400 font-medium py-2">
                Synthesizing insights...
              </div>
            </motion.div>
          )}
        </div>
      </main>

      {/* Input Area - Minimalist, but with a shadow for discovery */}
      <footer className="pb-12 pt-4 shrink-0">
        <form 
          onSubmit={handleSubmit}
          className="relative group w-full"
        >
          <div className="flex items-center bg-white shadow-[0_20px_50px_rgba(0,0,0,0.04)] rounded-full px-6 py-2 ring-1 ring-slate-100/50 hover:ring-indigo-100 transition-all duration-300">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Query clinical metrics or pharma trends..."
              className="flex-1 bg-transparent py-4 text-[15px] font-medium text-slate-900 focus:outline-none placeholder:text-slate-300"
            />
            <button
              type="submit"
              disabled={!input.trim() || isLoading}
              className="p-3 text-indigo-500 hover:text-indigo-600 transition-all disabled:opacity-20 disabled:pointer-events-none active:scale-95"
            >
              <Send className="w-5 h-5" />
            </button>
          </div>
        </form>
        <p className="text-[10px] text-center mt-6 text-slate-400 font-bold tracking-[0.15em] uppercase opacity-50">
          Agentic Analytic Pipeline
        </p>
      </footer>
    </div>
  );
}
