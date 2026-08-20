from sqlalchemy.schema import CreateSchema
from sqlalchemy.sql import text, select, insert


async def initialize_db(conn):
	await conn.execute(CreateSchema("settings", if_not_exists=True))

	await conn.execute(text("""\
		CREATE TABLE IF NOT EXISTS settings.banned_ips(
			address INET PRIMARY KEY,
			ban_date TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
			reason TEXT DEFAULT ''
	);"""))

	await conn.execute(text("""\
		CREATE TABLE IF NOT EXISTS users.jtis(
			id UUID REFERENCES users.users(id) ON DELETE CASCADE,
			jti UUID UNIQUE NOT NULL,
			PRIMARY KEY(id, jti)
		);
	"""))
