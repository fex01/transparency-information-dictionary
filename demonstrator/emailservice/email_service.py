import os
import time
from concurrent import futures
import grpc
from signal import signal, SIGTERM
import pyisemail
from demo_pb2 import (
    ResponseCode,
    EmailResponse,
)
from grpc_health.v1 import (
    health_pb2,
    health_pb2_grpc,
)
import demo_pb2_grpc
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))


class EmailService(demo_pb2_grpc.EmailServicer):

    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)

    def Watch(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.UNIMPLEMENTED)

    def Send(self, request, context):
        span = trace.get_current_span()
        span.set_attribute("ti_c01", ["C01", "R02", "COA7_C1", "ST11"])
        span.set_attribute("ti_c07", ["C07", "COA7_C1", "ST11"])
        span.set_attribute("ti_tct01", ["TCT01"])

        if not pyisemail.is_email(request.recipient):
            print("invalid recipient")
            return EmailResponse(responseCode=ResponseCode.INVALID_RECIPIENT)

        # If you actually want to send an email_service do it here
        time.sleep(0.1)

        print("success - test")
        return EmailResponse(responseCode=ResponseCode.SUCCESS)


class HealthCheck():
    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    demo_pb2_grpc.add_EmailServicer_to_server(EmailService(), server)
    health_pb2_grpc.add_HealthServicer_to_server(EmailService(), server)

    port = os.getenv("EMAIL_SERVICE_PORT", "50051")
    server.add_insecure_port("[::]:" + port)
    server.start()

    def handle_sigterm(*_):
        print("Received shutdown signal")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        print("Shut down gracefully")

    signal(SIGTERM, handle_sigterm)
    server.wait_for_termination()


if __name__ == "__main__":
    logging.basicConfig()
    serve()
