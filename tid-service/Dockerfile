FROM amd64/python:3.9-slim

RUN mkdir /services
COPY protobufs/ /services/protobufs/
COPY dictionary/ /services/dictionary/
COPY tid-service/ /services/tidservice/
WORKDIR /services/tidservice
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
RUN python -m grpc_tools.protoc -I ../protobufs --python_out=. --grpc_python_out=. ../protobufs/tid.proto

# for integration test generate demo.proto files
RUN python -m grpc_tools.protoc -I ../protobufs --python_out=. --grpc_python_out=. ../protobufs/demo.proto

RUN apt-get -qq update \
  && apt-get install -y --no-install-recommends \
  wget
RUN GRPC_HEALTH_PROBE_VERSION=v0.4.11 && \
  wget -qO/bin/grpc_health_probe https://github.com/grpc-ecosystem/grpc-health-probe/releases/download/${GRPC_HEALTH_PROBE_VERSION}/grpc_health_probe-linux-amd64 && \
  chmod +x /bin/grpc_health_probe

ENTRYPOINT [ "python", "tidservice.py" ]
