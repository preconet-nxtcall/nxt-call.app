/* admin/js/followup.js */

class FollowupManager {
    constructor() {
        this.followups = [];
        this.tbody = document.getElementById('followupsTableBody');
        this.emptyState = document.getElementById('followupsEmptyState');
    }

    // Called by main.js when the section is activated
    async load() {
        await this.fetchFollowups();
        this.render();
    }

    async fetchFollowups() {
        try {
            // Assuming auth.makeAuthenticatedRequest exists and handles tokens
            const response = await auth.makeAuthenticatedRequest('/api/admin/followups');
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

            // Format dates
            const dateTime = new Date(f.date_time).toLocaleString();
            const createdAt = new Date(f.created_at).toLocaleString();

            // Status Styles
            let statusClass = 'bg-gray-100 text-gray-800';
            if (f.status === 'pending') statusClass = 'bg-yellow-100 text-yellow-800';
            if (f.status === 'completed') statusClass = 'bg-green-100 text-green-800';
            if (f.status === 'cancelled') statusClass = 'bg-red-100 text-red-800';

            tr.innerHTML = `
        <td class="px-6 py-4">
            <div class="font-medium text-gray-900">${f.contact_name || 'No Name'}</div>
            ${f.message ? `<div class="text-sm text-gray-500 truncate max-w-xs" title="${f.message}">${f.message}</div>` : ''}
        </td>
        <td class="px-6 py-4 text-sm text-gray-900">${f.phone}</td>
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
