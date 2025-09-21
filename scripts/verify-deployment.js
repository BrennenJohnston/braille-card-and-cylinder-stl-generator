#!/usr/bin/env node
/**
 * Deployment Verification Script
 * Validates that the build is ready for Cloudflare Pages deployment
 */

import fs from 'fs/promises';
import path from 'path';

class DeploymentVerifier {
  constructor() {
    this.checks = [];
    this.warnings = [];
    this.errors = [];
  }

  async verify() {
    console.log('🔍 Cloudflare Pages Deployment Verification');
    console.log('=' .repeat(50));
    console.log('📋 Checking build readiness for production deployment...\n');

    try {
      await this.checkBuildOutput();
      await this.checkRequiredFiles();
      await this.checkFileIntegrity();
      await this.checkAssetSizes();
      await this.checkConfiguration();
      await this.checkSecurityHeaders();
      
      this.generateReport();
      
    } catch (error) {
      console.error('❌ Verification failed:', error.message);
      process.exit(1);
    }
  }

  async checkBuildOutput() {
    console.log('📦 Checking build output...');
    
    try {
      const distStats = await fs.stat('dist');
      if (!distStats.isDirectory()) {
        throw new Error('dist directory not found');
      }
      
      this.addCheck('Build directory exists', true);
      console.log('  ✅ Build directory: present');
      
    } catch (error) {
      this.addCheck('Build directory exists', false, 'Run npm run build first');
      throw new Error('Build output not found. Run: npm run build');
    }
  }

  async checkRequiredFiles() {
    console.log('\n📄 Checking required files...');
    
    const requiredFiles = {
      'index.html': { minSize: 500, description: 'Main HTML entry point' },
      'main.js': { minSize: 10000, description: 'Application bundle' },
      'geometry-worker.js': { minSize: 10000, description: 'Geometry processing worker' },
      'liblouis-worker.js': { minSize: 1000, description: 'Braille translation worker' },
      'liblouis/build-no-tables-utf16.js': { minSize: 50000, description: 'Liblouis core' },
      'liblouis/easy-api.js': { minSize: 1000, description: 'Liblouis API' }
    };
    
    for (const [file, requirements] of Object.entries(requiredFiles)) {
      try {
        const filePath = path.join('dist', file);
        const stats = await fs.stat(filePath);
        const sizeKB = (stats.size / 1024).toFixed(1);
        
        if (stats.size < requirements.minSize) {
          this.addCheck(`${file} size`, false, `File too small: ${sizeKB} KB`);
          console.log(`  ❌ ${file}: ${sizeKB} KB (too small)`);
        } else {
          this.addCheck(`${file} exists`, true);
          console.log(`  ✅ ${file}: ${sizeKB} KB`);
        }
        
      } catch (error) {
        this.addCheck(`${file} exists`, false, 'File missing');
        console.log(`  ❌ ${file}: missing`);
      }
    }
  }

  async checkFileIntegrity() {
    console.log('\n🔍 Checking file integrity...');
    
    // Check HTML structure
    try {
      const htmlContent = await fs.readFile('dist/index.html', 'utf-8');
      
      if (!htmlContent.includes('<!DOCTYPE html>')) {
        this.addWarning('HTML doctype missing');
      }
      
      if (!htmlContent.includes('src="/main.js"') && !htmlContent.includes('src="./main.js"')) {
        this.addWarning('Main.js script tag not found in HTML');
      }
      
      this.addCheck('HTML integrity', true);
      console.log('  ✅ HTML structure: valid');
      
    } catch (error) {
      this.addCheck('HTML integrity', false, error.message);
      console.log('  ❌ HTML structure: invalid');
    }
    
    // Check JavaScript syntax (basic)
    try {
      const mainJS = await fs.readFile('dist/main.js', 'utf-8');
      
      // Basic syntax checks
      if (mainJS.includes('import ') && mainJS.includes('export ')) {
        this.addCheck('JavaScript ES modules', true);
        console.log('  ✅ JavaScript: ES modules detected');
      } else {
        this.addWarning('No ES modules detected in main.js');
      }
      
      // Check for worker references
      if (mainJS.includes('Worker') || mainJS.includes('worker')) {
        this.addCheck('Worker integration', true);
        console.log('  ✅ Workers: integration detected');
      } else {
        this.addWarning('No worker integration detected');
      }
      
    } catch (error) {
      this.addCheck('JavaScript integrity', false, error.message);
      console.log('  ❌ JavaScript: invalid');
    }
  }

  async checkAssetSizes() {
    console.log('\n📊 Analyzing asset sizes...');
    
    const sizeTargets = {
      'main.js': { max: 100 * 1024, warning: 80 * 1024 }, // 100KB max, warn at 80KB
      'geometry-worker.js': { max: 2 * 1024 * 1024, warning: 1.5 * 1024 * 1024 }, // 2MB max, warn at 1.5MB
      'liblouis-worker.js': { max: 10 * 1024, warning: 8 * 1024 } // 10KB max, warn at 8KB
    };
    
    let totalSize = 0;
    
    for (const [file, limits] of Object.entries(sizeTargets)) {
      try {
        const filePath = path.join('dist', file);
        const stats = await fs.stat(filePath);
        const sizeKB = (stats.size / 1024).toFixed(1);
        
        totalSize += stats.size;
        
        if (stats.size > limits.max) {
          this.addCheck(`${file} size`, false, `File too large: ${sizeKB} KB`);
          console.log(`  ❌ ${file}: ${sizeKB} KB (exceeds ${(limits.max / 1024).toFixed(0)} KB limit)`);
        } else if (stats.size > limits.warning) {
          this.addWarning(`${file} approaching size limit: ${sizeKB} KB`);
          console.log(`  ⚠️  ${file}: ${sizeKB} KB (large)`);
        } else {
          this.addCheck(`${file} size`, true);
          console.log(`  ✅ ${file}: ${sizeKB} KB`);
        }
        
      } catch (error) {
        console.log(`  ❓ ${file}: not found`);
      }
    }
    
    const totalMB = (totalSize / 1024 / 1024).toFixed(1);
    console.log(`\n  📊 Total bundle size: ${totalMB} MB`);
    
    if (totalSize > 10 * 1024 * 1024) { // 10MB
      this.addWarning(`Large total bundle size: ${totalMB} MB`);
    } else {
      this.addCheck('Total bundle size', true);
    }
  }

  async checkConfiguration() {
    console.log('\n⚙️ Checking configuration files...');
    
    const configFiles = [
      { file: 'cloudflare/_headers', description: 'Cloudflare headers' },
      { file: 'cloudflare/_redirects', description: 'URL redirects' },
      { file: 'wrangler.toml', description: 'Wrangler configuration' },
      { file: '.github/workflows/cloudflare-deploy.yml', description: 'GitHub Actions workflow' }
    ];
    
    for (const { file, description } of configFiles) {
      try {
        await fs.access(file);
        this.addCheck(`${description} config`, true);
        console.log(`  ✅ ${description}: configured`);
      } catch (error) {
        this.addCheck(`${description} config`, false, 'File missing');
        console.log(`  ❌ ${description}: missing`);
      }
    }
  }

  async checkSecurityHeaders() {
    console.log('\n🔒 Checking security configuration...');
    
    try {
      const headersContent = await fs.readFile('cloudflare/_headers', 'utf-8');
      
      const securityHeaders = [
        'X-Content-Type-Options',
        'X-Frame-Options', 
        'X-XSS-Protection',
        'Content-Security-Policy',
        'Referrer-Policy'
      ];
      
      for (const header of securityHeaders) {
        if (headersContent.includes(header)) {
          this.addCheck(`${header} header`, true);
          console.log(`  ✅ ${header}: configured`);
        } else {
          this.addCheck(`${header} header`, false, 'Header missing');
          console.log(`  ❌ ${header}: missing`);
        }
      }
      
    } catch (error) {
      this.addCheck('Security headers', false, 'Headers file not found');
      console.log('  ❌ Security headers: configuration missing');
    }
  }

  addCheck(name, passed, details = '') {
    this.checks.push({ name, passed, details });
  }

  addWarning(message) {
    this.warnings.push(message);
  }

  addError(message) {
    this.errors.push(message);
  }

  generateReport() {
    console.log('\n' + '='.repeat(50));
    console.log('📋 DEPLOYMENT VERIFICATION REPORT');
    console.log('='.repeat(50));
    
    const passedChecks = this.checks.filter(c => c.passed).length;
    const totalChecks = this.checks.length;
    const successRate = ((passedChecks / totalChecks) * 100).toFixed(1);
    
    console.log(`\n✅ Passed checks: ${passedChecks}/${totalChecks} (${successRate}%)`);
    console.log(`⚠️  Warnings: ${this.warnings.length}`);
    console.log(`❌ Errors: ${this.errors.length}`);
    
    // Show failed checks
    const failedChecks = this.checks.filter(c => !c.passed);
    if (failedChecks.length > 0) {
      console.log('\n❌ Failed Checks:');
      failedChecks.forEach(check => {
        console.log(`  - ${check.name}: ${check.details}`);
      });
    }
    
    // Show warnings
    if (this.warnings.length > 0) {
      console.log('\n⚠️  Warnings:');
      this.warnings.forEach(warning => {
        console.log(`  - ${warning}`);
      });
    }
    
    // Deployment readiness
    const isReady = failedChecks.length === 0 && this.errors.length === 0;
    
    console.log('\n🎯 Deployment Status:');
    if (isReady) {
      console.log('  🟢 READY FOR DEPLOYMENT');
      console.log('  ✅ All critical checks passed');
      console.log('  🚀 Safe to deploy to Cloudflare Pages');
      
      console.log('\n📋 Next Steps:');
      console.log('  1. Set environment variables (see env.template)');
      console.log('  2. Run: npm run deploy');
      console.log('  3. Or use GitHub Actions for automated deployment');
      
    } else {
      console.log('  🔴 NOT READY FOR DEPLOYMENT');
      console.log('  ❌ Critical issues must be resolved first');
      console.log('  🔧 Fix the issues above and run verification again');
    }
    
    console.log('\n🌐 Cloudflare Pages Features:');
    console.log('  ⚡ Global CDN with edge caching');
    console.log('  🔒 Automatic HTTPS and security headers');
    console.log('  📊 Built-in analytics and monitoring');
    console.log('  🔄 Automatic deployments via Git');
    console.log('  📱 Optimized for mobile and desktop');
    
    console.log(`\n🎉 Braille STL Generator v2.0 Deployment Verification Complete!`);
    
    return isReady;
  }
}

// Run verification if called directly
if (import.meta.url === `file://${process.argv[1]}`) {
  const verifier = new DeploymentVerifier();
  const isReady = await verifier.verify();
  process.exit(isReady ? 0 : 1);
}

export { DeploymentVerifier };
