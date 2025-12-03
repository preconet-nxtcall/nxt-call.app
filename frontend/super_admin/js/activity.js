class ActivityManager {
    constructor() {
        this.activities = [];
        this.init();
    }

    init() {
        // Filter removed in new design for simplicity, or can be re-added if needed.
        // If we add it back, we'd attach listener here.
    }

    async loadActivity() {
        try {
            const response = await auth.makeAuthenticatedRequest("/api/superadmin/logs");
            const data = await response.json();

            if (!response.ok) {
                auth.showNotification(data.error || "Failed to load logs", "error");
                return;
            }

            this.activities = data.logs || [];
            this.renderActivity();

        } catch (error) {
            console.error("Error loading activity logs:", error);
            auth.showNotification("Error loading activity logs", "error");
        }
    }

    async deleteLogs() {
        try {
            const response = await auth.makeAuthenticatedRequest("/api/superadmin/logs", {
                method: "DELETE"
            });
            const data = await response.json();

            if (response.ok) {
                auth.showNotification(data.message || "Logs deleted successfully", "success");
                this.loadActivity(); // Reload to show empty state (or just the deletion log)
            } else {
                auth.showNotification(data.error || "Failed to delete logs", "error");
            }

        } catch (error) {
            console.error("Error deleting activity logs:", error);
            auth.showNotification("Error deleting activity logs", "error");
        }
    }

    renderActivity() {
        const tableBody = document.getElementById("activity-table-body");
        if (!tableBody) return;

        let logs = this.activities;

        if (logs.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="4" class="text-center py-10 text-gray-500">
                        <i class="fas fa-history text-3xl mb-3 text-gray-300"></i>
                        <p>No logs found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = logs.map(log => `
            <tr class="hover:bg-gray-50 transition">

                <td class="px-6 py-4 text-gray-800 font-medium">
                    ${log.action}
                </td>

                <td class="px-6 py-4">
                    <span class="px-3 py-1 rounded-full text-xs font-medium
                        ${log.actor_role === "super_admin"
                ? "bg-purple-100 text-purple-800"
                : log.actor_role === "admin"
                    ? "bg-blue-100 text-blue-800"
                    : "bg-green-100 text-green-800"
            }">
                        ${log.actor_role ? log.actor_role.replace("_", " ").toUpperCase() : "UNKNOWN"}
                    </span>
                </td>

                <td class="px-6 py-4 text-sm text-gray-700">
                    ${log.target_type || "N/A"}
                    <span class="text-xs text-gray-400 ml-1">(ID: ${log.target_id || "N/A"})</span>
                </td>

                <td class="px-6 py-4 text-sm text-gray-500">
                    ${new Date(log.timestamp).toLocaleString()}
                </td>

            </tr>
        `).join("");
    }
}

// Instance is created in index.html now, but we can keep this if we want global access
// window.activityManager = new ActivityManager();
