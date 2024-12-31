"""Functions for interacting with postgres database"""
from configparser import ConfigParser, NoSectionError
from os import PathLike, getenv
from pathlib import Path
from psycopg import connect, sql
from psycopg.connection import Connection
from re import sub
from shutil import copy
from uuid import UUID


__all__ = ["initialize_database", "modify_database_configuration", "get_database_connection_string", "Database"]


def get_database_connection_string(configuration_file:PathLike[str] = None, section:str = "Postgres") -> str:
	def get_value(environment_name:str, default_value:str, ini_params:dict[str, str], ini_name:str=None) -> str:
		value = getenv(environment_name, default_value)
		value = ini_params.get(ini_name, value)
		return value

	ini_params = {}
	if configuration_file is not None:
		parser = ConfigParser()
		parser.read(configuration_file)

		if not parser.has_section(section):
			raise NoSectionError(section)

		ini_params = {key: value for key, value in parser.items(section)}

	username = get_value("POSTGRES_USER", "exsclaim", ini_params, "user")
	password = get_value("POSTGRES_PASSWORD", "exsclaimtest!9700", ini_params, "password")
	port = get_value("POSTGRES_PORT", "5432", ini_params, "port")
	database_name = get_value("POSTGRES_DB", "exsclaim", ini_params, "database")
	host = get_value("POSTGRES_HOST", "localhost", ini_params, "host")

	# db is one of the aliases given through Docker Compose
	url = f"postgres://{username}:{password}@{host}:{port}/{database_name}"
	return url


def initialize_database(db_connection_string:str) -> None:
	with connect(db_connection_string, autocommit=True) as conn:
		cursor = conn.cursor()

		with open(Path(__file__).parent / "setup.sql", "r") as setup:
			cursor.execute(setup.read())

		cursor.close()


def modify_database_configuration(config_path:str):
	"""Alter database.ini to store configuration for future runs

	Args:
		config_path (str): path to .ini file
	Modifies:
		database.ini
	"""
	current_file = Path(__file__).resolve()
	database_ini = current_file.parent / "database.ini"
	config_path = Path(config_path)
	copy(config_path, database_ini)


class Database:
	def __init__(self, name, configuration_file=None):
		db_url = get_database_connection_string(configuration_file, name)
		# initialize_database(db_url)

		self.connection = connect(db_url)
		self.cursor = self.connection.cursor()

	def query_many(self, sql, data):
		self.cursor.executemany(sql, data)

	def copy_from(self, file:PathLike[str], schema:str, table:str, run_id:str | UUID, app_name:str="results"):
		temp_name = f"{table}_temp"
		# Creates a temporary table to copy data into. We then use copy to populate the table with a csv contents.\
		# Then we insert temp table contents into the real table, ignoring conflicts. We use copy because it is faster \
		# than insert, but create the temporary table to mimic a nonexistent "COPY... ON CONFLICT" command

		temp_id = sql.Identifier(temp_name)
		table_id = sql.Identifier(table)
		schema_id = sql.Identifier(schema)

		query = sql.SQL("CREATE TEMPORARY TABLE {} (LIKE {}.{} INCLUDING ALL) ON COMMIT DROP;").format(temp_id, schema_id, table_id)
		self.cursor.execute(query)

		with open(file, "r", encoding="utf-8") as csv_file:
			with self.cursor.copy(sql.SQL("COPY {} FROM STDIN (FORMAT CSV, DELIMITER ',', QUOTE '\"')").format(temp_id)) as copy:
				while data := csv_file.readline():
					copy.write(f"{run_id},{data}")

		self.cursor.execute(sql.SQL("INSERT INTO {}.{} SELECT * FROM {} ON CONFLICT DO NOTHING;").format(schema_id, table_id, temp_id))

	def close(self):
		self.cursor.close()
		self.connection.close()

	def __enter__(self):
		return self

	def __exit__(self, exception_type, exception_value, exception_traceback):
		self.close()

	def commit(self):
		self.connection.commit()
