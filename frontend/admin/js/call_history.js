/* admin/js/call_history.js */

class CallHistoryManager {

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
      let url = user_id
        ? `/api/admin/user-call-history/${user_id}?page=${page}&per_page=${per_page}`
        : `/api/admin/all-call-history?page=${page}&per_page=${per_page}`;

      // ================================
      // Add filters dynamically
      // ================================
      if (filter) url += `&filter=${filter}`;          // today / week / month
      if (date) url += `&date=${date}`;                // custom date (YYYY-MM-DD)
      if (search) url += `&search=${encodeURIComponent(search)}`; // phone search
      if (call_type) url += `&call_type=${call_type}`; // incoming/outgoing/missed

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

      const container = document.getElementById("call-history-container");
      if (!container) return;

      // ================================
      // Render Table
      // ================================
      container.innerHTML = `
        <table class="w-full bg-white rounded shadow overflow-hidden">
          <thead class="bg-gray-200">
            <tr>
              <th class="p-3">User</th>
              <th class="p-3">Number</th>
              <th class="p-3">Contact Name</th>
              <th class="p-3">Type</th>
              <th class="p-3">Duration</th>
              <th class="p-3">Timestamp</th>
            </tr>
          </thead>
          <tbody>
            ${
              list.length
                ? list
                    .map(
                      (r) => `
                  <tr class="border-t hover:bg-gray-50">
                    <td class="p-3">${r.user_name || r.user_id || '-'}</td>
                    <td class="p-3">${r.phone_number || '-'}</td>
                    <td class="p-3">${r.contact_name || '-'}</td>
                    <td class="p-3">${r.call_type || '-'}</td>
                    <td class="p-3">${r.duration ? r.duration + "s" : "-"}</td>
                    <td class="p-3 text-sm text-gray-600">
                      ${r.timestamp ? new Date(r.timestamp).toLocaleString() : '-'}
                    </td>
                  </tr>
                `
                    )
                    .join("")
                : `<tr><td colspan="6" class="p-4 text-center text-gray-500">No call records found</td></tr>`
            }
          </tbody>
        </table>
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
      <div class="flex justify-between mt-4">
        <button 
          class="px-4 py-2 bg-gray-300 rounded ${meta.has_prev ? "hover:bg-gray-400" : "opacity-50 cursor-not-allowed"}"
          ${meta.has_prev ? `onclick="callHistoryManager.loadCalls(${user_id}, ${meta.page - 1}, ${meta.per_page}, '${filter}', '${date}', '${search}', '${call_type}')"` : ""}
        >
          Previous
        </button>

        <span class="px-4 py-2">Page ${meta.page} of ${meta.pages}</span>

        <button 
          class="px-4 py-2 bg-gray-300 rounded ${meta.has_next ? "hover:bg-gray-400" : "opacity-50 cursor-not-allowed"}"
          ${meta.has_next ? `onclick="callHistoryManager.loadCalls(${user_id}, ${meta.page + 1}, ${meta.per_page}, '${filter}', '${date}', '${search}', '${call_type}')"` : ""}
        >
          Next
        </button>
      </div>
    `;
  }
}

const callHistoryManager = new CallHistoryManager();
