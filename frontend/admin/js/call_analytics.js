class CallAnalyticsManager {

  constructor() {
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

      this.updateKPICards();
      // Charts removed as per request
      // this.renderCharts();

      // Also load the user summary table if needed
      if (this.data.user_summary) {
        this.renderTable();
      } else {
        await this.loadUserSummary();
        this.renderTable();
      }

    } catch (e) {
      console.error(e);
      auth.showNotification("Analytics error", "error");
    }
  }

  updateKPICards() {
    if (!this.data) return;

    // API returns flat structure, not nested 'kpis'
    const kpis = this.data;

    // Helper to safely set text content
    const setText = (id, value) => {
      const el = document.getElementById(id);
      if (el) el.textContent = value;
    };

    setText("analytics-total-calls", (kpis.total_calls || 0).toLocaleString());
    setText("analytics-total-duration", this.formatDuration(kpis.total_duration || 0));
    setText("analytics-total-answered", (kpis.total_answered || 0).toLocaleString());

    // Calculate latest sync from user summary if available
    let latestSync = null;
    if (this.data.user_summary && Array.isArray(this.data.user_summary)) {
      const syncs = this.data.user_summary
        .map(u => u.last_sync ? new Date(u.last_sync) : null)
        .filter(d => d !== null);
      if (syncs.length > 0) {
        latestSync = new Date(Math.max.apply(null, syncs));
      }
    }

    if (latestSync) {
      setText("analytics-last-sync", latestSync.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }));
    } else {
      setText("analytics-last-sync", "Never");
    }

    setText("analytics-outbound", (kpis.outgoing || 0).toLocaleString());
    setText("analytics-inbound", (kpis.incoming || 0).toLocaleString());
    setText("analytics-avg-outbound", this.formatDuration(kpis.avg_outbound_duration || 0));
    setText("analytics-avg-inbound", this.formatDuration(kpis.avg_inbound_duration || 0));
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
                <th class="px-6 py-3 text-left text-xs font-bold text-black uppercase tracking-wider">User</th>
                <th class="px-6 py-3 text-center text-xs font-bold text-black uppercase tracking-wider">Incoming</th>
                <th class="px-6 py-3 text-center text-xs font-bold text-black uppercase tracking-wider">Outgoing</th>
                <th class="px-6 py-3 text-center text-xs font-bold text-black uppercase tracking-wider">Missed</th>
                <th class="px-6 py-3 text-center text-xs font-bold text-black uppercase tracking-wider">Rejected</th>
                <th class="px-6 py-3 text-left text-xs font-bold text-black uppercase tracking-wider">Total Duration</th>
                <th class="px-6 py-3 text-left text-xs font-bold text-black uppercase tracking-wider">Last Sync</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
              ${rows.length
        ? rows.map(row => `
                    <tr class="hover:bg-gray-50 transition-colors">
                      <td class="p-3 text-sm font-medium text-gray-900">${row.name || row.user_name || "-"}</td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-green-100 text-green-800 font-medium">
                          ${row.incoming || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-purple-100 text-purple-800 font-medium">
                          ${row.outgoing || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-red-100 text-red-800 font-medium">
                          ${row.missed || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-center">
                        <span class="inline-block px-2 py-1 rounded bg-orange-100 text-orange-800 font-medium">
                          ${row.rejected || 0}
                        </span>
                      </td>
                      <td class="p-3 text-sm text-gray-600">
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
    // Auto-refresh every 60 seconds
    setInterval(() => this.loadAnalytics(), 60000);
  }
}

// Initialize the manager
const callAnalyticsManager = new CallAnalyticsManager();

// Auto-start when page loads
document.addEventListener('DOMContentLoaded', function () {
  callAnalyticsManager.init();
});

// Make it globally available
window.callAnalyticsManager = callAnalyticsManager;