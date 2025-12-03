/* admin/js/performance.js */

class PerformanceManager {

  async loadPerformance(sortType = "desc", dateFilter = "today") {
    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/performance?sort=${sortType}&filter=${dateFilter}`);
      if (!resp) return;

      const data = await resp.json();

      if (!resp.ok) {
        auth.showNotification(data.error || "Failed to load performance", "error");
        return;
      }

      const labels = data.labels || [];
      const values = data.values || [];
      const user_ids = data.user_ids || [];
      const incoming = data.incoming || [];
      const outgoing = data.outgoing || [];
      const total_calls = data.total_calls || [];

      // Render both chart + table
      this.renderChart(labels, values);
      this.renderTable(labels, values, user_ids, incoming, outgoing, total_calls);

    } catch (e) {
      console.error(e);
      auth.showNotification("Error loading performance", "error");
    }
  }

  renderChart(labels, values) {
    const ctx = document.getElementById("performanceBarCanvas").getContext("2d");

    if (this.chart) this.chart.destroy();

    // Custom plugin to draw values on top of bars
    const dataLabelPlugin = {
      id: 'dataLabelPlugin',
      afterDatasetsDraw(chart, args, options) {
        const { ctx } = chart;
        chart.data.datasets.forEach((dataset, i) => {
          const meta = chart.getDatasetMeta(i);
          meta.data.forEach((bar, index) => {
            const value = dataset.data[index];
            if (value > 0) {
              ctx.fillStyle = '#000000';
              ctx.font = 'bold 12px Inter';
              ctx.textAlign = 'center';
              ctx.fillText(`${value}%`, bar.x, bar.y - 5);
            }
          });
        });
      }
    };

    // Colorful palette
    const colors = [
      '#3B82F6', // Blue
      '#10B981', // Green
      '#EF4444', // Red
      '#8B5CF6', // Purple
      '#F59E0B', // Orange
      '#06B6D4', // Cyan
      '#EC4899', // Pink
      '#6366F1', // Indigo
    ];

    this.chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Performance Score",
            data: values,
            backgroundColor: labels.map((_, i) => colors[i % colors.length]),
            borderRadius: 4,
            barPercentage: 0.6,
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            display: false // Hide legend as bars are colorful
          },
          tooltip: {
            callbacks: {
              label: ctx => `Score: ${ctx.raw}%`
            }
          }
        },
        scales: {
          y: {
            beginAtZero: true,
            max: 100, // Assuming score is percentage
            grid: {
              display: false
            }
          },
          x: {
            grid: {
              display: false
            }
          }
        }
      },
      plugins: [dataLabelPlugin]
    });
  }

  renderTable(labels, values, ids, incoming, outgoing, total) {
    const body = document.getElementById("performanceTableBody");
    if (!body) return;

    body.innerHTML = labels.map((name, i) => `
      <tr class="border-t hover:bg-gray-50 transition-colors">
        <td class="px-6 py-4 text-gray-900 font-medium">#${i + 1}</td>
        <td class="px-6 py-4 text-gray-700 font-medium">${name}</td>
        <td class="px-6 py-4 text-center">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
                ${incoming[i] || 0}
            </span>
        </td>
        <td class="px-6 py-4 text-center">
            <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-purple-100 text-purple-800">
                ${outgoing[i] || 0}
            </span>
        </td>
        <td class="px-6 py-4 text-center font-bold text-gray-900">
            ${total[i] || 0}
        </td>
        <td class="px-6 py-4 text-center">
          <span class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${values[i] >= 80 ? 'bg-green-100 text-green-800' :
        values[i] >= 60 ? 'bg-blue-100 text-blue-800' :
          values[i] >= 40 ? 'bg-yellow-100 text-yellow-800' :
            'bg-red-100 text-red-800'
      }">
            ${values[i]}%
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
      const modal = document.getElementById('userDetailsModal');
      if (modal) modal.classList.remove('hidden');

      // Get current filter
      const dateFilter = document.getElementById("performanceDateFilter");
      const filterVal = dateFilter ? dateFilter.value : "today";

      const resp = await auth.makeAuthenticatedRequest(`/api/admin/call-analytics/${user_id}?period=${filterVal}`);
      if (!resp.ok) {
        auth.showNotification("Failed to load user details", "error");
        if (modal) modal.classList.add('hidden');
        return;
      }

      const data = await resp.json();

      document.getElementById('modal-user-name').textContent = data.user_name || "User Details";

      // Update modal title to reflect period
      const periodText = filterVal === 'today' ? "Today's" :
        filterVal === 'week' ? "This Week's" :
          filterVal === 'month' ? "This Month's" : "All Time";
      const subtitle = document.querySelector('#userDetailsModal p.text-sm.text-gray-500');
      if (subtitle) subtitle.textContent = `${periodText} Call Analytics`;

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

// EVENTS
document.addEventListener("DOMContentLoaded", () => {
  const sortSelect = document.getElementById("performanceSort");
  const dateFilter = document.getElementById("performanceDateFilter");

  function reload() {
    const s = sortSelect ? sortSelect.value : "desc";
    const d = dateFilter ? dateFilter.value : "today";
    performanceManager.loadPerformance(s, d);
  }

  if (sortSelect) sortSelect.addEventListener("change", reload);
  if (dateFilter) dateFilter.addEventListener("change", reload);

  // Initial load
  reload();
});
