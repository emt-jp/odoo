/** @odoo-module **/

import { Component, useState, onWillStart, onMounted } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";

export class AnalyticsDashboard extends Component {
    static template = "advanced_analytics.AnalyticsDashboard";
    static props = {
        action: { type: Object, optional: true },
    };

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.notification = useService("notification");

        this.state = useState({
            dashboards: [],
            selectedDashboard: null,
            kpis: [],
            charts: [],
            isLoading: true,
            error: null,
            dateFrom: this.getDefaultDateFrom(),
            dateTo: this.getDefaultDateTo(),
        });

        onWillStart(async () => {
            await this.loadDashboards();
        });

        onMounted(() => {
            this.renderCharts();
        });
    }

    getDefaultDateFrom() {
        const date = new Date();
        date.setMonth(date.getMonth() - 1);
        return date.toISOString().split('T')[0];
    }

    getDefaultDateTo() {
        return new Date().toISOString().split('T')[0];
    }

    async loadDashboards() {
        try {
            this.state.isLoading = true;
            const dashboards = await this.orm.searchRead(
                "analytics.dashboard",
                [["active", "=", true]],
                ["id", "name", "dashboard_type", "description"]
            );
            this.state.dashboards = dashboards;

            if (dashboards.length > 0) {
                await this.selectDashboard(dashboards[0]);
            }
        } catch (error) {
            this.state.error = error.message;
            this.notification.add(_t("Failed to load dashboards"), {
                type: "danger",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    async selectDashboard(dashboard) {
        this.state.selectedDashboard = dashboard;
        await this.loadDashboardData(dashboard.id);
    }

    async loadDashboardData(dashboardId) {
        try {
            this.state.isLoading = true;

            // Load KPIs
            const kpis = await this.orm.searchRead(
                "analytics.kpi",
                [["dashboard_id", "=", dashboardId], ["active", "=", true]],
                ["id", "name", "kpi_type", "target_value", "color", "icon"]
            );
            this.state.kpis = kpis;

            // Load dashboard data
            const data = await this.orm.call(
                "analytics.dashboard",
                "get_dashboard_data",
                [dashboardId]
            );

            if (data.charts) {
                this.state.charts = data.charts;
            }

        } catch (error) {
            console.error("Dashboard load error:", error);
            this.notification.add(_t("Failed to load dashboard data"), {
                type: "warning",
            });
        } finally {
            this.state.isLoading = false;
        }
    }

    renderCharts() {
        // Charts will be rendered by the template using Chart.js or similar
        // This is a placeholder for chart initialization
    }

    async refreshDashboard() {
        if (this.state.selectedDashboard) {
            await this.loadDashboardData(this.state.selectedDashboard.id);
            this.notification.add(_t("Dashboard refreshed"), {
                type: "success",
            });
        }
    }

    onDateChange() {
        if (this.state.selectedDashboard) {
            this.loadDashboardData(this.state.selectedDashboard.id);
        }
    }

    openDashboardConfig() {
        if (this.state.selectedDashboard) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "analytics.dashboard",
                res_id: this.state.selectedDashboard.id,
                views: [[false, "form"]],
                target: "current",
            });
        }
    }

    openKpiConfig(kpiId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            res_model: "analytics.kpi",
            res_id: kpiId,
            views: [[false, "form"]],
            target: "new",
        });
    }

    getKpiIcon(kpi) {
        return kpi.icon || "fa-chart-line";
    }

    getKpiColorClass(kpi) {
        const colorMap = {
            "primary": "bg-primary",
            "success": "bg-success",
            "warning": "bg-warning",
            "danger": "bg-danger",
            "info": "bg-info",
        };
        return colorMap[kpi.color] || "bg-primary";
    }

    getDashboardTypeIcon(type) {
        const iconMap = {
            "sales": "fa-shopping-cart",
            "financial": "fa-dollar",
            "inventory": "fa-cubes",
            "crm": "fa-users",
            "custom": "fa-cog",
        };
        return iconMap[type] || "fa-chart-bar";
    }
}

// Register the component as a client action
registry.category("actions").add("advanced_analytics.dashboard", AnalyticsDashboard);
