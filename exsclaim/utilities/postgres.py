"""Functions for interacting with postgres database"""
from configparser import ConfigParser
from shutil import copy
from pathlib import Path
from psycopg import connect, sql
from psycopg.connection import Connection


__ALL__ = ["initialize_database", "modify_database_configuration", "Database"]


def initialize_database(configuration_file):
    parser = ConfigParser()
    parser.read(configuration_file)
    # connect to default postgres database, create exsclaim user
    conn = connect(**parser["postgres"], autocommit=True)
    cursor = conn.cursor()

    create_query = sql.SQL("CREATE USER {username} WITH PASSWORD {password};").format(
        username=sql.Identifier(parser["exsclaim"]["user"]), password=sql.Placeholder()
    )
    alter_query = sql.SQL("ALTER USER {username} CREATEDB;").format(
        username=sql.Identifier(parser["exsclaim"]["user"])
    )
    try:
        cursor.execute(create_query, (parser["exsclaim"]["password"],))
        cursor.execute(alter_query)
    except Exception as e:
        print(e)

    cursor.close()
    conn.close()

    # connect to postgres, create exsclaim database
    conn = connect(
        host=parser["postgres"]["host"],
        database=parser["postgres"]["database"],
        user=parser["exsclaim"]["user"],
        password=parser["exsclaim"].get("password", ""),
        autocommit=True
    )
    cursor = conn.cursor()
    try:
        cursor.execute("CREATE DATABASE exsclaim")
    except Exception as e:
        print(e)
    cursor.close()
    conn.close()


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
        initialize_database(configuration_file)

        if configuration_file is None:
            current_file = Path(__file__).resolve()
            configuration_file = current_file.parent / "database.ini"

        parser = ConfigParser()
        parser.read(configuration_file)

        db_params = {}
        if parser.has_section(name):
            db_params = {key: value for key, value in parser.items(name)}

        self.connection = connect(**db_params)
        self.cursor = self.connection.cursor()

    def query(self, sql, data=None):
        self.cursor.execute(sql, data)

    def query_many(self, sql, data):
        self.cursor.executemany(sql, data)
        # psycopg2.execute_values(self.cursor, sql, data) # TODO: Check if this is the right move from version 2

    def copy_from(self, file, table):
        app_name = "results"
        table_to_copy_command = {
            f"{app_name}_article": f"{app_name}_article_temp",
            f"{app_name}_figure": f"{app_name}_figure_temp",
            f"{app_name}_subfigure": f"{app_name}_subfigure_temp",
            f"{app_name}_scalebar": f"{app_name}_scalebar_temp",
            f"{app_name}_scalebarlabel": f"{app_name}_scalebarlabel_temp(text,x1,y1,x2,y2,label_confidence,"
                                         "box_confidence,nm,scale_bar_id)",
            f"{app_name}_subfigurelabel": f"{app_name}_subfigurelabel_temp(text,x1,y1,x2,y2,label_confidence,"
                                          "box_confidence,subfigure_id)"
        }

        temp_name = f"{table}_temp"
        # Creates a temporary table to copy data into. We then use copy to
        # populate the table with a csv contents. Then we insert temp table
        # contents into the real table, ignoring conflicts. We use copy
        # because it is faster than insert, but create the temporary table
        # to mimic a nonexistent "COPY... ON CONFLICT" command

        temp_id = sql.Identifier(temp_name)
        table_id = sql.Identifier(table)
        self.query(
            sql.SQL(
                "CREATE TEMPORARY TABLE {temp_id} (LIKE {table_id} INCLUDING ALL) ON COMMIT DROP;"
            ).format(temp_id=temp_id, table_id=table_id)
        )

        with open(file, "r", encoding="utf-8") as csv_file:
            self.cursor.copy_expert("COPY {} FROM STDIN CSV".format(table_to_copy_command[table]), csv_file)

        self.query(
            sql.SQL("INSERT INTO {table_id} SELECT * FROM {temp_id} ON CONFLICT DO NOTHING;").format(temp_id=temp_id, table_id=table_id)
        )

    def close(self):
        self.cursor.close()
        self.connection.close()

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, exception_traceback):
        self.close()

    def commit(self):
        self.connection.commit()
