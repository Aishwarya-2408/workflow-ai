import React from "react";
import { User, Workflow, Menu, LogOut } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";

interface WorkflowHeaderProps {
  userName?: string;
  userAvatar?: string;
  onProfileClick?: () => void;
  onMenuClick?: () => void;
  onLogoutClick?: () => void;
}

const WorkflowHeader: React.FC<WorkflowHeaderProps> = ({
  userName = "GD - R&D",
  userAvatar = "",
  onProfileClick = () => {},
  onMenuClick = () => {},
  onLogoutClick = () => {},
}) => {
  // Extract initials for avatar fallback
  const getInitials = (name: string) => {
    return name
      .split(" ")
      .map((n) => n[0])
      .join("")
      .toUpperCase();
  };

  const userInitials = getInitials(userName);

  return (
    <header className="w-full h-16 px-4 md:px-6 bg-white border-b border-gray-200 flex items-center justify-between shadow-sm flex-shrink-0 z-10">
      <div className="flex items-center">
        <Button variant="ghost" size="icon" className="mr-2" onClick={onMenuClick}>
          <Menu className="h-6 w-6" />
        </Button>
        <div className="w-8 h-8 rounded-md bg-blue-600 flex items-center justify-center mr-3">
          <Workflow size={20} className="text-white" />
        </div>
        <h1 className="text-lg font-semibold text-gray-800 hidden md:block">GenAI Workflow System</h1>
      </div>

      <div className="flex items-center">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" className="relative h-10 w-10 rounded-full">
              <Avatar className="h-8 w-8">
                {userAvatar ? (
                  <AvatarImage src={userAvatar} alt={userName} />
                ) : null}
                <AvatarFallback className="bg-blue-100 text-blue-800 text-xs">
                  {userInitials}
                </AvatarFallback>
              </Avatar>
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel>My Account</DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onProfileClick} className="cursor-pointer">
              <User className="mr-2 h-4 w-4" />
              <span>{userName}</span>
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onLogoutClick} className="cursor-pointer text-red-600 hover:!text-red-600 hover:!bg-red-50">
              <LogOut className="mr-2 h-4 w-4" />
              <span>Log out</span>
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  );
};

export default WorkflowHeader;
