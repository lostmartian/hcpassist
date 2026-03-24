import ChatInterface from "@/components/chat-interface";
import { MolecularBackground } from "@/components/molecular-background";

export default function Home() {
  return (
    <div className="flex-1 flex flex-col min-h-screen bg-[#FBFDFF] text-slate-900 relative">
      <MolecularBackground />
      <ChatInterface />
    </div>
  );
}
