import frappe
from frappe import _
from frappe.utils import add_to_date, today
from frappe.utils.user import get_users_with_role
from collections import defaultdict


def send_birthday_reminders():
    _send_employee_reminders("birthday")


def send_work_anniversary_reminders():
    _send_employee_reminders("work_anniversary")


def _send_employee_reminders(event_type):
    if event_type == "birthday":
        condition_column = "date_of_birth"
    elif event_type == "work_anniversary":
        condition_column = "date_of_joining"
    else:
        return

    to_send = int(
        frappe.db.get_single_value("HR Settings", f"send_{event_type}_reminders")
    )
    if not to_send:
        return

    today_date = today()
    tomorrow_date = add_to_date(today_date, days=1)

    employees_today = frappe.db.sql(
        f"""
        SELECT `employee_name` AS 'name', `company`
        FROM `tabEmployee`
        WHERE
            DAY({condition_column}) = DAY(%(today)s)
        AND MONTH({condition_column}) = MONTH(%(today)s)
        AND YEAR({condition_column}) < YEAR(%(today)s)
        AND `status` = 'Active'
        """,
        dict(today=today_date),
        as_dict=1,
    )

    employees_tomorrow = frappe.db.sql(
        f"""
        SELECT `employee_name` AS 'name', `company`
        FROM `tabEmployee`
        WHERE
            DAY({condition_column}) = DAY(%(tomorrow)s)
        AND MONTH({condition_column}) = MONTH(%(tomorrow)s)
        AND YEAR({condition_column}) < YEAR(%(tomorrow)s)
        AND `status` = 'Active'
        """,
        dict(tomorrow=tomorrow_date),
        as_dict=1,
    )

    grouped_today = defaultdict(list)
    for emp in employees_today:
        grouped_today[emp["company"]].append(emp["name"])

    grouped_tomorrow = defaultdict(list)
    for emp in employees_tomorrow:
        grouped_tomorrow[emp["company"]].append(emp["name"])

    hr_users = _get_hr_users()

    if not hr_users:
        return

    today_str = today()
    for company, names in grouped_today.items():
        subject = _get_subject(event_type, names)
        for user in hr_users:
            if not _notification_exists(user, subject, today_str):
                _create_notification_log(for_user=user, subject=subject, link="/app/employee")

    for company, names in grouped_tomorrow.items():
        subject = _get_subject(event_type, names, days_before=1)
        for user in hr_users:
            if not _notification_exists(user, subject, today_str):
                _create_notification_log(for_user=user, subject=subject, link="/app/employee")


def _get_subject(event_type, employee_names, days_before=0):
    names_text = ", ".join(employee_names)
    if days_before == 1:
        if event_type == "birthday":
            return _("🎂 Tomorrow's Birthdays: {0}").format(names_text)
        return _("🎉 Tomorrow's Work Anniversaries: {0}").format(names_text)
    if event_type == "birthday":
        return _("🎂 Today's Birthdays: {0}").format(names_text)
    return _("🎉 Today's Work Anniversaries: {0}").format(names_text)


def _get_hr_users():
    users = set()
    for role in ["HR User", "HR Manager"]:
        users.update(get_users_with_role(role))
    return [u for u in users if u != "Administrator"]


def _create_notification_log(*, for_user, subject, link=None):
    notification = frappe.new_doc("Notification Log")
    notification.subject = subject
    notification.for_user = for_user
    notification.type = "Alert"
    notification.document_type = "Employee"
    notification.from_user = "Administrator"
    if link:
        notification.link = link
    notification.insert(ignore_permissions=True)


def _notification_exists(for_user, subject, date):
    return frappe.db.exists("Notification Log", {
        "for_user": for_user,
        "subject": subject,
        "creation": ["like", f"{date}%"],
    })
