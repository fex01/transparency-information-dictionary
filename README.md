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

## Concepts

## Tools & Technology

## Thanks

## Sources

## Footnotes

<b id="f1">1</b>: Git as locally installed tool, not a platform like GitHub. [git-scm.com](https://git-scm.com) might be a good starting point to understand the difference und to find an installation for your OS.  
<b id="f1">2</b>: The newer v2 of [`docker-compose`](https://docs.docker.com/compose/) - now without the hyphen `-`. If you are using a current version of Docker Desktop than you are good to go. On Linux you might have to update manually. Relevant, because the old command `docker-compose` might have trouble with the environment variables or other untested side effects.
