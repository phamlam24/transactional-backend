from flask import Flask, request, jsonify
import sqlite3 as sql
import os
from dotenv import load_dotenv

# Get a Flask instance and load environment variables
app = Flask(__name__)
load_dotenv()

# Return constants
HTTP_OK = 200
HTTP_BAD_REQUEST = 400
HTTP_ERROR = 500

# Get the database name from the environment variables
DATABASE = os.getenv('DATABASE_NAME')

# Create or connect to a database, and create a table if it doesn't exist
conn = sql.connect(DATABASE + ".db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
               CREATE TABLE IF NOT EXISTS transactions 
               (id INTEGER PRIMARY KEY AUTOINCREMENT, 
               payer TEXT, 
               points INTEGER, 
               used INTEGER DEFAULT 0, 
               timestamp TEXT)
               ''')
conn.commit()

# Create an index on the timestamp column for faster queries
cursor.execute('''
               CREATE INDEX IF NOT EXISTS timestamp 
               ON transactions (timestamp)
               ''')
conn.commit()

## ROUTES ##
@app.route('/add', methods=['POST'])
def add():
    # Ensure the request is in JSON format with the required fields
    if not request.is_json:
        return 'ERROR: Invalid request format', HTTP_BAD_REQUEST

    required_fields = ['payer', 'points', 'timestamp']
    for field in required_fields:
        if field not in request.json:
            return f'ERROR: Missing required field: {field}', HTTP_BAD_REQUEST
        
    # Extract the data from the request
    data = request.get_json()
    payer = data['payer']
    points = data['points']
    timestamp = data['timestamp']

    # Handling the negative points case
    if points < 0:
        # Get the amount of points needed to subtract from transactions
        remaining_points = -points

        # SQL query to get all transactions from the payer
        payer_transactions = cursor.execute('''
                                            SELECT id, points, used 
                                            FROM transactions 
                                            WHERE payer = ? 
                                            AND used < points 
                                            AND timestamp <= ?
                                            ORDER BY timestamp ASC
                                            ''', (payer, timestamp)).fetchall()

        # Check if there are enough points to deduct
        total_available_points = sum(row[1] - row[2] for row in payer_transactions)
        if total_available_points < remaining_points:
            return 'ERROR: Not enough points for this negative transaction', HTTP_BAD_REQUEST
        
        # Deduct the points from the transactions
        for transaction in payer_transactions:
            id, points, used = transaction
            usable_points = points - used

            # If the transaction has enough points to cover the remaining points
            if remaining_points <= usable_points:
                cursor.execute('''
                               UPDATE transactions 
                               SET used = ? 
                               WHERE id = ?
                               ''', (used + remaining_points, id))
                break
            else: # If the transaction doesn't have enough points to cover the remaining points
                cursor.execute('''
                               UPDATE transactions 
                               SET used = ? 
                               WHERE id = ?
                               ''', (points, id))
                remaining_points -= usable_points
        
        # Insert the transaction into the database
        cursor.execute('''
                    INSERT INTO transactions 
                    (payer, points, timestamp) 
                    VALUES (?, ?, ?)
                    ''', (payer, -points, timestamp))

        # Commit the changes to the database
        conn.commit()
    else:
        # Insert the transaction into the database
        cursor.execute('''
                    INSERT INTO transactions 
                    (payer, points, timestamp) 
                    VALUES (?, ?, ?)
                    ''', (payer, points, timestamp))
        conn.commit()

    return '', HTTP_OK


@app.route('/spend', methods=['POST'])
def spend():
    # Get the points to spend from the request
    if not request.is_json:
        return 'ERROR: Invalid request format', HTTP_BAD_REQUEST
    remaining_points = request.json.get('points')

    # SQL query to fetch all rows from the transactions table where there are still points to use and order them by timestamp
    transactions = cursor.execute('''
                                  SELECT id, payer, points, used 
                                  FROM transactions 
                                  WHERE used < points 
                                  ORDER BY timestamp ASC
                                  ''').fetchall()

    # Check if there are enough points to deduct
    total_available_points = sum(row[2] - row[3] for row in transactions)
    if total_available_points < remaining_points:
        return 'ERROR: Not enough points for this transaction', HTTP_BAD_REQUEST    
    
    payers_map = {}

    # Deduct the points from the transactions
    for transaction in transactions:
        id, payer, points, used = transaction
        usable_points = points - used

        # If the transaction has enough points to cover the remaining points
        if remaining_points <= usable_points:
            cursor.execute('''
                           UPDATE transactions 
                           SET used = ? 
                           WHERE id = ?
                           ''', (used + remaining_points, id))
            payers_map[payer] = payers_map.get(payer, 0) - remaining_points
            break
        else: # If the transaction doesn't have enough points to cover the remaining points
            cursor.execute('''
                           UPDATE transactions 
                           SET used = ? 
                           WHERE id = ?
                           ''', (points, id))
            payers_map[payer] = payers_map.get(payer, 0) - usable_points
            remaining_points -= usable_points
    
    # Commit the changes to the database
    conn.commit()

    # Convert the map into an array and return it as a JSON object
    payers_list = [{'payer': key, 'points': value} for key, value in payers_map.items()]
    return jsonify(payers_list), HTTP_OK

@app.route('/balance')
def balance():
    # Fetch points and used points from the transactions table. Do not count any transaction with negative points
    rows = cursor.execute('''SELECT payer, SUM(points - used) 
                          FROM transactions 
                          WHERE points >= 0 
                          GROUP BY payer
                          ''').fetchall()
    balances = {}
    for row in rows:
        balances[row[0]] = row[1]
    
    # Return the balances as a JSON object
    return jsonify(balances), HTTP_OK

# An additional route to reset the transactions table
@app.route('/reset', methods=['DELETE'])
def reset():
    cursor.execute('DROP TABLE transactions')
    cursor.execute('''CREATE TABLE IF NOT EXISTS transactions 
                   (id INTEGER PRIMARY KEY AUTOINCREMENT, 
                   payer TEXT, 
                   points INTEGER, 
                   used INTEGER DEFAULT 0, 
                   timestamp TEXT)
                   ''')
    conn.commit()
    return 'Transactions table successully resetted', HTTP_OK

# An additional route to fetch all rows from the transactions table and turn into a JSON object
@app.route('/view')
def view():
    rows = cursor.execute('SELECT * FROM transactions').fetchall()
    transactions = []

    for row in rows:
        transaction = {
            'id': row[0],
            'payer': row[1],
            'points': row[2],
            'used': row[3],
            'timestamp': row[4]
        }
        transactions.append(transaction)

    return jsonify(transactions), HTTP_OK

if __name__ == '__main__':
    app.run(port=8000)