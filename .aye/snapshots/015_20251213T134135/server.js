const express = require('express');
const path = require('path');
const fs = require('fs');

const app = express();
const PORT = process.env.PORT || 3000;

// Ensure required directories exist
const requiredDirs = ['public', 'gui', 'product'];
requiredDirs.forEach(dir => {
    const dirPath = path.join(__dirname, dir);
    if (!fs.existsSync(dirPath)) {
        console.log(`Creating missing directory: ${dir}`);
        fs.mkdirSync(dirPath, { recursive: true });
    }
});

// Serve static files from public directory
app.use(express.static(path.join(__dirname, 'public')));

// Serve gui folder for assets (e.g. demo video)
app.use('/gui', express.static(path.join(__dirname, 'gui')));

// Serve product folder for downloadable files
app.use('/product', express.static(path.join(__dirname, 'product')));

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

// Start server with proper error handling
const server = app.listen(PORT, () => {
    console.log(`\n✅ Market Terminal server running at http://localhost:${PORT}`);
    console.log(`   - Main page: http://localhost:${PORT}/`);
    console.log(`   - AI Chat:   http://localhost:${PORT}/chat.html\n`);
});

// Handle server errors
server.on('error', (err) => {
    if (err.code === 'EADDRINUSE') {
        console.error(`\n❌ ERROR: Port ${PORT} is already in use!`);
        console.error(`\nTry one of these solutions:`);
        console.error(`  1. Kill the process using port ${PORT}:`);
        console.error(`     - Windows: netstat -ano | findstr :${PORT}`);
        console.error(`     - Mac/Linux: lsof -i :${PORT}`);
        console.error(`  2. Use a different port:`);
        console.error(`     - PORT=3001 npm start\n`);
    } else if (err.code === 'EACCES') {
        console.error(`\n❌ ERROR: Permission denied for port ${PORT}`);
        console.error(`   Try using a port number above 1024\n`);
    } else {
        console.error(`\n❌ Server error:`, err.message);
    }
    process.exit(1);
});

// Graceful shutdown
process.on('SIGINT', () => {
    console.log('\n👋 Shutting down server...');
    server.close(() => {
        console.log('Server closed.');
        process.exit(0);
    });
});
