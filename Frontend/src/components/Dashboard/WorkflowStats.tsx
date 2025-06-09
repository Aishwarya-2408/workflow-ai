import React from 'react';
import { WorkflowRun } from './WorkflowRunsTable';
import { CheckCircle, Clock, AlertCircle, BarChart2 } from 'lucide-react';
import { motion } from 'framer-motion';

interface WorkflowStatsProps {
  runs: WorkflowRun[];
}

const WorkflowStats: React.FC<WorkflowStatsProps> = ({ runs }) => {
  // Calculate stats
  const completedRuns = runs.filter(run => run.status === 'completed').length;
  const processingRuns = runs.filter(run => run.status === 'processing').length;
  const failedRuns = runs.filter(run => run.status === 'failed').length;
  const totalRuns = runs.length;

  // Calculate success rate
  const successRate = totalRuns ? Math.round((completedRuns / totalRuns) * 100) : 0;
  
  // Animation variants
  const containerVariants = {
    hidden: { opacity: 0 },
    visible: {
      opacity: 1,
      transition: {
        staggerChildren: 0.1
      }
    }
  };
  
  const itemVariants = {
    hidden: { y: 20, opacity: 0 },
    visible: {
      y: 0,
      opacity: 1,
      transition: { 
        type: "spring",
        stiffness: 300,
        damping: 24
      }
    }
  };

  const stats = [
    {
      name: 'Completed',
      value: completedRuns,
      icon: <CheckCircle className="h-5 w-5" />,
      color: 'text-emerald-500',
      bgColor: 'bg-emerald-50 dark:bg-emerald-900/20',
      borderColor: 'border-emerald-200 dark:border-emerald-700',
      progressColor: 'bg-emerald-500'
    },
    {
      name: 'In Progress',
      value: processingRuns,
      icon: <Clock className="h-5 w-5" />,
      color: 'text-blue-500',
      bgColor: 'bg-blue-50 dark:bg-blue-900/20',
      borderColor: 'border-blue-200 dark:border-blue-700',
      progressColor: 'bg-blue-500'
    },
    {
      name: 'Failed',
      value: failedRuns,
      icon: <AlertCircle className="h-5 w-5" />,
      color: 'text-rose-500',
      bgColor: 'bg-rose-50 dark:bg-rose-900/20',
      borderColor: 'border-rose-200 dark:border-rose-700',
      progressColor: 'bg-rose-500'
    }
  ];

  return (
    <section className="w-full">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Workflow Statistics</h2>
        <div className="h-1 w-20 bg-gradient-to-r from-blue-500 to-sky-500 rounded-full"></div>
      </div>
      
      {/* Top card - overall success rate */}
      <motion.div 
        className="relative mb-5 p-5 rounded-xl bg-gradient-to-tr from-blue-50 to-sky-100 dark:from-blue-900/20 dark:to-sky-800/20 border border-blue-200 dark:border-blue-800 shadow-sm overflow-hidden"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
      >
        <div className="absolute top-0 right-0 w-32 h-32 transform translate-x-10 -translate-y-10">
          <div className="w-full h-full rounded-full bg-blue-200/40 dark:bg-blue-600/20"></div>
        </div>
        
        <div className="flex items-center gap-3">
          <div className="bg-white dark:bg-blue-800/40 p-2 rounded-lg shadow-md text-blue-600 dark:text-blue-300">
            <BarChart2 className="h-5 w-5" />
          </div>
          <h3 className="font-semibold text-lg text-blue-700 dark:text-blue-300">Overall Success Rate</h3>
        </div>
        
        <div className="mt-4 flex items-end gap-2">
          <span className="text-3xl font-bold text-blue-800 dark:text-blue-200">{successRate}%</span>
          <span className="text-sm font-medium text-blue-600/70 dark:text-blue-400/70 mb-1">
            from {totalRuns} {totalRuns === 1 ? 'workflow' : 'workflows'}
          </span>
        </div>
        
        {/* Progress bar */}
        <div className="mt-4 w-full bg-white/80 dark:bg-gray-800/50 rounded-full h-2.5 overflow-hidden">
          <div 
            className="h-2.5 rounded-full bg-blue-500"
            style={{ width: `${successRate}%` }}
          ></div>
        </div>
      </motion.div>
      
      {/* Stats grid */}
      <motion.div 
        className="grid grid-cols-1 sm:grid-cols-3 gap-4"
        variants={containerVariants}
        initial="hidden"
        animate="visible"
      >
        {stats.map((stat) => (
          <motion.div 
            key={stat.name}
            className={`${stat.bgColor} ${stat.borderColor} border rounded-xl p-4 shadow-sm flex flex-col transition-all hover:shadow-md`}
            variants={itemVariants}
          >
            <div className={`${stat.color} mb-2 flex items-center gap-2`}>
              {stat.icon}
              <span className="font-medium text-sm">{stat.name}</span>
            </div>
            
            <div className="flex items-end gap-2 mt-1">
              <span className="text-2xl font-bold text-slate-800 dark:text-slate-200">{stat.value}</span>
              <span className="text-xs text-slate-500 dark:text-slate-400 mb-1">
                {stat.value === 1 ? 'workflow' : 'workflows'}
              </span>
            </div>
            
            {totalRuns > 0 && (
              <div className="mt-2 text-xs text-slate-600 dark:text-slate-300">
                {Math.round((stat.value / totalRuns) * 100)}% of total
              </div>
            )}
            
            {/* Progress bar */}
            <div className="mt-2 w-full bg-white/80 dark:bg-gray-800/50 rounded-full h-1.5 overflow-hidden">
              <div 
                className={`h-1.5 rounded-full ${stat.progressColor}`}
                style={{ width: totalRuns ? `${(stat.value / totalRuns) * 100}%` : '0%' }}
              ></div>
            </div>
          </motion.div>
        ))}
      </motion.div>
    </section>
  );
};

export default WorkflowStats; 