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

  renderTrend() {
    const container = document.getElementById("call-trend-canvas");
    if (!container) return;

    // If we have a canvas, use Chart.js
    // If it's a div (from previous code), use HTML bars

    // Check if it's a canvas
    if (container.tagName === 'CANVAS') {
      if (this.chart) this.chart.destroy();

      const trendData = this.data.daily_trend || [];
      const labels = trendData.map(d => d.date.split('-').slice(1).join('/'));
      const values = trendData.map(d => d.count);

      this.chart = new Chart(container, {
        type: 'line',
        data: {
          labels: labels,
          datasets: [{
            label: 'Calls',
            data: values,
            borderColor: '#3B82F6',
            backgroundColor: 'rgba(59, 130, 246, 0.1)',
            fill: true,
            tension: 0.4
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false }
          },
          scales: {
            y: { beginAtZero: true, grid: { display: false } },
            x: { grid: { display: false } }
          }
        }
      });
      return;
    }

    // Fallback to HTML bars if not canvas (legacy support)
    const trendData = this.data.daily_trend || [];
    if (trendData.length === 0) {
      container.innerHTML = `<div class="text-gray-500 text-center p-8">No trend data available</div>`;
      return;
    }

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