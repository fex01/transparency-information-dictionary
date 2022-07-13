# Transparency Information Dictionary

*The Transparency Information Dictionary was developed as part of the module Privacy Engineering from Dr. Frank Pallas at Technical University Berlin during the Summer Semester 2022.*

Transparency - one of the key concepts of Data Protection as defined by the GDPR is a major challenge for fast-paced, agile software development as summarized under concepts such as DevOps. One common way DevOps centred approaches mitigate challenges is to develop and integrate ready-to-use tools for specific problems, automating where possible to speed up development time.

The Transparency Information Dictionary is an approach to bring these qualities to the domain of Transparency by 1) developing a concept to enrich existing Open Source tracing solutions for performance monitoring with service-level transparency information to generate and collect dynamic per-request transparency information traces, 2) combining this with methods from the area of quality assurance we level testing to ensure coverage and complete, highly detailed ex-ante transparency information, 3) which is to be structured in the [Transparency Information Language](#tools--technologies) to enable the use of existing and to be developed tools to aggregate, manage and present transparency information.

Such offering service-providers a tool that decreases the need for overly broad and vague privacy policies.

## Table of Content

Head to section [Spin Up](#spin-up) and [Use](#use) to spin up the demonstrator yourself and to go step by step through the process of how to use the Transparency Information Dictionary.

Head to section [Tools & Technologies](#tools--technologies) to find further information about the tools and technologies used in this project.

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
  - [5)-8) Collect Transparency Information From Traces](#5-8-collect-transparency-information-from-traces)
  - [Adding Transparency Information Values to the Underlying Dictionary](#adding-transparency-information-values-to-the-underlying-dictionary)
- [Tools & Technologies](#tools--technologies)
- [Thanks](#thanks)
- [Footnotes](#footnotes)

## Spin Up

The default deployment is the [docker compose deployment](#docker), all commands listed in [Use](#use) will assume the default deployment. But if you are familiar with Kubernetes deployments you will have no trouble translating them to their `kubectl` counterpart. Same will hold for expressions like *container* instead of *pod* and use of *localhost* addresses for said container.

### Docker

For now it's enough to have an environment with git<sup id="a1">[1](#f1)</sup>, [Docker](https://www.docker.com) and `docker compose`<sup id="a2">[2](#f2)</sup> to get started:

- `git clone https://github.com/fex01/transparency-information-dictionary.git` clone the repository
- `cd transparency-information-dictionary` move into the repos directory
- `docker compose build` build the images for the demonstrator and the Transparency Information Dictionary Service (tid-services)
- `docker compose up` start container for the tid-service, demonstrator services, a [OpenTelemetry](https://opentelemetry.io) collector service and a [jaeger](https://www.jaegertracing.io) backend

### Kubernetes

The images are provided at `europe-north1-docker.pkg.dev/ti-dictionary/transparency-information-dictionary/<service-name>` via the [Google Artifact Registry](#tools--technologies) (complete with automated builds via this repository). A kubernetes manifest was created and is part of this repository - but the author could not get the deployment to work via the [Google Kubernetes Engine (GKE)](#tools--technologies). The main problems seem to be:

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

To understand the interaction with the tid-service let’s have a look at an excerpt of the [protobuf](#tools--technologies) file defining the service request for Data Disclosed properties:

```proto
# protobufs/tid.proto

service TIDict {
    // get lists of options defined in the company dictionary for Data Disclosed properties
    // DataDisclosedRequest.value = a value of enum DataDisclosedType
    // returns DataDisclosedResponse.list = [property_1 .. property_n]
    rpc GetDataDisclosedOfType(DataDisclosedRequest) returns (DataDisclosedResponse);
    ...
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

If you want to run the test yourself you can either install the necessary requirements locally with `cd tid-service && pip install -r requirements.txt` - or just connect to the tid-service container `docker exec -it transparency_tracing-tidservice-1 bash` to then use  

- `pytest -s tid_test.py::TestTIDictService::test_02_category` to run the test and print the output to the console
  - do not overlook flag `-s` to actually show to output in the console

```txt
// abbreviated output for tid_test.py::TestTIDictService::test_02_category
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

**Path**: If you used the command `cd tid-service && pip install -r requirements.txt` please switch back to the main directory with `cd ..` after testing :-)

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
    # attribute identifier (first string) needs to start with "ti_",
    # the rest needs to be unique for this span
    # ti_c01: Data Disclosed object for category C01: E-mail address
    span.set_attribute("ti_c01", ["C01", "R02", "COA7_C1", "ST11"])
    span.set_attribute("ti_c07", ["C07", "COA7_C1", "ST11"])
    span.set_attribute("ti_tct01", ["TCT01"])
    ...
```

Let's keep an eye on the first tag list *ti_c01* with the tag *C01* for E-mail address (mentioned in [step 1](#1-request-tags-for-transparency-information)) for later reference.

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

Run the test, either locally or in the *tid-service* container (compare [step 1](#1-request-tags-for-transparency-information)), with `pytest integration_test.py` to trigger the integration test.

As an alternative you can also open the minimal webpage provided by the frontend service to manually trigger service calls. For the docker compose setup the frontend can be found at <http://localhost:5000/>.

#### 4) Spans Are Collected And Forwarded as Traces to the Jaeger Backend

To collect traces with [OpenTelemetry](https://opentelemetry.io) and [Jaeger](https://www.jaegertracing.io) we are using an OpenTelemetry Collector (service *otelcollector*) and the [*jaegertracing/opentelemetry-all-in-one*](https://www.jaegertracing.io/docs/1.35/getting-started/) image as tracing backend.
Make sure that you expose jaegers gRPC query port to enable [trace querying for our tid-service](#6-jaeger-backend-gets-queried-regarding-all-services-and-traces).

You can see the traces generated in [step 3](#3-trigger-integration-test-with-activated-tracing) via the jaeger backend - if you did use the provided docker compose file the backend can be found at <http://localhost:16686>.

The following screenshot is a trace covering multiple services. You can find the familiar tag lists mentioned in [step 2](#2-annotate-services-with-transparency-information) in the expanded tag section for span *emailservice* - for example *ti_c01*:

![trace with tag section for span emailservice expanded](https://github.com/fex01/transparency-information-dictionary/blob/main/images/20220711_trace_expanded.png)

### 5)-8) Collect Transparency Information From Traces

Now how to go forward from transparency information encoded as tags in traces on the jaeger backend? Thats where the last function offered by our *tid-service* comes into play:

The *tid-service* offers a function to get the transparency information from all traces of the last x minutes as formatted [TIL](#tools--technologies) objects - sorted by service:

```proto
# protobufs/tid.proto

service TIDict {
    ...
    rpc GetTransparencyInformationFromTraces(TransparencyInformationRequest) returns (TransparencyInformationResponse);
}

message TransparencyInformationRequest {
    int32 cover_traces_of_the_last_x_min = 1;
}

message TransparencyInformationResponse {
    repeated ServiceRelatedTransparencyInformation services = 1;
    message ServiceRelatedTransparencyInformation {
        string service = 1;
        repeated DataDisclosed data_disclosed_entries = 2;
        repeated ThirdCountryTransfer third_country_transfers = 3;
        repeated ChangesOfPurpose changes_of_purposes = 4;
    }
}
```

Once again will will have a look into *tid-service/tid_test.py* to see how to use this function:

```python
# tid-service/tid_test.py
...
def test_14_for_traces_from_all_services(self):
  response = tid_server.GetTransparencyInformationFromTraces(
      tid_pb2.TransparencyInformationRequest(cover_traces_of_the_last_x_min=30), None
  )
  pprint(response)
  ...  # some assertions follow to validate the response
...
```

If you want to run the test yourself (compare [step 1](#1-request-tags-for-transparency-information)) execute `pytest -s tid_test.py::TestTIDictService::test_14_for_traces_from_all_services`.

- remember the flag `-s` to actually show to output in the console
- the traces for the last 30 minutes are requested (compare `cover_traces_of_the_last_x_min=30`), if your last service call was longer ago you will get empty results

```txt
// abbreviated output for tid_test.py::TestTIDictService::test_14_for_traces_from_all_services

tid_test.py services {
  service: "emailservice"
  data_disclosed_entries {
    id: "C01_R02_COA7_C1_ST11"
    category: "E-mail address"
    purposes {
      id: "COA7_C1"
      purpose: "Communications"
      description: "Data are processed for any activities that are focused on communication with the customer."
    }
    recipients {
      id: "R02"
      name: "Best Communication Delivery Company AG"
      division: "Third Party E-mail Service"
      address: "Triana 123, 9999 Seville"
      country: "ES"
      representative {
        name: "Jane Super"
        email: "contact@yellowcompany.de"
        phone: "0049 151 1234 9876"
      }
      category: "Service provider e-mail"
    }
    storage {
      temporal {
        description: "Live data - log detention time."
        ttl: "P0Y0M1W0DT0H0M0S"
      }
    }
  }
  data_disclosed_entries {...}
  third_country_transfers {...}
}
services {
  service: "accountservice"
  ...
}
services {
  service: "courierservice"
  ...
}
services {
  service: "frontend"
  ...
}
```

As you can see you get a list of all services, each one with all the associated Transparency Information structured according to [TIL]. For example, the fully listed DataDisclosed entry with the id *C01_R02_COA7_C1_ST11* is the result of the tag list *ti_c01* already highlighted in steps [2](#2-annotate-services-with-transparency-information) and [4](#4-spans-are-collected-and-forwarded-as-traces-to-the-jaeger-backend).

### Adding Transparency Information Values to the Underlying Dictionary

We are not providing any tool assistant for filling / adapting the underlying dictionary - that might, including a concept to restrict dictionary adaption to specific access conditions and expanding the service to additional [TIL](#tools--technologies) properties, be it's own further project.

What we do, in the docker compose setup, is mounting the repos dictionary as a bind mount into the *tid-service* container. As such everybody with access to the host running the container can use whatever tools are preferred to edit the JSON file *dictionary/TransparencyInformationDictionary.json*. This is possible during the runtime of the container, the service will incorporate changes to said file on the fly.

## Tools & Technologies

- [Transparency Information Language (TIL) Root Schema](https://transparency-information-language.github.io/schema/index.html) - defining a structured language to express transparency information
- Python gRPC microservices - have a look at [Real Python](https://realpython.com/python-microservices-grpc/#docker) for a great introduction
- [protocol buffers (protobufs)](https://developers.google.com/protocol-buffers/) - to define our gRPC microservices
- [OpenTelemetry](https://opentelemetry.io) - a collection of tools, APIs, and SDKs that be used to instrument, generate and collect telemetry data (metrics, logs, and traces) to help analyzing software performance and behavior
- [Jaeger Tracing](https://www.jaegertracing.io) - distributed tracing system
  - [Trace retrieval APIs - gRPC/Protobuf (stable)](https://www.jaegertracing.io/docs/1.36/apis/#grpcprotobuf-stable)
    - due to a number of dependencies generating the Jaeger gRPC stubs requires to clone the [jaeger-idl](https://github.com/jaegertracing/jaeger-idl) (including submodules!)
- [Docker](https://www.docker.com)
- Google Cloud Services
  - [Google Cloud Build](https://cloud.google.com/build)
  - [Google Cloud Artifact Registry](https://cloud.google.com/artifact-registry)
  - [Google Kubernetes Engine](https://cloud.google.com/kubernetes-engine)

## Thanks

- To my project partner [Ronny Georgi](https://github.com/georgir20)
- To [Juliano Costa](https://github.com/julianocosta89) and his repo [opentelemetry-microservice-demo](https://github.com/julianocosta89/opentelemetry-microservices-demo). His repository was a great help getting started with - and on the way to - understanding how tracing with OpenTelemetry works - and he personally answered many of our technical questions, even completely unrelated to tracing itself.

## Footnotes

<b id="f1">1</b>: Git as locally installed tool, not a platform like GitHub. [git-scm.com](https://git-scm.com) might be a good starting point to understand the difference und to find an installation for your OS. [↩](#a1)  
<b id="f1">2</b>: The newer v2 of [`docker-compose`](https://docs.docker.com/compose/) - now without the hyphen `-`. If you are using a current version of Docker Desktop than you are good to go. On Linux you might have to update manually. Relevant, because the old command `docker-compose` might have trouble with the environment variables or other untested side effects. [↩](#a2)
