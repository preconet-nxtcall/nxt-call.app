class CallAnalyticsManager {

  constructor() {
    this.chart = null;
    this.data = null;
  }

  async loadAnalytics() {
    try {
      const resp = await auth.makeAuthenticatedRequest(
        "/api/admin/call-analytics"
      );

      if (!resp.ok) {
        auth.showNotification("Failed to load analytics", "error");
        return;
      }

      const data = await resp.json();
      this.data = data;

      // Load user details list
      await this.loadUserSummary();

      this.renderCards();

      this.renderTable();

    } catch (e) {
      console.error(e);
      auth.showNotification("Analytics error", "error");
    }
  }

  async loadUserSummary() {
    try {
      const resp = await auth.makeAuthenticatedRequest(
        "/api/admin/call-analytics/users"
      );

      if (!resp.ok) {
        console.warn("Could not load user summary, using existing data");
        return;
      }

      const data = await resp.json();
      // Update user summary from the separate endpoint
      if (data.users && Array.isArray(data.users)) {
        this.data.user_summary = data.users;
      }
    } catch (e) {
      console.warn("Failed to load user summary:", e);
      // Continue with existing data if available
    }
  }

  renderCards() {
    const container = document.getElementById("call-analytics-cards");
    if (!container) return;

    const d = this.data || {};

    const cards = [
      {
        label: "Total Calls",
        value: d.total_calls || 0,
        icon: "phone",
        color: "blue"
      },
      {
        label: "Incoming",
        value: d.incoming || 0,
        icon: "phone-volume",
        color: "green"
      },
      {
        label: "Outgoing",
        value: d.outgoing || 0,
        icon: "phone",
        color: "purple"
      },
      {
        label: "Missed",
        value: d.missed || 0,
        icon: "phone-slash",
        color: "red"
      },
      {
        label: "Rejected",
        value: d.rejected || 0,
        icon: "phone-xmark",
        color: "orange"
      }
    ];

    const colorMap = {
      blue: "bg-blue-50 text-blue-600",
      green: "bg-green-50 text-green-600",
      purple: "bg-purple-50 text-purple-600",
      red: "bg-red-50 text-red-600",
      orange: "bg-orange-50 text-orange-600"
    };

    container.innerHTML = cards
      .map(card => `
        <div class="bg-white p-6 rounded-xl shadow-sm border border-gray-100 hover-card flex items-center gap-4 transition-all duration-200">
          <div class="w-14 h-14 rounded-full flex items-center justify-center ${colorMap[card.color]} shadow-sm">
            <i class="fas fa-${card.icon} text-xl"></i>
          </div>
          <div>
            <div class="text-3xl font-bold text-gray-900 tracking-tight">${card.value.toLocaleString()}</div>
            <div class="text-sm font-medium text-gray-500">${card.label}</div>
          </div>
        </div>
      `)
      .join("");
  }

  renderTable() {
    const container = document.getElementById("call-analytics-table-container");
    if (!container) return;

    const rows = this.data?.user_summary || [];

    container.innerHTML = `
      <div class="bg-white rounded-lg shadow overflow-hidden">
        <div class="overflow-x-auto">
          <table class="w-full">
            <thead class="bg-gray-50">
              <tr>
                <th class="p-3 text-left text-sm font-medium text-gray-700">User</th>
                <th class="p-3 text-left text-sm font-medium text-gray-700">Incoming</th>
                <th class="p-3 text-left text-sm font-medium text-gray-700">Outgoing</th>
                <th class="p-3 text-left text-sm font-medium text-gray-700">Missed</th>
                <th class="p-3 text-left text-sm font-medium text-gray-700">Rejected</th>
                <th class="p-3 text-left text-sm font-medium text-gray-700">Total Duration</th>
                <th class="p-3 text-left text-sm font-medium text-gray-700">Last Sync</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              ${rows.length
        ? rows.map(row => `
                    <tr class="hover:bg-gray-50 transition-colors">
                      <td class="p-3 text-sm">${row.name || row.user_name || "-"}</td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-green-100 text-green-800">
                          ${row.incoming || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-purple-100 text-purple-800">
                          ${row.outgoing || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-red-100 text-red-800">
                          ${row.missed || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-orange-100 text-orange-800">
                          ${row.rejected || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm">
                        ${this.formatDuration(row.total_duration_seconds || 0)}
                      </td>
                      <td class="p-3 text-sm text-gray-500">
                        ${row.last_sync ? new Date(row.last_sync).toLocaleDateString() : 'Never'}
                      </td>
                    </tr>
                  `).join("")
        : `
                    <tr>
                      <td colspan="7" class="p-6 text-center text-gray-500">
                        <i class="fas fa-users-slash text-3xl mb-2 text-gray-300"></i>
                        <div>No user data available</div>
                      </td>
                    </tr>
                  `
      }
            </tbody>
          </table>
        </div>
      </div>
    `;
  }

  formatDuration(seconds) {
    if (!seconds || seconds === 0) return "0s";

    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = seconds % 60;

    const parts = [];
    if (hours > 0) parts.push(`${hours}h`);
    if (minutes > 0) parts.push(`${minutes}m`);
    if (secs > 0 || parts.length === 0) parts.push(`${secs}s`);

    return parts.join(" ");
  }

  // Optional: Add refresh functionality
  async refresh() {
    await this.loadAnalytics();
    auth.showNotification("Analytics refreshed", "success");
  }

  // Optional: Initialize with auto-refresh
  init() {
    this.loadAnalytics();
    // Auto-refresh every 30 seconds if needed
    // setInterval(() => this.loadAnalytics(), 30000);
  }
}

// Initialize the manager
const callAnalyticsManager = new CallAnalyticsManager();

// Auto-start when page loads
document.addEventListener('DOMContentLoaded', function () {
  callAnalyticsManager.init();

  // Optional: Add refresh button if you have one
  const refreshBtn = document.getElementById('refresh-analytics-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => callAnalyticsManager.refresh());
  }
});

// Make it globally available if needed
window.callAnalyticsManager = callAnalyticsManager;