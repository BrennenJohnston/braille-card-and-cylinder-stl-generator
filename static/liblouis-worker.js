// Web Worker for liblouis translation
// This allows us to use enableOnDemandTableLoading which only works in web workers

let liblouisInstance = null;
let liblouisReady = false;
// Remember working fallbacks to avoid repeated failing attempts and console noise
const tableResolutionCache = Object.create(null);
// Track support for UEB tables in the current liblouis build
const uebSupport = { g1: false, g2: false };
// Default tables decided at init based on support detection
const defaultTables = { g1: 'en-us-g1.ctb', g2: 'en-us-g2.ctb' };

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
            
            // Reduce log verbosity in production; only surface warnings/errors
            try {
                if (liblouisInstance.setLogLevel && liblouisInstance.LOG) {
                    liblouisInstance.setLogLevel(liblouisInstance.LOG.WARN);
                }
                if (liblouisInstance.registerLogCallback && liblouisInstance.LOG) {
                    liblouisInstance.registerLogCallback((lvl, msg) => {
                        // Only log ERROR/FATAL from liblouis to avoid console spam
                        if (lvl >= liblouisInstance.LOG.ERROR) {
                            console.error('[liblouis]', msg);
                        }
                    });
                }
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
            
            // Detect UEB table support of the embedded liblouis build
            try {
                uebSupport.g1 = !!liblouisInstance.checkTable('en-ueb-g1.ctb');
            } catch (_) { uebSupport.g1 = false; }
            try {
                uebSupport.g2 = !!liblouisInstance.checkTable('en-ueb-g2.ctb');
            } catch (_) { uebSupport.g2 = false; }

            if (uebSupport.g1) { defaultTables.g1 = 'en-ueb-g1.ctb'; }
            if (uebSupport.g2) { defaultTables.g2 = 'en-ueb-g2.ctb'; }
            console.log('Worker: Table defaults ->', JSON.stringify(defaultTables));

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
                    // Pick the best available default determined at init
                    selectedTable = (grade === 'g2' ? defaultTables.g2 : defaultTables.g1);
                }
                
                console.log('Worker: Translating text:', text, 'with table:', selectedTable);
                
                // Try using just the table name first, without unicode.dis prefix
                // This should work if the table is properly configured for Unicode output
                console.log('Worker: Using table:', selectedTable);
                
                // If we've already resolved a better working table for this selection, use it immediately
                if (tableResolutionCache[selectedTable]) {
                    try {
                        const cachedTable = tableResolutionCache[selectedTable];
                        const cachedResult = liblouisInstance.translateString(cachedTable, text);
                        if (cachedResult && typeof cachedResult === 'string') {
                            const hasBrailleChars = cachedResult.split('').some(ch => {
                                const c = ch.charCodeAt(0);
                                return c >= 0x2800 && c <= 0x28FF;
                            });
                            if (hasBrailleChars) {
                                self.postMessage({ id, type: 'translate', result: { success: true, translation: cachedResult } });
                                return;
                            }
                        }
                        // If cached table unexpectedly stops working, drop cache and continue with full strategy
                        delete tableResolutionCache[selectedTable];
                    } catch (e) {
                        // Drop cache on error and proceed to resolution attempts
                        delete tableResolutionCache[selectedTable];
                    }
                }

                const tryTables = [];
                // Primary: requested or default
                tryTables.push(selectedTable);
                tryTables.push('unicode.dis,' + selectedTable);

                // Additional safe fallbacks: prefer en-us variants first on builds lacking UEB support
                if (/en-ueb-g1\.ctb$/i.test(selectedTable) || (!uebSupport.g1 && /g1/.test(selectedTable))) {
                    tryTables.push('en-us-g1.ctb');
                    tryTables.push('unicode.dis,en-us-g1.ctb');
                    tryTables.push('UEBC-g1.utb');
                    tryTables.push('unicode.dis,UEBC-g1.utb');
                } else if (/en-ueb-g2\.ctb$/i.test(selectedTable) || (!uebSupport.g2 && /g2/.test(selectedTable))) {
                    tryTables.push('en-us-g2.ctb');
                    tryTables.push('unicode.dis,en-us-g2.ctb');
                    tryTables.push('UEBC-g2.ctb');
                    tryTables.push('unicode.dis,UEBC-g2.ctb');
                }

                let lastError = null;
                for (let i = 0; i < tryTables.length; i++) {
                    const table = tryTables[i];
                    try {
                        const result = liblouisInstance.translateString(table, text);
                        if (result && typeof result === 'string') {
                            const hasBrailleChars = result.split('').some(char => {
                                const code = char.charCodeAt(0);
                                return code >= 0x2800 && code <= 0x28FF;
                            });
                            if (hasBrailleChars) {
                                console.log('Worker: Translation successful with table:', table);
                                // Remember resolution for this selectedTable to skip failing attempts next time
                                if (table !== selectedTable) {
                                    tableResolutionCache[selectedTable] = table;
                                }
                                self.postMessage({ id, type: 'translate', result: { success: true, translation: result } });
                                return;
                            }
                        }
                        lastError = new Error('No braille chars in output');
                    } catch (err) {
                        lastError = err;
                        console.log('Worker: Translation attempt failed with table', table, '-', err && err.message ? err.message : err);
                    }
                }
                throw lastError || new Error('Translation failed: Unknown error');
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
