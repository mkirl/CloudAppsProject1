from flask import Blueprint, request, jsonify, current_app, g
from bson import ObjectId

from api.auth.decorators import jwt_required
from api.projects import project_pb2, project_pb2_grpc
from api.hardware import hardware_pb2, hardware_pb2_grpc
from api.projects.routes import get_project_stub
import grpc
from google.protobuf import empty_pb2
import os

hardware_bp = Blueprint('hardware', __name__, url_prefix='/api/hardware')

def get_hardware_stub():
    # Reuse a single channel/stub per Flask app instance.
    ext = current_app.extensions
    if "hardware_grpc_stub" not in ext:
        addr = current_app.config.get(
            "HARDWARE_GRPC_ADDR",
            os.environ.get("HARDWARE_GRPC_ADDR", "nginx-proxy.wonderfulpond-ecedce94.northcentralus.azurecontainerapps.io:443"),
        )
        
        channel = grpc.secure_channel(addr, grpc.ssl_channel_credentials())

        ext["hardware_grpc_channel"] = channel
        ext["hardware_grpc_stub"] = hardware_pb2_grpc.HardwareServiceStub(channel)

    return ext["hardware_grpc_stub"]

@hardware_bp.route('', methods=['GET'])
@jwt_required
def get_hardware():
    """Get all hardware sets with availability."""
    stub = get_hardware_stub()
    hardware_sets = stub.GetHardwareResources(empty_pb2.Empty()).hardware_sets


    result = []
    for hw in hardware_sets:
        set = hw.name
        capacity = hw.capacity
        available = hw.available
        result.append({
            'set': set,
            'capacity': capacity,
            'available': available,
            'checkedOut': capacity - available
        })

    return jsonify(result), 200


@hardware_bp.route('/request', methods=['POST'])
@jwt_required
def request_hardware():
    """Check out hardware to a project."""
    data = request.get_json() or {}

    token = g.current_token
    project_id = data.get('projectId', '').strip()
    requests = data.get('requests', [])  # [{set: "HW Set 1", quantity: 5}, ...]

    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400

    if not requests:
        return jsonify({'error': 'No hardware requested'}), 400

    # Check project exists and user is a member
    project_stub = get_project_stub()
    project = project_stub.GetProject(project_pb2.GetProjectRequest(token=token, project_slug=project_id)).project
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Check if a member
    in_project = project_stub.CheckUserInProject(project_pb2.CheckUserInProjectRequest(token=token, project_slug=project_id)).in_project
    if not in_project:
        return jsonify({'error': 'You are not a member of this project'}), 403

    # Process each hardware request
    hardware_stub = get_hardware_stub()

    hardware_sets = hardware_stub.GetHardwareResources(empty_pb2.Empty()).hardware_sets
    for req in requests:
        hw_name = req.get('set')
        quantity = req.get('quantity', 0)

        if quantity <= 0:
            continue

        # Find hardware set
        hw = next((hw for hw in hardware_sets if hw.name == hw_name), None)

        if not hw:
            return jsonify({'error': f'Hardware set "{hw_name}" not found'}), 404

        if hw.available < quantity:
            return jsonify({
                'error': f'Not enough "{hw_name}" available. Requested: {quantity}, Available: {hw.available}'
            }), 400

        # Update hardware availability
        # should probably update rpc to return a RequestHardwareResponse message with a bool field ok for success instead of relying on grpc error handling for this
        hardware_stub.RequestHardware(hardware_pb2.HardwareRequest(
            hw_set_id=str(hw.name),
            project_id=project_id,
            quantity=quantity
        ))

        # TODO when project allocations are tracked, update project allocations for this hardware set
        # # Update project allocation
        # result = current_app.db.projects.update_one(
        #     {'project_id': project_id, 'hw_allocations.hw_set_id': str(hw['_id'])},
        #     {'$inc': {'hw_allocations.$.count': quantity}}
        # )

        # # If no existing allocation, add new one
        # if result.matched_count == 0:
        #     current_app.db.projects.update_one(
        #         {'project_id': project_id},
        #         {'$push': {'hw_allocations': {'hw_set_id': str(hw['_id']), 'count': quantity}}}
        #     )

    return jsonify({'message': 'Hardware checked out successfully'}), 200


@hardware_bp.route('/return', methods=['POST'])
@jwt_required
def return_hardware():
    """Return hardware from a project."""
    data = request.get_json() or {}

    token = g.current_token
    project_id = data.get('projectId', '').strip()
    returns = data.get('returns', [])  # [{set: "HW Set 1", quantity: 5}, ...]

    if not project_id:
        return jsonify({'error': 'Project ID is required'}), 400

    if not returns:
        return jsonify({'error': 'No hardware to return'}), 400

    # Check project exists and user is a member
    project_stub = get_project_stub()
    project = project_stub.GetProject(project_pb2.GetProjectRequest(token=token, project_slug=project_id)).project
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    # Check if a member
    in_project = project_stub.CheckUserInProject(project_pb2.CheckUserInProjectRequest(token=token, project_slug=project_id)).in_project
    if not in_project:
        return jsonify({'error': 'You are not a member of this project'}), 403

    # Process each return
    hardware_stub = get_hardware_stub()
    hardware_sets = hardware_stub.GetHardwareResources(empty_pb2.Empty()).hardware_sets
    for ret in returns:
        hw_name = ret.get('set')
        quantity = ret.get('quantity', 0)

        if quantity <= 0:
            continue

        # Find hardware set
        hw = next((hw for hw in hardware_sets if hw.name == hw_name), None)
        if not hw:
            return jsonify({'error': f'Hardware set "{hw_name}" not found'}), 404

        # TODO when project allocations are tracked, check that the project has enough of this hardware allocated to return
        # Check project has enough allocated
        # hw_allocations = project.allocations
        # allocation = next(
        #     (a for a in hw_allocations if a['hw_set_id'] == str(hw['_id'])),
        #     None
        # )

        # workaround until project allocations are tracked
        allocation = hw.capacity - hw.available
        if not allocation or allocation < quantity:
            return jsonify({
                'error': f'Cannot return {quantity} of "{hw_name}". Project only has {allocation if allocation else 0}'
            }), 400

        # Update hardware availability (increase)
        hardware_stub.ReturnHardware(hardware_pb2.HardwareRequest(
            hw_set_id=str(hw.name),
            project_id=project_id,
            quantity=quantity
        ))

        # # Update project allocation (decrease)
        # current_app.db.projects.update_one(
        #     {'project_id': project_id, 'hw_allocations.hw_set_id': str(hw['_id'])},
        #     {'$inc': {'hw_allocations.$.count': -quantity}}
        # )

    return jsonify({'message': 'Hardware returned successfully'}), 200
