/* admin/js/users.js */

class UsersManager {
  constructor() {
    this.users = [];
    this.page = 1;
    this.per_page = 25;

    // Bind form submit
    const form = document.getElementById('createUserForm');
    if (form) form.addEventListener('submit', (e)=>{ e.preventDefault(); this.createUser(); });
  }

  // MAIN LOADER ---------------------------------
  async loadUsers(filters = {}) {
    try {
      // Extract filters
      const search = filters.search || "";
      const status = filters.status || "all";

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
      <tr class="hover:bg-gray-50">
        <td class="p-3">
          <div class="flex items-center gap-3">
            <div class="w-10 h-10 rounded-full bg-blue-600 text-white flex items-center justify-center">
              ${(u.name || 'U')[0].toUpperCase()}
            </div>
            <div>
              <div class="font-medium">${u.name}</div>
              <div class="text-xs text-gray-500">${u.email}</div>
            </div>
          </div>
        </td>

        <td class="p-3">${u.phone || 'N/A'}</td>

        <td class="p-3 font-semibold ${u.performance_score >= 70 ? 'text-green-600' : u.performance_score >= 40 ? 'text-yellow-600' : 'text-red-600'}">
          ${u.performance_score ?? 0}%
        </td>

        <td class="p-3">
          <span class="${u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'} px-2 py-1 rounded text-xs">
            ${u.is_active ? 'Active' : 'Inactive'}
          </span>
        </td>

        <td class="p-3 text-right">
          <button onclick="usersManager.view(${u.id})" class="text-blue-600 mr-2">
            <i class="fas fa-eye"></i>
          </button>
          <button onclick="usersManager.delete(${u.id})" class="text-red-600">
            <i class="fas fa-trash"></i>
          </button>
        </td>
      </tr>
    `).join('');
  }

  // VIEW USER -----------------------------------
  async view(id) {
    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/user-data/${id}`);
      if (!resp) return;

      const data = await resp.json();
      if (!resp.ok) {
        auth.showNotification(data.error || 'Load failed', 'error');
        return;
      }

      // Instead of alert → you can convert to a modal later
      alert(JSON.stringify(data, null, 2));

    } catch (e) {
      console.error(e);
      auth.showNotification('User data error','error');
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
        auth.showNotification(data.error || 'Delete failed','error');
      }

    } catch (e) {
      console.error(e);
      auth.showNotification('Delete error','error');
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
