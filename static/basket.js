// basket.js - COMPLETE basket system with server sync
class BasketManager {
    constructor() {
        this.basket = [];
        this.email = null;
        this.indexNumber = null;
        this.isOnline = navigator.onLine;
        
        // Initialize from URL parameters or localStorage
        this.initializeUser();
        
        // Load basket
        this.loadBasket();
        this.updateBasketBadge();
        this.setupListeners();
        
        console.log('BasketManager initialized', { 
            email: this.email, 
            index: this.indexNumber,
            basketCount: this.basket.length 
        });
    }

    initializeUser() {
        // Try to get from URL parameters first
        const urlParams = new URLSearchParams(window.location.search);
        const urlEmail = urlParams.get('email');
        const urlIndex = urlParams.get('index');
        
        if (urlEmail && urlIndex) {
            this.email = urlEmail;
            this.indexNumber = urlIndex;
            this.saveUserInfo();
        } else {
            // Try to get from localStorage
            this.email = localStorage.getItem('kuccps_user_email');
            this.indexNumber = localStorage.getItem('kuccps_user_index');
        }
    }

    saveUserInfo() {
        if (this.email) {
            localStorage.setItem('kuccps_user_email', this.email);
        }
        if (this.indexNumber) {
            localStorage.setItem('kuccps_user_index', this.indexNumber);
        }
    }

    setUser(email, indexNumber) {
        this.email = email;
        this.indexNumber = indexNumber;
        this.saveUserInfo();
        this.loadBasket(); // Reload basket for new user
    }

    hasUser() {
        return !!this.email && !!this.indexNumber;
    }

    async loadBasket() {
        console.log('Loading basket...');
        
        // First load from localStorage (for quick display)
        const saved = localStorage.getItem('kuccps_basket');
        if (saved) {
            try {
                this.basket = JSON.parse(saved);
                console.log('Loaded from localStorage:', this.basket.length, 'items');
            } catch (e) {
                console.error('Error loading basket from localStorage:', e);
                this.basket = [];
            }
        }
        
        // If we have user info, try to sync with server
        if (this.hasUser() && this.isOnline) {
            await this.syncFromServer();
        }
        
        this.updateBasketBadge();
        this.updatePageDisplay();
    }

    async syncFromServer() {
        if (!this.isOnline || !this.hasUser()) {
            console.log('Cannot sync: offline or no user');
            return;
        }
        
        try {
            console.log('Syncing from server for:', this.email, this.indexNumber);
            
            const response = await fetch('/api/basket/load', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: this.email,
                    index_number: this.indexNumber
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Server response:', data);
                
                if (data.success && data.exists && data.items) {
                    // Server data takes priority
                    this.basket = data.items;
                    this.saveLocal();
                    console.log('Synced from server:', this.basket.length, 'items');
                }
            } else {
                console.error('Server response not OK:', response.status);
            }
        } catch (error) {
            console.error('Error syncing from server:', error);
        }
    }

    async saveToServer() {
        if (!this.isOnline || !this.hasUser()) {
            console.log('Cannot save to server: offline or no user');
            return false;
        }
        
        try {
            const response = await fetch('/api/basket/save', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({
                    email: this.email,
                    index_number: this.indexNumber,
                    items: this.basket
                })
            });
            
            if (response.ok) {
                const data = await response.json();
                console.log('Saved to server:', data);
                return data.success;
            }
        } catch (error) {
            console.error('Error saving to server:', error);
        }
        
        return false;
    }

    async addToBasket(programCode, courseName, institution, programType, cutoff = null, cluster = '') {
        console.log('Adding to basket:', programCode);
        
        // Check if already in basket
        const existingIndex = this.basket.findIndex(item => item.program_code === programCode);
        let wasAdded = false;
        
        if (existingIndex === -1) {
            // Add new item
            this.basket.push({
                program_code: programCode,
                course_name: courseName,
                institution: institution,
                program_type: programType,
                cutoff: cutoff,
                cluster: cluster,
                priority: 0,
                added_at: new Date().toISOString()
            });
            wasAdded = true;
        } else {
            // Update existing item
            this.basket[existingIndex] = {
                ...this.basket[existingIndex],
                course_name: courseName,
                institution: institution,
                program_type: programType,
                cutoff: cutoff,
                cluster: cluster,
                updated_at: new Date().toISOString()
            };
            wasAdded = false; // Updated existing item
        }
        
        // Save locally
        this.saveLocal();
        
        // Save to server if we have user info
        if (this.hasUser()) {
            await this.saveToServer();
        }
        
        this.updateBasketBadge();
        return wasAdded;
    }

    async removeFromBasket(programCode) {
        console.log('Removing from basket:', programCode);
        
        const beforeCount = this.basket.length;
        this.basket = this.basket.filter(item => item.program_code !== programCode);
        const wasRemoved = this.basket.length < beforeCount;
        
        if (wasRemoved) {
            this.saveLocal();
            
            // Update server if we have user info
            if (this.hasUser()) {
                try {
                    await fetch('/api/basket/remove-item', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({
                            email: this.email,
                            index_number: this.indexNumber,
                            program_code: programCode
                        })
                    });
                } catch (error) {
                    console.error('Error removing from server:', error);
                }
            }
            
            this.updateBasketBadge();
            this.updatePageDisplay();
        }
        
        return wasRemoved;
    }

    async clearBasket() {
        console.log('Clearing basket');
        this.basket = [];
        this.saveLocal();
        
        // Clear from server if we have user info
        if (this.hasUser()) {
            try {
                await fetch('/api/basket/clear', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({
                        email: this.email,
                        index_number: this.indexNumber
                    })
                });
            } catch (error) {
                console.error('Error clearing from server:', error);
            }
        }
        
        this.updateBasketBadge();
        this.updatePageDisplay();
    }

    saveLocal() {
        localStorage.setItem('kuccps_basket', JSON.stringify(this.basket));
        localStorage.setItem('kuccps_basket_last_updated', new Date().toISOString());
        this.updateBasketBadge();
    }

    isInBasket(programCode) {
        return this.basket.some(item => item.program_code === programCode);
    }

    updateBasketBadge() {
        const basketBadge = document.getElementById('basketBadge');
        
        if (basketBadge) {
            if (this.basket.length > 0) {
                basketBadge.style.display = 'inline-block';
                basketBadge.textContent = this.basket.length;
            } else {
                basketBadge.style.display = 'none';
            }
        }
        
        // Also update any other count displays
        const countElements = document.querySelectorAll('[data-basket-count]');
        countElements.forEach(el => {
            el.textContent = this.basket.length;
        });
    }

    updatePageDisplay() {
        // This function updates the basket page display
        // Check if we're on the basket page
        if (window.location.pathname.includes('/basket')) {
            this.renderBasketItems();
        }
    }

    renderBasketItems() {
        const container = document.getElementById('basketItems');
        if (!container) return;
        
        console.log('Rendering basket items:', this.basket.length);
        
        if (this.basket.length === 0) {
            container.innerHTML = `
                <div class="empty-basket">
                    <i class="bi bi-basket"></i>
                    <h4>Your basket is empty</h4>
                    <p>Start adding courses from your search results</p>
                    <a href="/" class="primary-btn" style="margin-top: 20px;">
                        <i class="bi bi-search"></i> Find Courses
                    </a>
                </div>
            `;
            return;
        }
        
        // Group by program type for counts
        const degreeCount = this.basket.filter(item => item.program_type === 'degree').length;
        const diplomaCount = this.basket.filter(item => item.program_type === 'diploma').length;
        const certificateCount = this.basket.filter(item => item.program_type === 'certificate' || item.program_type === 'kmtc').length;
        const priorityCount = this.basket.filter(item => item.priority && item.priority > 0).length;
        
        // Update counts on page
        document.getElementById('totalCourses').textContent = this.basket.length;
        document.getElementById('degreeCount').textContent = degreeCount;
        document.getElementById('diplomaCount').textContent = diplomaCount;
        document.getElementById('countAll').textContent = this.basket.length;
        document.getElementById('countDegree').textContent = degreeCount;
        document.getElementById('countDiploma').textContent = diplomaCount;
        document.getElementById('countCertificate').textContent = certificateCount;
        document.getElementById('countPriority').textContent = priorityCount;
        
        // Render all items (for 'all' tab)
        let html = '';
        this.basket.forEach((item) => {
            const priorityDots = item.priority ? 
                `<div class="priority-indicator">
                    ${[1, 2, 3].map(p => 
                        `<span class="priority-dot ${p <= item.priority ? 'active' : ''}"></span>`
                    ).join('')}
                </div>` : '';
            
            html += `
                <div class="basket-item" id="item-${item.program_code}">
                    <div class="item-checkbox">
                        <input class="form-check-input" type="checkbox" 
                               id="select-${item.program_code}"
                               onchange="window.basketManager.toggleSelectItem('${item.program_code}')">
                    </div>
                    <div class="item-content">
                        <div class="item-code">${item.program_code}</div>
                        <div class="item-name">${item.course_name}</div>
                        <div class="item-meta">
                            <span class="item-institution">${item.institution}</span>
                            <span>${item.program_type ? item.program_type.toUpperCase() : ''}</span>
                            ${item.cutoff ? `<span>Cutoff: ${item.cutoff}</span>` : ''}
                            ${priorityDots}
                        </div>
                    </div>
                    <div class="item-actions">
                        <button class="action-btn action-btn-priority" 
                                onclick="window.basketManager.setSinglePriority('${item.program_code}')">
                            <i class="bi bi-star"></i> Priority
                        </button>
                        <button class="action-btn action-btn-remove" 
                                onclick="window.basketManager.removeFromBasket('${item.program_code}')">
                            <i class="bi bi-trash"></i> Remove
                        </button>
                    </div>
                </div>
            `;
        });
        
        container.innerHTML = html;
    }

    // Basket page methods
    toggleSelectItem(programCode) {
        // Implementation for basket page selection
        console.log('Toggle select:', programCode);
    }

    setSinglePriority(programCode) {
        // Implementation for setting priority
        console.log('Set priority:', programCode);
    }

    setupListeners() {
        window.addEventListener('online', () => {
            this.isOnline = true;
            this.syncFromServer();
        });
        
        window.addEventListener('offline', () => {
            this.isOnline = false;
        });
        
        window.addEventListener('storage', (e) => {
            if (e.key === 'kuccps_basket') {
                this.loadBasket();
            }
        });
        
        // Listen for user info updates
        document.addEventListener('userInfoUpdated', (e) => {
            if (e.detail && e.detail.email && e.detail.indexNumber) {
                this.setUser(e.detail.email, e.detail.indexNumber);
            }
        });
    }

    // Public API for other pages
    getBasket() {
        return this.basket;
    }

    getBasketCount() {
        return this.basket.length;
    }
}

// Initialize basket manager
window.basketManager = new BasketManager();

// Auto-detect user from page on load
document.addEventListener('DOMContentLoaded', function() {
    // Update user info from URL
    const urlParams = new URLSearchParams(window.location.search);
    const email = urlParams.get('email');
    const index = urlParams.get('index');
    
    if (email && index && window.basketManager) {
        window.basketManager.setUser(email, index);
        
        // Update display
        const emailEl = document.getElementById('studentEmail');
        const indexEl = document.getElementById('studentIndex');
        if (emailEl) emailEl.textContent = email;
        if (indexEl) indexEl.textContent = index;
        
        // Trigger basket render if on basket page
        if (window.location.pathname.includes('/basket')) {
            window.basketManager.renderBasketItems();
        }
    }
    
    // Also check for data attributes
    const userEmail = document.querySelector('[data-user-email]')?.dataset.userEmail;
    const userIndex = document.querySelector('[data-user-index]')?.dataset.userIndex;
    
    if (userEmail && userIndex && window.basketManager) {
        window.basketManager.setUser(userEmail, userIndex);
    }
});
// Auto-render on basket page
document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a basket page by looking for basketItems container
    if (document.getElementById('basketItems')) {
        console.log('Basket page detected, auto-rendering...');
        
        // Wait for basketManager to initialize
        setTimeout(function() {
            if (window.basketManager) {
                console.log('Auto-rendering basket items');
                window.basketManager.renderBasketItems();
                
                // Also handle URL params
                const urlParams = new URLSearchParams(window.location.search);
                const email = urlParams.get('email');
                const index = urlParams.get('index');
                
                if (email && index) {
                    const emailEl = document.getElementById('studentEmail');
                    const indexEl = document.getElementById('studentIndex');
                    if (emailEl) emailEl.textContent = email;
                    if (indexEl) indexEl.textContent = index;
                }
            }
        }, 100);
    }
});