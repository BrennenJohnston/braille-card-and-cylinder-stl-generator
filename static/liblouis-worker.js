// Web Worker for liblouis translation
// This allows us to use enableOnDemandTableLoading which only works in web workers

let liblouisInstance = null;
let liblouisReady = false;
let recentLogs = [];

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

            try {
                liblouisInstance.registerLogCallback(function(level, msg){
                    try {
                        recentLogs.push(`[${level}] ${msg}`);
                        if (recentLogs.length > 50) {
                            recentLogs.shift();
                        }
                    } catch (_) {}
                });
            } catch (_) {}
            
            // Enable on-demand table loading - this should work in web worker
            if (liblouisInstance.enableOnDemandTableLoading) {
                console.log('Worker: Enabling on-demand table loading...');
                try {
                    // Try the static directory first
                    liblouisInstance.enableOnDemandTableLoading('/static/liblouis/tables/');
                    console.log('Worker: Table loading enabled from static directory');
                } catch (e) {
                    console.log('Worker: Static path failed, trying node_modules path...');
                    try {
                        liblouisInstance.enableOnDemandTableLoading('/node_modules/liblouis-build/tables/');
                        console.log('Worker: Table loading enabled from node_modules');
                    } catch (e2) {
                        console.log('Worker: Both paths failed, trying relative path...');
                        try {
                            liblouisInstance.enableOnDemandTableLoading('static/liblouis/tables/');
                            console.log('Worker: Table loading enabled with relative path');
                        } catch (e3) {
                            console.log('Worker: All table loading attempts failed:', e3.message);
                            // Continue without on-demand loading - tables might be pre-loaded
                        }
                    }
                }
            } else {
                console.log('Worker: enableOnDemandTableLoading not available, tables may be pre-loaded');
            }
            
            liblouisReady = true;
            console.log('Worker: Liblouis initialized successfully');
            
            // Test translation to verify it works
            try {
                const testResult = liblouisInstance.translateString('unicode.dis,en-us-g1.ctb', 'test');
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
                
                // Use the provided table name or default UEB based on grade when not specified
                let selectedTable;
                if (tableName) {
                    selectedTable = tableName;
                } else {
                    selectedTable = grade === 'g2' ? 'en-ueb-g2.ctb' : 'en-ueb-g1.ctb';
                }

                console.log('Worker: Translating text:', text, 'with table:', selectedTable);

                try {
                    // Ensure unicode braille output by adding unicode-braille.utb to the table chain
                    // Use unicode.dis as first table to force Unicode Braille output
                    const tableChain = selectedTable.indexOf('unicode.dis') !== -1
                        ? selectedTable
                        : ('unicode.dis,' + selectedTable);
                    const result = liblouisInstance.translateString(tableChain, text);
                    if (typeof result !== 'string' || result.length === 0) {
                        throw new Error('Liblouis returned empty result');
                    }
                    const hasBrailleChars = result.split('').some(function(char){
                        const code = char.charCodeAt(0);
                        return code >= 0x2800 && code <= 0x28FF;
                    });
                    if (!hasBrailleChars) {
                        throw new Error('Translation produced no braille Unicode output');
                    }
                    self.postMessage({ id, type: 'translate', result: { success: true, translation: result } });
                } catch (e) {
                    var logTail = '';
                    try {
                        var tail = recentLogs.slice(-8).join('\n');
                        if (tail) {
                            logTail = '\nRecent liblouis logs:\n' + tail;
                        }
                    } catch (_) {}
                    const message = 'Translation failed for table ' + selectedTable + ': ' + (e && e.message ? e.message : 'Unknown error') + logTail;
                    throw new Error(message);
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
