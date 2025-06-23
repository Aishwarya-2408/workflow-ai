import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { ScrollArea } from "@/components/ui/scroll-area";

interface MessageDetailModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  message: string;
}

export function MessageDetailModal({ isOpen, onClose, title, message }: MessageDetailModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent className="max-w-2xl max-h-[80vh]">
        <DialogHeader>
          <DialogTitle>{title}</DialogTitle>
          <DialogDescription>
            Full message details
          </DialogDescription>
        </DialogHeader>
        <ScrollArea className="max-h-[60vh] w-full rounded-md border p-4">
          <div className="whitespace-pre-wrap text-sm">
            {message}
          </div>
        </ScrollArea>
      </DialogContent>
    </Dialog>
  );
} 