# Sistemas Olivium - Network Monitoring System (v2.0)

## Overview

This is a modernized, professional network monitoring system built for "Sistemas Olivium" that provides real-time monitoring of network devices. The application has been completely updated with a modern interface, optimized performance, and professional styling. It performs continuous network scanning using ICMP ping and TCP port checks to monitor device availability across specified IP ranges. The system features a responsive web dashboard with light/dark mode, sticky header, professional footer, and enhanced PDF export capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## Version 2.0 Modernization Features

### Frontend Modernization
- **Modern Professional Design**: Complete UI/UX overhaul with clean, professional styling
- **Light/Dark Mode Toggle**: Manual switching with browser preference persistence
- **Sticky Header**: "Sistemas Olivium" header remains visible during scrolling
- **Professional Footer**: Dynamic copyright footer adapting to themes
- **Responsive Design**: Fully responsive across all devices and screen sizes
- **Status Animations**: Smooth animations for status changes and updates
- **Enhanced Visual Indicators**: Modern color schemes and gradients

### Backend Optimization
- **Performance Improvements**: Optimized threading with 32 worker pool
- **Smart Caching**: Intelligent machine list caching (5-minute intervals)
- **Error Handling**: Comprehensive error handling and logging
- **Invalid IP Filtering**: Automatic filtering of malformed IP addresses
- **Reduced Timeouts**: Optimized ping timeouts (800ms) for better responsiveness
- **Database Optimization**: Enhanced SQLite configuration with connection pooling

### Enhanced PDF Export
- **Professional Styling**: Modern PDF design matching dashboard aesthetics
- **Complete Branding**: Header and footer with "Sistemas Olivium" branding
- **Executive Summary**: Statistics and availability percentages
- **Modern Color Scheme**: Professional blues and grays
- **Dynamic Year**: Automatic copyright year updates

## System Architecture

### Backend Architecture
- **Framework**: Flask web application with SQLAlchemy ORM
- **Database**: SQLite for storing historical monitoring data
- **Monitoring Engine**: Multi-threaded network scanning using ThreadPoolExecutor
- **Data Models**: HostHistory table tracking device status over time
- **Configuration**: CSV-based machine definitions with configurable network ranges

### Frontend Architecture
- **UI Framework**: Tailwind CSS for responsive design
- **JavaScript**: Vanilla JS with Axios for API communication
- **Real-time Updates**: Periodic AJAX polling to refresh device status
- **Template Engine**: Jinja2 templates served by Flask

### Network Monitoring Design
- **Dual Detection**: ICMP ping combined with TCP port scanning (3389, 445, 80)
- **Concurrency**: Thread pool executor with configurable worker limits (64 max workers)
- **Scanning Strategy**: Continuous background scanning at 10-second intervals
- **Cross-platform Support**: Windows and Linux compatible ping implementations

### Data Storage Strategy
- **SQLite Database**: Single-file database for historical status tracking
- **In-memory Cache**: Real-time status cache for quick API responses
- **CSV Configuration**: External machine list management for easy administration

### Error Handling and Performance
- **Timeout Management**: Configurable ping timeouts (1000ms default)
- **Latency Tracking**: Response time measurement and storage
- **Concurrent Processing**: Parallel network checks to minimize scan time

## External Dependencies

### Python Libraries
- **Flask**: Web framework for API and template serving
- **SQLAlchemy**: ORM for database operations and schema management
- **Threading/Concurrent.futures**: Multi-threaded network scanning

### Frontend Dependencies
- **Tailwind CSS**: CDN-based styling framework for responsive UI
- **Axios**: HTTP client for API communication

### System Dependencies
- **Platform-specific ping**: Native OS ping commands for network testing
- **Socket operations**: TCP port connectivity testing
- **CSV file handling**: Machine configuration management

### Network Infrastructure
- **Local Network Access**: Requires network access to target IP ranges
- **ICMP/TCP Permissions**: May require elevated privileges for network operations