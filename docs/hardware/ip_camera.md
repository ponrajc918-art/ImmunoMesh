# IP camera integration

Two independent, read-only probes — neither accesses video:
- `camera/rtsp.py`: a plain TCP connect + RTSP `OPTIONS` request on port 554. Confirms an RTSP
  service answers; never streams video, never sends credentials.
- `camera/onvif.py`: one real WS-Discovery multicast probe (stdlib socket, no onvif/zeep
  dependency) to `239.255.255.250:3702`. Returns exactly what answered within the timeout —
  verified in this environment to correctly return `[]` when no camera is present (no fabricated
  detection).

Device classification (`devices/classification.py`) also flags a device as `"camera"` purely from
observed traffic (RTSP/ONVIF ports) with no active probe needed, once some flows have been seen.

**Not implemented**: ONVIF device-management calls (pulling camera metadata/model), credentialed
RTSP, or any video access — out of scope: the project's objective is to monitor the camera's network behaviour, not its stream.
