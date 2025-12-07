/* admin/js/followup.js - READ ONLY VERSION */

class FollowupManager {
    constructor() {
        this.followups = [];
        this.users = [];
    }

    async init() {
        // Load users for filter dropdown
        await this.loadUsers();

        // Load followups
        await this.loadFollowups();

        // Setup event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Filters
        const statusFilter = document.getElementById('statusFilter');
        const userFilter = document.getElementById('userFilter');
        const dateFrom = document.getElementById('dateFrom');
        const dateTo = document.getElementById('dateTo');
        const searchInput = document.getElementById('searchInput');

        if (statusFilter) statusFilter.addEventListener('change', () => this.loadFollowups());
        if (userFilter) userFilter.addEventListener('change', () => this.loadFollowups());
        if (dateFrom) dateFrom.addEventListener('change', () => this.loadFollowups());
        if (dateTo) dateTo.addEventListener('change', () => this.loadFollowups());
        if (searchInput) {
            searchInput.addEventListener('input', this.debounce(() => this.loadFollowups(), 500));
        }
    }

    debounce(func, wait) {
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

    async loadUsers() {
        try {
            const resp = await auth.makeAuthenticatedRequest('/api/admin/users?per_page=1000');
            if (!resp) return;

            const data = await resp.json();
            if (resp.ok) {
                this.users = data.users || [];
                this.populateUserFilter();
            }
        } catch (e) {
            console.error('Failed to load users:', e);
        }
    }

    populateUserFilter() {
        const userFilterSelect = document.getElementById('userFilter');

        if (userFilterSelect) {
            userFilterSelect.innerHTML = '<option value="">All Users</option>';
            this.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = user.name;
                userFilterSelect.appendChild(option);
            });
        }
    }

    async loadFollowups() {
        try {
            // Build query params
            const params = new URLSearchParams();

            const status = document.getElementById('statusFilter')?.value;
            const userId = document.getElementById('userFilter')?.value;
            const dateFrom = document.getElementById('dateFrom')?.value;
            const dateTo = document.getElementById('dateTo')?.value;
            const search = document.getElementById('searchInput')?.value;

            if (status) params.append('status', status);
            if (userId) params.append('user_id', userId);
            if (dateFrom) params.append('date_from', dateFrom);
            if (dateTo) params.append('date_to', dateTo);
            if (search) params.append('search', search);

            const url = `/api/followup/list?${params.toString()}`;
            const resp = await auth.makeAuthenticatedRequest(url);

            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                this.followups = data.followups || [];
                this.render();
            } else {
                auth.showNotification(data.error || 'Failed to load follow-ups', 'error');
            }
        } catch (e) {
            console.error('Load followups error:', e);
            auth.showNotification('Failed to load follow-ups', 'error');
        }
    }

    render() {
        const tbody = document.getElementById('followupsTableBody');
        if (!tbody) return;

        if (!this.followups.length) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="5" class="px-6 py-12 text-center text-gray-500">
                        <i class="fas fa-calendar-times text-4xl mb-3 text-gray-300"></i>
                        <p class="text-lg font-medium">No follow-ups found</p>
                        <p class="text-sm">Follow-ups created from the mobile app will appear here</p>
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.followups.map(f => {
            const statusColors = {
                pending: 'bg-yellow-100 text-yellow-800',
                completed: 'bg-green-100 text-green-800',
                cancelled: 'bg-red-100 text-red-800'
            };

            const statusIcons = {
                pending: 'fa-clock',
                completed: 'fa-check-circle',
                cancelled: 'fa-times-circle'
            };

            const dateTime = new Date(f.date_time);
            const formattedDateTime = window.formatDateTime ? window.formatDateTime(f.date_time) : dateTime.toLocaleString();

            return `
                <tr class="hover:bg-gray-50 transition-colors">
                    <td class="px-6 py-4">
                        <div class="font-medium text-gray-900">${f.contact_name || '-'}</div>
                        ${f.message ? `<div class="text-sm text-gray-500 truncate max-w-xs">${f.message}</div>` : ''}
                    </td>
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-2">
                            <i class="fas fa-phone text-gray-400"></i>
                            <span class="text-gray-900">${f.phone}</span>
                        </div>
                    </td>
                    <td class="px-6 py-4">
                        <div class="text-gray-900">${f.user_name}</div>
                    </td>
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-2">
                            <i class="fas fa-calendar text-gray-400"></i>
                            <span class="text-gray-900">${formattedDateTime}</span>
                        </div>
                    </td>
                    <td class="px-6 py-4">
                        <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium ${statusColors[f.status]}">
                            <i class="fas ${statusIcons[f.status]}"></i>
                            ${f.status.charAt(0).toUpperCase() + f.status.slice(1)}
                        </span>
                    </td>
                </tr>
            `;
        }).join('');
    }

    // Method called by main.js when section is activated
    load() {
        this.loadFollowups();
    }
}

// Initialize and expose to window
const followupManager = new FollowupManager();
window.followupManager = followupManager;
