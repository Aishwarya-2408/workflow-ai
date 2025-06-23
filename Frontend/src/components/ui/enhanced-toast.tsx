import React from "react";
import { truncateMessage } from "@/utils/messageUtils";

interface EnhancedToastDescriptionProps {
  message: string;
  onReadMore: () => void;
  truncateLimit?: number;
}

export function EnhancedToastDescription({ 
  message, 
  onReadMore, 
  truncateLimit = 150 
}: EnhancedToastDescriptionProps) {
  const { truncated, needsTruncation } = truncateMessage(message, truncateLimit);

  if (!needsTruncation) {
    return <span>{message}</span>;
  }

  return (
    <div className="space-y-2">
      <div>{truncated}</div>
      <button
        onClick={(e) => {
          e.preventDefault();
          e.stopPropagation();
          onReadMore();
        }}
        className="text-sm text-blue-600 hover:text-blue-800 underline focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1 rounded transition-colors"
        type="button"
      >
        Read more
      </button>
    </div>
  );
} 