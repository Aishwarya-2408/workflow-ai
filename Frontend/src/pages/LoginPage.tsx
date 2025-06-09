import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardHeader, CardTitle, CardDescription, CardContent, CardFooter } from "@/components/ui/card";
import { Workflow } from 'lucide-react'; // Or use a different relevant icon

const LoginPage: React.FC = () => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const handleLogin = (event: React.FormEvent) => {
    event.preventDefault();
    setError(null); // Clear previous errors
    setIsLoading(true);
    console.log('Login attempt:', { username, password });

    // --- Placeholder for actual authentication logic --- 
    // Simulate API call
    setTimeout(() => {
       // Example: Check hardcoded credentials (replace with API call)
       if (username === 'admin' && password === 'password') {
         console.log('Login successful');
         // TODO: Store auth token/session info
         navigate('/dashboard'); // Redirect to dashboard on successful login
       } else {
         console.log('Login failed');
         setError('Invalid username or password.');
         setIsLoading(false);
       }
    }, 1000); // Simulate network delay
    // --- End Placeholder --- 
  };

  return (
    <div className="flex items-center justify-center min-h-screen bg-gray-100">
      <Card className="w-full max-w-sm shadow-lg">
        <CardHeader className="space-y-1 text-center">
          <div className="flex justify-center mb-4">
             <div className="w-12 h-12 rounded-lg bg-blue-600 flex items-center justify-center">
               <Workflow size={28} className="text-white" />
             </div>
          </div>
          <CardTitle className="text-2xl font-bold">Login</CardTitle>
          <CardDescription>Enter your username and password to access the system.</CardDescription>
        </CardHeader>
        <form onSubmit={handleLogin}>
          <CardContent className="space-y-4">
             {error && (
                <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded relative" role="alert">
                   <span className="block sm:inline">{error}</span>
                </div>
             )}
            <div className="space-y-2">
              <Label htmlFor="username">Username</Label>
              <Input 
                 id="username" 
                 type="text" 
                 placeholder="Enter your username" 
                 required 
                 value={username}
                 onChange={(e) => setUsername(e.target.value)}
                 disabled={isLoading}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">Password</Label>
              <Input 
                 id="password" 
                 type="password" 
                 placeholder="Enter your password" 
                 required 
                 value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 disabled={isLoading}
               />
            </div>
          </CardContent>
          <CardFooter>
            <Button type="submit" className="w-full" disabled={isLoading}>
              {isLoading ? 'Logging in...' : 'Login'}
            </Button>
          </CardFooter>
        </form>
      </Card>
    </div>
  );
};

export default LoginPage; 