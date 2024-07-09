# `openlane_plugin_example`

This is a demonstrative example on how to make a plugin for OpenLane 2 that
includes both a custom step and a custom flow.

The step has a tool dependency, namely Ruby, to demonstrate the inclusion of an
open-source utility wiht a plugin.

## Testing this Plugin

Checking if the plugin is recognized by OpenLane:

```bash
$ nix develop --command openlane --version
[…]
Discovered plugins:
openlane_plugin_example -> 0.1.0
```

Testing that the added step and flow are working correctly:

```bash
$ nix develop --command openlane --flow FlowWithCustomAreaDoubler --run-example spm
```

## License
Apache License, version 2.0.

See `License`.

