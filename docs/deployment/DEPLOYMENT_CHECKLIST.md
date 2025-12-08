# Deployment Checklist - Braille Card Generator

## Pre-Deployment Security & Configuration

### ✅ Security Measures Implemented
- [x] Rate limiting (10 requests/minute per IP)
- [x] Input validation and sanitization
- [x] Security headers (CSP, XSS protection, etc.)
- [x] Path traversal protection
- [x] Request size limits (1MB max)
- [x] Error handling that doesn't expose sensitive information
- [x] Debug code and test endpoints removed

### ⚠️ Required Configuration Before Deployment

#### 1. Environment Variables
Set these environment variables in your deployment platform:

```bash
# Required - Generate a strong secret key
SECRET_KEY=your-super-secure-secret-key-here

# Optional - Set to 'production' for production environment
FLASK_ENV=production

# Optional - For enhanced logging
LOG_LEVEL=INFO
```

#### 2. CORS Origins
Update `backend.py` allowed origins:
```python
allowed_origins = [
    'https://your-actual-vercel-domain.vercel.app',  # Replace with your domain
    'https://your-custom-domain.com'  # Add custom domain if any
]
```

#### 3. Security Headers CSP
Review and update Content Security Policy in `backend.py` if needed:
- Currently allows Google Fonts
- Restricts script sources to self + inline
- Update if you add additional external resources

### 🔒 Production Security Checklist

#### Before Going Live:
- [ ] Generate and set a strong SECRET_KEY (use `python -c "import secrets; print(secrets.token_urlsafe(32))"`)
- [ ] Update CORS origins with your actual domain(s)
- [ ] Verify all test endpoints are removed
- [ ] Confirm debug mode is disabled
- [ ] Test rate limiting works
- [ ] Verify error messages don't expose sensitive info
- [ ] Check that file upload limits are appropriate
- [ ] Test with various input edge cases
- [ ] Verify accessibility in production environment

#### Domain & SSL:
- [ ] Secure domain name chosen
- [ ] SSL certificate configured (automatic with Vercel)
- [ ] HTTPS redirect enabled
- [ ] Security headers working (test with securityheaders.com)

#### Monitoring & Logging:
- [ ] Error logging configured
- [ ] Set up monitoring for unusual traffic patterns
- [ ] Configure alerts for error rates
- [ ] Monitor file generation times and server resources

### 🚀 Deployment Steps

#### For Vercel:
1. Push code to GitHub repository
2. Connect repository to Vercel
3. Set environment variables in Vercel dashboard
4. Deploy and test

> Note: `wsgi.py` imports `app` from `backend.py` for Vercel serverless.
> Use `requirements.txt` for the Install step to reduce footprint.
> Add a `.vercelignore` to exclude build artifacts and large `third_party/` assets; keep `static/liblouis/`.

#### Environment Variables in Vercel:
1. Go to Project Settings > Environment Variables
2. Add `SECRET_KEY` with a secure random value
3. Add `FLASK_ENV=production`
4. Deploy

### 🧪 Post-Deployment Testing

#### Functionality Tests:
- [ ] Generate embossing plate STL
- [ ] Generate counter plate STL
- [ ] Test with various languages
- [ ] Verify braille translation works
- [ ] Test expert mode parameters
- [ ] Test accessibility features
- [ ] Test mobile responsiveness

#### Security Tests:
- [ ] Attempt XSS injection in text inputs
- [ ] Test rate limiting by making rapid requests
- [ ] Try malformed JSON requests
- [ ] Test file path traversal attempts
- [ ] Verify error handling doesn't leak info
- [ ] Test with very large inputs
- [ ] Check security headers with online tools

#### Performance Tests:
- [ ] STL generation time under load
- [ ] Frontend load times
- [ ] Mobile performance
- [ ] Test with slow network conditions

### 📊 Monitoring Recommendations

#### Key Metrics to Monitor:
- Request rate and patterns
- Error rates by endpoint
- STL generation times
- Memory usage during mesh operations
- Failed translation attempts

#### Alert Thresholds:
- Error rate > 5%
- Request rate > 100/minute from single IP
- Generation time > 30 seconds
- Memory usage > 80%

### 🛡️ Ongoing Security Maintenance

#### Regular Tasks:
- [ ] Update dependencies monthly
- [ ] Review error logs weekly
- [ ] Monitor for new security vulnerabilities
- [ ] Check for unusual usage patterns
- [ ] Update security headers as needed
- [ ] Review and rotate SECRET_KEY annually

#### Dependency Updates:
```bash
# Check for updates
pip list --outdated

# Update requirements
pip freeze > requirements.txt
```

### 🆘 Incident Response

#### If Security Issue Detected:
1. Immediately disable affected functionality
2. Investigate scope of issue
3. Update code and redeploy
4. Monitor for continued issues
5. Document incident and prevention measures

#### If Performance Issues:
1. Check server metrics
2. Review recent changes
3. Scale resources if needed
4. Optimize code if necessary
5. Add monitoring if gaps found

### 📝 Documentation

#### Keep Updated:
- [ ] README.md with current feature list
- [ ] API documentation if applicable
- [ ] User guide for accessibility features
- [ ] Developer setup instructions
- [ ] Deployment process documentation

---

## Final Pre-Launch Checklist

- [ ] All security measures tested
- [ ] Environment variables set
- [ ] CORS origins updated
- [ ] Dependencies up to date
- [ ] Error handling tested
- [ ] Rate limiting tested
- [ ] Accessibility tested
- [ ] Mobile responsiveness tested
- [ ] Security headers verified
- [ ] Performance benchmarked
- [ ] Monitoring configured
- [ ] Documentation updated
- [ ] Incident response plan ready

**✅ Ready for Public Launch!**
