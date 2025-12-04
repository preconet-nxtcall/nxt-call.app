/* admin/js/attendance.js */
class AttendanceManager {

  constructor() {
    this.loadUsersForFilter();
    this.initEventListeners();
  }

  initEventListeners() {
    const userFilter = document.getElementById("attendanceUserFilter");
    const dateFilter = document.getElementById("attendanceDateFilter");
    const btnExport = document.getElementById("btnExportAttendance");

    const refresh = () => {
      this.loadAttendance(
        dateFilter?.value,
        userFilter?.value === 'all' ? null : userFilter?.value
      );
    };

    if (userFilter) userFilter.addEventListener("change", refresh);
    if (dateFilter) dateFilter.addEventListener("change", refresh);

    if (btnExport) {
      btnExport.addEventListener("click", () => {
        this.exportAttendance();
      });
    }
  }

  // Standard interface for main.js
  load() {
    const userFilter = document.getElementById("attendanceUserFilter");
    const dateFilter = document.getElementById("attendanceDateFilter");

    if (userFilter) userFilter.value = "all";
    if (dateFilter) dateFilter.value = "";

    this.loadAttendance();
  }

  async loadUsersForFilter() {
    try {
      const resp = await auth.makeAuthenticatedRequest('/api/admin/users?per_page=100');
      if (!resp || !resp.ok) return;
      const data = await resp.json();
      const users = data.users || [];

      const select = document.getElementById('attendanceUserFilter');
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

  async loadAttendance(date = null, user_id = null, page = 1, per_page = 25) {
    console.log("loadAttendance called with date:", date, "user:", user_id);
    try {
      let url = `/api/admin/attendance?page=${page}&per_page=${per_page}`;
      if (date) {
        url += `&date=${date}`;
      }
      if (user_id && user_id !== 'all') {
        url += `&user_id=${user_id}`;
      }

      const resp = await auth.makeAuthenticatedRequest(url);

      if (!resp) return;
      const data = await resp.json();

      if (!resp.ok) {
        auth.showNotification(data.error || "Failed to load attendance", "error");
        return;
      }

      const items = data.attendance || [];
      const tableBody = document.getElementById("attendance-table-body");
      if (!tableBody) return;

      if (!items.length) {
        tableBody.innerHTML = `
          <tr>
            <td colspan="6" class="p-4 text-center text-gray-500">
              No attendance records found
            </td>
          </tr>
        `;
        return;
      }

      tableBody.innerHTML = items.map(a => `
        <tr class="table-row-hover">

          <!-- USER -->
          <td class="p-3 font-medium text-gray-900">
            ${a.user_name || "Unknown"}
            <div class="text-xs text-gray-500">${a.external_id || ""}</div>
          </td>

          <!-- CHECK IN -->
          <td class="p-3 text-gray-700">
            ${window.formatDateTime(a.check_in)}
            <div class="text-xs text-gray-500">${a.address || ""}</div>
          </td>

          <!-- CHECK OUT -->
          <td class="p-3 text-gray-700">
            ${window.formatDateTime(a.check_out)}
          </td>

          <!-- STATUS -->
          <td class="p-3">
            <span class="px-3 py-1 rounded-full text-white text-sm
              ${a.status === "present" ? "bg-green-500" : "bg-red-500"}">
              ${a.status}
            </span>
          </td>

          <!-- ACTIONS -->
          <td class="p-3 flex gap-4">

            <!-- VIEW IMAGE (if exists) -->
            ${a.image_path ? `
              <button onclick="attendanceManager.showImage('${a.image_path}')"
                class="text-blue-600 hover:underline">
                View Image
              </button>
            ` : "-"}

            <!-- OPEN MAP -->
            ${a.latitude && a.longitude ? `
              <a href="https://www.google.com/maps?q=${a.latitude},${a.longitude}"
                target="_blank"
                class="text-green-600 hover:underline">
                Map
              </a>
            ` : "-"}

          </td>

        </tr>
      `).join("");

    } catch (e) {
      console.error(e);
      auth.showNotification("Failed to load attendance", "error");
    }
  }

  /* OPEN IMAGE PREVIEW */
  showImage(path) {
    const fullPath = `${window.location.origin}/${path}`;
    const modal = document.getElementById('imagePreviewModal');
    const img = document.getElementById('previewImage');

    if (modal && img) {
      img.src = fullPath;
      modal.classList.remove('hidden');
    } else {
      window.open(fullPath, "_blank");
    }
  }

  async exportAttendance() {
    const dateFilter = document.getElementById("attendanceDateFilter");
    const userFilter = document.getElementById("attendanceUserFilter");

    const date = dateFilter ? dateFilter.value : null;
    const user_id = userFilter?.value === 'all' ? null : userFilter?.value;

    try {
      let url = `/api/admin/attendance?per_page=10000`; // Fetch large number for export
      if (date) url += `&date=${date}`;
      if (user_id) url += `&user_id=${user_id}`;

      const resp = await auth.makeAuthenticatedRequest(url);
      if (!resp || !resp.ok) {
        auth.showNotification("Failed to fetch data for export", "error");
        return;
      }

      const data = await resp.json();
      const items = data.attendance || [];

      if (items.length === 0) {
        auth.showNotification("No records to export", "info");
        return;
      }

      // Convert to CSV
      const headers = ["User", "Check In", "Check Out", "Status", "Address"];
      const rows = items.map(a => [
        a.user_name || "Unknown",
        window.formatDateTime(a.check_in),
        window.formatDateTime(a.check_out),
        a.status,
        (a.address || "").replace(/,/g, " ") // Escape commas
      ]);

      let csvContent = "data:text/csv;charset=utf-8,"
        + headers.join(",") + "\n"
        + rows.map(e => e.join(",")).join("\n");

      const encodedUri = encodeURI(csvContent);
      const link = document.createElement("a");
      link.setAttribute("href", encodedUri);
      link.setAttribute("download", `attendance_export_${date || "all"}.csv`);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);

    } catch (e) {
      console.error("Export failed", e);
      auth.showNotification("Export failed", "error");
    }
  }
}

// Attach to window
window.AttendanceManager = AttendanceManager;
window.attendanceManager = new AttendanceManager();