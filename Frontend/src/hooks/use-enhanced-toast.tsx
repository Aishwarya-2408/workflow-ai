import React, { useState, useCallback } from "react";
import { useToast } from "./use-toast";
import { truncateMessage, formatMessageForModal } from "@/utils/messageUtils";
import { EnhancedToastDescription } from "@/components/ui/enhanced-toast";

interface EnhancedToastOptions {
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
  duration?: number;
  truncateLimit?: number;
}

interface ModalState {
  isOpen: boolean;
  title: string;
  message: string;
}

export function useEnhancedToast() {
  const { toast, dismiss, toasts } = useToast();
  const [modalState, setModalState] = useState<ModalState>({
    isOpen: false,
    title: "",
    message: "",
  });

  const showModal = useCallback((title: string, message: string) => {
    setModalState({
      isOpen: true,
      title,
      message: formatMessageForModal(message),
    });
  }, []);

  const hideModal = useCallback(() => {
    setModalState(prev => ({ ...prev, isOpen: false }));
  }, []);

  const enhancedToast = useCallback((options: EnhancedToastOptions) => {
    const { title = "", description = "", variant = "default", duration, truncateLimit = 150 } = options;
    
    if (!description) {
      // If no description, use regular toast
      return toast({ title, description, variant, duration });
    }

    const { truncated, full, needsTruncation } = truncateMessage(description, truncateLimit);

    if (!needsTruncation) {
      // If no truncation needed, use regular toast
      return toast({ title, description, variant, duration });
    }

    // For truncated messages, use the enhanced description component
    return toast({
      title,
      description: (
        <EnhancedToastDescription
          message={full}
          onReadMore={() => showModal(title || "Message Details", full)}
          truncateLimit={truncateLimit}
        />
      ),
      variant,
      duration,
    });
  }, [toast, showModal]);

  return {
    toast: enhancedToast,
    dismiss,
    toasts,
    modalState,
    showModal,
    hideModal,
  };
} 