# Transparency Information Dictionary

- [Quick Start](#quick-start)
  - [Docker](#docker)
  - [Kubernetes](#kubernetes)
- [Concepts](#concepts)
- [Tools & Technology](#tools--technology)
- [Thanks](#thanks)
- [Sources](#sources)
- [Footnotes](#footnotes)

## Quick Start

### Docker

For now it's enough to have an environment with git[↩](#a1), [Docker](https://www.docker.com) and `docker compose`[↩](#a2) to get started:

- `git clone https://github.com/fex01/transparency-information-dictionary.git` clone the repository
- `cd transparency-information-dictionary` move into the repos directory
- `docker compose build` build the images for the demonstrator and the Transparency Information Dictionary Service (tid-services)
- `docker compose up` start container for the tid-service, demonstrator services, a [OpenTelemetry](https://opentelemetry.io) collector service and a [jaeger](https://www.jaegertracing.io) backend

### Kubernetes

The images are provided at `europe-north1-docker.pkg.dev/ti-dictionary/transparency-information-dictionary/<service-name>` via the [Google Artifact Registry](https://cloud.google.com/artifact-registry) (complete with automated builds via this repository). A kubernetes manifest was created and is part of this repository - but the author could not get the deployment to work via the [Google Kubernetes Engine (GKE)](https://cloud.google.com/kubernetes-engine/). The main problems seem to be:

- discover ready/live status for gRPC services: Our gRPC services support ready/live status via [grpc health probe](https://github.com/grpc-ecosystem/grpc-health-probe), which works fine for Docker Desktops local Kubernetes cluster, but does not seem to work with GKE.
- inter-pod communication: Communication to / from jaeger OpenTelemetry Collector, Jaeger backend, flask Frontend and our tid-service seem to work - but for reasons not understood the communication between our demonstrators gRPC service seems not to work.

Hints why our Kubernetes deployment does not run as expected, especially after going trough all the work of understanding how to build, register and publish images in the cloud and trying to understand the differences between a docker compose deploy and Kubernetes would be highly appreciated...

## Concepts

## Tools & Technology

## Thanks

- To my project partner [Ronny Georgi](https://github.com/georgir20)
- To [Juliano Costa](https://github.com/julianocosta89) and his repo [opentelemetry-microservice-demo](https://github.com/julianocosta89/opentelemetry-microservices-demo). His repository was a great help getting started with and on the way to understanding how tracing with OpenTelemetry works - and he personally answered many of our technical questions, even completely unrelated to tracing itself.

## Sources

## Footnotes

<b id="f1">1</b>: Git as locally installed tool, not a platform like GitHub. [git-scm.com](https://git-scm.com) might be a good starting point to understand the difference und to find an installation for your OS.  
<b id="f1">2</b>: The newer v2 of [`docker-compose`](https://docs.docker.com/compose/) - now without the hyphen `-`. If you are using a current version of Docker Desktop than you are good to go. On Linux you might have to update manually. Relevant, because the old command `docker-compose` might have trouble with the environment variables or other untested side effects.
