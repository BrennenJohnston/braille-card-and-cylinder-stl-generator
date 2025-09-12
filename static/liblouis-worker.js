// Web Worker for liblouis translation
// This allows us to use enableOnDemandTableLoading which only works in web workers

let liblouisInstance = null;
let liblouisReady = false;

// Import liblouis scripts with error handling
try {
    console.log('Worker: Attempting to load liblouis scripts from static directory...');
    importScripts('/static/liblouis/build-no-tables-utf16.js');
    console.log('Worker: Loaded build-no-tables-utf16.js');
    importScripts('/static/liblouis/easy-api.js');
    console.log('Worker: Loaded easy-api.js');
} catch (error) {
    console.error('Worker: Failed to load liblouis scripts from static:', error);
    // Try original paths as fallback
    try {
        console.log('Worker: Trying original node_modules paths...');
        importScripts('/node_modules/liblouis-build/build-no-tables-utf16.js');
        importScripts('/node_modules/liblouis/easy-api.js');
        console.log('Worker: Loaded scripts with node_modules paths');
    } catch (altError) {
        console.error('Worker: All paths failed:', altError);
        throw new Error('Could not load liblouis scripts: ' + error.message);
    }
}

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
                try {
                    liblouisInstance.enableOnDemandTableLoading('/static/liblouis/tables/');
                    console.log('Worker: Table loading enabled from static directory');
                } catch (e) {
                    console.log('Worker: Static path failed, trying node_modules path...');
                    liblouisInstance.enableOnDemandTableLoading('/node_modules/liblouis-build/tables/');
                    console.log('Worker: Table loading enabled from node_modules');
                }
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
                
                const { text, grade, tableName } = data;
                
                // Use the provided table name or fall back to default English UEB tables
                let selectedTable;
                if (tableName) {
                    selectedTable = tableName;
                } else {
                    // Default to English UEB if no table specified
                    selectedTable = grade === 'g2' ? 'en-ueb-g2.ctb' : 'en-ueb-g1.ctb';
                }
                
                console.log('Worker: Translating text:', text, 'with table:', selectedTable);
                
                // Use the correct table format to get Unicode braille output
                // The 'unicode.dis' table must come first to ensure Unicode output
                const tableFormat = 'unicode.dis,' + selectedTable;
                
                console.log('Worker: Using table format:', tableFormat);
                
                try {
                    const result = liblouisInstance.translateString(tableFormat, text);
                    console.log('Worker: Translation successful:', result);
                    
                    // Verify the result contains proper braille Unicode characters
                    const hasBrailleChars = result.split('').some(char => {
                        const code = char.charCodeAt(0);
                        return code >= 0x2800 && code <= 0x28FF;
                    });
                    
                    if (hasBrailleChars) {
                        console.log('Worker: Result contains proper braille Unicode characters');
                        self.postMessage({ id, type: 'translate', result: { success: true, translation: result } });
                    } else {
                        console.log('Worker: Result does not contain braille Unicode, trying alternative approach');
                        // If we still get liblouis format, try to convert it using the library's internal methods
                        // This is a fallback - ideally the unicode.dis table should give us Unicode directly
                        throw new Error('Translation result is not in Unicode braille format');
                    }
                } catch (e) {
                    console.log('Worker: Translation failed:', e.message);
                    throw e;
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
