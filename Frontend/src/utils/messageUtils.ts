export interface TruncatedMessage {
  truncated: string;
  full: string;
  needsTruncation: boolean;
}

/**
 * Truncates a message to a specified character limit, preferring word boundaries
 * @param message - The full message to truncate
 * @param limit - Character limit (default: 150)
 * @returns Object containing truncated message, full message, and whether truncation was needed
 */
export function truncateMessage(message: string, limit: number = 150): TruncatedMessage {
  if (!message || message.length <= limit) {
    return {
      truncated: message,
      full: message,
      needsTruncation: false,
    };
  }

  // Find the last space before the limit to avoid cutting words
  let truncateAt = limit;
  const lastSpaceIndex = message.lastIndexOf(' ', limit);
  
  if (lastSpaceIndex > limit * 0.8) { // Only use word boundary if it's not too far back
    truncateAt = lastSpaceIndex;
  }

  const truncated = message.substring(0, truncateAt).trim() + '...';
  
  return {
    truncated,
    full: message,
    needsTruncation: true,
  };
}

/**
 * Formats a message for better display in modal
 * @param message - The message to format
 * @returns Formatted message with proper line breaks
 */
export function formatMessageForModal(message: string): string {
  // Preserve existing line breaks and add proper spacing
  return message
    .replace(/\n\n/g, '\n\n') // Preserve double line breaks
    .replace(/\n/g, '\n') // Preserve single line breaks
    .trim();
} 