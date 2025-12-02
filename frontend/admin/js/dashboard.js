/* admin/js/dashboard.js */
class DashboardManager {
  constructor() {
    this.stats = {};
    this.performanceChart = null; // IMPORTANT: prevent "canvas already in use"
  }

  async loadStats() {
    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/dashboard-stats');
      if (!resp) return;

      const data = await resp.json();
      if (!resp.ok) {
        auth.showNotification(data.error || 'Failed to load dashboard stats', 'error');
        return;
      }

      this.stats = data.stats || {};

      this.renderStats();
      this.renderRecentSync();
      this.renderUserLogs();
      this.renderPerformanceChart();

    } catch (e) {
      console.error(e);
      auth.showNotification('Failed to load dashboard stats', 'error');
    }
  }

  renderStats() {
    const container = document.getElementById('stats-cards');
    if (!container) return;

    const s = this.stats;

    const cards = [
      { title: "Total Users", value: s.total_users ?? 0, icon: "users", color: "blue" },
      { title: "Active Users", value: s.active_users ?? 0, icon: "user-check", color: "green" },
      { title: "Users With Sync", value: s.users_with_sync ?? 0, icon: "sync", color: "purple" },
      { title: "Remaining Slots", value: s.remaining_slots ?? 0, icon: "user-plus", color: "orange" }
    ];

    container.innerHTML = cards.map(c => `
      <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover-card flex items-center gap-4 transition-all duration-200">
        <div class="w-14 h-14 rounded-full flex items-center justify-center bg-${c.color}-50 text-${c.color}-600 shadow-sm">
          <i class="fas fa-${c.icon} text-xl"></i>
        </div>
        <div>
          <p class="text-3xl font-bold text-gray-900 tracking-tight">${c.value}</p>
          <p class="text-sm font-medium text-gray-500">${c.title}</p>
        </div>
      </div>
    `).join('');
  }

  /* ------------------------------
     RECENT SYNC
  ------------------------------ */
  async renderRecentSync() {
    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/recent-sync');
      if (!resp) return;

      const data = await resp.json();
      if (!resp.ok) {
        auth.showNotification(data.error || 'Failed to load recent sync', 'error');
        return;
      }

      const list = document.getElementById('recent-sync-list');
      if (!list) return;

      const items = data.recent_sync || [];

      list.innerHTML = items.map(r => `
        <div class="border p-3 rounded bg-white">
          <div class="flex justify-between items-start">
            <div>
              <div class="font-medium">${r.name}</div>
              <div class="text-xs text-gray-500">
                Last Sync: ${r.last_sync ? new Date(r.last_sync).toLocaleString() : 'Never'}
              </div>
            </div>
            <div class="text-sm ${r.is_active ? 'text-green-600' : 'text-red-600'}">
              ${r.is_active ? 'Active' : 'Inactive'}
            </div>
          </div>
        </div>
      `).join('');

    } catch (e) {
      console.error(e);
      auth.showNotification("Failed to load recent sync", "error");
    }
  }

  /* ------------------------------
     USER LOGS
  ------------------------------ */
  async renderUserLogs() {
    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/user-logs');
      if (!resp) return;

      const data = await resp.json();
      if (!resp.ok) return;

      const container = document.getElementById('user-logs-container');
      if (!container) return;

      const logs = data.logs || [];

      container.innerHTML = logs.map(l => `
        <div class="p-4 rounded border bg-white">
          <div class="flex justify-between items-center">
            <div>
              <div class="font-medium">${l.user_name || 'Unknown'}</div>
              <div class="text-xs text-gray-500">${l.action}</div>
            </div>
            <div class="text-xs text-gray-500">
              ${new Date(l.timestamp).toLocaleString()}
            </div>
          </div>
        </div>
      `).join('');

    } catch (e) {
      console.error(e);
    }
  }

  /* ------------------------------
     PERFORMANCE CHART
  ------------------------------ */
  renderPerformanceChart() {
    const canvas = document.getElementById('performanceChart');
    if (!canvas || typeof Chart === 'undefined') return;

    // Destroy previous chart to avoid canvas reuse error
    if (this.performanceChart) {
      this.performanceChart.destroy();
    }

    this.performanceChart = new Chart(canvas, {
      type: 'line',
      data: {
        labels: ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        datasets: [{
          label: 'Avg Performance',
          data: this.stats.performance_trend || [0, 0, 0, 0, 0, 0, 0],
          borderColor: '#2563EB',
          tension: 0.3
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false
      }
    });
  }
}

const dashboard = new DashboardManager();
