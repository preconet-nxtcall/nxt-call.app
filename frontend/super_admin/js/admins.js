/************************************************************
 *  ADMINS MANAGER – SUPER ADMIN DASHBOARD
 ************************************************************/
class AdminsManager {
    constructor() {
        this.admins = [];
        // Init handled by index.html calls
    }

    /************************************************************
     * CREATE ADMIN
     ************************************************************/
    async createAdmin() {
        const name = document.getElementById("adminName").value.trim();
        const email = document.getElementById("adminEmail").value.trim();
        const password = document.getElementById("adminPassword").value.trim();
        const userLimit = Number(document.getElementById("userLimit").value || 10);
        const expiryRaw = document.getElementById("expiryDate").value;

        if (!name || !email || !password || !expiryRaw) {
            auth.showNotification("Please fill all fields", "error");
            return;
        }

        const payload = {
            name,
            email,
            password,
            user_limit: userLimit,
            expiry_date: expiryRaw // Backend expects YYYY-MM-DD
        };

        try {
            const response = await auth.makeAuthenticatedRequest(
                "/api/superadmin/create-admin",
                {
                    method: "POST",
                    body: JSON.stringify(payload)
                }
            );

            const data = await response.json();

            if (response.ok) {
                auth.showNotification("Admin created successfully!", "success");

                // Reset form and close modal
                document.getElementById("createAdminForm").reset();
                document.getElementById("createAdminModal").classList.add("hidden");

                this.loadAdmins();

            } else {
                auth.showNotification(data.error || "Failed to create admin", "error");
            }

        } catch (error) {
            console.error("CREATE ADMIN ERROR:", error);
            auth.showNotification("Server error while creating admin", "error");
        }
    }

    /************************************************************
     * LOAD ADMINS
     ************************************************************/
    async loadAdmins() {
        try {
            const response = await auth.makeAuthenticatedRequest("/api/superadmin/admins");
            const data = await response.json();

            if (response.ok) {
                this.admins = data.admins || [];
                this.renderAdmins();
            } else {
                auth.showNotification(data.error || "Failed to load admins", "error");
            }

        } catch (error) {
            console.error("LOAD ADMINS ERROR:", error);
            auth.showNotification("Server error while loading admins", "error");
        }
    }

    /************************************************************
     * TOGGLE ADMIN STATUS (BLOCK/UNBLOCK)
     ************************************************************/
    async toggleAdminStatus(adminId, currentStatus) {
        if (!confirm(`Are you sure you want to ${currentStatus ? 'block' : 'unblock'} this admin?`)) {
            return;
        }

        try {
            const response = await auth.makeAuthenticatedRequest(
                `/api/superadmin/admin/${adminId}/status`,
                { method: "PUT" }
            );
            const data = await response.json();

            if (response.ok) {
                auth.showNotification(data.message, "success");
                this.loadAdmins();
            } else {
                auth.showNotification(data.error || "Failed to update status", "error");
            }

        } catch (error) {
            console.error("TOGGLE STATUS ERROR:", error);
            auth.showNotification("Server error", "error");
        }
    }

    /************************************************************
     * DELETE ADMIN
     ************************************************************/
    async deleteAdmin(adminId) {
        if (!confirm("Are you sure you want to delete this admin? This action cannot be undone.")) {
            return;
        }

        try {
            const response = await auth.makeAuthenticatedRequest(
                `/api/superadmin/admin/${adminId}`,
                { method: "DELETE" }
            );
            const data = await response.json();

            if (response.ok) {
                auth.showNotification(data.message, "success");
                this.loadAdmins();
            } else {
                auth.showNotification(data.error || "Failed to delete admin", "error");
            }

        } catch (error) {
            console.error("DELETE ADMIN ERROR:", error);
            auth.showNotification("Server error", "error");
        }
    }

    /************************************************************
     * RENDER ADMIN TABLE
     ************************************************************/
    renderAdmins() {
        const tableBody = document.getElementById("admins-table-body");
        if (!tableBody) return;

        if (this.admins.length === 0) {
            tableBody.innerHTML = `
                <tr>
                    <td colspan="6" class="py-10 text-center text-gray-500">
                        <i class="fas fa-users-slash text-3xl mb-2 text-gray-300"></i>
                        <p>No admins found</p>
                    </td>
                </tr>
            `;
            return;
        }

        tableBody.innerHTML = this.admins
            .map(admin => {
                let exp = admin.expiry_date ? new Date(admin.expiry_date) : null;
                let expiryStr = exp && !isNaN(exp) ? exp.toLocaleDateString() : "N/A";

                let status =
                    !admin.is_active
                        ? `<span class="bg-red-100 text-red-800 px-2.5 py-0.5 rounded-full text-xs font-medium">Inactive</span>`
                        : admin.is_expired
                            ? `<span class="bg-orange-100 text-orange-800 px-2.5 py-0.5 rounded-full text-xs font-medium">Expired</span>`
                            : `<span class="bg-green-100 text-green-800 px-2.5 py-0.5 rounded-full text-xs font-medium">Active</span>`;

                return `
                <tr class="hover:bg-gray-50 transition">

                    <!-- NAME -->
                    <td class="px-6 py-4">
                        <div class="flex items-center space-x-3">
                            <div class="w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center text-blue-600 font-bold text-xs">
                                ${admin.name.substring(0, 2).toUpperCase()}
                            </div>
                            <div class="font-medium text-gray-900">${admin.name}</div>
                        </div>
                    </td>

                    <!-- EMAIL -->
                    <td class="px-6 py-4 text-gray-500">
                        ${admin.email}
                    </td>

                    <!-- USER LIMIT -->
                    <td class="px-6 py-4 text-gray-500">
                        ${admin.user_limit}
                    </td>

                    <!-- USERS CREATED -->
                    <td class="px-6 py-4">
                        <span class="px-2.5 py-0.5 bg-gray-100 text-gray-800 rounded-full text-xs font-medium">
                            ${admin.user_count} / ${admin.user_limit}
                        </span>
                    </td>

                    <!-- EXPIRY -->
                    <td class="px-6 py-4 text-gray-500">
                        ${expiryStr}
                    </td>

                    <!-- STATUS -->
                    <td class="px-6 py-4">
                        ${status}
                    </td>

                    <!-- ACTIONS -->
                    <td class="px-6 py-4">
                        <div class="flex items-center space-x-2">
                            <!-- Toggle Status Button -->
                            <button onclick="adminsManager.toggleAdminStatus(${admin.id}, ${admin.is_active})"
                                class="p-2 rounded hover:bg-gray-100 text-gray-600 transition"
                                title="${admin.is_active ? 'Block Admin' : 'Unblock Admin'}">
                                <i class="fas ${admin.is_active ? 'fa-ban text-orange-500' : 'fa-check-circle text-green-500'}"></i>
                            </button>

                            <!-- Delete Button -->
                            <button onclick="adminsManager.deleteAdmin(${admin.id})"
                                class="p-2 rounded hover:bg-red-50 text-red-600 transition"
                                title="Delete Admin">
                                <i class="fas fa-trash"></i>
                            </button>
                        </div>
                    </td>

                </tr>
                `;
            })
            .join("");
    }
}
