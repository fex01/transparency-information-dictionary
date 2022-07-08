import os
import datetime
import traceback
from flask_healthz import healthz, HealthError
import grpc
import demo_pb2_grpc, demo_pb2
from flask import Flask, request, render_template
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import (BatchSpanProcessor)
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter

tracer_provider = TracerProvider()
trace.set_tracer_provider(tracer_provider)
tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))

app = Flask(__name__)
app.register_blueprint(healthz, url_prefix="/healthz")

def liveness():
    pass

def readiness():
    pass

app.config.update(
    HEALTHZ = {
        "live": app.name + ".liveness",
        "ready": app.name + ".readiness",
    }
)

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


@app.route("/", methods=['GET', 'POST'])
def render_homepage():
    feedback = "frontend initialized"

    if request.method == 'POST':
        if request.form.get('create_account') == 'Create Account':
            feedback = create_account()
        if request.form.get('request_courier') == 'Request Courier':
            feedback = request_courier()
        elif request.form.get('delete_output') == 'Delete Output':
            feedback = ""
        else:
            pass  # unknown
    elif request.method == 'GET':
        return render_template('index.html', form=request.form)

    return render_template("index.html", output=feedback)


def create_account():
    span = trace.get_current_span()
    span.set_attribute("ti_c01", ["C01", "R02", "COA7", "ST11"])
    span.set_attribute("ti_c02", ["C02", "COA7", "ST11"])
    span.set_attribute("ti_c03", ["C03", "COA7", "ST11"])
    span.set_attribute("ti_c07", ["C07", "COA7", "ST11"])
    span.set_attribute("ti_tct01", ["TCT01"])
    span.set_attribute("ti_cop02", ["COP02"])
    feedback = "create_account()\n"
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
    try:
        response = account_server.CreateAccount(user_details)
    except Exception:
        feedback += "account_channel: " + "f{account_host}:{account_port}"
        feedback += traceback.format_exc()
    else:
        for code in response.responseCodes:
            feedback += "response code: " + demo_pb2.ResponseCode.Name(code) + "\n"
        feedback += "user ID: " + str(response.user_id) + "\n"
    return feedback


def request_courier():
    span = trace.get_current_span()
    span.set_attribute("ti_c01", ["C01", "R02", "COA7_C1", "ST11"])
    span.set_attribute("ti_c07", ["C07", "COA7_C1", "ST11"])
    span.set_attribute("ti_tct01", ["TCT01"])
    span.set_attribute("ti_cop02", ["COP02"])
    feedback = "request_courier()\n"
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
    try:
        response = courier_server.RequestCourier(courier_request)
    except Exception:
        feedback += "courier_channel: " + "f{courier_host}:{courier_port}"
        feedback += traceback.format_exc()
    else:
        feedback += "response: " + demo_pb2.ResponseCode.Name(response.responseCode) + "\n"
    return feedback
