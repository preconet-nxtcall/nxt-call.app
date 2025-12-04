/* admin/js/users.js */

class UsersManager {
  constructor() {
    this.users = [];
    this.page = 1;
    this.per_page = 25;

    // Bind form submit
    const form = document.getElementById('createUserForm');
    if (form) form.addEventListener('submit', (e) => { e.preventDefault(); this.createUser(); });

    // Bind Search & Filter
    const searchInput = document.getElementById('userSearchInput');
    const statusFilter = document.getElementById('userStatusFilter');

    if (searchInput) {
      searchInput.addEventListener('input', this.debounce(() => this.loadUsers(), 500));
    }
    if (statusFilter) {
      statusFilter.addEventListener('change', () => this.loadUsers());
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

  // Standard interface for main.js
  load() {
    const searchInput = document.getElementById('userSearchInput');
    const statusFilter = document.getElementById('userStatusFilter');
    if (searchInput) searchInput.value = "";
    if (statusFilter) statusFilter.value = "all";
    this.loadUsers();
  }

  // MAIN LOADER ---------------------------------
  async loadUsers() {
    try {
      // Extract filters from DOM
      const searchInput = document.getElementById('userSearchInput');
      const statusFilter = document.getElementById('userStatusFilter');

      const search = searchInput ? searchInput.value : "";
      const status = statusFilter ? statusFilter.value : "all";

      // Build URL
      let url = `/api/admin/users?page=${this.page}&per_page=${this.per_page}`;

      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (status !== "all") url += `&status=${status}`;

      const resp = await auth.makeAuthenticatedRequest(url);

      if (!resp) return;
      const data = await resp.json();

      if (!resp.ok) {
        auth.showNotification(data.error || 'Failed to load users', 'error');
        return;
      }

      this.users = data.users || [];
      this.render();

    } catch (e) {
      console.error(e);
      auth.showNotification('Failed to load users', 'error');
    }
  }

  // RENDER TABLE --------------------------------
  render() {
    const body = document.getElementById('usersTableBody');
    if (!body) return;

    if (!this.users.length) {
      body.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-gray-500">No users found</td></tr>`;
      return;
    }

    body.innerHTML = this.users.map(u => `
      <tr class="hover:bg-gray-50 transition-colors">
        <td class="p-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center font-bold shadow-sm">
              ${(u.name || 'U')[0].toUpperCase()}
            </div>
            <div>
              <div class="font-medium text-gray-900">${u.name}</div>
              <div class="text-xs text-gray-500">${u.email}</div>
            </div>
          </div>
        </td>

        <td class="p-3 text-sm text-gray-600">${u.phone || 'N/A'}</td>

        <td class="p-3 font-semibold text-sm ${u.performance_score >= 70 ? 'text-green-600' : u.performance_score >= 40 ? 'text-yellow-600' : 'text-red-600'}">
          ${u.performance_score ?? 0}%
        </td>

        <td class="p-3">
          <span class="${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'} px-2 py-1 rounded-full text-xs font-medium">
            ${u.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>

        <td class="p-3 text-right">
          <div class="flex items-center justify-end gap-2">
            <button onclick="usersManager.view(${u.id})" class="p-1.5 text-blue-600 hover:bg-blue-50 rounded transition-colors" title="View User">
              <i class="fas fa-eye"></i>
            </button>
            <button onclick="usersManager.toggleStatus(${u.id}, ${u.is_active})" 
              class="p-1.5 ${u.is_active ? 'text-orange-500 hover:bg-orange-50' : 'text-green-500 hover:bg-green-50'} rounded transition-colors"
              title="${u.is_active ? 'Block User' : 'Unblock User'}">
              <i class="fas ${u.is_active ? 'fa-ban' : 'fa-check-circle'}"></i>
            </button>
            <button onclick="usersManager.delete(${u.id})" class="p-1.5 text-red-600 hover:bg-red-50 rounded transition-colors" title="Delete User">
              <i class="fas fa-trash"></i>
            </button>
          </div>
        </td>
      </tr>
    `).join('');
  }

  // VIEW USER -----------------------------------
  async view(id) {
    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/user-analytics/${id}`);
      if (!resp) return;

      const data = await resp.json();
      if (!resp.ok) {
        auth.showNotification(data.error || 'Load failed', 'error');
        return;
      }

      const analytics = data.analytics;
      const user = analytics.user;

      // Populate Modal
      document.getElementById('um-modal-name').textContent = user.name || '-';
      document.getElementById('um-modal-email').textContent = user.email || '-';
      document.getElementById('um-modal-phone').textContent = user.phone || '-'; // Phone might be in user object or not, depending on API. Assuming it's in user object from analytics response.

      // Note: The analytics.user object in admin.py only has id, name, email. 
      // If phone is needed, we might need to fetch it separately or update backend. 
      // For now, let's use what we have or placeholder.
      // Actually, let's check if we can get phone from the list if we have it, or just show '-' if missing.

      // Status is not in analytics.user. We can infer or fetch. 
      // But wait, the previous code used `data.user` which had everything. 
      // `user-analytics` returns `analytics` object.
      // Let's rely on what `user-analytics` returns.

      // Update: I will update the backend to include phone and status in user-analytics if needed, 
      // BUT for now I will just use what is available. 
      // `user-analytics` returns: user {id, name, email}, calls, attendance, last_sync, last_login, performance.

      // I'll try to find the user in `this.users` to get status and phone if missing.
      const localUser = this.users.find(u => u.id === id);
      if (localUser) {
        document.getElementById('um-modal-phone').textContent = localUser.phone || '-';
        const statusEl = document.getElementById('um-modal-status');
        statusEl.textContent = localUser.is_active ? 'Active' : 'Inactive';
        statusEl.className = `text-sm font-medium ${localUser.is_active ? 'text-green-600' : 'text-red-600'}`;
        document.getElementById('um-modal-created').textContent = localUser.created_at ? new Date(localUser.created_at).toLocaleDateString() : '-';
      }

      document.getElementById('um-modal-last-sync').textContent = analytics.last_sync ? new Date(analytics.last_sync).toLocaleString() : 'Never';
      document.getElementById('um-modal-last-login').textContent = analytics.last_login ? new Date(analytics.last_login).toLocaleString() : 'Never';

      document.getElementById('um-modal-attendance').textContent = analytics.attendance.total_attendance || 0;
      document.getElementById('um-modal-calls').textContent = analytics.calls.total_calls || 0;
      document.getElementById('um-modal-score').textContent = analytics.performance.score || 0;

      // Show Modal
      document.getElementById('userManagementModal').classList.remove('hidden');

    } catch (e) {
      console.error(e);
      auth.showNotification('User data error', 'error');
    }
  }

  // TOGGLE STATUS -------------------------------
  async toggleStatus(id, currentStatus) {
    if (!confirm(`Are you sure you want to ${currentStatus ? 'block' : 'unblock'} this user?`)) return;

    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/user/${id}/status`, {
        method: 'PUT'
      });

      if (!resp) return;
      const data = await resp.json();

      if (resp.ok) {
        auth.showNotification(data.message, 'success');
        this.loadUsers();
      } else {
        auth.showNotification(data.error || 'Update failed', 'error');
      }

    } catch (e) {
      console.error(e);
      auth.showNotification('Update error', 'error');
    }
  }

  // DELETE USER ---------------------------------
  async delete(id) {
    if (!confirm('Are you sure? Delete user permanently?')) return;

    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/delete-user/${id}`, {
        method: 'DELETE'
      });

      if (!resp) return;
      const data = await resp.json();

      if (resp.ok) {
        auth.showNotification('User deleted', 'success');
        this.loadUsers();
      } else {
        auth.showNotification(data.error || 'Delete failed', 'error');
      }

    } catch (e) {
      console.error(e);
      auth.showNotification('Delete error', 'error');
    }
  }

  // CREATE USER ---------------------------------
  async createUser() {
    const name = document.getElementById('userName').value.trim();
    const email = document.getElementById('userEmail').value.trim();
    const phone = document.getElementById('userPhone').value.trim();
    const password = document.getElementById('userPassword').value;

    if (!name || !email || !password) {
      auth.showNotification('Name, Email, Password are required', 'error');
      return;
    }

    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/create-user', {
        method: 'POST',
        body: JSON.stringify({ name, email, phone, password })
      });

      if (!resp) return;
      const data = await resp.json();

      if (resp.ok) {
        auth.showNotification('User created successfully', 'success');
        document.getElementById('createUserForm').reset();
        this.loadUsers();
      } else {
        auth.showNotification(data.error || 'Failed to create user', 'error');
      }

    } catch (e) {
      console.error(e);
      auth.showNotification('Failed to create user', 'error');
    }
  }
}

const usersManager = new UsersManager();
