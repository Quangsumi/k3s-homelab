# PostgreSQL Security Model

Each application connects to PostgreSQL with its own user/role/identity and controls only its own database.

| Identity | Access |
| --- | --- |
| `litellm_user` | Owns and manages only the `litellm` database |
| `normal_ass_note_user` | Owns and manages only the `normal-ass-note` database |
| `postgres_exporter` | Reads monitoring statistics through `pg_monitor` |
| `quangsumi` | Superuser used only for administration |

Each database does not accept connections from PostgreSQL's general `PUBLIC` role. Access is granted explicitly to the matching application identity.
```
# default
litellm_user ──> litellm              allowed
random_user ───> litellm              also allowed to enter

# explicitly grant
REVOKE CONNECT ON DATABASE litellm FROM PUBLIC;
GRANT CONNECT ON DATABASE litellm TO litellm_user;

litellm_user -> litellm           allowed
random_user --> litellm           rejected
```