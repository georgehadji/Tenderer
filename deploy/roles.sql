-- Database roles (docs/architecture.md §10.2). Run as the owner of the tables (the `migrator` role that runs
-- `manage.py migrate`), after every migration, in the application database. The app connects as tenderer_app.
-- Create the role once, with its password from the secret store:  CREATE ROLE tenderer_app LOGIN PASSWORD '...';

REVOKE ALL ON ALL TABLES IN SCHEMA public FROM tenderer_app;
REVOKE ALL ON ALL SEQUENCES IN SCHEMA public FROM tenderer_app;
GRANT USAGE ON SCHEMA public TO tenderer_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO tenderer_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tenderer_app;
-- The audit log is append-only for the app: no UPDATE, DELETE or TRUNCATE (a trigger also refuses them).
REVOKE UPDATE, DELETE, TRUNCATE ON audit_auditevent FROM tenderer_app;
