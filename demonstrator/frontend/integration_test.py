# run with `opentelemetry-instrument pytest integration_test.py` to generate trace
import datetime
import os
from urllib.request import urlopen
import grpc
import demo_pb2_grpc, demo_pb2
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

email_host = os.getenv("EMAIL_SERVICE_HOST", "localhost")
email_port = os.getenv("EMAIL_SERVICE_PORT", "50051")
email_channel = grpc.insecure_channel(
    f"{email_host}:{email_port}"
)
email_server = demo_pb2_grpc.EmailStub(email_channel)

account_host = os.getenv("ACCOUNT_SERVICE_HOST", "localhost")
account_port = os.getenv("ACCOUNT_SERVICE_PORT", "50053")
account_channel = grpc.insecure_channel(
    f"{account_host}:{account_port}"
)
account_server = demo_pb2_grpc.AccountStub(account_channel)

courier_host = os.getenv("COURIER_SERVICE_HOST", "localhost")
courier_port = os.getenv("COURIER_SERVICE_PORT", "50052")
courier_channel = grpc.insecure_channel(
    f"{courier_host}:{courier_port}"
)
courier_server = demo_pb2_grpc.CourierStub(courier_channel)


def test_email_service():
    email_valide = demo_pb2.EmailRequest(
        recipient="test@miske.email", topic="email_valide", body="Test"
    )
    response = email_server.Send(email_valide, None)
    assert response.responseCode == demo_pb2.ResponseCode.SUCCESS


def test_create_account():
    user_details = demo_pb2.UserInformation(
        last_name="Mustermann",
        first_name="Max",
        address=demo_pb2.Address(
            street_name="Berliner Chaussee",
            street_number=13,
            city="Entenhausen",
            zip="99999"
        ),
        email="max@mustermann.ente",
        phone="+99 999 999 999"
    )
    response = account_server.CreateAccount(user_details)
    assert response.responseCodes[0] == demo_pb2.ResponseCode.SUCCESS
    assert response.user_id >= 0


def test_request_user_information():
    user_id = 0
    response = account_server.RequestUserInformation(
        demo_pb2.UserID(user_id=user_id)
    )
    assert response.responseCode == demo_pb2.ResponseCode.SUCCESS


def test_courier_service():
    pickup_time = datetime.datetime(year=2022, month=7, day=11, hour=10)
    drop_off_time = datetime.datetime(year=2022, month=7, day=15, hour=12)
    courier_request = demo_pb2.CourierRequest(
        customer_id=0,
        pickup_location=demo_pb2.Address(
            street_name="Berliner Chaussee",
            street_number=13,
            city="Entenhausen",
            zip="99999"
        ),
        drop_off_location=demo_pb2.Address(
            street_name="Pariser Chaussee",
            street_number=31,
            city="Entenhausen",
            zip="66666"
        ),
        pickup_timestamp=int(round(pickup_time.timestamp())),
        drop_off_timestamp=int(round(drop_off_time.timestamp()))
    )
    response = courier_server.RequestCourier(courier_request)
    assert response.responseCode == demo_pb2.ResponseCode.SUCCESS


def test_frontend():
    homepage_html = urlopen("http://localhost:5000").read().decode("utf-8")
    assert "<title>Transparency Tracing Demo</title>" in homepage_html