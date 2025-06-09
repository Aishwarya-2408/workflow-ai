import React from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import { FileSpreadsheet, Image } from 'lucide-react';

const WorkflowSelection: React.FC = () => {
  const navigate = useNavigate();

  const handleRedirect = (path: string) => {
    navigate(path);
  };

  // Animation variants
  const cardVariants = {
    hover: { 
      y: -8,
      transition: { 
        type: "spring", 
        stiffness: 400, 
        damping: 10 
      }
    }
  };

  return (
    <section className="w-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Start New Workflow</h2>
        <div className="h-1 w-20 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full"></div>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {/* Excel Workflow Card */}
        <motion.div 
          className="cursor-pointer group"
          onClick={() => handleRedirect('/workflow/excel')}
          whileHover="hover"
          variants={cardVariants}
        >
          <div className="bg-gradient-to-tr from-emerald-50 to-emerald-100 dark:from-emerald-900/20 dark:to-emerald-800/20 p-6 rounded-xl border border-emerald-200 dark:border-emerald-800 shadow-sm h-full overflow-hidden relative">
            <div className="absolute right-0 top-0 bg-gradient-to-bl from-emerald-200/50 via-transparent to-transparent dark:from-emerald-700/30 w-1/2 h-1/2 rounded-bl-full"></div>
            
            <div className="relative">
              <div className="flex items-center gap-4 mb-4">
                <div className="bg-white dark:bg-emerald-900/50 p-3 rounded-lg shadow-md text-emerald-600 dark:text-emerald-400 group-hover:shadow-lg transition-shadow">
                  <FileSpreadsheet size={28} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-emerald-700 dark:text-emerald-400">Excel Workflow</h3>
                  <p className="text-sm text-emerald-600/80 dark:text-emerald-400/80">Automated data extraction</p>
                </div>
              </div>
              
              <p className="text-slate-600 dark:text-slate-300 mb-5 text-sm">
                Transform Excel files into structured data with intelligent automated extraction and processing.
              </p>
              
              <div className="flex justify-between items-center">
                <span className="text-xs text-emerald-800 dark:text-emerald-300 font-medium">
                  Supports XLS, XLSX formats
                </span>
                <div className="bg-emerald-100 dark:bg-emerald-800/50 text-emerald-600 dark:text-emerald-400 text-xs py-1 px-3 rounded-full font-medium flex items-center gap-1 transition-colors group-hover:bg-emerald-600 group-hover:text-white dark:group-hover:bg-emerald-600">
                  Get Started
                  <svg className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </motion.div>

        {/* Image Workflow Card */}
        <motion.div 
          className="cursor-pointer group"
          onClick={() => handleRedirect('/workflow/image')}
          whileHover="hover"
          variants={cardVariants}
        >
          <div className="bg-gradient-to-tr from-blue-50 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-800/20 p-6 rounded-xl border border-blue-200 dark:border-blue-800 shadow-sm h-full overflow-hidden relative">
            <div className="absolute right-0 top-0 bg-gradient-to-bl from-blue-200/50 via-transparent to-transparent dark:from-blue-700/30 w-1/2 h-1/2 rounded-bl-full"></div>
            
            <div className="relative">
              <div className="flex items-center gap-4 mb-4">
                <div className="bg-white dark:bg-blue-900/50 p-3 rounded-lg shadow-md text-blue-600 dark:text-blue-400 group-hover:shadow-lg transition-shadow">
                  <Image size={28} />
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-blue-700 dark:text-blue-400">Image Workflow</h3>
                  <p className="text-sm text-blue-600/80 dark:text-blue-400/80">Visual data recognition</p>
                </div>
              </div>
              
              <p className="text-slate-600 dark:text-slate-300 mb-5 text-sm">
                Extract valuable data from images using advanced AI recognition to automate document processing.
              </p>
              
              <div className="flex justify-between items-center">
                <span className="text-xs text-blue-800 dark:text-blue-300 font-medium">
                  Supports JPG, PNG, SVG formats
                </span>
                <div className="bg-blue-100 dark:bg-blue-800/50 text-blue-600 dark:text-blue-400 text-xs py-1 px-3 rounded-full font-medium flex items-center gap-1 transition-colors group-hover:bg-blue-600 group-hover:text-white dark:group-hover:bg-blue-600">
                  Get Started
                  <svg className="w-3.5 h-3.5 group-hover:translate-x-1 transition-transform" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <path d="M5 12H19M19 12L12 5M19 12L12 19" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </div>
    </section>
  );
};

export default WorkflowSelection; 