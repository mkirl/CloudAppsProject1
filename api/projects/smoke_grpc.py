#!/usr/bin/env python3
import os
import uuid
import sys
from pathlib import Path

import grpc


GENERATED_PATH = Path(__file__).resolve().parent / "generated"
if str(GENERATED_PATH) not in sys.path:
	sys.path.insert(0, str(GENERATED_PATH))

import project_pb2  # type: ignore
import project_pb2_grpc  # type: ignore

PROJECT_GRPC_ADDR = "projectapp.jollyocean-e8f011bb.centralus.azurecontainerapps.io:443"
SMOKE_SLUG = f"smoke-project-{uuid.uuid4().hex[:8]}"
OWNER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI2NGY0YTY0MyIsInVzZXJuYW1lIjoiaGFycmlzb24yIiwiZXhwIjoxNzczNjQ2NTAxfQ.4JuHQOcY_C9zqE9F1jUvDHGZ-h1WmWuJELlJmc7wvgA"
OTHER_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiJkZGM3MzUyYSIsInVzZXJuYW1lIjoiaGFycmlzb24iLCJleHAiOjE3NzM2NDY2MjF9.l9ub_cJIGXiw79o436J9dQrG1NMsXpFK8hT_-AbU_y4"
INVALID_TOKEN = "not-a-real-token"


def _expect_rpc_error(expected_code, call, label: str) -> None:
	try:
		call()
		raise AssertionError(f"{label}: expected {expected_code.name}, call succeeded")
	except grpc.RpcError as exc:
		if exc.code() != expected_code:
			raise AssertionError(
				f"{label}: expected {expected_code.name}, got {exc.code().name}: {exc.details()}"
			)
		print(f"PASS: {label} -> {exc.code().name}")


def _assert_membership(stub, token: str, slug: str, expected: bool, label: str) -> None:
	response = stub.CheckUserInProject(
		project_pb2.CheckUserInProjectRequest(token=token, project_slug=slug)
	)
	if response.in_project != expected:
		raise AssertionError(
			f"{label}: expected in_project={expected}, got {response.in_project}"
		)
	print(f"PASS: {label} -> in_project={response.in_project}")


def _assert_project_in_list(projects, slug: str, expected: bool, label: str) -> None:
	found = any(project.slug == slug for project in projects)
	if found != expected:
		raise AssertionError(f"{label}: expected present={expected}, got present={found}")
	print(f"PASS: {label} -> present={found}")


def main() -> int:
	channel = grpc.secure_channel(
		PROJECT_GRPC_ADDR,
		grpc.ssl_channel_credentials(),
	)
	stub = project_pb2_grpc.ProjectServiceStub(channel)

	second_slug = f"{SMOKE_SLUG}-2"
	third_slug = f"{SMOKE_SLUG}-3"

	try:
		print("[1] Create project")
		create_one = stub.CreateProject(
			project_pb2.CreateProjectRequest(
				token=OWNER_TOKEN,
				slug=SMOKE_SLUG,
				name="My Project",
				description="A sample project",
			)
		)
		if not create_one.project_id:
			raise AssertionError("create project: project_id empty")
		print("PASS: create project")

		print("[2] Create second project")
		create_two = stub.CreateProject(
			project_pb2.CreateProjectRequest(
				token=OWNER_TOKEN,
				slug=second_slug,
				name="My Project",
				description="A sample project",
			)
		)
		if not create_two.project_id:
			raise AssertionError("create second project: project_id empty")
		print("PASS: create second project")

		print("[2b] Validate project by id")
		validate_ok = stub.ValidateProject(
			project_pb2.ValidateProjectRequest(project_id=create_one.project_id)
		)
		if not validate_ok.valid:
			raise AssertionError("validate project: expected valid=True")
		validate_bad = stub.ValidateProject(
			project_pb2.ValidateProjectRequest(project_id="507f1f77bcf86cd799439011")
		)
		if validate_bad.valid:
			raise AssertionError("validate project: expected valid=False for unknown id")
		print("PASS: validate project by id")

		print("[3] Create project with invalid token")
		_expect_rpc_error(
			grpc.StatusCode.UNAUTHENTICATED,
			lambda: stub.CreateProject(
				project_pb2.CreateProjectRequest(
					token=INVALID_TOKEN,
					slug=third_slug,
					name="My Project",
					description="A sample project",
				)
			),
			"invalid token create rejected",
		)

		print("[4] Get projects for valid user")
		list_valid = stub.ListProjects(project_pb2.ListProjectsRequest(token=OWNER_TOKEN))
		_assert_project_in_list(list_valid.projects, SMOKE_SLUG, True, "get projects")

		print("[5] Get projects with invalid token")
		_expect_rpc_error(
			grpc.StatusCode.UNAUTHENTICATED,
			lambda: stub.ListProjects(project_pb2.ListProjectsRequest(token=INVALID_TOKEN)),
			"invalid token list rejected",
		)

		print("[6] Get project details")
		details = stub.GetProject(
			project_pb2.GetProjectRequest(token=OWNER_TOKEN, project_slug=SMOKE_SLUG)
		)
		if details.project.slug != SMOKE_SLUG:
			raise AssertionError(
				f"get project details: expected slug={SMOKE_SLUG}, got {details.project.slug}"
			)
		print("PASS: get project details")

		print("[7] Join as owner (already member)")
		_expect_rpc_error(
			grpc.StatusCode.FAILED_PRECONDITION,
			lambda: stub.JoinProject(
				project_pb2.JoinProjectRequest(token=OWNER_TOKEN, project_slug=SMOKE_SLUG)
			),
			"join already-member rejected",
		)

		print("[8] Join as second user")
		joined = stub.JoinProject(
			project_pb2.JoinProjectRequest(token=OTHER_TOKEN, project_slug=SMOKE_SLUG)
		)
		if not joined.project_id:
			raise AssertionError("join second user: project_id empty")
		print("PASS: join second user")

		print("[9] Membership check for owner")
		_assert_membership(stub, OWNER_TOKEN, SMOKE_SLUG, True, "membership owner")

		print("[10] Leave as second user")
		left = stub.LeaveProject(
			project_pb2.LeaveProjectRequest(token=OTHER_TOKEN, project_slug=SMOKE_SLUG)
		)
		if not left.project_id:
			raise AssertionError("leave second user: project_id empty")
		print("PASS: leave second user")

		print("[11] Leave as last user")
		_expect_rpc_error(
			grpc.StatusCode.FAILED_PRECONDITION,
			lambda: stub.LeaveProject(
				project_pb2.LeaveProjectRequest(token=OWNER_TOKEN, project_slug=SMOKE_SLUG)
			),
			"last-user leave rejected",
		)
	except AssertionError as exc:
		print(f"FAIL: {exc}")
		return 1
	except grpc.RpcError as exc:
		print(f"FAIL: unexpected gRPC error {exc.code().name}: {exc.details()}")
		return 1

	print("smoke_grpc.py PASSED")
	return 0


if __name__ == "__main__":
	raise SystemExit(main())

