// pims/static/js/base.js - Core JavaScript for PIMS (Parliament IT Inventory Management System)

document.addEventListener('DOMContentLoaded', function() {
    // Initialize PIMS application
    PIMS.init();
});

// Main PIMS namespace
const PIMS = {
    // Configuration
    config: {
        searchDelay: 300,
        alertDuration: 5000,
        animationDuration: 300,
        sidebarBreakpoint: 1024
    },

    // Initialize application
    init: function() {
        console.log('Initializing PIMS...');
        
        this.initSidebar();
        this.initNavigation();
        this.initAlerts();
        this.initTooltips();
        this.initModals();
        this.initTables();
        this.initForms();
        this.initImageHandling();
        this.initCharts();
        
        console.log('PIMS initialized successfully');
    },

    // ===== SIDEBAR FUNCTIONALITY =====
    initSidebar: function() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        
        if (sidebarToggle && sidebar) {
            // Toggle sidebar on button click
            sidebarToggle.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                sidebar.classList.toggle('show');
                
                // Update ARIA attributes for accessibility
                const isOpen = sidebar.classList.contains('show');
                sidebarToggle.setAttribute('aria-expanded', isOpen);
                sidebar.setAttribute('aria-hidden', !isOpen);
            });

            // Close sidebar when clicking outside on mobile/tablet
            document.addEventListener('click', function(e) {
                if (window.innerWidth <= PIMS.config.sidebarBreakpoint) {
                    if (!sidebar.contains(e.target) && 
                        !sidebarToggle.contains(e.target) && 
                        sidebar.classList.contains('show')) {
                        sidebar.classList.remove('show');
                        sidebarToggle.setAttribute('aria-expanded', 'false');
                        sidebar.setAttribute('aria-hidden', 'true');
                    }
                }
            });

            // Handle window resize
            window.addEventListener('resize', function() {
                if (window.innerWidth > PIMS.config.sidebarBreakpoint) {
                    sidebar.classList.remove('show');
                    sidebarToggle.setAttribute('aria-expanded', 'false');
                    sidebar.setAttribute('aria-hidden', 'false');
                }
            });
        }

        // Initialize click-based submenu functionality
        this.initClickBasedMenus();
    },

    // Handle click-based persistent sidebar submenus
    initClickBasedMenus: function() {
        const menuToggleLinks = document.querySelectorAll('.nav-link-toggle[data-toggle="submenu"]');
        
        menuToggleLinks.forEach(toggleLink => {
            toggleLink.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                const parentNavItem = this.closest('.nav-item');
                const submenu = parentNavItem.querySelector('.submenu');
                const toggleIcon = this.querySelector('.toggle-icon');
                
                if (submenu) {
                    // Check if submenu is currently open
                    const isOpen = submenu.classList.contains('show');
                    
                    if (isOpen) {
                        // Close this submenu
                        submenu.classList.remove('show');
                        this.classList.remove('expanded');
                        this.setAttribute('aria-expanded', 'false');
                        submenu.setAttribute('aria-hidden', 'true');
                    } else {
                        // Open this submenu
                        submenu.classList.add('show');
                        this.classList.add('expanded');
                        this.setAttribute('aria-expanded', 'true');
                        submenu.setAttribute('aria-hidden', 'false');
                    }
                    
                    // Optional: Close other submenus (uncomment for accordion behavior)
                    /*
                    document.querySelectorAll('.submenu.show').forEach(openSubmenu => {
                        if (openSubmenu !== submenu) {
                            openSubmenu.classList.remove('show');
                            const otherToggleLink = openSubmenu.closest('.nav-item').querySelector('.nav-link-toggle');
                            otherToggleLink.classList.remove('expanded');
                            otherToggleLink.setAttribute('aria-expanded', 'false');
                            openSubmenu.setAttribute('aria-hidden', 'true');
                        }
                    });
                    */
                }
            });
            
            // Set initial ARIA attributes
            const submenu = toggleLink.closest('.nav-item').querySelector('.submenu');
            if (submenu) {
                const isInitiallyOpen = submenu.classList.contains('show');
                toggleLink.setAttribute('aria-expanded', isInitiallyOpen.toString());
                submenu.setAttribute('aria-hidden', (!isInitiallyOpen).toString());
            }
        });
        
        // Initialize default state - set which submenus should be open by default
        this.setDefaultSubmenuState();
    },

    // Set default submenu states
    setDefaultSubmenuState: function() {
        // Define which submenus should be open by default
        const defaultOpenSubmenus = [
            'devices', // devices submenu open by default
            'assignments' // assignments submenu open by default
        ];
        
        defaultOpenSubmenus.forEach(submenuName => {
            const submenuElement = document.querySelector(`[data-submenu="${submenuName}"]`);
            const toggleLink = document.querySelector(`[data-toggle="submenu"][href*="${submenuName}"]`);
            
            if (submenuElement && toggleLink) {
                submenuElement.classList.add('show');
                toggleLink.classList.add('expanded');
                toggleLink.setAttribute('aria-expanded', 'true');
                submenuElement.setAttribute('aria-hidden', 'false');
            }
        });
    },

    // Store submenu preferences in localStorage (optional)
    saveSubmenuState: function() {
        const openSubmenus = [];
        document.querySelectorAll('.submenu.show').forEach(submenu => {
            const navItem = submenu.closest('.nav-item');
            const toggleLink = navItem.querySelector('.nav-link-toggle');
            if (toggleLink) {
                const href = toggleLink.getAttribute('href');
                if (href) openSubmenus.push(href);
            }
        });
        
        try {
            localStorage.setItem('pims_sidebar_state', JSON.stringify(openSubmenus));
        } catch (e) {
            console.log('Could not save sidebar state to localStorage');
        }
    },

    // Restore submenu preferences from localStorage (optional)
    restoreSubmenuState: function() {
        try {
            const savedState = localStorage.getItem('pims_sidebar_state');
            if (savedState) {
                const openSubmenus = JSON.parse(savedState);
                
                openSubmenus.forEach(href => {
                    const toggleLink = document.querySelector(`[data-toggle="submenu"][href="${href}"]`);
                    if (toggleLink) {
                        const parentNavItem = toggleLink.closest('.nav-item');
                        const submenu = parentNavItem.querySelector('.submenu');
                        
                        if (submenu) {
                            submenu.classList.add('show');
                            toggleLink.classList.add('expanded');
                            toggleLink.setAttribute('aria-expanded', 'true');
                            submenu.setAttribute('aria-hidden', 'false');
                        }
                    }
                });
            }
        } catch (e) {
            console.log('Could not restore sidebar state from localStorage');
            // Fall back to default state
            this.setDefaultSubmenuState();
        }
    },

    // ===== NAVIGATION FUNCTIONALITY =====
    initNavigation: function() {
        // Highlight active navigation
        this.highlightActiveNav();
        
        // Smooth scrolling for anchor links
        this.initSmoothScrolling();
        
        // Dropdown menu enhancements
        this.initDropdowns();
    },

    // Highlight active navigation items
    highlightActiveNav: function() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            
            // Remove existing active classes
            link.classList.remove('active');
            
            // Add active class for current page
            if (href && (currentPath === href || 
                       (href !== '/' && currentPath.startsWith(href)))) {
                link.classList.add('active');
                
                // If it's a submenu item, expand parent menu
                const parentSubmenu = link.closest('.submenu');
                if (parentSubmenu) {
                    parentSubmenu.classList.add('show');
                    
                    // Update parent toggle link
                    const parentNavItem = parentSubmenu.closest('.nav-item');
                    const toggleLink = parentNavItem.querySelector('.nav-link-toggle');
                    const toggleIcon = toggleLink.querySelector('.toggle-icon');
                    
                    if (toggleLink) {
                        toggleLink.classList.add('expanded');
                        toggleLink.setAttribute('aria-expanded', 'true');
                        parentSubmenu.setAttribute('aria-hidden', 'false');
                    }
                }
            }
        });
    },

    // Smooth scrolling for anchor links
    initSmoothScrolling: function() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function (e) {
                const target = document.querySelector(this.getAttribute('href'));
                if (target) {
                    e.preventDefault();
                    target.scrollIntoView({
                        behavior: 'smooth',
                        block: 'start'
                    });
                }
            });
        });
    },

    // Enhanced dropdown functionality
    initDropdowns: function() {
        // Auto-close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            const dropdowns = document.querySelectorAll('.dropdown-menu.show');
            dropdowns.forEach(dropdown => {
                if (!dropdown.closest('.dropdown').contains(e.target)) {
                    const bsDropdown = bootstrap.Dropdown.getInstance(dropdown.previousElementSibling);
                    if (bsDropdown) {
                        bsDropdown.hide();
                    }
                }
            });
        });
    },

    // ===== ALERT SYSTEM =====
    initAlerts: function() {
        // Auto-hide alerts after specified duration
        const alerts = document.querySelectorAll('.alert[role="alert"]');
        alerts.forEach(alert => {
            // Skip alerts with data-persist attribute
            if (!alert.hasAttribute('data-persist')) {
                setTimeout(() => {
                    if (alert.classList.contains('show') || alert.classList.contains('fade')) {
                        const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                        bsAlert.close();
                    } else {
                        alert.style.transition = 'opacity 0.3s';
                        alert.style.opacity = '0';
                        setTimeout(() => alert.remove(), 300);
                    }
                }, this.config.alertDuration);
            }
        });

        // Enhanced alert close functionality
        document.querySelectorAll('.alert .btn-close').forEach(closeBtn => {
            closeBtn.addEventListener('click', function() {
                const alert = this.closest('.alert');
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            });
        });
    },

    // Show dynamic alert
    showAlert: function(message, type = 'info', persist = false) {
        const alertContainer = document.getElementById('alert-container') || document.body;
        const alertId = 'alert-' + Date.now();
        
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert" ${persist ? 'data-persist' : ''}>
                <i class="bi bi-info-circle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('afterbegin', alertHTML);
        
        // Auto-hide if not persistent
        if (!persist) {
            setTimeout(() => {
                const alert = document.getElementById(alertId);
                if (alert) {
                    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    bsAlert.close();
                }
            }, this.config.alertDuration);
        }
    },

    // ===== TOOLTIP AND POPOVER INITIALIZATION =====
    initTooltips: function() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                delay: { show: 500, hide: 100 }
            });
        });

        // Initialize Bootstrap popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function (popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    },

    // ===== MODAL ENHANCEMENTS =====
    initModals: function() {
        // Auto-focus first input in modals
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('shown.bs.modal', function() {
                const firstInput = this.querySelector('input, select, textarea');
                if (firstInput) {
                    firstInput.focus();
                }
            });
        });

        // Confirmation modals
        document.querySelectorAll('[data-confirm]').forEach(element => {
            element.addEventListener('click', function(e) {
                const message = this.getAttribute('data-confirm');
                if (!confirm(message)) {
                    e.preventDefault();
                    return false;
                }
            });
        });
    },

    // ===== TABLE ENHANCEMENTS =====
    initTables: function() {
        // Table sorting functionality
        this.initTableSorting();
        
        // Table row selection
        this.initTableSelection();
        
        // Responsive table enhancements
        this.initResponsiveTables();
    },

    // Table sorting
    initTableSorting: function() {
        document.querySelectorAll('th[data-sort]').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const table = this.closest('table');
                const column = this.getAttribute('data-sort');
                const currentOrder = this.getAttribute('data-order') || 'asc';
                const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
                
                // Update header indicators
                table.querySelectorAll('th[data-sort]').forEach(th => {
                    th.removeAttribute('data-order');
                    th.classList.remove('sorted-asc', 'sorted-desc');
                });
                
                this.setAttribute('data-order', newOrder);
                this.classList.add(`sorted-${newOrder}`);
                
                // Perform sorting (this would typically trigger a server request)
                console.log(`Sorting by ${column} in ${newOrder} order`);
            });
        });
    },

    // Table row selection
    initTableSelection: function() {
        // Select all checkbox functionality
        document.querySelectorAll('input[data-select-all]').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                const targetCheckboxes = document.querySelectorAll(`input[${this.getAttribute('data-select-all')}]`);
                targetCheckboxes.forEach(cb => {
                    cb.checked = this.checked;
                });
                
                PIMS.updateBulkActions();
            });
        });

        // Individual checkbox functionality
        document.querySelectorAll('input[data-select-item]').forEach(checkbox => {
            checkbox.addEventListener('change', function() {
                PIMS.updateBulkActions();
            });
        });
    },

    // Update bulk action buttons based on selection
    updateBulkActions: function() {
        const selectedItems = document.querySelectorAll('input[data-select-item]:checked');
        const bulkActions = document.querySelectorAll('.bulk-actions');
        
        bulkActions.forEach(actionGroup => {
            actionGroup.style.display = selectedItems.length > 0 ? 'block' : 'none';
        });
        
        // Update count displays
        document.querySelectorAll('.selected-count').forEach(counter => {
            counter.textContent = selectedItems.length;
        });
    },

    // Responsive table enhancements
    initResponsiveTables: function() {
        document.querySelectorAll('.table-responsive').forEach(container => {
            const table = container.querySelector('table');
            if (table) {
                // Add scroll indicators
                this.addTableScrollIndicators(container);
            }
        });
    },

    // Add scroll indicators to tables
    addTableScrollIndicators: function(container) {
        const checkScroll = () => {
            const isScrollable = container.scrollWidth > container.clientWidth;
            const isAtStart = container.scrollLeft === 0;
            const isAtEnd = container.scrollLeft >= container.scrollWidth - container.clientWidth - 1;
            
            container.classList.toggle('scrollable', isScrollable);
            container.classList.toggle('scroll-start', isAtStart);
            container.classList.toggle('scroll-end', isAtEnd);
        };
        
        container.addEventListener('scroll', checkScroll);
        window.addEventListener('resize', checkScroll);
        checkScroll();
    },

    // ===== FORM ENHANCEMENTS =====
    initForms: function() {
        // Enhanced form validation
        this.initFormValidation();
        
        // Auto-save functionality
        this.initAutoSave();
        
        // File upload enhancements
        this.initFileUploads();
        
        // Search functionality
        this.initSearchForms();
    },

    // Enhanced form validation
    initFormValidation: function() {
        document.querySelectorAll('form[data-validate]').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!this.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Focus first invalid field
                    const firstInvalid = this.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                    }
                }
                
                this.classList.add('was-validated');
            });
        });
    },

    // Auto-save functionality
    initAutoSave: function() {
        document.querySelectorAll('form[data-autosave]').forEach(form => {
            const formId = form.id || 'form-' + Date.now();
            let saveTimeout;
            
            form.addEventListener('input', function() {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => {
                    PIMS.autoSaveForm(formId, form);
                }, 2000);
            });
            
            // Restore saved data on load
            PIMS.restoreFormData(formId, form);
        });
    },

    // Auto-save form data
    autoSaveForm: function(formId, form) {
        const formData = new FormData(form);
        const data = {};
        
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        
        try {
            localStorage.setItem(`pims_form_${formId}`, JSON.stringify(data));
            PIMS.showAutoSaveIndicator();
        } catch (e) {
            console.log('Could not auto-save form data');
        }
    },

    // Restore form data
    restoreFormData: function(formId, form) {
        try {
            const savedData = localStorage.getItem(`pims_form_${formId}`);
            if (savedData) {
                const data = JSON.parse(savedData);
                Object.keys(data).forEach(key => {
                    const field = form.querySelector(`[name="${key}"]`);
                    if (field && field.type !== 'file') {
                        field.value = data[key];
                    }
                });
            }
        } catch (e) {
            console.log('Could not restore form data');
        }
    },

    // Show auto-save indicator
    showAutoSaveIndicator: function() {
        const indicator = document.getElementById('autosave-indicator');
        if (indicator) {
            indicator.style.opacity = '1';
            setTimeout(() => {
                indicator.style.opacity = '0';
            }, 2000);
        }
    },

    // File upload enhancements
    initFileUploads: function() {
        document.querySelectorAll('input[type="file"]').forEach(input => {
            input.addEventListener('change', function() {
                const files = Array.from(this.files);
                const preview = this.parentElement.querySelector('.file-preview');
                
                if (preview && files.length > 0) {
                    PIMS.showFilePreview(files, preview);
                }
            });
        });
    },

    // Show file preview
    showFilePreview: function(files, container) {
        container.innerHTML = '';
        
        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item d-flex align-items-center mb-2';
            
            const icon = PIMS.getFileIcon(file.type);
            const size = PIMS.formatFileSize(file.size);
            
            fileItem.innerHTML = `
                <i class="bi bi-${icon} me-2"></i>
                <span class="file-name flex-grow-1">${file.name}</span>
                <small class="text-muted">${size}</small>
            `;
            
            container.appendChild(fileItem);
        });
    },

    // Get file icon based on type
    getFileIcon: function(mimeType) {
        if (mimeType.startsWith('image/')) return 'file-image';
        if (mimeType.startsWith('video/')) return 'file-play';
        if (mimeType.startsWith('audio/')) return 'file-music';
        if (mimeType.includes('pdf')) return 'file-pdf';
        if (mimeType.includes('word')) return 'file-word';
        if (mimeType.includes('excel') || mimeType.includes('spreadsheet')) return 'file-excel';
        if (mimeType.includes('powerpoint') || mimeType.includes('presentation')) return 'file-ppt';
        return 'file-earmark';
    },

    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Search form enhancements
    initSearchForms: function() {
        document.querySelectorAll('input[type="search"], .search-input').forEach(input => {
            let searchTimeout;
            
            input.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                const query = this.value.trim();
                
                if (query.length >= 2 || query.length === 0) {
                    searchTimeout = setTimeout(() => {
                        PIMS.performSearch(query, this);
                    }, PIMS.config.searchDelay);
                }
            });
        });
    },

    // Perform search
    performSearch: function(query, input) {
        const form = input.closest('form');
        const resultsContainer = document.querySelector(input.getAttribute('data-results'));
        
        if (form && !input.hasAttribute('data-no-auto-submit')) {
            form.submit();
        }
        
        // Live search functionality can be added here
        console.log('Searching for:', query);
    },

    // ===== IMAGE HANDLING =====
    initImageHandling: function() {
        // Lazy loading
        this.initLazyLoading();
        
        // Image lightbox
        this.initImageLightbox();
        
        // Image error handling
        this.initImageErrorHandling();
    },

    // Lazy loading for images
    initLazyLoading: function() {
        if ('IntersectionObserver' in window) {
            const imageObserver = new IntersectionObserver((entries, observer) => {
                entries.forEach(entry => {
                    if (entry.isIntersecting) {
                        const img = entry.target;
                        img.src = img.dataset.src;
                        img.classList.remove('lazy');
                        observer.unobserve(img);
                    }
                });
            });
            
            document.querySelectorAll('img[data-src]').forEach(img => {
                imageObserver.observe(img);
            });
        }
    },

    // Image lightbox functionality
    initImageLightbox: function() {
        document.querySelectorAll('[data-lightbox]').forEach(trigger => {
            trigger.addEventListener('click', function(e) {
                e.preventDefault();
                const src = this.getAttribute('href') || this.getAttribute('data-src');
                PIMS.showLightbox(src);
            });
        });
    },

    // Show image lightbox
    showLightbox: function(src) {
        const lightbox = document.createElement('div');
        lightbox.className = 'lightbox position-fixed top-0 start-0 w-100 h-100';
        lightbox.style.cssText = 'background: rgba(0,0,0,0.8); z-index: 9999; display: flex; align-items: center; justify-content: center;';
        
        lightbox.innerHTML = `
            <div class="lightbox-content text-center">
                <img src="${src}" class="img-fluid" style="max-height: 90vh; max-width: 90vw;">
                <button class="btn btn-light position-absolute top-0 end-0 m-3" onclick="this.closest('.lightbox').remove()">
                    <i class="bi bi-x-lg"></i>
                </button>
            </div>
        `;
        
        lightbox.addEventListener('click', function(e) {
            if (e.target === this) {
                this.remove();
            }
        });
        
        document.body.appendChild(lightbox);
    },

    // Image error handling
    initImageErrorHandling: function() {
        document.querySelectorAll('img').forEach(img => {
            img.addEventListener('error', function() {
                if (!this.classList.contains('error-handled')) {
                    this.src = '/static/images/placeholder.png'; // Fallback image
                    this.classList.add('error-handled');
                }
            });
        });
    },

    // ===== CHART INITIALIZATION =====
    initCharts: function() {
        // Initialize Chart.js charts
        document.querySelectorAll('[data-chart]').forEach(canvas => {
            const chartType = canvas.getAttribute('data-chart');
            const chartData = JSON.parse(canvas.getAttribute('data-chart-data') || '{}');
            
            PIMS.createChart(canvas, chartType, chartData);
        });
    },

    // Create Chart.js chart
    createChart: function(canvas, type, data) {
        if (typeof Chart === 'undefined') {
            console.log('Chart.js not loaded');
            return;
        }
        
        const ctx = canvas.getContext('2d');
        const config = {
            type: type,
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    }
                }
            }
        };
        
        new Chart(ctx, config);
    },

    // ===== UTILITY FUNCTIONS =====
    
    // Show loading overlay
    showLoading: function() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('d-none');
        }
    },

    // Hide loading overlay
    hideLoading: function() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.add('d-none');
        }
    },

    // Copy text to clipboard
    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            navigator.clipboard.writeText(text).then(() => {
                PIMS.showAlert('Copied to clipboard!', 'success');
            });
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            PIMS.showAlert('Copied to clipboard!', 'success');
        }
    },

    // Format number with commas
    formatNumber: function(num) {
        return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ',');
    },

    // Debounce function
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
};

// Global functions for backward compatibility
window.showLoading = PIMS.showLoading;
window.hideLoading = PIMS.hideLoading;
window.copyToClipboard = PIMS.copyToClipboard;

// Save submenu state on page unload (optional)
window.addEventListener('beforeunload', () => {
    if (PIMS.saveSubmenuState) {
        PIMS.saveSubmenuState();
    }
});