import React, { useEffect, useMemo, useState } from "react";

import { KpiCard } from "../components/KpiCard";
import { TaskBoard } from "../components/TaskBoard";

const gatewayUrl = import.meta.env.VITE_API_GATEWAY_URL || "http://localhost:8480";

const emptyDashboard = {
  order: {
    order_id: "ORD-DEMO",
    origin: "Москва",
    destination: "Казань",
    transport_mode: "road",
    cargo_type: "refrigerated",
    weight_kg: 0,
    cost: { total_cost: 0 },
    status: "created",
  },
  routes: { items: [] },
  tracking: { items: [] },
  violations: { items: [] },
  warehouse: { total_sku: 0, total_units: 0, zones: {}, operations_count: 0 },
  inventory: { items: [] },
  fleet: { avg_load_ratio: 0, avg_cost_per_km: 0, eta_mape: 0, tracked_routes: 0 },
  kpi: {
    route_build_seconds_estimate: 0,
    target_route_build_seconds: 5,
    eta_mape_pct: 0,
    target_eta_mape_pct: 10,
    capacity_target_vehicles: 5000,
  },
  integration: { items: [] },
  notifications: { items: [] },
  assignment: { vehicle_id: "VEH-101", driver_id: "DRV-007", route_id: "ROUTE-DEMO" },
  driver_metrics: { kpi: 0, on_time_ratio: 0, incident_rate: 0, fuel_efficiency: 0 },
};

async function loadDashboard(orderId, vehicleId) {
  const response = await fetch(`${gatewayUrl}/dashboard/${orderId}/${vehicleId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch dashboard: ${response.status}`);
  }
  return response.json();
}

export function DashboardPage() {
  const [orderId, setOrderId] = useState("ORD-DEMO");
  const [vehicleId, setVehicleId] = useState("VEH-101");
  const [theme, setTheme] = useState("light");
  const [status, setStatus] = useState("loading");
  const [error, setError] = useState(null);
  const [dashboard, setDashboard] = useState(emptyDashboard);

  useEffect(() => {
    let active = true;

    loadDashboard(orderId, vehicleId)
      .then((payload) => {
        if (!active) {
          return;
        }
        setDashboard({ ...emptyDashboard, ...payload });
        setStatus("succeeded");
        setError(null);
      })
      .catch((err) => {
        if (!active) {
          return;
        }
        setStatus("failed");
        setError(err.message);
      });

    return () => {
      active = false;
    };
  }, [orderId, vehicleId]);

  const routes = dashboard.routes?.items || [];
  const lastTrackPoint = dashboard.tracking?.items?.[dashboard.tracking.items.length - 1];
  const violationCount = dashboard.violations?.count || dashboard.violations?.items?.length || 0;
  const integrationItems = dashboard.integration?.items || [];
  const notifications = dashboard.notifications?.items || [];
  const inventoryItems = dashboard.inventory?.items || [];
  const statusLabel = useMemo(() => {
    if (status === "loading") {
      return "loading";
    }
    if (status === "failed") {
      return "Service unavailable";
    }
    return "live";
  }, [status]);

  const refresh = async () => {
    try {
      setStatus("loading");
      const payload = await loadDashboard(orderId, vehicleId);
      setDashboard({ ...emptyDashboard, ...payload });
      setStatus("succeeded");
      setError(null);
    } catch (err) {
      setStatus("failed");
      setError(err.message);
    }
  };

  return (
    <div className={`app theme-${theme}`}>
      <div className="background-orb orb-a" />
      <div className="background-orb orb-b" />

      <header className="hero">
        <div className="hero-copy">
          <p className="eyebrow">LogiTrack Control Tower</p>
          <h1>Fleet operations</h1>
          <p className="sub">
            LogiTrack unifies order intake, ETA forecasting, dynamic rerouting, driver monitoring, warehouse operations,
            and external GPS or ERP integrations for dispatch teams.
          </p>
          <div className="hero-badges">
            <span>Dynamic rerouting</span>
            <span>ETA prediction</span>
            <span>GLONASS and GPS sync</span>
            <span>Parallel track processing</span>
          </div>
        </div>

        <div className="hero-panel">
          <label>
            Order ID
            <input value={orderId} onChange={(event) => setOrderId(event.target.value)} placeholder="ORD-DEMO" />
          </label>
          <label>
            Vehicle ID
            <input value={vehicleId} onChange={(event) => setVehicleId(event.target.value)} placeholder="VEH-101" />
          </label>
          <div className="hero-actions">
            <button onClick={refresh} disabled={status === "loading"}>Refresh dashboard</button>
            <button className="ghost" onClick={() => setTheme((current) => (current === "light" ? "dark" : "light"))}>
              Theme
            </button>
          </div>
          <p className="status-line" role="status" aria-live="polite">Status: {statusLabel}</p>
        </div>
      </header>

      <section className="kpi-grid">
        <KpiCard
          title="Route Build"
          value={`${Number(dashboard.kpi?.route_build_seconds_estimate || 0).toFixed(1)} sec`}
          target={`Target < ${dashboard.kpi?.target_route_build_seconds || 5} sec`}
          ok={Number(dashboard.kpi?.route_build_seconds_estimate || 99) <= Number(dashboard.kpi?.target_route_build_seconds || 5)}
        />
        <KpiCard
          title="ETA MAPE"
          value={`${Number(dashboard.kpi?.eta_mape_pct || 0).toFixed(1)}%`}
          target={`Target < ${dashboard.kpi?.target_eta_mape_pct || 10}%`}
          ok={Number(dashboard.kpi?.eta_mape_pct || 100) <= Number(dashboard.kpi?.target_eta_mape_pct || 10)}
        />
        <KpiCard
          title="Fleet Load"
          value={`${Math.round((dashboard.fleet?.avg_load_ratio || 0) * 100)}%`}
          target="Keep above 70%"
          ok={Number(dashboard.fleet?.avg_load_ratio || 0) >= 0.7}
        />
        <KpiCard
          title="Driver KPI"
          value={Number(dashboard.driver_metrics?.kpi || 0).toFixed(1)}
          target="Keep above 80"
          ok={Number(dashboard.driver_metrics?.kpi || 0) >= 80}
        />
      </section>

      {error ? <div className="error-banner" role="alert">{error}</div> : null}

      <section className="content-grid">
        <article className="panel panel-featured">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Order Control</p>
              <h2>
                {dashboard.order?.origin} to {dashboard.order?.destination}
              </h2>
            </div>
            <span className="pill">{dashboard.order?.status}</span>
          </div>
          <p className="panel-copy">
            {dashboard.order?.order_id} uses {dashboard.order?.transport_mode} transport with {dashboard.order?.cargo_type} cargo.
            Current assigned vehicle: {dashboard.assignment?.vehicle_id || vehicleId}.
          </p>
          <div className="metrics-row">
            <div>
              <strong>{dashboard.order?.weight_kg || 0}</strong>
              <span>kg cargo</span>
            </div>
            <div>
              <strong>{Math.round(dashboard.order?.cost?.total_cost || 0).toLocaleString()}</strong>
              <span>RUB total cost</span>
            </div>
            <div>
              <strong>{routes.length}</strong>
              <span>route options</span>
            </div>
            <div>
              <strong>{dashboard.kpi?.capacity_target_vehicles || 5000}</strong>
              <span>vehicle target</span>
            </div>
          </div>
          <TaskBoard routes={routes} />
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Telemetry</p>
              <h2>Vehicle pulse</h2>
            </div>
            <span className="pill accent">{dashboard.tracking?.items?.length || 0} points</span>
          </div>
          <div className="signal-grid">
            <div className="signal-card">
              <span>Speed</span>
              <strong>{lastTrackPoint ? `${Math.round(lastTrackPoint.speed_kph)} km/h` : "No data"}</strong>
            </div>
            <div className="signal-card">
              <span>Fuel</span>
              <strong>{lastTrackPoint ? `${Math.round(lastTrackPoint.fuel_level_pct)}%` : "No data"}</strong>
            </div>
            <div className="signal-card">
              <span>Cargo temp</span>
              <strong>{lastTrackPoint?.cargo_temp_c != null ? `${lastTrackPoint.cargo_temp_c} °C` : "N/A"}</strong>
            </div>
            <div className="signal-card">
              <span>Violations</span>
              <strong>{violationCount}</strong>
            </div>
          </div>
          <div className="stack-list">
            {(dashboard.tracking?.items || []).slice(-4).reverse().map((point, index) => (
              <div className="stack-item" key={`${point.timestamp}-${index}`}>
                <div>
                  <p className="stack-title">{new Date(point.timestamp).toLocaleString()}</p>
                  <p className="stack-sub">
                    {point.latitude.toFixed(3)}, {point.longitude.toFixed(3)}
                  </p>
                </div>
                <span>{Math.round(point.speed_kph)} km/h</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Risk Desk</p>
              <h2>Driver and delay alerts</h2>
            </div>
            <span className="pill">{dashboard.assignment?.driver_id || "DRV"}</span>
          </div>
          <div className="stack-list">
            {(dashboard.violations?.items || []).length ? (
              dashboard.violations.items.map((alert) => (
                <div className="stack-item" key={alert.alert_id}>
                  <div>
                    <p className="stack-title">{alert.severity}</p>
                    <p className="stack-sub">{alert.message}</p>
                  </div>
                  <span>{alert.driver_id}</span>
                </div>
              ))
            ) : (
              <div className="empty-board">Нарушений по текущему рейсу нет.</div>
            )}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Warehouse</p>
              <h2>Stock and zones</h2>
            </div>
            <span className="pill accent">{dashboard.warehouse?.total_units || 0} units</span>
          </div>
          <div className="analytics-grid">
            <div>
              <strong>{dashboard.warehouse?.total_sku || 0}</strong>
              <span>sku</span>
            </div>
            <div>
              <strong>{Object.keys(dashboard.warehouse?.zones || {}).length}</strong>
              <span>zones</span>
            </div>
            <div>
              <strong>{dashboard.warehouse?.operations_count || 0}</strong>
              <span>operations</span>
            </div>
            <div>
              <strong>{inventoryItems.length}</strong>
              <span>visible items</span>
            </div>
          </div>
          <div className="zone-list">
            {Object.entries(dashboard.warehouse?.zones || {}).map(([zone, value]) => (
              <div className="stack-item" key={zone}>
                <div>
                  <p className="stack-title">{zone}</p>
                  <p className="stack-sub">Storage zone</p>
                </div>
                <span>{value} units</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Integrations</p>
              <h2>External sync history</h2>
            </div>
            <span className="pill">{integrationItems.length} syncs</span>
          </div>
          <div className="stack-list">
            {integrationItems.slice(-4).reverse().map((item) => (
              <div className="stack-item" key={item.sync_id}>
                <div>
                  <p className="stack-title">{item.system_name}</p>
                  <p className="stack-sub">{item.status}</p>
                </div>
                <span>{new Date(item.created_at).toLocaleDateString()}</span>
              </div>
            ))}
          </div>
        </article>

        <article className="panel panel-analytics">
          <div className="panel-head compact">
            <div>
              <p className="section-kicker">Dispatch Analytics</p>
              <h2>Fleet and communications snapshot</h2>
            </div>
            <span className="pill accent">{dashboard.fleet?.tracked_routes || 0} routes</span>
          </div>
          <div className="analytics-grid">
            <div>
              <strong>{Number(dashboard.fleet?.avg_cost_per_km || 0).toFixed(1)}</strong>
              <span>RUB per km</span>
            </div>
            <div>
              <strong>{Math.round((dashboard.driver_metrics?.on_time_ratio || 0) * 100)}%</strong>
              <span>on-time ratio</span>
            </div>
            <div>
              <strong>{Number(dashboard.driver_metrics?.fuel_efficiency || 0).toFixed(2)}</strong>
              <span>fuel efficiency</span>
            </div>
            <div>
              <strong>{notifications.length}</strong>
              <span>queued notifications</span>
            </div>
          </div>
          <div className="timeline-list">
            {notifications.slice(-5).reverse().map((item, index) => (
              <div className="stack-item" key={`${item.subject}-${index}`}>
                <div>
                  <p className="stack-title">{item.subject}</p>
                  <p className="stack-sub">{item.body}</p>
                </div>
                <span>{item.channel}</span>
              </div>
            ))}
          </div>
        </article>
      </section>
    </div>
  );
}