/************************************************************
 * SUPER ADMIN DASHBOARD CONTROLLER
 ************************************************************/
class SuperAdminDashboard {
    constructor() {
        this.stats = null;
        this.init();
    }

    /************************************************************
     * INITIAL SETUP
     ************************************************************/
    async init() {
        console.log("DEBUG: Initializing SuperAdmin Dashboard...");
        this.setupNavigation();
        this.setupEventListeners();
        await this.loadStats();
        await this.loadRecentActivity();
    }

    /************************************************************
     * LOAD DASHBOARD STATS
     ************************************************************/
    async loadStats() {
        try {
            console.log("DEBUG: Fetching dashboard stats...");

            const response = await auth.makeAuthenticatedRequest("/api/superadmin/dashboard-stats");
            const data = await response.json();

            console.log("DEBUG: Dashboard stats received:", data);

            if (response.ok) {
                this.stats = data.stats;
                this.renderStats();
            } else {
                auth.showNotification(data.error || "Failed to load dashboard stats", "error");
            }

        } catch (error) {
            console.error("ERROR Loading Stats:", error);
            auth.showNotification("Error loading dashboard stats", "error");
        }
    }

    /************************************************************
     * RENDER STATS CARDS
     ************************************************************/
    renderStats() {
        const container = document.getElementById("stats-cards");
        if (!container || !this.stats) return;

        const cards = [
            {
                label: "Total Admins",
                value: this.stats.total_admins || 0,
                icon: "users-cog",
                color: "text-blue-600",
                bg: "bg-blue-50"
            },
            {
                label: "Total Users",
                value: this.stats.total_users || 0,
                icon: "users",
                color: "text-green-600",
                bg: "bg-green-50"
            },
            {
                label: "Active Admins",
                value: this.stats.active_admins || 0,
                icon: "user-check",
                color: "text-emerald-600",
                bg: "bg-emerald-50"
            },
            {
                label: "Expired Admins",
                value: this.stats.expired_admins || 0,
                icon: "exclamation-circle",
                color: "text-red-600",
                bg: "bg-red-50"
            }
        ];

        container.innerHTML = cards
            .map(card => `
                <div class="stat-card bg-white rounded-xl shadow-sm border border-gray-200 p-6">
                    <div class="flex items-center justify-between">
                        <div>
                            <p class="text-xs text-gray-500">${card.label}</p>
                            <p class="text-3xl font-bold text-gray-800 mt-1">${card.value}</p>
                        </div>
                        <div class="${card.bg} w-12 h-12 rounded-lg flex items-center justify-center">
                            <i class="fas fa-${card.icon} ${card.color} text-xl"></i>
                        </div>
                    </div>
                </div>
            `)
            .join("");
    }

    /************************************************************
     * LOAD RECENT ACTIVITY
     ************************************************************/
    async loadRecentActivity() {
        try {
            console.log("DEBUG: Loading recent activity...");

            const response = await auth.makeAuthenticatedRequest("/api/superadmin/logs");
            const data = await response.json();

            console.log("DEBUG: Recent Activity:", data);

            if (response.ok) {
                this.renderRecentActivity(data.logs || []);
            } else {
                auth.showNotification(data.error || "Unable to load recent activity", "error");
            }

        } catch (error) {
            console.error("ERROR Loading Activity:", error);
            auth.showNotification("Error loading recent activity", "error");
        }
    }

    /************************************************************
     * RENDER RECENT ACTIVITY (Right Side Panel)
     ************************************************************/
    renderRecentActivity(logs) {
        const container = document.getElementById("recent-activity");
        if (!container) return;

        if (logs.length === 0) {
            container.innerHTML = `
                <div class="text-center text-gray-500 py-6">
                    <i class="fas fa-history text-3xl text-gray-300"></i>
                    <p>No recent activity</p>
                </div>
            `;
            return;
        }

        container.innerHTML = logs.slice(0, 8).map(log => `
            <div class="flex items-start space-x-3 p-3 rounded-lg hover:bg-gray-50 transition">
                <div class="w-9 h-9 rounded-full flex items-center justify-center
                    ${
                        log.actor_role === "super_admin" ? "bg-purple-100 text-purple-600" :
                        log.actor_role === "admin" ? "bg-blue-100 text-blue-600" :
                        "bg-green-100 text-green-600"
                    }">
                    <i class="fas fa-${this.getIcon(log.action)}"></i>
                </div>

                <div>
                    <p class="text-sm text-gray-800">${log.action}</p>
                    <p class="text-xs text-gray-500">${this.formatTime(log.timestamp)}</p>
                </div>
            </div>
        `).join("");
    }

    /************************************************************
     * SMALL HELPERS
     ************************************************************/
    getIcon(action) {
        if (!action) return "history";
        const a = action.toLowerCase();
        if (a.includes("create")) return "plus-circle";
        if (a.includes("delete")) return "trash";
        if (a.includes("update")) return "edit";
        if (a.includes("login")) return "sign-in-alt";
        if (a.includes("logout")) return "sign-out-alt";
        return "history";
    }

    formatTime(timestamp) {
        if (!timestamp) return "Unknown";
        const d = new Date(timestamp);
        return `${d.toLocaleDateString()} ${d.toLocaleTimeString()}`;
    }

    /************************************************************
     * NAVIGATION (Switch Sections)
     ************************************************************/
    setupNavigation() {
        const navItems = document.querySelectorAll(".nav-item");

        navItems.forEach(item => {
            item.addEventListener("click", (e) => {
                e.preventDefault();

                // highlight active
                navItems.forEach(n => n.classList.remove("active"));
                item.classList.add("active");

                const target = item.getAttribute("href").replace("#", "");
                this.showSection(target);
            });
        });
    }

    showSection(section) {
        const sections = ["dashboard", "admins", "activity"];

        sections.forEach(sec => {
            const el = document.getElementById(`${sec}-section`);
            if (el) el.style.display = "none";
        });

        document.getElementById(`${section}-section`).style.display = "block";

        const title = document.getElementById("page-title");
        const subtitle = document.getElementById("page-subtitle");

        if (section === "dashboard") {
            title.textContent = "Dashboard Overview";
            subtitle.textContent = "Welcome back! Here's your system overview.";
            this.loadStats();
            this.loadRecentActivity();
        }

        if (section === "admins") {
            title.textContent = "Manage Administrators";
            subtitle.textContent = "Create & manage admin accounts.";
            adminsManager.loadAdmins();
        }

        if (section === "activity") {
            title.textContent = "Activity Logs";
            subtitle.textContent = "Track system activities.";
            activityManager.loadActivity();
        }
    }

    /************************************************************
     * EVENT HANDLERS
     ************************************************************/
    setupEventListeners() {
        console.log("Super Admin Dashboard Ready ✔");
    }
}

/************************************************************
 * INITIALIZE
 ************************************************************/
document.addEventListener("DOMContentLoaded", () => {
    window.superAdminDashboard = new SuperAdminDashboard();
});
