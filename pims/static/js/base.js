// pims/static/js/base.js - Core JavaScript functionality for PIMS

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
        animationDuration: 300
    },

    // Initialize application
    init: function() {
        this.initSidebar();
        this.initSearch();
        this.initAlerts();
        this.initTooltips();
        this.initConfirmModals();
        this.initFormValidation();
        this.initTableSorting();
        this.initImagePreviews();
        this.initQRCodeModals();
        this.initAjaxSetup();
        
        console.log('PIMS initialized successfully');
    },

    // Sidebar functionality
    initSidebar: function() {
        const sidebarToggle = document.getElementById('sidebarToggle');
        const sidebar = document.getElementById('sidebar');
        
        if (sidebarToggle && sidebar) {
            sidebarToggle.addEventListener('click', function() {
                sidebar.classList.toggle('show');
            });

            // Close sidebar when clicking outside on mobile
            document.addEventListener('click', function(e) {
                if (window.innerWidth <= 768) {
                    if (!sidebar.contains(e.target) && !sidebarToggle.contains(e.target)) {
                        sidebar.classList.remove('show');
                    }
                }
            });

            // Handle window resize
            window.addEventListener('resize', function() {
                if (window.innerWidth > 768) {
                    sidebar.classList.remove('show');
                }
            });
        }

        // Active navigation highlighting
        this.highlightActiveNav();
    },

    // Highlight active navigation
    highlightActiveNav: function() {
        const currentPath = window.location.pathname;
        const navLinks = document.querySelectorAll('.sidebar .nav-link');
        
        navLinks.forEach(link => {
            const href = link.getAttribute('href');
            if (href && (currentPath === href || currentPath.startsWith(href + '/'))) {
                link.classList.add('active', 'bg-white', 'bg-opacity-10');
                
                // Expand parent collapse if nested
                const parentCollapse = link.closest('.collapse');
                if (parentCollapse) {
                    parentCollapse.classList.add('show');
                }
            }
        });
    },

    // Global search functionality
    initSearch: function() {
        const searchInput = document.getElementById('globalSearch');
        
        if (searchInput) {
            let searchTimeout;
            
            searchInput.addEventListener('input', function() {
                clearTimeout(searchTimeout);
                const query = this.value.trim();
                
                if (query.length >= 2) {
                    searchTimeout = setTimeout(() => {
                        PIMS.performSearch(query);
                    }, PIMS.config.searchDelay);
                } else {
                    PIMS.clearSearchResults();
                }
            });

            // Handle search form submission
            const searchForm = searchInput.closest('form');
            if (searchForm) {
                searchForm.addEventListener('submit', function(e) {
                    e.preventDefault();
                    const query = searchInput.value.trim();
                    if (query) {
                        window.location.href = `/search/?q=${encodeURIComponent(query)}`;
                    }
                });
            }
        }
    },

    // Perform global search
    performSearch: function(query) {
        // This would typically make an AJAX call to a search endpoint
        console.log('Searching for:', query);
        
        // Placeholder for search functionality
        // In a real implementation, this would call your search API
        /*
        fetch(`/api/search/?q=${encodeURIComponent(query)}`)
            .then(response => response.json())
            .then(data => {
                this.displaySearchResults(data);
            })
            .catch(error => {
                console.error('Search error:', error);
            });
        */
    },

    // Clear search results
    clearSearchResults: function() {
        const resultsContainer = document.getElementById('searchResults');
        if (resultsContainer) {
            resultsContainer.innerHTML = '';
            resultsContainer.style.display = 'none';
        }
    },

    // Alert management
    initAlerts: function() {
        // Auto-hide alerts after specified duration
        const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
        
        alerts.forEach(alert => {
            setTimeout(() => {
                if (alert.classList.contains('show')) {
                    const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                    bsAlert.close();
                }
            }, this.config.alertDuration);
        });

        // Add close button functionality
        document.addEventListener('click', function(e) {
            if (e.target.matches('.alert .btn-close')) {
                const alert = e.target.closest('.alert');
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }
        });
    },

    // Show dynamic alert
    showAlert: function(message, type = 'info', duration = null) {
        const alertContainer = document.getElementById('alertContainer') || this.createAlertContainer();
        
        const alertHtml = `
            <div class="alert alert-${type} alert-dismissible fade show" role="alert">
                <i class="bi bi-${this.getAlertIcon(type)} me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;
        
        alertContainer.insertAdjacentHTML('beforeend', alertHtml);
        
        // Auto-hide if duration specified
        if (duration) {
            const alert = alertContainer.lastElementChild;
            setTimeout(() => {
                const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
                bsAlert.close();
            }, duration);
        }
    },

    // Create alert container if it doesn't exist
    createAlertContainer: function() {
        const container = document.createElement('div');
        container.id = 'alertContainer';
        container.className = 'position-fixed top-0 end-0 p-3';
        container.style.zIndex = '9999';
        document.body.appendChild(container);
        return container;
    },

    // Get icon for alert type
    getAlertIcon: function(type) {
        const icons = {
            'success': 'check-circle',
            'error': 'exclamation-triangle',
            'warning': 'exclamation-circle',
            'info': 'info-circle',
            'danger': 'exclamation-triangle'
        };
        return icons[type] || 'info-circle';
    },

    // Initialize tooltips
    initTooltips: function() {
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function(tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    },

    // Initialize confirmation modals
    initConfirmModals: function() {
        document.addEventListener('click', function(e) {
            const confirmBtn = e.target.closest('[data-confirm]');
            if (confirmBtn) {
                e.preventDefault();
                
                const message = confirmBtn.getAttribute('data-confirm');
                const title = confirmBtn.getAttribute('data-confirm-title') || 'Confirm Action';
                const action = confirmBtn.getAttribute('href') || confirmBtn.getAttribute('data-action');
                
                PIMS.showConfirmModal(title, message, action);
            }
        });
    },

    // Show confirmation modal
    showConfirmModal: function(title, message, action) {
        const modalHtml = `
            <div class="modal fade" id="confirmModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body">
                            <p>${message}</p>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                            <button type="button" class="btn btn-danger" id="confirmAction">Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        const existingModal = document.getElementById('confirmModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('confirmModal'));
        modal.show();
        
        // Handle confirm action
        document.getElementById('confirmAction').addEventListener('click', function() {
            if (action.startsWith('http') || action.startsWith('/')) {
                window.location.href = action;
            } else if (typeof window[action] === 'function') {
                window[action]();
            }
            modal.hide();
        });
        
        // Clean up modal after hiding
        document.getElementById('confirmModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    },

    // Form validation
    initFormValidation: function() {
        const forms = document.querySelectorAll('.needs-validation');
        
        forms.forEach(form => {
            form.addEventListener('submit', function(e) {
                if (!form.checkValidity()) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                form.classList.add('was-validated');
            });
        });

        // Real-time validation for specific fields
        this.initRealTimeValidation();
    },

    // Real-time validation
    initRealTimeValidation: function() {
        // Employee ID validation
        const employeeIdInputs = document.querySelectorAll('input[name="employee_id"]');
        employeeIdInputs.forEach(input => {
            input.addEventListener('input', function() {
                const value = this.value;
                const isValid = /^\d+$/.test(value) && value.length >= 3;
                
                this.setCustomValidity(isValid ? '' : 'Employee ID must contain only numbers and be at least 3 digits');
                this.classList.toggle('is-valid', isValid && value.length > 0);
                this.classList.toggle('is-invalid', !isValid && value.length > 0);
            });
        });

        // Phone number validation
        const phoneInputs = document.querySelectorAll('input[name="phone_number"]');
        phoneInputs.forEach(input => {
            input.addEventListener('input', function() {
                const value = this.value;
                const isValid = /^(\+?8801[3-9]\d{8}|01[3-9]\d{8})$/.test(value) || value === '';
                
                this.setCustomValidity(isValid ? '' : 'Enter a valid Bangladesh phone number');
                this.classList.toggle('is-valid', isValid && value.length > 0);
                this.classList.toggle('is-invalid', !isValid && value.length > 0);
            });
        });
    },

    // Table sorting
    initTableSorting: function() {
        const sortableHeaders = document.querySelectorAll('th[data-sort]');
        
        sortableHeaders.forEach(header => {
            header.style.cursor = 'pointer';
            header.innerHTML += ' <i class="bi bi-arrow-down-up text-muted"></i>';
            
            header.addEventListener('click', function() {
                const table = this.closest('table');
                const column = this.getAttribute('data-sort');
                const currentOrder = this.getAttribute('data-order') || 'asc';
                const newOrder = currentOrder === 'asc' ? 'desc' : 'asc';
                
                this.setAttribute('data-order', newOrder);
                PIMS.sortTable(table, column, newOrder);
            });
        });
    },

    // Sort table
    sortTable: function(table, column, order) {
        const tbody = table.querySelector('tbody');
        const rows = Array.from(tbody.querySelectorAll('tr'));
        
        rows.sort((a, b) => {
            const aCell = a.querySelector(`[data-value="${column}"]`) || a.children[parseInt(column)];
            const bCell = b.querySelector(`[data-value="${column}"]`) || b.children[parseInt(column)];
            
            const aValue = aCell?.getAttribute('data-sort-value') || aCell?.textContent.trim() || '';
            const bValue = bCell?.getAttribute('data-sort-value') || bCell?.textContent.trim() || '';
            
            const comparison = aValue.localeCompare(bValue, undefined, { numeric: true });
            return order === 'asc' ? comparison : -comparison;
        });
        
        // Re-append sorted rows
        rows.forEach(row => tbody.appendChild(row));
    },

    // Image preview functionality
    initImagePreviews: function() {
        const imageInputs = document.querySelectorAll('input[type="file"][accept*="image"]');
        
        imageInputs.forEach(input => {
            input.addEventListener('change', function() {
                const file = this.files[0];
                const previewContainer = document.getElementById(this.id + '_preview') || this.parentNode.querySelector('.image-preview');
                
                if (file && previewContainer) {
                    const reader = new FileReader();
                    reader.onload = function(e) {
                        previewContainer.innerHTML = `<img src="${e.target.result}" class="img-thumbnail" style="max-width: 200px; max-height: 200px;">`;
                    };
                    reader.readAsDataURL(file);
                }
            });
        });
    },

    // QR Code modal functionality
    initQRCodeModals: function() {
        document.addEventListener('click', function(e) {
            const qrBtn = e.target.closest('[data-qr-code]');
            if (qrBtn) {
                e.preventDefault();
                const qrCodeUrl = qrBtn.getAttribute('data-qr-code');
                const title = qrBtn.getAttribute('data-qr-title') || 'QR Code';
                
                PIMS.showQRCodeModal(qrCodeUrl, title);
            }
        });
    },

    // Show QR code modal
    showQRCodeModal: function(qrCodeUrl, title) {
        const modalHtml = `
            <div class="modal fade" id="qrCodeModal" tabindex="-1">
                <div class="modal-dialog">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title">${title}</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                        </div>
                        <div class="modal-body text-center">
                            <img src="${qrCodeUrl}" alt="QR Code" class="img-fluid">
                            <div class="mt-3">
                                <button class="btn btn-primary" onclick="PIMS.downloadQRCode('${qrCodeUrl}', '${title}')">
                                    <i class="bi bi-download me-2"></i>Download
                                </button>
                                <button class="btn btn-secondary" onclick="PIMS.printQRCode('${qrCodeUrl}')">
                                    <i class="bi bi-printer me-2"></i>Print
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // Remove existing modal
        const existingModal = document.getElementById('qrCodeModal');
        if (existingModal) {
            existingModal.remove();
        }
        
        // Add modal to page
        document.body.insertAdjacentHTML('beforeend', modalHtml);
        
        const modal = new bootstrap.Modal(document.getElementById('qrCodeModal'));
        modal.show();
        
        // Clean up modal after hiding
        document.getElementById('qrCodeModal').addEventListener('hidden.bs.modal', function() {
            this.remove();
        });
    },

    // Download QR code
    downloadQRCode: function(url, filename) {
        const link = document.createElement('a');
        link.href = url;
        link.download = `${filename.replace(/\s+/g, '_')}_QR.png`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },

    // Print QR code
    printQRCode: function(url) {
        const printWindow = window.open('', '_blank');
        printWindow.document.write(`
            <html>
                <head>
                    <title>Print QR Code</title>
                    <style>
                        body { text-align: center; margin: 20px; }
                        img { max-width: 300px; }
                    </style>
                </head>
                <body>
                    <img src="${url}" alt="QR Code">
                    <script>window.print(); window.close();</script>
                </body>
            </html>
        `);
    },

    // AJAX setup
    initAjaxSetup: function() {
        // Get CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        
        if (csrfToken) {
            // Set default headers for fetch requests
            const originalFetch = window.fetch;
            window.fetch = function(url, options = {}) {
                if (options.method && options.method.toUpperCase() !== 'GET') {
                    options.headers = {
                        'X-CSRFToken': csrfToken,
                        'Content-Type': 'application/json',
                        ...options.headers
                    };
                }
                return originalFetch(url, options);
            };
        }
    },

    // Utility functions
    utils: {
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

        // Format date
        formatDate: function(date, format = 'yyyy-mm-dd') {
            if (!(date instanceof Date)) {
                date = new Date(date);
            }
            
            const year = date.getFullYear();
            const month = String(date.getMonth() + 1).padStart(2, '0');
            const day = String(date.getDate()).padStart(2, '0');
            
            return format.replace('yyyy', year).replace('mm', month).replace('dd', day);
        },

        // Copy to clipboard
        copyToClipboard: function(text) {
            navigator.clipboard.writeText(text).then(() => {
                PIMS.showAlert('Copied to clipboard!', 'success', 2000);
            }).catch(() => {
                PIMS.showAlert('Failed to copy to clipboard', 'error', 3000);
            });
        },

        // Validate file size
        validateFileSize: function(file, maxSizeMB = 2) {
            const maxSize = maxSizeMB * 1024 * 1024;
            return file.size <= maxSize;
        },

        // Generate random ID
        generateId: function(length = 8) {
            return Math.random().toString(36).substring(2, length + 2);
        }
    }
};

// Expose PIMS globally
window.PIMS = PIMS;