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
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
import googlecloudprofiler

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
        # get the current span to add attributes to tracing
        span = trace.get_current_span()
        # each TIL objects needs it's own line
        # attribute identifier (first string) needs to start with "ti_", the rest needs to be unique for this span
        # ti_c01: Data Disclosed object for category C01: E-mail address
        span.set_attribute("ti_c01", ["C01", "R02", "COA7_C1", "ST11"])
        span.set_attribute("ti_c07", ["C07", "COA7_C1", "ST11"])
        #
        span.set_attribute("ti_tct01", ["TCT01"])

        # logger.info('A request to send an email to {} has been received.'.format(request.recipient))

        if not pyisemail.is_email(request.recipient):
            # logger.info('"{}" is not a valid email address.'.format(request.recipient))
            return EmailResponse(responseCode=ResponseCode.INVALID_RECIPIENT)

        # If you actually want to send an email_service do it here
        time.sleep(0.1)

        return EmailResponse(responseCode=ResponseCode.SUCCESS)


class HealthCheck():
    def Check(self, request, context):
        return health_pb2.HealthCheckResponse(
            status=health_pb2.HealthCheckResponse.SERVING)


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    demo_pb2_grpc.add_EmailServicer_to_server(EmailService(), server)
    health_pb2_grpc.add_HealthServicer_to_server(EmailService(), server)

    port = os.getenv("EMAIL_SERVICE_PORT", "8000")
    # logger.info("listening on port: " + port)
    server.add_insecure_port("[::]:" + port)
    server.start()

    def handle_sigterm(*_):
        print("Received shutdown signal")
        all_rpcs_done_event = server.stop(30)
        all_rpcs_done_event.wait(30)
        print("Shut down gracefully")

    signal(SIGTERM, handle_sigterm)
    server.wait_for_termination()

def initStackdriverProfiling():
  project_id = None
  try:
    project_id = os.environ["GCP_PROJECT_ID"]
  except KeyError:
    # Environment variable not set
    pass

  for retry in range(1,4):
    try:
      if project_id:
        googlecloudprofiler.start(service='emailservice', service_version='1.0.0', verbose=0, project_id=project_id)
      else:
        googlecloudprofiler.start(service='emailservice', service_version='1.0.0', verbose=0)
      # logger.info("Successfully started Stackdriver Profiler.")
      return
    except (BaseException) as exc:
        print(BaseException)
      # logger.info("Unable to start Stackdriver Profiler Python agent. " + str(exc))
      # if (retry < 4):
      #   logger.info("Sleeping %d to retry initializing Stackdriver Profiler"%(retry*10))
      #   time.sleep (1)
      # else:
      #   logger.warning("Could not initialize Stackdriver Profiler after retrying, giving up")
  return


if __name__ == "__main__":
    # logger.info('starting the emailservice.')
    serve()
