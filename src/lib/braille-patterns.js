/**
 * Braille Pattern Mapping and Utilities
 * Handles conversion between text, braille Unicode, and dot patterns
 */

// Standard 6-dot braille cell positions
// 1 4
// 2 5
// 3 6
export const BRAILLE_DOT_POSITIONS = {
  1: { x: 0, y: 0 },
  2: { x: 0, y: 1 },
  3: { x: 0, y: 2 },
  4: { x: 1, y: 0 },
  5: { x: 1, y: 1 },
  6: { x: 1, y: 2 }
};

// 8-dot braille adds:
// 7 8 (below the 6-dot cell)
export const BRAILLE_DOT_POSITIONS_8 = {
  ...BRAILLE_DOT_POSITIONS,
  7: { x: 0, y: 3 },
  8: { x: 1, y: 3 }
};

/**
 * Convert braille Unicode character to dot pattern
 * @param {string} char - Braille Unicode character (U+2800 to U+28FF)
 * @returns {number[]} Array of dot positions (1-8)
 */
export function unicodeToDots(char) {
  if (!char || typeof char !== 'string') {
    return [];
  }

  const codePoint = char.charCodeAt(0);
  
  // Braille Unicode block starts at U+2800 (⠀)
  if (codePoint < 0x2800 || codePoint > 0x28FF) {
    return [];
  }
  
  const pattern = codePoint - 0x2800;
  const dots = [];
  
  // Each bit represents a dot (bits 0-7 = dots 1-8)
  // Bit mapping: bit 0 = dot 1, bit 1 = dot 2, etc.
  for (let i = 0; i < 8; i++) {
    if (pattern & (1 << i)) {
      dots.push(i + 1);
    }
  }
  
  return dots;
}

/**
 * Convert dot pattern to braille Unicode
 * @param {number[]} dots - Array of dot positions (1-8)
 * @returns {string} Braille Unicode character
 */
export function dotsToUnicode(dots) {
  if (!Array.isArray(dots)) {
    return '⠀'; // Empty braille character
  }
  
  let pattern = 0;
  
  // Set bits for each dot
  for (const dot of dots) {
    if (dot >= 1 && dot <= 8) {
      pattern |= (1 << (dot - 1));
    }
  }
  
  return String.fromCharCode(0x2800 + pattern);
}

/**
 * Parse liblouis output to dot patterns
 * @param {string} brailleText - Liblouis translated text
 * @returns {Array<Array<number[]>>} 2D array of dot patterns
 */
export function parseBrailleText(brailleText) {
  if (!brailleText || typeof brailleText !== 'string') {
    return [];
  }

  const lines = brailleText.split('\n').filter(line => line.trim());
  return lines.map(line => {
    const characters = Array.from(line.trim());
    return characters.map(char => unicodeToDots(char));
  });
}

/**
 * Convert regular text to braille dots (basic ASCII mapping)
 * This is a fallback for when liblouis is not available
 * @param {string} text - Regular text
 * @returns {Array<Array<number[]>>} 2D array of dot patterns
 */
export function textToBrailleDots(text) {
  // Basic braille mappings for common characters
  const basicBrailleMap = {
    'a': [1],
    'b': [1, 2],
    'c': [1, 4],
    'd': [1, 4, 5],
    'e': [1, 5],
    'f': [1, 2, 4],
    'g': [1, 2, 4, 5],
    'h': [1, 2, 5],
    'i': [2, 4],
    'j': [2, 4, 5],
    'k': [1, 3],
    'l': [1, 2, 3],
    'm': [1, 3, 4],
    'n': [1, 3, 4, 5],
    'o': [1, 3, 5],
    'p': [1, 2, 3, 4],
    'q': [1, 2, 3, 4, 5],
    'r': [1, 2, 3, 5],
    's': [2, 3, 4],
    't': [2, 3, 4, 5],
    'u': [1, 3, 6],
    'v': [1, 2, 3, 6],
    'w': [2, 4, 5, 6],
    'x': [1, 3, 4, 6],
    'y': [1, 3, 4, 5, 6],
    'z': [1, 3, 5, 6],
    ' ': [], // Space
    '.': [2, 5, 6],
    ',': [2],
    '?': [2, 6],
    '!': [2, 3, 5]
  };

  const lines = text.toLowerCase().split('\n');
  return lines.map(line => {
    const characters = Array.from(line);
    return characters.map(char => basicBrailleMap[char] || []);
  });
}

/**
 * Validate braille dot patterns
 * @param {Array<Array<number[]>>} brailleMatrix - 2D array of dot patterns
 * @returns {boolean} True if valid
 */
export function validateBrailleMatrix(brailleMatrix) {
  if (!Array.isArray(brailleMatrix)) {
    return false;
  }

  for (const row of brailleMatrix) {
    if (!Array.isArray(row)) {
      return false;
    }
    
    for (const cell of row) {
      if (!Array.isArray(cell)) {
        return false;
      }
      
      // Check if all dots are valid (1-8)
      for (const dot of cell) {
        if (!Number.isInteger(dot) || dot < 1 || dot > 8) {
          return false;
        }
      }
    }
  }
  
  return true;
}

/**
 * Get braille matrix dimensions
 * @param {Array<Array<number[]>>} brailleMatrix - 2D array of dot patterns
 * @returns {Object} {rows, cols, totalCells, totalDots}
 */
export function getBrailleMatrixStats(brailleMatrix) {
  if (!Array.isArray(brailleMatrix) || brailleMatrix.length === 0) {
    return { rows: 0, cols: 0, totalCells: 0, totalDots: 0 };
  }

  const rows = brailleMatrix.length;
  const cols = Math.max(...brailleMatrix.map(row => row.length));
  let totalCells = 0;
  let totalDots = 0;

  for (const row of brailleMatrix) {
    for (const cell of row) {
      totalCells++;
      totalDots += Array.isArray(cell) ? cell.length : 0;
    }
  }

  return { rows, cols, totalCells, totalDots };
}

/**
 * Create test braille patterns for development
 * @param {string} type - 'alphabet', 'numbers', 'hello', or 'test'
 * @returns {Array<Array<number[]>>} Test braille matrix
 */
export function createTestPattern(type = 'hello') {
  switch (type) {
    case 'hello':
      return [
        [[1, 2, 5], [1, 5], [1, 2, 3], [1, 2, 3], [1, 3, 5]], // "HELLO"
      ];
    
    case 'alphabet':
      return [
        [[1], [1, 2], [1, 4], [1, 4, 5], [1, 5]], // A B C D E
        [[1, 2, 4], [1, 2, 4, 5], [1, 2, 5], [2, 4], [2, 4, 5]] // F G H I J
      ];
    
    case 'numbers':
      return [
        [[1, 4, 5, 6], [1, 2], [1, 4], [1, 4, 5], [1, 5], [1, 2, 4]] // Numbers 1-6
      ];
    
    case 'test':
      return [
        [[1, 2, 3, 4, 5, 6]], // Full cell for testing
        [[], [1], [1, 2], [1, 2, 3]] // Various patterns
      ];
    
    default:
      return [[[1, 2, 5], [1, 5], [1, 2, 3], [1, 2, 3], [1, 3, 5]]]; // HELLO
  }
}

/**
 * Debug: Print braille matrix in readable format
 * @param {Array<Array<number[]>>} brailleMatrix - 2D array of dot patterns
 */
export function debugPrintBrailleMatrix(brailleMatrix) {
  console.log('🔤 Braille Matrix Debug:');
  
  brailleMatrix.forEach((row, rowIndex) => {
    const unicodeChars = row.map(cell => dotsToUnicode(cell)).join('');
    const dotPatterns = row.map(cell => `[${cell.join(',')}]`).join(' ');
    
    console.log(`Row ${rowIndex}: "${unicodeChars}" - ${dotPatterns}`);
  });
  
  const stats = getBrailleMatrixStats(brailleMatrix);
  console.log('📊 Stats:', stats);
}
