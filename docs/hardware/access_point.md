# Access point integration

`access_point/base.py` defines `AccessPointAdapter`. The only shipped implementation
is `UnconfiguredAccessPointAdapter`, which always reports `UNSUPPORTED` — no AP hardware or
vendor API was available to build and verify a real one against. This is an honest interface
stub, not a working integration: implement a concrete subclass for your AP vendor before using
AP-based enforcement.
