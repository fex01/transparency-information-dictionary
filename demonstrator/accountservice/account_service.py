import os
from concurrent import futures

import grpc

from signal import signal, SIGTERM

import pyisemail

import demo_pb2_grpc, demo_pb2
import logging
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))


class AccountService(demo_pb2_grpc.AccountServicer):

    def __init__(self):
        """
        Default constructor, initializes object fields with new instances.
        """
        self.users = {}

    def CreateAccount(self, user_information, context):
        span = trace.get_current_span()
        span.set_attribute("ti_c01", ["C01", "R02", "COA7", "ST11"])
        span.set_attribute("ti_c02", ["C02", "COA7", "ST11"])
        span.set_attribute("ti_c03", ["C03", "COA7", "ST11"])
        span.set_attribute("ti_c07", ["C07", "COA7", "ST11"])
        span.set_attribute("ti_tct01", ["TCT01"])
        span.set_attribute("ti_cop02", ["COP02"])
        response_codes = []

        street_number = user_information.address.street_number
        if street_number <= 0 or street_number >= 10000:
            response_codes.append(demo_pb2.ResponseCode.INVALID_ADDRESS)
        zip_code = user_information.address.zip
        if not zip_code.isdigit() or int(zip_code) <= 0 or int(zip_code) >= 100000:
            if demo_pb2.ResponseCode.INVALID_ADDRESS not in response_codes:
                response_codes.append(demo_pb2.ResponseCode.INVALID_ADDRESS)
        if not pyisemail.is_email(user_information.email):
            response_codes.append(demo_pb2.ResponseCode.INVALID_EMAIL)

        # if data is valid add user
        if len(response_codes) == 0:
            user_id = len(self.users.keys())
            self.users[user_id] = {
                "last_name": user_information.last_name,
                "first_name": user_information.first_name,
                "address": {
                    "street_name": user_information.address.street_name,
                    "street_number": street_number,
                    "city": user_information.address.city,
                    "zip": zip_code
                },
                "email": user_information.email,
                "phone": user_information.phone
            }
            return demo_pb2.CreateAccountResponse(
                responseCodes=[demo_pb2.ResponseCode.SUCCESS],
                user_id=user_id
            )
        # otherwise return response codes and user_id -1
        else:
            return demo_pb2.CreateAccountResponse(
                responseCodes=response_codes,
                user_id=-1
            )

    def RequestUserInformation(self, request, context):
        span = trace.get_current_span()
        span.set_attribute("ti_c01", ["C01", "R02", "COA7", "ST11"])
        span.set_attribute("ti_c02", ["C02", "COA7", "ST11"])
        span.set_attribute("ti_c03", ["C03", "COA7", "ST11"])
        span.set_attribute("ti_c07", ["C07", "COA7", "ST11"])
        user_id = request.user_id
        if user_id not in self.users.keys():
            return demo_pb2.UserInformationResponse(
                responseCode=demo_pb2.ResponseCode.UNKNOWN_USER_ID,
                user_information=None
            )
        else:
            user = self.users[user_id]
            user_information = demo_pb2.UserInformation(
                last_name=user["last_name"],
                first_name=user["first_name"],
                address=demo_pb2.Address(
                    street_name=user["address"]["street_name"],
                    street_number=user["address"]["street_number"],
                    city=user["address"]["city"],
                    zip=user["address"]["zip"],
                ),
                email=user["email"],
                phone=user["phone"]
            )
            return demo_pb2.UserInformationResponse(
                responseCode=demo_pb2.ResponseCode.SUCCESS,
                user_information=user_information
            )


def serve():
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))

    demo_pb2_grpc.add_AccountServicer_to_server(AccountService(), server)
    port = os.getenv("ACCOUNT_SERVICE_PORT", "50053")
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
