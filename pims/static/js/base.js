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
        sidebarBreakpoint: 991
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

        // Initialize collapsible menu items
        this.initCollapsibleMenus();
    },

    // Handle collapsible sidebar menus (Reports, etc.)
    initCollapsibleMenus: function() {
        const collapseButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
        
        collapseButtons.forEach(button => {
            const chevron = button.querySelector('.bi-chevron-down, .bi-chevron-up');
            
            if (chevron) {
                button.addEventListener('click', function() {
                    setTimeout(() => {
                        const isExpanded = button.getAttribute('aria-expanded') === 'true';
                        chevron.classList.toggle('bi-chevron-down', !isExpanded);
                        chevron.classList.toggle('bi-chevron-up', isExpanded);
                    }, 50);
                });
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
                const parentCollapse = link.closest('.collapse');
                if (parentCollapse) {
                    const bsCollapse = new bootstrap.Collapse(parentCollapse, {show: true});
                    
                    // Update chevron icon
                    const toggleButton = document.querySelector(`[data-bs-target="#${parentCollapse.id}"]`);
                    if (toggleButton) {
                        const chevron = toggleButton.querySelector('.bi-chevron-down');
                        if (chevron) {
                            chevron.classList.remove('bi-chevron-down');
                            chevron.classList.add('bi-chevron-up');
                        }
                    }
                }
            }
        });
    },

    // Smooth scrolling for anchor links
    initSmoothScrolling: function() {
        document.querySelectorAll('a[href^="#"]').forEach(anchor => {
            anchor.addEventListener('click', function(e) {
                const href = this.getAttribute('href');
                if (href.length > 1) { // More than just "#"
                    e.preventDefault();
                    const target = document.querySelector(href);
                    if (target) {
                        target.scrollIntoView({
                            behavior: 'smooth',
                            block: 'start'
                        });
                    }
                }
            });
        });
    },

    // Enhanced dropdown functionality
    initDropdowns: function() {
        const dropdowns = document.querySelectorAll('.dropdown-toggle');
        
        dropdowns.forEach(dropdown => {
            dropdown.addEventListener('shown.bs.dropdown', function() {
                const menu = this.nextElementSibling;
                if (menu && menu.classList.contains('dropdown-menu')) {
                    menu.style.opacity = '0';
                    menu.style.transform = 'translateY(-10px)';
                    
                    setTimeout(() => {
                        menu.style.transition = 'all 0.2s ease';
                        menu.style.opacity = '1';
                        menu.style.transform = 'translateY(0)';
                    }, 10);
                }
            });
        });
    },

    // ===== ALERT SYSTEM =====
    initAlerts: function() {
        // Auto-hide alerts after configured duration
        setTimeout(() => {
            const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
            alerts.forEach(alert => {
                const alertInstance = bootstrap.Alert.getOrCreateInstance(alert);
                if (alertInstance) {
                    alert.style.transition = 'all 0.3s ease';
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateY(-20px)';
                    
                    setTimeout(() => {
                        alertInstance.close();
                    }, 300);
                }
            });
        }, this.config.alertDuration);

        // Enhanced alert dismissal
        document.querySelectorAll('.alert .btn-close').forEach(button => {
            button.addEventListener('click', function() {
                const alert = this.closest('.alert');
                if (alert) {
                    alert.style.transition = 'all 0.3s ease';
                    alert.style.opacity = '0';
                    alert.style.transform = 'translateX(100%)';
                }
            });
        });
    },

    // ===== TOOLTIPS AND POPOVERS =====
    initTooltips: function() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl, {
                animation: true,
                delay: { show: 500, hide: 100 }
            });
        });

        // Initialize Bootstrap popovers
        const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
        popoverTriggerList.map(function(popoverTriggerEl) {
            return new bootstrap.Popover(popoverTriggerEl);
        });
    },

    // ===== MODAL FUNCTIONALITY =====
    initModals: function() {
        // Confirmation modals
        this.initConfirmModals();
        
        // QR Code modals
        this.initQRCodeModals();
        
        // Image preview modals
        this.initImageModals();
    },

    // Confirmation modals for delete actions
    initConfirmModals: function() {
        document.querySelectorAll('[data-confirm]').forEach(button => {
            button.addEventListener('click', function(e) {
                e.preventDefault();
                
                const message = this.getAttribute('data-confirm') || 'Are you sure?';
                const action = this.getAttribute('data-action') || 'delete';
                
                if (confirm(message)) {
                    // If it's a form, submit it
                    const form = this.closest('form');
                    if (form) {
                        form.submit();
                    } else {
                        // If it's a link, follow it
                        const href = this.getAttribute('href');
                        if (href) {
                            window.location.href = href;
                        }
                    }
                }
            });
        });
    },

    // QR Code modal functionality
    initQRCodeModals: function() {
        document.querySelectorAll('[data-qr-code]').forEach(button => {
            button.addEventListener('click', function() {
                const qrCodeUrl = this.getAttribute('data-qr-code');
                const modal = document.getElementById('qrCodeModal');
                
                if (modal && qrCodeUrl) {
                    const img = modal.querySelector('.qr-code-image');
                    if (img) {
                        img.src = qrCodeUrl;
                        img.alt = 'QR Code for ' + (this.getAttribute('data-device-name') || 'Device');
                    }
                }
            });
        });
    },

    // Image preview modals
    initImageModals: function() {
        document.querySelectorAll('.image-preview').forEach(img => {
            img.addEventListener('click', function() {
                const modal = document.getElementById('imageModal');
                if (modal) {
                    const modalImg = modal.querySelector('.modal-image');
                    if (modalImg) {
                        modalImg.src = this.src;
                        modalImg.alt = this.alt;
                    }
                    
                    const modalInstance = new bootstrap.Modal(modal);
                    modalInstance.show();
                }
            });
        });
    },

    // ===== TABLE FUNCTIONALITY =====
    initTables: function() {
        // Enhanced table sorting
        this.initTableSorting();
        
        // Table row selection
        this.initTableSelection();
        
        // Responsive table enhancements
        this.initResponsiveTables();
    },

    // Table sorting functionality
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
            
            const countElement = actionGroup.querySelector('.selection-count');
            if (countElement) {
                countElement.textContent = selectedItems.length;
            }
        });
    },

    // Responsive table enhancements
    initResponsiveTables: function() {
        // Add mobile-friendly data attributes
        document.querySelectorAll('.table-responsive table').forEach(table => {
            const headers = Array.from(table.querySelectorAll('thead th')).map(th => th.textContent.trim());
            
            table.querySelectorAll('tbody tr').forEach(row => {
                Array.from(row.querySelectorAll('td')).forEach((cell, index) => {
                    if (headers[index]) {
                        cell.setAttribute('data-label', headers[index]);
                    }
                });
            });
        });
    },

    // ===== FORM FUNCTIONALITY =====
    initForms: function() {
        // Form validation
        this.initFormValidation();
        
        // Image upload handling
        this.initImageUpload();
        
        // Auto-save functionality
        this.initAutoSave();
    },

    // Form validation
    initFormValidation: function() {
        document.querySelectorAll('.needs-validation').forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // Real-time validation
        document.querySelectorAll('input[required], select[required], textarea[required]').forEach(field => {
            field.addEventListener('blur', function() {
                if (this.checkValidity()) {
                    this.classList.remove('is-invalid');
                    this.classList.add('is-valid');
                } else {
                    this.classList.remove('is-valid');
                    this.classList.add('is-invalid');
                }
            });
        });
    },

    // ===== IMAGE HANDLING =====
    initImageHandling: function() {
        this.initImageUpload();
        this.initImagePreviews();
    },

    // Image upload with preview
    initImageUpload: function() {
        document.querySelectorAll('input[type="file"][accept*="image"]').forEach(input => {
            input.addEventListener('change', function() {
                const file = this.files[0];
                const previewContainer = document.querySelector(`[data-preview-for="${this.id}"]`);
                
                if (file && previewContainer) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        let img = previewContainer.querySelector('img');
                        if (!img) {
                            img = document.createElement('img');
                            img.className = 'img-thumbnail';
                            img.style.maxWidth = '200px';
                            img.style.maxHeight = '200px';
                            previewContainer.appendChild(img);
                        }
                        img.src = e.target.result;
                        img.style.display = 'block';
                    };
                    reader.readAsDataURL(file);
                }
            });
        });
    },

    // Image preview functionality
    initImagePreviews: function() {
        document.querySelectorAll('.image-preview').forEach(img => {
            img.style.cursor = 'pointer';
            img.addEventListener('click', function() {
                // Create modal if it doesn't exist
                let modal = document.getElementById('imagePreviewModal');
                if (!modal) {
                    modal = this.createImageModal();
                }
                
                const modalImg = modal.querySelector('.modal-body img');
                if (modalImg) {
                    modalImg.src = this.src;
                    modalImg.alt = this.alt;
                }
                
                const modalInstance = new bootstrap.Modal(modal);
                modalInstance.show();
            });
        });
    },

    // Create image preview modal
    createImageModal: function() {
        const modal = document.createElement('div');
        modal.className = 'modal fade';
        modal.id = 'imagePreviewModal';
        modal.innerHTML = `
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Image Preview</h5>
                        <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                    </div>
                    <div class="modal-body text-center">
                        <img src="" alt="" class="img-fluid">
                    </div>
                </div>
            </div>
        `;
        document.body.appendChild(modal);
        return modal;
    },

    // ===== AUTO-SAVE FUNCTIONALITY =====
    initAutoSave: function() {
        let autoSaveTimeout;
        const autoSaveForms = document.querySelectorAll('[data-auto-save]');
        
        autoSaveForms.forEach(form => {
            const inputs = form.querySelectorAll('input, select, textarea');
            
            inputs.forEach(input => {
                input.addEventListener('input', function() {
                    clearTimeout(autoSaveTimeout);
                    autoSaveTimeout = setTimeout(() => {
                        PIMS.performAutoSave(form);
                    }, 2000); // Auto-save after 2 seconds of inactivity
                });
            });
        });
    },

    // Perform auto-save
    performAutoSave: function(form) {
        const formData = new FormData(form);
        const saveUrl = form.getAttribute('data-auto-save');
        
        if (saveUrl) {
            fetch(saveUrl, {
                method: 'POST',
                body: formData,
                headers: {
                    'X-Requested-With': 'XMLHttpRequest',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                }
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    this.showToast('Draft saved automatically', 'success');
                }
            })
            .catch(error => {
                console.log('Auto-save failed:', error);
            });
        }
    },

    // ===== UTILITY FUNCTIONS =====
    
    // Show toast notification
    showToast: function(message, type = 'info') {
        // Create toast container if it doesn't exist
        let toastContainer = document.querySelector('.toast-container');
        if (!toastContainer) {
            toastContainer = document.createElement('div');
            toastContainer.className = 'toast-container position-fixed top-0 end-0 p-3';
            toastContainer.style.zIndex = '1090';
            document.body.appendChild(toastContainer);
        }

        // Create toast
        const toast = document.createElement('div');
        toast.className = `toast align-items-center text-white bg-${type} border-0`;
        toast.setAttribute('role', 'alert');
        toast.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;

        toastContainer.appendChild(toast);
        
        const toastInstance = new bootstrap.Toast(toast);
        toastInstance.show();

        // Remove toast element after it's hidden
        toast.addEventListener('hidden.bs.toast', function() {
            toast.remove();
        });
    },

    // Show loading overlay
    showLoading: function() {
        let overlay = document.querySelector('.loading-overlay');
        if (!overlay) {
            overlay = document.createElement('div');
            overlay.className = 'loading-overlay';
            overlay.innerHTML = '<div class="loading-spinner"></div>';
            document.body.appendChild(overlay);
        }
        overlay.style.display = 'flex';
    },

    // Hide loading overlay
    hideLoading: function() {
        const overlay = document.querySelector('.loading-overlay');
        if (overlay) {
            overlay.style.display = 'none';
        }
    },

    // AJAX setup for CSRF token
    initAjaxSetup: function() {
        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
        if (csrfToken) {
            // Set up fetch defaults for CSRF
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (typeof url === 'string' && !url.startsWith('http')) {
                    options.headers = options.headers || {};
                    if (options.method && options.method.toUpperCase() !== 'GET') {
                        options.headers['X-CSRFToken'] = csrfToken.value;
                    }
                }
                return originalFetch(url, options);
            };
        }
    }
};

// Export PIMS for global access
window.PIMS = PIMS;