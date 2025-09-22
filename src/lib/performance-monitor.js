/**
 * Performance Monitor - Real-time performance tracking and optimization
 * Tracks rendering, memory usage, and user experience metrics
 */

export class PerformanceMonitor {
  constructor() {
    this.metrics = new Map();
    this.performanceObserver = null;
    this.memoryTracker = null;
    this.isEnabled = true;
    
    console.log('📊 Performance Monitor initialized');
    this.initializeTracking();
  }

  initializeTracking() {
    // Track page load performance
    this.trackPageLoad();
    
    // Track Core Web Vitals
    this.trackCoreWebVitals();
    
    // Track memory usage
    this.trackMemoryUsage();
    
    // Track STL generation performance
    this.trackSTLGeneration();
  }

  trackPageLoad() {
    if (typeof performance !== 'undefined' && performance.timing && typeof window !== 'undefined') {
      window.addEventListener('load', () => {
        const timing = performance.timing;
        const loadTime = timing.loadEventEnd - timing.navigationStart;
        
        this.recordMetric('page_load_time', loadTime, {
          domReady: timing.domContentLoadedEventEnd - timing.navigationStart,
          firstPaint: this.getFirstPaint(),
          resourcesLoaded: timing.loadEventEnd - timing.domContentLoadedEventEnd
        });
        
        console.log(`📊 Page load: ${loadTime}ms`);
      });
    }
  }

  trackCoreWebVitals() {
    // Track First Contentful Paint (FCP)
    this.observePerformanceEntry('paint', (entries) => {
      entries.forEach(entry => {
        if (entry.name === 'first-contentful-paint') {
          this.recordMetric('fcp', entry.startTime);
          console.log(`🎨 First Contentful Paint: ${entry.startTime.toFixed(1)}ms`);
        }
      });
    });

    // Track Largest Contentful Paint (LCP)
    this.observePerformanceEntry('largest-contentful-paint', (entries) => {
      const lastEntry = entries[entries.length - 1];
      this.recordMetric('lcp', lastEntry.startTime);
      console.log(`🖼️ Largest Contentful Paint: ${lastEntry.startTime.toFixed(1)}ms`);
    });

    // Track First Input Delay (FID) approximation
    this.observePerformanceEntry('first-input', (entries) => {
      entries.forEach(entry => {
        const fid = entry.processingStart - entry.startTime;
        this.recordMetric('fid', fid);
        console.log(`⚡ First Input Delay: ${fid.toFixed(1)}ms`);
      });
    });

    // Track Cumulative Layout Shift (CLS)
    this.observePerformanceEntry('layout-shift', (entries) => {
      let clsValue = 0;
      entries.forEach(entry => {
        if (!entry.hadRecentInput) {
          clsValue += entry.value;
        }
      });
      this.recordMetric('cls', clsValue);
    });
  }

  trackMemoryUsage() {
    if (performance.memory) {
      this.memoryTracker = setInterval(() => {
        const memory = performance.memory;
        const memoryUsage = {
          used: memory.usedJSHeapSize,
          total: memory.totalJSHeapSize,
          limit: memory.jsHeapSizeLimit,
          usagePercent: (memory.usedJSHeapSize / memory.jsHeapSizeLimit) * 100
        };
        
        this.recordMetric('memory_usage', memoryUsage.usagePercent, memoryUsage);
        
        // Warn if memory usage is high
        if (memoryUsage.usagePercent > 80) {
          console.warn(`🧠 High memory usage: ${memoryUsage.usagePercent.toFixed(1)}%`);
        }
        
      }, 5000); // Check every 5 seconds
    }
  }

  trackSTLGeneration() {
    // This will be called by the STL generation process
    this.stlGenerationMetrics = {
      totalGenerations: 0,
      averageTime: 0,
      memoryPeaks: [],
      errorRate: 0,
      successRate: 0
    };
  }

  observePerformanceEntry(type, callback) {
    if (typeof window !== 'undefined' && 'PerformanceObserver' in window) {
      try {
        const observer = new PerformanceObserver((list) => {
          callback(list.getEntries());
        });
        observer.observe({ entryTypes: [type] });
      } catch (error) {
        console.warn(`Performance tracking for ${type} not supported:`, error);
      }
    }
  }

  getFirstPaint() {
    const paintEntries = performance.getEntriesByType('paint');
    const firstPaint = paintEntries.find(entry => entry.name === 'first-paint');
    return firstPaint ? firstPaint.startTime : 0;
  }

  // Method to be called by STL generation workflow
  startSTLGeneration(options = {}) {
    const generationId = `stl_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    
    const startMetrics = {
      id: generationId,
      startTime: performance.now(),
      startMemory: performance.memory?.usedJSHeapSize || 0,
      options: {
        shapeType: options.shapeType,
        textLength: options.textLength,
        complexity: options.complexity
      }
    };
    
    this.metrics.set(generationId, startMetrics);
    console.log(`🚀 STL Generation started: ${generationId}`);
    
    return generationId;
  }

  endSTLGeneration(generationId, result = {}) {
    const startMetrics = this.metrics.get(generationId);
    if (!startMetrics) return;
    
    const endTime = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
    const duration = endTime - (startMetrics.startTime || 0);
    const endMemory = performance.memory?.usedJSHeapSize || 0;
    const memoryDelta = endMemory - startMetrics.startMemory;
    
    const finalMetrics = {
      ...startMetrics,
      endTime,
      duration,
      endMemory,
      memoryDelta,
      success: result.success !== false,
      fileSize: result.fileSize || 0,
      triangles: result.triangles || 0,
      error: result.error || null
    };
    
    this.metrics.set(generationId, finalMetrics);
    
    // Update aggregate metrics
    this.updateSTLAggregates(finalMetrics);
    
    console.log(`✅ STL Generation completed: ${duration.toFixed(1)}ms, ${(memoryDelta / 1024 / 1024).toFixed(1)}MB memory`);
    
    // Report to analytics if available
    this.reportToAnalytics(finalMetrics);
    
    return finalMetrics;
  }

  updateSTLAggregates(metrics) {
    const agg = this.stlGenerationMetrics;
    agg.totalGenerations++;
    
    if (metrics.success) {
      agg.averageTime = ((agg.averageTime * (agg.totalGenerations - 1)) + metrics.duration) / agg.totalGenerations;
      agg.successRate = (agg.successRate * (agg.totalGenerations - 1) + 1) / agg.totalGenerations;
    } else {
      agg.errorRate = (agg.errorRate * (agg.totalGenerations - 1) + 1) / agg.totalGenerations;
    }
    
    if (metrics.memoryDelta > 0) {
      agg.memoryPeaks.push(metrics.memoryDelta);
      // Keep only last 10 measurements
      if (agg.memoryPeaks.length > 10) {
        agg.memoryPeaks.shift();
      }
    }
  }

  recordMetric(name, value, metadata = {}) {
    const metric = {
      name,
      value,
      timestamp: Date.now(),
      url: typeof window !== 'undefined' && window.location ? window.location.href : 'node',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent.substring(0, 100) : 'node',
      metadata
    };
    
    // Store in local metrics
    if (!this.metrics.has('page_metrics')) {
      this.metrics.set('page_metrics', []);
    }
    this.metrics.get('page_metrics').push(metric);
    
    // Keep only last 50 metrics
    const pageMetrics = this.metrics.get('page_metrics');
    if (pageMetrics.length > 50) {
      pageMetrics.shift();
    }
  }

  reportToAnalytics(metrics) {
    // Google Analytics 4 integration (if available)
    if (typeof gtag !== 'undefined') {
      gtag('event', 'stl_generation_complete', {
        event_category: 'Performance',
        event_label: metrics.options.shapeType,
        value: Math.round(metrics.duration),
        custom_parameters: {
          memory_used_mb: Math.round(metrics.memoryDelta / 1024 / 1024),
          file_size_kb: Math.round(metrics.fileSize / 1024),
          triangle_count: metrics.triangles,
          success: metrics.success
        }
      });
    }
    
    // Custom analytics endpoint (if configured)
    if (window.customAnalytics) {
      window.customAnalytics.track('stl_generation', metrics);
    }
  }

  getPerformanceReport() {
    const report = {
      timestamp: new Date().toISOString(),
      pageMetrics: this.metrics.get('page_metrics') || [],
      stlMetrics: this.stlGenerationMetrics,
      currentMemory: (typeof performance !== 'undefined' && performance.memory) ? {
        used: performance.memory.usedJSHeapSize,
        total: performance.memory.totalJSHeapSize,
        limit: performance.memory.jsHeapSizeLimit,
        usagePercent: (performance.memory.usedJSHeapSize / performance.memory.jsHeapSizeLimit) * 100
      } : null,
      connection: (typeof navigator !== 'undefined' && navigator.connection) ? {
        effectiveType: navigator.connection.effectiveType,
        downlink: navigator.connection.downlink,
        rtt: navigator.connection.rtt
      } : null,
      deviceInfo: {
        cores: (typeof navigator !== 'undefined' && navigator.hardwareConcurrency) ? navigator.hardwareConcurrency : 'unknown',
        platform: typeof navigator !== 'undefined' ? navigator.platform : 'node',
        mobile: typeof navigator !== 'undefined' ? /Mobile|Android|iPhone|iPad/.test(navigator.userAgent) : false
      }
    };
    
    return report;
  }

  exportPerformanceData() {
    const report = this.getPerformanceReport();
    const blob = new Blob([JSON.stringify(report, null, 2)], { 
      type: 'application/json' 
    });
    
    if (typeof URL !== 'undefined' && typeof document !== 'undefined') {
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `braille-stl-performance-${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    }
    
    console.log('📊 Performance data exported');
  }

  getOptimizationRecommendations() {
    const report = this.getPerformanceReport();
    const recommendations = [];
    
    // Check Core Web Vitals
    const fcp = this.getLatestMetric('fcp');
    const lcp = this.getLatestMetric('lcp');
    const cls = this.getLatestMetric('cls');
    
    if (fcp > 1800) {
      recommendations.push({
        type: 'critical',
        metric: 'FCP',
        current: `${fcp.toFixed(1)}ms`,
        target: '<1800ms',
        suggestions: ['Reduce bundle size', 'Enable resource hints', 'Optimize critical CSS']
      });
    }
    
    if (lcp > 2500) {
      recommendations.push({
        type: 'critical', 
        metric: 'LCP',
        current: `${lcp.toFixed(1)}ms`,
        target: '<2500ms',
        suggestions: ['Optimize large images', 'Preload key resources', 'Reduce server response time']
      });
    }
    
    if (cls > 0.1) {
      recommendations.push({
        type: 'warning',
        metric: 'CLS', 
        current: cls.toFixed(3),
        target: '<0.1',
        suggestions: ['Set image dimensions', 'Reserve space for dynamic content', 'Avoid inserting content above existing content']
      });
    }
    
    // Check memory usage
    const avgMemory = this.stlGenerationMetrics.memoryPeaks.length > 0 ? 
      this.stlGenerationMetrics.memoryPeaks.reduce((a, b) => a + b, 0) / this.stlGenerationMetrics.memoryPeaks.length : 0;
    
    if (avgMemory > 100 * 1024 * 1024) { // 100MB
      recommendations.push({
        type: 'warning',
        metric: 'Memory Usage',
        current: `${(avgMemory / 1024 / 1024).toFixed(1)}MB`,
        target: '<100MB',
        suggestions: ['Implement geometry streaming', 'Add memory cleanup', 'Use lower-poly models for preview']
      });
    }
    
    // Check generation time
    if (this.stlGenerationMetrics.averageTime > 10000) { // 10 seconds
      recommendations.push({
        type: 'info',
        metric: 'Generation Time',
        current: `${(this.stlGenerationMetrics.averageTime / 1000).toFixed(1)}s`,
        target: '<10s',
        suggestions: ['Implement spatial indexing', 'Use worker pools', 'Optimize CSG operations']
      });
    }
    
    return recommendations;
  }

  getLatestMetric(name) {
    const pageMetrics = this.metrics.get('page_metrics') || [];
    const metric = pageMetrics.filter(m => m.name === name).pop();
    return metric ? metric.value : 0;
  }

  // Real-time performance dashboard
  createPerformanceDashboard() {
    const dashboard = document.createElement('div');
    dashboard.id = 'performance-dashboard';
    dashboard.style.cssText = `
      position: fixed;
      top: 10px;
      right: 10px;
      background: rgba(0,0,0,0.8);
      color: white;
      padding: 10px;
      border-radius: 8px;
      font-family: monospace;
      font-size: 12px;
      z-index: 10000;
      max-width: 300px;
      display: none;
    `;
    
    document.body.appendChild(dashboard);
    
    // Update dashboard every second
    setInterval(() => {
      this.updateDashboard(dashboard);
    }, 1000);
    
    // Toggle with Ctrl+Shift+P
    document.addEventListener('keydown', (e) => {
      if (e.ctrlKey && e.shiftKey && e.key === 'P') {
        dashboard.style.display = dashboard.style.display === 'none' ? 'block' : 'none';
      }
    });
    
    return dashboard;
  }

  updateDashboard(dashboard) {
    const memory = performance.memory;
    const report = this.getPerformanceReport();
    
    dashboard.innerHTML = `
      <div style="font-weight: bold; margin-bottom: 8px;">🚀 Performance Monitor</div>
      
      <div>💾 Memory: ${memory ? (memory.usedJSHeapSize / 1024 / 1024).toFixed(1) : 'N/A'}MB</div>
      <div>⚡ Generations: ${this.stlGenerationMetrics.totalGenerations}</div>
      <div>📊 Avg Time: ${(this.stlGenerationMetrics.averageTime / 1000).toFixed(1)}s</div>
      <div>✅ Success Rate: ${(this.stlGenerationMetrics.successRate * 100).toFixed(1)}%</div>
      
      <div style="margin-top: 8px; font-size: 10px;">
        🎯 FCP: ${this.getLatestMetric('fcp').toFixed(0)}ms<br>
        🖼️ LCP: ${this.getLatestMetric('lcp').toFixed(0)}ms<br>
        📐 CLS: ${this.getLatestMetric('cls').toFixed(3)}
      </div>
      
      <div style="margin-top: 8px; font-size: 10px; opacity: 0.7;">
        Press Ctrl+Shift+P to toggle
      </div>
    `;
  }

  // Integration with Cloudflare Analytics
  setupCloudflareAnalytics() {
    // Cloudflare Web Analytics integration
    if (window.cloudflareAnalytics) {
      // Send custom events to Cloudflare Analytics
      const sendEvent = (eventName, data) => {
        cloudflareAnalytics('track', eventName, data);
      };
      
      // Track STL generations
      document.addEventListener('stl-generation-complete', (event) => {
        sendEvent('stl_generation', {
          duration: event.detail.duration,
          shape_type: event.detail.shapeType,
          file_size: event.detail.fileSize,
          success: event.detail.success
        });
      });
    }
  }

  // Automatic performance optimization
  enableAutoOptimization() {
    console.log('🔧 Enabling automatic performance optimization...');
    
    // Adaptive quality based on device performance
    this.adaptiveQuality = {
      enabled: true,
      baseQuality: 1.0,
      currentQuality: 1.0,
      adjustmentFactor: 0.1
    };
    
    // Monitor frame rate and adjust quality
    let lastFrameTime = performance.now();
    let frameCount = 0;
    let fps = 60;
    
    const measureFPS = () => {
      frameCount++;
      const now = performance.now();
      
      if (now - lastFrameTime >= 1000) {
        fps = frameCount;
        frameCount = 0;
        lastFrameTime = now;
        
        // Adjust quality based on FPS
        if (fps < 30 && this.adaptiveQuality.currentQuality > 0.5) {
          this.adaptiveQuality.currentQuality -= this.adaptiveQuality.adjustmentFactor;
          console.log(`📉 Reduced quality to ${this.adaptiveQuality.currentQuality.toFixed(1)} (FPS: ${fps})`);
        } else if (fps > 50 && this.adaptiveQuality.currentQuality < this.adaptiveQuality.baseQuality) {
          this.adaptiveQuality.currentQuality += this.adaptiveQuality.adjustmentFactor;
          console.log(`📈 Increased quality to ${this.adaptiveQuality.currentQuality.toFixed(1)} (FPS: ${fps})`);
        }
      }
      
      requestAnimationFrame(measureFPS);
    };
    
    requestAnimationFrame(measureFPS);
  }

  getCurrentQuality() {
    return this.adaptiveQuality?.currentQuality || 1.0;
  }

  dispose() {
    if (this.memoryTracker) {
      clearInterval(this.memoryTracker);
    }
    
    if (this.performanceObserver) {
      this.performanceObserver.disconnect();
    }
    
    console.log('📊 Performance Monitor disposed');
  }
}
