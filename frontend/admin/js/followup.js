/* admin/js/followup.js */

class FollowupManager {
    constructor() {
        this.followups = [];
        this.tbody = document.getElementById('followupsTableBody');
        this.emptyState = document.getElementById('followupsEmptyState');
        this.userFilter = document.getElementById('followupUserFilter');
        this.dateFilters = document.querySelectorAll('.followup-date-filter');
        this.currentFilter = 'all';
        this.currentUserId = 'all';

        this.initFilters();
    }

    initFilters() {
        // User Filter Change
        if (this.userFilter) {
            this.userFilter.addEventListener('change', (e) => {
                this.currentUserId = e.target.value;
                this.load();
            });
        }

        // Date Filter Clicks
        this.dateFilters.forEach(btn => {
            btn.addEventListener('click', () => {
                // Update active state
                this.dateFilters.forEach(b => {
                    b.classList.remove('bg-gray-100', 'active', 'text-gray-900', 'font-semibold');
                    b.classList.add('text-gray-700', 'hover:bg-gray-50'); // Default inactive
                });

                // Active style
                btn.classList.remove('text-gray-700', 'hover:bg-gray-50');
                btn.classList.add('bg-gray-100', 'active', 'text-gray-900', 'font-semibold');

                this.currentFilter = btn.dataset.filter;
                this.load();
            });
        });
    }

    // Called by main.js when the section is activated
    async load() {
        // Load users only once if empty
        if (this.userFilter && this.userFilter.options.length <= 1) {
            await this.loadUsers();
        }
        await this.fetchFollowups();
        this.render();
    }

    async loadUsers() {
        try {
            console.log('Fetching users for filter...');
            // Request large page size to get all users for the dropdown
            const response = await auth.makeAuthenticatedRequest('/api/admin/users?per_page=1000');
            if (response && response.ok) {
                const data = await response.json();
                console.log('Users fetched:', data);
                const users = data.users || [];

                // Clear existing (except "All")
                while (this.userFilter.options.length > 1) {
                    this.userFilter.remove(1);
                }

                if (users.length === 0) {
                    console.warn('No users returned from API');
                }

                users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = user.name || user.email || `User ${user.id}`;
                    this.userFilter.appendChild(option);
                });

                // Restore selection if reloaded
                this.userFilter.value = this.currentUserId;
            } else {
                console.error('Failed to fetch users response not OK');
            }
        } catch (error) {
            console.error('Failed to load users for filter', error);
        }
    }

    async fetchFollowups() {
        try {
            const params = new URLSearchParams();
            if (this.currentUserId !== 'all') params.append('user_id', this.currentUserId);
            if (this.currentFilter !== 'all') params.append('filter', this.currentFilter);

            const url = `/api/admin/followups?${params.toString()}`;
            const response = await auth.makeAuthenticatedRequest(url);

            if (response && response.ok) {
                this.followups = await response.json();
            } else {
                console.error('Failed to fetch followups');
                auth.showNotification('Failed to load follow-up reminders', 'error');
                this.followups = [];
            }
        } catch (error) {
            console.error('Error fetching followups:', error);
            auth.showNotification('Error loading follow-up reminders', 'error');
            this.followups = [];
        }
    }

    render() {
        if (!this.tbody) return;

        this.tbody.innerHTML = '';

        if (this.followups.length === 0) {
            if (this.emptyState) this.emptyState.classList.remove('hidden');
            return;
        }

        if (this.emptyState) this.emptyState.classList.add('hidden');

        this.followups.forEach(f => {
            const tr = document.createElement('tr');
            tr.className = 'hover:bg-gray-50 transition-colors';

            // Format dates using the global formatDateTime function (12-hour format with AM/PM)
            const dateTime = window.formatDateTime(f.date_time);
            const createdAt = window.formatDateTime(f.created_at);

            // Status Styles
            let statusClass = 'bg-gray-100 text-gray-800';
            if (f.status === 'pending') statusClass = 'bg-yellow-100 text-yellow-800';
            if (f.status === 'completed') statusClass = 'bg-green-100 text-green-800';
            if (f.status === 'cancelled') statusClass = 'bg-red-100 text-red-800';

            tr.innerHTML = `
        <td class="px-6 py-4">
            <div class="font-medium text-gray-900">${f.contact_name || 'No Name'}</div>
        </td>
        <td class="px-6 py-4 text-sm text-gray-900">${f.phone}</td>
        <td class="px-6 py-4">
            <div class="text-sm text-gray-500 max-w-xs truncate" title="${f.message || ''}">${f.message || '-'}</div>
        </td>
        <td class="px-6 py-4 text-sm text-gray-900">${f.user_name || 'Unknown'}</td>
         <td class="px-6 py-4 text-sm text-gray-900">${dateTime}</td>
        <td class="px-6 py-4">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${statusClass}">
            ${f.status.toUpperCase()}
            </span>
        </td>
         <td class="px-6 py-4 text-sm text-gray-500">${createdAt}</td>
      `;
            this.tbody.appendChild(tr);
        });
    }
}

// Initialize and expose
const followupManager = new FollowupManager();
window.followupManager = followupManager;
