class CallAnalyticsManager {

  constructor() {
    this.activityChart = null;
    this.durationChart = null;
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
      this.renderCharts();

      // Also load the user summary table if needed
      // Note: The admin API already returns 'user_summary' in the main response!
      // So we might not need to call loadUserSummary separately if the API provides it.
      // Let's check if data.user_summary exists.
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

  renderCharts() {
    if (!this.data) return;

    // API returns 'daily_trend' and 'duration_trend' at top level
    const activityData = this.data.daily_trend || [];
    const durationData = this.data.duration_trend || [];

    // Activity Chart
    this.renderActivityChart(activityData);

    // Duration Chart
    this.renderDurationChart(durationData);
  }

  renderActivityChart(data) {
    const ctx = document.getElementById('analyticsActivityChart');
    if (!ctx) return;

    if (this.activityChart) {
      this.activityChart.destroy();
    }

    const labels = data.map(d => new Date(d.date).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' }));
    const counts = data.map(d => d.count);

    this.activityChart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: labels,
        datasets: [{
          label: 'Calls',
          data: counts,
          borderColor: '#3B82F6', // Blue-500
          backgroundColor: 'rgba(59, 130, 246, 0.1)',
          borderWidth: 3,
          tension: 0.4,
          fill: true,
          pointBackgroundColor: '#FFFFFF',
          pointBorderColor: '#3B82F6',
          pointBorderWidth: 2,
          pointRadius: 4,
          pointHoverRadius: 6
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            mode: 'index',
            intersect: false,
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            titleColor: '#F3F4F6',
            bodyColor: '#F3F4F6',
            borderColor: '#374151',
            borderWidth: 1,
            padding: 10,
            displayColors: false,
            callbacks: {
              label: function (context) {
                return context.parsed.y + ' Calls';
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: '#F3F4F6',
              drawBorder: false
            },
            ticks: {
              font: {
                family: "'Inter', sans-serif",
                size: 11
              },
              color: '#6B7280',
              padding: 10,
              precision: 0
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              font: {
                family: "'Inter', sans-serif",
                size: 11
              },
              color: '#6B7280'
            }
          }
        },
        interaction: {
          intersect: false,
          mode: 'index',
        },
      }
    });
  }

  renderDurationChart(data) {
    const ctx = document.getElementById('analyticsDurationChart');
    if (!ctx) return;

    if (this.durationChart) {
      this.durationChart.destroy();
    }

    const labels = data.map(d => new Date(d.date).toLocaleDateString(undefined, { weekday: 'short', day: 'numeric' }));
    const durations = data.map(d => Math.round(d.duration / 60)); // Convert to minutes

    this.durationChart = new Chart(ctx, {
      type: 'bar',
      data: {
        labels: labels,
        datasets: [{
          label: 'Duration (mins)',
          data: durations,
          backgroundColor: '#8B5CF6', // Purple-500
          borderRadius: 6,
          barThickness: 24,
          hoverBackgroundColor: '#7C3AED'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false
          },
          tooltip: {
            backgroundColor: 'rgba(17, 24, 39, 0.9)',
            titleColor: '#F3F4F6',
            bodyColor: '#F3F4F6',
            borderColor: '#374151',
            borderWidth: 1,
            padding: 10,
            displayColors: false,
            callbacks: {
              label: function (context) {
                return context.parsed.y + ' Mins';
              }
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            grid: {
              color: '#F3F4F6',
              drawBorder: false
            },
            ticks: {
              font: {
                family: "'Inter', sans-serif",
                size: 11
              },
              color: '#6B7280',
              padding: 10
            }
          },
          x: {
            grid: {
              display: false
            },
            ticks: {
              font: {
                family: "'Inter', sans-serif",
                size: 11
              },
              color: '#6B7280'
            }
          }
        }
      }
    });
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