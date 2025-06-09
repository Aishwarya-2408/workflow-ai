import React, { useState, useEffect } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Home, FileText, Image, LogOut } from 'lucide-react'; // Icons for navigation and LogOut icon
import WorkflowHeader from '../ExcelWorkflow/WorkflowHeader'; // Import the header

// Helper function to apply conditional classes for active NavLink
const getNavLinkClass = ({ isActive }: { isActive: boolean }): string => {
  return `
    flex items-center px-4 py-2 text-sm font-medium rounded-md transition-colors
    ${isActive
      ? 'bg-primary/10 text-primary'
      : 'text-gray-700 hover:bg-gray-100'
    }
  `;
};

interface SidebarProps {
  isOpen: boolean;
  onLinkClick?: () => void; // Optional: Close sidebar when a link is clicked on mobile
}

const Sidebar: React.FC<SidebarProps> = ({ isOpen, onLinkClick }) => {
  return (
    // Simplified: Toggle width and padding, added overflow-hidden
    <aside
      className={`
        flex-shrink-0 border-r bg-gray-50/50 flex flex-col
        h-full overflow-y-auto overflow-x-hidden // Added overflow-x-hidden
        transition-all duration-300 ease-in-out
        ${isOpen ? 'w-64' : 'w-0'}
        // Removed translate-x class
        ${isOpen ? 'p-4 pt-6' : 'p-0'}
      `}
      // Removed inline visibility style
    >
      {/* Content needs to be wrapped to prevent flexing when width is 0 */}
      <div className="flex-grow flex flex-col">
        <nav className="flex-grow space-y-1">
          <NavLink to="/dashboard" className={getNavLinkClass} onClick={onLinkClick} end>
            <Home className="mr-3 h-4 w-4" />
            Dashboard
          </NavLink>
          <NavLink to="/workflow/excel" className={getNavLinkClass} onClick={onLinkClick}>
            <FileText className="mr-3 h-4 w-4" />
            Excel Workflow
          </NavLink>
          <NavLink to="/workflow/image" className={getNavLinkClass} onClick={onLinkClick}>
            <Image className="mr-3 h-4 w-4" />
            Image Workflow
          </NavLink>
          <NavLink to="/workflow/file-preprocessing" className={getNavLinkClass} onClick={onLinkClick}>
            <FileText className="mr-3 h-4 w-4" />
            Workflow File Pre-processing
          </NavLink>
          {/* Add more navigation links here */}
        </nav>
      </div>
    </aside>
  );
};

const Footer: React.FC = () => {
  return (
    <footer className="py-3 px-6 border-t bg-gray-50/50 text-center text-xs text-gray-600 flex-shrink-0"> {/* Removed mt-auto */}
      © An initiative by GD R&D Zycus 2025
    </footer>
  );
};

const Layout: React.FC = () => {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true); // Start open again for desktop
  const navigate = useNavigate(); // Get navigate function

  const toggleSidebar = () => {
    setIsSidebarOpen(!isSidebarOpen);
  };

  // Close sidebar when a nav link is clicked (optional, maybe only for mobile later)
  const handleNavLinkClick = () => {
      // Keep open on desktop for now
      // setIsSidebarOpen(false);
  };

  // Function to handle logout navigation
  const handleLogout = () => {
    console.log("Logging out..."); // Placeholder for actual logout logic
    navigate('/login');
  };

  return (
    <div className="flex flex-col h-screen bg-background overflow-hidden"> {/* Prevent body scroll */}
      {/* Pass handleLogout to the header */}
      <WorkflowHeader onMenuClick={toggleSidebar} onLogoutClick={handleLogout} />

      {/* Horizontal container for Sidebar + Main Content Area */}
      <div className="flex flex-1 overflow-hidden"> {/* Horizontal flex, allow vertical scroll within children */}
        {/* Sidebar takes fixed width when open */}
        <Sidebar isOpen={isSidebarOpen} onLinkClick={handleNavLinkClick} />

        {/* Main content wrapper */}
        <div className="flex flex-col flex-1 overflow-hidden"> {/* Takes remaining space */}
          {/* Main content scrolls vertically */}
          <main className="flex-1 overflow-y-auto bg-gray-100/50 p-6"> {/* Add padding here */}
                 <Outlet />
          </main>
          <Footer />
        </div>
      </div>

       {/* Removed the overlay */}
    </div>
  );
};

export default Layout;

// The global styles should be in a CSS file or styled-components/emotion implementation
// For a quick fix, we can use a component with useEffect to inject the styles
export function GlobalStyleFix() {
  useEffect(() => {
    // Create a style element
    const style = document.createElement('style');
    style.textContent = `
      :root {
        --toaster-z-index: 9999;
      }
      
      .fixed.inset-0.flex.items-center.justify-center.z-50 {
        z-index: 9000;
      }
    `;
    // Append to document head
    document.head.appendChild(style);
    
    // Clean up on unmount
    return () => {
      document.head.removeChild(style);
    };
  }, []);
  
  return null;
} 