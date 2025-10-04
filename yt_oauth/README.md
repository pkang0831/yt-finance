# YouTube OAuth Setup Instructions

## Required Files

### 1. client_secret.json
This file should contain your YouTube API OAuth2 client credentials from Google Cloud Console.

**How to get it:**
1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable YouTube Data API v3
4. Go to "Credentials" → "Create Credentials" → "OAuth 2.0 Client IDs"
5. Choose "Desktop application"
6. Download the JSON file and rename it to `client_secret.json`
7. Place it in this directory

### 2. token.json
This file will be automatically generated after the first successful OAuth authentication.

**What it contains:**
- Access token
- Refresh token
- Token expiration time
- Scopes

## Security Notes

- Never commit `client_secret.json` or `token.json` to version control
- Keep these files secure and private
- The `token.json` file can be regenerated if needed

## First Run

When you run the pipeline for the first time:
1. The system will open a browser window for OAuth authentication
2. Sign in with your Google account
3. Grant permissions for YouTube upload
4. The `token.json` file will be created automatically

## Troubleshooting

If you encounter OAuth issues:
1. Delete `token.json` and re-authenticate
2. Check that your Google Cloud project has YouTube Data API v3 enabled
3. Verify that your OAuth2 client is configured for desktop applications
4. Ensure the redirect URI is set to `http://localhost:8080/` or similar

