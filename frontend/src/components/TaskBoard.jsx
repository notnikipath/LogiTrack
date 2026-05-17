import React from "react";

export function TaskBoard({ routes }) {
  const primaryRoute = routes?.[0];

  if (!primaryRoute) {
    return <div className="empty-board">Маршрут пока не рассчитан. Запусти workflow назначения рейса, чтобы увидеть точки и ETA.</div>;
  }

  return (
    <section className="route-lane">
      {(primaryRoute.waypoints || []).map((waypoint) => (
        <article className="route-stop" key={waypoint.waypoint_id}>
          <p className="lesson-type">Точка {waypoint.sequence}</p>
          <h4>{waypoint.location}</h4>
          <div className="lesson-meta">
            <span>{new Date(waypoint.eta).toLocaleString()}</span>
            <span>{waypoint.stop_minutes || 0} min stop</span>
          </div>
        </article>
      ))}
    </section>
  );
}