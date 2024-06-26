# `openlane_plugin_example`

This is a demonstrative example on how to make a plugin for OpenLane 2 that
includes both a custom step and a custom flow.

The step has a tool dependency, namely Ruby, to demonstrate the inclusion of an
open-source utility wiht a plugin.

## Testing this Plugin

You can test this plugin by invoking:

```
nix develop --command openlane --flow FlowWithCustomAreaDoubler --run-example spm
```

## License
Apache License, version 2.0.

See `License`.

