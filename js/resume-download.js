/**
 * Resume Download with reCAPTCHA Protection, Download Tracking, and S3 Presigned URLs
 * Features:
 * - Bot protection via Google reCAPTCHA v3
 * - Download count tracking
 * - Secure S3 presigned URL downloads (5-minute expiration)
 * - Success/error notifications
 * - Proper error handling and user feedback
 */

document.addEventListener('DOMContentLoaded', () => {
    const resumeBtn = document.getElementById('resumeDownloadBtn');
    
    if (!resumeBtn) {
        console.warn('Resume download button not found');
        return;
    }
    
    // Store original button HTML
    const originalButtonHTML = resumeBtn.innerHTML;
    
    resumeBtn.addEventListener('click', async () => {
        const recaptchaKey = document.querySelector('meta[name="recaptcha-key"]')?.content;
        
        if (!recaptchaKey) {
            showError('reCAPTCHA is not configured. Please contact the site administrator.');
            return;
        }
        
        // Check if grecaptcha is loaded
        if (typeof grecaptcha === 'undefined') {
            showError('reCAPTCHA script not loaded. Please refresh the page.');
            return;
        }
        
        // Disable button during processing
        setButtonState(resumeBtn, 'loading', 'Verifying...');
        
        try {
            // Execute reCAPTCHA
            const token = await grecaptcha.execute(recaptchaKey, { action: 'resume_download' });
            
            // Verify the token and get download URL from backend
            const response = await fetch('https://api.joshcarl.dev/resume-download', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    token: token,
                    action: 'resume_download'
                })
            });
            
            if (!response.ok) {
                throw new Error(`Server returned ${response.status}: ${response.statusText}`);
            }
            
            const data = await response.json();
            
            // Check if verification was successful and download is allowed
            if (data.success && data.downloadAllowed) {
                // Use the presigned S3 URL from backend
                if (data.downloadUrl) {
                    setButtonState(resumeBtn, 'loading', 'Downloading...');
                    await downloadResumeFromUrl(data.downloadUrl);
                    
                    // Show success notification
                    showSuccess(`Resume downloaded successfully!${data.downloadCount ? ` (Download #${data.downloadCount})` : ''}`);
                } else {
                    throw new Error('Download URL not provided');
                }
                
                // Reset button after short delay
                setTimeout(() => {
                    resetButton(resumeBtn, originalButtonHTML);
                }, 1500);
            } else {
                throw new Error(data.message || 'Download verification failed. Please try again.');
            }
        } catch (error) {
            console.error('Resume download failed:', error);
            showError(error.message || 'Failed to verify download. Please try again.');
            resetButton(resumeBtn, originalButtonHTML);
        }
    });
});

/**
 * Download resume from S3 presigned URL
 */
async function downloadResumeFromUrl(url) {
    return new Promise((resolve, reject) => {
        try {
            const link = document.createElement('a');
            link.href = url;
            link.target = '_blank';  // Open in new tab as fallback
            
            // Track if download started
            link.addEventListener('click', () => {
                setTimeout(() => resolve(), 100);
            });
            
            // Append, click, and remove
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Fallback: Trigger resume download from local file (not used with S3)
 */
async function downloadResume() {
    return new Promise((resolve, reject) => {
        try {
            const link = document.createElement('a');
            link.href = '/resume.pdf';
            link.download = 'Joshua_Carl_Soguilon_Resume.pdf';
            
            // Track if download started
            link.addEventListener('click', () => {
                setTimeout(() => resolve(), 100);
            });
            
            // Append, click, and remove
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            reject(error);
        }
    });
}

/**
 * Set button state (loading, success, error)
 */
function setButtonState(button, state, text) {
    button.disabled = true;
    
    const icons = {
        loading: '<span class="spinner">⏳</span>',
        success: '<span class="success-icon">✓</span>',
        error: '<span class="error-icon">✗</span>'
    };
    
    button.innerHTML = `${icons[state] || ''}<span>${text}</span>`;
}

/**
 * Reset button to original state
 */
function resetButton(button, originalHTML) {
    button.disabled = false;
    button.innerHTML = originalHTML;
}

/**
 * Show success notification
 */
function showSuccess(message) {
    showNotification(message, 'success');
}

/**
 * Show error notification
 */
function showError(message) {
    showNotification(message, 'error');
}

/**
 * Show notification to user
 * You can customize this to use your own toast/notification system
 */
function showNotification(message, type = 'info') {
    // Simple alert for now - you can replace with a better UI notification
    if (type === 'error') {
        alert(`❌ ${message}`);
    } else if (type === 'success') {
        // Optional: Don't show alert for success, just console log
        console.log(`✅ ${message}`);
        // Or use a toast notification library
    } else {
        console.log(`ℹ️ ${message}`);
    }
}

/**
 * Optional: Add CSS for spinner animation
 * Add this to your stylesheet:
 * 
 * @keyframes spin {
 *   to { transform: rotate(360deg); }
 * }
 * 
 * .spinner {
 *   display: inline-block;
 *   animation: spin 1s linear infinite;
 * }
 */
