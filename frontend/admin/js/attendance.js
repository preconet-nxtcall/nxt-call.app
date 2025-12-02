/* admin/js/attendance.js */
class AttendanceManager {

  async loadAttendance(filter = "today", page = 1, per_page = 25) {
    try {
      const resp = await auth.makeAuthenticatedRequest(
        `/api/admin/attendance?filter=${filter}&page=${page}&per_page=${per_page}`
      );

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
            ${a.check_in ? new Date(a.check_in).toLocaleString() : "-"}
            <div class="text-xs text-gray-500">${a.address || ""}</div>
          </td>

          <!-- CHECK OUT -->
          <td class="p-3 text-gray-700">
            ${a.check_out ? new Date(a.check_out).toLocaleString() : "-"}
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
    window.open(fullPath, "_blank");
  }
}

const attendanceManager = new AttendanceManager();