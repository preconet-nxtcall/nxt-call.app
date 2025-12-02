/* admin/js/performance.js */

class PerformanceManager {

  async loadPerformance(sortType = "desc") {
    try {
      const resp = await auth.makeAuthenticatedRequest(`/api/admin/performance?sort=${sortType}`);
      if (!resp) return;

      const data = await resp.json();

      if (!resp.ok) {
        auth.showNotification(data.error || "Failed to load performance", "error");
        return;
      }

      const labels = data.labels || [];
      const values = data.values || [];
      const user_ids = data.user_ids || [];

      // Render both chart + table
      this.renderChart(labels, values);
      this.renderTable(labels, values, user_ids);

    } catch (e) {
      console.error(e);
      auth.showNotification("Error loading performance", "error");
    }
  }

  renderChart(labels, values) {
    const ctx = document.getElementById("performanceBarCanvas").getContext("2d");

    if (this.chart) this.chart.destroy();

    this.chart = new Chart(ctx, {
      type: "bar",
      data: {
        labels: labels,
        datasets: [
          {
            label: "Performance Score",
            data: values,
            backgroundColor: values.map(v =>
              v >= 80 ? "#22c55e" :      // green (excellent)
              v >= 60 ? "#3b82f6" :      // blue (good)
              v >= 40 ? "#f59e0b" :      // orange (average)
              "#ef4444"                 // red (poor)
            ),
            borderWidth: 1
          }
        ]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          tooltip: {
            callbacks: {
              label: ctx => `Score: ${ctx.raw}`
            }
          }
        }
      }
    });
  }

  renderTable(labels, values, ids) {
    const body = document.getElementById("performanceTableBody");
    if (!body) return;

    body.innerHTML = labels.map((name, i) => `
      <tr class="border-t hover:bg-gray-50">
        <td class="p-2">${name}</td>
        <td class="p-2 font-semibold">${values[i]}</td>
        <td class="p-2">
          <button 
            class="text-blue-600 underline"
            onclick="performanceManager.viewUserDetails(${ids[i]})"
          >
            View
          </button>
        </td>
      </tr>
    `).join('');
  }

  async viewUserDetails(user_id) {
    auth.showNotification("Feature coming soon: User details (#" + user_id + ")", "info");
  }
}

const performanceManager = new PerformanceManager();

// SORT CHANGE EVENT
document.addEventListener("DOMContentLoaded", () => {
  const sortSelect = document.getElementById("performanceSort");
  if (sortSelect) {
    sortSelect.addEventListener("change", () => {
      performanceManager.loadPerformance(sortSelect.value);
    });
  }

  performanceManager.loadPerformance("desc");
});
