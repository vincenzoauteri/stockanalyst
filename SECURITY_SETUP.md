# Security Setup Guide

This guide provides instructions for setting up the Stock Analyst application with proper security configurations.

## Required Environment Variables

### Production Environment

For production deployments, the following environment variables **must** be set:

1. **SECRET_KEY** - Flask session encryption key (minimum 32 characters)
2. **POSTGRES_PASSWORD** - Database password (minimum 12 characters)
3. **FMP_API_KEY** - Financial Modeling Prep API key

### Generating Secure Secrets

Use the included secret generator to create secure values:

```bash
# Generate secrets with usage instructions
python generate_secrets.py

# Generate in .env file format
python generate_secrets.py --env-file

# Generate for docker-compose environment section
python generate_secrets.py --docker-compose
```

### Manual Secret Generation

If you prefer to generate secrets manually:

```bash
# Generate SECRET_KEY (64 characters)
python -c "import secrets; print(secrets.token_urlsafe(48))"

# Generate POSTGRES_PASSWORD (16 characters)
python -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(16)))"
```

## Environment Configuration

### Option 1: Environment Variables

```bash
export SECRET_KEY='your-64-character-secret-key-here'
export POSTGRES_PASSWORD='your-secure-database-password'
export FMP_API_KEY='your-fmp-api-key'
```

### Option 2: .env File

Create a `.env` file in the project root:

```env
SECRET_KEY=your-64-character-secret-key-here
POSTGRES_PASSWORD=your-secure-database-password
FMP_API_KEY=your-fmp-api-key
FLASK_ENV=production
```

### Option 3: Docker Compose Override

Create a `docker-compose.override.yml` file:

```yaml
version: '3.8'
services:
  webapp:
    environment:
      - SECRET_KEY=your-64-character-secret-key-here
      - POSTGRES_PASSWORD=your-secure-database-password
      - FMP_API_KEY=your-fmp-api-key
  
  scheduler:
    environment:
      - SECRET_KEY=your-64-character-secret-key-here
      - POSTGRES_PASSWORD=your-secure-database-password
      - FMP_API_KEY=your-fmp-api-key
  
  postgres:
    environment:
      - POSTGRES_PASSWORD=your-secure-database-password
```

## Security Validation

The application will automatically validate security configuration on startup:

- **Development mode**: Warnings for missing configurations, but continues to run
- **Production mode**: **Fails to start** if required secrets are missing or weak

### Validation Checks

1. **SECRET_KEY**:
   - Must be set (no default in production)
   - Must not be a known default value
   - Must be at least 32 characters long

2. **POSTGRES_PASSWORD**:
   - Must be set (no default in production)
   - Must not be a common weak password
   - Must be at least 12 characters long

3. **API Keys**:
   - FMP_API_KEY must be configured

## Testing Security Configuration

Test your configuration without starting the full application:

```bash
# Test current configuration
python -c "from unified_config import BaseConfig; BaseConfig.validate_and_exit_on_error(); print('✅ Configuration valid')"

# Test with production environment
FLASK_ENV=production python -c "from unified_config import BaseConfig; BaseConfig.validate_and_exit_on_error(); print('✅ Production configuration valid')"
```

## Additional Security Recommendations

### 1. Use Strong Passwords
- Minimum 12 characters for database passwords
- Include letters, numbers, and special characters
- Avoid dictionary words and common patterns

### 2. Rotate Secrets Regularly
- Change SECRET_KEY and database passwords periodically
- Update FMP_API_KEY if compromised

### 3. Secure Storage
- Never commit secrets to version control
- Use environment-specific secret management
- Consider using vault solutions for production

### 4. Network Security
- Use HTTPS in production
- Restrict database access to application containers only
- Enable firewall rules for production deployments

### 5. Container Security
- Run containers with non-root users when possible
- Keep base images updated
- Scan for vulnerabilities regularly

## Troubleshooting

### Common Issues

1. **"SECRET_KEY environment variable is required for production"**
   - Solution: Set SECRET_KEY environment variable with a secure value

2. **"SECRET_KEY must be at least 32 characters long in production"**
   - Solution: Generate a longer secret key using the provided generator

3. **"POSTGRES_PASSWORD must be changed from default value in production"**
   - Solution: Set a custom database password, not a default value

4. **Application won't start in production**
   - Check that FLASK_ENV is set to 'production'
   - Verify all required environment variables are set
   - Run the validation test command above

### Getting Help

If you encounter issues:

1. Run the configuration validation test
2. Check the application logs for specific error messages
3. Ensure environment variables are properly exported
4. Verify file permissions on .env files

---

*Last Updated: 2025-07-08*
*Version: Compatible with Stock Analyst v0.0.24+*