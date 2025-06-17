import React from "react";
import { motion } from "framer-motion";
import { BrainCircuit } from "lucide-react";
import { cn } from "@/lib/utils";

// Animated Brain Icon
const BrainAIIcon = ({ className = "" }) => (
  <motion.div
    className={cn("relative", className)}
    animate={{
      scale: [1, 1.1, 1],
      rotate: [0, 5, -5, 0],
    }}
    transition={{
      duration: 2,
      repeat: Infinity,
      repeatType: "reverse",
      ease: "easeInOut",
    }}
  >
    <motion.div
      className="absolute inset-0 rounded-full"
      animate={{
        background: [
          "radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)",
          "radial-gradient(circle, rgba(147, 51, 234, 0.3) 0%, transparent 70%)",
          "radial-gradient(circle, rgba(236, 72, 153, 0.3) 0%, transparent 70%)",
          "radial-gradient(circle, rgba(59, 130, 246, 0.3) 0%, transparent 70%)",
        ],
      }}
      transition={{
        duration: 3,
        repeat: Infinity,
        ease: "linear",
      }}
    />
    <motion.div
      animate={{
        filter: [
          "drop-shadow(0 0 4px rgba(59, 130, 246, 0.5))",
          "drop-shadow(0 0 8px rgba(147, 51, 234, 0.5))",
          "drop-shadow(0 0 6px rgba(236, 72, 153, 0.5))",
          "drop-shadow(0 0 4px rgba(59, 130, 246, 0.5))",
        ],
      }}
      transition={{
        duration: 2.5,
        repeat: Infinity,
        ease: "easeInOut",
      }}
    >
      <BrainCircuit className="w-4 h-4 relative z-10 !text-white" />
    </motion.div>
  </motion.div>
);

// Button
const BrainAIButton = ({ onClick, disabled }) => (
  <button
    onClick={onClick}
    disabled={disabled}
    className="inline-flex items-center justify-center h-10 px-6 py-2 rounded-md !bg-black !text-white shadow-lg transition-all duration-300 text-sm font-medium disabled:!bg-gray-700 disabled:!text-gray-400 disabled:cursor-not-allowed z-50 hover:!bg-gray-800 hover:!text-gray-200"
  >
    <BrainAIIcon className="mr-2" />
    AI Assist
  </button>
);

export default BrainAIButton; 