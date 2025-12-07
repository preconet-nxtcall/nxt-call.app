/* admin/js/followup.js */

class FollowupManager {
    constructor() {
        this.followups = [];
        this.currentPage = 1;
        this.totalPages = 1;
        this.totalItems = 0;

        this.tbody = document.getElementById('followupsTableBody');
        this.emptyState = document.getElementById('followupsEmptyState');
        this.userFilter = document.getElementById('followupUserFilter');
        this.dateFilters = document.querySelectorAll('.followup-date-filter');

        // Pager refs
        this.btnPrev = document.getElementById('btnPrevPage');
        this.btnNext = document.getElementById('btnNextPage');
        this.infoText = document.getElementById('followupPaginationInfo');

        this.currentFilter = 'all';
        this.currentUserId = 'all';

        this.initFilters();
        this.initPagination();
    }

    initFilters() {
        if (this.userFilter) {
            this.userFilter.addEventListener('change', (e) => {
                this.currentUserId = e.target.value;
                this.currentPage = 1; // Reset to page 1
                this.load();
            });
        }

        this.dateFilters.forEach(btn => {
            btn.addEventListener('click', () => {
                this.dateFilters.forEach(b => {
                    b.classList.remove('bg-gray-100', 'active', 'text-gray-900', 'font-semibold');
                    b.classList.add('text-gray-700', 'hover:bg-gray-50');
                });

                btn.classList.remove('text-gray-700', 'hover:bg-gray-50');
                btn.classList.add('bg-gray-100', 'active', 'text-gray-900', 'font-semibold');

                this.currentFilter = btn.dataset.filter;
                this.currentPage = 1; // Reset to page 1
                this.load();
            });
        });
    }

    initPagination() {
        if (this.btnPrev) {
            this.btnPrev.addEventListener('click', () => {
                if (this.currentPage > 1) {
                    this.currentPage--;
                    this.load();
                }
            });
        }
        if (this.btnNext) {
            this.btnNext.addEventListener('click', () => {
                if (this.currentPage < this.totalPages) {
                    this.currentPage++;
                    this.load();
                }
            });
        }
    }

    async load() {
        if (this.userFilter && this.userFilter.options.length <= 1) {
            await this.loadUsers();
        }
        await this.fetchFollowups();
        this.render();
        this.renderPagination();
    }

    async loadUsers() {
        try {
            const response = await auth.makeAuthenticatedRequest('/api/admin/users?per_page=1000');
            if (response && response.ok) {
                const data = await response.json();
                const users = data.users || [];

                while (this.userFilter.options.length > 1) {
                    this.userFilter.remove(1);
                }

                users.forEach(user => {
                    const option = document.createElement('option');
                    option.value = user.id;
                    option.textContent = user.name || user.email || `User ${user.id}`;
                    this.userFilter.appendChild(option);
                });

                this.userFilter.value = this.currentUserId;
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
            params.append('page', this.currentPage);
            params.append('per_page', 10); // Show 10 per page

            const url = `/api/admin/followups?${params.toString()}`;
            const response = await auth.makeAuthenticatedRequest(url);

            if (response && response.ok) {
                const data = await response.json();
                // Handle new PAGINATED response structure
                if (data.followups) {
                    this.followups = data.followups;
                    this.totalPages = data.pages;
                    this.totalItems = data.total;
                    this.currentPage = data.current_page;
                } else {
                    // Fallback for old list response
                    this.followups = Array.isArray(data) ? data : [];
                    this.totalPages = 1;
                    this.totalItems = this.followups.length;
                }
            } else {
                auth.showNotification('Failed to load follow-up reminders', 'error');
                this.followups = [];
            }
        } catch (error) {
            console.error('Error fetching followups:', error);
            this.followups = [];
        }
    }

    async completeFollowup(id) {
        if (!confirm('Mark this reminder as complete? It will be removed from the list.')) return;

        try {
            const response = await auth.makeAuthenticatedRequest(`/api/admin/followup/${id}`, {
                method: 'DELETE'
            });

            if (response && response.ok) {
                auth.showNotification('Reminder marked as completed', 'success');
                this.load(); // Reload list
            } else {
                auth.showNotification('Failed to complete reminder', 'error');
            }
        } catch (error) {
            console.error('Complete error:', error);
            auth.showNotification('Error completing reminder', 'error');
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
            tr.className = 'hover:bg-gray-50 transition-colors group';

            const dateTime = new Date(f.date_time).toLocaleString(undefined, {
                dateStyle: 'short', timeStyle: 'short'
            });
            const createdAt = new Date(f.created_at).toLocaleString(undefined, {
                dateStyle: 'short', timeStyle: 'short'
            });

            // Status Styles
            let statusBadge = `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-gray-100 text-gray-800">${f.status.toUpperCase()}</span>`;
            if (f.status === 'pending') statusBadge = `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800">PENDING</span>`;
            if (f.status === 'completed') statusBadge = `<span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">COMPLETED</span>`;

            tr.innerHTML = `
        <td class="px-6 py-4">
            <div class="font-medium text-gray-900">${f.contact_name || 'No Name'}</div>
        </td>
        <td class="px-6 py-4 text-sm text-gray-900 font-mono">${f.phone}</td>
        <td class="px-6 py-4">
            <div class="text-sm text-gray-500 max-w-xs truncate" title="${f.message || ''}">${f.message || '-'}</div>
        </td>
        <td class="px-6 py-4 text-sm text-gray-900">${f.user_name || 'Unknown'}</td>
        <td class="px-6 py-4 text-sm text-gray-500">${dateTime}</td>
        <td class="px-6 py-4">${statusBadge}</td>
        <td class="px-6 py-4 text-sm text-gray-400">${createdAt}</td>
        <td class="px-6 py-4 text-right">
            <button onclick="window.followupManager.completeFollowup('${f.reminder_id}')" 
                class="text-green-600 hover:text-green-900 font-medium text-sm border border-green-200 hover:bg-green-50 px-3 py-1 rounded transition-colors"
                title="Mark as Complete">
                Complete
            </button>
        </td>
      `;
            this.tbody.appendChild(tr);
        });
    }

    renderPagination() {
        if (!this.infoText || !this.btnPrev || !this.btnNext) return;

        this.infoText.textContent = `Showing page ${this.currentPage} of ${this.totalPages} (${this.totalItems} total)`;

        this.btnPrev.disabled = this.currentPage <= 1;
        this.btnNext.disabled = this.currentPage >= this.totalPages;
    }
}

// Initialize and expose
const followupManager = new FollowupManager();
window.followupManager = followupManager;
