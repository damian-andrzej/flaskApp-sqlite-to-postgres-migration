# flaskApp-sqlite-to-postgres-migration
This repo describes step by step process of sqlite db migration to postresql

## Prerequisites

* **PostgreSQL Installed and Configured:** Ensure you have a PostgreSQL server running and accessible.
* **psql:** The PostgreSQL command-line tool.
* **sqlite3:** The SQLite command-line tool.
* **pgloader (Recommended):** A powerful tool for data migration. Install instructions can be found [here](https://pgloader.io/).
* **Python (Optional):** If you need to write custom scripts for data transformation.

Table of content:
1. Migration steps
2. Database config
3. App config
4. BONUS: move app on 2 docker containers

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

## 2. Database config

   Config for Flask app shows how app comunicates with db, path for database and the database structure itself. We need adjust it for new PostgreSQL solution.
Firstly lets provision database 'flask_db', we dont need any structure only empty table with user that is allowed to create tables and insert records

config.py
```python
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your_secret_key_here'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///site.db'  # SQLite database for simplicity
    SQLALCHEMY_TRACK_MODIFICATIONS = False
```
New path to postgresql may differ but still uses SQLALCHEMY so only DB URI needs to be changed
                   SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@localhost/database_name

```python
SQLALCHEMY_DATABASE_URI ='postgresql://postgres:YOUR_PASSWORD@localhost:5432/flask_db'
```

Fantastic point is that SQLite and PostgreSQL communicates with the app in very similar way and the model is almost identical.
Model.py file including User class works for both database solution

models.py
```python
from flask_sqlalchemy import SQLAlchemy
import bcrypt
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    #email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

    def __repr__(self):
        return f"User('{self.username})"
```

## 3. App config

Flask application needs to communicate with a PostgreSQL database, it essentially involves these key steps:

- psycopg2/psycopg3:
  - The most common and recommended way for Python to interact with PostgreSQL is through the psycopg2 or the newer psycopg3 library. These are PostgreSQL adapters for Python.
  - They allow your Python code to execute SQL queries, retrieve data, and manage database connections

- Your Flask application will need to establish a connection to the PostgreSQL database. This involves providing the database's connection details, such as:
Host (e.g., "localhost" or the database server's IP address)
  - Database name
  - Username
  - Password
  - Port (usually 5432)

### SQL operations

 1. *Registration process*

    Dont need to strugle much as ORM driver makes most work for us. We need only to point specific method to execute.

```python
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data,password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Your account has been created! You can now log in.', 'success')
        return redirect(url_for('login'))  # Redirect to login page in a real app
    return render_template('register.html', form=form)
```

2. *Login*

```python
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        #if username == USERNAME and password == PASSWORD:
        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            session['username'] = username  # Store username in session
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')

    return render_template('login.html')
 ```

3. *List users*

```python
def list_users():
    # Query all users from the database
    users = User.query.all()

    # Pass the users list to the template
    return render_template('users.html', users=users)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    #email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)

```

## 4. BONUS

Postgresql advantages over sqlite is high availibility, scalabillity, peformance and security. Now we are able to contenerize app or create a cluster for database to ensure production environment with all key facilities and properties. Lets divide our app on 2 independent containers that will comunicate with each other.

First  step is to modify DATABASE_URI. It will be hosted on container so instead of localhost we need container name and port defined in docker-compose.yaml

```python
SQLALCHEMY_DATABASE_URI = 'postgresql://user:password@container_name:5432/database_name
```


### Dockerfile

This is regular python dockerfile for flask deployment

```dockerfile
# Use Python image
FROM python:3.10

# Set working directory
WORKDIR /app

# Copy application files
COPY . .

# Install dependencies
RUN pip install -r requirements.txt

# Expose the Flask port
EXPOSE 5000

# Run the Flask app
CMD ["python", "app.py"]

```

### Docker-compose.yaml

This utility allow us start app + database with one command. Flask container will wait for database container to initialize then its gonna launch with all the environments specified.

```dockerfile
version: '3.8'

services:
  db:
    image: postgres:latest
    restart: always
    environment:
      POSTGRES_USER: admin
      POSTGRES_PASSWORD: mypassword
      POSTGRES_DB: flask_db
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  web:
    build: .
    depends_on:
      - db
    environment:
      DATABASE_URL: postgresql://admin:mypassword@db:5432/flask_db
    ports:
      - "5000:5000"

volumes:
  pgdata:
```

Its how it start...

![My Image](images/startapp.png)



and how it looks from docker's processes perspective..

![My Image](images/dockerView.png)

