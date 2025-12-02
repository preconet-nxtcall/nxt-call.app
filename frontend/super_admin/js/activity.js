class ActivityManager {
    constructor() {
        this.activities = [];
        this.init();
    }

    init() {
        const filter = document.getElementById("activityFilter");
        if (filter) {
            filter.addEventListener("change", () => this.renderActivity());
        }
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

    renderActivity() {
        const tableBody = document.getElementById("activity-table-body");
        const filterValue = document.getElementById("activityFilter")?.value || "";

        if (!tableBody) return;

        let logs = this.activities;

        // Apply filter
        if (filterValue) {
            logs = logs.filter(l => l.actor_role === filterValue);
        }

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

                <td class="px-4 py-3 text-gray-800">
                    ${log.action}
                </td>

                <td class="px-4 py-3">
                    <span class="px-3 py-1 rounded-full text-xs font-medium
                        ${
                            log.actor_role === "super_admin"
                                ? "bg-purple-100 text-purple-800"
                                : log.actor_role === "admin"
                                ? "bg-blue-100 text-blue-800"
                                : "bg-green-100 text-green-800"
                        }">
                        ${log.actor_role.replace("_", " ").toUpperCase()}
                    </span>
                </td>

                <td class="px-4 py-3 text-sm text-gray-700">
                    ${log.target_type || "N/A"}
                    <span class="text-xs text-gray-400">(ID: ${log.target_id || "N/A"})</span>
                </td>

                <td class="px-4 py-3 text-sm text-gray-700">
                    ${new Date(log.timestamp).toLocaleString()}
                </td>

            </tr>
        `).join("");
    }
}

const activityManager = new ActivityManager();
