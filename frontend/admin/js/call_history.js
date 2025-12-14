/* admin/js/call_history.js */

class CallHistoryManager {

  constructor() {
    this.loadUsersForFilter();
    this.initEventListeners();
  }

  initEventListeners() {
    const userFilter = document.getElementById('callUserFilter');
    const dateFilter = document.getElementById('callDateFilter'); // Not currently in HTML but good to keep if added later
    const searchInput = document.getElementById('callSearchInput');
    const typeFilter = document.getElementById('callTypeFilter');
    const btnExport = document.getElementById('btnExportCalls');

    const refresh = () => {
      this.loadCalls(
        userFilter?.value === 'all' ? null : userFilter?.value,
        1,
        50,
        "",
        dateFilter?.value,
        searchInput?.value,
        typeFilter?.value
      );
    };

    if (userFilter) userFilter.addEventListener('change', refresh);
    if (dateFilter) dateFilter.addEventListener('change', refresh);
    const monthFilter = document.getElementById('callMonthFilter');
    if (monthFilter) monthFilter.addEventListener('change', refresh);

    if (typeFilter) typeFilter.addEventListener('change', refresh);
    if (searchInput && window.debounce) {
      searchInput.addEventListener('input', window.debounce(refresh, 500));
    } else if (searchInput) {
      searchInput.addEventListener('change', refresh);
    }

    if (btnExport) {
      btnExport.addEventListener('click', () => {
        this.exportCalls();
      });
    }
  }

  // Standard interface for main.js
  load() {
    const userFilter = document.getElementById('callUserFilter');
    const monthFilter = document.getElementById('callMonthFilter');
    const typeFilter = document.getElementById('callTypeFilter');
    const searchInput = document.getElementById('callSearchInput');

    if (userFilter) userFilter.value = 'all';
    if (monthFilter) monthFilter.value = '';
    if (typeFilter) typeFilter.value = 'all';
    if (searchInput) searchInput.value = '';

    this.loadCalls();
  }

  async loadUsersForFilter() {
    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/users?per_page=100');
      if (!resp || !resp.ok) return;
      const data = await resp.json();
      const users = data.users || [];

      const select = document.getElementById('callUserFilter');
      if (!select) return;

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

  async loadCalls(
    user_id = null,
    page = 1,
    per_page = 50,
    filter = "",
    date = "",
    search = "",
    call_type = ""
  ) {
    try {

      // ================================
      // Build base URL (admin or user)
      // ================================
      const container = document.getElementById("call-history-container");
      if (container) {
        container.innerHTML = '<div class="p-4 text-center text-gray-500">Loading...</div>';
      }

      // ================================
      // Build base URL (admin or user)
      // ================================
      let url = `/api/admin/all-call-history?page=${page}&per_page=${per_page}`;

      // ================================
      // Add filters dynamically
      // ================================
      if (user_id && user_id !== 'all') url += `&user_id=${user_id}`;
      if (filter) url += `&filter=${filter}`;          // today / week / month
      if (date) url += `&date=${date}`;                // custom date (YYYY-MM-DD)
      if (search) url += `&search=${encodeURIComponent(search)}`; // phone search
      if (call_type && call_type !== 'all') url += `&call_type=${call_type}`; // incoming/outgoing/missed

      // Month filter (UI driven)
      const monthFilter = document.getElementById('callMonthFilter');
      if (monthFilter && monthFilter.value) {
        url += `&month=${monthFilter.value}`;
      }

      // Make authenticated request
      const resp = await auth.makeAuthenticatedRequest(url);
      if (!resp) return;

      const data = await resp.json();

      if (!resp.ok) {
        auth.showNotification(data.error || 'Failed to load call history', 'error');
        return;
      }

      // Main list
      const list = data.call_history || [];

      if (!container) return;

      // ================================
      // Render Table
      // ================================
      if (list.length === 0) {
        container.innerHTML = `
          <div class="flex flex-col items-center justify-center py-12 bg-white rounded shadow">
            <div class="text-gray-400 mb-3">
              <i class="fas fa-search text-4xl"></i>
            </div>
            <h3 class="text-lg font-medium text-gray-900">No records found</h3>
            <p class="text-gray-500 text-sm mt-1">Try adjusting your search or filters</p>
          </div>
        `;
        // Clear pagination
        const pagination = document.getElementById("call-history-pagination");
        if (pagination) pagination.innerHTML = "";
        return;
      }

      container.innerHTML = `
        <div class="overflow-x-auto bg-white rounded shadow">
          <table class="w-full">
              <thead class="bg-gray-200">
            <tr>
              <th class="p-3 text-left whitespace-nowrap">User</th>
              <th class="p-3 text-left whitespace-nowrap">Number</th>
              <th class="p-3 text-left whitespace-nowrap">Contact Name</th>
              <th class="p-3 text-left whitespace-nowrap">Type</th>
              <th class="p-3 text-left whitespace-nowrap">Duration</th>
              <th class="p-3 text-left whitespace-nowrap">Recording</th>
              <th class="p-3 text-left whitespace-nowrap">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            ${list
          .map(
            (r) => {
              // Color badges for types
              let typeBadge = "";
              const cType = (r.call_type || "").toLowerCase();
              if (cType === "incoming") {
                typeBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-700">Incoming</span>`;
              } else if (cType === "outgoing") {
                typeBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-blue-100 text-blue-700">Outgoing</span>`;
              } else if (cType === "missed") {
                typeBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-red-100 text-red-700">Missed</span>`;
              } else {
                typeBadge = `<span class="px-2 py-0.5 rounded text-xs font-semibold bg-gray-100 text-gray-700">${r.call_type}</span>`;
              }

              // Recording Player
              let recordingPlayer = '<span class="text-gray-400 text-xs">-</span>';
              if (r.recording_path) {
                // Assuming static files are served at /static/
                recordingPlayer = `
                    <audio controls controlsList="nodownload" class="h-8 w-32">
                        <source src="/${r.recording_path}" type="audio/mpeg">
                        Your browser does not support the audio element.
                    </audio>
                  `;
              }

              return `
                <tr class="border-t hover:bg-gray-50">
                  <td class="p-3 whitespace-nowrap text-sm font-medium text-gray-900" data-label="User">${r.user_name || r.user_id || '-'}</td>
                  <td class="p-3 whitespace-nowrap text-sm text-gray-600" data-label="Number">${r.phone_number || '-'}</td>
                  <td class="p-3 whitespace-nowrap text-sm text-gray-600" data-label="Contact">${r.contact_name || '-'}</td>
                  <td class="p-3 whitespace-nowrap" data-label="Type">${typeBadge}</td>
                  <td class="p-3 whitespace-nowrap text-sm text-gray-600" data-label="Duration">${r.duration ? r.duration + "s" : "-"}</td>
                  <td class="p-3 min-w-[150px]" data-label="Recording">${recordingPlayer}</td>
                  <td class="p-3 text-sm text-gray-600 whitespace-nowrap" data-label="Time">
                    ${window.formatDateTime(r.timestamp)}
                  </td>
                </tr>
              `;
            }
          )
          .join("")
        }
          </tbody>
        </table>
      </div>
      `;

      // ================================
      // Render Pagination Buttons
      // ================================
      if (data.meta) {
        this.renderPagination(data.meta, user_id, filter, date, search, call_type);
      }
    }

    catch (e) {
      console.error(e);
      auth.showNotification("Failed to load call history", "error");
    }
  }

  // ======================================================
  // PAGINATION RENDERING
  // ======================================================
  renderPagination(meta, user_id, filter, date, search, call_type) {
    const pagination = document.getElementById("call-history-pagination");
    if (!pagination) return;

    pagination.innerHTML = `
      <div class="flex justify-between mt-4 p-4">
        <button 
          class="px-4 py-2 bg-gray-300 rounded ${meta.has_prev ? "hover:bg-gray-400" : "opacity-50 cursor-not-allowed"}"
          ${meta.has_prev ? `onclick="callHistoryManager.loadCalls(${user_id ? `'${user_id}'` : 'null'}, ${meta.page - 1}, ${meta.per_page}, '${filter}', '${date}', '${search}', '${call_type}')"` : ""}
        >
          Previous
        </button>

        <span class="px-4 py-2">Page ${meta.page} of ${meta.pages}</span>

        <button 
          class="px-4 py-2 bg-gray-300 rounded ${meta.has_next ? "hover:bg-gray-400" : "opacity-50 cursor-not-allowed"}"
          ${meta.has_next ? `onclick="callHistoryManager.loadCalls(${user_id ? `'${user_id}'` : 'null'}, ${meta.page + 1}, ${meta.per_page}, '${filter}', '${date}', '${search}', '${call_type}')"` : ""}
        >
          Next
        </button>
      </div>
    `;
  }

  async exportCalls() {
    const userFilter = document.getElementById('callUserFilter');
    const searchInput = document.getElementById('callSearchInput');
    const typeFilter = document.getElementById('callTypeFilter');
    const monthFilter = document.getElementById('callMonthFilter');

    const user_id = userFilter?.value === 'all' ? null : userFilter?.value;
    const search = searchInput?.value || "";
    const call_type = typeFilter?.value === 'all' ? "" : typeFilter?.value;
    const month = monthFilter?.value || "";

    try {
      let url = `/api/admin/all-call-history?per_page=10000`; // Fetch large number for export
      if (user_id) url += `&user_id=${user_id}`;
      if (search) url += `&search=${encodeURIComponent(search)}`;
      if (call_type) url += `&call_type=${call_type}`;
      if (month) url += `&month=${month}`;

      const resp = await auth.makeAuthenticatedRequest(url);
      if (!resp || !resp.ok) {
        auth.showNotification("Failed to fetch data for export", "error");
        return;
      }

      const data = await resp.json();
      const items = data.call_history || [];

      if (items.length === 0) {
        auth.showNotification("No records to export", "info");
        return;
      }

      // Convert to CSV
      const headers = ["User", "Number", "Contact Name", "Type", "Duration (s)", "Timestamp"];
      const rows = items.map(r => [
        r.user_name || r.user_id || '-',
        r.phone_number ? `="${r.phone_number}"` : '-',
        (r.contact_name || '-').replace(/,/g, " "),
        r.call_type || '-',
        r.duration || 0,
        window.formatDateTime(r.timestamp)
      ]);

      let csvContent = "data:text/csv;charset=utf-8,"
        + headers.join(",") + "\n"
        + rows.map(e => e.join(",")).join("\n");

      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `call_history_export_${new Date().toISOString().split('T')[0]}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

    } catch (e) {
      console.error("Export failed", e);
      auth.showNotification("Export failed", "error");
    }
  }
}

const callHistoryManager = new CallHistoryManager();
