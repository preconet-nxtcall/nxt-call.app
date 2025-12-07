/* js/main.js */

document.addEventListener("DOMContentLoaded", () => {
    console.log("Admin Panel Loaded");

    // ---------------------------------
    // 0. GLOBAL HELPERS
    // ---------------------------------
    window.formatDateTime = (dateString) => {
        if (!dateString) return '-';
        const date = new Date(dateString);
        return date.toLocaleString('en-US', {
            year: 'numeric',
            month: 'short',
            day: 'numeric',
            hour: 'numeric',
            minute: 'numeric',
            hour12: true
        });
    };

    // ---------------------------------
    // 0. INITIALIZATION (Moved top for Nav)
    // ---------------------------------
    window.dashboard = new DashboardManager();
    window.usersManager = new UsersManager();
    window.attendanceManager = new AttendanceManager();
    window.callHistoryManager = new CallHistoryManager();
    window.callAnalyticsManager = new CallAnalyticsManager();
    window.performanceManager = new PerformanceManager();

    // Load Dashboard by default
    if (window.dashboard) {
        window.dashboard.loadStats();
    }

    // ---------------------------------
    // 1. SIDEBAR TOGGLE
    // ---------------------------------
    const sidebar = document.getElementById("sidebar");
    const overlay = document.getElementById("overlay");
    const openBtn = document.getElementById("openSidebar");
    const closeBtn = document.getElementById("closeSidebar");

    function toggleSidebar(show) {
        if (show) {
            sidebar.classList.add("active");
            overlay.classList.add("active");
        } else {
            sidebar.classList.remove("active");
            overlay.classList.remove("active");
        }
    }

    if (openBtn) openBtn.onclick = () => toggleSidebar(true);
    if (closeBtn) closeBtn.onclick = () => toggleSidebar(false);
    if (overlay) overlay.onclick = () => toggleSidebar(false);


    // ---------------------------------
    // 2. NAVIGATION HANDLER
    // ---------------------------------
    const navItems = [
        { id: "menuDashboard", section: "sectionDashboard", title: "Dashboard", manager: window.dashboard },
        { id: "menuCallAnalytics", section: "sectionCallAnalytics", title: "Call Analytics", manager: window.callAnalyticsManager },
        { id: "menuPerformance", section: "sectionPerformance", title: "Performance", manager: window.performanceManager },
        { id: "menuUsers", section: "sectionUsers", title: "User Management", manager: window.usersManager },
        { id: "menuCreateUser", section: "sectionCreateUser", title: "Create User", manager: null }, // No manager needed for form
        { id: "menuAttendance", section: "sectionAttendance", title: "Attendance Records", manager: window.attendanceManager },
        { id: "menuCallHistory", section: "sectionCallHistory", title: "Call Logs", manager: window.callHistoryManager },
        { id: "menuFollowup", section: "sectionFollowup", title: "Follow-ups", manager: window.followupManager }
    ];

    const pageTitle = document.getElementById("pageTitle");

    function activateSection(item) {
        // 1. Hide all sections
        navItems.forEach(nav => {
            const sec = document.getElementById(nav.section);
            if (sec) sec.classList.add("hidden-section");

            const menu = document.getElementById(nav.id);
            if (menu) {
                menu.classList.remove("bg-blue-600", "text-white", "shadow-md");
                menu.classList.add("text-gray-300", "hover:bg-gray-800", "hover:text-white");

                // Reset icon color
                const icon = menu.querySelector("i");
                if (icon) {
                    icon.classList.remove("text-blue-200");
                    icon.classList.add("text-gray-400");
                }
            }
        });

        // 2. Show target section
        const targetSec = document.getElementById(item.section);
        if (targetSec) targetSec.classList.remove("hidden-section");

        // 3. Highlight menu item
        const targetMenu = document.getElementById(item.id);
        if (targetMenu) {
            targetMenu.classList.remove("text-gray-300", "hover:bg-gray-800", "hover:text-white");
            targetMenu.classList.add("bg-blue-600", "text-white", "shadow-md");

            const icon = targetMenu.querySelector("i");
            if (icon) {
                icon.classList.remove("text-gray-400");
                icon.classList.add("text-blue-200");
            }
        }

        // 4. Update Title
        if (pageTitle) pageTitle.textContent = item.title;

        // 5. Initialize/Load Data if Manager exists
        if (item.manager && typeof item.manager.init === 'function') {
            item.manager.init();
        } else if (item.manager && typeof item.manager.load === 'function') {
            item.manager.load();
        }

        // Special case for Dashboard (it might use loadStats)
        if (item.id === "menuDashboard" && window.dashboard) {
            window.dashboard.loadStats();
        }

        // Close sidebar on mobile
        if (window.innerWidth < 1024) {
            toggleSidebar(false);
        }
    }

    // Attach Click Events
    navItems.forEach(item => {
        const el = document.getElementById(item.id);
        if (el) {
            el.addEventListener("click", () => activateSection(item));
        }
    });






    // Set current date
    const dateEl = document.getElementById("currentDate");
    if (dateEl) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        dateEl.textContent = new Date().toLocaleDateString('en-US', options);
    }

    // Logout Handler
    const logoutBtn = document.getElementById("logoutBtn");
    if (logoutBtn) {
        logoutBtn.addEventListener("click", () => {
            if (confirm("Are you sure you want to logout?")) {
                auth.logout();
            }
        });
    }

});
