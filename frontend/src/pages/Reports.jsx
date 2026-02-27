import { motion } from 'framer-motion'
import {
  FileText,
  Download,
  Calendar,
  TrendingDown,
  TrendingUp,
  AlertTriangle,
  CheckCircle,
  BarChart3,
  PieChart,
  Filter,
  RefreshCw,
} from 'lucide-react'
import { Button, GlassCard } from '../components/ui/Common'
import { EmissionTrendChart } from '../components/charts/Charts'
import { monthlyReports, emissionTrends } from '../data/mockData'

/**
 * Reports Page
 * Monthly emission reports and analytics summaries
 */
const Reports = () => {
  // Current month summary stats
  const currentReport = monthlyReports[0]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <FileText className="w-7 h-7 text-accent-green" />
            Reports & Analytics
          </h1>
          <p className="text-gray-400 mt-1">
            Monthly emission summaries and downloadable reports
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" icon={Filter} size="sm">
            Filter
          </Button>
          <Button variant="primary" icon={Download} size="sm">
            Download All
          </Button>
        </div>
      </div>

      {/* Current Month Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="glass-card p-6"
      >
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-lg font-semibold text-white">{currentReport.month} Summary</h2>
            <p className="text-sm text-gray-400">Current reporting period overview</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 bg-accent-green/10 rounded-full">
            <CheckCircle className="w-4 h-4 text-accent-green" />
            <span className="text-sm text-accent-green font-medium">{currentReport.status}</span>
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-4">
          <div className="bg-dark-bg/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="w-4 h-4 text-info-blue" />
              <p className="text-xs text-gray-500">Total Emissions</p>
            </div>
            <p className="text-xl font-bold text-white">
              {(currentReport.totalEmissions / 1000).toFixed(1)}k
            </p>
            <p className="text-xs text-gray-500">metric tons CH₄</p>
          </div>

          <div className="bg-dark-bg/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-danger-red" />
              <p className="text-xs text-gray-500">Detected Leaks</p>
            </div>
            <p className="text-xl font-bold text-white">{currentReport.detectedLeaks}</p>
            <div className="flex items-center gap-1 text-danger-red">
              <TrendingUp className="w-3 h-3" />
              <span className="text-xs">+8.7%</span>
            </div>
          </div>

          <div className="bg-dark-bg/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <CheckCircle className="w-4 h-4 text-accent-green" />
              <p className="text-xs text-gray-500">Resolved Leaks</p>
            </div>
            <p className="text-xl font-bold text-white">{currentReport.resolvedLeaks}</p>
            <div className="flex items-center gap-1 text-accent-green">
              <TrendingUp className="w-3 h-3" />
              <span className="text-xs">+12.3%</span>
            </div>
          </div>

          <div className="bg-dark-bg/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="w-4 h-4 text-warning-yellow" />
              <p className="text-xs text-gray-500">Super Emitters</p>
            </div>
            <p className="text-xl font-bold text-white">{currentReport.superEmitters}</p>
            <div className="flex items-center gap-1 text-warning-yellow">
              <TrendingUp className="w-3 h-3" />
              <span className="text-xs">+2</span>
            </div>
          </div>

          <div className="bg-dark-bg/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <PieChart className="w-4 h-4 text-purple-400" />
              <p className="text-xs text-gray-500">CO₂ Equivalent</p>
            </div>
            <p className="text-xl font-bold text-white">{currentReport.co2Equivalent}M</p>
            <p className="text-xs text-gray-500">tons/year</p>
          </div>

          <div className="bg-dark-bg/50 rounded-xl p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingDown className="w-4 h-4 text-accent-green" />
              <p className="text-xs text-gray-500">Resolution Rate</p>
            </div>
            <p className="text-xl font-bold text-white">
              {((currentReport.resolvedLeaks / currentReport.detectedLeaks) * 100).toFixed(1)}%
            </p>
            <div className="flex items-center gap-1 text-accent-green">
              <TrendingUp className="w-3 h-3" />
              <span className="text-xs">+3.2%</span>
            </div>
          </div>
        </div>
      </motion.div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <EmissionTrendChart data={emissionTrends} />

        {/* Resolution Progress */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="glass-card p-6"
        >
          <h3 className="text-lg font-semibold text-white mb-4">Monthly Resolution Progress</h3>
          <div className="space-y-4">
            {emissionTrends.slice(-6).map((month, index) => (
              <div key={month.month}>
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-gray-400">{month.month}</span>
                  <span className="text-sm text-white">
                    {month.resolved} / {month.detected} resolved
                  </span>
                </div>
                <div className="w-full h-3 bg-dark-border rounded-full overflow-hidden">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${(month.resolved / month.detected) * 100}%` }}
                    transition={{ duration: 0.5, delay: index * 0.1 }}
                    className="h-full bg-gradient-to-r from-accent-green to-emerald-400 rounded-full"
                  />
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Reports List */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.3 }}
        className="glass-card"
      >
        <div className="p-4 border-b border-dark-border">
          <h3 className="text-lg font-semibold text-white">Available Reports</h3>
          <p className="text-sm text-gray-400">Download monthly emission reports in PDF format</p>
        </div>

        <div className="divide-y divide-dark-border/50">
          {monthlyReports.map((report, index) => (
            <motion.div
              key={report.id}
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.4 + index * 0.1 }}
              className="p-4 flex items-center justify-between hover:bg-dark-border/20 transition-colors"
            >
              <div className="flex items-center gap-4">
                <div className="w-12 h-12 rounded-xl bg-accent-green/10 flex items-center justify-center">
                  <FileText className="w-6 h-6 text-accent-green" />
                </div>
                <div>
                  <h4 className="font-medium text-white">{report.month} Emission Report</h4>
                  <div className="flex items-center gap-4 mt-1">
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <BarChart3 className="w-3 h-3" />
                      {(report.totalEmissions / 1000).toFixed(1)}k tons
                    </span>
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <AlertTriangle className="w-3 h-3" />
                      {report.detectedLeaks} leaks
                    </span>
                    <span className="text-xs text-gray-500 flex items-center gap-1">
                      <CheckCircle className="w-3 h-3" />
                      {report.resolvedLeaks} resolved
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center gap-4">
                <div className="flex items-center gap-2 px-3 py-1 bg-accent-green/10 rounded-full">
                  <div className="w-2 h-2 rounded-full bg-accent-green" />
                  <span className="text-xs text-accent-green">{report.status}</span>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  icon={Download}
                  onClick={() => {
                    // Simulate download
                    alert(`Downloading ${report.month} report...`)
                  }}
                >
                  Download PDF
                </Button>
              </div>
            </motion.div>
          ))}
        </div>

        {/* Generate New Report */}
        <div className="p-4 border-t border-dark-border bg-dark-bg/30">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-400">Need a custom report?</p>
              <p className="text-xs text-gray-500">Generate reports for specific date ranges or regions</p>
            </div>
            <Button variant="secondary" icon={RefreshCw}>
              Generate Custom Report
            </Button>
          </div>
        </div>
      </motion.div>

      {/* Export Options */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.5 }}
        className="grid grid-cols-1 md:grid-cols-3 gap-4"
      >
        <GlassCard className="p-6 text-center hover:border-accent-green/50 cursor-pointer transition-all">
          <div className="w-12 h-12 rounded-xl bg-info-blue/20 flex items-center justify-center mx-auto mb-4">
            <FileText className="w-6 h-6 text-info-blue" />
          </div>
          <h4 className="font-semibold text-white mb-2">Export as PDF</h4>
          <p className="text-sm text-gray-400">Complete report with charts and analytics</p>
        </GlassCard>

        <GlassCard className="p-6 text-center hover:border-accent-green/50 cursor-pointer transition-all">
          <div className="w-12 h-12 rounded-xl bg-accent-green/20 flex items-center justify-center mx-auto mb-4">
            <BarChart3 className="w-6 h-6 text-accent-green" />
          </div>
          <h4 className="font-semibold text-white mb-2">Export as CSV</h4>
          <p className="text-sm text-gray-400">Raw data for custom analysis</p>
        </GlassCard>

        <GlassCard className="p-6 text-center hover:border-accent-green/50 cursor-pointer transition-all">
          <div className="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center mx-auto mb-4">
            <Calendar className="w-6 h-6 text-purple-400" />
          </div>
          <h4 className="font-semibold text-white mb-2">Schedule Reports</h4>
          <p className="text-sm text-gray-400">Automated weekly/monthly delivery</p>
        </GlassCard>
      </motion.div>
    </div>
  )
}

export default Reports
