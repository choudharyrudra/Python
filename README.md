# Market Terminal

Professional Stock Analysis Terminal - Node.js Web Server

## Quick Start

```bash
# Install dependencies
npm install

# Start the server
npm start
```

Open http://localhost:3000 in your browser.

## Pages

- **/** - Main landing page
- **/chat.html** - Dedicated AI chat page with multi-language support

## Features

### AI Chat Page
The dedicated chat page (`/chat.html`) includes:
- Full-page chat interface
- Multi-language support:
  - 🇺🇸 English
  - 🇪🇸 Español (Spanish)
  - 🇮🇳 हिंदी (Hindi)
  - 🇫🇷 Français (French)
- Quick suggestion buttons
- Typing indicators
- Responsive design

## Project Structure

```
market-terminal/
├── package.json      # Node.js manifest
├── server.js         # Express server
├── public/
│   ├── index.html    # Main landing page
│   └── chat.html     # AI chat page
└── README.md
```

## Environment Variables

- `PORT` - Server port (default: 3000)
