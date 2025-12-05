/* admin/js/performance.js */

class PerformanceManager {

  constructor() {
    this.loadUsersForFilter();
  }

  // Standard interface for main.js
  load() {
    const sortSelect = document.getElementById("performanceSort");
    const userFilter = document.getElementById("performanceUserFilter");
    if (sortSelect) sortSelect.value = "desc";
    if (userFilter) userFilter.value = "all";

    this.loadPerformance("desc", "all", "all");
  }

  async loadUsersForFilter() {
    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/users?per_page=100');
      if (!resp || !resp.ok) return;
      const data = await resp.json();
      const users = data.users || [];

      const select = document.getElementById('performanceUserFilter');
      if (!select) return;

      // Keep "All Users" option
      select.innerHTML = '<option value="all">All Users</option>';

      users.forEach(u => {
        const opt = document.createElement('option');
        opt.value = u.id;
        opt.textContent = u.name;
        select.appendChild(opt);
      });
    } catch (e) {
      console.error("Failed to load users for filter", e);
    }
  }

  async loadPerformance(sortType = "desc", dateFilter = "all", userId = "all") {
    try {
      let url = `/api/admin/performance?sort=${sortType}&filter=${dateFilter}`;
      if (userId && userId !== 'all') {
        url += `&user_id=${userId}`;
      }

      const resp = await auth.makeAuthenticatedRequest(url);
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
      // Render both chart + table
      this.renderChart(labels, values);
      this.renderTable(labels, values, user_ids);

    } catch (e) {
      console.error(e);
      auth.showNotification("Error loading performance: " + (e.message || e), "error");
    }
  }

  renderChart(labels, values) {
    const canvas = document.getElementById("performanceBarCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

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

  renderTable(labels, values, ids) {
    const body = document.getElementById("performanceTableBody");
    if (!body) return;

    if (labels.length === 0) {
      body.innerHTML = `<tr><td colspan="4" class="p-6 text-center text-gray-500">No performance data found</td></tr>`;
      return;
    }

    body.innerHTML = labels.map((name, i) => `
      <tr class="border-t hover:bg-gray-50 transition-colors">
        <td class="px-6 py-4 text-gray-900 font-medium">#${i + 1}</td>
        <td class="px-6 py-4 text-gray-700 font-medium">${name}</td>
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
            onclick="performanceManager.viewUserCallHistory(${ids[i]}, '${name.replace(/'/g, "\\'")}')"
          >
            View Details
          </button>
        </td>
      </tr>
    `).join('');
  }

  async viewUserCallHistory(userId, userName, page = 1) {
    try {
      const modal = document.getElementById('userCallHistoryModal');
      const title = document.getElementById('modalUserTitle');
      const tbody = document.getElementById('modalCallHistoryBody');
      const paginationContainer = document.getElementById('modalCallHistoryPagination');

      if (!modal || !tbody) return;

      if (title) title.textContent = userName;
      tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">Loading...</td></tr>';

      modal.classList.remove('hidden');

      // Store current user for pagination
      this.currentModalUser = { userId, userName };

      // Fetch calls with pagination (defaults to last 7 days)
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/all-call-history?user_id=${userId}&page=${page}&per_page=20`);
      if (!resp || !resp.ok) {
        tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-red-500">Failed to load history</td></tr>';
        return;
      }

      const data = await resp.json();
      const calls = data.call_history || [];
      const meta = data.meta || {};

      if (calls.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">No call records found</td></tr>';
        if (paginationContainer) paginationContainer.innerHTML = '';
        return;
      }

      tbody.innerHTML = calls.map(call => `
        <tr>
          <td class="px-6 py-4 whitespace-nowrap">
            <span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full 
              ${call.call_type === 'incoming' ? 'bg-green-100 text-green-800' :
          call.call_type === 'outgoing' ? 'bg-blue-100 text-blue-800' :
            'bg-red-100 text-red-800'}">
              ${call.call_type}
            </span>
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${call.phone_number}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${this.formatDuration(call.duration)}
          </td>
          <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
            ${new Date(call.timestamp).toLocaleString()}
          </td>
        </tr>
      `).join('');

      // Render pagination
      this.renderModalPagination(meta, paginationContainer);

    } catch (e) {
      console.error("Error viewing user call history", e);
      auth.showNotification("Error opening call history", "error");
    }
  }

  renderModalPagination(meta, container) {
    if (!container || !meta || meta.pages <= 1) {
      if (container) container.innerHTML = '';
      return;
    }

    const currentPage = meta.page;
    const totalPages = meta.pages;

    let pagesHtml = '';

    // Show max 5 page numbers
    let startPage = Math.max(1, currentPage - 2);
    let endPage = Math.min(totalPages, currentPage + 2);

    for (let i = startPage; i <= endPage; i++) {
      pagesHtml += `
        <button 
          onclick="performanceManager.viewUserCallHistory(${this.currentModalUser.userId}, '${this.currentModalUser.userName}', ${i})"
          class="px-3 py-1 rounded ${i === currentPage ? 'bg-blue-600 text-white' : 'bg-white text-gray-700 hover:bg-gray-50'} border border-gray-300 text-sm font-medium">
          ${i}
        </button>
      `;
    }

    container.innerHTML = `
      <div class="flex items-center justify-between px-4 py-3 bg-gray-50 border-t border-gray-200">
        <div class="text-sm text-gray-700">
          Showing page <span class="font-medium">${currentPage}</span> of <span class="font-medium">${totalPages}</span>
          <span class="text-gray-500">(${meta.total} total records)</span>
        </div>
        <div class="flex gap-1">
          <button 
            onclick="performanceManager.viewUserCallHistory(${this.currentModalUser.userId}, '${this.currentModalUser.userName}', ${currentPage - 1})"
            ${!meta.has_prev ? 'disabled' : ''}
            class="px-3 py-1 rounded bg-white text-gray-700 hover:bg-gray-50 border border-gray-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed">
            Previous
          </button>
          ${pagesHtml}
          <button 
            onclick="performanceManager.viewUserCallHistory(${this.currentModalUser.userId}, '${this.currentModalUser.userName}', ${currentPage + 1})"
            ${!meta.has_next ? 'disabled' : ''}
            class="px-3 py-1 rounded bg-white text-gray-700 hover:bg-gray-50 border border-gray-300 text-sm font-medium disabled:opacity-50 disabled:cursor-not-allowed">
            Next
          </button>
        </div>
      </div>
    `;
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
  const userFilter = document.getElementById("performanceUserFilter");

  function reload() {
    const s = sortSelect ? sortSelect.value : "desc";
    const d = "all"; // Default to all time
    const u = userFilter ? userFilter.value : "all";
    performanceManager.loadPerformance(s, d, u);
  }

  if (sortSelect) sortSelect.addEventListener("change", reload);
  if (userFilter) userFilter.addEventListener("change", reload);

  // Initial load
  reload();
});
