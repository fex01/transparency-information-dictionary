from concurrent import futures
import os
import grpc

from signal import signal, SIGTERM
import time

import demo_pb2, demo_pb2_grpc
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

email_host = os.getenv("EMAIL_SERVICE_HOST", "localhost")
email_port = os.getenv("EMAIL_SERVICE_PORT", "50051")
email_channel = grpc.insecure_channel(
    f"{email_host}:{email_port}"
)
email_stub = demo_pb2_grpc.EmailStub(email_channel)

account_host = os.getenv("ACCOUNT_SERVICE_HOST", "localhost")
account_port = os.getenv("ACCOUNT_SERVICE_PORT", "50051")
account_channel = grpc.insecure_channel(
    f"{account_host}:{account_port}"
)
account_stub = demo_pb2_grpc.AccountStub(account_channel)


class CourierService(demo_pb2_grpc.CourierServicer):

    def RequestCourier(self, request, context):
        span = trace.get_current_span()
        span.set_attribute("ti_c01", ["C01", "R02", "COA7_C1", "ST11"])
        span.set_attribute("ti_c07", ["C07", "COA7_C1", "ST11"])
        span.set_attribute("ti_tct01", ["TCT01"])
        span.set_attribute("ti_cop02", ["COP02"])
        account_response = account_stub.RequestUserInformation(
            demo_pb2.UserID(user_id=request.customer_id)
        )
        if account_response.responseCode == demo_pb2.ResponseCode.UNKNOWN_USER_ID:
            return demo_pb2.CourierRequestResponse(
                responseCode=demo_pb2.ResponseCode.INVALID_CUSTOMER
            )

        customer = account_response.user_information

        order_confirmation = demo_pb2.EmailRequest(
            recipient=customer.email,
            topic="Courier Request Confirmation",
            body="Hi " + customer.first_name + "\n\n" +
                 "We at James River Runners are happy to confirm that you ordered our courier service.\n" +
                 "Details are:\n" +
                 "Pickup: " + str(time.ctime(request.pickup_timestamp)) + ", " +
                 self.print_address(request.pickup_location) + "\n" +
                 "Delivery: " + str(time.ctime(request.drop_off_timestamp)) + ", " +
                 self.print_address(request.pickup_location) + "\n\n" +
                 "Best Regards,\n" +
                 "Your James River Runners-Team"
        )
        email_stub.Send(order_confirmation)

        return demo_pb2.CourierRequestResponse(
            responseCode=demo_pb2.ResponseCode.SUCCESS
        )

    @staticmethod
    def print_address(address):
        return address.street_name + " " + str(address.street_number) + ", " + address.zip + " " + address.city


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    demo_pb2_grpc.add_CourierServicer_to_server(CourierService(), server)
    port = os.getenv("COURIER_SERVICE_PORT", "50052")
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
