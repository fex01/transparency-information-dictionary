# run with `opentelemetry-instrument pytest integration_test.py` to generate trace
import datetime
import os
from urllib import parse
from urllib.request import urlopen

import grpc
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)

import demo_pb2
import demo_pb2_grpc

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

account_host = os.getenv("ACCOUNTSERVICE_SERVICE_HOST", "localhost")
account_port = os.getenv("ACCOUNTSERVICE_SERVICE_PORT", "6000")
account_channel = grpc.insecure_channel(
    f"{account_host}:{account_port}"
)
account_server = demo_pb2_grpc.AccountStub(account_channel)

courier_host = os.getenv("COURIERSERVICE_SERVICE_HOST", "localhost")
courier_port = os.getenv("COURIERSERVICE_SERVICE_PORT", "7000")
courier_channel = grpc.insecure_channel(
    f"{courier_host}:{courier_port}"
)
courier_server = demo_pb2_grpc.CourierStub(courier_channel)

email_host = os.getenv("EMAILSERVICE_SERVICE_HOST", "localhost")
email_port = os.getenv("EMAILSERVICE_SERVICE_PORT", "8000")
email_channel = grpc.insecure_channel(
    f"{email_host}:{email_port}"
)
email_server = demo_pb2_grpc.EmailStub(email_channel)

FRONTEND_SERVICE_HOST = os.getenv("FRONTEND_SERVICE_HOST", "localhost")
FRONTEND_SERVICE_PORT = os.getenv("FRONTEND_SERVICE_PORT", "5000")
frontend = "http://" + FRONTEND_SERVICE_HOST + ":" + FRONTEND_SERVICE_PORT


def test_01_email_service():
    email_valide = demo_pb2.EmailRequest(
        recipient="test@miske.email", topic="email_valide", body="Test"
    )
    response = email_server.Send(email_valide, None)
    assert response.responseCode == demo_pb2.ResponseCode.SUCCESS


def test_02_create_account():
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


def test_03_request_user_information():
    user_id = 0
    response = account_server.RequestUserInformation(
        demo_pb2.UserID(user_id=user_id)
    )
    assert response.responseCode == demo_pb2.ResponseCode.SUCCESS


def test_04_courier_service():
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


def test_05_frontend():
    homepage_html = urlopen(frontend).read().decode("utf-8")
    assert "<title>Transparency Tracing Demo</title>" in homepage_html


def test_06_frontend_create_account():
    data = parse.urlencode({"create_account": "Create Account"}).encode()
    homepage_html = urlopen(frontend, data).read().decode("utf-8")
    assert "response code: SUCCESS" in homepage_html


def test_07_frontend_courier_service():
    data = parse.urlencode({"request_courier": "Request Courier"}).encode()
    homepage_html = urlopen(frontend, data).read().decode("utf-8")
    assert "response: SUCCESS" in homepage_html
