	frappe.query_reports["Employee Checkin and Overtime"] = {
		filters: [
			{
				fieldname: "from_date",
				label: __("From Date"),
				fieldtype: "Date",
				reqd: 1,
				default: frappe.datetime.month_start(),
			},
			{
				fieldname: "to_date",
				label: __("To Date"),
				fieldtype: "Date",
				reqd: 1,
				default: frappe.datetime.month_end(),
			},
			{
				fieldname: "employee",
				label: __("Employee"),
				fieldtype: "Link",
				options: "Employee",
			},
			{
				fieldname: "department",
				label: __("Department"),
				fieldtype: "Link",
				options: "Department",
			},
		],

		formatter(value, row, column, data, default_formatter) {
			value = default_formatter(value, row, column, data);

			if (column.fieldname === "overtime_amount" && data?.overtime_amount > 0) {
				value = `<span style="color:#28a745;font-weight:bold">${value}</span>`;
			}

			if (column.fieldname === "late_amount" && data?.late_amount < 0) {
				value = `<span style="color:#dc3545;font-weight:bold">${value}</span>`;
			}

			if (column.fieldname === "actual_overtime" && data?.actual_overtime) {
				const params = new URLSearchParams({
					employee: data.employee,
					overtime_date: data.date,
					overtime_time: data.actual_overtime,
					overtime_type: "Hourly",
				});
				if (data?.late_amount) {
					params.append("adjust_amount", data.late_amount);
				}
				const link = `/app/overtime-entry/new-overtime-entry?${params.toString()}`;
				value = `<a href="${link}" style="color:red;font-weight:bold;text-decoration:underline">${value}</a>`;
			}

			return value;
		},
	};
