# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
API endpoints for agent performance metrics.
"""

import frappe
from frappe import _
from frappe.utils import today, add_days, getdate
from whatsapp_chat.performance.tracker import get_realtime_agent_stats


@frappe.whitelist()
def get_agent_stats(agent: str = None, days: int = 30):
	"""
	Get performance statistics for an agent.
	
	Args:
		agent: User ID (defaults to current user)
		days: Number of days to analyze
		
	Returns:
		Dictionary with agent statistics
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	if not agent:
		agent = frappe.session.user
	
	# Check permission - agents can see their own stats
	if agent != frappe.session.user:
		if not frappe.has_permission("Agent Performance Log", "read"):
			frappe.throw(_("Permission denied"))
	
	start_date = add_days(today(), -days)
	
	# Get aggregated stats from performance logs
	stats = frappe.db.sql("""
		SELECT
			SUM(chats_handled) as total_chats_handled,
			SUM(chats_resolved) as total_chats_resolved,
			AVG(avg_first_response_seconds) as avg_first_response,
			AVG(avg_resolution_time_seconds) as avg_resolution_time,
			COUNT(*) as days_active
		FROM `tabAgent Performance Log`
		WHERE agent = %s
		AND date >= %s
		AND period_type = 'Daily'
	""", (agent, start_date), as_dict=True)[0]
	
	# Get daily breakdown
	daily_stats = frappe.get_all(
		"Agent Performance Log",
		filters={
			"agent": agent,
			"date": [">=", start_date],
			"period_type": "Daily"
		},
		fields=[
			"date", "chats_handled", "chats_resolved",
			"avg_first_response_seconds", "avg_resolution_time_seconds"
		],
		order_by="date asc"
	)
	
	# Get real-time stats
	realtime = get_realtime_agent_stats(agent)
	
	# Calculate resolution rate
	total_handled = stats.get("total_chats_handled") or 0
	total_resolved = stats.get("total_chats_resolved") or 0
	resolution_rate = (total_resolved / total_handled * 100) if total_handled > 0 else 0
	
	return {
		"agent": agent,
		"period_days": days,
		"summary": {
			"total_chats_handled": total_handled,
			"total_chats_resolved": total_resolved,
			"resolution_rate": round(resolution_rate, 2),
			"avg_first_response_seconds": round(stats.get("avg_first_response") or 0, 2),
			"avg_resolution_time_seconds": round(stats.get("avg_resolution_time") or 0, 2),
			"days_active": stats.get("days_active") or 0
		},
		"realtime": realtime,
		"daily": daily_stats
	}


@frappe.whitelist()
def get_team_stats(days: int = 30):
	"""
	Get team-wide performance statistics.
	
	Args:
		days: Number of days to analyze
		
	Returns:
		Dictionary with team statistics
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	if not frappe.has_permission("Agent Performance Log", "read"):
		frappe.throw(_("Permission denied"))
	
	start_date = add_days(today(), -days)
	
	# Get team totals
	team_stats = frappe.db.sql("""
		SELECT
			SUM(chats_handled) as total_chats_handled,
			SUM(chats_resolved) as total_chats_resolved,
			AVG(avg_first_response_seconds) as avg_first_response,
			AVG(avg_resolution_time_seconds) as avg_resolution_time,
			COUNT(DISTINCT agent) as active_agents
		FROM `tabAgent Performance Log`
		WHERE date >= %s
		AND period_type = 'Daily'
	""", (start_date,), as_dict=True)[0]
	
	# Get per-agent stats
	agent_stats = frappe.db.sql("""
		SELECT
			agent,
			SUM(chats_handled) as chats_handled,
			SUM(chats_resolved) as chats_resolved,
			AVG(avg_first_response_seconds) as avg_first_response,
			AVG(avg_resolution_time_seconds) as avg_resolution_time
		FROM `tabAgent Performance Log`
		WHERE date >= %s
		AND period_type = 'Daily'
		GROUP BY agent
		ORDER BY chats_resolved DESC
	""", (start_date,), as_dict=True)
	
	# Enhance with user info
	for stat in agent_stats:
		user = frappe.get_value("User", stat.agent, ["full_name", "user_image"])
		stat["full_name"] = user[0] if user else stat.agent
		stat["user_image"] = user[1] if user else None
		
		# Calculate resolution rate
		handled = stat.get("chats_handled") or 0
		resolved = stat.get("chats_resolved") or 0
		stat["resolution_rate"] = round((resolved / handled * 100) if handled > 0 else 0, 2)
	
	# Daily trend
	daily_trend = frappe.db.sql("""
		SELECT
			date,
			SUM(chats_handled) as chats_handled,
			SUM(chats_resolved) as chats_resolved,
			AVG(avg_first_response_seconds) as avg_first_response
		FROM `tabAgent Performance Log`
		WHERE date >= %s
		AND period_type = 'Daily'
		GROUP BY date
		ORDER BY date ASC
	""", (start_date,), as_dict=True)
	
	return {
		"period_days": days,
		"summary": {
			"total_chats_handled": team_stats.get("total_chats_handled") or 0,
			"total_chats_resolved": team_stats.get("total_chats_resolved") or 0,
			"avg_first_response_seconds": round(team_stats.get("avg_first_response") or 0, 2),
			"avg_resolution_time_seconds": round(team_stats.get("avg_resolution_time") or 0, 2),
			"active_agents": team_stats.get("active_agents") or 0
		},
		"agents": agent_stats,
		"daily_trend": daily_trend
	}


@frappe.whitelist()
def get_agent_leaderboard(days: int = 7, metric: str = "chats_resolved"):
	"""
	Get agent leaderboard by specified metric.
	
	Args:
		days: Number of days to analyze
		metric: Metric to rank by (chats_resolved, avg_resolution_time_seconds, etc.)
		
	Returns:
		List of agents ranked by metric
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Authentication required"))
	
	start_date = add_days(today(), -days)
	
	# Validate metric
	valid_metrics = [
		"chats_resolved", "chats_handled",
		"avg_first_response_seconds", "avg_resolution_time_seconds"
	]
	
	if metric not in valid_metrics:
		metric = "chats_resolved"
	
	# Determine sort order (lower is better for time metrics)
	order = "ASC" if "seconds" in metric else "DESC"
	agg_func = "AVG" if "avg" in metric else "SUM"
	
	leaderboard = frappe.db.sql(f"""
		SELECT
			agent,
			{agg_func}({metric}) as metric_value,
			SUM(chats_resolved) as chats_resolved,
			SUM(chats_handled) as chats_handled
		FROM `tabAgent Performance Log`
		WHERE date >= %s
		AND period_type = 'Daily'
		GROUP BY agent
		HAVING metric_value > 0
		ORDER BY metric_value {order}
		LIMIT 10
	""", (start_date,), as_dict=True)
	
	# Enhance with user info and rank
	for i, entry in enumerate(leaderboard):
		entry["rank"] = i + 1
		user = frappe.get_value("User", entry.agent, ["full_name", "user_image"])
		entry["full_name"] = user[0] if user else entry.agent
		entry["user_image"] = user[1] if user else None
	
	return {
		"metric": metric,
		"period_days": days,
		"leaderboard": leaderboard
	}
