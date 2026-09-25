# Written by hand: Django has no operation for triggers. The database refuses every UPDATE and DELETE of an audit
# event, whoever asks (docs/architecture.md §6.7). The app role also lacks the grants (deploy/roles.sql).

from django.db import migrations

FORWARD = """
CREATE FUNCTION audit_event_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_auditevent is append-only: % refused', TG_OP;
END
$$;
CREATE TRIGGER audit_event_append_only BEFORE UPDATE OR DELETE ON audit_auditevent
    FOR EACH ROW EXECUTE FUNCTION audit_event_append_only();
"""

BACKWARD = """
DROP TRIGGER audit_event_append_only ON audit_auditevent;
DROP FUNCTION audit_event_append_only();
"""


class Migration(migrations.Migration):

    dependencies = [("audit", "0001_initial")]

    operations = [migrations.RunSQL(FORWARD, BACKWARD)]
