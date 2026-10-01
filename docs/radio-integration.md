# Radio/audio interface boundary

VoxShield currently exposes standard mono audio-device input/output. That output can feed a radio
only through an interface appropriate to the specific radio; the software must not guess its
levels, connector, push-to-talk behavior, isolation, or regulatory requirements.

Before integration, record:

- radio make/model and whether the port is microphone-level, line-level, USB audio, or digital;
- required impedance, maximum RMS/peak voltage, bias voltage, balanced/unbalanced wiring, and
  galvanic-isolation needs;
- push-to-talk/control protocol and the safe state on process or power failure;
- sample rate/format if the radio presents a digital interface;
- hardware limiter/protection and a physical bypass path independent of Python and the Pi.

Validate first into a dummy load or recorder at low gain. Measure clipping, noise floor, frequency
response, round-trip latency, and behavior during unplug/replug, process crash, Pi reboot, and power
loss. The live runtime reports PortAudio status events and systemd can restart a failed process,
but neither is a safety-rated hardware fail-safe.

