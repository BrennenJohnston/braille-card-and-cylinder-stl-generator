/**
 * File Utilities for Braille STL Generator
 * Handle file downloads, validation, and format conversions
 */

/**
 * Download file blob to user's computer
 * @param {Blob|ArrayBuffer} data - File data
 * @param {string} filename - Filename with extension
 * @param {string} mimeType - MIME type (optional, auto-detected)
 */
export function downloadFile(data, filename, mimeType = null) {
  console.log(`💾 Downloading file: ${filename}`);
  
  let blob;
  
  // Convert ArrayBuffer to Blob if necessary
  if (data instanceof ArrayBuffer) {
    const detectedMimeType = mimeType || getMimeTypeFromExtension(filename);
    blob = new Blob([data], { type: detectedMimeType });
  } else if (data instanceof Blob) {
    blob = data;
  } else {
    throw new Error('Invalid data type for file download');
  }
  
  // Create download link
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.style.display = 'none';
  
  // Trigger download
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  
  // Clean up object URL
  URL.revokeObjectURL(url);
  
  console.log(`✅ File download initiated: ${filename} (${formatFileSize(blob.size)})`);
}

/**
 * Get MIME type from file extension
 * @param {string} filename - Filename with extension
 * @returns {string} MIME type
 */
export function getMimeTypeFromExtension(filename) {
  const extension = filename.split('.').pop().toLowerCase();
  
  const mimeTypes = {
    'stl': 'application/octet-stream',
    'obj': 'text/plain',
    'ply': 'application/octet-stream',
    'json': 'application/json',
    'txt': 'text/plain',
    'log': 'text/plain'
  };
  
  return mimeTypes[extension] || 'application/octet-stream';
}

/**
 * Format file size in human-readable format
 * @param {number} bytes - Size in bytes
 * @returns {string} Formatted size string
 */
export function formatFileSize(bytes) {
  if (bytes === 0) return '0 Bytes';
  
  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Validate file extension
 * @param {string} filename - Filename to validate
 * @param {string[]} allowedExtensions - Array of allowed extensions
 * @returns {boolean} True if valid
 */
export function validateFileExtension(filename, allowedExtensions) {
  const extension = filename.split('.').pop().toLowerCase();
  return allowedExtensions.includes(extension);
}

/**
 * Generate safe filename from text
 * @param {string} text - Source text
 * @param {string} extension - File extension
 * @param {number} maxLength - Maximum filename length
 * @returns {string} Safe filename
 */
export function generateSafeFilename(text, extension = 'stl', maxLength = 100) {
  // Remove or replace invalid characters
  const safe = text
    .replace(/[<>:"/\\|?*]/g, '-')  // Replace invalid chars with dash
    .replace(/\s+/g, '_')           // Replace spaces with underscore
    .replace(/[^\w\-_.]/g, '')      // Remove non-alphanumeric chars
    .toLowerCase();
  
  // Truncate if too long
  const maxNameLength = maxLength - extension.length - 1; // -1 for the dot
  const truncated = safe.length > maxNameLength ? 
    safe.substring(0, maxNameLength) : safe;
  
  return `${truncated}.${extension}`;
}

/**
 * Read file as text
 * @param {File} file - File object
 * @returns {Promise<string>} File contents as text
 */
export function readFileAsText(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = (e) => reject(new Error('Failed to read file'));
    
    reader.readAsText(file);
  });
}

/**
 * Read file as ArrayBuffer
 * @param {File} file - File object  
 * @returns {Promise<ArrayBuffer>} File contents as ArrayBuffer
 */
export function readFileAsArrayBuffer(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    
    reader.onload = (e) => resolve(e.target.result);
    reader.onerror = (e) => reject(new Error('Failed to read file'));
    
    reader.readAsArrayBuffer(file);
  });
}

/**
 * Create and download log file
 * @param {Array<string>} logLines - Array of log messages
 * @param {string} filename - Log filename
 */
export function downloadLog(logLines, filename = 'braille-generator-log.txt') {
  const timestamp = new Date().toISOString();
  const header = [
    `Braille STL Generator - Log File`,
    `Generated: ${timestamp}`,
    `Version: 2.0.0 - Cloudflare Pages Edition`,
    ``,
    `${'='.repeat(50)}`,
    ``
  ];
  
  const fullLog = [...header, ...logLines].join('\n');
  const blob = new Blob([fullLog], { type: 'text/plain' });
  
  downloadFile(blob, filename);
}

/**
 * Export generation settings as JSON
 * @param {Object} settings - Generation settings
 * @param {string} filename - Settings filename
 */
export function exportSettings(settings, filename = 'braille-settings.json') {
  const exportData = {
    version: '2.0.0',
    timestamp: new Date().toISOString(),
    settings: settings
  };
  
  const json = JSON.stringify(exportData, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  
  downloadFile(blob, filename);
}

/**
 * Import settings from JSON file
 * @param {File} file - JSON settings file
 * @returns {Promise<Object>} Parsed settings
 */
export async function importSettings(file) {
  if (!validateFileExtension(file.name, ['json'])) {
    throw new Error('Invalid file type. Please select a JSON file.');
  }
  
  const text = await readFileAsText(file);
  
  try {
    const data = JSON.parse(text);
    
    if (!data.settings) {
      throw new Error('Invalid settings file format');
    }
    
    return data.settings;
  } catch (error) {
    throw new Error(`Failed to parse settings file: ${error.message}`);
  }
}

/**
 * Check browser download support
 * @returns {boolean} True if downloads are supported
 */
export function isDownloadSupported() {
  // Check for required APIs
  return !!(
    window.Blob &&
    window.URL &&
    window.URL.createObjectURL &&
    document.createElement &&
    document.body
  );
}

/**
 * Estimate download time based on file size
 * @param {number} bytes - File size in bytes
 * @param {number} speedMbps - Connection speed in Mbps (default: 10)
 * @returns {string} Estimated time string
 */
export function estimateDownloadTime(bytes, speedMbps = 10) {
  const speedBytesPerSecond = (speedMbps * 1024 * 1024) / 8; // Convert Mbps to bytes/sec
  const seconds = bytes / speedBytesPerSecond;
  
  if (seconds < 1) {
    return 'Less than 1 second';
  } else if (seconds < 60) {
    return `${Math.ceil(seconds)} seconds`;
  } else {
    const minutes = Math.ceil(seconds / 60);
    return `${minutes} minute${minutes > 1 ? 's' : ''}`;
  }
}
