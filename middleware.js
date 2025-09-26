const ALLOWED_METHODS = new Set(['POST']);
const MAX_CONTENT_LENGTH = 1 * 1024 * 1024; // 1MB, matches backend limit
const ALLOWED_PLATE_TYPES = new Set(['positive', 'negative']);
const ALLOWED_GRADES = new Set(['g1', 'g2']);
const ALLOWED_SHAPE_TYPES = new Set(['card', 'cylinder']);

function errorResponse(message, status = 400) {
  return new Response(
    JSON.stringify({ error: message }),
    {
      status,
      headers: {
        'Content-Type': 'application/json',
        'Cache-Control': 'no-store',
      },
    },
  );
}

export const config = {
  matcher: ['/generate_braille_stl', '/generate_counter_plate_stl'],
};

export default async function middleware(request) {
  if (!ALLOWED_METHODS.has(request.method)) {
    return errorResponse('Method not allowed', 405);
  }

  const contentType = request.headers.get('content-type') || '';
  if (!contentType.toLowerCase().includes('application/json')) {
    return errorResponse('Content-Type must be application/json');
  }

  const contentLengthHeader = request.headers.get('content-length');
  if (contentLengthHeader) {
    const numericLength = Number(contentLengthHeader);
    if (!Number.isFinite(numericLength) || numericLength > MAX_CONTENT_LENGTH) {
      return errorResponse('Request payload too large', 413);
    }
  }

  let payload;
  try {
    payload = await request.clone().json();
  } catch (error) {
    return errorResponse('Invalid JSON payload');
  }

  if (typeof payload !== 'object' || payload === null) {
    return errorResponse('Request body must be a JSON object');
  }

  const {
    lines,
    plate_type: plateType = 'positive',
    grade = 'g2',
    settings = {},
    shape_type: shapeType = 'card',
  } = payload;

  if (!Array.isArray(lines)) {
    return errorResponse('`lines` must be an array of strings');
  }

  if (lines.length === 0 || lines.length > 12) {
    return errorResponse('`lines` must contain between 1 and 12 entries');
  }

  for (let i = 0; i < lines.length; i += 1) {
    const entry = lines[i];
    if (typeof entry !== 'string') {
      return errorResponse(`Line ${i + 1} must be a string`);
    }
    if (entry.length > 50) {
      return errorResponse(`Line ${i + 1} exceeds 50 character limit`);
    }
  }

  if (!ALLOWED_PLATE_TYPES.has(plateType)) {
    return errorResponse('Invalid plate_type');
  }

  if (!ALLOWED_GRADES.has(grade)) {
    return errorResponse('Invalid grade');
  }

  if (!ALLOWED_SHAPE_TYPES.has(shapeType)) {
    return errorResponse('Invalid shape_type');
  }

  if (typeof settings !== 'object' || settings === null) {
    return errorResponse('`settings` must be an object');
  }

  return undefined;
}


