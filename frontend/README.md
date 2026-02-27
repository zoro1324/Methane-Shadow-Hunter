# Methane Shadow Hunter - Frontend

A production-ready React frontend for a climate-tech AI platform focused on satellite-driven methane leakage detection and super-emitter attribution.

![Methane Shadow Hunter](https://img.shields.io/badge/React-18.2.0-blue) ![Tailwind CSS](https://img.shields.io/badge/Tailwind-3.4.0-blue) ![Vite](https://img.shields.io/badge/Vite-5.0.0-purple)

## 🌍 Overview

Methane Shadow Hunter is a modern, responsive web dashboard for monitoring methane emissions globally. The platform:

- **Detects** methane plumes from satellite data
- **Identifies** super-emitter events
- **Pinpoints** leaking valves and pipes
- **Provides** real-time analytics and alert systems
- **Uses** AI/ML for plume detection and attribution

## 🚀 Quick Start

### Prerequisites

- Node.js 18.x or higher
- npm 9.x or higher

### Installation

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will open at `http://localhost:3000`

### Build for Production

```bash
# Create production build
npm run build

# Preview production build
npm run preview
```

## 📁 Project Structure

```
frontend/
├── public/
│   └── favicon.svg
├── src/
│   ├── components/
│   │   ├── cards/
│   │   │   └── StatCard.jsx
│   │   ├── charts/
│   │   │   └── Charts.jsx
│   │   ├── layout/
│   │   │   └── DashboardLayout.jsx
│   │   ├── tables/
│   │   │   └── DataTable.jsx
│   │   └── ui/
│   │       ├── AlertCard.jsx
│   │       └── Common.jsx
│   ├── data/
│   │   └── mockData.js
│   ├── pages/
│   │   ├── Alerts.jsx
│   │   ├── Dashboard.jsx
│   │   ├── Landing.jsx
│   │   ├── LiveMap.jsx
│   │   ├── Reports.jsx
│   │   └── SuperEmitters.jsx
│   ├── services/
│   │   └── api.js
│   ├── App.jsx
│   ├── index.css
│   └── main.jsx
├── index.html
├── package.json
├── postcss.config.js
├── tailwind.config.js
└── vite.config.js
```

## 🎨 Tech Stack

| Technology | Purpose |
|------------|---------|
| **React 18** | UI Framework |
| **Vite** | Build Tool & Dev Server |
| **Tailwind CSS** | Utility-first Styling |
| **React Router** | Client-side Routing |
| **Recharts** | Data Visualization |
| **Leaflet + React-Leaflet** | Interactive Maps |
| **Framer Motion** | Animations |
| **Lucide React** | Icon Library |
| **Axios** | HTTP Client |

## 🖥️ Pages

### 1. Landing Page (`/`)
- Hero section with animated background
- Features showcase
- How it works flow
- Call-to-action buttons

### 2. Dashboard Overview (`/dashboard`)
- Statistics cards (Active Leaks, CO₂ Equivalent, High-Risk Zones, Satellites)
- Emission trend charts
- Regional distribution
- Severity pie chart
- Recent alerts

### 3. Live Map (`/dashboard/map`)
- Interactive Leaflet map with dark theme
- Color-coded markers by risk level
- Emission radius visualization
- Filter controls
- Marker popups with details

### 4. Super Emitters (`/dashboard/super-emitters`)
- Sortable/filterable data table
- Status indicators
- Confidence scores
- Detail modal on row click
- CSV export

### 5. Reports (`/dashboard/reports`)
- Monthly summaries
- Downloadable PDF reports
- Analytics charts
- Export options (PDF, CSV)

### 6. Alerts (`/dashboard/alerts`)
- Notification center
- Filter by type (Critical, Warning, Info, Success)
- Mark as read functionality
- Notification preferences

## 🎯 Design System

### Colors

| Color | Tailwind Class | Hex | Usage |
|-------|---------------|-----|-------|
| Dark Background | `bg-dark-bg` | `#0f172a` | Main background |
| Dark Card | `bg-dark-card` | `#1e293b` | Card backgrounds |
| Green Accent | `text-accent-green` | `#22c55e` | Primary actions, success |
| Danger Red | `text-danger-red` | `#ef4444` | Critical alerts, errors |
| Warning Yellow | `text-warning-yellow` | `#eab308` | Warnings |
| Info Blue | `text-info-blue` | `#3b82f6` | Information |

### Components

- **Glass Cards**: Glassmorphism effect with blur
- **Stat Cards**: Animated statistics with trends
- **Data Tables**: Sortable, filterable, paginated
- **Alert Cards**: Severity-based styling
- **Buttons**: Primary, Secondary, Ghost, Outline variants

## ⚙️ Configuration

### Environment Variables

Create a `.env` file:

```env
VITE_API_URL=http://localhost:8000/api
```

### Tailwind Configuration

Custom theme extensions in `tailwind.config.js`:
- Custom colors for dark theme
- Animation utilities
- Glassmorphism utilities

## 🔌 API Integration

The `src/services/api.js` file contains pre-configured service methods for:

- **Emissions**: Trends, regional data, severity distribution
- **Super Emitters**: CRUD operations, status updates
- **Map**: Markers, heatmap data
- **Alerts**: Notifications, preferences
- **Reports**: Generation, export, download
- **Auth**: Login, logout, profile

Currently uses mock data from `src/data/mockData.js`. Backend integration ready.

## 📱 Responsive Design

- Mobile-first approach
- Collapsible sidebar on mobile
- Responsive grid layouts
- Touch-friendly interactions

## 🎬 Animations

Powered by Framer Motion:
- Page transitions
- Card entrance animations
- Hover effects
- Loading states
- Modal animations

## 📦 Dependencies

```json
{
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "react-router-dom": "^7.0.0",
    "axios": "^1.7.0",
    "recharts": "^2.15.0",
    "leaflet": "^1.9.4",
    "react-leaflet": "^5.0.0",
    "framer-motion": "^12.0.0",
    "lucide-react": "^0.470.0"
  },
  "devDependencies": {
    "vite": "^6.0.0",
    "@vitejs/plugin-react": "^5.0.0",
    "tailwindcss": "^3.4.0",
    "postcss": "^8.5.0",
    "autoprefixer": "^10.4.0"
  }
}
```

## 🚀 Deployment

### Vercel

```bash
npm run build
vercel deploy
```

### Docker

```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "run", "preview"]
```

### Static Hosting

Build files are output to `dist/`. Deploy to any static host (Netlify, AWS S3, etc.).

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📄 License

MIT License - see LICENSE file for details.

---

Built with ❤️ for climate action | **Detect Methane. Save the Planet.**
