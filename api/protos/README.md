# Compiling Protocol Buffers
To compile the Protocol Buffers (.proto files) into Python code, you can use the `protoc` compiler. It should be installed as part of your development environment when you `uv sync`. The following command will compile all .proto files in the `api/protos` directory:

```bash
uv run python3 -m grpc_tools.protoc -Iapi/protos=api/hardware --python_out=. --grpc_python_out=. api/protos/hardware.proto
```