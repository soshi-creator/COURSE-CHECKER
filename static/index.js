    // Fixed Modal Functions
    function openModal() {
      const modal = document.getElementById('degreeModal');
      modal.style.display = 'flex';
      document.body.style.overflow = 'hidden';
    }
    
    function closeModal() {
      const modal = document.getElementById('degreeModal');
      modal.style.display = 'none';
      document.body.style.overflow = 'auto';
    }
    
    // Close modal when clicking outside
    document.getElementById('degreeModal').addEventListener('click', function(e) {
      if (e.target === this) {
        closeModal();
      }
    });
    
    // Close with Escape key
    document.addEventListener('keydown', function(e) {
      if (e.key === 'Escape') {
        closeModal();
        closePWAInstallModal();
      }
    });
    
    // PWA Install Modal Functions
    function closePWAInstallModal() {
      const modal = document.getElementById('pwaInstallModal');
      modal.style.display = 'none';
      document.body.style.overflow = 'auto';
    }
    
    // Service Worker Registration
    if ("serviceWorker" in navigator) {
      navigator.serviceWorker.register("{{ url_for('static', filename='service-worker.js') }}")
        .then(() => console.log("Service Worker registered"))
        .catch((err) => console.log("Service Worker registration failed:", err));
    }
    
    // PWA Install Prompt
    let deferredPrompt;
    const pwaInstallModal = document.getElementById('pwaInstallModal');
    const pwaInstallBtn = document.getElementById('pwaInstallBtn');
    const pwaDismissBtn = document.getElementById('pwaDismissBtn');
    
    window.addEventListener('beforeinstallprompt', (e) => {
      e.preventDefault();
      deferredPrompt = e;
      
      setTimeout(() => {
        pwaInstallModal.style.display = 'flex';
        document.body.style.overflow = 'hidden';
      }, 3000);
    });
    
    pwaInstallBtn.addEventListener('click', async () => {
      if (!deferredPrompt) return;
      
      deferredPrompt.prompt();
      const { outcome } = await deferredPrompt.userChoice;
      console.log(`User response: ${outcome}`);
      
      closePWAInstallModal();
      deferredPrompt = null;
    });
    
    pwaDismissBtn.addEventListener('click', () => {
      closePWAInstallModal();
    });
    
    pwaInstallModal.addEventListener('click', (e) => {
      if (e.target === pwaInstallModal) {
        closePWAInstallModal();
      }
    });
    
    window.addEventListener('appinstalled', () => {
      console.log('PWA was installed');
      closePWAInstallModal();
      deferredPrompt = null;
    });
    
    // Enhanced button hover effects with sound simulation
    document.querySelectorAll('.main-btn').forEach(btn => {
      btn.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-5px)';
        // Add subtle animation to click indicator
        const indicator = this.querySelector('.click-indicator');
        if (indicator) {
          indicator.style.animation = 'pulse 0.6s ease';
        }
      });
      
      btn.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
      });
      
      btn.addEventListener('mousedown', function() {
        this.style.transform = 'translateY(2px) scale(0.98)';
      });
      
      btn.addEventListener('mouseup', function() {
        this.style.transform = 'translateY(-5px)';
      });
      
      // For touch devices
      btn.addEventListener('touchstart', function() {
        this.style.transform = 'translateY(2px) scale(0.98)';
      });
      
      btn.addEventListener('touchend', function() {
        this.style.transform = 'translateY(0)';
      });
    });
    
    // Add click animation to all interactive elements
    document.querySelectorAll('.payment-btn, .modal-btn, .floating-action-btn').forEach(btn => {
      btn.addEventListener('mousedown', function() {
        this.style.transform = 'translateY(2px)';
      });
      
      btn.addEventListener('mouseup', function() {
        if (this.classList.contains('payment-btn') || this.classList.contains('modal-btn-primary')) {
          this.style.transform = 'translateY(-3px)';
        } else {
          this.style.transform = 'translateY(0)';
        }
      });
    });

// Auto-prompt for notifications (removed modal approach)
async function requestNotificationPermission() {
  if (!("Notification" in window) || !("serviceWorker" in navigator)) {
    console.log("Push notifications are not supported on this device.");
    return;
  }

  // Check if already granted
  if (Notification.permission === "granted") {
    console.log("Notifications already enabled");
    await subscribeToPush();
    return;
  }

  // Check if previously denied
  if (Notification.permission === "denied") {
    console.log("Notifications previously denied by user");
    return;
  }

  // Directly request permission
  const permission = await Notification.requestPermission();
  
  if (permission === "granted") {
    console.log("Notification permission granted");
    await subscribeToPush();
  } else {
    console.log("Notification permission denied");
  }
}

// Public VAPID key
const VAPID_PUBLIC_KEY = "BB703tCdCyIRMmn-aZDAiCA7GDQmiE9nDo8IjnFIWRm67xJeiXtm631QB8E7z_PitRwVD2O8Xf8KJztfKMLUb6s=";

async function urlBase64ToUint8Array(base64String) {
  const padding = '='.repeat((4 - base64String.length % 4) % 4);
  const base64 = (base64String + padding)
    .replace(/\-/g, '+')
    .replace(/_/g, '/');
  const rawData = atob(base64);
  return Uint8Array.from([...rawData].map(char => char.charCodeAt(0)));
}

async function subscribeToPush() {
  try {
    const registration = await navigator.serviceWorker.ready;

    const subscription = await registration.pushManager.subscribe({
      userVisibleOnly: true,
      applicationServerKey: await urlBase64ToUint8Array(VAPID_PUBLIC_KEY)
    });

    console.log("Push Subscription:", subscription);

    // Send to backend
    const res = await fetch("/subscribe", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(subscription)
    });

    const data = await res.json();
    if (data.success) {
      console.log("Notifications enabled successfully!");
    } else {
      console.error("Failed to save subscription:", data.error);
    }
  } catch (err) {
    console.error("Error enabling notifications:", err);
  }
}

// Check and send subscription on every page load
document.addEventListener('DOMContentLoaded', function() {
  // Check if notifications are already granted
  if (Notification.permission === "granted") {
    console.log("Notifications already granted - sending subscription to backend");
    
    // Small delay to ensure service worker is ready
    setTimeout(() => {
      subscribeToPush();
    }, 1000);
  }
  
  // Still request permission for new users after 3 seconds
  setTimeout(requestNotificationPermission, 3000);
});

// Function to open chat from support dropdown
function openChatFromSupport() {
  // Close support dropdown
  closeContactDetails();
  
  // Open chat widget (uses your existing chat functions)
  setTimeout(() => {
    // Check if chat widget toggle function exists
    if (typeof toggleChatWidget === 'function') {
      toggleChatWidget();
    } else if (typeof openChatFrame === 'function') {
      // Or use your existing chat opening function
      openChatFrame('https://anonymoussupport.onrender.com/chat/new');
    } else {
      // Fallback: trigger click on chat icon
      const chatIcon = document.querySelector('.chat-icon-circle');
      if (chatIcon) chatIcon.click();
    }
  }, 300);
}

// Update chat status indicator
function updateChatStatus() {
  const statusIndicator = document.getElementById('chatStatusIndicator');
  if (!statusIndicator) return;
  
  // Check if chat is available (you can replace this with actual status check)
  const isOnline = Math.random() > 0.3; // Example: 70% chance online
  
  if (isOnline) {
    statusIndicator.textContent = 'Online';
    statusIndicator.className = 'contact-option-status online';
  } else {
    statusIndicator.textContent = 'Offline';
    statusIndicator.className = 'contact-option-status offline';
  }
}

// Update notification badge
function updateSupportNotificationBadge() {
  const badge = document.getElementById('supportNotificationBadge');
  if (!badge) return;
  
  // Check for unread messages or new notifications
  const unreadCount = getChatSession() ? 1 : 0; // Example: 1 if has chat session
  
  if (unreadCount > 0) {
    badge.textContent = unreadCount;
    badge.style.display = 'flex';
  } else {
    badge.style.display = 'none';
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Update chat status and notifications
  updateChatStatus();
  updateSupportNotificationBadge();
  
  // Update status periodically
  setInterval(updateChatStatus, 60000); // Update every minute
});

// Override the existing contact details toggle to add active class
const originalToggleContactDetails = toggleContactDetails;
toggleContactDetails = function() {
  const container = document.querySelector('.contact-details-container');
  const isOpening = !isContactExpanded;
  
  originalToggleContactDetails();
  
  if (isOpening) {
    container.classList.add('active');
    // Update status when dropdown opens
    updateChatStatus();
  } else {
    container.classList.remove('active');
  }
};

// Also update closeContactDetails function
const originalCloseContactDetails = closeContactDetails;
closeContactDetails = function() {
  const container = document.querySelector('.contact-details-container');
  container.classList.remove('active');
  originalCloseContactDetails();
};

// Configuration
const ANONYMOUS_SUPPORT_URL = "https://anonymoussupport.onrender.com";
const COURSE_CHECKER_URL = "https://course-checker-2vfv.onrender.com";

// Generate device fingerprint
function generateDeviceFingerprint() {
  const data = navigator.userAgent + 
               screen.height + 
               screen.width + 
               navigator.language +
               new Date().getTimezoneOffset();
  
  let hash = 0;
  for (let i = 0; i < data.length; i++) {
    hash = ((hash << 5) - hash) + data.charCodeAt(i);
    hash = hash & hash;
  }
  return Math.abs(hash).toString(16).slice(0, 16);
}

// Local Storage Management
function saveChatSession(sessionData) {
  localStorage.setItem('kuccps_chat_session', JSON.stringify({
    ...sessionData,
    saved_at: new Date().toISOString(),
    source: 'course_checker'
  }));
}

function getChatSession() {
  const session = localStorage.getItem('kuccps_chat_session');
  return session ? JSON.parse(session) : null;
}

function clearChatSession() {
  localStorage.removeItem('kuccps_chat_session');
}

// Remove old help popup functions (not needed anymore)
function showHelpPopup() {
  // This function is no longer used
}

function closeHelpPopup() {
  // This function is no longer used
}

// Step Navigation
function showStep(stepNumber) {
  // Hide all steps
  document.querySelectorAll('.chat-step').forEach(step => {
    step.style.display = 'none';
  });
  
  // Show selected step
  document.getElementById(`chatStep${stepNumber}`).style.display = 'block';
}

function showUsernameStep() {
  showStep(2);
}

// Check existing session
async function checkExistingSession() {
  const session = getChatSession();
  if (!session) {
    alert('No existing chat session found. Starting new chat...');
    showUsernameStep();
    return;
  }
  
  try {
    const response = await fetch(`${ANONYMOUS_SUPPORT_URL}/api/session_status/${session.session_id}`, {
      credentials: "include"
    });
    
    if (response.ok) {
      const data = await response.json();
      if (data.exists) {
        // Open existing chat
        openChatFrame(`${ANONYMOUS_SUPPORT_URL}/chat/${session.session_id}`);
        return;
      }
    }
  } catch (error) {
    console.error('Session check error:', error);
  }
  
  // Session doesn't exist
  alert('Your previous chat session has expired. Starting new chat...');
  showUsernameStep();
}

// Create username and start chat
async function createUsernameAndStartChat() {
  const usernameInput = document.getElementById('chatUsername');
  const username = usernameInput.value.trim();
  
  if (!username) {
    alert('Please enter a username');
    return;
  }
  
  if (username.length < 3 || username.length > 20) {
    alert('Username must be between 3-20 characters');
    return;
  }
  
  const deviceFp = generateDeviceFingerprint();
  
  try {
    const response = await fetch(`${ANONYMOUS_SUPPORT_URL}/api/create_username`, {
      method: 'POST',
      credentials: "include",
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        username: username,
        device_fingerprint: deviceFp
      })
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || 'Failed to create username');
    }
    
    // Save session
    saveChatSession({
      session_id: data.session_id,
      username: data.username,
      device_fp: deviceFp
    });
    
    // Open chat
    openChatFrame(`${ANONYMOUS_SUPPORT_URL}/chat/${data.session_id}`);
    
  } catch (error) {
    console.error('Create username error:', error);
    alert(`Error: ${error.message}. Please try a different username.`);
  }
}

// Open chat in iframe
function openChatFrame(chatUrl) {
  showStep(3);
  const iframe = document.getElementById('chatFrame');
  iframe.src = chatUrl;
  
  // Start checking chat status
  startStatusCheck();
}

// Chat status checking (ALWAYS ONLINE)
let statusCheckInterval;

function startStatusCheck() {
  // Set status to ALWAYS ONLINE
  updateChatStatusToAlwaysOnline();
  
  // Keep checking periodically but always show online
  statusCheckInterval = setInterval(() => {
    updateChatStatusToAlwaysOnline();
  }, 30000);
}

function stopStatusCheck() {
  if (statusCheckInterval) {
    clearInterval(statusCheckInterval);
  }
}

function updateChatStatusToAlwaysOnline() {
  const statusText = document.getElementById('chatStatusText');
  const statusDot = document.querySelector('.status-dot');
  
  if (statusText) {
    statusText.textContent = 'Always Online';
  }
  
  if (statusDot) {
    statusDot.style.background = '#2ecc71';
    statusDot.style.animation = 'pulse 2s infinite';
  }
}

// Open chat modal (main function)
function openChatModal() {
  const modal = document.getElementById('chatModal');
  modal.style.display = 'flex';
  document.body.style.overflow = 'hidden';
  
  // Initialize chat to step 1
  showStep(1);
  
  // Update chat status to always online
  updateChatStatusToAlwaysOnline();
}

// Close chat modal
function closeChatModal() {
  const modal = document.getElementById('chatModal');
  modal.style.display = 'none';
  document.body.style.overflow = 'auto';
  
  // Stop status check when modal closes
  stopStatusCheck();
}

// Update the function called from support dropdown
function openChatFromSupport() {
  // Close support dropdown
  closeContactDetails();
  
  // Open chat modal
  setTimeout(() => {
    openChatModal();
  }, 300);
}

// Toggle chat widget (for backward compatibility)
function toggleChatWidget() {
  openChatModal();
}

// Close modal when clicking outside
document.addEventListener('click', function(event) {
  const modal = document.getElementById('chatModal');
  if (modal && modal.style.display === 'flex' && event.target === modal) {
    closeChatModal();
  }
});

// Close with Escape key
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    const modal = document.getElementById('chatModal');
    if (modal && modal.style.display === 'flex') {
      closeChatModal();
    }
  }
});

// Update support dropdown chat status to ALWAYS ONLINE
function updateChatStatus() {
  const statusIndicator = document.getElementById('chatStatusIndicator');
  if (!statusIndicator) return;
  
  // ALWAYS SET TO ONLINE
  statusIndicator.textContent = 'Always Online';
  statusIndicator.className = 'contact-option-status online';
}

// Update notification badge
function updateSupportNotificationBadge() {
  const badge = document.getElementById('supportNotificationBadge');
  if (!badge) return;
  
  // Check for unread messages or new notifications
  const session = getChatSession();
  const unreadCount = session ? 1 : 0;
  
  if (unreadCount > 0) {
    badge.textContent = unreadCount;
    badge.style.display = 'flex';
  } else {
    badge.style.display = 'none';
  }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Update chat status to ALWAYS ONLINE
  updateChatStatus();
  updateSupportNotificationBadge();
  
  // Remove the old help popup timeout
  // Chat is now always online
  
  // Update status when support dropdown opens
  const supportBtn = document.querySelector('.contact-main-btn');
  if (supportBtn) {
    supportBtn.addEventListener('click', function() {
      setTimeout(updateChatStatus, 100);
    });
  }
  
  // Check if user has existing session
  const session = getChatSession();
  if (session) {
    // Update the resume button text in chat modal
    const resumeBtn = document.querySelector('[onclick="checkExistingSession()"]');
    if (resumeBtn) {
      resumeBtn.innerHTML = `<i class="bi bi-arrow-clockwise me-1"></i> Resume as ${session.username}`;
    }
  }
});

// Remove old click outside handlers that reference non-existent elements
// These are replaced by the new modal close handlers above

// Collapsible Contact Details (keep this part as is)
let isContactExpanded = false;

function toggleContactDetails() {
  const contactOptions = document.getElementById('contactOptions');
  const mainBtn = document.querySelector('.contact-main-btn');
  const arrow = document.getElementById('contactArrow');
  const overlay = document.getElementById('contactOverlay') || createContactOverlay();
  
  if (!isContactExpanded) {
    // Expand contact options
    contactOptions.classList.add('show');
    mainBtn.classList.add('collapsed');
    arrow.className = 'bi bi-chevron-down contact-arrow';
    overlay.style.display = 'block';
    isContactExpanded = true;
  } else {
    // Collapse contact options
    contactOptions.classList.remove('show');
    mainBtn.classList.remove('collapsed');
    arrow.className = 'bi bi-chevron-up contact-arrow';
    overlay.style.display = 'none';
    isContactExpanded = false;
  }
}

function createContactOverlay() {
  const overlay = document.createElement('div');
  overlay.id = 'contactOverlay';
  overlay.className = 'contact-overlay';
  overlay.onclick = closeContactDetails;
  document.body.appendChild(overlay);
  return overlay;
}

function closeContactDetails() {
  const contactOptions = document.getElementById('contactOptions');
  const mainBtn = document.querySelector('.contact-main-btn');
  const arrow = document.getElementById('contactArrow');
  const overlay = document.getElementById('contactOverlay');
  
  if (contactOptions && contactOptions.classList.contains('show')) {
    contactOptions.classList.remove('show');
    mainBtn.classList.remove('collapsed');
    arrow.className = 'bi bi-chevron-up contact-arrow';
    overlay.style.display = 'none';
    isContactExpanded = false;
  }
}

// Close contact details when clicking outside
document.addEventListener('click', function(event) {
  const contactContainer = document.querySelector('.contact-details-container');
  if (!contactContainer.contains(event.target)) {
    closeContactDetails();
  }
});

// Close with Escape key (updated to handle both modals)
document.addEventListener('keydown', function(e) {
  if (e.key === 'Escape') {
    // Close chat modal if open
    const chatModal = document.getElementById('chatModal');
    if (chatModal && chatModal.style.display === 'flex') {
      closeChatModal();
    }
    
    // Close support dropdown if open
    closeContactDetails();
    
    // Close other modals
    closeModal();
    closePWAInstallModal();
  }
});
// Support Tooltip Functions
function showSupportTooltip() {
  const tooltip = document.getElementById('supportTooltip');
  
  // ALWAYS show on every visit (remove the sessionStorage check)
  setTimeout(() => {
    tooltip.style.display = 'block';
    
    // Auto-hide after 8 seconds
    setTimeout(() => {
      if (tooltip.style.display === 'block') {
        tooltip.style.display = 'none';
      }
    }, 8000);
  }, 2000);
}

function hideSupportTooltip() {
  const tooltip = document.getElementById('supportTooltip');
  if (tooltip) {
    tooltip.style.display = 'none';
    sessionStorage.setItem('supportTooltipShown', 'true');
  }
}

// Close tooltip when clicking Support button
document.querySelector('.contact-main-btn').addEventListener('click', function() {
  hideSupportTooltip();
});

// Close tooltip when clicking anywhere
document.addEventListener('click', function(event) {
  const tooltip = document.getElementById('supportTooltip');
  if (tooltip && tooltip.style.display === 'block') {
    // Don't hide if clicking on the tooltip itself
    if (!tooltip.contains(event.target)) {
      hideSupportTooltip();
    }
  }
});

// Initialize on page load
document.addEventListener('DOMContentLoaded', function() {
  // Show support tooltip
  setTimeout(showSupportTooltip, 1000);
});