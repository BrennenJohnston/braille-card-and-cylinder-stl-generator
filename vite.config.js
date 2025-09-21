import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: '.',
  publicDir: 'public',
  base: '/', // Ensure proper base path for Cloudflare Pages
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        main: resolve(process.cwd(), 'index.html'),
        'geometry-worker': resolve(process.cwd(), 'src/workers/geometry-worker.js'),
        'liblouis-worker': resolve(process.cwd(), 'src/workers/liblouis-worker.js')
      },
      output: {
        entryFileNames: '[name].js',
        chunkFileNames: 'chunks/[name]-[hash].js',
        assetFileNames: 'assets/[name]-[hash].[ext]',
        // Manual chunking for better caching
        manualChunks: {
          'three': ['three'],
          'three-bvh-csg': ['three-bvh-csg'],
          'worker-utils': ['comlink', 'idb']
        }
      }
    },
    target: 'esnext',
    minify: 'terser',
    terserOptions: {
      compress: {
        drop_console: process.env.NODE_ENV === 'production',
        drop_debugger: true,
        pure_funcs: ['console.log', 'console.debug']
      },
      mangle: {
        safari10: true
      }
    },
    chunkSizeWarningLimit: 1000, // Allow large chunks for 3D libraries
    // Optimize for Cloudflare Pages
    sourcemap: false, // Disable sourcemaps for production
    reportCompressedSize: false // Skip gzip size reporting for faster builds
  },
  worker: {
    format: 'es',
    rollupOptions: {
      output: {
        entryFileNames: 'workers/[name].js',
        format: 'es'
      }
    }
  },
  server: {
    port: 3000,
    open: true,
    cors: true
  },
  preview: {
    port: 4173,
    open: true,
    cors: true
  },
  // Optimize dependencies for Cloudflare Pages
  optimizeDeps: {
    include: [
      'three',
      'three-bvh-csg', 
      'comlink',
      'idb'
    ],
    exclude: [
      'three-stlexporter' // Already bundled
    ]
  },
  // Define environment variables
  define: {
    __APP_VERSION__: JSON.stringify(process.env.npm_package_version || '2.0.0'),
    __BUILD_TIME__: JSON.stringify(new Date().toISOString()),
    __CLOUDFLARE_PAGES__: JSON.stringify(process.env.VITE_CLOUDFLARE_PAGES === 'true')
  }
});
