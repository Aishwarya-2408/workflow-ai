import React from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "./ui/button";
import { Home, AlertTriangle } from "lucide-react";

const NotFound: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="flex flex-col min-h-screen">
      <main className="flex-1 flex flex-col items-center justify-center bg-white px-6 py-16">
        <div className="max-w-lg w-full text-center">
          <div className="flex justify-center mb-4">
            <AlertTriangle className="h-16 w-16 text-yellow-500" strokeWidth={1.5} />
          </div>
          <h1 className="text-6xl font-bold text-gray-900 mb-4">404</h1>
          <h2 className="text-2xl font-semibold text-gray-800 mb-3">Page Not Found</h2>
          <p className="text-gray-600 mb-8">
            The page you are looking for doesn't exist or has been moved.
          </p>
          <Button 
            onClick={() => navigate("/")} 
            size="lg" 
            className="bg-primary text-white hover:bg-primary/90 transition-colors"
          >
            <Home className="mr-2 h-4 w-4" />
            Go Back Home
          </Button>
        </div>
      </main>
      
      <footer className="bg-white border-t">
        <div className="container mx-auto py-4 px-4">
          <div className="mt-1 flex justify-end">
            <div className="text-xs text-gray-500 italic">
              An initiative by GD R&D
            </div>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default NotFound;
