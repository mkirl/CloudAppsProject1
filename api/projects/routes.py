from flask import Blueprint, request, jsonify, current_app, g
from bson import ObjectId

from api.auth.decorators import jwt_required

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')


@projects_bp.route('', methods=['GET'])
@jwt_required
def get_user_projects():
    """Get all projects for the current user."""
    user_id = str(g.current_user['_id'])

    # Find projects where user is a member
    projects = current_app.db.projects.find({'members': user_id})

    # Convert to list and format response
    result = []
    for project in projects:
        result.append({
            'id': str(project['project_id']),
            'name': project['name'],
            'description': project.get('description', '')
        })

    return jsonify(result), 200


@projects_bp.route('', methods=['POST'])
@jwt_required
def create_project():
    """Create a new project."""
    data = request.get_json() or {}

    name = data.get('name', '').strip()
    description = data.get('description', '').strip()
    project_id = data.get('id', '').strip()

    # Validation
    if not name:
        return jsonify({'error': 'Project name is required'}), 400
    
    if not description:
        return jsonify({'error': 'Project description is required'}), 400
    
    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400

    # Check if project exists
    project = current_app.db.projects.find_one({'project_id': project_id})
    if project:
        return jsonify({'error': 'Project already exists'}), 400
    
    user_id = str(g.current_user['_id'])

    # Create project document
    project_doc = {
        'name': name,
        'project_id': project_id,
        'description': description,
        'members': [user_id],  # Creator is first member
        'hw_allocations': []   # No hardware allocated initially
    }

    result = current_app.db.projects.insert_one(project_doc)
    project_doc['_id'] = result.inserted_id

    return jsonify({
        'id': project_doc['project_id'],
        'name': project_doc['name'],
        'description': project_doc['description']
    }), 201


@projects_bp.route('/join', methods=['POST'])
@jwt_required
def join_project():
    """Join an existing project."""
    data = request.get_json() or {}

    project_id = data.get('projectId', '').strip()

    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400

    # Find the project
    project = current_app.db.projects.find_one({'project_id': project_id})
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    user_id = str(g.current_user['_id'])

    # Extract the ObjectId for update
    obj_id = str(project['_id'])

    # Check if already a member
    if user_id in project.get('members', []):
        return jsonify({'error': 'Already a member of this project'}), 400

    # Add user to members
    current_app.db.projects.update_one(
        {'_id': ObjectId(obj_id)},
        {'$push': {'members': user_id}}
    )

    return jsonify({
        'id': project['project_id'],
        'name': project['name'],
        'description': project.get('description', '')
    }), 200

@projects_bp.route('/<project_id>/hardware', methods=['GET'])
@jwt_required
def get_project_hardware_billing(project_id):
    """Get hardware checked out to a project, for billing purposes."""

    # Fetch the project
    project = current_app.db.projects.find_one({'project_id': project_id})
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Ensure the requesting user is a member
    user_id = str(g.current_user['_id'])
    if user_id not in project.get('members', []):
        return jsonify({'error': 'You are not a member of this project'}), 403

    # Look up HW Set 1 and HW Set 2 from the hardware collection
    hw_set_1_doc = current_app.db.hardware.find_one({'name': 'HW Set 1'})
    hw_set_2_doc = current_app.db.hardware.find_one({'name': 'HW Set 2'})

    hw_set_1_id = str(hw_set_1_doc['_id']) if hw_set_1_doc else None
    hw_set_2_id = str(hw_set_2_doc['_id']) if hw_set_2_doc else None

    # Sum up allocations for each set from the project's hw_allocations array
    hw_set_1_count = 0
    hw_set_2_count = 0

    for alloc in project.get('hw_allocations', []):
        if alloc['hw_set_id'] == hw_set_1_id:
            hw_set_1_count += alloc.get('count', 0)
        elif alloc['hw_set_id'] == hw_set_2_id:
            hw_set_2_count += alloc.get('count', 0)

    return jsonify({
        'hw_set_1': hw_set_1_count,
        'hw_set_2': hw_set_2_count,
    }), 200