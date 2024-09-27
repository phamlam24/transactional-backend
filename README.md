# Fetch Backend Internship Challenge - RESTful API
Note: The commands below assume Windows. Use similar commands for macOS/Linux.

## First time running
Clone the repository (requires Git):
```bash
git clone https://github.com/phamlam24/transactional-backend.git
```

Go into the project folder:
```bash
cd transactional-backend
```

This is a Python server. Install or use the latest version of Python.

After installation, create a virtual environment:

```bash
python -m venv env
```

You can customize the SQLite database name in `src/server.py`, go to line 16 and change the value of `DATABASE_NAME` to any value.

## Run the server
Activate the virtual environment:

```bash
.\env\Scripts\activate
```

Install necessary dependencies:

```bash
pip install -r requirements.txt
```

Run the server:

```bash
python src/server.py
```

Once the server starts running, you can use Postman or a similar tool to test the server.
