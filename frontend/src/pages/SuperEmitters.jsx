import { useState } from 'react'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  Download,
  RefreshCw,
  Eye,
  MapPin,
  Satellite,
  Calendar,
  Filter,
} from 'lucide-react'
import DataTable from '../components/tables/DataTable'
import { StatusBadge, RiskIndicator } from '../components/ui/AlertCard'
import { Button, GlassCard, SectionHeader } from '../components/ui/Common'
import { superEmitters } from '../data/mockData'

/**
 * Super Emitters Page
 * Table view of all detected super-emitter events
 */
const SuperEmitters = () => {
  const [selectedEmitter, setSelectedEmitter] = useState(null)

  // Calculate stats
  const activeCount = superEmitters.filter(e => e.status === 'Active').length
  const investigatingCount = superEmitters.filter(e => e.status === 'Investigating').length
  const resolvedCount = superEmitters.filter(e => e.status === 'Resolved').length
  const totalEmissions = superEmitters.reduce((sum, e) => sum + e.emissionRate, 0)

  // Table column configuration
  const columns = [
    {
      key: 'id',
      label: 'ID',
      sortable: true,
      render: (value) => (
        <span className="font-mono text-accent-green">{value}</span>
      ),
    },
    {
      key: 'location',
      label: 'Location',
      sortable: true,
      render: (value, row) => (
        <div className="flex items-center gap-2">
          <MapPin className="w-4 h-4 text-gray-500" />
          <div>
            <p className="text-white font-medium">{value}</p>
            <p className="text-xs text-gray-500">
              {row.coordinates.lat.toFixed(4)}, {row.coordinates.lng.toFixed(4)}
            </p>
          </div>
        </div>
      ),
    },
    {
      key: 'emissionRate',
      label: 'Emission Rate',
      sortable: true,
      render: (value, row) => (
        <div>
          <span className="text-white font-semibold">{value.toLocaleString()}</span>
          <span className="text-gray-500 ml-1">{row.unit}</span>
        </div>
      ),
    },
    {
      key: 'confidence',
      label: 'Confidence',
      sortable: true,
      render: (value) => (
        <div className="flex items-center gap-2">
          <div className="w-16 h-2 bg-dark-border rounded-full overflow-hidden">
            <div
              className="h-full bg-accent-green rounded-full"
              style={{ width: `${value}%` }}
            />
          </div>
          <span className="text-sm text-gray-400">{value}%</span>
        </div>
      ),
    },
    {
      key: 'satellite',
      label: 'Satellite',
      sortable: true,
      render: (value) => (
        <div className="flex items-center gap-2">
          <Satellite className="w-4 h-4 text-info-blue" />
          <span className="text-gray-300">{value}</span>
        </div>
      ),
    },
    {
      key: 'riskLevel',
      label: 'Risk',
      sortable: true,
      render: (value) => <RiskIndicator level={value} />,
    },
    {
      key: 'status',
      label: 'Status',
      sortable: true,
      render: (value) => <StatusBadge status={value} />,
    },
    {
      key: 'lastDetected',
      label: 'Last Detected',
      sortable: true,
      render: (value) => (
        <div className="flex items-center gap-2 text-gray-400">
          <Calendar className="w-4 h-4" />
          <span className="text-sm">
            {new Date(value).toLocaleDateString('en-US', {
              month: 'short',
              day: 'numeric',
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
        </div>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation()
            setSelectedEmitter(row)
          }}
          className="p-2 hover:bg-dark-border rounded-lg transition-colors"
        >
          <Eye className="w-4 h-4 text-gray-400 hover:text-accent-green" />
        </button>
      ),
    },
  ]

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-3">
            <AlertTriangle className="w-7 h-7 text-danger-red" />
            Super Emitters
          </h1>
          <p className="text-gray-400 mt-1">
            High-emission events requiring immediate attention
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" icon={RefreshCw} size="sm">
            Refresh
          </Button>
          <Button variant="primary" icon={Download} size="sm">
            Export CSV
          </Button>
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="stat-card"
        >
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-danger-red/20">
              <AlertTriangle className="w-6 h-6 text-danger-red" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Active</p>
              <p className="text-2xl font-bold text-white">{activeCount}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="stat-card"
        >
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-warning-yellow/20">
              <Eye className="w-6 h-6 text-warning-yellow" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Investigating</p>
              <p className="text-2xl font-bold text-white">{investigatingCount}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="stat-card"
        >
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-accent-green/20">
              <RefreshCw className="w-6 h-6 text-accent-green" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Resolved</p>
              <p className="text-2xl font-bold text-white">{resolvedCount}</p>
            </div>
          </div>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          className="stat-card"
        >
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-info-blue/20">
              <Satellite className="w-6 h-6 text-info-blue" />
            </div>
            <div>
              <p className="text-sm text-gray-400">Total Emissions</p>
              <p className="text-2xl font-bold text-white">{(totalEmissions / 1000).toFixed(1)}k<span className="text-sm text-gray-500"> kg/hr</span></p>
            </div>
          </div>
        </motion.div>
      </div>

      {/* Data Table */}
      <DataTable
        columns={columns}
        data={superEmitters}
        searchPlaceholder="Search by location, ID, or satellite..."
        onRowClick={(row) => setSelectedEmitter(row)}
        pageSize={8}
      />

      {/* Detail Modal/Drawer */}
      {selectedEmitter && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedEmitter(null)}
        >
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass-card w-full max-w-2xl max-h-[90vh] overflow-y-auto"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Header */}
            <div className="p-6 border-b border-dark-border">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <span className="font-mono text-accent-green">{selectedEmitter.id}</span>
                    <StatusBadge status={selectedEmitter.status} />
                  </div>
                  <h2 className="text-xl font-bold text-white">{selectedEmitter.location}</h2>
                </div>
                <button
                  onClick={() => setSelectedEmitter(null)}
                  className="p-2 hover:bg-dark-border rounded-lg transition-colors"
                >
                  <span className="text-gray-400 hover:text-white">✕</span>
                </button>
              </div>
            </div>

            {/* Content */}
            <div className="p-6 space-y-6">
              {/* Key Metrics */}
              <div className="grid grid-cols-2 gap-4">
                <div className="bg-dark-bg/50 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Emission Rate</p>
                  <p className="text-2xl font-bold text-white">
                    {selectedEmitter.emissionRate.toLocaleString()}
                    <span className="text-sm text-gray-500 ml-1">{selectedEmitter.unit}</span>
                  </p>
                </div>
                <div className="bg-dark-bg/50 rounded-lg p-4">
                  <p className="text-sm text-gray-400 mb-1">Confidence Score</p>
                  <p className="text-2xl font-bold text-accent-green">
                    {selectedEmitter.confidence}%
                  </p>
                </div>
              </div>

              {/* Details Grid */}
              <div className="space-y-4">
                <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">Details</h3>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <p className="text-sm text-gray-500">Coordinates</p>
                    <p className="text-white font-mono">
                      {selectedEmitter.coordinates.lat.toFixed(4)}, {selectedEmitter.coordinates.lng.toFixed(4)}
                    </p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Satellite Source</p>
                    <p className="text-white">{selectedEmitter.satellite}</p>
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Risk Level</p>
                    <RiskIndicator level={selectedEmitter.riskLevel} />
                  </div>
                  <div>
                    <p className="text-sm text-gray-500">Company</p>
                    <p className="text-white">{selectedEmitter.company}</p>
                  </div>
                  <div className="col-span-2">
                    <p className="text-sm text-gray-500">Last Detected</p>
                    <p className="text-white">
                      {new Date(selectedEmitter.lastDetected).toLocaleString('en-US', {
                        weekday: 'long',
                        year: 'numeric',
                        month: 'long',
                        day: 'numeric',
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </p>
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex gap-3 pt-4 border-t border-dark-border">
                <Button variant="primary" className="flex-1">
                  Create Investigation
                </Button>
                <Button variant="secondary" className="flex-1">
                  View on Map
                </Button>
                <Button variant="outline">
                  <Download className="w-4 h-4" />
                </Button>
              </div>
            </div>
          </motion.div>
        </motion.div>
      )}
    </div>
  )
}

export default SuperEmitters
