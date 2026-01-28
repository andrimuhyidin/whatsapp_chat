# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

"""
Performance tracking functions for WhatsApp Chat agents.
"""

import frappe
from frappe import _
from frappe.utils import nowdatetime, getdate, time_diff_in_seconds, today
from typing import Optional
import json


def log_chat_assigned(contact_name: str, agent: str):
	"""
	Log when a chat is assigned to an agent.
	
	Args:
		contact_name: Name of the WhatsApp Contact
		agent: User ID of the agent
	"""
	try:
		# Store assignment time in contact doc or cache
		cache_key = f"chat_assigned:{contact_name}"
		frappe.cache.set(cache_key, {
			"agent": agent,
			"assigned_at": str(nowdatetime())
		}, expires_in_sec=86400 * 7)  # Keep for 7 days
		
	except Exception as e:
		frappe.log_error(f"Error logging chat assignment: {str(e)}", "Performance Tracker")


def log_first_response(contact_name: str, agent: str):
	"""
	Log when agent sends first response to a chat.
	
	Args:
		contact_name: Name of the WhatsApp Contact
		agent: User ID of the agent
	"""
	try:
		cache_key = f"chat_assigned:{contact_name}"
		assignment_data = frappe.cache.get(cache_key)
		
		if not assignment_data:
			return
		
		assigned_at = frappe.utils.get_datetime(assignment_data.get("assigned_at"))
		response_time = time_diff_in_seconds(nowdatetime(), assigned_at)
		
		# Store first response time
		response_key = f"first_response:{contact_name}"
		frappe.cache.set(response_key, {
			"agent": agent,
			"response_time_seconds": response_time,
			"responded_at": str(nowdatetime())
		}, expires_in_sec=86400 * 7)
		
		# Update daily metrics
		_update_agent_metric(agent, "first_response_times", response_time)
		
	except Exception as e:
		frappe.log_error(f"Error logging first response: {str(e)}", "Performance Tracker")


def log_chat_resolved(contact_name: str, agent: str):
	"""
	Log when a chat is resolved.
	
	Args:
		contact_name: Name of the WhatsApp Contact
		agent: User ID of the agent
	"""
	try:
		cache_key = f"chat_assigned:{contact_name}"
		assignment_data = frappe.cache.get(cache_key)
		
		if assignment_data:
			assigned_at = frappe.utils.get_datetime(assignment_data.get("assigned_at"))
			resolution_time = time_diff_in_seconds(nowdatetime(), assigned_at)
			
			# Update daily metrics
			_update_agent_metric(agent, "resolution_times", resolution_time)
			_increment_agent_counter(agent, "chats_resolved")
		
		# Clear cache
		frappe.cache.delete(cache_key)
		frappe.cache.delete(f"first_response:{contact_name}")
		
	except Exception as e:
		frappe.log_error(f"Error logging chat resolution: {str(e)}", "Performance Tracker")


def _update_agent_metric(agent: str, metric_name: str, value: float):
	"""Update agent metric in cache for daily aggregation."""
	cache_key = f"agent_metrics:{agent}:{today()}"
	metrics = frappe.cache.get(cache_key) or {}
	
	if metric_name not in metrics:
		metrics[metric_name] = []
	
	metrics[metric_name].append(value)
	frappe.cache.set(cache_key, metrics, expires_in_sec=86400 * 2)


def _increment_agent_counter(agent: str, counter_name: str):
	"""Increment agent counter in cache."""
	cache_key = f"agent_counters:{agent}:{today()}"
	counters = frappe.cache.get(cache_key) or {}
	
	counters[counter_name] = counters.get(counter_name, 0) + 1
	frappe.cache.set(cache_key, counters, expires_in_sec=86400 * 2)


def aggregate_daily_metrics():
	"""
	Daily job to aggregate agent performance metrics.
	
	Creates Agent Performance Log records from cached data.
	"""
	from frappe.utils import add_days
	
	# Get yesterday's date
	yesterday = add_days(today(), -1)
	
	# Get all agents
	agents = frappe.get_all(
		"WhatsApp Agent Queue",
		fields=["agent"]
	)
	
	for agent_record in agents:
		agent = agent_record.agent
		
		try:
			# Get cached metrics
			metrics_key = f"agent_metrics:{agent}:{yesterday}"
			counters_key = f"agent_counters:{agent}:{yesterday}"
			
			metrics = frappe.cache.get(metrics_key) or {}
			counters = frappe.cache.get(counters_key) or {}
			
			# Calculate averages
			first_response_times = metrics.get("first_response_times", [])
			resolution_times = metrics.get("resolution_times", [])
			
			avg_first_response = (
				sum(first_response_times) / len(first_response_times)
				if first_response_times else 0
			)
			avg_resolution = (
				sum(resolution_times) / len(resolution_times)
				if resolution_times else 0
			)
			
			# Get chat counts from database
			chats_handled = frappe.db.count(
				"WhatsApp Contact",
				{
					"assigned_agent": agent,
					"modified": [">=", yesterday],
					"modified": ["<", today()]
				}
			)
			
			chats_resolved = counters.get("chats_resolved", 0)
			
			# Check if log already exists
			existing = frappe.db.exists(
				"Agent Performance Log",
				{"agent": agent, "date": yesterday, "period_type": "Daily"}
			)
			
			if existing:
				# Update existing
				frappe.db.set_value("Agent Performance Log", existing, {
					"chats_handled": chats_handled,
					"chats_resolved": chats_resolved,
					"avg_first_response_seconds": avg_first_response,
					"avg_resolution_time_seconds": avg_resolution,
					"first_response_times": json.dumps(first_response_times),
					"resolution_times": json.dumps(resolution_times)
				})
			else:
				# Create new log
				frappe.get_doc({
					"doctype": "Agent Performance Log",
					"agent": agent,
					"date": yesterday,
					"period_type": "Daily",
					"chats_handled": chats_handled,
					"chats_resolved": chats_resolved,
					"avg_first_response_seconds": avg_first_response,
					"avg_resolution_time_seconds": avg_resolution,
					"first_response_times": json.dumps(first_response_times),
					"resolution_times": json.dumps(resolution_times)
				}).insert(ignore_permissions=True)
			
			# Clear cache
			frappe.cache.delete(metrics_key)
			frappe.cache.delete(counters_key)
			
		except Exception as e:
			frappe.log_error(
				f"Error aggregating metrics for {agent}: {str(e)}",
				"Agent Metrics Aggregation"
			)
	
	frappe.db.commit()


def get_realtime_agent_stats(agent: str) -> dict:
	"""
	Get real-time statistics for an agent.
	
	Args:
		agent: User ID of the agent
		
	Returns:
		Dictionary with current stats
	"""
	# Current active chats
	active_chats = frappe.db.count(
		"WhatsApp Contact",
		{
			"assigned_agent": agent,
			"chat_status": ["in", ["Open", "In Progress"]]
		}
	)
	
	# Today's resolved
	today_resolved = frappe.db.count(
		"WhatsApp Contact",
		{
			"assigned_agent": agent,
			"chat_status": "Resolved",
			"modified": [">=", today()]
		}
	)
	
	# Queue status
	queue = frappe.db.get_value(
		"WhatsApp Agent Queue",
		{"agent": agent},
		["status", "current_load", "max_capacity"],
		as_dict=True
	) or {}
	
	return {
		"active_chats": active_chats,
		"today_resolved": today_resolved,
		"queue_status": queue.get("status", "Unknown"),
		"current_load": queue.get("current_load", 0),
		"max_capacity": queue.get("max_capacity", 10)
	}
