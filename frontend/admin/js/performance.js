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
      const statuses = data.statuses || [];
      const details = data.details || [];

      // Store stats for modal access
      this.userStats = {};
      user_ids.forEach((uid, i) => {
        this.userStats[uid] = {
          score: values[i],
          status: statuses[i],
          details: details[i]
        };
      });

      // Render both chart + table
      this.renderChart(labels, values);
      this.renderTable(labels, values, user_ids, statuses);

    } catch (e) {
      console.error(e);
      auth.showNotification("Error loading performance: " + (e.message || e), "error");
    }
  }

  renderChart(labels, values) {
    const canvas = document.getElementById("performanceBarCanvas");
    if (!canvas) return;
    const ctx = canvas.getContext("2d");

    // Robustly destroy existing chart
    if (this.chart) {
      this.chart.destroy();
      this.chart = null;
    }

    // Double check canvas for attached instance (Chart.js 3+)
    const existingChart = Chart.getChart(canvas);
    if (existingChart) {
      existingChart.destroy();
    }

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

    const colors = [
      '#3B82F6', '#10B981', '#EF4444', '#8B5CF6',
      '#F59E0B', '#06B6D4', '#EC4899', '#6366F1',
    ];

    this.chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Activity Ratio (%)",
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
          legend: { display: false },
          tooltip: {
            callbacks: {
              label: ctx => `Ratio: ${ctx.raw}%`
            }
          }
        },
        scales: {
          y: { beginAtZero: true, max: 100, grid: { display: false } },
          x: { grid: { display: false } }
        }
      },
      plugins: [dataLabelPlugin]
    });
  }

  renderTable(labels, values, ids, statuses) {
    const body = document.getElementById("performanceTableBody");
    if (!body) return;

    // Update Header if needed? 
    // Assuming table header has: Rank, Team Member, Score, Details
    // We should probably inject a Status column or combine it.
    // For now, I'll put Status in a pill next to Score or in a new column if I could edit HTML easily.
    // I will combine Score and Status in the same cell for layout stability.

    if (labels.length === 0) {
      body.innerHTML = `<tr><td colspan="5" class="p-6 text-center text-gray-500">No performance data found</td></tr>`;
      return;
    }

    body.innerHTML = labels.map((name, i) => {
      const score = values[i];
      const status = statuses[i] || 'Unknown';
      let statusColor = 'bg-gray-100 text-gray-800';
      if (status === 'Excellent') statusColor = 'bg-green-100 text-green-800';
      else if (status === 'Moderate') statusColor = 'bg-yellow-100 text-yellow-800';
      else if (status === 'Poor' || status === 'Inactive') statusColor = 'bg-red-100 text-red-800';

      return `
      <tr class="border-t hover:bg-gray-50 transition-colors">
        <td class="px-6 py-4 text-gray-900 font-medium">#${i + 1}</td>
        <td class="px-6 py-4 text-gray-700 font-medium">${name}</td>
        <td class="px-6 py-4">
             <div class="flex flex-col gap-1">
                <span class="text-sm font-bold text-gray-900">${score}% Efficiency</span>
                <span class="inline-flex w-fit items-center px-2 py-0.5 rounded text-xs font-medium ${statusColor}">
                    ${status}
                </span>
             </div>
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
    `}).join('');
  }

  async viewUserCallHistory(userId, userName, page = 1) {
    try {
      const modal = document.getElementById('userCallHistoryModal');
      const title = document.getElementById('modalUserTitle');
      const tbody = document.getElementById('modalCallHistoryBody');
      const paginationContainer = document.getElementById('modalCallHistoryPagination');

      if (!modal || !tbody) return;

      if (title) title.textContent = userName;

      // INJECT STATS SUMMARY
      // Check if stats container exists, if not create active/inactive info
      let statsContainer = document.getElementById('modalUserStats');
      if (!statsContainer) {
        // Create it after title
        const header = modal.querySelector('h3'); // Usually the title
        if (header && header.parentNode) {
          statsContainer = document.createElement('div');
          statsContainer.id = 'modalUserStats';
          statsContainer.className = "grid grid-cols-2 md:grid-cols-5 gap-4 mb-4 mt-2 p-3 bg-gray-50 rounded-lg text-center";
          header.parentNode.insertBefore(statsContainer, header.nextSibling);
        }
      }

      if (statsContainer && this.userStats && this.userStats[userId]) {
        const s = this.userStats[userId];
        const d = s.details || {};
        statsContainer.innerHTML = `
            <div>
                <p class="text-xs text-gray-500 uppercase">Check In</p>
                <p class="font-bold text-gray-900">${d.check_in || '-'}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Check Out</p>
                <p class="font-bold text-gray-900">${d.check_out || '-'}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Work Time</p>
                <p class="font-bold text-gray-900">${d.work_time || '0h'}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Active</p>
                <p class="font-bold text-green-600">${d.active_time || '0h'}</p>
            </div>
             <div>
                <p class="text-xs text-gray-500 uppercase">Inactive</p>
                <p class="font-bold text-red-600">${d.inactive_time || '0h'}</p>
            </div>
          `;
      } else if (statsContainer) {
        statsContainer.innerHTML = '';
      }


      tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-gray-500">Loading...</td></tr>';
      modal.classList.remove('hidden');

      // Reset filter on open
      this.currentModalFilter = 'all';
      this.currentModalUser = { userId, userName };
      this.setupModalControls(userId);
      await this.loadModalData(userId, userName, page);

    } catch (e) {
      console.error("Error viewing user call history", e);
      auth.showNotification("Error opening call history", "error");
    }
  }

  setupModalControls(userId) {
    const btnAll = document.getElementById('modal-history-filter-all');
    const btnToday = document.getElementById('modal-history-filter-today');
    const btnMonth = document.getElementById('modal-history-filter-month');
    const btnDownload = document.getElementById('modal-history-download');

    // Reset UI active state based on current filter
    [btnAll, btnToday, btnMonth].forEach(btn => {
      if (btn) {
        btn.classList.remove('bg-gray-100', 'active', 'ring-1', 'ring-transparent', 'focus:ring-blue-500');
        // Reset to default simplistic style then add active if matches
        // Simplified: just remove "active" logic class and re-add 
        btn.className = "px-3 py-1 text-xs font-medium rounded-md text-gray-700 hover:bg-gray-50 focus:outline-none";
      }
    });

    const activeClass = "bg-gray-100";

    // Default filter state if not set
    if (!this.currentModalFilter) this.currentModalFilter = 'all';

    if (this.currentModalFilter === 'all' && btnAll) btnAll.classList.add(activeClass);
    if (this.currentModalFilter === 'today' && btnToday) btnToday.classList.add(activeClass);
    if (this.currentModalFilter === 'month' && btnMonth) btnMonth.classList.add(activeClass);

    // Attach listeners (remove old ones by cloning or just assigning onclick handling carefully)
    // using onclick assignment for simplicity in this context to avoid stacking listeners on modal reopen
    if (btnAll) btnAll.onclick = () => this.changeModalFilter('all');
    if (btnToday) btnToday.onclick = () => this.changeModalFilter('today');
    if (btnMonth) btnMonth.onclick = () => this.changeModalFilter('month');

    if (btnDownload) btnDownload.onclick = () => this.downloadModalReport();
  }

  async changeModalFilter(filter) {
    this.currentModalFilter = filter;
    // Update UI immediately
    this.setupModalControls(this.currentModalUser.userId);
    // Reload data page 1
    await this.loadModalData(this.currentModalUser.userId, this.currentModalUser.userName, 1);
  }

  async loadModalData(userId, userName, page = 1) {
    const tbody = document.getElementById('modalCallHistoryBody');
    const paginationContainer = document.getElementById('modalCallHistoryPagination');

    let url = `/api/admin/all-call-history?user_id=${userId}&page=${page}&per_page=20`;

    // Append Filter
    if (this.currentModalFilter && this.currentModalFilter !== 'all') {
      url += `&filter=${this.currentModalFilter}`;
    }

    const resp = await auth.makeAuthenticatedRequest(url);
    if (!resp || !resp.ok) {
      tbody.innerHTML = '<tr><td colspan="4" class="px-6 py-4 text-center text-red-500">Failed to load history</td></tr>';
      return;
    }

    const data = await resp.json();
    const calls = data.call_history || [];
    const meta = data.meta || {};
    const stats = data.stats || null;

    // Update Stats Header if present
    if (stats) {
      const statsContainer = document.getElementById('modalUserStats');
      if (statsContainer) {
        statsContainer.innerHTML = `
            <div>
                <p class="text-xs text-gray-500 uppercase">Check In</p>
                <p class="font-bold text-gray-900">${stats.check_in || '-'}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Check Out</p>
                <p class="font-bold text-gray-900">${stats.check_out || '-'}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Work Time</p>
                <p class="font-bold text-gray-900">${stats.work_time || '0h'}</p>
            </div>
            <div>
                <p class="text-xs text-gray-500 uppercase">Active</p>
                <p class="font-bold text-green-600">${stats.active_time || '0h'}</p>
            </div>
             <div>
                <p class="text-xs text-gray-500 uppercase">Inactive</p>
                <p class="font-bold text-red-600">${stats.inactive_time || '0h'}</p>
            </div>
          `;
      }
    }

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
  }

  async downloadModalReport() {
    try {
      const userId = this.currentModalUser?.userId;
      if (!userId) return;

      const filter = this.currentModalFilter || 'all';
      // auth.showNotification("Generating Report...", "info");

      const token = auth.getToken();
      const response = await fetch(`/api/admin/download-user-history?user_id=${userId}&filter=${filter}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      });

      if (!response.ok) throw new Error("Failed to download");

      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.style.display = 'none';
      a.href = url;
      a.download = `CallHistory_Report_${filter}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      auth.showNotification("Report downloaded successfully", "success");

    } catch (e) {
      console.error(e);
      auth.showNotification("Failed to download report", "error");
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
