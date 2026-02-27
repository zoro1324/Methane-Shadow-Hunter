import { Link } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  Database,
  Brain,
  AlertTriangle,
  Bell,
  ChevronRight,
  ArrowRight,
  Play,
  Globe,
  Shield,
  Zap,
  BarChart3,
  Github,
  Twitter,
  Linkedin,
  Mail,
  Flame,
} from 'lucide-react'

/**
 * Landing Page Component
 * Main entry point with hero, features, and how it works sections
 */
const Landing = () => {
  // Animation variants
  const fadeInUp = {
    initial: { opacity: 0, y: 40 },
    animate: { opacity: 1, y: 0 },
    transition: { duration: 0.6 }
  }

  const staggerContainer = {
    animate: {
      transition: {
        staggerChildren: 0.1
      }
    }
  }

  // Features data
  const features = [
    {
      icon: Database,
      title: 'Data Processing',
      description: 'Advanced analysis of satellite imagery data to detect and quantify methane emissions.',
      color: 'from-blue-500 to-cyan-500',
    },
    {
      icon: Brain,
      title: 'AI Attribution Engine',
      description: 'Advanced machine learning algorithms for precise source attribution and leak identification.',
      color: 'from-purple-500 to-pink-500',
    },
    {
      icon: AlertTriangle,
      title: 'Super-Emitter Detection',
      description: 'Automatically identify and prioritize high-emission events requiring immediate attention.',
      color: 'from-orange-500 to-red-500',
    },
    {
      icon: Bell,
      title: 'Real-Time Alerts',
      description: 'Instant notifications for emission spikes, new leaks, and critical environmental events.',
      color: 'from-green-500 to-emerald-500',
    },
  ]

  // How it works steps
  const steps = [
    {
      number: '01',
      title: 'Data Collection',
      description: 'Satellite imagery is processed to identify methane concentration anomalies.',
      icon: Globe,
    },
    {
      number: '02',
      title: 'AI Analysis',
      description: 'Our AI processes the data to identify emission sources and quantify leaks.',
      icon: Brain,
    },
    {
      number: '03',
      title: 'Action & Reporting',
      description: 'Receive alerts, view interactive maps, and generate compliance reports.',
      icon: BarChart3,
    },
  ]

  // Stats
  const stats = [
    { value: '312+', label: 'Active Leaks Tracked' },
    { value: '4.2M', label: 'Tons CO₂ Equivalent' },
    { value: '24/7', label: 'Continuous Monitoring' },
    { value: '94%', label: 'Detection Accuracy' },
  ]

  return (
    <div className="min-h-screen bg-dark-bg overflow-hidden">
      {/* Animated Background */}
      <div className="fixed inset-0 z-0">
        <div className="absolute inset-0 bg-gradient-to-b from-dark-bg via-dark-bg to-emerald-950/20" />
        
        {/* Animated gradient orbs */}
        <motion.div
          animate={{
            scale: [1, 1.2, 1],
            opacity: [0.3, 0.5, 0.3],
          }}
          transition={{
            duration: 8,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute top-1/4 left-1/4 w-96 h-96 bg-accent-green/20 rounded-full blur-3xl"
        />
        <motion.div
          animate={{
            scale: [1.2, 1, 1.2],
            opacity: [0.2, 0.4, 0.2],
          }}
          transition={{
            duration: 10,
            repeat: Infinity,
            ease: 'easeInOut',
          }}
          className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-blue-500/10 rounded-full blur-3xl"
        />

        {/* Grid pattern */}
        <div 
          className="absolute inset-0 opacity-20"
          style={{
            backgroundImage: `
              linear-gradient(rgba(34, 197, 94, 0.1) 1px, transparent 1px),
              linear-gradient(90deg, rgba(34, 197, 94, 0.1) 1px, transparent 1px)
            `,
            backgroundSize: '50px 50px',
          }}
        />
      </div>

      {/* Navigation */}
      <nav className="relative z-10 border-b border-dark-border/50 backdrop-blur-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-accent-green/20 flex items-center justify-center glow-green">
                <Flame className="w-6 h-6 text-accent-green" />
              </div>
              <span className="text-xl font-bold text-white">
                Methane<span className="text-accent-green">Shadow</span>Hunter
              </span>
            </Link>

            {/* Nav Links */}
            <div className="hidden md:flex items-center gap-8">
              <a href="#features" className="text-gray-400 hover:text-white transition-colors">Features</a>
              <a href="#how-it-works" className="text-gray-400 hover:text-white transition-colors">How It Works</a>
              <a href="#about" className="text-gray-400 hover:text-white transition-colors">About</a>
            </div>

            {/* CTA */}
            <div className="flex items-center gap-4">
              <Link
                to="/login"
                className="hidden sm:inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
              >
                Sign In
              </Link>
              <Link
                to="/signup"
                className="btn-primary flex items-center gap-2"
              >
                <span>Get Started</span>
                <ArrowRight className="w-4 h-4" />
              </Link>
            </div>
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="relative z-10 pt-20 pb-32">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial="initial"
            animate="animate"
            variants={staggerContainer}
            className="text-center"
          >
            {/* Badge */}
            <motion.div
              variants={fadeInUp}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-accent-green/10 border border-accent-green/30 mb-8"
            >
              <div className="w-2 h-2 rounded-full bg-accent-green animate-pulse" />
              <span className="text-sm text-accent-green font-medium">AI-Powered Climate Tech</span>
            </motion.div>

            {/* Headline */}
            <motion.h1
              variants={fadeInUp}
              className="text-5xl sm:text-6xl lg:text-7xl font-bold text-white mb-6 leading-tight"
            >
              Detect Methane.
              <br />
              <span className="bg-gradient-to-r from-accent-green to-emerald-400 bg-clip-text text-transparent">
                Save the Planet.
              </span>
            </motion.h1>

            {/* Subheadline */}
            <motion.p
              variants={fadeInUp}
              className="text-xl text-gray-400 max-w-3xl mx-auto mb-10"
            >
              Satellite-driven methane leakage detection and super-emitter attribution system.
              Monitor emissions in real-time, identify sources, and take action to reduce climate impact.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              variants={fadeInUp}
              className="flex flex-col sm:flex-row items-center justify-center gap-4"
            >
              <Link
                to="/dashboard/map"
                className="btn-primary flex items-center gap-2 text-lg px-8 py-4"
              >
                <Globe className="w-5 h-5" />
                View Live Map
              </Link>
              <Link
                to="/dashboard"
                className="btn-secondary flex items-center gap-2 text-lg px-8 py-4"
              >
                <BarChart3 className="w-5 h-5" />
                Explore Dashboard
              </Link>
            </motion.div>

            {/* Stats */}
            <motion.div
              variants={fadeInUp}
              className="grid grid-cols-2 md:grid-cols-4 gap-8 mt-20 pt-10 border-t border-dark-border/50"
            >
              {stats.map((stat, index) => (
                <div key={index} className="text-center">
                  <p className="text-3xl sm:text-4xl font-bold text-white">{stat.value}</p>
                  <p className="text-sm text-gray-500 mt-1">{stat.label}</p>
                </div>
              ))}
            </motion.div>
          </motion.div>
        </div>
      </section>

      {/* Features Section */}
      <section id="features" className="relative z-10 py-24 bg-dark-card/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              Powerful Features for
              <span className="text-accent-green"> Climate Action</span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              Advanced technology stack combining satellite imagery, artificial intelligence,
              and real-time analytics to combat methane emissions.
            </p>
          </motion.div>

          <div className="grid md:grid-cols-2 lg:grid-cols-4 gap-6">
            {features.map((feature, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.1 }}
                whileHover={{ y: -8, transition: { duration: 0.3 } }}
                className="glass-card p-6 group"
              >
                <div className={`w-14 h-14 rounded-xl bg-gradient-to-br ${feature.color} p-3 mb-4 group-hover:scale-110 transition-transform duration-300`}>
                  <feature.icon className="w-full h-full text-white" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">{feature.title}</h3>
                <p className="text-gray-400">{feature.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="relative z-10 py-24">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            whileInView={{ opacity: 1, y: 0 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="text-center mb-16"
          >
            <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
              How It <span className="text-accent-green">Works</span>
            </h2>
            <p className="text-lg text-gray-400 max-w-2xl mx-auto">
              Three simple steps from detection to action
            </p>
          </motion.div>

          <div className="grid md:grid-cols-3 gap-8 relative">
            {/* Connection line */}
            <div className="hidden md:block absolute top-24 left-1/4 right-1/4 h-0.5 bg-gradient-to-r from-accent-green via-accent-green to-accent-green/30" />

            {steps.map((step, index) => (
              <motion.div
                key={index}
                initial={{ opacity: 0, y: 20 }}
                whileInView={{ opacity: 1, y: 0 }}
                viewport={{ once: true }}
                transition={{ duration: 0.6, delay: index * 0.2 }}
                className="relative text-center"
              >
                {/* Step number */}
                <div className="w-12 h-12 rounded-full bg-accent-green/20 border-2 border-accent-green flex items-center justify-center mx-auto mb-6 relative z-10">
                  <span className="text-accent-green font-bold">{step.number}</span>
                </div>

                {/* Icon */}
                <div className="w-20 h-20 rounded-2xl bg-dark-card border border-dark-border flex items-center justify-center mx-auto mb-6">
                  <step.icon className="w-10 h-10 text-accent-green" />
                </div>

                <h3 className="text-xl font-semibold text-white mb-3">{step.title}</h3>
                <p className="text-gray-400">{step.description}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="relative z-10 py-24">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
          <motion.div
            initial={{ opacity: 0, scale: 0.95 }}
            whileInView={{ opacity: 1, scale: 1 }}
            viewport={{ once: true }}
            transition={{ duration: 0.6 }}
            className="glass-card p-12 text-center relative overflow-hidden"
          >
            {/* Background glow */}
            <div className="absolute -top-1/2 -right-1/2 w-full h-full bg-accent-green/10 rounded-full blur-3xl" />

            <div className="relative z-10">
              <div className="w-16 h-16 rounded-2xl bg-accent-green/20 flex items-center justify-center mx-auto mb-6">
                <Shield className="w-8 h-8 text-accent-green" />
              </div>
              <h2 className="text-3xl sm:text-4xl font-bold text-white mb-4">
                Ready to Track Methane Emissions?
              </h2>
              <p className="text-lg text-gray-400 mb-8 max-w-xl mx-auto">
                Join the fight against climate change with our advanced satellite monitoring platform.
                Start detecting and mitigating methane emissions today.
              </p>
              <div className="flex flex-col sm:flex-row items-center justify-center gap-4">
                <Link
                  to="/dashboard"
                  className="btn-primary flex items-center gap-2 text-lg px-8 py-4"
                >
                  <Zap className="w-5 h-5" />
                  Start Free Trial
                </Link>
                <button className="btn-ghost flex items-center gap-2 text-lg px-8 py-4">
                  <Play className="w-5 h-5" />
                  Watch Demo
                </button>
              </div>
            </div>
          </motion.div>
        </div>
      </section>

      {/* Footer */}
      <footer id="about" className="relative z-10 border-t border-dark-border bg-dark-card/50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12">
          <div className="grid md:grid-cols-4 gap-8">
            {/* Brand */}
            <div className="md:col-span-2">
              <Link to="/" className="flex items-center gap-3 mb-4">
                <div className="w-10 h-10 rounded-lg bg-accent-green/20 flex items-center justify-center">
                  <Flame className="w-6 h-6 text-accent-green" />
                </div>
                <span className="text-xl font-bold text-white">
                  Methane<span className="text-accent-green">Shadow</span>Hunter
                </span>
              </Link>
              <p className="text-gray-400 mb-4 max-w-md">
                AI-powered methane leakage detection and super-emitter attribution system
                for a cleaner, more sustainable future.
              </p>
              <div className="flex items-center gap-4">
                <a href="#" className="p-2 bg-dark-border rounded-lg hover:bg-accent-green/20 transition-colors">
                  <Github className="w-5 h-5 text-gray-400 hover:text-white" />
                </a>
                <a href="#" className="p-2 bg-dark-border rounded-lg hover:bg-accent-green/20 transition-colors">
                  <Twitter className="w-5 h-5 text-gray-400 hover:text-white" />
                </a>
                <a href="#" className="p-2 bg-dark-border rounded-lg hover:bg-accent-green/20 transition-colors">
                  <Linkedin className="w-5 h-5 text-gray-400 hover:text-white" />
                </a>
                <a href="#" className="p-2 bg-dark-border rounded-lg hover:bg-accent-green/20 transition-colors">
                  <Mail className="w-5 h-5 text-gray-400 hover:text-white" />
                </a>
              </div>
            </div>

            {/* Links */}
            <div>
              <h4 className="text-white font-semibold mb-4">Platform</h4>
              <ul className="space-y-2">
                <li><Link to="/dashboard" className="text-gray-400 hover:text-accent-green transition-colors">Dashboard</Link></li>
                <li><Link to="/dashboard/map" className="text-gray-400 hover:text-accent-green transition-colors">Live Map</Link></li>
                <li><Link to="/dashboard/reports" className="text-gray-400 hover:text-accent-green transition-colors">Reports</Link></li>
                <li><a href="#" className="text-gray-400 hover:text-accent-green transition-colors">API Docs</a></li>
              </ul>
            </div>

            <div>
              <h4 className="text-white font-semibold mb-4">Company</h4>
              <ul className="space-y-2">
                <li><a href="#" className="text-gray-400 hover:text-accent-green transition-colors">About Us</a></li>
                <li><a href="#" className="text-gray-400 hover:text-accent-green transition-colors">Careers</a></li>
                <li><a href="#" className="text-gray-400 hover:text-accent-green transition-colors">Contact</a></li>
                <li><a href="#" className="text-gray-400 hover:text-accent-green transition-colors">Privacy Policy</a></li>
              </ul>
            </div>
          </div>

          <div className="border-t border-dark-border mt-12 pt-8 flex flex-col md:flex-row items-center justify-between">
            <p className="text-gray-500 text-sm">
              © 2024 Methane Shadow Hunter. All rights reserved.
            </p>
            <p className="text-gray-500 text-sm mt-2 md:mt-0">
              Built with ❤️ for the planet
            </p>
          </div>
        </div>
      </footer>
    </div>
  )
}

export default Landing
