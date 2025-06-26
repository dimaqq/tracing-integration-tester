# Tracing Integration Tester

This is a mock trace data collector.

Relate your app to it in your integration tests to validate that your charm
or workload tracing works are expected.

It is much lighter than the COS stack.

This charm can be deployed on both k8s and machines.

This charm is not meant for production.


### Limitations

CORS response headers and OPTIONS requests are not supported.
Don't aim your browser at this charm.

TLS/CA integration is not presently supported. This will be done later.
