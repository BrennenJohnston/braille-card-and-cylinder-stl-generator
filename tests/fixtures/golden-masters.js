/**
 * Golden Master Test Data
 * Known-good test cases for regression testing
 */

/**
 * Golden master test cases with expected outputs
 * These represent verified, correct braille-to-STL conversions
 */
export const goldenMasters = {
  // Basic single characters
  singleA: {
    name: 'Single Letter A',
    input: {
      brailleLines: ['⠁'],
      shapeType: 'card',
      settings: {
        card_width: 30,
        card_height: 20,
        card_thickness: 1.0
      }
    },
    expected: {
      minFileSize: 2000,    // Minimum STL file size in bytes
      maxFileSize: 10000,   // Maximum STL file size in bytes
      minTriangles: 50,     // Minimum triangle count
      maxTriangles: 500,    // Maximum triangle count
      dotPattern: [1, 0, 0, 0, 0, 0], // Expected braille dot pattern
      processingTimeMs: 3000 // Maximum processing time
    }
  },

  // Full braille cell
  fullCell: {
    name: 'Full Braille Cell',
    input: {
      brailleLines: ['⠿'], // All 6 dots
      shapeType: 'card',
      settings: {
        card_width: 30,
        card_height: 20,
        card_thickness: 1.0
      }
    },
    expected: {
      minFileSize: 5000,
      maxFileSize: 20000,
      minTriangles: 200,
      maxTriangles: 1000,
      dotPattern: [1, 1, 1, 1, 1, 1],
      processingTimeMs: 4000
    }
  },

  // Standard "HELLO" test
  hello: {
    name: 'Hello World Standard',
    input: {
      brailleLines: ['⠓⠑⠇⠇⠕'],
      shapeType: 'card',
      settings: {
        card_width: 85.60,
        card_height: 53.98,
        card_thickness: 0.76
      }
    },
    expected: {
      minFileSize: 8000,
      maxFileSize: 50000,
      minTriangles: 300,
      maxTriangles: 2000,
      totalDots: 14, // H(4) + E(2) + L(3) + L(3) + O(2) = 14 dots
      processingTimeMs: 8000
    }
  },

  // Multi-line card
  multiLine: {
    name: 'Multi-Line Card',
    input: {
      brailleLines: [
        '⠓⠑⠇⠇⠕',     // HELLO
        '⠺⠕⠗⠇⠙',     // WORLD  
        '⠞⠑⠎⠞',       // TEST
        '⠁⠃⠉⠙'        // ABCD
      ],
      shapeType: 'card',
      settings: {
        card_width: 85.60,
        card_height: 53.98,
        card_thickness: 0.76,
        grid_rows: 4
      }
    },
    expected: {
      minFileSize: 15000,
      maxFileSize: 100000,
      minTriangles: 600,
      maxTriangles: 4000,
      processingTimeMs: 12000
    }
  },

  // Cylinder test
  cylinderBasic: {
    name: 'Basic Cylinder',
    input: {
      brailleLines: ['⠓⠊'], // HI
      shapeType: 'cylinder',
      settings: {
        cylinder_params: {
          diameter_mm: 31.35,
          height_mm: 53.98
        }
      }
    },
    expected: {
      minFileSize: 5000,
      maxFileSize: 40000,
      minTriangles: 200,
      maxTriangles: 2000,
      processingTimeMs: 6000
    }
  },

  // Large text test
  largeText: {
    name: 'Large Text Processing',
    input: {
      brailleLines: [
        '⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚⠅⠇⠍⠝⠕⠏⠟⠗⠎⠞⠥⠧⠺⠭⠽⠵', // Full alphabet
        '⠼⠁⠃⠉⠙⠑⠋⠛⠓⠊⠚',                               // Numbers
        '⠲⠂⠦⠖⠤⠨⠌⠡⠪⠳⠻',                               // Punctuation
        '⠞⠑⠎⠞⠊⠝⠛⠀⠇⠁⠗⠛⠑⠀⠞⠑⠭⠞'                 // Testing large text
      ],
      shapeType: 'card',
      settings: {
        card_width: 120,
        card_height: 80,
        grid_columns: 40,
        grid_rows: 4
      }
    },
    expected: {
      minFileSize: 30000,
      maxFileSize: 200000,
      minTriangles: 1000,
      maxTriangles: 8000,
      processingTimeMs: 15000
    }
  }
};

/**
 * Validate STL output against golden master expectations
 * @param {ArrayBuffer} stlBuffer - Generated STL data
 * @param {Object} expected - Expected characteristics
 * @param {Object} stats - Generation statistics
 * @returns {Object} Validation results
 */
export function validateGoldenMaster(stlBuffer, expected, stats = {}) {
  const results = {
    valid: true,
    issues: [],
    warnings: [],
    metrics: {}
  };

  // File size validation
  const fileSize = stlBuffer.byteLength;
  results.metrics.fileSize = fileSize;
  
  if (expected.minFileSize && fileSize < expected.minFileSize) {
    results.issues.push(`File too small: ${fileSize} < ${expected.minFileSize} bytes`);
    results.valid = false;
  }
  
  if (expected.maxFileSize && fileSize > expected.maxFileSize) {
    results.warnings.push(`File large: ${fileSize} > ${expected.maxFileSize} bytes`);
  }

  // Triangle count validation
  const view = new DataView(stlBuffer);
  const triangleCount = view.getUint32(80, true);
  results.metrics.triangleCount = triangleCount;
  
  if (expected.minTriangles && triangleCount < expected.minTriangles) {
    results.issues.push(`Too few triangles: ${triangleCount} < ${expected.minTriangles}`);
    results.valid = false;
  }
  
  if (expected.maxTriangles && triangleCount > expected.maxTriangles) {
    results.warnings.push(`Many triangles: ${triangleCount} > ${expected.maxTriangles}`);
  }

  // Processing time validation
  if (expected.processingTimeMs && stats.totalTime && stats.totalTime > expected.processingTimeMs) {
    results.warnings.push(`Slow processing: ${stats.totalTime}ms > ${expected.processingTimeMs}ms`);
  }

  // STL format validation
  const expectedFileSize = 84 + (50 * triangleCount);
  if (fileSize !== expectedFileSize) {
    results.issues.push(`Invalid STL format: size ${fileSize} != expected ${expectedFileSize}`);
    results.valid = false;
  }

  return results;
}

/**
 * Run all golden master tests
 * @param {WorkerManager} workerManager - Worker manager instance
 * @returns {Promise<Object>} Test results summary
 */
export async function runGoldenMasterTests(workerManager) {
  console.log('🎯 Running Golden Master Validation Tests...');
  
  const results = {
    passed: 0,
    failed: 0,
    total: Object.keys(goldenMasters).length,
    details: []
  };

  for (const [key, goldenMaster] of Object.entries(goldenMasters)) {
    console.log(`\n🧪 Testing: ${goldenMaster.name}`);
    
    try {
      const startTime = Date.now();
      
      // Generate STL
      const stlResult = await workerManager.generateSTL(
        goldenMaster.input.shapeType,
        goldenMaster.input.brailleLines,
        goldenMaster.input.settings
      );
      
      const processingTime = Date.now() - startTime;
      
      // Validate against golden master
      const validation = validateGoldenMaster(
        stlResult.stlBuffer, 
        goldenMaster.expected,
        { ...stlResult.stats, totalTime: processingTime }
      );
      
      if (validation.valid) {
        results.passed++;
        console.log(`  ✅ ${goldenMaster.name}: PASSED`);
      } else {
        results.failed++;
        console.log(`  ❌ ${goldenMaster.name}: FAILED`);
        validation.issues.forEach(issue => console.log(`    - ${issue}`));
      }
      
      // Show warnings
      validation.warnings.forEach(warning => console.log(`    ⚠️  ${warning}`));
      
      results.details.push({
        name: goldenMaster.name,
        key,
        passed: validation.valid,
        metrics: validation.metrics,
        issues: validation.issues,
        warnings: validation.warnings,
        processingTime
      });
      
    } catch (error) {
      results.failed++;
      console.log(`  ❌ ${goldenMaster.name}: ERROR - ${error.message}`);
      
      results.details.push({
        name: goldenMaster.name,
        key,
        passed: false,
        error: error.message
      });
    }
  }

  console.log(`\n🎯 Golden Master Results: ${results.passed}/${results.total} passed`);
  return results;
}

/**
 * Create test STL files for manual validation
 * @param {WorkerManager} workerManager - Worker manager instance
 */
export async function createTestSTLFiles(workerManager) {
  console.log('📁 Creating test STL files for manual validation...');
  
  const testFiles = [
    { name: 'hello-card.stl', braille: ['⠓⠑⠇⠇⠕'], shape: 'card' },
    { name: 'hello-cylinder.stl', braille: ['⠓⠑⠇⠇⠕'], shape: 'cylinder' },
    { name: 'alphabet-card.stl', braille: ['⠁⠃⠉⠙⠑⠋⠛'], shape: 'card' }
  ];

  const outputDir = path.join(process.cwd(), 'tests', 'fixtures', 'test-models');
  
  try {
    // Ensure output directory exists
    await fs.mkdir(outputDir, { recursive: true });
    
    for (const testFile of testFiles) {
      try {
        const result = await workerManager.generateSTL(
          testFile.shape,
          testFile.braille
        );
        
        const filePath = path.join(outputDir, testFile.name);
        await fs.writeFile(filePath, Buffer.from(result.stlBuffer));
        
        console.log(`  ✅ Created: ${testFile.name} (${(result.stlBuffer.byteLength / 1024).toFixed(1)} KB)`);
        
      } catch (error) {
        console.error(`  ❌ Failed to create ${testFile.name}:`, error.message);
      }
    }
    
    console.log('✅ Test STL files created successfully');
    
  } catch (error) {
    console.error('❌ Failed to create test files:', error);
    throw error;
  }
}
