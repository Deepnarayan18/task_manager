from flask import Flask, render_template, request, redirect, url_for, jsonify
import mysql.connector
import os
from datetime import datetime

app = Flask(__name__)

# MySQL configuration from environment variables
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASS', ''),
    'database': os.getenv('DB_NAME', 'task_manager_db')
}

def get_db_connection():
    """Establish a MySQL connection."""
    try:
        connection = mysql.connector.connect(**DB_CONFIG)
        if connection.is_connected():
            return connection
        raise Exception("Connection not established")
    except Exception as e:
        raise Exception(f"Database connection failed: {e}")

def execute_query(query, params=(), fetch=True):
    """Execute a SQL query and return results if fetch is True."""
    connection = get_db_connection()
    try:
        cursor = connection.cursor()
        cursor.execute(query, params)
        if fetch:
            results = cursor.fetchall()
        else:
            connection.commit()
            results = None
        cursor.close()
        connection.close()
        return results
    except Exception as e:
        connection.close()
        raise Exception(f"Query failed: {e}")

# API Endpoints (JSON-only, for curl/Postman)
@app.route('/tasks', methods=['GET'])
def list_tasks():
    """List all tasks in JSON, sorted by due date."""
    try:
        tasks = execute_query("SELECT id, title, description, due_date, status, priority FROM Task ORDER BY due_date ASC")
        task_list = [
            {
                'id': task[0],
                'title': task[1],
                'description': task[2],
                'due_date': task[3].isoformat() if task[3] else None,
                'status': task[4],
                'priority': task[5]
            } for task in tasks
        ]
        return jsonify({'tasks': task_list}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks', methods=['POST'])
def create_task():
    """Create a new task, expects JSON input."""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        due_date = data.get('due_date')
        status = data.get('status', 'Pending')
        priority = data.get('priority', 'Medium')

        if not title or not due_date:
            return jsonify({'error': 'title and due_date are required'}), 400

        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid due_date format, use YYYY-MM-DD'}), 400

        execute_query(
            "INSERT INTO Task (title, description, due_date, status, priority) VALUES (%s, %s, %s, %s, %s)",
            (title, description, due_date, status, priority),
            fetch=False
        )

        new_task = execute_query("SELECT id, title, description, due_date, status, priority FROM Task WHERE id = LAST_INSERT_ID()")[0]
        task_response = {
            'id': new_task[0],
            'title': new_task[1],
            'description': new_task[2],
            'due_date': new_task[3].isoformat() if new_task[3] else None,
            'status': new_task[4],
            'priority': new_task[5]
        }
        return jsonify({'task': task_response}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<int:task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task, expects JSON input."""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415
    try:
        data = request.get_json()
        title = data.get('title')
        description = data.get('description', '')
        due_date = data.get('due_date')
        status = data.get('status')
        priority = data.get('priority')

        if not title or not due_date:
            return jsonify({'error': 'title and due_date are required'}), 400

        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid due_date format, use YYYY-MM-DD'}), 400

        tasks = execute_query("SELECT id FROM Task WHERE id=%s", (task_id,))
        if not tasks:
            return jsonify({'error': 'Task not found'}), 404

        execute_query(
            "UPDATE Task SET title=%s, description=%s, due_date=%s, status=%s, priority=%s WHERE id=%s",
            (title, description, due_date, status, priority, task_id),
            fetch=False
        )

        updated_task = execute_query("SELECT id, title, description, due_date, status, priority FROM Task WHERE id=%s", (task_id,))[0]
        task_response = {
            'id': updated_task[0],
            'title': updated_task[1],
            'description': updated_task[2],
            'due_date': updated_task[3].isoformat() if updated_task[3] else None,
            'status': updated_task[4],
            'priority': updated_task[5]
        }
        return jsonify({'task': task_response}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<int:task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task."""
    try:
        tasks = execute_query("SELECT id FROM Task WHERE id=%s", (task_id,))
        if not tasks:
            return jsonify({'error': 'Task not found'}), 404

        execute_query("DELETE FROM Task WHERE id=%s", (task_id,), fetch=False)
        return jsonify({'message': 'Task deleted'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/tasks/<int:task_id>/status', methods=['PATCH'])
def update_task_status(task_id):
    """Update task status, expects JSON input."""
    if not request.is_json:
        return jsonify({'error': 'Content-Type must be application/json'}), 415
    try:
        data = request.get_json()
        status = data.get('status')
        if not status:
            return jsonify({'error': 'status is required'}), 400

        tasks = execute_query("SELECT id FROM Task WHERE id=%s", (task_id,))
        if not tasks:
            return jsonify({'error': 'Task not found'}), 404

        execute_query("UPDATE Task SET status=%s WHERE id=%s", (status, task_id), fetch=False)

        updated_task = execute_query("SELECT id, title, description, due_date, status, priority FROM Task WHERE id=%s", (task_id,))[0]
        task_response = {
            'id': updated_task[0],
            'title': updated_task[1],
            'description': updated_task[2],
            'due_date': updated_task[3].isoformat() if updated_task[3] else None,
            'status': updated_task[4],
            'priority': updated_task[5]
        }
        return jsonify({'task': task_response}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Web Interface (for browser access)
@app.route('/')
def index():
    """Render the web interface at http://127.0.0.1:5000/, displaying tasks from index.html."""
    try:
        tasks = execute_query("SELECT id, title, description, due_date, status, priority FROM Task ORDER BY due_date ASC")
        return render_template('index.html', tasks=tasks)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/web/tasks', methods=['POST'])
def web_create_task():
    """Handle web form submission for creating a task."""
    try:
        title = request.form.get('title')
        description = request.form.get('description', '')
        due_date = request.form.get('due_date')
        status = request.form.get('status', 'Pending')
        priority = request.form.get('priority', 'Medium')

        if not title or not due_date:
            return jsonify({'error': 'Title and due_date are required'}), 400

        try:
            due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'error': 'Invalid due_date format, use YYYY-MM-DD'}), 400

        execute_query(
            "INSERT INTO Task (title, description, due_date, status, priority) VALUES (%s, %s, %s, %s, %s)",
            (title, description, due_date, status, priority),
            fetch=False
        )
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/web/tasks/<int:task_id>/status', methods=['POST'])
def web_update_task_status(task_id):
    """Handle web form submission for updating task status."""
    try:
        status = request.form.get('status')
        if not status:
            return jsonify({'error': 'Status is required'}), 400

        tasks = execute_query("SELECT id FROM Task WHERE id=%s", (task_id,))
        if not tasks:
            return jsonify({'error': 'Task not found'}), 404

        execute_query("UPDATE Task SET status=%s WHERE id=%s", (status, task_id), fetch=False)
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/web/tasks/<int:task_id>/delete', methods=['POST'])
def web_delete_task(task_id):
    """Handle web form submission for deleting a task."""
    try:
        tasks = execute_query("SELECT id FROM Task WHERE id=%s", (task_id,))
        if not tasks:
            return jsonify({'error': 'Task not found'}), 404

        execute_query("DELETE FROM Task WHERE id=%s", (task_id,), fetch=False)
        return redirect(url_for('index'))
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)