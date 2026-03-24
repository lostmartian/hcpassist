"use client";

import ReactMarkdown, { Components } from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

interface MarkdownRendererProps {
  content: string;
  className?: string;
}

const components: Components = {
  p: ({ children }) => (
    <p className="mb-3 last:mb-0 leading-relaxed text-black">{children}</p>
  ),
  ul: ({ children }) => (
    <ul className="mb-4 list-disc list-inside space-y-1">{children}</ul>
  ),
  ol: ({ children }) => (
    <ol className="mb-4 list-decimal list-inside space-y-1">{children}</ol>
  ),
  li: ({ children }) => (
    <li className="text-black px-1">{children}</li>
  ),
  h1: ({ children }) => <h1 className="text-xl font-bold mb-4 text-black tracking-tight">{children}</h1>,
  h2: ({ children }) => <h2 className="text-lg font-bold mb-3 text-black tracking-tight">{children}</h2>,
  h3: ({ children }) => <h3 className="text-base font-bold mb-2 text-black tracking-tight">{children}</h3>,
  strong: ({ children }) => <strong className="font-bold text-black">{children}</strong>,
  em: ({ children }) => <em className="italic text-black">{children}</em>,
  table: ({ children }) => (
    <div className="my-8 overflow-x-auto bg-white/50 rounded-xl ring-1 ring-slate-100">
      <table className="w-full text-left text-xs sm:text-sm border-collapse">
        {children}
      </table>
    </div>
  ),
  thead: ({ children }) => (
    <thead className="bg-slate-50">
      {children}
    </thead>
  ),
  th: ({ children }) => (
    <th className="px-6 py-4 font-bold text-slate-500 uppercase tracking-widest text-[9px]">
      {children}
    </th>
  ),
  td: ({ children }) => (
    <td className="px-6 py-4 border-t border-slate-100 text-black">
      {children}
    </td>
  ),
};

export function MarkdownRenderer({ content, className }: MarkdownRendererProps) {
  return (
    <div className={cn("max-w-none break-words text-black", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
