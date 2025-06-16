# iTow VMS Mobile Application

## Overview
This directory contains the mobile application components for the iTow Vehicle Management System, including both Progressive Web App (PWA) capabilities and native mobile app development.

## Architecture

### Progressive Web App (PWA)
- **Framework**: React with TypeScript
- **Build Tool**: Vite for fast development and building
- **PWA Features**: Service workers, offline capabilities, push notifications
- **UI Library**: Material-UI for consistent design
- **State Management**: Redux Toolkit for app state

### Native Mobile Apps
- **Framework**: React Native with Expo
- **Platforms**: iOS and Android
- **Offline Storage**: SQLite with async storage
- **Camera Integration**: Expo Camera for document scanning
- **Push Notifications**: Expo Notifications

## Features

### Core Functionality
- [x] Vehicle search and filtering
- [x] Real-time status updates
- [x] Document capture and upload
- [x] AI-powered insights
- [x] Offline data synchronization

### Advanced Features
- [x] Barcode/QR code scanning
- [x] GPS location tracking
- [x] Voice commands (NLP integration)
- [x] Augmented reality vehicle identification
- [x] Biometric authentication

## Development Setup

### Prerequisites
- Node.js 18+
- npm or yarn
- Expo CLI (for React Native)
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)

### Installation
```bash
cd mobile
npm install
npm run dev  # Start PWA development server
npm run mobile  # Start Expo development server
```

## Deployment

### PWA Deployment
- Built as part of main Flask application
- Served from `/static/pwa/` directory
- Automatic service worker registration

### Mobile App Deployment
- iOS: App Store via TestFlight
- Android: Google Play Store via Internal Testing
- Over-the-air updates via Expo

## File Structure
```
mobile/
├── pwa/                 # Progressive Web App
│   ├── src/
│   ├── public/
│   └── package.json
├── native/              # React Native App
│   ├── src/
│   ├── app.json
│   └── package.json
└── shared/              # Shared utilities and types
    ├── api/
    ├── types/
    └── utils/
```
