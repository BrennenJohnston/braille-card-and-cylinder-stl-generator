/**
 * WorkerManager - Orchestrates Web Worker jobs and communication
 * Provides a clean API for managing geometry and liblouis workers
 */

export class WorkerManager {
  constructor() {
    this.workers = new Map();
    this.activeJobs = new Map();
    this.jobCounter = 0;
    
    console.log('🎭 WorkerManager initialized');
  }

  /**
   * Get or create a worker of specified type
   * @param {string} type - Worker type ('geometry' or 'liblouis')
   * @returns {Promise<Worker>} Worker instance
   */
  async getWorker(type) {
    if (!this.workers.has(type)) {
      console.log(`🔧 Creating ${type} worker...`);
      
      let worker;
      try {
        if (type === 'geometry') {
          // Use Vite's worker import syntax
          worker = new Worker(
            new URL('../workers/geometry-worker.js', import.meta.url),
            { type: 'module' }
          );
        } else if (type === 'liblouis') {
          // Use existing liblouis worker
          worker = new Worker('/liblouis-worker.js');
        } else {
          throw new Error(`Unknown worker type: ${type}`);
        }
        
        // Initialize worker
        await this.initializeWorker(worker, type);
        this.workers.set(type, worker);
        
        console.log(`✅ ${type} worker created and initialized`);
        
      } catch (error) {
        console.error(`❌ Failed to create ${type} worker:`, error);
        throw new Error(`Failed to create ${type} worker: ${error.message}`);
      }
    }
    
    return this.workers.get(type);
  }

  /**
   * Initialize a worker and wait for ready signal
   * @param {Worker} worker - Worker instance
   * @param {string} type - Worker type
   * @returns {Promise<void>}
   */
  async initializeWorker(worker, type) {
    return new Promise((resolve, reject) => {
      const timeout = setTimeout(() => {
        reject(new Error(`${type} worker initialization timeout (10s)`));
      }, 10000);

      const handleMessage = (event) => {
        if (event.data.type === 'READY') {
          clearTimeout(timeout);
          worker.removeEventListener('message', handleMessage);
          console.log(`🎯 ${type} worker ready`);
          resolve(event.data.capabilities || {});
        } else if (event.data.type === 'ERROR') {
          clearTimeout(timeout);
          worker.removeEventListener('message', handleMessage);
          reject(new Error(`${type} worker initialization error: ${event.data.error.message}`));
        }
      };

      const handleError = (error) => {
        clearTimeout(timeout);
        worker.removeEventListener('message', handleMessage);
        worker.removeEventListener('error', handleError);
        reject(new Error(`${type} worker error: ${error.message}`));
      };

      worker.addEventListener('message', handleMessage);
      worker.addEventListener('error', handleError);
      
      // Send initialization message
      worker.postMessage({ type: 'INIT', id: this.generateJobId() });
    });
  }

  /**
   * Generate STL file from braille text
   * @param {string} shapeType - 'card' or 'cylinder'
   * @param {string[]} brailleLines - Array of braille Unicode text lines
   * @param {Object} options - Generation options
   * @param {Function} onProgress - Progress callback
   * @returns {Promise<ArrayBuffer>} STL binary data
   */
  async generateSTL(shapeType, brailleLines, options = {}, onProgress = null) {
    console.log(`🏭 Starting STL generation: ${shapeType}`);
    console.log(`Input: ${brailleLines.length} lines of braille text`);
    
    const worker = await this.getWorker('geometry');
    const jobId = this.generateJobId();
    
    return new Promise((resolve, reject) => {
      // Store job info
      const job = { 
        resolve, 
        reject, 
        onProgress, 
        type: 'generation',
        shapeType,
        startTime: Date.now()
      };
      this.activeJobs.set(jobId, job);

      // Set up message handler
      const handleMessage = (event) => {
        const { type: msgType, id, progress, result, error, message } = event.data;
        
        if (id !== jobId) return; // Not our job
        
        console.log(`📨 Worker message: ${msgType} for job ${id}`);

        switch (msgType) {
          case 'PROGRESS':
            if (onProgress) {
              onProgress(progress, message);
            }
            break;
            
          case 'GENERATION_COMPLETE':
            // Continue to STL export
            this.exportGeometryToSTL(worker, result.geometry, jobId, {
              onProgress: (exportProgress, exportMessage) => {
                // Map export progress to 90-100% range
                const totalProgress = 90 + (exportProgress * 0.1);
                if (onProgress) {
                  onProgress(totalProgress, exportMessage || 'Exporting to STL...');
                }
              }
            });
            break;
            
          case 'EXPORT_COMPLETE':
            worker.removeEventListener('message', handleMessage);
            this.activeJobs.delete(jobId);
            
            // Combine generation and export stats
            const combinedStats = {
              ...result.stats,
              totalTime: Date.now() - job.startTime,
              fileSize: result.data.byteLength || result.data.length
            };
            
            resolve({
              stlBuffer: result.data,
              format: result.format,
              stats: combinedStats
            });
            break;
            
          case 'ERROR':
            worker.removeEventListener('message', handleMessage);
            this.activeJobs.delete(jobId);
            const errorMsg = error.message || 'Unknown worker error';
            console.error(`❌ Worker error for job ${jobId}:`, errorMsg);
            reject(new Error(errorMsg));
            break;
            
          case 'CANCELLED':
            worker.removeEventListener('message', handleMessage);
            this.activeJobs.delete(jobId);
            reject(new Error('Job was cancelled'));
            break;
        }
      };

      worker.addEventListener('message', handleMessage);
      
      // Send generation request
      const messageType = shapeType === 'card' ? 'GENERATE_CARD' : 'GENERATE_CYLINDER';
      worker.postMessage({
        type: messageType,
        id: jobId,
        data: { brailleLines, options }
      });
    });
  }

  /**
   * Export generated geometry to STL
   * @private
   */
  async exportGeometryToSTL(worker, geometry, jobId, options = {}) {
    console.log(`📤 Exporting geometry to STL for job ${jobId}`);
    
    worker.postMessage({
      type: 'EXPORT_STL',
      id: jobId,
      data: { 
        geometry, 
        format: options.format || 'binary' 
      }
    });
  }

  /**
   * Translate text to braille using liblouis worker
   * @param {string} text - Text to translate
   * @param {string} table - Braille table (optional)
   * @returns {Promise<string>} Braille Unicode text
   */
  async translateToBraille(text, table = 'en-us-g1.ctb') {
    console.log(`🔤 Translating text to braille: "${text.substring(0, 50)}..."`);
    
    const worker = await this.getWorker('liblouis');
    const jobId = this.generateJobId();
    
    return new Promise((resolve, reject) => {
      const job = { resolve, reject, type: 'translation', startTime: Date.now() };
      this.activeJobs.set(jobId, job);

      const handleMessage = (event) => {
        // Handle liblouis worker response format
        if (event.data.result) {
          worker.removeEventListener('message', handleMessage);
          this.activeJobs.delete(jobId);
          resolve(event.data.result);
        } else if (event.data.error) {
          worker.removeEventListener('message', handleMessage);
          this.activeJobs.delete(jobId);
          reject(new Error(`Translation error: ${event.data.error}`));
        }
      };

      const timeout = setTimeout(() => {
        worker.removeEventListener('message', handleMessage);
        this.activeJobs.delete(jobId);
        reject(new Error('Translation timeout'));
      }, 10000);

      worker.addEventListener('message', (event) => {
        clearTimeout(timeout);
        handleMessage(event);
      });
      
      // Send translation request (liblouis worker format)
      worker.postMessage({
        text,
        table,
        id: jobId
      });
    });
  }

  /**
   * Cancel an active job
   * @param {string} jobId - Job ID to cancel
   */
  cancelJob(jobId) {
    const job = this.activeJobs.get(jobId);
    if (!job) {
      console.log(`⚠️ No active job found with ID: ${jobId}`);
      return;
    }

    console.log(`🚫 Cancelling job: ${jobId}`);

    // Find which worker has this job and send cancel message
    for (const [workerType, worker] of this.workers) {
      worker.postMessage({
        type: 'CANCEL',
        id: jobId
      });
    }

    // Clean up job
    this.activeJobs.delete(jobId);
    job.reject(new Error('Job cancelled by user'));
  }

  /**
   * Get status of all workers and active jobs
   * @returns {Object} Status information
   */
  async getStatus() {
    const status = {
      workers: {},
      activeJobs: this.activeJobs.size,
      totalJobs: this.jobCounter
    };

    // Get status from each worker
    for (const [type, worker] of this.workers) {
      const statusJobId = this.generateJobId();
      
      try {
        const workerStatus = await new Promise((resolve, reject) => {
          const timeout = setTimeout(() => reject(new Error('Status timeout')), 2000);
          
          const handleMessage = (event) => {
            if (event.data.type === 'STATUS' && event.data.id === statusJobId) {
              clearTimeout(timeout);
              worker.removeEventListener('message', handleMessage);
              resolve(event.data.status);
            }
          };
          
          worker.addEventListener('message', handleMessage);
          worker.postMessage({ type: 'GET_STATUS', id: statusJobId });
        });
        
        status.workers[type] = workerStatus;
      } catch (error) {
        status.workers[type] = { error: error.message };
      }
    }

    return status;
  }

  /**
   * Terminate all workers and clean up
   */
  terminate() {
    console.log('🧹 Terminating WorkerManager...');
    
    // Cancel all active jobs
    for (const [jobId, job] of this.activeJobs) {
      job.reject(new Error('WorkerManager terminated'));
    }
    this.activeJobs.clear();
    
    // Terminate all workers
    for (const [type, worker] of this.workers) {
      try {
        worker.terminate();
        console.log(`✅ Terminated ${type} worker`);
      } catch (error) {
        console.warn(`⚠️ Error terminating ${type} worker:`, error);
      }
    }
    this.workers.clear();
    
    console.log('✅ WorkerManager terminated');
  }

  /**
   * Generate unique job ID
   * @private
   */
  generateJobId() {
    return `job_${++this.jobCounter}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get active job count
   */
  getActiveJobCount() {
    return this.activeJobs.size;
  }

  /**
   * Check if workers are available
   */
  areWorkersReady() {
    return this.workers.size > 0;
  }
}
