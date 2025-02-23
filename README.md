# flaskApp-sqlite-to-postgres-migration
This repo rescribes step by step process  of migration  sqlite db to postresql

## Prerequisites

* **PostgreSQL Installed and Configured:** Ensure you have a PostgreSQL server running and accessible.
* **psql:** The PostgreSQL command-line tool.
* **sqlite3:** The SQLite command-line tool.
* **pgloader (Recommended):** A powerful tool for data migration. Install instructions can be found [here](https://pgloader.io/).
* **Python (Optional):** If you need to write custom scripts for data transformation.

## Migration Steps

1.  **Schema Extraction from SQLite:**

    * Use the `.schema` command in the `sqlite3` shell to extract the table schemas.
    * Save the output to a `.sql` file (e.g., `sqlite_schema.sql`).

    ```bash
    sqlite3 your_sqlite_database.db ".schema" > sqlite_schema.sql
    ```

2.  **Schema Conversion to PostgreSQL:**

    * Manually or using a script, convert the SQLite schema to PostgreSQL syntax.
    * Pay close attention to data type differences (e.g., `INTEGER` in SQLite vs. `SERIAL` or `BIGINT` in PostgreSQL).
    * Address any SQLite-specific features that don't have direct PostgreSQL equivalents.
    * Example changes:
        * `INTEGER PRIMARY KEY AUTOINCREMENT` -> `SERIAL PRIMARY KEY` or `BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY`
        * Adjusting data types to match postgres.
    * Save the converted schema to a new `.sql` file (e.g., `postgres_schema.sql`).

    ```sql
    -- Example postgres_schema.sql (after conversion)
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        username VARCHAR(255) NOT NULL,
        email VARCHAR(255) UNIQUE,
        created_at TIMESTAMP DEFAULT NOW()
    );

    CREATE TABLE posts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id),
        title TEXT,
        content TEXT,
        published_at TIMESTAMP
    );

    -- ... other tables
    ```

3.  **Create Tables in PostgreSQL:**

    * Connect to your PostgreSQL database using `psql`.
    * Execute the `postgres_schema.sql` file to create the tables.

    ```bash
    psql -U your_user -d your_database -f postgres_schema.sql
    ```

4.  **Data Export from SQLite:**

    * Export the data from each SQLite table to CSV files.
    * Example for the users table.

    ```bash
    sqlite3 -header -csv your_sqlite_database.db "SELECT * FROM users;" > users.csv
    sqlite3 -header -csv your_sqlite_database.db "SELECT * FROM posts;" > posts.csv
    #Repeat for all tables.
    ```

5.  **Data Import into PostgreSQL (using pgloader - Recommended):**

    * pgloader simplifies the migration process.
    * Create a pgloader script (e.g., `migrate.load`).

    ```lisp
    LOAD CSV
        FROM 'users.csv'
        INTO postgresql://your_user@localhost/your_database?users (id, username, email, created_at)
        WITH truncate,
             fields escaped by double-quote,
             fields terminated by ','
             skip header = 1
    ;
    LOAD CSV
        FROM 'posts.csv'
        INTO postgresql://your_user@localhost/your_database?posts (id, user_id, title, content, published_at)
        WITH truncate,
             fields escaped by double-quote,
             fields terminated by ','
             skip header = 1
    ;
    --Add all tables.
    ```

    * Run pgloader with your script.

    ```bash
    pgloader migrate.load
    ```

6.  **Data Import into PostgreSQL (using psql and \copy - Alternative):**

    * If you don't use pgloader, you can use `\copy` within `psql`.
    * Connect to your PostgreSQL database using `psql`.
    * Import each CSV file into the corresponding table.

    ```sql
    \copy users(id, username, email, created_at) FROM 'users.csv' CSV HEADER;
    \copy posts(id, user_id, title, content, published_at) FROM 'posts.csv' CSV HEADER;
    --Repeat for all tables.
    ```

7.  **Data Validation:**

    * Compare the data in the SQLite and PostgreSQL databases to ensure a successful migration.
    * Run queries to check data integrity and consistency.
    * Compare row counts.
    * Compare specific data values.

8.  **Index and Constraint Creation (if needed):**

    * If your original sqlite database had indexes that weren't included in the schema conversion, add them now.
    * Add any foreign key constraints that are needed, if they were not created earlier.

    ```sql
    CREATE INDEX idx_users_username ON users(username);
    ALTER TABLE posts ADD CONSTRAINT fk_user_id FOREIGN KEY (user_id) REFERENCES users(id);
    ```
