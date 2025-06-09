import React, { useState, useEffect } from 'react';
import { Card, CardContent } from "@/components/ui/card";
import WorkflowStats from '@/components/Dashboard/WorkflowStats';
import WorkflowRunsTable, { WorkflowRun } from '@/components/Dashboard/WorkflowRunsTable';
import { fetchWorkflowRuns, fetchDashboardStats } from '@/services/api';
import { motion } from 'framer-motion';
import { Activity, FileSpreadsheet, Image, ArrowRight } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

const DashboardPage: React.FC = () => {
  const [workflowRuns, setWorkflowRuns] = useState<WorkflowRun[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  // Fetch workflow runs data from API
  const fetchData = async () => {
    try {
      setIsLoading(true);
      setError(null);
      const response = await fetchWorkflowRuns();
      setWorkflowRuns(response.data);
    } catch (error) {
      console.error('Error fetching workflow data:', error);
      setError('Failed to load workflow data. Please try again later.');
    } finally {
      setIsLoading(false);
    }
  };

  // Initial data load
  useEffect(() => {
    fetchData();
  }, []);

  // Poll for updates every 10 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      fetchData();
    }, 10000);

    return () => clearInterval(interval);
  }, []);

  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        when: "beforeChildren",
        staggerChildren: 0.1
      }
    }
  };

  const itemVariants = {
    hidden: { opacity: 0, y: 20 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: "spring",
        stiffness: 300,
        damping: 24
      }
    }
  };

  const handleWorkflowRedirect = (type: string) => {
    navigate(`/workflow/${type}`);
  };

  return (
    <motion.div 
      className="container mx-auto px-4 py-8 max-w-[1200px]"
      variants={containerVariants}
      initial="hidden"
      animate="visible"
    > 
      {/* Main Content */}
      <motion.div className="flex flex-col gap-6" variants={itemVariants}>
        {/* Stats at top - full width */}
        <motion.div variants={itemVariants}>
          <WorkflowStats runs={workflowRuns} />
        </motion.div>
        
        {/* Create New Workflow Buttons */}
        <motion.div variants={itemVariants}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Start New Workflow</h2>
            <div className="h-1 w-20 bg-gradient-to-r from-blue-500 to-sky-500 rounded-full"></div>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Excel Button */}
            <motion.div 
              className="cursor-pointer bg-gradient-to-tr from-blue-50 to-emerald-50 dark:from-blue-900/10 dark:to-emerald-900/10 border border-blue-200 dark:border-blue-700 rounded-xl p-4 shadow-sm hover:shadow-md transition-all group"
              whileHover={{ y: -4 }}
              onClick={() => handleWorkflowRedirect('excel')}
            >
              <div className="flex items-center gap-4">
                <div className="bg-white dark:bg-emerald-900/20 p-3 rounded-lg shadow-sm text-emerald-600 dark:text-emerald-400 group-hover:shadow transition-shadow">
                  <FileSpreadsheet className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-emerald-700 dark:text-emerald-400 flex items-center gap-2">
                    Excel Workflow
                    <ArrowRight className="h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400">Transform and extract data from spreadsheets</p>
                </div>
              </div>
            </motion.div>
            
            {/* Image Button */}
            <motion.div 
              className="cursor-pointer bg-gradient-to-tr from-blue-50 to-sky-50 dark:from-blue-900/10 dark:to-sky-900/10 border border-blue-200 dark:border-blue-700 rounded-xl p-4 shadow-sm hover:shadow-md transition-all group"
              whileHover={{ y: -4 }}
              onClick={() => handleWorkflowRedirect('image')}
            >
              <div className="flex items-center gap-4">
                <div className="bg-white dark:bg-sky-900/20 p-3 rounded-lg shadow-sm text-blue-600 dark:text-blue-400 group-hover:shadow transition-shadow">
                  <Image className="h-6 w-6" />
                </div>
                <div className="flex-1">
                  <h3 className="font-semibold text-blue-700 dark:text-blue-400 flex items-center gap-2">
                    Image Workflow
                    <ArrowRight className="h-4 w-4 opacity-0 -translate-x-2 group-hover:opacity-100 group-hover:translate-x-0 transition-all" />
                  </h3>
                  <p className="text-xs text-slate-600 dark:text-slate-400">Extract data from images and documents</p>
                </div>
              </div>
            </motion.div>
          </div>
        </motion.div>
        
        {/* Table - Full width */}
        <motion.div variants={itemVariants}>
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Recent Executions</h2>
            <div className="h-1 w-20 bg-gradient-to-r from-blue-500 to-sky-500 rounded-full"></div>
          </div>
          
          <Card className="border border-slate-200 dark:border-slate-700 rounded-xl shadow-sm overflow-hidden">
            <CardContent className="p-0">
              {isLoading && workflowRuns.length === 0 ? (
                <div className="flex flex-col items-center justify-center p-10 space-y-4">
                  <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-blue-500"></div>
                  <p className="text-slate-500 dark:text-slate-400">Loading workflow data...</p>
                </div>
              ) : error ? (
                <div className="flex flex-col items-center justify-center p-10 space-y-4 text-red-500">
                  <svg className="h-12 w-12" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="1.5"/>
                    <path d="M12 7V13" stroke="currentColor" strokeWidth="2" strokeLinecap="round"/>
                    <circle cx="12" cy="16" r="1" fill="currentColor"/>
                  </svg>
                  <p>{error}</p>
                  <button 
                    onClick={fetchData}
                    className="px-4 py-2 bg-red-100 dark:bg-red-900/30 text-red-600 dark:text-red-400 rounded-lg hover:bg-red-200 dark:hover:bg-red-900/50 transition-colors"
                  >
                    Try Again
                  </button>
                </div>
              ) : (
                <WorkflowRunsTable runs={workflowRuns} />
              )}
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </motion.div>
  );
};

export default DashboardPage; 