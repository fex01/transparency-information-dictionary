# Transparency Information Dictionary

- [Spin Up](#spin-up)
  - [Docker](#docker)
  - [Kubernetes](#kubernetes)
- [Use](#use)
  - [Enrich Services With Transparency Information](#enrich-services-with-transparency-information)
    - [1) Request Tags for Transparency Information](#1-request-tags-for-transparency-information)
    - [2) Annotate Services With Transparency Information](#2-annotate-services-with-transparency-information)
  - [Test to Generate Traces](#test-to-generate-traces)
    - [3) Trigger Integration Test With Activated Tracing](#3-trigger-integration-test-with-activated-tracing)
    - [4) Spans Are Collected And Forwarded as Traces to the Jaeger Backend](#4-spans-are-collected-and-forwarded-as-traces-to-the-jaeger-backend)
  - [Collect Transparency Information From Traces](#collect-transparency-information-from-traces)
    - [5) Request Formatted Transparency Information From Traces](#5-request-formatted-transparency-information-from-traces)
    - [6) Jaeger Backend Gets Queried Regarding All Services and Traces](#6-jaeger-backend-gets-queried-regarding-all-services-and-traces)
    - [7) Returns Collected Traces as JSON](#7-returns-collected-traces-as-json)
    - [8) Filters Traces for Tags and Transforms Them Into TIL Objects](#8-filters-traces-for-tags-and-transforms-them-into-til-objects)
- [Concepts](#concepts)
- [Tools & Technology](#tools--technology)
- [Thanks](#thanks)
- [Sources](#sources)
- [Footnotes](#footnotes)

## Spin Up

### Docker

For now it's enough to have an environment with git<sup id="a1">[1](#f1)</sup>, [Docker](https://www.docker.com) and `docker compose`<sup id="a2">[2](#f2)</sup> to get started:

- `git clone https://github.com/fex01/transparency-information-dictionary.git` clone the repository
- `cd transparency-information-dictionary` move into the repos directory
- `docker compose build` build the images for the demonstrator and the Transparency Information Dictionary Service (tid-services)
- `docker compose up` start container for the tid-service, demonstrator services, a [OpenTelemetry](https://opentelemetry.io) collector service and a [jaeger](https://www.jaegertracing.io) backend

### Kubernetes

The images are provided at `europe-north1-docker.pkg.dev/ti-dictionary/transparency-information-dictionary/<service-name>` via the [Google Artifact Registry](https://cloud.google.com/artifact-registry) (complete with automated builds via this repository). A kubernetes manifest was created and is part of this repository - but the author could not get the deployment to work via the [Google Kubernetes Engine (GKE)](https://cloud.google.com/kubernetes-engine/). The main problems seem to be:

- discover ready/live status for gRPC services: Our gRPC services support ready/live status via [grpc health probe](https://github.com/grpc-ecosystem/grpc-health-probe), which works fine for Docker Desktops local Kubernetes cluster, but does not seem to work with GKE.
- inter-pod communication: Communication to / from jaeger OpenTelemetry Collector, Jaeger backend, flask Frontend and our tid-service seem to work - but for reasons not understood the communication between our demonstrators gRPC service seems not to work.

Hints why our Kubernetes deployment does not run as expected, especially after going trough all the work of understanding how to build, register and publish images in the cloud and trying to understand the differences between a docker compose deploy and Kubernetes would be highly appreciated...

## Use

Your containers are up and running - so how to make use of the Transparency Information Dictionary? In the following diagram you can see how our dictionary service, the demonstrator services, the OpenTelemetry Collector and the Jaeger backend interact with each other - with numbered steps 1 to 8 to explain the flow. So lets go through them.

![TI-Dictionary Architecture](https://github.com/fex01/transparency-information-dictionary/blob/main/images/ti-dictionary_architecture.png)

### Enrich Services With Transparency Information

To get service level detailed transparency information via tracing the services code has to be annotated with said transparency information.
We aim to avoid a wild mixup of different interpretations and expressions of free form transparency information, which would make it hard to compare and aggregate information from different services. Our dictionary is a tool to provide company wide “sanctioned” options - expressed as tags.

Ideally the interaction with the tid-service to retrieve tag options and annotate the service in development would be supported with an IDE plugin - but that might be it’s own further Privacy Engineering project ;-)

So for now let’s have a look at how to do this manually:

#### 1) Request Tags for Transparency Information

To understand the interaction with the tid-service let’s have a look at an excerpt of the [protobuf](https://developers.google.com/protocol-buffers/) file defining the service request for Data Disclosed properties:

```proto
# protobufs/tid.proto

service TIDict {
    // get lists of options defined in the company dictionary for Data Disclosed properties
    // DataDisclosedRequest.value = a value of enum DataDisclosedType
    // returns DataDisclosedResponse.list = [property_1 .. property_n]
    rpc GetDataDisclosedOfType(DataDisclosedRequest) returns (DataDisclosedResponse);
    …
}

message DataDisclosedRequest {
    DataDisclosedType value = 1;
}

message DataDisclosedResponse {
    repeated DataDisclosedEntry list = 1;
}

enum DataDisclosedType {
    CATEGORY = 0;
    PURPOSE = 1;
    LEGAL_BASE = 2;
    RECIPIENT = 3;
    STORAGE = 4;
}
```

Let's have a look at how to query this function and at an example output:

```python
# tid-service/tid_test.py
...
def test_02_category(self):
    # request the list of possible Data Disclosed Categories
    response = tid_server.GetDataDisclosedOfType(
        tid_pb2.DataDisclosedRequest(value=tid_pb2.CATEGORY), None
    )
    print(response.list)
    assert response.list[0].category.id == "C01"
...
```

```json
// abbreviated output for tid-service/tid_test.py/test_02_category()
[
  category {
    id: "C01"
    value: "E-mail address"
  }, 
  ...
  category {
    id: "C11"
    value: "Credit score"
  }
]
```

Let's assume we have to annotate an email-service - so picking tag `C01` for category might be a good start. Do the same for other Data Disclosed properties - and other supported [TIL](https://transparency-information-language.github.io/schema/index.html) objects to assemble the necessary tags for [step 2](#2-annotating-services-with-transparency-information).

#### 2) Annotate Services With Transparency Information

Add tags as tracing attributes to the code - here an example of out demonstrators email service:

```python
# demonstrator/emailservice/email_service.py
...
class EmailService(demo_pb2_grpc.EmailServicer):
  ...
  def Send(self, request, context):
    # get the current span to add attributes to tracing
    span = trace.get_current_span()
    # each TIL objects needs its own line
    # attribute identifier (first string) needs to start with "ti_", the rest needs to be unique for this span
    # ti_c01: Data Disclosed object for category C01: E-mail address
    span.set_attribute("ti_c01", ["C01", "R02", "COA7_C1", "ST11"])
    span.set_attribute("ti_c07", ["C07", "COA7_C1", "ST11"])
    span.set_attribute("ti_tct01", ["TCT01"])
    ...
```

Having done that with all your services you are now good to go to reap the benefits. [Test](#test-to-generate-traces) your application, use standard test strategies to ensure service coverage and generate ex-ante [formatted Transparency Information](#collect-transparency-information-from-traces) for use with further tools such as [TILT](#sources).

### Test to Generate Traces

To get detailed service level transparency information via tracing it has to be ensured that each service [enriched with transparency information](#enrich-services-with-transparency-information) gets covered by service calls. Since service / component coverage is part of every integration test strategy - just run your (hopefully existing) integration test:

#### 3) Trigger Integration Test With Activated Tracing

Ensure that you are running your services with activated tracing and use your existing tools for testing (and test automation) to make service calls.
For our demonstrator tracing is baked into the Dockerfiles:

```dockerfile
# demonstrator/emailservice/Dockerfile
...
ENTRYPOINT [ "opentelemetry-instrument", "python", "email_service.py" ]
```

To run the container without tracing you would just delete the first list entry *"opentelemetry-instrument"* from *ENTRYPOINT* before building the image.

As testing tool we are using [pytest](https://docs.pytest.org/en/7.1.x/), an example for a test case would be the following excerpt from the integration test:

```python
# tid-service/integration_test.py
...
def test_06_frontend_create_account():
  data = parse.urlencode({"create_account": "Create Account"}).encode()
  homepage_html = urlopen(frontend, data).read().decode("utf-8")
  assert "response code: SUCCESS" in homepage_html
...
```

The test case triggers the service *frontend* to send a request for creating a new user account to service *accountservice* and asserts a successful response.
As you can see - the test tool and the test definition have no connection to tracing nor tid-specific annotations.

For this demonstration just run *tid-service/integration_test.py* to generate traces. Just connect to the tid-service container (Docker or pod (Kubernetes) (the following commands are for use with Docker containers, the Kubernetes commands are very similar):

- `docker exec -it transparency_tracing-tidservice-1 bash` to connect to the tid-service container and use its bash shell
- `pytest integration_test.py` to run the integration test

#### 4) Spans Are Collected And Forwarded as Traces to the Jaeger Backend

To collect traces with [OpenTelemetry](https://opentelemetry.io) and [Jaeger](https://www.jaegertracing.io) we are using an OpenTelemetry Collector (service *otelcollector*) and the [*jaegertracing/opentelemetry-all-in-one*](https://www.jaegertracing.io/docs/1.35/getting-started/) image as tracing backend.
Make sure that you expose jaegers gRPC query port to enable [trace querying for our tid-service](#6-jaeger-backend-gets-queried-regarding-all-services-and-traces).

You can see the traces generated in [step 3](#3-trigger-integration-test-with-activated-tracing) via the jaeger backend - if you did use the provided docker compose file the backend can be found at <http://localhost:16686>.
The following screenshot is a trace covering multiple services. You can fin the familiar tag lists mentioned in [step 2](#2-annotate-services-with-transparency-information) in the expanded tag section for span *emailservice*:

![trace with tag section for span emailservice expanded](https://github.com/fex01/transparency-information-dictionary/blob/main/images/20220711_trace_expanded.png)

### Collect Transparency Information From Traces

#### 5) Request Formatted Transparency Information From Traces

#### 6) Jaeger Backend Gets Queried Regarding All Services and Traces

#### 7) Returns Collected Traces as JSON

#### 8) Filters Traces for Tags and Transforms Them Into TIL Objects

## Concepts

## Tools & Technology

## Thanks

- To my project partner [Ronny Georgi](https://github.com/georgir20)
- To [Juliano Costa](https://github.com/julianocosta89) and his repo [opentelemetry-microservice-demo](https://github.com/julianocosta89/opentelemetry-microservices-demo). His repository was a great help getting started with - and on the way to - understanding how tracing with OpenTelemetry works - and he personally answered many of our technical questions, even completely unrelated to tracing itself.

## Sources

## Footnotes

<b id="f1">1</b>: Git as locally installed tool, not a platform like GitHub. [git-scm.com](https://git-scm.com) might be a good starting point to understand the difference und to find an installation for your OS. [↩](#a1)  
<b id="f1">2</b>: The newer v2 of [`docker-compose`](https://docs.docker.com/compose/) - now without the hyphen `-`. If you are using a current version of Docker Desktop than you are good to go. On Linux you might have to update manually. Relevant, because the old command `docker-compose` might have trouble with the environment variables or other untested side effects. [↩](#a2)
