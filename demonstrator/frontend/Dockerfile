FROM amd64/python:3.9-slim

RUN mkdir /service
COPY protobufs/ /service/protobufs/
COPY demonstrator/frontend/ /service/frontend/
WORKDIR /service/frontend
RUN python -m pip install --upgrade pip
RUN python -m pip install -r requirements.txt
RUN python -m grpc_tools.protoc -I ../protobufs --python_out=. --grpc_python_out=. ../protobufs/demo.proto

ENV FLASK_APP=frontend.py
ENTRYPOINT [ "opentelemetry-instrument", "flask", "run", "--host=0.0.0.0"]