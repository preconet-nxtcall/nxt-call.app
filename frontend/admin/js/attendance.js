/* admin/js/attendance.js */
class AttendanceManager {

  async loadAttendance(date = null, page = 1, per_page = 25) {
    console.log("loadAttendance called with date:", date);
    try {
      let url = `/api/admin/attendance?page=${page}&per_page=${per_page}`;
      if (date) {
        url += `&date=${date}`;
      } else {
        // Default to today (Local Time)
        // en-CA gives YYYY-MM-DD
        const today = new Date().toLocaleDateString('en-CA');
        url += `&date=${today}`;
        console.log("Using default local date:", today);
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
    const modal = document.getElementById('imagePreviewModal');
    const img = document.getElementById('previewImage');

    if (modal && img) {
      img.src = fullPath;
      modal.classList.remove('hidden');
    } else {
      window.open(fullPath, "_blank");
    }
  }
}

// Attach to window
window.AttendanceManager = AttendanceManager;
window.attendanceManager = new AttendanceManager();