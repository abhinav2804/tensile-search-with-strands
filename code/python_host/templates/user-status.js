<!-- Add this script tag just before the closing </body> tag in your index.html -->
<script src="user-status.js"></script>

<!-- Or if you prefer to include it inline, add this script block before your existing main script -->
<script>
// Add this to your existing authManager.handleAuthSuccess function
// Replace the existing handleAuthSuccess method with this enhanced version:

// Find this section in your existing code and modify it:
/*
handleAuthSuccess(authData) {
    console.log('Processing auth success:', authData);
    
    const userData = authData.user || {};
    const sessionData = authData.sessionJwt || authData.sessionToken || '';
    
    const user = {
        id: userData.userId || userData.id || 'user-' + Date.now(),
        name: userData.name || userData.givenName || userData.email?.split('@')[0] || 'User',
        email: userData.email || '',
        token: sessionData,
        loginTime: Date.now()
    };

    console.log('Created user object:', user);
    
    this.setUser(user);
    this.storeUser(user);
    this.hideAuthModal();
    this.hideProtectedOverlay();
    
    this.showNotification('Successfully signed in! Welcome to Product Discovery AI.', 'success');
    
    // ADD THIS LINE: Show user status after successful login
    setTimeout(() => {
        if (window.userStatusManager) {
            window.userStatusManager.checkUserStatus();
        }
    }, 1500);
}
*/

// Also add this helper function to manually trigger the status box
window.showUserStatus = function() {
    if (window.userStatusManager) {
        window.userStatusManager.checkUserStatus();
    } else {
        console.warn('User status manager not initialized');
    }
};

// Optional: Add a keyboard shortcut to show status (Ctrl+Shift+S)
document.addEventListener('keydown', function(e) {
    if (e.ctrlKey && e.shiftKey && e.key === 'S') {
        e.preventDefault();
        window.showUserStatus();
    }
});
</script>

<!-- Alternative: If you want to add a small button to manually trigger status -->
<!-- Add this button somewhere in your UI, like near the user info section -->
<!--
<button id="statusCheckBtn" class="status-check-btn" title="Check Status" onclick="window.showUserStatus()">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <path d="M9 12l2 2 4-4"/>
        <path d="M21 12c.552 0 1-.448 1-1s-.448-1-1-1-1 .448-1 1 .448 1 1 1z"/>
        <path d="M3 12c.552 0 1-.448 1-1s-.448-1-1-1-1 .448-1 1 .448 1 1 1z"/>
        <path d="M12 21c.552 0 1-.448 1-1s-.448-1-1-1-1 .448-1 1 .448 1 1 1z"/>
        <path d="M12 3c.552 0 1-.448 1-1s-.448-1-1-1-1 .448-1 1 .448 1 1 1z"/>
    </svg>
</button>

<style>
.status-check-btn {
    position: fixed;
    bottom: 20px;
    left: 20px;
    width: 48px;
    height: 48px;
    background: linear-gradient(135deg, #8b5cf6, #7c3aed);
    border: none;
    border-radius: 50%;
    cursor: pointer;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 15px rgba(139, 92, 246, 0.3);
    transition: all 0.3s ease;
    z-index: 1000;
}

.status-check-btn:hover {
    transform: translateY(-2px) scale(1.05);
    box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}

.status-check-btn svg {
    width: 20px;
    height: 20px;
}
</style>
