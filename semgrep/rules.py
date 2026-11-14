# ai-generated: 100% - wrote Semgrep positive and negative fixtures for the service-specific rules in rules.yml
def broad_error_handler():
    # ruleid: svcdesk.generic-exception-catch
    try:
        return "request"
    except Exception:
        return "error"


def specific_error_handler():
    # ok: svcdesk.generic-exception-catch
    try:
        return "request"
    except ValueError:
        return "error"


def unsafe_query(cursor, user_value):
    # ruleid: svcdesk.sql-query-concatenation
    cursor.execute("SELECT * FROM tickets WHERE id = '" + user_value + "'")


def parameterized_query(cursor, ticket_id):
    # ok: svcdesk.sql-query-concatenation
    cursor.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,))
