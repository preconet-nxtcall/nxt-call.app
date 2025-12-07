/* admin/js/followup.js */

class FollowupManager {
    constructor() {
        this.followups = [];
        this.users = [];
        this.editingId = null;
    }

    async init() {
        // Load users for dropdowns
        await this.loadUsers();

        // Load followups
        await this.loadFollowups();

        // Setup event listeners
        this.setupEventListeners();
    }

    setupEventListeners() {
        // Form submit
        const form = document.getElementById('followupForm');
        if (form) {
            form.addEventListener('submit', (e) => {
                e.preventDefault();
                this.saveFollowup();
            });
        }

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
                this.populateUserDropdowns();
            }
        } catch (e) {
            console.error('Failed to load users:', e);
        }
    }

    populateUserDropdowns() {
        const userIdSelect = document.getElementById('userId');
        const userFilterSelect = document.getElementById('userFilter');

        if (userIdSelect) {
            userIdSelect.innerHTML = '<option value="">Select User</option>';
            this.users.forEach(user => {
                const option = document.createElement('option');
                option.value = user.id;
                option.textContent = `${user.name} (${user.email})`;
                userIdSelect.appendChild(option);
            });
        }

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
                    <td colspan="6" class="px-6 py-12 text-center text-gray-500">
                        <i class="fas fa-calendar-times text-4xl mb-3 text-gray-300"></i>
                        <p class="text-lg font-medium">No follow-ups found</p>
                        <p class="text-sm">Create your first follow-up reminder to get started</p>
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
                    <td class="px-6 py-4">
                        <div class="flex items-center gap-2">
                            ${f.status === 'pending' ? `
                                <button onclick="followupManager.updateStatus(${f.id}, 'completed')" 
                                    class="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors" 
                                    title="Mark as Completed">
                                    <i class="fas fa-check"></i>
                                </button>
                            ` : ''}
                            <button onclick="followupManager.edit(${f.id})" 
                                class="p-2 text-blue-600 hover:bg-blue-50 rounded-lg transition-colors" 
                                title="Edit">
                                <i class="fas fa-edit"></i>
                            </button>
                            <button onclick="followupManager.delete(${f.id})" 
                                class="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors" 
                                title="Delete">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>
                </tr>
            `;
        }).join('');
    }

    openCreateModal() {
        this.editingId = null;
        document.getElementById('modalTitle').textContent = 'Create Follow-up';
        document.getElementById('followupForm').reset();
        document.getElementById('followupModal').classList.remove('hidden');
    }

    async edit(id) {
        try {
            const resp = await auth.makeAuthenticatedRequest(`/api/followup/${id}`);
            if (!resp) return;

            const data = await resp.json();
            if (resp.ok) {
                const f = data.followup;
                this.editingId = id;

                document.getElementById('modalTitle').textContent = 'Edit Follow-up';
                document.getElementById('userId').value = f.user_id;
                document.getElementById('contactName').value = f.contact_name || '';
                document.getElementById('phone').value = f.phone;
                document.getElementById('message').value = f.message || '';
                document.getElementById('reminderId').value = f.reminder_id || '';

                // Format datetime for input
                const dt = new Date(f.date_time);
                const formatted = dt.toISOString().slice(0, 16);
                document.getElementById('dateTime').value = formatted;

                document.getElementById('followupModal').classList.remove('hidden');
            } else {
                auth.showNotification(data.error || 'Failed to load follow-up', 'error');
            }
        } catch (e) {
            console.error('Edit error:', e);
            auth.showNotification('Failed to load follow-up', 'error');
        }
    }

    async saveFollowup() {
        try {
            const userId = document.getElementById('userId').value;
            const contactName = document.getElementById('contactName').value.trim();
            const phone = document.getElementById('phone').value.trim();
            const dateTime = document.getElementById('dateTime').value;
            const message = document.getElementById('message').value.trim();
            const reminderId = document.getElementById('reminderId').value.trim();

            if (!userId || !phone || !dateTime) {
                auth.showNotification('Please fill in all required fields', 'error');
                return;
            }

            const payload = {
                user_id: parseInt(userId),
                contact_name: contactName,
                phone: phone,
                date_time: dateTime,
                message: message,
                reminder_id: reminderId
            };

            let url, method;
            if (this.editingId) {
                url = `/api/followup/${this.editingId}`;
                method = 'PUT';
            } else {
                url = '/api/followup/create';
                method = 'POST';
            }

            const resp = await auth.makeAuthenticatedRequest(url, {
                method: method,
                body: JSON.stringify(payload)
            });

            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                auth.showNotification(this.editingId ? 'Follow-up updated successfully' : 'Follow-up created successfully', 'success');
                this.closeModal();
                this.loadFollowups();
            } else {
                auth.showNotification(data.error || 'Failed to save follow-up', 'error');
            }
        } catch (e) {
            console.error('Save error:', e);
            auth.showNotification('Failed to save follow-up', 'error');
        }
    }

    async updateStatus(id, status) {
        try {
            const resp = await auth.makeAuthenticatedRequest(`/api/followup/${id}/status`, {
                method: 'PUT',
                body: JSON.stringify({ status })
            });

            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                auth.showNotification(`Status updated to ${status}`, 'success');
                this.loadFollowups();
            } else {
                auth.showNotification(data.error || 'Failed to update status', 'error');
            }
        } catch (e) {
            console.error('Update status error:', e);
            auth.showNotification('Failed to update status', 'error');
        }
    }

    async delete(id) {
        if (!confirm('Are you sure you want to delete this follow-up?')) return;

        try {
            const resp = await auth.makeAuthenticatedRequest(`/api/followup/${id}`, {
                method: 'DELETE'
            });

            if (!resp) return;
            const data = await resp.json();

            if (resp.ok) {
                auth.showNotification('Follow-up deleted successfully', 'success');
                this.loadFollowups();
            } else {
                auth.showNotification(data.error || 'Failed to delete follow-up', 'error');
            }
        } catch (e) {
            console.error('Delete error:', e);
            auth.showNotification('Failed to delete follow-up', 'error');
        }
    }

    closeModal() {
        document.getElementById('followupModal').classList.add('hidden');
        document.getElementById('followupForm').reset();
        this.editingId = null;
    }
}

// Initialize
const followupManager = new FollowupManager();
