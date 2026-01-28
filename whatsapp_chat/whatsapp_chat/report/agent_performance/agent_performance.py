# Copyright (c) 2026, Frappe Technologies and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import getdate, add_days, today


def execute(filters=None):
	columns = get_columns()
	data = get_data(filters)
	chart = get_chart(data)
	summary = get_summary(data)
	
	return columns, data, None, chart, summary


def get_columns():
	return [
		{
			"label": _("Agent"),
			"fieldname": "agent",
			"fieldtype": "Link",
			"options": "User",
			"width": 180
		},
		{
			"label": _("Agent Name"),
			"fieldname": "agent_name",
			"fieldtype": "Data",
			"width": 150
		},
		{
			"label": _("Chats Handled"),
			"fieldname": "chats_handled",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Chats Resolved"),
			"fieldname": "chats_resolved",
			"fieldtype": "Int",
			"width": 120
		},
		{
			"label": _("Resolution Rate (%)"),
			"fieldname": "resolution_rate",
			"fieldtype": "Percent",
			"width": 130
		},
		{
			"label": _("Avg First Response (min)"),
			"fieldname": "avg_first_response",
			"fieldtype": "Float",
			"precision": 1,
			"width": 160
		},
		{
			"label": _("Avg Resolution Time (min)"),
			"fieldname": "avg_resolution_time",
			"fieldtype": "Float",
			"precision": 1,
			"width": 170
		},
		{
			"label": _("Days Active"),
			"fieldname": "days_active",
			"fieldtype": "Int",
			"width": 100
		}
	]


def get_data(filters):
	conditions = get_conditions(filters)
	
	data = frappe.db.sql("""
		SELECT
			apl.agent,
			u.full_name as agent_name,
			SUM(apl.chats_handled) as chats_handled,
			SUM(apl.chats_resolved) as chats_resolved,
			AVG(apl.avg_first_response_seconds) / 60 as avg_first_response,
			AVG(apl.avg_resolution_time_seconds) / 60 as avg_resolution_time,
			COUNT(DISTINCT apl.date) as days_active
		FROM `tabAgent Performance Log` apl
		LEFT JOIN `tabUser` u ON apl.agent = u.name
		WHERE apl.period_type = 'Daily'
		{conditions}
		GROUP BY apl.agent
		ORDER BY chats_resolved DESC
	""".format(conditions=conditions), filters, as_dict=True)
	
	# Calculate resolution rate
	for row in data:
		handled = row.get("chats_handled") or 0
		resolved = row.get("chats_resolved") or 0
		row["resolution_rate"] = (resolved / handled * 100) if handled > 0 else 0
		
		# Round time values
		row["avg_first_response"] = round(row.get("avg_first_response") or 0, 1)
		row["avg_resolution_time"] = round(row.get("avg_resolution_time") or 0, 1)
	
	return data


def get_conditions(filters):
	conditions = []
	
	if filters.get("from_date"):
		conditions.append("AND apl.date >= %(from_date)s")
	
	if filters.get("to_date"):
		conditions.append("AND apl.date <= %(to_date)s")
	
	if filters.get("agent"):
		conditions.append("AND apl.agent = %(agent)s")
	
	return " ".join(conditions)


def get_chart(data):
	if not data:
		return None
	
	labels = [row.get("agent_name") or row.get("agent") for row in data[:10]]
	resolved_values = [row.get("chats_resolved") or 0 for row in data[:10]]
	handled_values = [row.get("chats_handled") or 0 for row in data[:10]]
	
	return {
		"data": {
			"labels": labels,
			"datasets": [
				{
					"name": _("Chats Resolved"),
					"values": resolved_values
				},
				{
					"name": _("Chats Handled"),
					"values": handled_values
				}
			]
		},
		"type": "bar",
		"colors": ["#5e64ff", "#98d85b"],
		"barOptions": {
			"stacked": False
		}
	}


def get_summary(data):
	if not data:
		return []
	
	total_handled = sum(row.get("chats_handled") or 0 for row in data)
	total_resolved = sum(row.get("chats_resolved") or 0 for row in data)
	avg_resolution_rate = (total_resolved / total_handled * 100) if total_handled > 0 else 0
	
	avg_first_response = sum(row.get("avg_first_response") or 0 for row in data) / len(data) if data else 0
	avg_resolution_time = sum(row.get("avg_resolution_time") or 0 for row in data) / len(data) if data else 0
	
	return [
		{
			"value": total_handled,
			"label": _("Total Chats Handled"),
			"datatype": "Int"
		},
		{
			"value": total_resolved,
			"label": _("Total Chats Resolved"),
			"datatype": "Int"
		},
		{
			"value": round(avg_resolution_rate, 1),
			"label": _("Avg Resolution Rate (%)"),
			"datatype": "Percent"
		},
		{
			"value": round(avg_first_response, 1),
			"label": _("Avg First Response (min)"),
			"datatype": "Float"
		},
		{
			"value": round(avg_resolution_time, 1),
			"label": _("Avg Resolution Time (min)"),
			"datatype": "Float"
		}
	]
