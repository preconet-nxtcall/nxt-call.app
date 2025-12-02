class CallAnalyticsManager {

  constructor() {
    this.chart = null;
    this.data = null;
  }

  async loadAnalytics() {
    try {
      // ✅ CORRECTED: Fixed URL (removed "/summary")
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
      this.renderTrend();
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

    // ✅ CORRECTED: Fixed data access (removed .call_types)
    const cards = [
      { 
        label: "Total Calls", 
        value: d.total_calls || 0, 
        icon: "phone", 
        color: "blue" 
      },
      { 
        label: "Incoming", 
        value: d.incoming || 0,  // Was: d.call_types?.incoming
        icon: "phone-volume", 
        color: "green" 
      },
      { 
        label: "Outgoing", 
        value: d.outgoing || 0,  // Was: d.call_types?.outgoing
        icon: "phone", 
        color: "purple" 
      },
      { 
        label: "Missed", 
        value: d.missed || 0,  // Was: d.call_types?.missed
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
      blue: "bg-blue-100 text-blue-600",
      green: "bg-green-100 text-green-600",
      purple: "bg-purple-100 text-purple-600",
      red: "bg-red-100 text-red-600",
      orange: "bg-orange-100 text-orange-600"
    };

    container.innerHTML = cards
      .map(card => `
        <div class="bg-white p-4 rounded-lg shadow card-hover">
          <div class="flex justify-between items-center">
            <div>
              <div class="text-xs text-gray-500">${card.label}</div>
              <div class="text-xl font-bold">${card.value.toLocaleString()}</div>
            </div>
            <div class="w-12 h-12 rounded-full flex items-center justify-center ${colorMap[card.color]}">
              <i class="fas fa-${card.icon} text-lg"></i>
            </div>
          </div>
        </div>
      `)
      .join("");
  }

  renderTrend() {
    const container = document.getElementById("call-trend-chart");
    if (!container || !this.data || !this.data.daily_trend) return;
    
    const trendData = this.data.daily_trend || [];
    
    if (trendData.length === 0) {
      container.innerHTML = `<div class="text-gray-500 text-center p-8">No trend data available</div>`;
      return;
    }
    
    // If you want to implement a chart, you can use Chart.js here
    // For now, let's create a simple HTML trend display
    const maxCount = Math.max(...trendData.map(d => d.count));
    
    container.innerHTML = `
      <div class="bg-white p-4 rounded-lg shadow">
        <h3 class="text-lg font-semibold mb-4">Last 7 Days Trend</h3>
        <div class="flex items-end h-40 space-x-2">
          ${trendData.map(day => `
            <div class="flex-1 flex flex-col items-center">
              <div 
                class="w-full bg-blue-200 rounded-t transition-all hover:bg-blue-300"
                style="height: ${maxCount > 0 ? (day.count / maxCount * 100) : 0}%"
                title="${day.date}: ${day.count} calls"
              ></div>
              <div class="text-xs mt-2 text-gray-600">${day.date.split('-')[2]}/${day.date.split('-')[1]}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
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
              ${
                rows.length
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
document.addEventListener('DOMContentLoaded', function() {
  callAnalyticsManager.init();
  
  // Optional: Add refresh button if you have one
  const refreshBtn = document.getElementById('refresh-analytics-btn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', () => callAnalyticsManager.refresh());
  }
});

// Make it globally available if needed
window.callAnalyticsManager = callAnalyticsManager;