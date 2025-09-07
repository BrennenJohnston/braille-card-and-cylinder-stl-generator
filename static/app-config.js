// Runtime configuration for static deployments (e.g., GitHub Pages)
// Override API_BASE_URL at deploy-time if backend is on a different origin
// Example: window.APP_CONFIG = { API_BASE_URL: 'https://your-vercel-app.vercel.app' };
window.APP_CONFIG = window.APP_CONFIG || {
    API_BASE_URL: '' // empty = same origin
};



