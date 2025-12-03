/* admin/js/performance.js */

class PerformanceManager {

  async loadPerformance(sortType = "desc") {
    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/performance?sort=${sortType}`);
      if (!resp) return;

      const data = await resp.json();

      if (!resp.ok) {
        auth.showNotification(data.error || "Failed to load performance", "error");
        return;
      }

      const labels = data.labels || [];
      const values = data.values || [];
      const user_ids = data.user_ids || [];

      // Render both chart + table
      this.renderChart(labels, values);
      this.renderTable(labels, values, user_ids);

    } catch (e) {
      console.error(e);
      auth.showNotification("Error loading performance", "error");
    }
  }

  renderChart(labels, values) {
    const ctx = document.getElementById("performanceBarCanvas").getContext("2d");

    if (this.chart) this.chart.destroy();

    this.chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Performance Score",
            data: values,
            backgroundColor: values.map(v =>
              v >= 80 ? "#22c55e" :      // green (excellent)
                v >= 60 ? "#3b82f6" :      // blue (good)
                  v >= 40 ? "#f59e0b" :      // orange (average)
                    "#ef4444"                 // red (poor)
            ),
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: {
            callbacks: {
              label: ctx => `Score: ${ctx.raw}`
            }
          }
        }
      }
    });
  }

  renderTable(labels, values, ids) {
    const body = document.getElementById("performanceTableBody");
    if (!body) return;

    body.innerHTML = labels.map((name, i) => `
      <tr class="border-t hover:bg-gray-50 transition-colors">
        <td class="px-6 py-4 text-gray-900 font-medium">#${i + 1}</td>
        <td class="px-6 py-4 text-gray-700">${name}</td>
        <td class="px-6 py-4">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${values[i] >= 80 ? 'bg-green-100 text-green-800' :
        values[i] >= 60 ? 'bg-blue-100 text-blue-800' :
          values[i] >= 40 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800'
      }">
            ${values[i]}
          </span>
        </td>
        <td class="px-6 py-4">
          <button 
            class="text-blue-600 hover:text-blue-900 font-medium text-sm transition-colors"
            onclick="performanceManager.viewUserDetails(${ids[i]})"
          >
            View Details
          </button>
        </td>
      </tr>
    `).join('');
  }

  async viewUserDetails(user_id) {
    try {
      // Show loading state or just open modal with loader
      const modal = document.getElementById('userDetailsModal');
      if (modal) modal.classList.remove('hidden');

      const resp = await auth.makeAuthenticatedRequest(`/api/admin/call-analytics/${user_id}?period=today`);
      if (!resp.ok) {
        auth.showNotification("Failed to load user details", "error");
        if (modal) modal.classList.add('hidden');
        return;
      }

      const data = await resp.json();

      // Populate Modal
      document.getElementById('modal-user-name').textContent = data.user_name || "User Details";
      document.getElementById('modal-total').textContent = data.total_calls || 0;
      document.getElementById('modal-duration').textContent = this.formatDuration(data.total_duration_seconds || 0);
      document.getElementById('modal-incoming').textContent = data.incoming || 0;
      document.getElementById('modal-outgoing').textContent = data.outgoing || 0;
      document.getElementById('modal-missed').textContent = data.missed || 0;
      document.getElementById('modal-rejected').textContent = data.rejected || 0;

    } catch (e) {
      console.error(e);
      auth.showNotification("Error loading user details", "error");
      const modal = document.getElementById('userDetailsModal');
      if (modal) modal.classList.add('hidden');
    }
  }

  formatDuration(seconds) {
    if (!seconds || seconds === 0) return "0s";
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;
    if (h > 0) return `${h}h ${m}m ${s}s`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }
}

const performanceManager = new PerformanceManager();

// SORT CHANGE EVENT
document.addEventListener("DOMContentLoaded", () => {
  const sortSelect = document.getElementById("performanceSort");
  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      performanceManager.loadPerformance(sortSelect.value);
    });
  }

  // Initial load
  performanceManager.loadPerformance("desc");
});
