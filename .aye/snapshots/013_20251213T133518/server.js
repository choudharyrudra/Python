const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Serve static files from public directory
app.use(express.static(path.join(__dirname, 'public')));

// Serve gui folder for assets (e.g. demo video)
app.use('/gui', express.static(path.join(__dirname, 'gui')));

// Explicit route for chat page
app.get('/chat', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'chat.html'));
});

// Explicit route for chat.html
app.get('/chat.html', (req, res) => {
    const chatPath = path.join(__dirname, 'public', 'chat.html');
    if (fs.existsSync(chatPath)) {
        res.sendFile(chatPath);
    } else {
        res.status(404).send('Chat page not found. Make sure public/chat.html exists.');
    }
});

// Fallback to index.html for SPA-style routing (only for non-file routes)
app.get('*', (req, res) => {
    // Don't catch requests that look like file requests
    if (req.path.includes('.')) {
        res.status(404).send('File not found');
    } else {
        res.sendFile(path.join(__dirname, 'public', 'index.html'));
    }
});

app.listen(PORT, () => {
    console.log(`Market Terminal server running at http://localhost:${PORT}`);
    console.log(`  - Main page: http://localhost:${PORT}/`);
    console.log(`  - AI Chat:   http://localhost:${PORT}/chat.html`);
});
