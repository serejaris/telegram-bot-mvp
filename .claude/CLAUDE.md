# Telegram Bot MVP Project Instructions

## Project Overview

This is a Python-based Telegram Bot MVP for collecting and storing messages from group chats into a PostgreSQL database. The bot uses asynchronous programming for high performance and includes health monitoring capabilities.

## Development Environment

- **Python Version**: 3.12+
- **Database**: PostgreSQL 12+
- **Framework**: python-telegram-bot with asyncio
- **Deployment**: Railway (production) or local development

## File Structure Rules

- `main.py` - Main bot application with telegram handlers
- `requirements.txt` - Python dependencies
- `create_tables.sql` - Database schema
- `runtime.txt` - Python version specification for Railway
- `Procfile` - Railway deployment configuration
- `railway.json` - Railway service configuration

## Code Style Guidelines

### Python Conventions
- Use async/await for all database and telegram operations
- Follow PEP 8 style guidelines
- Use descriptive variable names (Russian comments allowed for domain-specific terms)
- Implement proper error handling with try/except blocks
- Use logging instead of print statements

### Database Operations
- Use UPSERT operations (ON CONFLICT) to prevent duplicates
- Always use parameterized queries for security
- Include proper foreign key relationships
- Add appropriate indexes for performance

### Environment Variables
Required variables:
- `TELEGRAM_TOKEN` - Bot token from @BotFather
- `DATABASE_URL` - PostgreSQL connection string
- `PORT` - HTTP server port (auto-detected on Railway)

## Bot Configuration Rules

### Critical Setup Requirements
1. **Privacy Mode MUST be disabled** in @BotFather for group chat functionality
2. Bot must have proper permissions in target group chats
3. Use long-polling mode for simplicity (no webhooks in MVP)

### Message Handling
- Process only text messages in groups
- Store complete message metadata in JSONB format
- Handle message edits and updates properly
- Prevent duplicate storage using composite primary keys

## Database Schema

### Core Tables
- `chats` - Telegram chat information
- `users` - Telegram user profiles
- `messages` - Message content and metadata

### Key Relationships
- Messages belong to chats and users
- Use CASCADE deletion for chat-message relationship
- Use SET NULL for user-message relationship

## Deployment Guidelines

### Railway Deployment (Production)
- Use the comprehensive guide in `RAILWAY_DEPLOY.md`
- Ensure PostgreSQL service is properly connected
- Set environment variables in Railway dashboard
- Monitor health check endpoint

### Local Development
1. Set up local PostgreSQL instance
2. Run SQL schema from `create_tables.sql`
3. Configure environment variables
4. Use virtual environment for dependencies

## Health Monitoring

- HTTP server runs on configurable port
- Health check available at `/health` and `/`
- Returns database connection status
- Include timestamp in health responses

## Error Handling Strategy

- Log all errors with appropriate severity levels
- Graceful degradation for non-critical failures
- Proper cleanup on bot shutdown (Ctrl+C)
- Database connection retry logic

## Security Considerations

- Never commit tokens or sensitive data
- Use parameterized database queries
- Validate input data before storage
- Implement rate limiting considerations for production

## Testing Approach

- Test database connection and table creation
- Verify message handling with various chat types
- Test health check endpoint functionality
- Validate environment variable handling

## Common Pitfalls to Avoid

1. ❌ Using synchronous operations instead of async/await
2. ❌ Not handling Privacy Mode settings properly
3. ❌ Storing duplicate messages without UPSERT logic
4. ❌ Missing error handling for database operations
5. ❌ Not implementing proper logging
6. ❌ Hardcoding configuration instead of using environment variables

## Development Workflow

1. Make changes to bot logic in `main.py`
2. Test locally with development database
3. Update requirements.txt if adding dependencies
4. Commit changes (using git-workflow-manager agent)
5. Deploy to Railway for production testing

## Performance Considerations

- Use connection pooling for database operations
- Implement batch processing for high-volume scenarios
- Add appropriate database indexes
- Monitor memory usage with large message volumes

## Future Enhancements (Post-MVP)

- LLM integration for message analysis
- Webhook mode for production scalability
- Message queue system for high volume
- Support for media messages (images, documents)
- Admin interface for bot management