// Web Worker for liblouis translation
// This allows us to use enableOnDemandTableLoading which only works in web workers

let liblouisInstance = null;
let liblouisReady = false;

// Import liblouis scripts
importScripts('/node_modules/liblouis-build/build-no-tables-utf16.js');
importScripts('/node_modules/liblouis/easy-api.js');

// Initialize liblouis in the worker
async function initializeLiblouis() {
    try {
        console.log('Worker: Initializing liblouis...');
        
        // Wait for scripts to load
        await new Promise(resolve => setTimeout(resolve, 100));
        
        if (typeof liblouisBuild !== 'undefined' && typeof LiblouisEasyApi !== 'undefined') {
            console.log('Worker: Creating LiblouisEasyApi instance');
            liblouisInstance = new LiblouisEasyApi(liblouisBuild);
            
            // Enable on-demand table loading - this should work in web worker
            if (liblouisInstance.enableOnDemandTableLoading) {
                console.log('Worker: Enabling on-demand table loading...');
                liblouisInstance.enableOnDemandTableLoading('/node_modules/liblouis-build/tables/');
                console.log('Worker: Table loading enabled successfully');
            }
            
            liblouisReady = true;
            console.log('Worker: Liblouis initialized successfully');
            
            // Test translation to verify it works
            try {
                const testResult = liblouisInstance.translateString('en-us-g1.ctb', 'test');
                console.log('Worker: Test translation successful:', testResult);
            } catch (e) {
                console.log('Worker: Test translation failed:', e.message);
            }
            
            return { success: true, message: 'Liblouis initialized successfully' };
        } else {
            throw new Error('Liblouis scripts not loaded properly');
        }
    } catch (error) {
        console.error('Worker: Failed to initialize liblouis:', error);
        return { success: false, error: error.message };
    }
}

// Handle messages from main thread
self.onmessage = async function(e) {
    const { id, type, data } = e.data;
    
    try {
        switch (type) {
            case 'init':
                const initResult = await initializeLiblouis();
                self.postMessage({ id, type: 'init', result: initResult });
                break;
                
            case 'translate':
                if (!liblouisReady || !liblouisInstance) {
                    throw new Error('Liblouis not initialized');
                }
                
                const { text, grade } = data;
                const tableName = grade === 'g2' ? 'en-us-g2.ctb' : 'en-us-g1.ctb';
                
                console.log('Worker: Translating text:', text, 'with table:', tableName);
                
                // Try different table formats
                const tableFormats = [
                    tableName,
                    'unicode.dis,' + tableName
                ];
                
                let result = null;
                let lastError = null;
                
                for (const table of tableFormats) {
                    try {
                        console.log('Worker: Trying table format:', table);
                        result = liblouisInstance.translateString(table, text);
                        if (result) {
                            console.log('Worker: Translation successful with table:', table);
                            break;
                        }
                    } catch (e) {
                        console.log('Worker: Translation failed with table:', table, 'Error:', e.message);
                        lastError = e;
                    }
                }
                
                if (result) {
                    self.postMessage({ id, type: 'translate', result: { success: true, translation: result } });
                } else {
                    throw lastError || new Error('All table formats failed');
                }
                break;
                
            default:
                throw new Error('Unknown message type: ' + type);
        }
    } catch (error) {
        console.error('Worker: Error handling message:', error);
        self.postMessage({ id, type: e.data.type, result: { success: false, error: error.message } });
    }
};

console.log('Worker: Liblouis worker script loaded');
