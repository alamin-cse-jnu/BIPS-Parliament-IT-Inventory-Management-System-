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

    // ===== ENHANCED SIDEBAR FUNCTIONALITY =====
    initSidebar: function() {
        // Original sidebar toggle functionality for mobile
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

        // NEW: Initialize desktop sidebar collapse functionality
        this.initDesktopSidebarCollapse();
        
        // Initialize click-based submenu functionality
        this.initClickBasedMenus();
        
        // Initialize sidebar overlay for mobile
        this.initSidebarOverlay();
        
        // Restore sidebar state
        this.restoreSubmenuState();
    },

    // NEW: Desktop sidebar collapse functionality
    initDesktopSidebarCollapse: function() {
        const sidebarToggleDesktop = document.querySelector('.sidebar-toggle');
        const sidebar = document.querySelector('.sidebar');
        const contentArea = document.querySelector('.content-area');
        
        if (sidebarToggleDesktop && sidebar && contentArea) {
            // Load saved sidebar state
            const savedState = localStorage.getItem('pims_sidebar_collapsed');
            if (savedState === 'true') {
                sidebar.classList.add('collapsed');
                contentArea.classList.add('sidebar-collapsed');
            }
            
            sidebarToggleDesktop.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                
                // Toggle collapsed state
                const isCollapsed = sidebar.classList.contains('collapsed');
                
                if (isCollapsed) {
                    // Expand sidebar
                    sidebar.classList.remove('collapsed');
                    contentArea.classList.remove('sidebar-collapsed');
                    localStorage.setItem('pims_sidebar_collapsed', 'false');
                } else {
                    // Collapse sidebar
                    sidebar.classList.add('collapsed');
                    contentArea.classList.add('sidebar-collapsed');
                    localStorage.setItem('pims_sidebar_collapsed', 'true');
                }
                
                // Update tooltip
                this.setAttribute('data-bs-original-title', 
                    isCollapsed ? 'Collapse Sidebar' : 'Expand Sidebar');
                
                // Trigger layout recalculation for charts if they exist
                setTimeout(() => {
                    if (window.Chart) {
                        Object.values(Chart.instances).forEach(chart => {
                            chart.resize();
                        });
                    }
                }, 300);
            });
        }
    },

    // Initialize sidebar overlay for mobile
    initSidebarOverlay: function() {
        const sidebar = document.querySelector('.sidebar');
        const overlay = document.querySelector('.sidebar-overlay');
        
        if (sidebar && overlay) {
            // Show overlay when sidebar is shown on mobile
            const observer = new MutationObserver(function(mutations) {
                mutations.forEach(function(mutation) {
                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                        const hasSidebarShow = sidebar.classList.contains('show');
                        const isMobile = window.innerWidth <= PIMS.config.sidebarBreakpoint;
                        
                        if (hasSidebarShow && isMobile) {
                            overlay.classList.add('show');
                        } else {
                            overlay.classList.remove('show');
                        }
                    }
                });
            });
            
            observer.observe(sidebar, { attributes: true });
            
            // Close sidebar when clicking overlay
            overlay.addEventListener('click', function() {
                sidebar.classList.remove('show');
                this.classList.remove('show');
                
                const sidebarToggle = document.getElementById('sidebarToggle');
                if (sidebarToggle) {
                    sidebarToggle.setAttribute('aria-expanded', 'false');
                    sidebar.setAttribute('aria-hidden', 'true');
                }
            });
        }
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
                    document.querySelectorAll('.submenu.show').forEach(otherSubmenu => {
                        if (otherSubmenu !== submenu) {
                            otherSubmenu.classList.remove('show');
                            const otherToggle = otherSubmenu.closest('.nav-item').querySelector('.nav-link-toggle');
                            if (otherToggle) {
                                otherToggle.classList.remove('expanded');
                                otherToggle.setAttribute('aria-expanded', 'false');
                                otherSubmenu.setAttribute('aria-hidden', 'true');
                            }
                        }
                    });
                    */
                    
                    // Save current submenu state
                    this.saveSubmenuState();
                }
            });
        });
    },

    // Save submenu state to localStorage
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

    // Set default submenu state (optional)
    setDefaultSubmenuState: function() {
        // You can customize which submenus should be open by default
        const defaultOpenMenus = []; // Add default menu hrefs here
        
        defaultOpenMenus.forEach(href => {
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
    },

    // ===== NAVIGATION FUNCTIONALITY =====
    initNavigation: function() {
        // Highlight active navigation
        this.highlightActiveNav();
        
        // Smooth scrolling for anchor links
        this.initSmoothScrolling();
        
        // Dropdown menu enhancements
        this.initDropdownEnhancements();
        
        // Breadcrumb automation
        this.initBreadcrumbs();
    },

    // Highlight active navigation items
    highlightActiveNav: function() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.sidebar .nav-link[href], .navbar .nav-link[href]');
        
        // Remove existing active classes
        navLinks.forEach(link => {
            link.classList.remove('active');
        });
        
        // Find and mark active links
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (currentPath === href || (href !== '/' && currentPath.startsWith(href)))) {
                link.classList.add('active');
                
                // If it's in a submenu, ensure the submenu is shown
                const submenu = link.closest('.submenu');
                if (submenu) {
                    submenu.classList.add('show');
                    const parentToggle = submenu.closest('.nav-item').querySelector('.nav-link-toggle');
                    if (parentToggle) {
                        parentToggle.classList.add('expanded');
                        parentToggle.setAttribute('aria-expanded', 'true');
                        submenu.setAttribute('aria-hidden', 'false');
                    }
                }
            }
        });
    },

    // Initialize smooth scrolling
    initSmoothScrolling: function() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
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

    // Enhance dropdown menus
    initDropdownEnhancements: function() {
        // Close dropdowns when clicking outside
        document.addEventListener('click', function(e) {
            if (!e.target.closest('.dropdown')) {
                document.querySelectorAll('.dropdown-menu.show').forEach(menu => {
                    menu.classList.remove('show');
                });
            }
        });

        // Keyboard navigation for dropdowns
        document.querySelectorAll('.dropdown-toggle').forEach(toggle => {
            toggle.addEventListener('keydown', function(e) {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    this.click();
                }
            });
        });
    },

    // Initialize breadcrumb automation
    initBreadcrumbs: function() {
        const breadcrumb = document.querySelector('.breadcrumb');
        if (breadcrumb) {
            // Add click handlers for breadcrumb items
            breadcrumb.querySelectorAll('.breadcrumb-item a').forEach(link => {
                link.addEventListener('click', function(e) {
                    // You can add custom breadcrumb click handling here
                });
            });
        }
    },

    // ===== ALERT SYSTEM =====
    initAlerts: function() {
        // Auto-dismiss alerts
        document.querySelectorAll('.alert[data-auto-dismiss]').forEach(alert => {
            const delay = parseInt(alert.dataset.autoDismiss) || this.config.alertDuration;
            setTimeout(() => {
                this.dismissAlert(alert);
            }, delay);
        });

        // Manual alert dismissal
        document.querySelectorAll('.alert .btn-close').forEach(closeBtn => {
            closeBtn.addEventListener('click', function() {
                const alert = this.closest('.alert');
                PIMS.dismissAlert(alert);
            });
        });
    },

    // Dismiss alert with animation
    dismissAlert: function(alert) {
        if (alert) {
            alert.style.opacity = '0';
            alert.style.transform = 'translateY(-20px)';
            setTimeout(() => {
                alert.remove();
            }, this.config.animationDuration);
        }
    },

    // Show alert programmatically
    showAlert: function(message, type = 'info', duration = null) {
        const alertContainer = document.getElementById('alert-container') || document.body;
        const alertId = 'alert-' + Date.now();
        
        const alertHTML = `
            <div id="${alertId}" class="alert alert-${type} alert-dismissible fade show" role="alert">
                ${message}
                <button type="button" class="btn-close" aria-label="Close"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('afterbegin', alertHTML);
        
        const newAlert = document.getElementById(alertId);
        
        // Auto-dismiss if duration is specified
        if (duration) {
            setTimeout(() => {
                this.dismissAlert(newAlert);
            }, duration);
        }
        
        // Add manual dismissal
        const closeBtn = newAlert.querySelector('.btn-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                this.dismissAlert(newAlert);
            });
        }
        
        return newAlert;
    },

    // ===== TOOLTIP AND POPOVER INITIALIZATION =====
    initTooltips: function() {
        // Initialize Bootstrap tooltips
        if (typeof bootstrap !== 'undefined') {
            const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
            tooltipTriggerList.map(function(tooltipTriggerEl) {
                return new bootstrap.Tooltip(tooltipTriggerEl);
            });

            // Initialize Bootstrap popovers
            const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
            popoverTriggerList.map(function(popoverTriggerEl) {
                return new bootstrap.Popover(popoverTriggerEl);
            });
        }
    },

    // ===== MODAL ENHANCEMENTS =====
    initModals: function() {
        // Modal keyboard navigation
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('keydown', function(e) {
                if (e.key === 'Escape') {
                    const modalInstance = bootstrap.Modal.getInstance(this);
                    if (modalInstance) {
                        modalInstance.hide();
                    }
                }
            });
        });

        // Auto-focus on modal open
        document.querySelectorAll('.modal').forEach(modal => {
            modal.addEventListener('shown.bs.modal', function() {
                const autofocusElement = this.querySelector('[autofocus]') || 
                                       this.querySelector('.btn-primary') || 
                                       this.querySelector('input, select, textarea');
                if (autofocusElement) {
                    autofocusElement.focus();
                }
            });
        });
    },

    // ===== TABLE ENHANCEMENTS =====
    initTables: function() {
        // Add table responsiveness
        document.querySelectorAll('table:not(.table-responsive table)').forEach(table => {
            const wrapper = document.createElement('div');
            wrapper.className = 'table-responsive';
            table.parentNode.insertBefore(wrapper, table);
            wrapper.appendChild(table);
        });

        // Table sorting (basic implementation)
        this.initTableSorting();
        
        // Table search functionality
        this.initTableSearch();
    },

    // Basic table sorting
    initTableSorting: function() {
        document.querySelectorAll('th[data-sortable]').forEach(header => {
            header.style.cursor = 'pointer';
            header.addEventListener('click', function() {
                const table = this.closest('table');
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr'));
                const column = Array.from(this.parentNode.children).indexOf(this);
                const currentOrder = this.dataset.sortOrder || 'asc';
                const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
                
                rows.sort((a, b) => {
                    const aVal = a.children[column].textContent.trim();
                    const bVal = b.children[column].textContent.trim();
                    
                    if (newOrder === 'asc') {
                        return aVal.localeCompare(bVal, undefined, { numeric: true });
                    } else {
                        return bVal.localeCompare(aVal, undefined, { numeric: true });
                    }
                });
                
                // Clear existing sort indicators
                this.parentNode.querySelectorAll('th').forEach(th => {
                    th.removeAttribute('data-sort-order');
                    th.classList.remove('sort-asc', 'sort-desc');
                });
                
                // Set new sort indicator
                this.dataset.sortOrder = newOrder;
                this.classList.add(`sort-${newOrder}`);
                
                // Reorder rows
                rows.forEach(row => tbody.appendChild(row));
            });
        });
    },

    // Table search functionality
    initTableSearch: function() {
        document.querySelectorAll('.table-search').forEach(searchInput => {
            const table = document.querySelector(searchInput.dataset.table);
            if (table) {
                searchInput.addEventListener('input', function() {
                    const searchTerm = this.value.toLowerCase();
                    const rows = table.querySelectorAll('tbody tr');
                    
                    rows.forEach(row => {
                        const text = row.textContent.toLowerCase();
                        const shouldShow = text.includes(searchTerm);
                        row.style.display = shouldShow ? '' : 'none';
                    });
                });
            }
        });
    },

    // ===== FORM ENHANCEMENTS =====
    initForms: function() {
        // Form validation enhancements
        this.initFormValidation();
        
        // Auto-save functionality
        this.initAutoSave();
        
        // File upload enhancements
        this.initFileUploads();
        
        // Dynamic form fields
        this.initDynamicFields();
    },

    // Enhanced form validation
    initFormValidation: function() {
        document.querySelectorAll('form[novalidate]').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!this.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    // Focus on first invalid field
                    const firstInvalid = this.querySelector(':invalid');
                    if (firstInvalid) {
                        firstInvalid.focus();
                    }
                }
                this.classList.add('was-validated');
            });
        });

        // Real-time validation feedback
        document.querySelectorAll('input, select, textarea').forEach(field => {
            field.addEventListener('blur', function() {
                if (this.hasAttribute('required') || this.value) {
                    this.classList.toggle('is-valid', this.checkValidity());
                    this.classList.toggle('is-invalid', !this.checkValidity());
                }
            });
        });
    },

    // Auto-save functionality
    initAutoSave: function() {
        const autoSaveForms = document.querySelectorAll('form[data-autosave]');
        
        autoSaveForms.forEach(form => {
            const formData = new FormData(form);
            let saveTimeout;
            
            form.addEventListener('input', function() {
                clearTimeout(saveTimeout);
                saveTimeout = setTimeout(() => {
                    PIMS.autoSaveForm(form);
                }, 2000); // Save after 2 seconds of inactivity
            });
        });
    },

    // Auto-save form data
    autoSaveForm: function(form) {
        const formData = new FormData(form);
        const formId = form.id || 'unnamed-form';
        
        try {
            const data = {};
            for (let [key, value] of formData.entries()) {
                data[key] = value;
            }
            localStorage.setItem(`autosave_${formId}`, JSON.stringify(data));
            this.showAutoSaveIndicator();
        } catch (e) {
            console.log('Could not auto-save form data');
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
        if (mimeType.includes('zip') || mimeType.includes('rar')) return 'file-zip';
        return 'file-text';
    },

    // Format file size
    formatFileSize: function(bytes) {
        if (bytes === 0) return '0 Bytes';
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    // Dynamic form fields
    initDynamicFields: function() {
        // Add field buttons
        document.querySelectorAll('[data-add-field]').forEach(button => {
            button.addEventListener('click', function() {
                const template = document.querySelector(this.dataset.addField);
                if (template) {
                    const clone = template.cloneNode(true);
                    clone.style.display = '';
                    template.parentNode.insertBefore(clone, template);
                }
            });
        });

        // Remove field buttons
        document.addEventListener('click', function(e) {
            if (e.target.matches('[data-remove-field]')) {
                const field = e.target.closest(e.target.dataset.removeField);
                if (field) {
                    field.remove();
                }
            }
        });
    },

    // ===== IMAGE HANDLING =====
    initImageHandling: function() {
        // Lazy loading for images
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

        // Image error handling
        document.querySelectorAll('img').forEach(img => {
            img.addEventListener('error', function() {
                this.src = '/static/images/placeholder.png'; // Fallback image
                this.classList.add('image-error');
            });
        });
    },

    // ===== CHART INITIALIZATION =====
    initCharts: function() {
        // Initialize Chart.js charts if the library is available
        if (typeof Chart !== 'undefined') {
            // Set default Chart.js configuration
            Chart.defaults.responsive = true;
            Chart.defaults.maintainAspectRatio = false;
            Chart.defaults.plugins.legend.display = true;
            
            // Initialize charts with data attributes
            document.querySelectorAll('canvas[data-chart]').forEach(canvas => {
                try {
                    const chartData = JSON.parse(canvas.dataset.chart);
                    new Chart(canvas, chartData);
                } catch (e) {
                    console.error('Error initializing chart:', e);
                }
            });
        }
    },

    // ===== UTILITY FUNCTIONS =====
    
    // Loading overlay
    showLoading: function() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.remove('d-none');
        }
    },

    hideLoading: function() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) {
            overlay.classList.add('d-none');
        }
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
    },

    // Throttle function
    throttle: function(func, limit) {
        let inThrottle;
        return function() {
            const args = arguments;
            const context = this;
            if (!inThrottle) {
                func.apply(context, args);
                inThrottle = true;
                setTimeout(() => inThrottle = false, limit);
            }
        };
    },

    // Copy to clipboard
    copyToClipboard: function(text) {
        if (navigator.clipboard) {
            return navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers
            const textArea = document.createElement('textarea');
            textArea.value = text;
            document.body.appendChild(textArea);
            textArea.select();
            document.execCommand('copy');
            document.body.removeChild(textArea);
            return Promise.resolve();
        }
    },

    // Format numbers
    formatNumber: function(num, decimals = 0) {
        return new Intl.NumberFormat('en-US', {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals
        }).format(num);
    },

    // Format currency (Bangladesh Taka)
    formatCurrency: function(amount) {
        return new Intl.NumberFormat('en-BD', {
            style: 'currency',
            currency: 'BDT'
        }).format(amount);
    },

    // Format dates
    formatDate: function(date, options = {}) {
        const defaultOptions = {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        return new Intl.DateTimeFormat('en-BD', { ...defaultOptions, ...options }).format(new Date(date));
    },

    // Get relative time
    getRelativeTime: function(date) {
        const now = new Date();
        const targetDate = new Date(date);
        const diffTime = now - targetDate;
        const diffDays = Math.floor(diffTime / (1000 * 60 * 60 * 24));
        
        if (diffDays === 0) return 'Today';
        if (diffDays === 1) return 'Yesterday';
        if (diffDays < 7) return `${diffDays} days ago`;
        if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
        if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
        return `${Math.floor(diffDays / 365)} years ago`;
    },

    // Validate email
    isValidEmail: function(email) {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    },

    // Validate phone number (Bangladesh format)
    isValidPhone: function(phone) {
        const phoneRegex = /^(\+88)?01[3-9]\d{8}$/;
        return phoneRegex.test(phone.replace(/\s/g, ''));
    },

    // Local storage helpers
    storage: {
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch (e) {
                console.error('Error saving to localStorage:', e);
                return false;
            }
        },
        
        get: function(key, defaultValue = null) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.error('Error reading from localStorage:', e);
                return defaultValue;
            }
        },
        
        remove: function(key) {
            try {
                localStorage.removeItem(key);
                return true;
            } catch (e) {
                console.error('Error removing from localStorage:', e);
                return false;
            }
        },
        
        clear: function() {
            try {
                localStorage.clear();
                return true;
            } catch (e) {
                console.error('Error clearing localStorage:', e);
                return false;
            }
        }
    },

    // AJAX helpers
    ajax: {
        get: function(url, options = {}) {
            return fetch(url, {
                method: 'GET',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    ...options.headers
                },
                ...options
            });
        },
        
        post: function(url, data, options = {}) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            
            return fetch(url, {
                method: 'POST',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                    ...options.headers
                },
                body: data instanceof FormData ? data : JSON.stringify(data),
                ...options
            });
        },
        
        put: function(url, data, options = {}) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            
            return fetch(url, {
                method: 'PUT',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                body: JSON.stringify(data),
                ...options
            });
        },
        
        delete: function(url, options = {}) {
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
            
            return fetch(url, {
                method: 'DELETE',
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': csrfToken,
                    ...options.headers
                },
                ...options
            });
        }
    },

    // Event helpers
    on: function(selector, event, handler, options = {}) {
        document.addEventListener(event, function(e) {
            if (e.target.matches(selector)) {
                handler.call(e.target, e);
            }
        }, options);
    },

    off: function(element, event, handler) {
        if (element) {
            element.removeEventListener(event, handler);
        }
    },

    // Custom events
    trigger: function(element, eventName, detail = {}) {
        const event = new CustomEvent(eventName, {
            detail: detail,
            bubbles: true,
            cancelable: true
        });
        element.dispatchEvent(event);
    },

    // Performance monitoring
    performance: {
        marks: {},
        
        mark: function(name) {
            this.marks[name] = performance.now();
        },
        
        measure: function(startMark, endMark = null) {
            const start = this.marks[startMark];
            const end = endMark ? this.marks[endMark] : performance.now();
            return end - start;
        },
        
        log: function(name, startMark, endMark = null) {
            const duration = this.measure(startMark, endMark);
            console.log(`${name}: ${duration.toFixed(2)}ms`);
        }
    },

    // Error handling
    handleError: function(error, context = '') {
        console.error(`PIMS Error ${context ? `(${context})` : ''}:`, error);
        
        // Log to server if error reporting endpoint exists
        if (window.PIMS_ERROR_ENDPOINT) {
            this.ajax.post(window.PIMS_ERROR_ENDPOINT, {
                error: error.message || error,
                stack: error.stack,
                context: context,
                url: window.location.href,
                userAgent: navigator.userAgent,
                timestamp: new Date().toISOString()
            }).catch(e => {
                console.error('Failed to log error to server:', e);
            });
        }
    },

    // Keyboard shortcuts
    shortcuts: {
        bindings: {},
        
        bind: function(key, callback, options = {}) {
            const { ctrl = false, shift = false, alt = false, meta = false } = options;
            const binding = `${ctrl ? 'ctrl+' : ''}${shift ? 'shift+' : ''}${alt ? 'alt+' : ''}${meta ? 'meta+' : ''}${key.toLowerCase()}`;
            
            this.bindings[binding] = callback;
        },
        
        init: function() {
            document.addEventListener('keydown', (e) => {
                const key = e.key.toLowerCase();
                const binding = `${e.ctrlKey ? 'ctrl+' : ''}${e.shiftKey ? 'shift+' : ''}${e.altKey ? 'alt+' : ''}${e.metaKey ? 'meta+' : ''}${key}`;
                
                if (this.bindings[binding]) {
                    e.preventDefault();
                    this.bindings[binding](e);
                }
            });
        }
    },

    // Initialize keyboard shortcuts
    initKeyboardShortcuts: function() {
        this.shortcuts.init();
        
        // Default shortcuts
        this.shortcuts.bind('/', () => {
            const searchInput = document.querySelector('input[type="search"], .table-search');
            if (searchInput) {
                searchInput.focus();
            }
        });
        
        this.shortcuts.bind('escape', () => {
            // Close modals, dropdowns, etc.
            document.querySelectorAll('.modal.show').forEach(modal => {
                const modalInstance = bootstrap.Modal.getInstance(modal);
                if (modalInstance) modalInstance.hide();
            });
            
            document.querySelectorAll('.dropdown-menu.show').forEach(dropdown => {
                dropdown.classList.remove('show');
            });
        });
        
        // Sidebar toggle shortcut
        this.shortcuts.bind('s', () => {
            const sidebarToggle = document.querySelector('.sidebar-toggle');
            if (sidebarToggle) {
                sidebarToggle.click();
            }
        }, { ctrl: true });
    }
};

// Initialize keyboard shortcuts after PIMS is loaded
document.addEventListener('DOMContentLoaded', function() {
    // Initialize shortcuts after main PIMS initialization
    setTimeout(() => {
        PIMS.initKeyboardShortcuts();
    }, 100);
});

// Global error handler
window.addEventListener('error', function(e) {
    PIMS.handleError(e.error, 'Global Error Handler');
});

// Unhandled promise rejection handler
window.addEventListener('unhandledrejection', function(e) {
    PIMS.handleError(e.reason, 'Unhandled Promise Rejection');
});

// Expose PIMS globally for debugging and external use
window.PIMS = PIMS;

// Parliament IT Inventory Management System
// Location: Dhaka, Bangladesh
// Enhanced with collapsible sidebar and modern JavaScript features