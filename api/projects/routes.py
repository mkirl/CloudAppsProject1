import os
import grpc
from api.projects import project_pb2
from flask import Blueprint, request, jsonify, current_app, g
from bson import ObjectId

from api.auth.decorators import jwt_required

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')


from api.projects import project_pb2, project_pb2_grpc


def get_project_stub():
    # Reuse a single channel/stub per Flask app instance.
    ext = current_app.extensions
    if "project_grpc_stub" not in ext:
        addr = current_app.config.get(
            "PROJECT_GRPC_ADDR",
            os.environ.get("PROJECT_GRPC_ADDR", "projectapp.jollyocean-e8f011bb.centralus.azurecontainerapps.io:443"),
        )
        
        channel = grpc.secure_channel(addr, grpc.ssl_channel_credentials())

        ext["project_grpc_channel"] = channel
        ext["project_grpc_stub"] = project_pb2_grpc.ProjectServiceStub(channel)

    return ext["project_grpc_stub"]

@projects_bp.route('', methods=['GET'])
@jwt_required
def get_user_projects():
    """Get all projects for the current user."""
    user_id = str(g.current_user['_id'])
    token = g.current_token

    # Find projects where user is a member
    stub = get_project_stub()
    projects = stub.ListProjects(project_pb2.ListProjectsRequest(token=token)).projects
    user_projects = [project for project in projects if stub.CheckUserInProject(project_pb2.CheckUserInProjectRequest(token=token, project_slug=project.slug)).in_project]

    # Convert to list and format response
    result = []
    for project in user_projects:
        result.append({
            'id': str(project.project_id),
            'name': project.name,
            'description': project.description
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

    user_id = str(g.current_user['_id'])
    token = g.current_token

    # Create project document
    project_doc = {
        'name': name,
        'project_id': project_id,
        'description': description,
        'members': [user_id],  # Creator is first member
        'hw_allocations': []   # No hardware allocated initially
    }

    stub = get_project_stub()

    result = stub.CreateProject(project_pb2.CreateProjectRequest(
        token=token,
        slug=project_id,
        name=name,
        description=description
    ))

    project_doc['_id'] = result.project_id

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
    stub = get_project_stub()
    project = stub.GetProject(project_pb2.GetProjectRequest(token=token, project_slug=project_id)).project

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    user_id = str(g.current_user['_id'])

    # Extract the ObjectId for update
    project_id = str(project.project_id)

    # Check if already a member
    if stub.CheckUserInProject(project_pb2.CheckUserInProjectRequest(token=token, project_slug=project.slug)).in_project:
        return jsonify({'error': 'Already a member of this project'}), 400

    # Add user to members
    joined = stub.JoinProjectRequest(token=token, project_slug=project.slug)

    return jsonify({
        'id': project.project_id,
        'name': project.name,
        'description': project.description
    }), 200
